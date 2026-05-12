"""Pendencias de montagem (defeitos de peca).

Pendencia aberta: chassi com ultimo evento = PENDENTE.
Pendencia resolvida: cada evento PENDENCIA_RESOLVIDA representa uma resolucao
historica (append-only). Mantemos o registro para auditoria mesmo apos o chassi
voltar para MONTADA.
"""

from __future__ import annotations

from typing import List, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiMotoEvento,
    EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA,
)


def _ultimo_evento_subquery():
    return (
        db.session.query(
            AssaiMotoEvento.chassi.label('chassi'),
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )


def listar_abertas() -> List[Dict[str, Any]]:
    """Chassis cujo ultimo evento = PENDENTE.

    Retorna: [{chassi, modelo_codigo, modelo_nome, cor, observacao,
               operador, ocorrido_em, chassi_doador}]
    """
    sub = _ultimo_evento_subquery()

    rows = (
        db.session.query(AssaiMotoEvento)
        .options(joinedload(AssaiMotoEvento.operador))
        .join(sub, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiMotoEvento.tipo == EVENTO_PENDENTE)
        .order_by(AssaiMotoEvento.ocorrido_em.desc())
        .all()
    )
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

    result = []
    for ev in rows:
        moto = moto_por_chassi.get(ev.chassi)
        obs = ev.observacao
        chassi_doador = None
        if isinstance(ev.dados_extras, dict):
            if not obs:
                obs = ev.dados_extras.get('descricao')
            chassi_doador = ev.dados_extras.get('chassi_doador')
        result.append({
            'evento_id': ev.id,
            'chassi': ev.chassi,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'modelo_nome': moto.modelo.nome if moto and moto.modelo else '-',
            'cor': (moto.cor if moto else None) or '-',
            'observacao': obs or '(sem observacao)',
            'chassi_doador': chassi_doador,
            'operador': ev.operador.nome if ev.operador else '-',
            'ocorrido_em': ev.ocorrido_em,
        })
    return result


def listar_historico_resolvidas(limit: int = 200) -> List[Dict[str, Any]]:
    """Eventos PENDENCIA_RESOLVIDA (historico append-only).

    Para cada evento, busca o ultimo PENDENTE imediatamente anterior do mesmo
    chassi para mostrar a observacao original.

    Retorna: [{chassi, modelo_codigo, cor, observacao_pendencia,
               descricao_resolucao, operador_pendencia, operador_resolucao,
               data_pendencia, data_resolucao}]
    """
    resolucoes = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter(AssaiMotoEvento.tipo == EVENTO_PENDENCIA_RESOLVIDA)
        .order_by(AssaiMotoEvento.ocorrido_em.desc())
        .limit(limit)
        .all()
    )
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
    # Map: chassi -> lista de PENDENTE eventos (mais recente primeiro)
    pendentes_por_chassi: dict = {}
    for ev in todos_pendentes:
        pendentes_por_chassi.setdefault(ev.chassi, []).append(ev)

    result = []
    for res in resolucoes:
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

        moto = moto_por_chassi.get(res.chassi)
        result.append({
            'evento_id': res.id,
            'chassi': res.chassi,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'modelo_nome': moto.modelo.nome if moto and moto.modelo else '-',
            'cor': (moto.cor if moto else None) or '-',
            'observacao_pendencia': obs_pend or '(sem registro)',
            'descricao_resolucao': res.observacao or '(sem descricao)',
            'operador_pendencia': pendente.operador.nome if pendente and pendente.operador else '-',
            'operador_resolucao': res.operador.nome if res.operador else '-',
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
