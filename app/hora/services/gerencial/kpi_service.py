"""KPIs comerciais/executivos da seção Gerencial HORA.

Todas as métricas são agregações SQL únicas (anti-N+1). Receita só FATURADO.
Custo real por chassi (`hora_nf_entrada_item.preco_real`, `desconsiderado=FALSE`).
Escopo por loja aplicado no WHERE via `Filtros.lojas`.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func

from app import db
from app.hora.models import (
    HoraLoja, HoraNfEntradaItem, HoraVenda, HoraVendaBrinde, HoraVendaItem,
)
from app.hora.models.venda import VENDA_STATUS_FATURADO
from app.hora.services.gerencial.filtros import Filtros

ZERO = Decimal('0')


def _D(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v or 0))


def _cond_venda(filtros: Filtros):
    """Condições WHERE comuns: FATURADO + período + escopo de loja."""
    conds = [
        HoraVenda.status == VENDA_STATUS_FATURADO,
        HoraVenda.data_venda >= filtros.data_ini,
        HoraVenda.data_venda <= filtros.data_fim,
    ]
    lojas = filtros.lojas
    if lojas is not None:
        # lista vazia (loja fora do escopo) -> in_([]) bloqueia tudo (correto).
        conds.append(HoraVenda.loja_id.in_(lojas))
    elif not filtros.inclui_bucket_sem_loja:
        conds.append(HoraVenda.loja_id.isnot(None))
    return conds


def _custo_por_chassi_sq():
    """Custo real por chassi = preço da NF de entrada MAIS RECENTE (maior id)
    não desconsiderada. Determinístico quando o mesmo chassi aparece em mais de
    uma NF (re-entrada / devolução + recompra) — evita escolher um custo arbitrário.
    """
    rn = func.row_number().over(
        partition_by=HoraNfEntradaItem.numero_chassi,
        order_by=HoraNfEntradaItem.id.desc(),
    ).label('rn')
    inner = (
        db.session.query(
            HoraNfEntradaItem.numero_chassi.label('chassi'),
            HoraNfEntradaItem.preco_real.label('preco_real'),
            rn,
        )
        .filter(HoraNfEntradaItem.desconsiderado.is_(False))
        .subquery()
    )
    return (
        db.session.query(inner.c.chassi, inner.c.preco_real)
        .filter(inner.c.rn == 1)
        .subquery()
    )


def receita_realizada(filtros: Filtros) -> dict:
    valor, qtd = (
        db.session.query(
            func.coalesce(func.sum(HoraVenda.valor_total), 0),
            func.count(HoraVenda.id),
        )
        .filter(*_cond_venda(filtros))
        .one()
    )
    return {'valor': _D(valor), 'qtd_vendas': int(qtd or 0)}


def ticket_medio(filtros: Filtros) -> Decimal:
    r = receita_realizada(filtros)
    return (r['valor'] / r['qtd_vendas']) if r['qtd_vendas'] else ZERO


def motos_vendidas(filtros: Filtros) -> int:
    q = (
        db.session.query(func.count(HoraVendaItem.id))
        .join(HoraVenda, HoraVendaItem.venda_id == HoraVenda.id)
        .filter(*_cond_venda(filtros))
    )
    return int(q.scalar() or 0)


def desconto_total(filtros: Filtros) -> Decimal:
    q = (
        db.session.query(func.coalesce(func.sum(HoraVendaItem.desconto_aplicado), 0))
        .join(HoraVenda, HoraVendaItem.venda_id == HoraVenda.id)
        .filter(*_cond_venda(filtros))
    )
    return _D(q.scalar())


def margem_bruta(filtros: Filtros) -> dict:
    """Margem bruta de CMV-moto (sem frete de compra nem custo de peça).

    margem_rs = Σ(preco_final − preco_real) [itens com custo] − Σ brindes.
    Cobertura por ITEM-moto: itens_com_custo / total_itens.
    """
    custo_sq = _custo_por_chassi_sq()
    total_itens, itens_com_custo, custo_total, receita_com_custo = (
        db.session.query(
            func.count(HoraVendaItem.id),
            func.count(custo_sq.c.preco_real),                       # ignora NULL
            func.coalesce(func.sum(custo_sq.c.preco_real), 0),
            func.coalesce(
                func.sum(
                    case((custo_sq.c.preco_real.isnot(None), HoraVendaItem.preco_final),
                         else_=0)
                ), 0,
            ),
        )
        .select_from(HoraVendaItem)
        .join(HoraVenda, HoraVendaItem.venda_id == HoraVenda.id)
        .outerjoin(custo_sq, custo_sq.c.chassi == HoraVendaItem.numero_chassi)
        .filter(*_cond_venda(filtros))
        .one()
    )
    brinde_total = (
        db.session.query(func.coalesce(func.sum(HoraVendaBrinde.custo_total), 0))
        .join(HoraVenda, HoraVendaBrinde.venda_id == HoraVenda.id)
        .filter(*_cond_venda(filtros))
        .scalar()
    )
    total_itens = int(total_itens or 0)
    itens_com_custo = int(itens_com_custo or 0)
    custo_total = _D(custo_total)
    receita_com_custo = _D(receita_com_custo)
    brinde_total = _D(brinde_total)
    margem_rs = receita_com_custo - custo_total - brinde_total
    margem_pct = (margem_rs / custo_total * 100) if custo_total else ZERO
    cobertura_pct = (Decimal(itens_com_custo) / Decimal(total_itens) * 100) if total_itens else ZERO
    return {
        'margem_rs': margem_rs,
        'margem_pct': margem_pct,
        'cobertura_pct': cobertura_pct,
        'itens_com_custo': itens_com_custo,
        'total_itens': total_itens,
        'custo_total': custo_total,
        'receita_com_custo': receita_com_custo,
        'brinde_total': brinde_total,
    }


def ranking_lojas(filtros: Filtros) -> list[dict]:
    """Receita + unidades por loja (bucket loja_id NULL só se irrestrito)."""
    conds = _cond_venda(filtros)
    receita = dict(
        db.session.query(HoraVenda.loja_id, func.sum(HoraVenda.valor_total))
        .filter(*conds)
        .group_by(HoraVenda.loja_id)
        .all()
    )
    unidades = dict(
        db.session.query(HoraVenda.loja_id, func.count(HoraVendaItem.id))
        .join(HoraVendaItem, HoraVendaItem.venda_id == HoraVenda.id)
        .filter(*conds)
        .group_by(HoraVenda.loja_id)
        .all()
    )
    nomes = dict(db.session.query(HoraLoja.id, HoraLoja.apelido).all())
    rows = [
        {
            'loja_id': loja_id,
            'loja_nome': nomes.get(loja_id, '(sem loja)') if loja_id else '(sem loja)',
            'receita': _D(valor),
            'unidades': int(unidades.get(loja_id, 0)),
        }
        for loja_id, valor in receita.items()
    ]
    rows.sort(key=lambda r: r['receita'], reverse=True)
    return rows


def receita_por_periodo(filtros: Filtros) -> list[dict]:
    """Série temporal de receita agrupada por dia/semana/mês (data_venda)."""
    trunc = {'dia': 'day', 'semana': 'week', 'mes': 'month'}.get(filtros.granularidade, 'day')
    periodo = func.date_trunc(trunc, HoraVenda.data_venda)
    rows = (
        db.session.query(periodo.label('p'), func.sum(HoraVenda.valor_total))
        .filter(*_cond_venda(filtros))
        .group_by('p')
        .order_by('p')
        .all()
    )
    out = []
    for p, valor in rows:
        chave = p.date().isoformat() if hasattr(p, 'date') else str(p)
        out.append({'periodo': chave, 'valor': _D(valor)})
    return out


def kpis_executivo(filtros: Filtros) -> dict:
    """Agrega todos os KPIs da Visão Executiva para a rota."""
    receita = receita_realizada(filtros)
    margem = margem_bruta(filtros)
    return {
        'receita': receita,
        'margem': margem,
        'ticket_medio': ticket_medio(filtros),
        'motos_vendidas': motos_vendidas(filtros),
        'desconto_total': desconto_total(filtros),
        'ranking_lojas': ranking_lojas(filtros),
        'serie_receita': receita_por_periodo(filtros),
    }
