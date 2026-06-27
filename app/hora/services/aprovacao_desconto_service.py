"""Aprovacao gerencial do pedido — roadmap #28 (Fatia 2) + #5b.

Cobre 3 gatilhos: desconto acima do teto do modelo (hora_modelo.desconto_maximo),
frete (valor_frete > 0) e brinde. Havendo qualquer gatilho, a venda NAO pode ser
confirmada ate aprovacao por quem tem permissao `aprovacoes/aprovar` (separada de
`comissao` em 2026-06-26). Fila + log (append-only de fato).
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from app import db
from app.hora.models import (
    HoraAprovacaoDesconto, HoraVenda,
    APROVACAO_STATUS_PENDENTE, APROVACAO_STATUS_APROVADO, APROVACAO_STATUS_REJEITADO,
    APROVACAO_TIPO_DESCONTO, APROVACAO_TIPO_FRETE, APROVACAO_TIPO_BRINDE,
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


def gatilhos_aprovacao(venda: HoraVenda) -> dict:
    """Mapa {tipo: detalhe} dos gatilhos que EXIGEM aprovacao nesta venda (#5b).

    Vazio = nada a aprovar. Regras (decisao 2026-06-26):
      - DESCONTO: item-moto com desconto acima do teto do modelo (regra atual).
      - FRETE:    qualquer valor_frete > 0.
      - BRINDE:   qualquer brinde no pedido.
    """
    gatilhos: dict = {}

    estourados = descontos_acima_teto(venda)
    if estourados:
        gatilhos[APROVACAO_TIPO_DESCONTO] = '; '.join(
            f"{e['chassi']} ({e['modelo']}): desconto {e['desconto']} > teto {e['teto']}"
            for e in estourados
        )

    frete = Decimal(str(venda.valor_frete or 0))
    if frete > ZERO:
        tipo_lbl = (venda.tipo_frete_calc or '').strip() or '—'
        gatilhos[APROVACAO_TIPO_FRETE] = f'Frete R$ {frete} ({tipo_lbl})'

    brindes = list(venda.brindes or [])
    if brindes:
        total = sum((Decimal(str(b.custo_total or 0)) for b in brindes), ZERO)
        descr = ', '.join(
            f'{(b.peca.codigo_interno if b.peca else b.peca_id)} x{b.qtd}'
            for b in brindes
        )
        gatilhos[APROVACAO_TIPO_BRINDE] = f'Brinde(s) custo R$ {total}: {descr}'

    return gatilhos


def tem_aprovacao_vigente(venda: HoraVenda, tipo: Optional[str] = None) -> bool:
    """True se existe aprovacao APROVADO para a venda. Com `tipo`, restringe a
    esse gatilho (sem `tipo`, considera qualquer um — retrocompat)."""
    q = HoraAprovacaoDesconto.query.filter_by(
        venda_id=venda.id, status=APROVACAO_STATUS_APROVADO,
    )
    if tipo is not None:
        q = q.filter_by(tipo=tipo)
    return q.first() is not None


def _pendente(venda: HoraVenda, tipo: str) -> Optional[HoraAprovacaoDesconto]:
    return HoraAprovacaoDesconto.query.filter_by(
        venda_id=venda.id, tipo=tipo, status=APROVACAO_STATUS_PENDENTE,
    ).first()


def garantir_aprovacao_para_confirmar(
    venda: HoraVenda, usuario: Optional[str] = None,
) -> Optional[str]:
    """Guard de confirmar_venda (#5b — desconto + frete + brinde).

    Para CADA gatilho ativo (desconto acima do teto, frete > 0, brinde) sem
    aprovacao vigente DAQUELE tipo, cria/garante uma solicitacao PENDENTE (flush)
    daquele tipo. Retorna o resumo dos tipos ainda pendentes (o caller bloqueia a
    confirmacao) ou None quando tudo ja esta liberado (sem gatilho ou ja aprovado).
    """
    gatilhos = gatilhos_aprovacao(venda)
    if not gatilhos:
        return None
    pendentes: list = []
    for tipo, detalhe in gatilhos.items():
        if tem_aprovacao_vigente(venda, tipo):
            continue
        if _pendente(venda, tipo) is None:
            db.session.add(HoraAprovacaoDesconto(
                venda_id=venda.id, tipo=tipo,
                status=APROVACAO_STATUS_PENDENTE, detalhe=detalhe,
                solicitado_em=agora_utc_naive(),
                solicitado_por=(usuario or '').strip()[:100] or None,
            ))
            db.session.flush()
        pendentes.append(f'{tipo}: {detalhe}')
    return ' | '.join(pendentes) if pendentes else None


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
