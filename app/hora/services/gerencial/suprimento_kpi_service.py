"""KPIs de Suprimento & Recebimento (gerência).

Lead time de recebimento, taxa de divergência por tipo, custo médio de entrada
e desvio real vs esperado. Agregações SQL; escopo por loja via Filtros.lojas.
"""
from __future__ import annotations

from sqlalchemy import func

from app import db
from app.hora.models import (
    HoraModelo, HoraMoto, HoraNfEntrada, HoraNfEntradaItem, HoraPedidoItem,
    HoraRecebimento, HoraRecebimentoConferencia,
)
from app.hora.services.gerencial.filtros import Filtros
from app.hora.services.gerencial.kpi_service import _D


def _escopo_col(query, coluna, filtros: Filtros):
    lojas = filtros.lojas
    if lojas is not None:
        return query.filter(coluna.in_(lojas))
    if not filtros.inclui_bucket_sem_loja:
        return query.filter(coluna.isnot(None))
    return query


def lead_time_recebimento(filtros: Filtros) -> dict:
    """Dias médios entre emissão da NF e o recebimento físico (por data_recebimento)."""
    q = (
        db.session.query(func.avg(HoraRecebimento.data_recebimento - HoraNfEntrada.data_emissao))
        .select_from(HoraRecebimento)
        .join(HoraNfEntrada, HoraRecebimento.nf_id == HoraNfEntrada.id)
        .filter(
            HoraRecebimento.data_recebimento >= filtros.data_ini,
            HoraRecebimento.data_recebimento <= filtros.data_fim,
        )
    )
    q = _escopo_col(q, HoraRecebimento.loja_id, filtros)
    dias = q.scalar()
    return {'dias_medios_nf_recebimento': float(dias) if dias is not None else None}


def taxa_divergencia(filtros: Filtros) -> list[dict]:
    """% de chassis com divergência por tipo (conferências não substituídas)."""
    base = (
        db.session.query(HoraRecebimentoConferencia.tipo_divergencia, func.count())
        .select_from(HoraRecebimentoConferencia)
        .join(HoraRecebimento, HoraRecebimentoConferencia.recebimento_id == HoraRecebimento.id)
        .filter(
            HoraRecebimentoConferencia.tipo_divergencia.isnot(None),
            HoraRecebimentoConferencia.substituida.is_(False),
            HoraRecebimento.data_recebimento >= filtros.data_ini,
            HoraRecebimento.data_recebimento <= filtros.data_fim,
        )
    )
    base = _escopo_col(base, HoraRecebimento.loja_id, filtros)
    rows = base.group_by(HoraRecebimentoConferencia.tipo_divergencia).all()
    total = sum(q for _, q in rows)
    return [
        {'tipo': tipo, 'qtd': int(qtd), 'pct': round(qtd / total * 100, 1) if total else 0}
        for tipo, qtd in rows
    ]


def custo_medio_entrada(filtros: Filtros) -> list[dict]:
    """Custo unitário médio de compra por modelo (NF não desconsiderada)."""
    q = (
        db.session.query(
            HoraModelo.nome_modelo,
            func.avg(HoraNfEntradaItem.preco_real),
            func.count(),
        )
        .select_from(HoraNfEntradaItem)
        .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
        .join(HoraMoto, HoraMoto.numero_chassi == HoraNfEntradaItem.numero_chassi)
        .join(HoraModelo, HoraModelo.id == HoraMoto.modelo_id)
        .filter(
            HoraNfEntradaItem.desconsiderado.is_(False),
            HoraNfEntrada.data_emissao >= filtros.data_ini,
            HoraNfEntrada.data_emissao <= filtros.data_fim,
        )
    )
    q = _escopo_col(q, HoraNfEntrada.loja_destino_id, filtros)
    rows = q.group_by(HoraModelo.nome_modelo).all()
    out = [{'modelo': m, 'custo_medio': _D(avg), 'qtd': int(qtd)} for m, avg, qtd in rows]
    out.sort(key=lambda r: r['custo_medio'], reverse=True)
    return out


def desvio_custo(filtros: Filtros) -> list[dict]:
    """Desvio médio entre custo real e o esperado no pedido, por modelo.

    O preço esperado é colapsado em 1 valor por chassi (subquery) ANTES do join —
    o mesmo chassi pode aparecer em mais de um HoraPedidoItem (UNIQUE é só por
    (pedido_id, chassi)); juntar direto faria fanout e enviesaria avg/count.
    """
    esperado_sq = (
        db.session.query(
            HoraPedidoItem.numero_chassi.label('chassi'),
            func.min(HoraPedidoItem.preco_compra_esperado).label('esperado'),
        )
        .filter(HoraPedidoItem.numero_chassi.isnot(None))
        .group_by(HoraPedidoItem.numero_chassi)
        .subquery()
    )
    q = (
        db.session.query(
            HoraModelo.nome_modelo,
            func.avg(HoraNfEntradaItem.preco_real - esperado_sq.c.esperado),
            func.count(),
        )
        .select_from(HoraNfEntradaItem)
        .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
        .join(esperado_sq, esperado_sq.c.chassi == HoraNfEntradaItem.numero_chassi)
        .join(HoraMoto, HoraMoto.numero_chassi == HoraNfEntradaItem.numero_chassi)
        .join(HoraModelo, HoraModelo.id == HoraMoto.modelo_id)
        .filter(
            HoraNfEntradaItem.desconsiderado.is_(False),
            HoraNfEntrada.data_emissao >= filtros.data_ini,
            HoraNfEntrada.data_emissao <= filtros.data_fim,
        )
    )
    q = _escopo_col(q, HoraNfEntrada.loja_destino_id, filtros)
    rows = q.group_by(HoraModelo.nome_modelo).all()
    return [{'modelo': m, 'desvio_medio': _D(avg), 'qtd': int(qtd)} for m, avg, qtd in rows]


def kpis_suprimento(filtros: Filtros) -> dict:
    return {
        'lead_time': lead_time_recebimento(filtros),
        'divergencias': taxa_divergencia(filtros),
        'custo_medio': custo_medio_entrada(filtros),
        'desvio_custo': desvio_custo(filtros),
    }
