"""Helpers para emitir e consultar eventos de moto.

Estado da moto = último evento por `ocorrido_em DESC`. Eventos são append-only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

from app import db
from app.motos_assai.models import (
    AssaiMotoEvento, EVENTOS_VALIDOS, EVENTOS_EM_ESTOQUE,
    EVENTO_ESTOQUE, EVENTO_MOTO_FALTANDO,
)


class EventoInvalidoError(Exception):
    pass


def emitir_evento(
    chassi: str,
    tipo: str,
    operador_id: Optional[int] = None,
    observacao: Optional[str] = None,
    dados_extras: Optional[Dict[str, Any]] = None,
    ocorrido_em: Optional[datetime] = None,
) -> AssaiMotoEvento:
    """Cria um novo evento (NÃO commita — caller decide).

    `ocorrido_em` opcional: registra o evento com data retroativa (carga
    histórica / backfill / correção). Quando None (default), o model aplica
    `agora_brasil_naive`, preservando o comportamento atual de todos os callers.
    Deve ser **Brasil naive** (sem tzinfo) — convenção do sistema, ver
    `.claude/references/REGRAS_TIMEZONE.md`.
    """
    if tipo not in EVENTOS_VALIDOS:
        raise EventoInvalidoError(f'Tipo inválido: {tipo}. Válidos: {EVENTOS_VALIDOS}')

    campos: Dict[str, Any] = dict(
        chassi=chassi.strip().upper(),
        tipo=tipo,
        operador_id=operador_id,
        observacao=observacao,
        dados_extras=dados_extras or {},
    )
    # Só sobrescreve o default do model quando uma data é fornecida — passar
    # ocorrido_em=None ao construtor anularia o default e violaria NOT NULL.
    if ocorrido_em is not None:
        campos['ocorrido_em'] = ocorrido_em

    evento = AssaiMotoEvento(**campos)
    db.session.add(evento)
    db.session.flush()
    return evento


def ultimo_evento(chassi: str) -> Optional[AssaiMotoEvento]:
    """Retorna o evento mais recente ou None."""
    return (
        AssaiMotoEvento.query
        .filter_by(chassi=chassi.strip().upper())
        .order_by(AssaiMotoEvento.ocorrido_em.desc(), AssaiMotoEvento.id.desc())
        .first()
    )


def status_efetivo(chassi: str) -> Optional[str]:
    """String do tipo do último evento, ou None se moto sem eventos."""
    e = ultimo_evento(chassi)
    return e.tipo if e else None


def eventos_chassi(chassi: str, limit: int = 50) -> List[AssaiMotoEvento]:
    """Histórico do chassi (mais recente primeiro)."""
    return (
        AssaiMotoEvento.query
        .filter_by(chassi=chassi.strip().upper())
        .order_by(AssaiMotoEvento.ocorrido_em.desc(), AssaiMotoEvento.id.desc())
        .limit(limit)
        .all()
    )


def chassis_em_estoque(modelo_id: Optional[int] = None) -> List[str]:
    """Lista chassis cujo último evento está em EVENTOS_EM_ESTOQUE.

    Implementação: subquery do MAX(ocorrido_em, id) por chassi → join.
    """
    from app.motos_assai.models import AssaiMoto
    from sqlalchemy import func, and_

    sub = (
        db.session.query(
            AssaiMotoEvento.chassi,
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )

    q = (
        db.session.query(AssaiMotoEvento.chassi)
        .join(sub, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiMotoEvento.tipo.in_(list(EVENTOS_EM_ESTOQUE)))
    )

    if modelo_id is not None:
        q = q.join(AssaiMoto, AssaiMoto.chassi == AssaiMotoEvento.chassi)\
             .filter(AssaiMoto.modelo_id == modelo_id)

    return [r[0] for r in q.all()]
