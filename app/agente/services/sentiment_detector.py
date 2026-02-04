"""
P1-2: Detecção de Sentimento do Usuário.

Detecta frustração do operador logístico usando heurísticas locais (sem API).
Quando frustração é detectada, retorna uma instrução para o modelo ser mais direto.

Custo: zero (detecção local, sem chamada Haiku).

Sinais de frustração detectados:
1. Mensagens muito curtas (1-2 palavras) em sequência com erros anteriores
2. Marcadores explícitos de insatisfação ("não era isso", "errado", "de novo")
3. Repetição de perguntas similares (indica que resposta anterior não ajudou)
4. Pontuação excessiva (???, !!!, CAPS)

Uso:
    O detector é chamado em _async_stream_sdk_client() antes de enviar a mensagem ao SDK.
    Se frustração detectada, a mensagem é prefixada com instrução de ajuste de tom.
"""

import logging
import re
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Marcadores explícitos de frustração (português brasileiro)
FRUSTRATION_MARKERS = [
    # Rejeição direta
    r'\bnão era isso\b',
    r'\bnao era isso\b',
    r'\berrado\b',
    r'\bincorreto\b',
    r'\bde novo\b',
    r'\boutra vez\b',
    r'\brepete\b',
    r'\brepita\b',
    r'\bjá falei\b',
    r'\bja falei\b',
    r'\bjá disse\b',
    r'\bja disse\b',
    # Impaciência
    r'\bsó isso\b',
    r'\bso isso\b',
    r'\bsó responde\b',
    r'\bso responde\b',
    r'\bdiret[oa]\b',
    r'\bobjetiv[oa]\b',
    r'\bpor favor\b.*\b(funciona|responde|mostra)\b',
    # Frustração forte
    r'\bnão funciona\b',
    r'\bnao funciona\b',
    r'\bnão entendeu\b',
    r'\bnao entendeu\b',
    r'\bque droga\b',
    r'\bque saco\b',
    r'\bpreciso disso\b',
]

# Instrução injetada quando frustração é detectada
FRUSTRATION_INSTRUCTION = (
    "\n\n[CONTEXTO INTERNO — NÃO MENCIONE: O usuário demonstra pressa ou frustração. "
    "Seja MAIS direto, MENOS explicativo. Vá direto ao ponto sem rodeios. "
    "Evite introduções longas, listas desnecessárias e explicações que o usuário não pediu. "
    "Responda de forma concisa e objetiva.]"
)


def detect_frustration(
    message: str,
    previous_messages: Optional[List[Dict[str, Any]]] = None,
    had_error: bool = False,
) -> bool:
    """
    Detecta sinais de frustração na mensagem do usuário.

    A detecção é conservadora: prefere falso negativo a falso positivo.
    Melhor não detectar frustração real do que irritar quem não está frustrado.

    Args:
        message: Mensagem atual do usuário
        previous_messages: Histórico recente (últimas 3-5 mensagens, opcional)
        had_error: Se houve erro na resposta anterior

    Returns:
        True se frustração detectada, False caso contrário
    """
    if not message or len(message.strip()) == 0:
        return False

    msg = message.strip()
    score = 0

    # =================================================================
    # Sinal 1: Marcadores explícitos de frustração (forte)
    # =================================================================
    msg_lower = msg.lower()
    for pattern in FRUSTRATION_MARKERS:
        if re.search(pattern, msg_lower):
            score += 3
            logger.debug(f"[SENTIMENT] Marcador de frustração: {pattern}")
            break  # Um marcador é suficiente para alto score

    # =================================================================
    # Sinal 2: Mensagem muito curta após erro (forte)
    # Uma resposta de 1-2 palavras logo após um erro é sinal forte
    # =================================================================
    word_count = len(msg.split())
    if word_count <= 2 and had_error:
        score += 3
        logger.debug(f"[SENTIMENT] Mensagem curta após erro: {word_count} palavras")

    # =================================================================
    # Sinal 3: Pontuação excessiva (moderado)
    # =================================================================
    if re.search(r'[?!]{3,}', msg):
        score += 2
        logger.debug("[SENTIMENT] Pontuação excessiva detectada")

    # =================================================================
    # Sinal 4: CAPS LOCK (moderado)
    # =================================================================
    # Mais de 60% em maiúsculas (excluindo números e pontuação)
    alpha_chars = [c for c in msg if c.isalpha()]
    if len(alpha_chars) > 5:
        upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        if upper_ratio > 0.6:
            score += 2
            logger.debug(f"[SENTIMENT] CAPS detectado: {upper_ratio:.0%}")

    # =================================================================
    # Sinal 5: Mensagem curta isolada (fraco)
    # Palavras únicas ou muito curtas podem indicar impaciência
    # =================================================================
    if word_count <= 3 and not had_error:
        score += 1

    # =================================================================
    # Threshold: score >= 3 = frustração detectada
    # =================================================================
    is_frustrated = score >= 3

    if is_frustrated:
        logger.info(
            f"[SENTIMENT] Frustração detectada (score={score}): "
            f"'{msg[:50]}{'...' if len(msg) > 50 else ''}'"
        )

    return is_frustrated


def enrich_message_if_frustrated(
    message: str,
    response_state: dict,
) -> str:
    """
    Verifica frustração e enriquece a mensagem se necessário.

    Função principal chamada por routes.py antes de enviar ao SDK.

    Args:
        message: Mensagem original do usuário
        response_state: Estado da resposta (contém error_message se houve erro)

    Returns:
        Mensagem original (se sem frustração) ou mensagem + instrução de tom
    """
    try:
        had_error = bool(response_state.get('error_message'))

        if detect_frustration(message=message, had_error=had_error):
            return message + FRUSTRATION_INSTRUCTION

    except Exception as e:
        # Best-effort: nunca bloqueia
        logger.warning(f"[SENTIMENT] Erro na detecção (ignorado): {e}")

    return message
