"""Pendencias de montagem (defeitos de peca).

Pendencia aberta: chassi com ultimo evento = PENDENTE.
Pendencia resolvida: cada evento PENDENCIA_RESOLVIDA representa uma resolucao
historica (append-only). Mantemos o registro para auditoria mesmo apos o chassi
voltar para MONTADA.

2026-05-13: filtros adicionados — chassi (ilike), modelo_id, data_inicio,
data_fim, operador_id. Auxiliares para autocomplete (operadores distintos +
modelos distintos com pendencias).
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import List, Dict, Any, Optional, TypedDict
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.auth.models import Usuario
from app.motos_assai.models import (
    AssaiMoto, AssaiMotoEvento, AssaiModelo,
    EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA,
)


class FiltrosPendencias(TypedDict, total=False):
    chassi: Optional[str]            # ilike %chassi%
    modelo_id: Optional[int]
    data_inicio: Optional[date]      # ocorrido_em >= data_inicio (00:00)
    data_fim: Optional[date]         # ocorrido_em <= data_fim (23:59:59)
    operador_id: Optional[int]


def _aplicar_filtros_evento(query, filtros: Optional[FiltrosPendencias]):
    """Aplica filtros que dependem do AssaiMotoEvento na query."""
    if not filtros:
        return query

    chassi = (filtros.get('chassi') or '').strip().upper()
    if chassi:
        query = query.filter(AssaiMotoEvento.chassi.ilike(f'%{chassi}%'))

    operador_id = filtros.get('operador_id')
    if operador_id:
        query = query.filter(AssaiMotoEvento.operador_id == operador_id)

    data_inicio = filtros.get('data_inicio')
    if data_inicio:
        query = query.filter(
            AssaiMotoEvento.ocorrido_em >= datetime.combine(data_inicio, time.min)
        )

    data_fim = filtros.get('data_fim')
    if data_fim:
        query = query.filter(
            AssaiMotoEvento.ocorrido_em <= datetime.combine(data_fim, time.max)
        )

    return query


def _ultimo_evento_subquery():
    return (
        db.session.query(
            AssaiMotoEvento.chassi.label('chassi'),
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )


def listar_abertas(filtros: Optional[FiltrosPendencias] = None) -> List[Dict[str, Any]]:
    """Chassis cujo ultimo evento = PENDENTE.

    Filtros aceitos (opcional):
    - chassi (str): ilike %chassi%
    - modelo_id (int): filtra pelo modelo da moto (filtro pos-load — moto/modelo)
    - data_inicio (date), data_fim (date): faixa de ocorrido_em do evento PENDENTE
    - operador_id (int): operador que registrou a pendencia

    Retorna: [{evento_id, chassi, modelo_id, modelo_codigo, modelo_nome, cor,
               observacao, chassi_doador, operador, ocorrido_em}]
    """
    sub = _ultimo_evento_subquery()

    q = (
        db.session.query(AssaiMotoEvento)
        .options(joinedload(AssaiMotoEvento.operador))
        .join(sub, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiMotoEvento.tipo == EVENTO_PENDENTE)
    )
    q = _aplicar_filtros_evento(q, filtros)
    rows = q.order_by(AssaiMotoEvento.ocorrido_em.desc()).all()
    if not rows:
        return []

    chassis = [ev.chassi for ev in rows]
    motos = (
        AssaiMoto.query
        .options(joinedload(AssaiMoto.modelo))
        .filter(AssaiMoto.chassi.in_(chassis))
        .all()
    )
    moto_por_chassi = {m.chassi: m for m in motos}

    # Filtro modelo_id (pos-load): aplicado depois do JOIN com AssaiMoto
    filtro_modelo_id = (filtros or {}).get('modelo_id')

    result = []
    for ev in rows:
        moto = moto_por_chassi.get(ev.chassi)
        if filtro_modelo_id and (not moto or moto.modelo_id != filtro_modelo_id):
            continue
        obs = ev.observacao
        chassi_doador = None
        if isinstance(ev.dados_extras, dict):
            if not obs:
                obs = ev.dados_extras.get('descricao')
            chassi_doador = ev.dados_extras.get('chassi_doador')
        result.append({
            'evento_id': ev.id,
            'chassi': ev.chassi,
            'modelo_id': moto.modelo_id if moto else None,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'modelo_nome': moto.modelo.nome if moto and moto.modelo else '-',
            'cor': (moto.cor if moto else None) or '-',
            'observacao': obs or '(sem observacao)',
            'chassi_doador': chassi_doador,
            'operador': ev.operador.nome if ev.operador else '-',
            'operador_id': ev.operador_id,
            'ocorrido_em': ev.ocorrido_em,
        })
    return result


def listar_historico_resolvidas(
    limit: int = 200,
    filtros: Optional[FiltrosPendencias] = None,
) -> List[Dict[str, Any]]:
    """Eventos PENDENCIA_RESOLVIDA (historico append-only).

    Para cada evento, busca o ultimo PENDENTE imediatamente anterior do mesmo
    chassi para mostrar a observacao original.

    Filtros aceitos: mesmos de listar_abertas. Filtros operador/data se aplicam
    ao evento de RESOLUCAO (PENDENCIA_RESOLVIDA), nao ao PENDENTE original.

    Retorna: [{evento_id, chassi, modelo_id, modelo_codigo, modelo_nome, cor,
               observacao_pendencia, descricao_resolucao, operador_pendencia,
               operador_resolucao, data_pendencia, data_resolucao}]
    """
    q = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter(AssaiMotoEvento.tipo == EVENTO_PENDENCIA_RESOLVIDA)
    )
    q = _aplicar_filtros_evento(q, filtros)
    resolucoes = q.order_by(AssaiMotoEvento.ocorrido_em.desc()).limit(limit).all()
    if not resolucoes:
        return []

    chassis = list({ev.chassi for ev in resolucoes})
    motos = (
        AssaiMoto.query
        .options(joinedload(AssaiMoto.modelo))
        .filter(AssaiMoto.chassi.in_(chassis))
        .all()
    )
    moto_por_chassi = {m.chassi: m for m in motos}

    # Batch fetch: pega TODOS os PENDENTE dos chassis envolvidos de uma vez,
    # ordenados por id DESC. Para cada resolucao busca o PENDENTE com id < res.id
    # do mesmo chassi (mais recente). Evita N+1.
    todos_pendentes = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter(
            AssaiMotoEvento.chassi.in_(chassis),
            AssaiMotoEvento.tipo == EVENTO_PENDENTE,
        )
        .order_by(AssaiMotoEvento.chassi, AssaiMotoEvento.id.desc())
        .all()
    )
    pendentes_por_chassi: dict = {}
    for ev in todos_pendentes:
        pendentes_por_chassi.setdefault(ev.chassi, []).append(ev)

    filtro_modelo_id = (filtros or {}).get('modelo_id')

    result = []
    for res in resolucoes:
        moto = moto_por_chassi.get(res.chassi)
        if filtro_modelo_id and (not moto or moto.modelo_id != filtro_modelo_id):
            continue
        # Encontra o PENDENTE imediatamente anterior (id < res.id) do mesmo chassi
        pendente = None
        for ev in pendentes_por_chassi.get(res.chassi, []):
            if ev.id < res.id:
                pendente = ev
                break
        obs_pend = None
        if pendente:
            obs_pend = pendente.observacao
            if not obs_pend and isinstance(pendente.dados_extras, dict):
                obs_pend = pendente.dados_extras.get('descricao')

        result.append({
            'evento_id': res.id,
            'chassi': res.chassi,
            'modelo_id': moto.modelo_id if moto else None,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'modelo_nome': moto.modelo.nome if moto and moto.modelo else '-',
            'cor': (moto.cor if moto else None) or '-',
            'observacao_pendencia': obs_pend or '(sem registro)',
            'descricao_resolucao': res.observacao or '(sem descricao)',
            'operador_pendencia': pendente.operador.nome if pendente and pendente.operador else '-',
            'operador_resolucao': res.operador.nome if res.operador else '-',
            'operador_resolucao_id': res.operador_id,
            'data_pendencia': pendente.ocorrido_em.strftime('%d/%m/%Y %H:%M') if pendente and pendente.ocorrido_em else '-',
            'data_resolucao': res.ocorrido_em.strftime('%d/%m/%Y %H:%M') if res.ocorrido_em else '-',
        })
    return result


def contar_pendencias_abertas() -> int:
    """Conta chassis cujo ultimo evento = PENDENTE."""
    sub = _ultimo_evento_subquery()
    return (
        db.session.query(func.count(AssaiMotoEvento.id))
        .join(sub, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiMotoEvento.tipo == EVENTO_PENDENTE)
        .scalar() or 0
    )


# ---------------------------------------------------------------------------
# Helpers para autocomplete dos filtros
# ---------------------------------------------------------------------------


def operadores_que_registraram_pendencia(tipos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Lista usuarios distintos que ja registraram PENDENTE ou PENDENCIA_RESOLVIDA.

    Usado para popular o select/datalist do filtro 'operador'.

    Args:
        tipos: lista de tipos de evento (default: ambos).

    Returns:
        [{id, nome, email}, ...] ordenado por nome.
    """
    tipos = tipos or [EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA]

    operador_ids = (
        db.session.query(AssaiMotoEvento.operador_id)
        .filter(
            AssaiMotoEvento.tipo.in_(tipos),
            AssaiMotoEvento.operador_id.isnot(None),
        )
        .distinct()
        .all()
    )
    ids = [oid for (oid,) in operador_ids]
    if not ids:
        return []

    usuarios = (
        Usuario.query
        .filter(Usuario.id.in_(ids))
        .order_by(Usuario.nome)
        .all()
    )
    return [{'id': u.id, 'nome': u.nome, 'email': u.email} for u in usuarios]


def modelos_com_pendencias(tipos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Lista modelos distintos que ja tiveram pendencia (chassi com PENDENTE
    ou PENDENCIA_RESOLVIDA registrado).

    Usado para popular o select do filtro 'modelo'.

    Returns:
        [{id, codigo, nome}, ...] ordenado por codigo.
    """
    tipos = tipos or [EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA]

    chassis_subq = (
        db.session.query(AssaiMotoEvento.chassi)
        .filter(AssaiMotoEvento.tipo.in_(tipos))
        .distinct()
        .subquery()
    )

    modelos = (
        db.session.query(AssaiModelo)
        .join(AssaiMoto, AssaiMoto.modelo_id == AssaiModelo.id)
        .filter(AssaiMoto.chassi.in_(db.session.query(chassis_subq.c.chassi)))
        .distinct()
        .order_by(AssaiModelo.codigo)
        .all()
    )
    return [{'id': m.id, 'codigo': m.codigo, 'nome': m.nome} for m in modelos]
