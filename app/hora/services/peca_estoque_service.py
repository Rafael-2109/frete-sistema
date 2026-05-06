"""Estoque de pecas: saldo derivado por SUM em hora_peca_movimento.

Mesmo padrao do estoque de motos (que deriva de eventos). Sem tabela de
saldo materializado.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func

from app import db
from app.hora.models import (
    HoraPeca,
    HoraPecaMovimento,
    HoraLoja,
    PECA_MOV_TIPO_AJUSTE_NEG,
    PECA_MOV_TIPO_AJUSTE_POS,
    PECA_MOV_TIPO_TRANSF_IN,
    PECA_MOV_TIPO_TRANSF_OUT,
    PECA_MOV_TIPOS_VALIDOS,
)


def saldo(peca_id: int, loja_id: int) -> Decimal:
    """Saldo atual de uma combinacao (peca, loja)."""
    r = db.session.query(
        func.coalesce(func.sum(HoraPecaMovimento.qtd), 0)
    ).filter(
        HoraPecaMovimento.peca_id == peca_id,
        HoraPecaMovimento.loja_id == loja_id,
    ).scalar()
    return Decimal(str(r or 0))


def saldos_por_loja(peca_id: int) -> dict[int, Decimal]:
    """Saldo por loja para uma peca (apenas saldo > 0)."""
    rows = db.session.query(
        HoraPecaMovimento.loja_id,
        func.sum(HoraPecaMovimento.qtd).label('total'),
    ).filter(
        HoraPecaMovimento.peca_id == peca_id,
    ).group_by(HoraPecaMovimento.loja_id).all()
    return {loja_id: Decimal(str(t)) for loja_id, t in rows if t}


def registrar_movimento(
    peca_id: int,
    loja_id: int,
    tipo: str,
    qtd: Decimal,
    ref_tabela: Optional[str] = None,
    ref_id: Optional[int] = None,
    motivo: Optional[str] = None,
    operador: Optional[str] = None,
) -> HoraPecaMovimento:
    """Registra movimento. NAO faz commit (chamador controla transacao se quiser).

    Excecao: chamadas isoladas (ajuste_manual, transferencia) commitam aqui.
    """
    if tipo not in PECA_MOV_TIPOS_VALIDOS:
        raise ValueError(f'tipo invalido: {tipo!r}')
    if not HoraPeca.query.get(peca_id):
        raise ValueError(f'peca {peca_id} nao existe')
    if not HoraLoja.query.get(loja_id):
        raise ValueError(f'loja {loja_id} nao existe')

    qtd_dec = Decimal(str(qtd))
    if qtd_dec == 0:
        raise ValueError('qtd nao pode ser zero')

    mov = HoraPecaMovimento(
        peca_id=peca_id, loja_id=loja_id, tipo=tipo, qtd=qtd_dec,
        ref_tabela=ref_tabela, ref_id=ref_id,
        motivo=motivo, operador=operador,
    )
    db.session.add(mov)
    db.session.flush()
    return mov


def ajuste_manual(
    peca_id: int,
    loja_id: int,
    qtd_signed: Decimal,
    motivo: str,
    operador: str,
) -> HoraPecaMovimento:
    """Ajuste positivo (qtd > 0) ou negativo (qtd < 0). Motivo obrigatorio."""
    if not (motivo or '').strip():
        raise ValueError('motivo do ajuste e obrigatorio')
    qtd_dec = Decimal(str(qtd_signed))
    if qtd_dec == 0:
        raise ValueError('qtd_signed nao pode ser zero')
    tipo = PECA_MOV_TIPO_AJUSTE_POS if qtd_dec > 0 else PECA_MOV_TIPO_AJUSTE_NEG

    if qtd_dec < 0:
        atual = saldo(peca_id, loja_id)
        if atual + qtd_dec < 0:
            raise ValueError(
                f'saldo insuficiente para ajuste negativo: '
                f'saldo={atual}, qtd_negativa={qtd_dec}'
            )

    mov = registrar_movimento(
        peca_id=peca_id, loja_id=loja_id, tipo=tipo, qtd=qtd_dec,
        motivo=motivo, operador=operador,
    )
    db.session.commit()
    return mov


def transferencia(
    peca_id: int,
    loja_origem_id: int,
    loja_destino_id: int,
    qtd: Decimal,
    motivo: str,
    operador: str,
) -> tuple[HoraPecaMovimento, HoraPecaMovimento]:
    """Transferencia atomica: emite OUT na origem e IN no destino."""
    if loja_origem_id == loja_destino_id:
        raise ValueError('loja origem e destino devem ser diferentes')
    qtd_dec = Decimal(str(qtd))
    if qtd_dec <= 0:
        raise ValueError('qtd deve ser positiva')
    atual = saldo(peca_id, loja_origem_id)
    if atual < qtd_dec:
        raise ValueError(
            f'saldo insuficiente: origem tem {atual}, transferencia exige {qtd_dec}'
        )
    if not (motivo or '').strip():
        raise ValueError('motivo e obrigatorio')

    mov_out = registrar_movimento(
        peca_id=peca_id, loja_id=loja_origem_id,
        tipo=PECA_MOV_TIPO_TRANSF_OUT, qtd=-qtd_dec,
        motivo=motivo, operador=operador,
    )
    mov_in = registrar_movimento(
        peca_id=peca_id, loja_id=loja_destino_id,
        tipo=PECA_MOV_TIPO_TRANSF_IN, qtd=qtd_dec,
        ref_tabela='hora_peca_movimento', ref_id=mov_out.id,
        motivo=motivo, operador=operador,
    )
    db.session.commit()
    return mov_out, mov_in


def listar_estoque(
    loja_id: Optional[int] = None,
    peca_id: Optional[int] = None,
    busca: Optional[str] = None,
    somente_positivo: bool = True,
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> list[dict]:
    """Lista saldo agregado por (peca, loja) com filtros.

    Retorna list[dict] com keys: peca_id, codigo_interno, descricao,
    foto_s3_key, unidade, loja_id, loja_nome, saldo.
    """
    q = (
        db.session.query(
            HoraPeca.id.label('peca_id'),
            HoraPeca.codigo_interno,
            HoraPeca.descricao,
            HoraPeca.foto_s3_key,
            HoraPeca.unidade,
            HoraLoja.id.label('loja_id'),
            HoraLoja.apelido,
            HoraLoja.nome,
            func.coalesce(func.sum(HoraPecaMovimento.qtd), 0).label('saldo'),
        )
        .select_from(HoraPecaMovimento)
        .join(HoraPeca, HoraPeca.id == HoraPecaMovimento.peca_id)
        .join(HoraLoja, HoraLoja.id == HoraPecaMovimento.loja_id)
    )
    if loja_id:
        q = q.filter(HoraPecaMovimento.loja_id == loja_id)
    if peca_id:
        q = q.filter(HoraPecaMovimento.peca_id == peca_id)
    if busca:
        b = f'%{busca.strip()}%'
        q = q.filter(db.or_(
            HoraPeca.codigo_interno.ilike(b),
            HoraPeca.descricao.ilike(b),
        ))
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraPecaMovimento.loja_id.in_(lojas_permitidas_ids))

    q = q.group_by(
        HoraPeca.id, HoraPeca.codigo_interno, HoraPeca.descricao,
        HoraPeca.foto_s3_key, HoraPeca.unidade,
        HoraLoja.id, HoraLoja.apelido, HoraLoja.nome,
    )
    if somente_positivo:
        q = q.having(func.coalesce(func.sum(HoraPecaMovimento.qtd), 0) > 0)
    q = q.order_by(HoraPeca.codigo_interno, HoraLoja.apelido)

    return [
        {
            'peca_id': r.peca_id,
            'codigo_interno': r.codigo_interno,
            'descricao': r.descricao,
            'foto_s3_key': r.foto_s3_key,
            'unidade': r.unidade,
            'loja_id': r.loja_id,
            'loja_nome': r.apelido or r.nome,
            'saldo': Decimal(str(r.saldo)),
        }
        for r in q.all()
    ]


def historico(
    peca_id: int,
    loja_id: Optional[int] = None,
    limit: int = 100,
) -> list[HoraPecaMovimento]:
    q = HoraPecaMovimento.query.filter(HoraPecaMovimento.peca_id == peca_id)
    if loja_id:
        q = q.filter(HoraPecaMovimento.loja_id == loja_id)
    return q.order_by(HoraPecaMovimento.criado_em.desc()).limit(limit).all()
