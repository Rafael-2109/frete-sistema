"""Agent Router — decide qual PAPEL (principal vs especialista quente) atende o turno.

Irmao do model_router.py. F1 piloto: unico especialista = 'gestor-recebimento'.
Decisao 1x por turno no inicio (cliente fixo no turno). Conservador (R-EXEC-6):
so' entra no especialista em frase clara de recebimento; mantem em continuacao
curta; sai (reversao) em sinal de outro dominio; default principal.
"""
from __future__ import annotations
import logging
import re

logger = logging.getLogger(__name__)

PILOT_SPECIALIST = "gestor-recebimento"

# Frase de recebimento (vinculacao/conciliacao/match NF x PO). Ancorada nos
# padroes reais (model_router padrao_nf_po + vinculacao_fastpath). Disciplina
# espelhada do model_router (2026-05-11):
#  - INFINITIVO completo (conciliar/consolidar, SEM '?'): 'concilia'/'consolida'
#    (3a pessoa) eh pergunta diagnostica, NAO comando -> fica no principal.
#  - VERBO obrigatorio: a mera co-ocorrencia de 'nota N' + 'pedido' sem verbo de
#    vinculo eh conversa de cobranca/financeiro (falso positivo) -> nao casa.
#  - PLURAL aceito (notas?/pedidos?/pos?): '\bpedido\b' nao casava 'pedidos'.
_RE_RECEBIMENTO = re.compile(
    r"\b(vincul\w+|desvincul\w+|conciliar|consolidar|split)\b.*\b(notas?|nfe?s?|pedidos?|pos?)\b"
    r"|\bmatch\s+(da\s+)?nf\b",
    re.IGNORECASE)

# Sinais de OUTRO dominio (reversao do especialista de recebimento).
_RE_OUTRO_DOMINIO = re.compile(
    r"\b(margem|custeio|frete|cota[cç][aã]o|estoque|ruptura|carteira|separa[cç][aã]o|"
    r"embarque|entrega|canhoto|devolu[cç][aã]o|sped|faturar?|sefaz)\b",
    re.IGNORECASE)


def select_specialist(message: str, current_active: str = "principal",
                      word_limit: int = 15) -> tuple[str, str]:
    if not message or not message.strip():
        return "principal", "empty"
    stripped = message.strip()
    words = len(stripped.split())

    # Frase clara de recebimento entra/permanece no especialista — MAS guard de
    # complexidade: pergunta longa/estrategica fica no principal (espelha
    # model_router prompt_complexo, >15 palavras).
    if _RE_RECEBIMENTO.search(stripped):
        if words > word_limit:
            return "principal", "prompt_complexo"
        return PILOT_SPECIALIST, "padrao_recebimento"

    # Ja' dentro do especialista: continuacao curta mantem; outro dominio reverte.
    if current_active == PILOT_SPECIALIST:
        if _RE_OUTRO_DOMINIO.search(stripped):
            return "principal", "reversao_outro_dominio"
        if words <= 6:
            return PILOT_SPECIALIST, "continuacao"
        return "principal", "reversao_assunto_amplo"

    return "principal", "default"


def log_specialist_decision(session_id, user_id, prompt_preview, role, reason) -> None:
    preview = (prompt_preview or "")[:80].replace("\n", " ")
    logger.info(
        f"[AGENT_ROUTER] session={(session_id or '')[:12]} user={user_id} "
        f"role={role} reason={reason} preview=\"{preview}\"")
