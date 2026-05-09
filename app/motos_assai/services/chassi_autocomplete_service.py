"""Autocomplete de chassi para inputs operacionais do modulo Motos Assai.

Filtros por contexto (read-only). Retorna no maximo `limit` chassis que casam
substring com o termo `q` (case-insensitive), ja anotados com modelo/cor/status.

Contextos suportados:
- ``recebimento``        : chassis declarados no recibo, ainda nao conferidos
- ``montagem``           : chassis cujo ultimo evento e ESTOQUE
- ``montagem_doador``    : qualquer chassi cadastrado em assai_moto
- ``disponibilizar``     : chassis cujo ultimo evento e MONTADA / REVERTIDA_PARA_MONTADA / PENDENCIA_RESOLVIDA
- ``separacao``          : chassis cujo ultimo evento e DISPONIVEL
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import func

from app import db
from app.motos_assai.models import (
    AssaiModelo,
    AssaiMoto,
    AssaiMotoEvento,
    AssaiReciboItem,
    EVENTO_DISPONIVEL,
    EVENTO_ESTOQUE,
    EVENTO_MONTADA,
    EVENTO_PENDENCIA_RESOLVIDA,
    EVENTO_REVERTIDA_PARA_MONTADA,
)


CONTEXTOS_VALIDOS = {
    'recebimento',
    'montagem',
    'montagem_doador',
    'disponibilizar',
    'separacao',
}

MIN_CHARS = 4
LIMIT_DEFAULT = 10
LIMIT_MAX = 30


class AutocompleteValidationError(ValueError):
    pass


def _ultimo_evento_subquery():
    """Subquery que retorna o id do ultimo evento por chassi.

    Padrao espelhado de `moto_evento_service.chassis_em_estoque` (ll. 79-86).
    """
    return (
        db.session.query(
            AssaiMotoEvento.chassi.label('chassi'),
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )


def _query_por_estado(eventos_aceitos: List[str], q_like: str, limit: int):
    """Retorna chassis em assai_moto cujo ultimo evento esta em `eventos_aceitos`."""
    sub = _ultimo_evento_subquery()
    return (
        db.session.query(
            AssaiMoto.chassi,
            AssaiModelo.codigo,
            AssaiModelo.nome,
            AssaiMoto.cor,
            AssaiMotoEvento.tipo,
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiMoto.modelo_id)
        .join(sub, sub.c.chassi == AssaiMoto.chassi)
        .join(AssaiMotoEvento, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiMotoEvento.tipo.in_(eventos_aceitos))
        .filter(AssaiMoto.chassi.ilike(q_like))
        .order_by(AssaiMoto.chassi.asc())
        .limit(limit)
        .all()
    )


def _query_qualquer_chassi(q_like: str, limit: int):
    """Retorna qualquer chassi cadastrado em assai_moto (estado opcional)."""
    sub = _ultimo_evento_subquery()
    return (
        db.session.query(
            AssaiMoto.chassi,
            AssaiModelo.codigo,
            AssaiModelo.nome,
            AssaiMoto.cor,
            AssaiMotoEvento.tipo,
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiMoto.modelo_id)
        .outerjoin(sub, sub.c.chassi == AssaiMoto.chassi)
        .outerjoin(AssaiMotoEvento, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiMoto.chassi.ilike(q_like))
        .order_by(AssaiMoto.chassi.asc())
        .limit(limit)
        .all()
    )


def _query_recibo(recibo_id: int, q_like: str, limit: int):
    """Retorna chassis declarados no recibo, ainda nao conferidos."""
    return (
        db.session.query(
            AssaiReciboItem.chassi,
            AssaiModelo.codigo,
            AssaiModelo.nome,
            AssaiReciboItem.cor_texto,
            AssaiReciboItem.modelo_texto_recibo,
        )
        .outerjoin(AssaiModelo, AssaiModelo.id == AssaiReciboItem.modelo_id)
        .filter(AssaiReciboItem.recibo_id == recibo_id)
        .filter(AssaiReciboItem.conferido.is_(False))
        .filter(AssaiReciboItem.chassi.ilike(q_like))
        .order_by(AssaiReciboItem.chassi.asc())
        .limit(limit)
        .all()
    )


def buscar_chassis(
    q: str,
    contexto: str,
    recibo_id: Optional[int] = None,
    limit: int = LIMIT_DEFAULT,
) -> List[Dict[str, str]]:
    """Busca chassis para autocomplete.

    Args:
        q: trecho a procurar (substring case-insensitive). Minimo `MIN_CHARS`.
        contexto: um dos ``CONTEXTOS_VALIDOS``.
        recibo_id: obrigatorio quando ``contexto == 'recebimento'``.
        limit: maximo de resultados (cap em ``LIMIT_MAX``).

    Returns:
        Lista de dicts ``{chassi, modelo_codigo, modelo_nome, cor, status}``.
        Lista vazia se ``q`` tem menos de ``MIN_CHARS`` chars (sem hit no banco).

    Raises:
        AutocompleteValidationError: contexto invalido ou recibo_id faltando.
    """
    q_norm = (q or '').strip().upper()
    if len(q_norm) < MIN_CHARS:
        return []

    if contexto not in CONTEXTOS_VALIDOS:
        raise AutocompleteValidationError(
            f'Contexto invalido: {contexto}. Validos: {sorted(CONTEXTOS_VALIDOS)}'
        )

    limit = max(1, min(int(limit or LIMIT_DEFAULT), LIMIT_MAX))
    # Escapa wildcards LIKE no termo do usuario
    q_escaped = q_norm.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    q_like = f'%{q_escaped}%'

    if contexto == 'recebimento':
        if not recibo_id:
            raise AutocompleteValidationError('recibo_id obrigatorio no contexto recebimento')
        rows = _query_recibo(int(recibo_id), q_like, limit)
        return [
            {
                'chassi': r[0],
                'modelo_codigo': r[1] or '',
                'modelo_nome': r[2] or (r[4] or ''),
                'cor': r[3] or '',
                'status': 'PENDENTE_RECIBO',
            }
            for r in rows
        ]

    if contexto == 'montagem':
        rows = _query_por_estado([EVENTO_ESTOQUE], q_like, limit)
    elif contexto == 'disponibilizar':
        rows = _query_por_estado(
            [EVENTO_MONTADA, EVENTO_REVERTIDA_PARA_MONTADA, EVENTO_PENDENCIA_RESOLVIDA],
            q_like,
            limit,
        )
    elif contexto == 'separacao':
        rows = _query_por_estado([EVENTO_DISPONIVEL], q_like, limit)
    else:  # montagem_doador
        rows = _query_qualquer_chassi(q_like, limit)

    return [
        {
            'chassi': r[0],
            'modelo_codigo': r[1] or '',
            'modelo_nome': r[2] or '',
            'cor': r[3] or '',
            'status': r[4] or '',
        }
        for r in rows
    ]
