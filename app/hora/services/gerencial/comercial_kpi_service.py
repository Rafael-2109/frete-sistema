"""KPIs do dashboard Comercial & Vendedores (gerência).

Conversão de funil, desempenho por vendedor, comissão (reusa o cálculo on-the-fly
de comissao_service respeitando escopo de loja), mix de pagamento, aprovações
pendentes, peças e brindes. Agregações SQL únicas; escopo via Filtros.lojas.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func

from app import db
from app.hora.models import (
    HoraAprovacaoDesconto, HoraVenda, HoraVendaBrinde, HoraVendaItem,
    HoraVendaItemPeca, HoraVendaPagamento,
)
from app.hora.models.venda import VENDA_STATUS_FATURADO
from app.hora.services.gerencial.filtros import Filtros
from app.hora.services.gerencial.kpi_service import _D, _cond_venda

ZERO = Decimal('0')

_STATUS_FUNIL = ('COTACAO', 'CONFIRMADO', 'FATURADO')


def _aplica_escopo_loja(query, filtros: Filtros):
    lojas = filtros.lojas
    if lojas is not None:
        return query.filter(HoraVenda.loja_id.in_(lojas))
    if not filtros.inclui_bucket_sem_loja:
        return query.filter(HoraVenda.loja_id.isnot(None))
    return query


def conversao_funil(filtros: Filtros) -> dict:
    """Funil COTAÇÃO→CONFIRMADO→FATURADO (só vendas MANUAL, por data_venda)."""
    base = (
        db.session.query(HoraVenda.status, func.count(HoraVenda.id))
        .filter(
            HoraVenda.origem_criacao == 'MANUAL',
            HoraVenda.status.in_(_STATUS_FUNIL),
            HoraVenda.data_venda >= filtros.data_ini,
            HoraVenda.data_venda <= filtros.data_fim,
        )
        .group_by(HoraVenda.status)
    )
    base = _aplica_escopo_loja(base, filtros)
    contagem = {s: 0 for s in _STATUS_FUNIL}
    for status, qtd in base.all():
        contagem[status] = int(qtd or 0)
    total = sum(contagem.values())
    faturado = contagem['FATURADO']
    taxa = (Decimal(faturado) / Decimal(total) * 100) if total else ZERO
    return {
        'cotacao': contagem['COTACAO'],
        'confirmado': contagem['CONFIRMADO'],
        'faturado': faturado,
        'taxa': taxa,
    }


def vendas_por_vendedor(filtros: Filtros) -> list[dict]:
    """Volume e receita por vendedor (FATURADO)."""
    receita = (
        db.session.query(HoraVenda.vendedor, func.sum(HoraVenda.valor_total))
        .filter(*_cond_venda(filtros))
        .group_by(HoraVenda.vendedor)
        .all()
    )
    unidades = dict(
        db.session.query(HoraVenda.vendedor, func.count(HoraVendaItem.id))
        .join(HoraVendaItem, HoraVendaItem.venda_id == HoraVenda.id)
        .filter(*_cond_venda(filtros))
        .group_by(HoraVenda.vendedor)
        .all()
    )
    rows = [
        {
            'vendedor': vend or '(sem vendedor)',
            'receita': _D(valor),
            'unidades': int(unidades.get(vend, 0)),
        }
        for vend, valor in receita
    ]
    rows.sort(key=lambda r: r['receita'], reverse=True)
    return rows


def comissao_por_vendedor(filtros: Filtros) -> list[dict]:
    """Comissão por vendedor (reusa calcular_comissao_venda; por faturado_em).

    Comissão é calculada on-the-fly sobre a config VIGENTE (não persistida) —
    valores refletem a configuração atual, não a do momento da venda. Iterar as
    vendas é inerente ao cálculo por-venda; o universo (FATURADO no período +
    escopo) é limitado.
    """
    from app.hora.services.comissao_service import calcular_comissao_venda
    q = HoraVenda.query.filter(
        HoraVenda.status == VENDA_STATUS_FATURADO,
        HoraVenda.faturado_em >= datetime.combine(filtros.data_ini, time.min),
        HoraVenda.faturado_em < datetime.combine(filtros.data_fim + timedelta(days=1), time.min),
    )
    q = _aplica_escopo_loja(q, filtros)
    por_vendedor: dict = {}
    for v in q.all():
        c = calcular_comissao_venda(v)
        vend = v.vendedor or '(sem vendedor)'
        agg = por_vendedor.setdefault(vend, {'vendedor': vend, 'qtd_vendas': 0, 'total': ZERO})
        agg['qtd_vendas'] += 1
        agg['total'] += c['total']
    return sorted(por_vendedor.values(), key=lambda x: x['total'], reverse=True)


def desconto_medio_por(filtros: Filtros, dimensao: str = 'loja') -> list[dict]:
    """Desconto médio (% e R$) por dimensão (loja/vendedor) sobre itens FATURADOS."""
    coluna = {'loja': HoraVenda.loja_id, 'vendedor': HoraVenda.vendedor}.get(dimensao, HoraVenda.loja_id)
    rows = (
        db.session.query(
            coluna,
            func.avg(HoraVendaItem.desconto_percentual),
            func.avg(HoraVendaItem.desconto_aplicado),
        )
        .join(HoraVenda, HoraVendaItem.venda_id == HoraVenda.id)
        .filter(*_cond_venda(filtros))
        .group_by(coluna)
        .all()
    )
    return [
        {'chave': chave, 'desconto_pct_medio': _D(pct), 'desconto_rs_medio': _D(rs)}
        for chave, pct, rs in rows
    ]


def mix_pagamento(filtros: Filtros) -> list[dict]:
    """Receita por forma de pagamento granular (hora_venda_pagamento, FATURADO)."""
    rows = (
        db.session.query(
            HoraVendaPagamento.forma_pagamento_hora,
            func.coalesce(func.sum(HoraVendaPagamento.valor), 0),
        )
        .join(HoraVenda, HoraVendaPagamento.venda_id == HoraVenda.id)
        .filter(*_cond_venda(filtros))
        .group_by(HoraVendaPagamento.forma_pagamento_hora)
        .all()
    )
    out = [{'forma': forma or '(não informado)', 'valor': _D(valor)} for forma, valor in rows]
    out.sort(key=lambda r: r['valor'], reverse=True)
    return out


def aprovacoes_pendentes(filtros: Filtros) -> dict:
    """Aprovações PENDENTES por tipo (estado atual, com escopo de loja via venda)."""
    base = (
        db.session.query(HoraAprovacaoDesconto.tipo, func.count(HoraAprovacaoDesconto.id))
        .join(HoraVenda, HoraAprovacaoDesconto.venda_id == HoraVenda.id)
        .filter(HoraAprovacaoDesconto.status == 'PENDENTE')
        .group_by(HoraAprovacaoDesconto.tipo)
    )
    base = _aplica_escopo_loja(base, filtros)
    contagem = {'DESCONTO': 0, 'FRETE': 0, 'BRINDE': 0}
    for tipo, qtd in base.all():
        contagem[tipo] = int(qtd or 0)
    return contagem


def receita_pecas(filtros: Filtros) -> Decimal:
    """Receita incremental de peças vendidas (FATURADO)."""
    q = (
        db.session.query(func.coalesce(func.sum(HoraVendaItemPeca.preco_final), 0))
        .join(HoraVenda, HoraVendaItemPeca.venda_id == HoraVenda.id)
        .filter(*_cond_venda(filtros))
    )
    return _D(q.scalar())


def custo_brindes(filtros: Filtros) -> Decimal:
    """Custo total de brindes concedidos (erosão de margem, FATURADO)."""
    q = (
        db.session.query(func.coalesce(func.sum(HoraVendaBrinde.custo_total), 0))
        .join(HoraVenda, HoraVendaBrinde.venda_id == HoraVenda.id)
        .filter(*_cond_venda(filtros))
    )
    return _D(q.scalar())


def kpis_comercial(filtros: Filtros) -> dict:
    """Agrega os KPIs do dashboard Comercial para a rota."""
    return {
        'funil': conversao_funil(filtros),
        'vendedores': vendas_por_vendedor(filtros),
        'comissao': comissao_por_vendedor(filtros),
        'mix_pagamento': mix_pagamento(filtros),
        'aprovacoes': aprovacoes_pendentes(filtros),
        'receita_pecas': receita_pecas(filtros),
        'custo_brindes': custo_brindes(filtros),
    }
