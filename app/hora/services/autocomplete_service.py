"""Autocomplete service centralizado para telas de listagem do modulo HORA.

Cada funcao recebe `q` (texto digitado) e `lojas_permitidas_ids` (escopo do
usuario via auth_helper.lojas_permitidas_ids()). Retornam lista de dicts
prontos para serializacao JSON.

Convencoes:
- Minimo 2 caracteres para nao retornar tudo
- Limite default 20
- Busca case-insensitive (ilike)
- Ordenacao por relevancia (mais recente primeiro quando aplicavel)
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_

from app import db
from app.hora.models import (
    HoraEmprestimoMoto,
    HoraLoja,
    HoraModelo,
    HoraMoto,
    HoraMotoEvento,
    HoraNfEntrada,
    HoraPedido,
    HoraVenda,
)


_MIN_CHARS = 2
_DEFAULT_LIMIT = 20


def _chassis_permitidos_subq(lojas_permitidas_ids: Optional[List[int]]):
    """Subquery: chassis que tiveram ao menos 1 evento em loja permitida.

    Mesmo criterio do estoque_service para autorizacao por loja.
    Retorna None se admin (sem filtro de loja).
    """
    if lojas_permitidas_ids is None:
        return None
    if not lojas_permitidas_ids:
        return False  # sentinela: usuario sem nenhuma loja
    return (
        db.session.query(HoraMotoEvento.numero_chassi)
        .filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))
        .distinct()
        .subquery()
    )


# ============================================================
# Chassis
# ============================================================

def chassis(q: str, lojas_permitidas_ids: Optional[List[int]] = None,
            limit: int = _DEFAULT_LIMIT) -> List[dict]:
    """Busca chassis por substring (sempre uppercase, ilike)."""
    q_norm = (q or '').strip().upper()
    if len(q_norm) < _MIN_CHARS:
        return []

    base = (
        db.session.query(HoraMoto, HoraModelo)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .filter(HoraMoto.numero_chassi.ilike(f'%{q_norm}%'))
    )

    sub = _chassis_permitidos_subq(lojas_permitidas_ids)
    if sub is False:
        return []
    if sub is not None:
        base = base.filter(HoraMoto.numero_chassi.in_(sub))

    base = base.order_by(HoraMoto.numero_chassi).limit(limit)
    return [
        {
            'chassi': m.numero_chassi,
            'modelo': modelo.nome_modelo,
            'cor': m.cor,
            'label': f'{m.numero_chassi} — {modelo.nome_modelo} ({m.cor})',
        }
        for m, modelo in base.all()
    ]


# ============================================================
# Pedidos de compra (HORA -> Motochefe)
# ============================================================

def pedidos_compra(q: str, lojas_permitidas_ids: Optional[List[int]] = None,
                   limit: int = _DEFAULT_LIMIT) -> List[dict]:
    """Busca pedidos por numero_pedido (substring).

    Filtra por escopo via loja_destino_id.
    """
    q_norm = (q or '').strip()
    if len(q_norm) < _MIN_CHARS:
        return []

    base = HoraPedido.query.filter(
        HoraPedido.numero_pedido.ilike(f'%{q_norm}%')
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        base = base.filter(HoraPedido.loja_destino_id.in_(lojas_permitidas_ids))

    base = base.order_by(HoraPedido.data_pedido.desc(), HoraPedido.id.desc()).limit(limit)
    return [
        {
            'id': p.id,
            'numero_pedido': p.numero_pedido,
            'data_pedido': p.data_pedido.isoformat() if p.data_pedido else None,
            'loja_destino': p.loja_destino.rotulo_display if p.loja_destino else None,
            'status': p.status,
            'label': (
                f'{p.numero_pedido} — '
                f'{p.data_pedido.strftime("%d/%m/%Y") if p.data_pedido else "?"} '
                f'· {p.loja_destino.rotulo_display if p.loja_destino else "sem loja"} '
                f'[{p.status}]'
            ),
        }
        for p in base.all()
    ]


# ============================================================
# NFs de entrada (Motochefe -> HORA)
# ============================================================

def nfs_entrada(q: str, lojas_permitidas_ids: Optional[List[int]] = None,
                limit: int = _DEFAULT_LIMIT) -> List[dict]:
    """Busca NFs entrada por numero (substring)."""
    q_norm = (q or '').strip()
    if len(q_norm) < _MIN_CHARS:
        return []

    base = HoraNfEntrada.query.filter(
        HoraNfEntrada.numero_nf.ilike(f'%{q_norm}%')
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        # NFs sem loja_destino_id ficam visiveis apenas para admin (sem escopo).
        base = base.filter(HoraNfEntrada.loja_destino_id.in_(lojas_permitidas_ids))

    base = base.order_by(HoraNfEntrada.data_emissao.desc(), HoraNfEntrada.id.desc()).limit(limit)
    return [
        {
            'id': nf.id,
            'numero_nf': nf.numero_nf,
            'emitente': nf.nome_emitente or nf.cnpj_emitente,
            'data_emissao': nf.data_emissao.isoformat() if nf.data_emissao else None,
            'loja_destino': nf.loja_destino.rotulo_display if nf.loja_destino else None,
            'label': (
                f'NF {nf.numero_nf} — '
                f'{nf.data_emissao.strftime("%d/%m/%Y") if nf.data_emissao else "?"} '
                f'· {nf.nome_emitente or nf.cnpj_emitente or "sem emissor"}'
            ),
        }
        for nf in base.all()
    ]


# ============================================================
# Vendas (NF saida) — busca por numero NF, cliente nome ou CPF
# ============================================================

def vendas(q: str, lojas_permitidas_ids: Optional[List[int]] = None,
           limit: int = _DEFAULT_LIMIT) -> List[dict]:
    """Busca vendas por nf_saida_numero, nome_cliente ou cpf_cliente."""
    q_norm = (q or '').strip()
    if len(q_norm) < _MIN_CHARS:
        return []

    only_digits = ''.join(c for c in q_norm if c.isdigit())

    conds = [
        HoraVenda.nf_saida_numero.ilike(f'%{q_norm}%'),
        HoraVenda.nome_cliente.ilike(f'%{q_norm}%'),
    ]
    if only_digits:
        conds.append(HoraVenda.cpf_cliente.ilike(f'%{only_digits}%'))

    base = HoraVenda.query.filter(or_(*conds))
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        base = base.filter(HoraVenda.loja_id.in_(lojas_permitidas_ids))

    base = base.order_by(HoraVenda.data_venda.desc(), HoraVenda.id.desc()).limit(limit)
    return [
        {
            'id': v.id,
            'nf_saida_numero': v.nf_saida_numero,
            'nome_cliente': v.nome_cliente,
            'cpf_cliente': v.cpf_cliente,
            'data_venda': v.data_venda.isoformat() if v.data_venda else None,
            'loja': v.loja.rotulo_display if v.loja else None,
            'status': v.status,
            'label': (
                f'{("NF " + v.nf_saida_numero) if v.nf_saida_numero else f"Pedido #{v.id}"} '
                f'— {v.nome_cliente} '
                f'· {v.data_venda.strftime("%d/%m/%Y") if v.data_venda else "?"} '
                f'[{v.status}]'
            ),
        }
        for v in base.all()
    ]


def clientes_venda(q: str, lojas_permitidas_ids: Optional[List[int]] = None,
                   limit: int = _DEFAULT_LIMIT) -> List[dict]:
    """Busca clientes UNICOS (nome + cpf) de vendas. Para autocomplete de
    filtros que precisam apenas de nome/CPF, nao da venda inteira."""
    q_norm = (q or '').strip()
    if len(q_norm) < _MIN_CHARS:
        return []
    only_digits = ''.join(c for c in q_norm if c.isdigit())

    conds = [HoraVenda.nome_cliente.ilike(f'%{q_norm}%')]
    if only_digits:
        conds.append(HoraVenda.cpf_cliente.ilike(f'%{only_digits}%'))

    base = (
        db.session.query(HoraVenda.nome_cliente, HoraVenda.cpf_cliente)
        .filter(or_(*conds))
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        base = base.filter(HoraVenda.loja_id.in_(lojas_permitidas_ids))

    base = base.distinct().order_by(HoraVenda.nome_cliente).limit(limit)
    return [
        {
            'nome_cliente': nome,
            'cpf_cliente': cpf,
            'label': f'{nome} ({cpf})' if cpf else nome,
        }
        for nome, cpf in base.all()
    ]


# ============================================================
# Lojas externas (emprestimos)
# ============================================================

def lojas_externas(q: str, limit: int = _DEFAULT_LIMIT) -> List[dict]:
    """Busca lojas externas distintas registradas em emprestimos por nome ou CNPJ."""
    q_norm = (q or '').strip()
    if len(q_norm) < _MIN_CHARS:
        return []
    only_digits = ''.join(c for c in q_norm if c.isdigit())

    cond = HoraEmprestimoMoto.loja_externa_nome.ilike(f'%{q_norm}%')
    if only_digits:
        cond = or_(cond, HoraEmprestimoMoto.loja_externa_cnpj.ilike(f'%{only_digits}%'))

    base = (
        db.session.query(
            HoraEmprestimoMoto.loja_externa_nome,
            HoraEmprestimoMoto.loja_externa_cnpj,
        )
        .filter(cond)
        .distinct()
        .order_by(HoraEmprestimoMoto.loja_externa_nome)
        .limit(limit)
    )
    return [
        {
            'nome': nome,
            'cnpj': cnpj,
            'label': f'{nome}{(" — CNPJ " + cnpj) if cnpj else ""}',
        }
        for nome, cnpj in base.all()
    ]


# ============================================================
# Modelos
# ============================================================

def modelos(q: str, apenas_ativos: bool = True,
            limit: int = _DEFAULT_LIMIT) -> List[dict]:
    """Busca modelos por nome (substring) + por aliases. Inclui modelos sem chassi (cadastro novo).

    Migration hora_29: tambem busca em hora_modelo_alias (qualquer tipo)
    para que o usuario digite "BOB AM" e ache modelo BOB. Modelos absorvidos
    (merged_em_id NOT NULL) sao automaticamente excluidos.
    """
    from app.hora.models import HoraModeloAlias

    q_norm = (q or '').strip()
    if len(q_norm) < _MIN_CHARS:
        return []

    # Busca por nome direto OU por alias
    matched_via_alias = (
        db.session.query(HoraModeloAlias.modelo_id)
        .filter(HoraModeloAlias.nome_alias.ilike(f'%{q_norm}%'))
        .subquery()
    )

    from sqlalchemy import or_
    base = HoraModelo.query.filter(
        or_(
            HoraModelo.nome_modelo.ilike(f'%{q_norm}%'),
            HoraModelo.id.in_(db.session.query(matched_via_alias.c.modelo_id)),
        )
    )
    if apenas_ativos:
        base = base.filter(HoraModelo.ativo.is_(True))
    # Sempre exclui modelos absorvidos — eles nao sao escolhiveis em UI.
    base = base.filter(HoraModelo.merged_em_id.is_(None))
    base = base.order_by(HoraModelo.nome_modelo).limit(limit)
    return [
        {
            'id': m.id,
            'nome_modelo': m.nome_modelo,
            'ativo': m.ativo,
            'label': m.nome_modelo + ('' if m.ativo else ' [inativo]'),
        }
        for m in base.all()
    ]


# ============================================================
# Lojas (cadastro)
# ============================================================

def lojas(q: str, lojas_permitidas_ids: Optional[List[int]] = None,
          apenas_ativas: bool = True,
          limit: int = _DEFAULT_LIMIT) -> List[dict]:
    """Busca lojas por nome, apelido, razao_social ou nome_fantasia."""
    q_norm = (q or '').strip()
    if len(q_norm) < _MIN_CHARS:
        return []

    cond = or_(
        HoraLoja.nome.ilike(f'%{q_norm}%'),
        HoraLoja.apelido.ilike(f'%{q_norm}%'),
        HoraLoja.razao_social.ilike(f'%{q_norm}%'),
        HoraLoja.nome_fantasia.ilike(f'%{q_norm}%'),
    )
    base = HoraLoja.query.filter(cond)
    if apenas_ativas:
        base = base.filter(HoraLoja.ativa.is_(True))  # noqa: E712 — col bool
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        base = base.filter(HoraLoja.id.in_(lojas_permitidas_ids))

    base = base.order_by(HoraLoja.nome).limit(limit)
    return [
        {
            'id': l.id,
            'nome': l.nome,
            'apelido': l.apelido,
            'rotulo_display': l.rotulo_display,
            'cidade': l.cidade,
            'uf': l.uf,
            'label': l.rotulo_display + (f' ({l.cidade}/{l.uf})' if l.cidade and l.uf else ''),
        }
        for l in base.all()
    ]
