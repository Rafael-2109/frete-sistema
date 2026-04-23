"""Estoque HORA: calcula estoque por loja a partir do ultimo evento de cada moto.

Regra (invariante 4): estado atual = ultimo HoraMotoEvento por chassi.
"Em estoque" = chassi cujo ultimo evento esta em `EVENTOS_EM_ESTOQUE` e a loja
do evento e a loja onde a moto esta.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import and_, func

from app import db
from app.hora.models import (
    HoraLoja,
    HoraModelo,
    HoraMoto,
    HoraMotoEvento,
)


# Eventos que significam "moto esta no estoque da loja do evento"
EVENTOS_EM_ESTOQUE = (
    'RECEBIDA', 'CONFERIDA', 'TRANSFERIDA',
    'CANCELADA',  # transferencia cancelada — moto voltou a origem
    'AVARIADA', 'FALTANDO_PECA',
)
# Eventos que tiram a moto do estoque
EVENTOS_FORA_ESTOQUE = ('VENDIDA', 'DEVOLVIDA')
# Eventos "em limbo" — nao estao no estoque de nenhuma loja
EVENTOS_EM_TRANSITO = ('EM_TRANSITO',)


def _subquery_ultimo_evento_id():
    """Subquery: para cada chassi, o id do evento mais recente."""
    return (
        db.session.query(
            HoraMotoEvento.numero_chassi.label('chassi'),
            func.max(HoraMotoEvento.id).label('max_id'),
        )
        .group_by(HoraMotoEvento.numero_chassi)
        .subquery()
    )


def listar_estoque(
    loja_id: Optional[int] = None,
    modelo_id: Optional[int] = None,
    cor: Optional[str] = None,
    incluir_avariadas: bool = True,
    incluir_faltando_peca: bool = True,
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Lista motos em estoque, chassi-a-chassi.

    Retorna dicts com: chassi, modelo_id, modelo_nome, cor, loja_id, loja_nome,
    ultimo_evento, ultimo_evento_em, motor, ano_modelo.
    """
    tipos = list(EVENTOS_EM_ESTOQUE)
    if not incluir_avariadas:
        tipos = [t for t in tipos if t != 'AVARIADA']
    if not incluir_faltando_peca:
        tipos = [t for t in tipos if t != 'FALTANDO_PECA']

    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(HoraMotoEvento, HoraMoto, HoraModelo, HoraLoja)
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraMoto, HoraMotoEvento.numero_chassi == HoraMoto.numero_chassi)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .outerjoin(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
        .filter(HoraMotoEvento.tipo.in_(tipos))
    )

    if loja_id:
        q = q.filter(HoraMotoEvento.loja_id == loja_id)
    if modelo_id:
        q = q.filter(HoraMoto.modelo_id == modelo_id)
    if cor:
        q = q.filter(HoraMoto.cor == cor.strip().upper())
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    q = q.order_by(HoraMotoEvento.timestamp.desc())

    resultado = []
    for ev, moto, modelo, loja in q.all():
        resultado.append({
            'chassi': moto.numero_chassi,
            'modelo_id': modelo.id,
            'modelo_nome': modelo.nome_modelo,
            'cor': moto.cor,
            'motor': moto.numero_motor,
            'ano_modelo': moto.ano_modelo,
            'loja_id': loja.id if loja else None,
            'loja_nome': loja.rotulo_display if loja else None,
            'ultimo_evento': ev.tipo,
            'ultimo_evento_em': ev.timestamp,
            'ultimo_evento_detalhe': ev.detalhe,
        })
    return resultado


def kpis_estoque_por_loja(
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Agrupa estoque por loja (contagem total + avariadas + faltando_peca)."""
    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(
            HoraLoja.id.label('loja_id'),
            HoraLoja.apelido,
            HoraLoja.nome,
            HoraLoja.nome_fantasia,
            HoraMotoEvento.tipo,
            func.count().label('total'),
        )
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
        .filter(HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE))
        .group_by(HoraLoja.id, HoraLoja.apelido, HoraLoja.nome,
                  HoraLoja.nome_fantasia, HoraMotoEvento.tipo)
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraLoja.id.in_(lojas_permitidas_ids))

    acum = {}
    for row in q.all():
        k = row.loja_id
        if k not in acum:
            acum[k] = {
                'loja_id': row.loja_id,
                'loja_nome': row.apelido or row.nome_fantasia or row.nome,
                'total': 0,
                'disponivel': 0,
                'avariada': 0,
                'faltando_peca': 0,
            }
        acum[k]['total'] += row.total
        if row.tipo == 'AVARIADA':
            acum[k]['avariada'] += row.total
        elif row.tipo == 'FALTANDO_PECA':
            acum[k]['faltando_peca'] += row.total
        else:
            acum[k]['disponivel'] += row.total

    return sorted(acum.values(), key=lambda x: x['loja_nome'] or '')


def kpis_estoque_por_modelo(
    loja_id: Optional[int] = None,
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Agrupa estoque por modelo (contagem total)."""
    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(
            HoraModelo.id,
            HoraModelo.nome_modelo,
            HoraMoto.cor,
            func.count().label('total'),
        )
        .join(HoraMoto, HoraMoto.modelo_id == HoraModelo.id)
        .join(
            sub,
            HoraMoto.numero_chassi == sub.c.chassi,
        )
        .join(HoraMotoEvento, HoraMotoEvento.id == sub.c.max_id)
        .filter(HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE))
        .group_by(HoraModelo.id, HoraModelo.nome_modelo, HoraMoto.cor)
        .order_by(HoraModelo.nome_modelo, HoraMoto.cor)
    )
    if loja_id:
        q = q.filter(HoraMotoEvento.loja_id == loja_id)
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    return [
        {
            'modelo_id': r.id,
            'modelo_nome': r.nome_modelo,
            'cor': r.cor,
            'total': r.total,
        }
        for r in q.all()
    ]


def historico_chassi(numero_chassi: str) -> List[dict]:
    """Retorna todos os eventos de um chassi, mais recentes primeiro."""
    chassi = numero_chassi.strip().upper()
    eventos = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .all()
    )
    return [
        {
            'id': e.id,
            'tipo': e.tipo,
            'timestamp': e.timestamp,
            'loja_id': e.loja_id,
            'loja_nome': e.loja.rotulo_display if e.loja else None,
            'operador': e.operador,
            'detalhe': e.detalhe,
            'origem_tabela': e.origem_tabela,
            'origem_id': e.origem_id,
        }
        for e in eventos
    ]


def listar_em_transito(
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Motos com ultimo evento EM_TRANSITO, filtradas por loja_id do evento.

    Interpretacao: o evento EM_TRANSITO e emitido com loja_id=destino
    (para que operador do destino veja 'motos chegando'). Origem ve pelo
    detalhe ou consulta alternativa.
    """
    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(HoraMotoEvento, HoraMoto, HoraModelo, HoraLoja)
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraMoto, HoraMotoEvento.numero_chassi == HoraMoto.numero_chassi)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .outerjoin(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
        .filter(HoraMotoEvento.tipo == 'EM_TRANSITO')
    )

    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    q = q.order_by(HoraMotoEvento.timestamp.desc())

    return [
        {
            'numero_chassi': moto.numero_chassi,
            'modelo_id': modelo.id,
            'modelo_nome': modelo.nome_modelo,
            'cor': moto.cor,
            'loja_destino_id': loja.id if loja else None,
            'loja_destino_nome': loja.rotulo_display if loja else None,
            'emitido_em': ev.timestamp,
            'detalhe': ev.detalhe,
        }
        for ev, moto, modelo, loja in q.all()
    ]
