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
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Cache in-memory de scores por sessao (cross-turn tracking)
# Perde no restart — aceitavel para deteccao real-time de frustracao
_session_scores: Dict[str, list] = {}  # session_id -> ultimos 3 scores

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
    # Falha de ENTREGA/RESULTADO de ferramenta (P5 #787 — "arquivo vazio" pontuava 0).
    # Especificos para NAO colidir com consultas de negocio do dominio logistico
    # (ex: "estoque vazio", "a NF nao saiu", "o pedido nao veio" sao perguntas, nao
    # frustracao). Por isso evitamos marcadores ambiguos como "nao saiu"/"nao veio".
    r'\bnão gerou\b',
    r'\bnao gerou\b',
    r'\bnão funcionou\b',
    r'\bnao funcionou\b',
    r'\bnão abriu\b',
    r'\bnão abre\b',
    r'\bnao abre\b',
    r'\bnão baixou\b',
    r'\bnão baixa\b',
    r'\bnao baixa\b',
    r'\bnão carrega\b',
    r'\bnao carrega\b',
    r'\bveio vazio\b',
    r'\barquivo vazio\b',
    r'\barquivo está vazio\b',
    r'\barquivo esta vazio\b',
    r'\bcadê\b',
    r'\bcade\b',
    r'\bdeu erro\b',
    r'\bdeu pau\b',
    r'\bdeu ruim\b',
]

# Instrução injetada quando frustração é detectada.
# FIX 2026-04-17: usa <system-reminder> (tag oficial Claude) em vez de
# "[CONTEXTO INTERNO — NAO MENCIONE: ...]" — Opus 4.7+ tem defesas fortes
# contra prompt injection e estava sinalizando o formato antigo como
# ataque (falso positivo — era instrucao legitima do sistema).
FRUSTRATION_INSTRUCTION = (
    "\n\n<system-reminder>O usuario demonstra pressa ou frustracao. "
    "Seja MAIS direto, MENOS explicativo. Va direto ao ponto sem rodeios. "
    "Evite introducoes longas, listas desnecessarias e explicacoes que o usuario nao pediu. "
    "Responda de forma concisa e objetiva.</system-reminder>"
)


def detect_frustration(
    message: str,
    previous_messages: Optional[List[Dict[str, Any]]] = None,
    had_error: bool = False,
    recent_scores: Optional[List[int]] = None,
) -> Tuple[bool, int]:
    """
    Detecta sinais de frustração na mensagem do usuário.

    A detecção é conservadora: prefere falso negativo a falso positivo.
    Melhor não detectar frustração real do que irritar quem não está frustrado.

    Args:
        message: Mensagem atual do usuário
        previous_messages: Histórico recente (últimas 3-5 mensagens, opcional)
        had_error: Se houve erro na resposta anterior
        recent_scores: Scores dos últimos 2-3 turns (cross-turn tracking)

    Returns:
        Tupla (is_frustrated, score) — is_frustrated se score >= 3
    """
    if not message or len(message.strip()) == 0:
        return (False, 0)

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
    # Sinal 6: Trend cross-turn (moderado)
    # Se últimos 2+ turns tiveram score >= 1, frustração crescente
    # =================================================================
    if recent_scores and len(recent_scores) >= 2:
        # P5 (#787): exige sinal REAL (>= 2) nos turnos anteriores. Mensagens curtas
        # neutras (Sinal 5 = +1) NAO alimentam mais o trend — antes, 3 curtas
        # seguidas atingiam o threshold (parte dos 49% de falsos positivos).
        if all(s >= 2 for s in recent_scores[-2:]):
            score += 2
            logger.debug(f"[SENTIMENT] Trend cross-turn: scores recentes={recent_scores[-2:]}")

    # =================================================================
    # Threshold: score >= 3 = frustração detectada
    # =================================================================
    is_frustrated = score >= 3

    if is_frustrated:
        logger.info(
            f"[SENTIMENT] Frustração detectada (score={score}): "
            f"'{msg[:50]}{'...' if len(msg) > 50 else ''}'"
        )

    return (is_frustrated, score)


def get_last_frustration_score(session_id: Optional[str]) -> Optional[int]:
    """Onda 1 / E1 — último score de frustração do turno (cache in-memory) ou None.

    Usado pelo wiring de persistência para capturar o score no turno antes
    que o cache seja sobrescrito pelo próximo turno.

    Args:
        session_id: ID da sessão no cache _session_scores.

    Returns:
        Último score inteiro (0-10+) ou None se sessão ausente / sem scores.
    """
    if not session_id:
        return None
    scores = _session_scores.get(session_id)
    return scores[-1] if scores else None


def enrich_message_if_frustrated(
    message: str,
    response_state: dict,
    session_id: Optional[str] = None,
) -> str:
    """
    Verifica frustração e enriquece a mensagem se necessário.

    Função principal chamada por routes.py antes de enviar ao SDK.
    Mantém scores cross-turn em cache in-memory por session_id.

    Args:
        message: Mensagem original do usuário
        response_state: Estado da resposta (contém error_message se houve erro)
        session_id: ID da sessão para tracking cross-turn (opcional)

    Returns:
        Mensagem original (se sem frustração) ou mensagem + instrução de tom
    """
    try:
        had_error = bool(response_state.get('error_message'))

        # Carregar scores anteriores da sessão
        recent_scores = _session_scores.get(session_id, []) if session_id else []

        is_frustrated, current_score = detect_frustration(
            message=message,
            had_error=had_error,
            recent_scores=recent_scores,
        )

        # Salvar score no cache (manter últimos 3)
        if session_id:
            scores = _session_scores.setdefault(session_id, [])
            scores.append(current_score)
            _session_scores[session_id] = scores[-3:]

        if is_frustrated:
            return message + FRUSTRATION_INSTRUCTION

    except Exception as e:
        # Best-effort: nunca bloqueia
        logger.warning(f"[SENTIMENT] Erro na detecção (ignorado): {e}")

    return message
