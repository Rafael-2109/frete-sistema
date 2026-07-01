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
    # NF-PO ampliado (REC-2026-04-06-006, 2026-05-11): cobre variacoes da
    # Gabriella e Marcus em sessoes high-cost (vinculacao, conciliacao, match,
    # consolidacao). Skill-set: validacao-nf-po, conciliando-odoo-po. Acao
    # repetitiva e estruturada — nao requer Opus.
    # Fix 2026-05-11 (code-review): `consolidar` sem `?` para nao matchear
    # `consolida` (3a pessoa, "o sistema consolida o PO?" eh pergunta diagnostica
    # que precisa Opus). Mesmo principio para `conciliar`, `vincular`, `validar`,
    # `verificar` — todos requerem infinitivo completo.
    (
        re.compile(
            r"\b("
            r"match\s+(da\s+)?nf\s+\S+\s+(com|x)\s+po"
            r"|conciliar\s+(o\s+)?po\s+\S+"
            r"|consolidar\s+(o\s+)?po\b"
            r"|vincular\s+(o\s+)?po\s+\S+"
            r"|split\s+(do\s+)?po\b"
            r"|validar\s+(o\s+)?nf\s+\S+\s+x?\s*po"
            r"|verificar\s+(o\s+)?match\s+nf"
            r")\b",
            re.IGNORECASE,
        ),
        "padrao_nf_po_ampliado",
    ),
    # Atualizar baseline (REC-2026-05-05-001, 2026-05-11): pattern persistente
    # de Marcus + 1 outro user — 15 reps em 30d. Skill: gerando-baseline-conciliacao.
    # Sonnet executa em 1 turn pequeno (~$0.20 vs $1+ Opus).
    (
        re.compile(
            r"\b(atualizar?|gerar?|rodar?)\s+(o\s+)?baseline\b",
            re.IGNORECASE,
        ),
        "atualizar_baseline",
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
    # ───────────── FASE 2 (plano 2026-06-06-reducao-custo-agente-fast-path) ─────────
    # Downgrade Opus->Sonnet de CONSULTAS read-only + cotacao + CarVia. Decisao do
    # Rafael: "Tudo Sonnet" (conservador, sem Haiku). Regex ancorados nos _TEMPLATES
    # ja testados de scripts/audits/session_automation_audit.py (T2.1), porem mais
    # conservadores no routing. NAO inclui faturamento (SEFAZ, irreversivel) nem
    # financeiro (julgamento) — T2.3. 'saldo' isolado foi REMOVIDO de consulta_estoque
    # (ambiguo com saldo financeiro). conversa_analise (default) permanece Opus.
    (
        re.compile(
            r"recalcul\w*.*frete|frete.*(m[íi]n|min)\.?\s*peso|"
            r"atualizar.*embarque.*carvia|embarque.*carvia.*frete",
            re.IGNORECASE,
        ),
        "recalculo_frete_carvia",
    ),
    (
        re.compile(
            r"foi entregue|\bentregue\b|que dia.*(embarc|fatur)|\bembarcou\b|"
            r"cad[êe]\w*\s+(o |a |os |as |meu |minha |esse |essa )?(pedido|entrega|nf|nota|carga|merc)|"
            r"\bstatus\b|\brastre|\bcanhoto\b|onde\s+est\w+.*(pedido|nf|nota|entrega|carga)|"
            r"quando\s+(foi\s+)?(entreg|fatur|embarc)|j[áa]\s+(foi\s+)?(entreg|fatur)",
            re.IGNORECASE,
        ),
        "monitoramento_entrega",
    ),
    (
        re.compile(
            r"cota[çc][ãa]o|quanto\s+(custa|sai|fica|vai|é|e)\b.*frete|"
            r"\bfrete\s+(para|pra|de\s)|valor\s+do\s+frete|pre[çc]o\s+do\s+frete|\bfrete\s+pra\b",
            re.IGNORECASE,
        ),
        "cotacao",
    ),
    (
        re.compile(
            r"quanto\s+(tem|temos|de)\b|estoque\s+d|tem\s+em\s+estoque|disponibilidade",
            re.IGNORECASE,
        ),
        "consulta_estoque",
    ),
    (
        re.compile(
            r"movimenta[çc][ãa]o\b|movimenta[çc][õo]es\b|"
            r"validade\s+(do\s+|de\s+)?lote|hist[óo]rico.*lote",
            re.IGNORECASE,
        ),
        "consulta_movimentacao",
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
        ...     "claude-opus-4-8",
        ...     "claude-sonnet-5",
        ... )
        ('claude-sonnet-5', 'padrao_nf_po')
    """
    if not prompt or not prompt.strip():
        return default_model, "empty"

    stripped = prompt.strip()
    word_count = len(stripped.split())

    # Guard de complexidade (2026-05-11 code-review): patterns usam .search(),
    # entao prompts longos podem casar substring inocente. Ex.: "match da nf X
    # com PO mas considerando lote split, verificar premissas, validar formula"
    # contem "match da nf X com PO" mas o todo eh complexo demais para Sonnet.
    # Acima de 15 palavras, default para Opus mesmo se pattern matchar.
    if word_count > 15:
        return default_model, "prompt_complexo"

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


def pick_warm_model(session_model: str | None, user_model: str | None) -> str | None:
    """
    Modelo do turno em sessao WEB "quente" (client reutilizado): a config do
    usuario PERSISTE pela sessao.

    Regra (diretriz Rafael, bug 2026-06-15): o modelo e decidido 1x por sessao.
    Em sessao quente NAO se aplica smart routing — so troca se o usuario alterou
    EXPLICITAMENTE o modelo no seletor (aí custa cache MODEL-SCOPED, mas e
    consciente). Sem alteracao, mantem o modelo com que a sessao roda.

    Antes (bug): o routing rebaixava Opus->Sonnet em follow-ups curtos
    ("deu certo?") mid-sessao, matando o cache e fazendo o Sonnet rebaixado
    responder sobre a propria troca de modelo em vez da tarefa. Capacidade extra
    mid-sessao = DELEGAR a subagente, nao trocar o modelo do loop principal.

    Args:
        session_model: modelo com que a sessao roda (existing.model do pool).
        user_model: modelo pedido pelo usuario no request (config do seletor;
            None = nao informado).

    Returns:
        Modelo a usar no turno (user_model se troca explicita, senao session_model).
    """
    if user_model and user_model != session_model:
        return user_model
    return session_model


def should_switch_model(requested_model: str | None, session_model: str | None) -> bool:
    """
    Decide se o client deve chamar set_model (troca real de modelo mid-sessao).

    So troca quando o modelo pedido difere do atual da sessao — evita o churn
    redundante que invalidaria o cache MODEL-SCOPED a toa. Como o caller nunca
    rebaixa em sessao quente (pick_warm_model), so a troca EXPLICITA do usuario
    chega aqui como diff real.

    Args:
        requested_model: modelo resolvido para este turno.
        session_model: modelo atual do client da sessao (existing.model).

    Returns:
        True se deve trocar (set_model + atualizar existing.model).
    """
    return bool(requested_model) and requested_model != session_model


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
