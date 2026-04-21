"""
Model Router — selecao programatica de modelo por intent.

Fase 1 (2026-04-21): roteamento baseado em padroes observados em 21 sessoes
de producao com custo > $10 USD. Tarefas estruturadas repetitivas (ex:
"vincular pedido X na nota Y") sao resolvidas por Sonnet sem perda de
qualidade — o pipeline de recebimento e deterministico apos o match NF-PO.

Compartilhado entre Teams (`app/teams/services.py:_select_model_for_message`)
e Web (`app/agente/routes/chat.py:api_chat`).

NUNCA promove Sonnet -> Opus: se usuario/frontend explicitou Sonnet, respeitar.
Apenas REBAIXA Opus -> Sonnet quando o padrao identifica tarefa repetitiva.

Flags: `TEAMS_SMART_MODEL_ROUTING`, `WEB_SMART_MODEL_ROUTING` (caller verifica).
"""
from __future__ import annotations

import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)


# Padroes que GARANTEM tarefa estruturada repetitiva (Sonnet adequado).
# Baseados em amostra real de 25 sessoes Teams da Gabriella e 21 sessoes > $10.
_FAST_MODEL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # NF-PO: "vincular (o) pedido C2615437 na nota 48862 pelo frete e pelo odoo"
    (
        re.compile(
            r"vincular\s+(o\s+)?pedido\s+[A-Z0-9]+\s+"
            r"na\s+nota\s+\d+\s+"
            r"(pelo|no|pelos?|nos?)\s+(frete|odoo)",
            re.IGNORECASE,
        ),
        "padrao_nf_po",
    ),
    # Follow-up curto de status (Marcus 15x "executou a tarefa anterior?")
    (
        re.compile(
            r"^(algum\s+retorno|executou(\s+[a-zA-Zá-úÁ-Ú]+){0,3}|"
            r"pronto|terminou|acabou|ta\s+pronto|tudo\s+certo|"
            r"ja\s+executou|ja\s+rodou|conseguiu)\s*\??$",
            re.IGNORECASE,
        ),
        "follow_up_curto",
    ),
    # Saudacoes / agradecimentos isolados (sem conteudo operacional)
    (
        re.compile(
            r"^(oi|ol[aá]|bom\s+dia|boa\s+tarde|boa\s+noite|"
            r"tudo\s+bem|como\s+vai|obrigad[oa]|valeu|thanks|hi|hello|hey)"
            r"[\s\?\.!]*$",
            re.IGNORECASE,
        ),
        "saudacao",
    ),
    # Confirmacoes curtas ("confirmo", "pode", "ok")
    (
        re.compile(
            r"^(confirmo|pode(\s+seguir|\s+prosseguir|\s+fazer)?|"
            r"ok|sim|yes|segue)[\s\.!]*$",
            re.IGNORECASE,
        ),
        "confirmacao_curta",
    ),
]


def select_model(
    prompt: str,
    default_model: str,
    fast_model: str,
) -> Tuple[str, str]:
    """
    Seleciona modelo com base em padroes de intent do prompt.

    Args:
        prompt: mensagem do usuario (stripped). String vazia = default.
        default_model: modelo padrao (tipicamente Opus 4.7).
        fast_model: modelo barato/rapido (tipicamente Sonnet 4.6).

    Returns:
        Tupla (model_escolhido, reason). Reason e string curta para log/metric.

    Regras:
        1. Prompt vazio ou None -> default_model, reason='empty'
        2. Matched um dos patterns em _FAST_MODEL_PATTERNS -> fast_model,
           reason do pattern.
        3. Prompt muito curto (<= 3 palavras) sem conteudo identificado ->
           fast_model, reason='prompt_muito_curto'.
        4. Default: default_model, reason='default'.

    NOTA: Se caller quer desabilitar routing, NAO chamar esta funcao —
    verificar flag antes (TEAMS_SMART_MODEL_ROUTING / WEB_SMART_MODEL_ROUTING).

    Exemplo:
        >>> select_model(
        ...     "vincular pedido C123 na nota 456 pelo odoo",
        ...     "claude-opus-4-7",
        ...     "claude-sonnet-4-6",
        ... )
        ('claude-sonnet-4-6', 'padrao_nf_po')
    """
    if not prompt or not prompt.strip():
        return default_model, "empty"

    stripped = prompt.strip()

    # Patterns explicitos
    for pattern, reason in _FAST_MODEL_PATTERNS:
        if pattern.search(stripped):
            return fast_model, reason

    # Prompt muito curto sem pattern -> provavelmente follow-up simples.
    # Fix pos-review (2026-04-21): limite reduzido para <=2 palavras +
    # guards contra comandos operacionais abreviados como:
    #   "cria separacao agora" (3 palavras, operacional, precisa Opus)
    #   "status pedido VCD123" (ID em caps, operacional)
    #   "odoo trava hoje"     (palavra-chave de dominio critico)
    # Sem isso, comandos operacionais 3-word cairiam em Sonnet silenciosamente.
    word_count = len(stripped.split())
    if word_count <= 2:
        return fast_model, "prompt_muito_curto"

    # 3 palavras: so rebaixa se NAO contem uppercase token (IDs)
    # E NAO contem palavras-chave operacionais
    if word_count == 3:
        import re as _re
        _tokens = stripped.split()
        has_uppercase_token = any(
            _re.search(r"[A-Z]{2,}|\d", tok) for tok in _tokens
        )
        _OPERATIONAL_KEYWORDS = {
            'separacao', 'separar', 'embarque', 'embarcar',
            'odoo', 'frete', 'carteira', 'pedido', 'pedidos',
            'nota', 'nf', 'faturamento', 'cte', 'recebimento',
            'cria', 'crie', 'criar', 'gerar', 'gera', 'executar',
            'rodar', 'processar', 'validar', 'conciliar',
            'cancelar', 'atualizar',
        }
        has_op_kw = any(
            tok.lower().rstrip('?!.,;:') in _OPERATIONAL_KEYWORDS
            for tok in _tokens
        )
        if not has_uppercase_token and not has_op_kw:
            return fast_model, "prompt_muito_curto"

    # Default: modelo principal
    return default_model, "default"


def log_routing_decision(
    session_id: str,
    user_id: int | None,
    prompt_preview: str,
    chosen_model: str,
    reason: str,
    default_model: str,
    fast_model: str,
) -> None:
    """
    Log estruturado da decisao de routing — usado para auditoria e ajuste
    de patterns ao longo do tempo.

    Formato: [MODEL_ROUTER] session=<id> user=<id> model=<chosen>
             reason=<reason> default=<default> fast=<fast> preview="<text>"
    """
    preview = prompt_preview[:80].replace("\n", " ")
    sid_short = (session_id or "")[:12]
    logger.info(
        f"[MODEL_ROUTER] session={sid_short} user={user_id} "
        f"model={chosen_model} reason={reason} "
        f"default={default_model} fast={fast_model} "
        f'preview="{preview}"'
    )
