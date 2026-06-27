"""KPIs de Estoque & Giro (gerência).

Estado atual da moto = último evento (MAX(id)) via window function
ROW_NUMBER() OVER (PARTITION BY chassi ORDER BY id DESC) — anti-N+1, consistente
com estoque_service. Escopo por loja via Filtros.lojas.
"""
from __future__ import annotations

from sqlalchemy import func

from app import db
from app.hora.models import (
    HoraLoja, HoraModelo, HoraMoto, HoraMotoEvento, HoraVenda, HoraVendaItem,
)
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE, EVENTOS_EM_TRANSITO
from app.hora.services.gerencial.filtros import Filtros
from app.hora.services.gerencial.kpi_service import _cond_venda
from app.utils.timezone import agora_brasil_naive

FAIXAS_AGING = ('0-30', '31-60', '61-90', '90+')


def _estado_atual_sq():
    """Subquery do estado ATUAL de cada chassi (último evento por MAX(id))."""
    rn = func.row_number().over(
        partition_by=HoraMotoEvento.numero_chassi,
        order_by=HoraMotoEvento.id.desc(),
    ).label('rn')
    inner = (
        db.session.query(
            HoraMotoEvento.numero_chassi.label('chassi'),
            HoraMotoEvento.tipo.label('tipo'),
            HoraMotoEvento.loja_id.label('loja_id'),
            HoraMotoEvento.timestamp.label('ts'),
            rn,
        )
        .subquery()
    )
    return (
        db.session.query(inner.c.chassi, inner.c.tipo, inner.c.loja_id, inner.c.ts)
        .filter(inner.c.rn == 1)
        .subquery()
    )


def _escopo_estado(query, ult, filtros: Filtros):
    lojas = filtros.lojas
    if lojas is not None:
        return query.filter(ult.c.loja_id.in_(lojas))
    if not filtros.inclui_bucket_sem_loja:
        return query.filter(ult.c.loja_id.isnot(None))
    return query


def estoque_por_loja_modelo(filtros: Filtros) -> list[dict]:
    """Snapshot de motos disponíveis por loja > modelo > cor (+ avariadas)."""
    ult = _estado_atual_sq()
    q = (
        db.session.query(
            ult.c.loja_id,
            HoraModelo.nome_modelo,
            HoraMoto.cor,
            func.count().label('qtd'),
        )
        .select_from(ult)
        .join(HoraMoto, HoraMoto.numero_chassi == ult.c.chassi)
        .join(HoraModelo, HoraModelo.id == HoraMoto.modelo_id)
        .filter(ult.c.tipo.in_(EVENTOS_EM_ESTOQUE))
    )
    q = _escopo_estado(q, ult, filtros).group_by(
        ult.c.loja_id, HoraModelo.nome_modelo, HoraMoto.cor
    )
    nomes = dict(db.session.query(HoraLoja.id, HoraLoja.apelido).all())
    rows = [
        {
            'loja_id': loja_id,
            'loja_nome': nomes.get(loja_id, '(sem loja)') if loja_id else '(sem loja)',
            'modelo': modelo,
            'cor': cor,
            'qtd': int(qtd or 0),
        }
        for loja_id, modelo, cor, qtd in q.all()
    ]
    rows.sort(key=lambda r: (r['loja_nome'], r['modelo'], r['cor'] or ''))
    return rows


def aging_estoque(filtros: Filtros) -> dict:
    """Distribuição do estoque parado por faixa de dias (hoje − último evento)."""
    ult = _estado_atual_sq()
    q = db.session.query(ult.c.ts).filter(ult.c.tipo.in_(EVENTOS_EM_ESTOQUE))
    q = _escopo_estado(q, ult, filtros)
    hoje = agora_brasil_naive().date()
    faixas = {f: 0 for f in FAIXAS_AGING}
    for (ts,) in q.all():
        dias = (hoje - ts.date()).days
        if dias <= 30:
            faixas['0-30'] += 1
        elif dias <= 60:
            faixas['31-60'] += 1
        elif dias <= 90:
            faixas['61-90'] += 1
        else:
            faixas['90+'] += 1
    return {'faixas': faixas, 'total': sum(faixas.values())}


def giro_dias(filtros: Filtros) -> list[dict]:
    """Dias médios entre RECEBIDA e a venda (FATURADO no período), por modelo."""
    receb = (
        db.session.query(
            HoraMotoEvento.numero_chassi.label('chassi'),
            func.min(HoraMotoEvento.timestamp).label('min_ts'),
        )
        .filter(HoraMotoEvento.tipo == 'RECEBIDA')
        .group_by(HoraMotoEvento.numero_chassi)
        .subquery()
    )
    rows = (
        db.session.query(HoraModelo.nome_modelo, HoraVenda.data_venda, receb.c.min_ts)
        .select_from(HoraVendaItem)
        .join(HoraVenda, HoraVendaItem.venda_id == HoraVenda.id)
        .join(receb, receb.c.chassi == HoraVendaItem.numero_chassi)
        .join(HoraMoto, HoraMoto.numero_chassi == HoraVendaItem.numero_chassi)
        .join(HoraModelo, HoraModelo.id == HoraMoto.modelo_id)
        .filter(*_cond_venda(filtros))
        .all()
    )
    por_modelo: dict = {}
    for modelo, data_venda, min_ts in rows:
        dias = (data_venda - min_ts.date()).days
        por_modelo.setdefault(modelo, []).append(dias)
    out = [
        {'modelo': m, 'dias_medios': round(sum(v) / len(v), 1), 'qtd': len(v)}
        for m, v in por_modelo.items()
    ]
    out.sort(key=lambda r: r['dias_medios'], reverse=True)
    return out


def reservadas_em_transito(filtros: Filtros) -> dict:
    """Capital comprometido fora do estoque disponível (reservas + transferências)."""
    ult = _estado_atual_sq()
    qr = db.session.query(func.count()).select_from(ult).filter(ult.c.tipo == 'RESERVADA')
    reservadas = int(_escopo_estado(qr, ult, filtros).scalar() or 0)
    qt = db.session.query(func.count()).select_from(ult).filter(ult.c.tipo.in_(EVENTOS_EM_TRANSITO))
    em_transito = int(_escopo_estado(qt, ult, filtros).scalar() or 0)
    return {'reservadas': reservadas, 'em_transito': em_transito}


def kpis_estoque(filtros: Filtros) -> dict:
    return {
        'estoque': estoque_por_loja_modelo(filtros),
        'aging': aging_estoque(filtros),
        'giro': giro_dias(filtros),
        'reservadas_transito': reservadas_em_transito(filtros),
    }
