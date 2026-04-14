"""
JSON Helpers — Sanitizacao de estruturas Python para campos JSON/JSONB
========================================================================

PROBLEMA
--------
Colunas `db.Column(db.JSON)` / `db.Column(JSONB)` do SQLAlchemy delegam
serializacao ao `json.dumps()` do Python, que NAO sabe serializar tipos
comuns em codigo financeiro/logistico:

- `Decimal`              -> TypeError: Object of type Decimal is not JSON serializable
- `datetime` / `date`    -> TypeError: Object of type datetime is not JSON serializable
- `UUID`                 -> TypeError: Object of type UUID is not JSON serializable
- `bytes`                -> TypeError: Object of type bytes is not JSON serializable
- `set` / `frozenset`    -> TypeError: Object of type set is not JSON serializable

O erro so aparece no `db.session.flush()`/`commit()`, DEPOIS que o ORM
ja marcou o objeto como sujo — a transacao inteira e abortada com
`This Session's transaction has been rolled back due to a previous exception`.

SOLUCAO
-------
Sanitize ANTES de atribuir o dict ao campo ORM.

    from app.utils.json_helpers import sanitize_for_json

    # ANTES (quebra):
    cotacao.detalhes_calculo = resultado_calculadora  # dict com Decimals

    # DEPOIS (seguro):
    cotacao.detalhes_calculo = sanitize_for_json(resultado_calculadora)

A funcao e IDEMPOTENTE: aplicar em dicts que ja sao JSON-safe nao causa
efeito colateral (passthrough para tipos nativos).

QUANDO USAR
-----------
SEMPRE que atribuir a um campo `db.JSON` / `JSONB` dados que contenham
(ou POSSAM conter) valores vindos de:

1. Queries SQLAlchemy com colunas `Numeric`/`DECIMAL` (retornam `Decimal`)
2. `CalculadoraFrete.calcular_frete_unificado()` e correlatos
3. ORM objects com `__dict__` / campos timestamp
4. APIs Odoo (retornam datetimes e UUIDs)
5. Parsers XML/PDF que usem `Decimal` para precisao monetaria
6. Qualquer dict cuja fonte voce nao controla 100%

QUANDO NAO PRECISA
------------------
- Dict construido manualmente SO com `str`, `int`, `float`, `bool`, `None`
- Payloads `request.get_json()` (ja vem deserializado em tipos JSON-safe)
- JSONB usado apenas com defaults estaticos (listas literais, etc.)

Em caso de duvida: APLICAR. E idempotente e ~microssegundos em dicts pequenos.

REGRA DE OURO
-------------
Campo `db.JSON`/`JSONB` recebendo dict vindo de calculo numerico ou
query -> `sanitize_for_json()` antes. Sem excecoes.

Ver tambem:
- `~/.claude/CLAUDE.md` (regra "JSON Sanitization")
- `.claude/references/INDEX.md` (entrada "Helper JSON sanitization")
"""

from __future__ import annotations

import base64
import logging
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


def sanitize_for_json(obj: Any, decimal_as_str: bool = False) -> Any:
    """Converte estrutura Python para JSON-safe recursivamente.

    Trata tipos comuns que `json.dumps()` nao serializa nativamente.
    Preserva estrutura (dict/list) e tipos ja JSON-safe (passthrough).

    Args:
        obj: Valor a sanitizar (qualquer tipo).
        decimal_as_str: Se True, Decimals viram strings (preserva precisao
            exata — recomendado para valores monetarios criticos de auditoria).
            Se False (default), viram floats (mais natural em JSON e no
            frontend; pode perder precisao em >15 digitos significativos).

    Returns:
        Estrutura equivalente com apenas tipos JSON-safe:
        None, bool, int, float, str, list, dict com chaves str.

    Conversoes:
        - Decimal                       -> float (ou str se decimal_as_str)
        - datetime / date / time        -> ISO 8601 string
        - UUID                          -> str
        - bytes / bytearray             -> UTF-8 string (fallback base64)
        - set / frozenset / tuple       -> list sanitizada
        - Enum                          -> sanitize(enum.value)
        - dict                          -> dict recursivo (chaves coercidas para str)
        - list                          -> list recursiva
        - objeto com `to_dict()`        -> sanitize(obj.to_dict())
        - objeto com `__dict__`         -> sanitize(obj.__dict__) (fallback)
        - None / bool / int / float / str -> passthrough

    Raises:
        TypeError: Apenas se encontrar tipo exotico sem fallback (raro).

    Exemplos:
        >>> from decimal import Decimal
        >>> sanitize_for_json({'frete': Decimal('123.45'), 'ok': True})
        {'frete': 123.45, 'ok': True}

        >>> sanitize_for_json({'frete': Decimal('123.45')}, decimal_as_str=True)
        {'frete': '123.45'}

        >>> from datetime import datetime
        >>> sanitize_for_json({'criado_em': datetime(2026, 4, 14, 10, 30)})
        {'criado_em': '2026-04-14T10:30:00'}

        >>> # Idempotente em estruturas ja JSON-safe:
        >>> sanitize_for_json({'a': 1, 'b': [1, 2, {'c': 'x'}]})
        {'a': 1, 'b': [1, 2, {'c': 'x'}]}

        >>> # Aninhamento profundo:
        >>> sanitize_for_json({
        ...     'items': [
        ...         {'valor': Decimal('10.5'), 'data': date(2026, 4, 14)}
        ...     ]
        ... })
        {'items': [{'valor': 10.5, 'data': '2026-04-14'}]}
    """
    # Tipos JSON-safe nativos — passthrough
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    # Decimal: conversao para float ou str
    if isinstance(obj, Decimal):
        if decimal_as_str:
            return str(obj)
        try:
            return float(obj)
        except (ValueError, OverflowError):
            # Decimal('Infinity'), Decimal('NaN'), etc.
            return str(obj)

    # datetime / date / time: ISO 8601
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.isoformat()

    # UUID
    if isinstance(obj, UUID):
        return str(obj)

    # Bytes / bytearray: tentar decodificar UTF-8, fallback base64
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode('utf-8')
        except (UnicodeDecodeError, AttributeError):
            return base64.b64encode(bytes(obj)).decode('ascii')

    # Enum: sanitizar valor interno
    if isinstance(obj, Enum):
        return sanitize_for_json(obj.value, decimal_as_str=decimal_as_str)

    # Dict: recursao preservando tipo
    if isinstance(obj, dict):
        return {
            _coerce_key(k): sanitize_for_json(v, decimal_as_str=decimal_as_str)
            for k, v in obj.items()
        }

    # Sequencias iteraveis -> list
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [
            sanitize_for_json(item, decimal_as_str=decimal_as_str)
            for item in obj
        ]

    # Fallback 1: objetos com to_dict() (comum em modelos ORM customizados)
    if hasattr(obj, 'to_dict') and callable(obj.to_dict):
        try:
            return sanitize_for_json(obj.to_dict(), decimal_as_str=decimal_as_str)
        except Exception as e:
            logger.debug("to_dict() falhou em %s: %s", type(obj).__name__, e)

    # Fallback 2: objetos com __dict__ (objetos arbitrarios Python)
    if hasattr(obj, '__dict__'):
        try:
            # Filtra atributos privados (_xxx) e de sistema (__xxx__)
            clean = {
                k: v for k, v in obj.__dict__.items()
                if not k.startswith('_')
            }
            return sanitize_for_json(clean, decimal_as_str=decimal_as_str)
        except Exception as e:
            logger.debug("__dict__ falhou em %s: %s", type(obj).__name__, e)

    # Fallback final: str() — perde fidelidade mas nao quebra o flush
    logger.warning(
        "sanitize_for_json: tipo nao suportado %s, usando str() fallback",
        type(obj).__name__,
    )
    return str(obj)


def _coerce_key(key: Any) -> str:
    """Coerce dict key to JSON-safe string.

    JSON exige chaves string. Converte int/float/bool/None/outros para str.
    """
    if isinstance(key, str):
        return key
    if key is None:
        return 'null'
    if isinstance(key, bool):
        return 'true' if key else 'false'
    if isinstance(key, (int, float, Decimal)):
        return str(key)
    return str(key)


__all__ = ['sanitize_for_json']
