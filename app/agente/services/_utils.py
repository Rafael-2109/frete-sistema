"""
Utilitários compartilhados entre services do agente.

Funções genéricas reutilizadas por múltiplos services para evitar duplicação.
"""

import json
import logging
import re
from typing import Optional, Type, Union

logger = logging.getLogger('sistema_fretes')


def parse_llm_json_response(
    text: str,
    expected_type: Type = dict,
    context: str = "",
) -> Optional[Union[dict, list]]:
    """
    Parse seguro de resposta JSON do LLM com fallback regex.

    Dois passos:
    1. Tenta json.loads() direto
    2. Fallback: extrai primeiro bloco JSON/array via regex

    Args:
        text: Texto bruto da resposta do LLM
        expected_type: dict ou list — tipo esperado do JSON
        context: Identificador para logging (ex: "PATTERNS user=5")

    Returns:
        dict ou list parseado, ou None/[] se falhar
    """
    regex = r'\{[\s\S]*\}' if expected_type is dict else r'\[[\s\S]*\]'

    # Tentativa 1: parse direto
    try:
        result = json.loads(text)
        if isinstance(result, expected_type):
            return result
    except json.JSONDecodeError:
        pass

    # Tentativa 2: regex fallback
    try:
        match = re.search(regex, text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            if isinstance(result, expected_type):
                return result
    except (json.JSONDecodeError, AttributeError):
        pass

    if context:
        logger.warning(f"[{context}] Resposta JSON invalida: {text[:200]}")
    return [] if expected_type is list else None
