"""Aprovacao de desconto acima do teto do modelo — roadmap #28 (Fatia 2).

Quando um item-moto tem desconto acima do teto do modelo
(hora_modelo.desconto_maximo), a venda NAO pode ser confirmada ate aprovacao
por quem tem permissao comissao/aprovar. Fila + log (append-only de fato).
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from app import db
from app.hora.models import (
    HoraAprovacaoDesconto, HoraVenda,
    APROVACAO_STATUS_PENDENTE, APROVACAO_STATUS_APROVADO, APROVACAO_STATUS_REJEITADO,
)
from app.utils.timezone import agora_utc_naive

ZERO = Decimal('0')


def descontos_acima_teto(venda: HoraVenda) -> List[dict]:
    """Itens-moto cujo desconto_aplicado excede o teto (desconto_maximo) do modelo.

    Modelos sem teto (NULL) nunca estouram. Retorna lista de dicts
    {chassi, modelo, desconto, teto}.
    """
    estourados = []
    for item in venda.itens:
        moto = getattr(item, 'moto', None)
        modelo = getattr(moto, 'modelo', None) if moto else None
        teto = getattr(modelo, 'desconto_maximo', None) if modelo else None
        if teto is None:
            continue
        desconto = Decimal(str(item.desconto_aplicado or 0))
        if desconto > Decimal(str(teto)):
            estourados.append({
                'chassi': item.numero_chassi,
                'modelo': modelo.nome_modelo,
                'desconto': desconto,
                'teto': Decimal(str(teto)),
            })
    return estourados


def tem_aprovacao_vigente(venda: HoraVenda) -> bool:
    """True se existe aprovacao APROVADO para a venda (libera a confirmacao)."""
    return HoraAprovacaoDesconto.query.filter_by(
        venda_id=venda.id, status=APROVACAO_STATUS_APROVADO,
    ).first() is not None


def _pendente(venda: HoraVenda) -> Optional[HoraAprovacaoDesconto]:
    return HoraAprovacaoDesconto.query.filter_by(
        venda_id=venda.id, status=APROVACAO_STATUS_PENDENTE,
    ).first()


def garantir_aprovacao_para_confirmar(
    venda: HoraVenda, usuario: Optional[str] = None,
) -> Optional[str]:
    """Guard de confirmar_venda.

    Se ha desconto acima do teto e NAO ha aprovacao vigente, cria (flush) uma
    solicitacao PENDENTE e retorna o `detalhe` (o caller deve bloquear a
    confirmacao). Retorna None quando pode confirmar (sem estouro ou ja aprovado).
    """
    estourados = descontos_acima_teto(venda)
    if not estourados:
        return None
    if tem_aprovacao_vigente(venda):
        return None
    ap = _pendente(venda)
    if ap is None:
        detalhe = '; '.join(
            f"{e['chassi']} ({e['modelo']}): desconto {e['desconto']} > teto {e['teto']}"
            for e in estourados
        )
        ap = HoraAprovacaoDesconto(
            venda_id=venda.id, status=APROVACAO_STATUS_PENDENTE, detalhe=detalhe,
            solicitado_em=agora_utc_naive(),
            solicitado_por=(usuario or '').strip()[:100] or None,
        )
        db.session.add(ap)
        db.session.flush()
    return ap.detalhe


def aprovar(aprovacao_id: int, usuario: Optional[str] = None) -> HoraAprovacaoDesconto:
    ap = HoraAprovacaoDesconto.query.get(aprovacao_id)
    if not ap:
        raise ValueError('Aprovacao nao encontrada.')
    ap.status = APROVACAO_STATUS_APROVADO
    ap.decidido_em = agora_utc_naive()
    ap.decidido_por = (usuario or '').strip()[:100] or None
    db.session.commit()
    return ap


def rejeitar(aprovacao_id: int, usuario: Optional[str] = None,
             motivo: Optional[str] = None) -> HoraAprovacaoDesconto:
    ap = HoraAprovacaoDesconto.query.get(aprovacao_id)
    if not ap:
        raise ValueError('Aprovacao nao encontrada.')
    ap.status = APROVACAO_STATUS_REJEITADO
    ap.decidido_em = agora_utc_naive()
    ap.decidido_por = (usuario or '').strip()[:100] or None
    ap.motivo_decisao = (motivo or '').strip()[:500] or None
    db.session.commit()
    return ap


def listar(status: Optional[str] = None) -> List[HoraAprovacaoDesconto]:
    q = HoraAprovacaoDesconto.query
    if status:
        q = q.filter_by(status=status)
    return q.order_by(HoraAprovacaoDesconto.solicitado_em.desc()).all()
