"""
Hook closures do AgentClient para o Claude Agent SDK.

8 hooks organizados numa factory function build_hooks() que retorna
o dict hooks para ClaudeAgentOptions.

Extraido de client.py em 2026-04-04.
"""
import logging
from typing import Optional

from app.utils.timezone import agora_utc_naive
from ..config.feature_flags import USE_SUBAGENT_COST_GRANULAR

logger = logging.getLogger('sistema_fretes')

# ── Fase 3.5: HARD enforcement de invariantes duros formalizados (PreToolUse) ──
import time as _enf_time
from threading import Lock as _EnfLock

_ENFORCE_CACHE: dict = {}            # {(user_id, time_bucket): [(token, rule_path), ...]}
_ENFORCE_CACHE_LOCK = _EnfLock()
# TTL 300s (era 30s): com I4 default-ON, cada cache-miss roda no event loop COMPARTILHADO
# dos streams; regra dura nova passa a valer em <=5min — trade-off aceito (code review I4).
_ENFORCE_TTL_SECONDS = 300

# Singleton lazy do app Flask para o caminho SEM context (thread do _sdk_loop):
# create_app() custa ~1,0-1,3s e congelava todos os streams a cada cache-miss.
# 1x por processo; protegido por lock proprio (corrida criaria 2 apps, um vazaria).
_ENFORCE_FLASK_APP = None
_ENFORCE_APP_LOCK = _EnfLock()


def _get_enforce_flask_app():
    global _ENFORCE_FLASK_APP
    if _ENFORCE_FLASK_APP is None:
        with _ENFORCE_APP_LOCK:
            if _ENFORCE_FLASK_APP is None:
                from app import create_app
                _ENFORCE_FLASK_APP = create_app()
    return _ENFORCE_FLASK_APP


def _enforce_decision(directives, tool_input_str):
    """PURO/testavel: retorna (token, rule_path) do 1o token proibido encontrado no input
    serializado (substring case-insensitive), ou None. NUNCA usa texto livre — so o token
    EXPLICITO declarado por 'ENFORCE_DENY_SUBSTR:' em uma regra dura."""
    s = (tool_input_str or '').lower()
    for token, rule_path in (directives or []):
        if token and token.lower() in s:
            return (token, rule_path)
    return None


def _load_enforce_directives(user_id: int):
    """Carrega (cacheado, TTL 30s) as diretivas DENY formalizaveis das regras duras do usuario.

    Convencao: uma regra 'mandatory' que carrega 'ENFORCE_DENY_SUBSTR: <token>' no content vira
    um invariante DURO. So invariantes EXPLICITAMENTE formalizados (curadoria humana) entram;
    o error_signature (slug de metrica) NAO e usado. Retorna [(token, rule_path), ...]. Fail-open
    (qualquer erro -> []). Roda fora do Flask context (padrao memory_injection: probe + create_app).
    """
    bucket = int(_enf_time.time() // _ENFORCE_TTL_SECONDS)
    key = (user_id, bucket)
    with _ENFORCE_CACHE_LOCK:
        if key in _ENFORCE_CACHE:
            return _ENFORCE_CACHE[key]
    directives = []
    try:
        from contextlib import nullcontext
        try:
            from flask import current_app as _app_probe
            _ = _app_probe.name
            _ctx = nullcontext()
        except RuntimeError:
            _ctx = _get_enforce_flask_app().app_context()
        with _ctx:
            from ..models import AgentMemory
            import re as _re
            rules = AgentMemory.query.filter(
                AgentMemory.user_id.in_([user_id, 0]),
                AgentMemory.is_directory == False,  # noqa: E712
                AgentMemory.is_cold == False,  # noqa: E712
                AgentMemory.priority == 'mandatory',
                AgentMemory.content.ilike('%ENFORCE_DENY_SUBSTR%'),
            ).limit(50).all()
            for r in rules:
                for m in _re.finditer(r'ENFORCE_DENY_SUBSTR:\s*(.+)', r.content or ''):
                    token = m.group(1).strip()
                    if token:
                        directives.append((token, r.path))
    except Exception as e:
        logger.debug(f"[ENFORCE] load directives falhou (fail-open): {e}")
        directives = []
    with _ENFORCE_CACHE_LOCK:
        # prune buckets antigos (cache nao cresce indefinidamente)
        for k in list(_ENFORCE_CACHE.keys()):
            if k[1] != bucket:
                del _ENFORCE_CACHE[k]
        _ENFORCE_CACHE[key] = directives
    return directives


def _compose_hook_context(
    *,
    resume_fallback: str = '',
    session_context: str = '',
    main_context: str = '',
    correction_hint: str = '',
    debug_context: str = '',
    sql_admin_context: str = '',
    skill_hints: str = '',
    world_model: str = '',
    tail_context: str = '',
) -> str:
    """PURO/testavel — montagem do additionalContext na ORDEM-ALVO do PAD-CTX
    (F4.4, tabela "Hook dinamico — layout, orcamento e ordem"):

    resume_fallback(1) -> session_context(2) -> main_context(3-9: user_rules,
    user_memories, directives, briefing, routing) -> correction_hint(10) ->
    debug/sql_admin(11) -> [skill_hints/world_model: flag-gated, OFF por
    default — decisao R-1] -> tail_context(12-13: recent_sessions +
    pendencias_acumuladas por ULTIMO, coladas a mensagem do usuario).
    """
    return (
        resume_fallback + session_context + main_context + correction_hint
        + debug_context + sql_admin_context + skill_hints + world_model
        + tail_context
    )


def _build_resume_fallback_notice(reason: str) -> str:
    """PURO/testavel — notice que antecede o historico injetado no 1o turno.

    'rotated': sessao ROTACIONADA por idle (controle de custo) — o usuario ve
    a MESMA conversa na UI e espera continuidade total (caso conversa-nacom
    2026-06-10). 'resume_failed' (default): resume do SDK falhou (R-CLI-CRASH).
    """
    aviso_anexos = (
        " ATENÇÃO a ARQUIVOS: anexos enviados antes (PDF, planilha .xlsx, XML, "
        "etc.) podem ter saído do /tmp nesta sessão. ANTES de pedir reenvio, tente "
        "recuperá-los: chame `list_session_uploads` para ver os anexos recentes do "
        "usuário e `recover_upload` (com o file_id retornado) para trazer cada um de "
        "volta para a sessão atual. Se a tarefa depende de um anexo que "
        "`list_session_uploads` NÃO encontrar, AVISE o usuário proativamente e peça "
        "o reenvio de TODOS os arquivos necessários de uma vez ANTES de executar "
        "qualquer passo — não tente prosseguir e descobrir o sumiço no meio do fluxo."
    )
    if reason == 'rotated':
        return (
            "IMPORTANTE: Esta conversa CONTINUA uma sessão anterior do mesmo "
            "usuário (rotacionada por inatividade, por controle de custo). "
            "O usuário vê a conversa antiga na tela e espera continuidade "
            "total — NÃO trate como assunto novo. Abaixo: resumo e últimas "
            "mensagens da sessão original. Se algo essencial não estiver "
            "aqui, pergunte objetivamente em vez de presumir."
            + aviso_anexos
        )
    return (
        "IMPORTANTE: A sessão anterior não pôde ser restaurada via resume. "
        "Abaixo está o histórico recente da conversa extraído do banco de dados. "
        "Use este contexto para continuar a conversa de forma coerente. "
        "O usuário pode não saber que o contexto foi perdido."
        + aviso_anexos
    )


def _build_skill_pretool_context(user_id: int, skill: str) -> Optional[str]:
    """Contexto pre-execucao da Skill tool (PreToolUse) — 2 fontes best-effort:

    1. Lembrete aprendido do usuario (Task 10 Fase 1 Skill Effectiveness),
       flag-gated por AGENT_SKILL_EVAL.
    2. F4.5 PAD-CTX — excecao condicional: improvement_response de skill_bug
       ATIVO volta ao contexto SOMENTE no turno que USA a skill afetada
       (fora do boot — relocada do intersession_briefing na F4.1). Sem gate
       de flag: query leve, so dispara com a Skill tool e response existente.
    """
    parts = []
    try:
        from ..config.feature_flags import AGENT_SKILL_EVAL
        if AGENT_SKILL_EVAL:
            from ..config.permissions import get_current_session_id
            from .memory_injection import get_skill_reminders_for_session
            sid = get_current_session_id() or ''
            rem = get_skill_reminders_for_session(user_id, sid).get(skill)
            if rem:
                parts.append(
                    f"LEMBRETE para a skill '{skill}' (aprendido de interacoes "
                    f"anteriores deste usuario):\n{rem}"
                )
    except Exception as e:
        logger.debug(f"[SKILL_EVAL] inject reminder falhou (ignorado): {e}")

    try:
        from ..services.intersession_briefing import get_skill_bug_responses_for_skill
        bug_responses = get_skill_bug_responses_for_skill(skill)
        if bug_responses:
            parts.append(
                f"AVISO skill_bug para '{skill}' (resposta do Claude Code ao "
                f"dialogo de melhoria — avalie nesta execucao se o problema "
                f"foi resolvido):\n{bug_responses}"
            )
    except Exception as e:
        logger.debug(f"[SKILL_BUG] inject response falhou (ignorado): {e}")

    return "\n".join(parts) if parts else None


def build_hooks(
    user_id: int,
    user_name: str,
    tool_failure_counts: dict,
    get_last_thinking: callable,
    get_model_name: callable,
    set_injected_ids: callable,
    resume_state: dict = None,
    our_session_id: str = None,
) -> dict:
    """Factory que cria hooks para ClaudeAgentOptions.

    Args:
        user_id: ID do usuario
        user_name: Nome do usuario
        tool_failure_counts: dict mutavel (ref ao self._tool_failure_counts)
        get_last_thinking: getter para self._last_thinking_content
        get_model_name: getter para str(self.settings.model)
        set_injected_ids: setter para self._last_injected_memory_ids
        resume_state: Dict mutavel compartilhado com o stream.
            Chaves: 'failed' (bool), 'fallback' (str XML com mensagens JSONB).
            Quando resume falha, stream seta failed=True. Hook injeta fallback.
        our_session_id: Nosso UUID de sessao (pool key). Fase B teams-melhorias:
            o client do pool e reusado SEM reaplicar hooks, entao user_id/
            user_name da closure congelam no falante que CONECTOU. Os hooks
            resolvem o falante ATUAL via turn_context_registry (fallback =
            closure; web 1:1 inalterado).

    Returns:
        Dict formatado para options_dict["hooks"]
    """
    if resume_state is None:
        resume_state = {'failed': False, 'fallback': None}
    from claude_agent_sdk import (
        HookMatcher, PreToolUseHookInput, PostToolUseHookInput,
        PostToolUseFailureHookInput,
        PreCompactHookInput, StopHookInput, UserPromptSubmitHookInput,
        HookContext,
    )

    from .stream_parser import _classify_tool_error
    from .memory_injection import _load_user_memories_for_context
    from ._sanitization import xml_escape
    from .turn_context_registry import resolve_turn_user

    def _turn_user():
        """Falante do turno ATUAL (registry) com fallback para a closure."""
        return resolve_turn_user(our_session_id, user_id, user_name)

    async def _keep_stream_open(hook_input: PreToolUseHookInput, signal, context: HookContext):
        """Hook OBRIGATÓRIO: mantém stream aberto para can_use_tool funcionar.

        FONTE: https://platform.claude.com/docs/en/agent-sdk/user-input
        'In Python, can_use_tool requires streaming mode and a PreToolUse hook
        that returns {"continue_": True} to keep the stream open. Without this
        hook, the stream closes before the permission callback can be invoked.'

        Sem este hook, AskUserQuestion e ExitPlanMode falham com 'stream closed'.

        SDK 0.1.29+: PreToolUseHookInput agora inclui tool_use_id e suporta
        additionalContext no output para injetar contexto antes da execução.
        """
        # Contexto adicional pré-execução para tools de consulta
        tool_name = hook_input.get('tool_name', '')
        additional = None

        # Injetar lembrete de campos corretos antes de queries SQL
        if tool_name == 'mcp__sql__consultar_sql':
            additional = (
                "CAMPOS CORRETOS: "
                "carteira_principal: cnpj_cpf/raz_social (nao cnpj_cliente/nome_cliente), "
                "qtd_saldo_produto_pedido (nao qtd_saldo), cod_uf (nao uf/estado_destino), "
                "nao tem codigo_ibge (usar nome_cidade+cod_uf). "
                "faturamento_produto: cnpj_cliente/nome_cliente (nao cnpj_cpf/razao_social). "
                "despesas_extras: valor_despesa (nao valor), criado_em (nao data_lancamento). "
                "separacao: cnpj_cpf, raz_social_red, codigo_ibge, uf_normalizada. "
                "tabela fretes: transportadora_id (JOIN transportadoras.razao_social, nao nome_transportadora). "
                "FIDELIDADE: valores EXATOS do resultado, nao arredondar nem inventar dados."
            )
        elif tool_name == 'Bash' and 'python' in str(hook_input.get('tool_input', '')).lower():
            additional = (
                "Se o script usa campos de tabela, valide nomes via consultar_schema ANTES. "
                "Campos comuns errados: qtd_saldo vs qtd_saldo_produto_pedido, "
                "codigo_produto vs cod_produto."
            )
        elif tool_name == 'Skill':
            # Lembrete aprendido (Task 10, flag AGENT_SKILL_EVAL) + aviso de
            # skill_bug respondido (F4.5 PAD-CTX — excecao condicional).
            # Best-effort: NUNCA quebra a tool.
            try:
                tinput = hook_input.get('tool_input', {})
                skill = tinput.get('skill', '') if isinstance(tinput, dict) else ''
                if skill:
                    additional = _build_skill_pretool_context(_turn_user()[0], skill)
            except Exception as e:
                logger.debug(f"[SKILL_CTX] pretool context falhou (ignorado): {e}")

        # B3: Pre-mortem seletivo para acoes irreversiveis
        # Dynamis/energeia: antes de atualizar (energeia), mapear modos de falha (dynamis)
        from ..config.permissions import _classify_destructive_action
        from ..config.feature_flags import USE_REVERSIBILITY_CHECK

        if USE_REVERSIBILITY_CHECK:
            tool_input_data = hook_input.get('tool_input', {})
            if isinstance(tool_input_data, str):
                tool_input_data = {}
            destructive = _classify_destructive_action(tool_name, tool_input_data)
            if destructive and destructive.get('reversibility') == 'irreversible':
                pre_mortem = (
                    f"ACAO IRREVERSIVEL DETECTADA: {destructive['description']}. "
                    "ANTES de executar, liste 2 consequencias negativas possiveis "
                    "desta acao e como cada uma poderia ser revertida ou mitigada. "
                    "Se nao houver como reverter, confirme com o usuario antes."
                )
                additional = f"{additional}\n{pre_mortem}" if additional else pre_mortem

        # Prefixo de ENV no subprocess Bash (race-free vs os.environ multi-worker —
        # usa updatedInput, isolado por tool call). DOIS propositos:
        #  1) NACOM_QUIET_BOOT=1 (BUG #1, 2026-06-08): silencia os logs de boot do
        #     `import app` nos scripts CLI de skill -> stdout/stderr limpos no agente.
        #     SEMPRE aplicado (independente de flags).
        #  2) AGENT_SESSION_ID/... (audit hook 2026-05-28): propaga session_id p/
        #     correlacao em operacao_odoo_auditoria. Condicional a AGENT_ODOO_AUDIT_HOOK.
        #     Ver app/utils/odoo_audit_helpers.py.
        updated_input = None
        if tool_name == 'Bash':
            try:
                import shlex
                tool_input_data = hook_input.get('tool_input', {})
                if isinstance(tool_input_data, dict):
                    command_orig = tool_input_data.get('command', '')
                    if command_orig and isinstance(command_orig, str):
                        prefix = 'export NACOM_QUIET_BOOT=1; '
                        from ..config.feature_flags import USE_ODOO_AUDIT_HOOK
                        if USE_ODOO_AUDIT_HOOK:
                            from ..config.permissions import get_current_session_id
                            current_sid = get_current_session_id() or 'noctx'
                            tool_use_id = hook_input.get('tool_use_id', '') or 'notui'
                            agent_type_atual = hook_input.get('agent_type', '') or 'main'
                            prefix += (
                                f'export AGENT_SESSION_ID={shlex.quote(current_sid)}; '
                                f'export AGENT_TOOL_USE_ID={shlex.quote(tool_use_id)}; '
                                f'export AGENT_TYPE={shlex.quote(agent_type_atual)}; '
                                f'export AGENT_USER_NAME={shlex.quote(_turn_user()[1] or str(_turn_user()[0]))}; '
                            )
                        updated_input = {**tool_input_data, 'command': prefix + command_orig}
            except Exception as e:
                # Hook NUNCA quebra tool — log e segue.
                logger.debug(f'[bash_prefix_propagacao] {e}')

        if additional or updated_input:
            output = {
                "continue_": True,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                },
            }
            if additional:
                output["hookSpecificOutput"]["additionalContext"] = additional
            if updated_input:
                output["hookSpecificOutput"]["updatedInput"] = updated_input
            return output

        return {"continue_": True}

    async def _enforce_mandatory_invariants(hook_input: PreToolUseHookInput, signal, context: HookContext):
        """Fase 3.5 — HARD enforcement (PreToolUse) de invariantes DUROS formalizados.

        Gated por AGENT_MANDATORY_HARD_ENFORCE (default LIGADO desde a estrategia I4,
        2026-06-12 — no-op ate a 1a regra dura declarar 'ENFORCE_DENY_SUBSTR:'; rollback:
        env=false). Bloqueia uma tool call cujo input serializado contenha um token
        proibido declarado por uma regra dura via 'ENFORCE_DENY_SUBSTR: <token>'. FAIL-OPEN:
        qualquer erro -> permite (nunca quebra o fluxo). NUNCA bloqueia por texto livre.
        """
        try:
            from ..config.feature_flags import USE_MANDATORY_HARD_ENFORCE
            if not USE_MANDATORY_HARD_ENFORCE:
                return {"continue_": True}
            enforce_uid = _turn_user()[0]
            directives = _load_enforce_directives(enforce_uid)
            if not directives:
                # caminho comum (0 regras): sem serializar tool_input (O(input) evitado)
                return {"continue_": True}
            hit = _enforce_decision(directives, str(hook_input.get('tool_input', '')))
            if hit:
                token, rule_path = hit
                logger.warning(
                    f"[ENFORCE] BLOQUEADO: input da tool contem token proibido '{token}' "
                    f"(regra dura {rule_path}, user={enforce_uid})"
                )
                return {
                    "continue_": True,
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"[INVARIANTE] Regra dura do usuario proibe '{token}' "
                            f"(fonte: {rule_path}). Ajuste a operacao para nao usar esse padrao."
                        ),
                    },
                }
        except Exception as e:
            logger.debug(f"[ENFORCE] hook falhou (fail-open): {e}")
        return {"continue_": True}

    async def _audit_post_tool_use(hook_input: PostToolUseHookInput, signal, context: HookContext):
        """Registra execução de tools para auditoria.

        SDK 0.1.29+: PostToolUseHookInput agora inclui tool_use_id
        para correlação precisa tool_call → tool_result.
        SDK 0.1.46+: agent_id e agent_type para distinguir subagentes.

        B2: Persiste thinking block quando acao e destrutiva (auditoria de deliberacao).
        """
        try:
            tool_name = hook_input.get('tool_name', 'unknown')
            tool_use_id = hook_input.get('tool_use_id', '')
            tool_input_str = str(hook_input.get('tool_input', ''))[:200]
            # SDK 0.1.46+: identificar qual agente executou a tool
            agent_id = hook_input.get('agent_id', '')
            agent_type = hook_input.get('agent_type', '')
            logger.info(
                f"[AUDIT] PostToolUse: {tool_name} "
                f"| id={tool_use_id[:12] if tool_use_id else 'N/A'} "
                f"| agent={agent_type or 'main'}:{agent_id[:12] if agent_id else 'N/A'} "
                f"| input: {tool_input_str}"
            )

            # B2: Persistir deliberacao para acoes destrutivas
            last_thinking = get_last_thinking()
            if last_thinking:
                from ..config.permissions import _classify_destructive_action
                tool_input_data = hook_input.get('tool_input', {})
                if isinstance(tool_input_data, str):
                    tool_input_data = {}
                destructive = _classify_destructive_action(tool_name, tool_input_data)
                if destructive and destructive.get('reversibility') in ('irreversible', 'hard_to_reverse'):
                    log_entry = {
                        'timestamp': agora_utc_naive().isoformat(),
                        'action': destructive['action'],
                        'description': destructive['description'],
                        'reversibility': destructive['reversibility'],
                        'tool_name': tool_name,
                        'thinking_excerpt': last_thinking[:2000],
                    }
                    logger.info(
                        f"[DELIBERATION] Thinking capturado para acao {destructive['action']} "
                        f"({len(last_thinking)} chars)"
                    )
                    # Salvar no session.data via ContextVar de session_id
                    try:
                        from ..config.permissions import get_current_session_id
                        current_sid = get_current_session_id()
                        if current_sid:
                            from ..models import AgentSession
                            from app import db
                            session_obj = AgentSession.query.filter_by(
                                session_id=current_sid
                            ).first()
                            if session_obj and session_obj.data:
                                if 'deliberation_log' not in session_obj.data:
                                    session_obj.data['deliberation_log'] = []
                                session_obj.data['deliberation_log'].append(log_entry)
                                from sqlalchemy.orm.attributes import flag_modified
                                flag_modified(session_obj, 'data')
                                db.session.commit()
                    except Exception as db_err:
                        logger.debug(f"[DELIBERATION] Erro ao persistir: {db_err}")

            return {}
        except Exception as e:
            logger.debug(f"[HOOK:PostToolUse] Suppressed (stream likely closed): {e}")
            return {}

    async def _post_tool_use_failure(
        hook_input: PostToolUseFailureHookInput, signal, context: HookContext
    ):
        """Hook de falha de tool: loga erro e fornece contexto corretivo ao modelo.

        Dispara quando qualquer tool falha. Categoriza o erro e opcionalmente
        retorna additionalContext para guiar o modelo na recuperação.

        Sempre ativo (não depende de feature flag) — custo zero, benefício
        de logging estruturado + contexto corretivo.
        """
        try:
            tool_name = hook_input.get('tool_name', 'unknown')
            tool_input_data = hook_input.get('tool_input', {})
            error_msg = hook_input.get('error', 'unknown error')
            is_interrupt = hook_input.get('is_interrupt', False)

            # Interrupt do usuário — não é erro real
            log_prefix = "[HOOK:PostToolUseFailure]"
            if is_interrupt:
                logger.info(f"{log_prefix} INTERRUPT: {tool_name}")
                return {}

            logger.warning(
                f"{log_prefix} {tool_name} falhou | "
                f"error={error_msg[:300]} | "
                f"input={str(tool_input_data)[:200]}"
            )

            # Classificação por tabela de lookup (ERROR_CLASSIFICATIONS)
            additional = _classify_tool_error(tool_name, error_msg)

            # Fallback: detecção de erro repetido na sessão
            if not additional:
                count = tool_failure_counts.get(tool_name, 0) + 1
                tool_failure_counts[tool_name] = count
                if count >= 2:
                    additional = (
                        f"{tool_name} já falhou {count}x nesta sessão. "
                        "Tente abordagem diferente ou use outra tool."
                    )
            else:
                # Incrementar contador mesmo quando classificação é encontrada
                tool_failure_counts[tool_name] = (
                    tool_failure_counts.get(tool_name, 0) + 1
                )

            if additional:
                logger.info(f"{log_prefix} Correção injetada: {additional[:100]}")
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUseFailure",
                        "additionalContext": additional,
                    }
                }

            return {}
        except Exception as e:
            logger.debug(f"[HOOK:PostToolUseFailure] Suppressed (stream likely closed): {e}")
            return {}

    async def _pre_compact_hook(hook_input: PreCompactHookInput, signal, context: HookContext):
        """Antes de compactação, instrui modelo a salvar contexto logístico estruturado.

        P0-1: Melhoria do Pre-Compaction Hook.
        Com USE_STRUCTURED_COMPACTION=true (default), instrui o modelo a salvar
        pedidos, decisões, tarefas e contexto em formato XML estruturado.
        Sem a flag, mantém comportamento genérico original como fallback.
        """
        try:
            from ..config.feature_flags import USE_STRUCTURED_COMPACTION

            # B3: Log enriquecido de compactação
            sdk_session = hook_input.get('session_id', 'unknown')
            logger.info(
                f"[COMPACTION] session={sdk_session[:12] if sdk_session != 'unknown' else 'unknown'} | "
                f"reason=context_window_full | "
                f"structured={USE_STRUCTURED_COMPACTION}"
            )

            if not USE_STRUCTURED_COMPACTION:
                return {
                    "custom_instructions": (
                        "O contexto será compactado agora. ANTES de continuar, "
                        "salve informações críticas usando mcp__memory__save_memory "
                        "em /memories/context/session_notes.xml. "
                        "Após compactação, consulte suas memórias para recuperar estado."
                    )
                }

            return {
                "custom_instructions": (
                    "⚠️ COMPACTAÇÃO IMINENTE — O contexto será reduzido agora.\n\n"
                    "ANTES de continuar, salve o estado da conversa usando "
                    "mcp__memory__save_memory no path /memories/context/session_notes.xml.\n\n"
                    "Use EXATAMENTE este formato XML:\n"
                    "```xml\n"
                    "<session_context>\n"
                    "  <pedidos_em_discussao>\n"
                    "    <!-- Liste TODOS os pedidos mencionados com código VCD/VFB, cliente e valor -->\n"
                    "    <pedido codigo=\"VCDxxx\" cliente=\"Nome\" valor=\"R$ X.XXX,XX\" status=\"pendente|parcial|concluido\" />\n"
                    "  </pedidos_em_discussao>\n"
                    "  <decisoes_tomadas>\n"
                    "    <!-- Decisões já confirmadas pelo usuário -->\n"
                    "    <decisao>Descrição da decisão</decisao>\n"
                    "  </decisoes_tomadas>\n"
                    "  <tarefas_pendentes>\n"
                    "    <!-- O que falta fazer nesta conversa -->\n"
                    "    <tarefa>Descrição</tarefa>\n"
                    "  </tarefas_pendentes>\n"
                    "  <dados_consultados>\n"
                    "    <!-- Últimas consultas SQL ou resultados relevantes -->\n"
                    "    <consulta tipo=\"sql|estoque|separacao\">Resumo do resultado</consulta>\n"
                    "  </dados_consultados>\n"
                    "  <contexto_usuario>\n"
                    "    <!-- Preferências e contexto mencionados -->\n"
                    "    <nota>Informação relevante sobre o usuário</nota>\n"
                    "  </contexto_usuario>\n"
                    "</session_context>\n"
                    "```\n\n"
                    "PRIORIZACAO (essencial → acidental):\n"
                    "1. decisoes_tomadas — ESSENCIAL: se perdidas, voce contradira o usuario\n"
                    "2. tarefas_pendentes — ESSENCIAL: se perdidas, trabalho fica incompleto\n"
                    "3. pedidos_em_discussao — ESSENCIAL: contexto de negocio ativo\n"
                    "4. contexto_usuario — MODERADO: preferencias e perfil\n"
                    "5. dados_consultados — ACIDENTAL: podem ser re-consultados\n"
                    "Se espaco for limitado, OMITA dados_consultados antes de omitir decisoes.\n\n"
                    "APÓS salvar, consulte /memories/context/session_notes.xml para "
                    "recuperar o estado e continue a conversa normalmente."
                )
            }
        except Exception as e:
            logger.debug(f"[HOOK:PreCompact] Suppressed (stream likely closed): {e}")
            return {}

    # ─── P3-2: Stop Hook — loga métricas finais da sessão ───
    async def _stop_hook(hook_input: StopHookInput, signal, context: HookContext):
        """Hook de encerramento: loga métricas finais da sessão.

        P3-2: Expanded Hooks.
        Executado pelo SDK quando a sessão termina (após ResultMessage).
        Loga: session_id, duração, indicador de stop_hook_active.
        CLI 2.1.47+: inclui last_assistant_message para audit trail.

        Quando USE_EXPANDED_HOOKS=false, retorna {} silenciosamente (noop).
        """
        try:
            from ..config.feature_flags import USE_EXPANDED_HOOKS

            if not USE_EXPANDED_HOOKS:
                return {}

            sdk_sid = hook_input.get('session_id', 'unknown')
            stop_active = hook_input.get('stop_hook_active', False)

            # CLI 2.1.47+: last_assistant_message disponível em runtime
            # (não tipado no SDK 0.1.39, mas enviado pelo CLI como campo extra)
            last_msg = hook_input.get('last_assistant_message', None)
            last_msg_preview = ""
            if last_msg and isinstance(last_msg, str):
                last_msg_preview = f" | last_msg={last_msg[:80]}..."

            logger.info(
                f"[HOOK:Stop] Sessão encerrada: "
                f"session={sdk_sid[:12]}... | "
                f"stop_hook_active={stop_active}"
                f"{last_msg_preview}"
            )

            # B4: Log de stats da sessão para análise futura
            # Nota: session_id (nosso UUID) não está no escopo de _build_options.
            # Stats são logados via [MEMORY_INJECT] a cada turno e podem ser
            # agregados via parsing de logs.
            logger.info(
                f"[HOOK:Stop] user_id={user_id or 'None'} | "
                f"sdk_session={sdk_sid[:12] if sdk_sid != 'unknown' else 'unknown'}"
            )

            # P2 — Arquivar subagents + findings para S3 (best-effort)
            # GOTCHA 2026-04-17: archive_session_to_s3 usa current_app e
            # db.session. Hook async roda FORA do Flask app context.
            # Mesmo padrao que SubagentStop aplicou.
            try:
                import os
                if os.environ.get('AGENT_SESSION_ARCHIVE_S3', 'true').lower() == 'true':
                    from contextlib import nullcontext
                    from .session_archive import archive_session_to_s3
                    session_id_stop = hook_input.get('session_id', '')
                    if session_id_stop:
                        try:
                            from flask import current_app as _app_probe
                            _ = _app_probe.name
                            _ctx = nullcontext()
                        except RuntimeError:
                            from app import create_app as _create_app
                            _ctx = _create_app().app_context()
                        with _ctx:
                            archive_session_to_s3(session_id_stop)
            except Exception as arch_err:
                logger.warning(
                    f"[HOOK:Stop] archive S3 falhou: "
                    f"{type(arch_err).__name__}: {arch_err}"
                )

            return {}
        except Exception as e:
            logger.debug(f"[HOOK:Stop] Suppressed (stream likely closed): {e}")
            return {}

    # ─── SubagentStart Hook — notificacao instantanea ao frontend ───
    async def _subagent_start_hook(hook_input, signal, context: HookContext):
        """Hook de inicio de subagente: emite SSE event ANTES do subagente processar.

        SDK 0.1.48+: SubagentStart dispara INSTANTANEAMENTE no spawn,
        antes mesmo do TaskStartedMessage (que e async e pode demorar).
        Permite ao frontend mostrar 'Delegando para analista-carteira...'
        imediatamente.

        FIX 2026-04-17: publicar `task_started` via pubsub com AGENT_ID (nao
        task_id). Testes em prod mostraram que o CLI bundled NAO emite
        TaskStartedMessage para subagents locais (definidos em
        `.claude/agents/*.md`) — apenas `Tool START: Grep/Read/Bash` da
        conversa interna. Resultado: linha "running" nunca era criada, e
        quando `subagent_summary` chegava com agent_id diferente do task_id,
        frontend caia em fallback (criar linha DONE orfa) — inconsistente.

        Publicar aqui usando o MESMO agent_id que o SubagentStop vai usar
        garante que o Map no frontend case (agent_id) tanto na start quanto
        na done, e a linha transiciona running→done corretamente.
        """
        try:
            agent_id = hook_input.get('agent_id', '')
            agent_type = hook_input.get('agent_type', '')
            session_id_local = hook_input.get('session_id', '')

            # SDK 0.1.52+: Registrar mapa agent_id → agent_type
            # para politicas de seguranca em can_use_tool()
            if agent_id and agent_type:
                from ..config.permissions import register_subagent
                register_subagent(agent_id, agent_type)

            logger.info(
                f"[HOOK:SubagentStart] "
                f"agent_type={agent_type} | "
                f"agent_id={agent_id[:12] if agent_id else 'N/A'} | "
                f"user_id={user_id or 'None'}"
            )

            # Publicar task_started no pubsub (FIX CLI nao emite
            # TaskStartedMessage para subagents locais)
            if session_id_local and agent_id:
                try:
                    import json as _json
                    import os as _os
                    import redis as _redis_lib
                    redis_url = _os.environ.get(
                        'REDIS_URL', 'redis://localhost:6379/0'
                    )
                    r = _redis_lib.from_url(redis_url)
                    channel = f'agent_sse:{session_id_local}'
                    buffer_key = f'agent_sse_buffer:{session_id_local}'
                    # Payload compativel com renderSubagentLineStart:
                    #   data.agent_id || data.task_id
                    #   data.agent_type || data.task_type || data.description
                    payload = _json.dumps({
                        'type': 'task_started',
                        'data': {
                            'agent_id': agent_id,
                            'task_id': agent_id,  # fallback compat
                            'agent_type': agent_type,
                            'task_type': 'subagent',
                            'description': agent_type,
                        },
                    })
                    n = r.publish(channel, payload)
                    try:
                        r.rpush(buffer_key, payload)
                        r.expire(buffer_key, 300)
                        r.ltrim(buffer_key, -20, -1)
                    except Exception:
                        pass
                    logger.info(
                        f"[HOOK:SubagentStart] task_started publicado "
                        f"channel={channel} agent_id={agent_id[:12]} "
                        f"subscribers={n}"
                    )
                except Exception as pub_err:
                    logger.warning(
                        f"[HOOK:SubagentStart] publish task_started falhou: "
                        f"{pub_err}"
                    )

            # BUG FIX 2026-05-26: NAO injetar additionalContext.
            #
            # Sintoma observado (sessao adcfe8d8 26/05): subagente
            # gestor-estoque-odoo (Opus 4.7) respondia em 1 turn, sem usar
            # nenhuma tool, com texto "Aguardando resultado do subagente X
            # conforme instrucao do SubagentStart hook" e end_turn.
            #
            # Causa raiz: o SDK injeta o `additionalContext` deste hook
            # tanto no contexto do PAI quanto no contexto do PROPRIO
            # SUBAGENTE recem-iniciado (como `hook_additional_context`
            # attachment). O texto "Subagente 'X' iniciado. Aguarde
            # resultado antes de responder ao usuario" eh ambiguo
            # gramaticalmente — o filho le como "(voce eh o) Subagente X,
            # aguarde resultado", obedece literalmente e termina sem
            # invocar nenhuma skill/tool.
            #
            # Solucao: remover o additionalContext. O pubsub `task_started`
            # acima ja notifica o frontend (proposito principal do hook).
            # O agente pai eh informado naturalmente quando o subagente
            # termina (TaskNotificationMessage + subagent_summary).
            return {}
        except Exception as e:
            logger.debug(f"[HOOK:SubagentStart] Suppressed: {e}")
            return {}

    # ─── SubagentStop Hook — metricas de subagente ao finalizar ───
    async def _subagent_stop_hook(hook_input, signal, context: HookContext):
        """Hook de fim de subagente: extrai custo e duracao do transcript.

        SDK 0.1.48+: SubagentStop dispara APOS o subagente terminar.
        Recebe agent_transcript_path — JSONL com todas as mensagens do
        subagente, incluindo ResultMessage com cost/usage.
        """
        try:
            agent_id = hook_input.get('agent_id', '')
            agent_type = hook_input.get('agent_type', '')
            transcript_path = hook_input.get('agent_transcript_path', '')
            session_id = hook_input.get('session_id', '')

            # SDK 0.1.52+: Limpar mapa agent_id → agent_type
            if agent_id:
                from ..config.permissions import unregister_subagent
                unregister_subagent(agent_id)

            # Extrair custo do transcript (ultima linha ResultMessage)
            cost_usd = None
            duration_ms = None
            num_turns = None
            stop_reason = ''
            last_result = None

            if transcript_path:
                try:
                    import json as _json
                    import os as _os
                    file_exists = _os.path.exists(transcript_path)
                    file_size = _os.path.getsize(transcript_path) if file_exists else 0
                    lines_read = 0
                    result_count = 0
                    with open(transcript_path, 'r') as f:
                        for line in f:
                            lines_read += 1
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                msg = _json.loads(line)
                                if msg.get('type') == 'result':
                                    last_result = msg
                                    result_count += 1
                            except _json.JSONDecodeError:
                                continue

                        if last_result:
                            cost_usd = last_result.get('total_cost_usd')
                            duration_ms = last_result.get('duration_ms')
                            num_turns = last_result.get('num_turns')
                            stop_reason = last_result.get('stop_reason', '')

                    logger.info(
                        f"[HOOK:SubagentStop] transcript_read "
                        f"path={transcript_path} exists={file_exists} "
                        f"size={file_size}B lines={lines_read} "
                        f"results={result_count} "
                        f"cost_usd={cost_usd} num_turns={num_turns}"
                    )
                except (OSError, IOError) as file_err:
                    logger.warning(
                        f"[HOOK:SubagentStop] Transcript inacessivel: "
                        f"path={transcript_path} err={file_err}"
                    )
            else:
                logger.warning(
                    f"[HOOK:SubagentStop] agent_transcript_path VAZIO no "
                    f"hook_input — keys={list(hook_input.keys())}"
                )

            logger.info(
                f"[HOOK:SubagentStop] "
                f"agent_type={agent_type} | "
                f"agent_id={agent_id[:12] if agent_id else 'N/A'} | "
                f"cost=${cost_usd or 0:.4f} | "
                f"duration={duration_ms or 0}ms | "
                f"turns={num_turns or 'N/A'} | "
                f"stop_reason={stop_reason or 'end_turn'} | "
                f"user_id={user_id or 'None'}"
            )

            # Registrar custo no cost_tracker
            if cost_usd and cost_usd > 0:
                try:
                    from .cost_tracker import cost_tracker
                    cost_tracker.record_cost(
                        message_id=f"subagent_{agent_id[:12] if agent_id else 'unknown'}",
                        input_tokens=0,  # Detalhes no log, aqui o total
                        output_tokens=0,
                        session_id=hook_input.get('session_id', ''),
                        user_id=user_id or 0,
                        tool_name=f"subagent:{agent_type}",
                    )
                    logger.debug(
                        f"[HOOK:SubagentStop] Custo registrado no cost_tracker: "
                        f"${cost_usd:.4f} ({agent_type})"
                    )
                except Exception as cost_err:
                    logger.debug(f"[HOOK:SubagentStop] cost_tracker falhou: {cost_err}")

            # #3 Cost granular — persiste em AgentSession.data (JSONB)
            # T5+T6 (2026-04-17): se last_result ausente (SDK 0.1.60 nao grava
            # type:'result' em subagent), usar helper compartilhado que soma
            # usage de AssistantMessages + timestamps.
            # T8: schema v2 + UPSERT atomico via SQL raw para evitar
            # lost-update em subagents concorrentes.
            # Log diagnostico antes do gate (detectar flag off / session/agent vazio)
            logger.info(
                f"[HOOK:SubagentStop] cost granular pre-gate: "
                f"flag={USE_SUBAGENT_COST_GRANULAR} "
                f"session={bool(session_id)} agent={bool(agent_id)}"
            )
            if USE_SUBAGENT_COST_GRANULAR and session_id and agent_id:
                try:
                    import json as _json
                    from contextlib import nullcontext
                    from app import db
                    from sqlalchemy import text as _sql_text

                    # GOTCHA 2026-04-17: Hooks async do SDK rodam FORA do Flask
                    # app context. `db.session.execute` sem context explode com
                    # RuntimeError("Working outside of application context").
                    # Padrao adotado em memory_injection.py:620-630.
                    try:
                        from flask import current_app as _app_probe
                        _ = _app_probe.name
                        _app_ctx = nullcontext()
                    except RuntimeError:
                        from app import create_app as _create_app
                        _hook_app = _create_app()
                        _app_ctx = _hook_app.app_context()

                    # Obter metadata — ResultMessage (compat forward) OU
                    # compute do JSONL (subagent real SDK 0.1.60)
                    computed_started_at = None
                    if last_result:
                        usage = last_result.get('usage', {}) or {}
                        computed_input = usage.get('input_tokens') or 0
                        computed_output = usage.get('output_tokens') or 0
                        computed_cache_read = usage.get('cache_read_input_tokens') or 0
                        computed_cache_create = usage.get('cache_creation_input_tokens') or 0
                        computed_cost = cost_usd or 0.0
                        computed_duration = duration_ms or 0
                        computed_turns = num_turns or 0
                        computed_stop = stop_reason or 'end_turn'
                    else:
                        from .subagent_reader import (
                            _compute_subagent_metadata_from_jsonl
                        )
                        meta = _compute_subagent_metadata_from_jsonl(transcript_path)
                        computed_input = meta['input_tokens']
                        computed_output = meta['output_tokens']
                        computed_cache_read = meta['cache_read_tokens']
                        computed_cache_create = meta['cache_creation_tokens']
                        computed_cost = meta['cost_usd']
                        computed_duration = meta['duration_ms']
                        computed_turns = meta['num_turns']
                        computed_stop = meta['stop_reason'] or 'end_turn'
                        # B12 fix: usar started_at computado do JSONL
                        _sa = meta.get('started_at')
                        if _sa is not None:
                            try:
                                computed_started_at = _sa.isoformat()
                            except AttributeError:
                                computed_started_at = None

                    # Log diagnostico dos valores computados
                    logger.info(
                        f"[HOOK:SubagentStop] cost granular computed: "
                        f"turns={computed_turns} cost=${computed_cost:.6f} "
                        f"input={computed_input} output={computed_output} "
                        f"cache_read={computed_cache_read} "
                        f"cache_create={computed_cache_create} "
                        f"duration={computed_duration}ms "
                        f"last_result={bool(last_result)}"
                    )

                    # So persistir se tivermos dados uteis
                    if not (computed_turns > 0 or computed_cost > 0):
                        logger.warning(
                            f"[HOOK:SubagentStop] cost granular SKIP — "
                            f"turns=0 e cost=0. Transcript="
                            f"{transcript_path or 'NONE'} "
                            f"agent_type={agent_type}"
                        )
                    if computed_turns > 0 or computed_cost > 0:
                        entry = {
                            'schema_version': 'v2',
                            'agent_id': agent_id,
                            'agent_type': agent_type,
                            'cost_usd': float(computed_cost),
                            'input_tokens': int(computed_input),
                            'output_tokens': int(computed_output),
                            'cache_read_tokens': int(computed_cache_read),
                            'cache_creation_tokens': int(computed_cache_create),
                            'duration_ms': int(computed_duration),
                            'num_turns': int(computed_turns),
                            'stop_reason': computed_stop,
                            'started_at': computed_started_at,
                            'ended_at': agora_utc_naive().isoformat(),
                        }

                        # T8 UPSERT atomico: jsonb_set append no array
                        # entries — impede lost-update em writes concorrentes.
                        # `UPDATE ... SET data = jsonb_set(..., data->... || :new)`
                        # e atomico por row em PostgreSQL: acquire lock, read,
                        # compute, write — UPDATE subsequente espera lock.
                        # Inicializa bucket se ausente (COALESCE).
                        #
                        # B15 fix (2026-04-17): hook async roda FORA do Flask
                        # app context. Envolver em `with _app_ctx` resolve
                        # RuntimeError("Working outside of application context").
                        # Mesmo padrao que _session_archive_hook usa.
                        # SQLAlchemy text() usa `:param` para bind. PostgreSQL
                        # cast `::jsonb` conflita — gera "syntax error at or
                        # near ':'". Solucao: usar CAST(... AS jsonb).
                        # Fase 4 (2026-04-21): Retry único com backoff 500ms quando
                        # rowcount=0. Root cause: race entre hook async e
                        # AgentSession.get_or_create — SubagentStop pode disparar
                        # ANTES do commit que cria a linha em agent_sessions.
                        # Antes: 21/21 sessoes > $10 com subagent_costs NULL.
                        # Fix: 1 retry curto recupera maioria dos casos sem custo.
                        _upsert_sql = _sql_text("""
                            UPDATE agent_sessions
                            SET data = jsonb_set(
                                COALESCE(data, CAST('{}' AS jsonb)),
                                '{subagent_costs}',
                                jsonb_build_object(
                                    'version', 2,
                                    'entries',
                                    COALESCE(
                                        data->'subagent_costs'->'entries',
                                        CAST('[]' AS jsonb)
                                    ) || CAST(:entry_json AS jsonb)
                                ),
                                true
                            )
                            WHERE session_id = :sid
                        """)
                        _entry_params = {
                            'sid': session_id,
                            'entry_json': _json.dumps(entry),
                        }
                        with _app_ctx:
                            result = db.session.execute(_upsert_sql, _entry_params)
                            rowcount = result.rowcount
                            db.session.commit()

                        # Retry único se session ainda não foi commitada.
                        # Fix pos-review (2026-04-21): sleep FORA do _app_ctx
                        # para liberar a conexao do pool durante a espera.
                        # Novo `with _app_ctx` para a query de retry — Flask
                        # AppContext e re-entrant (push multiplo funciona) e
                        # nullcontext e trivialmente re-utilizavel.
                        if rowcount == 0:
                            import time as _time
                            _time.sleep(0.5)
                            logger.info(
                                f"[HOOK:SubagentStop] rowcount=0 — retry "
                                f"apos 500ms session_id={session_id[:12]}..."
                            )
                            with _app_ctx:
                                result_retry = db.session.execute(
                                    _upsert_sql, _entry_params
                                )
                                rowcount = result_retry.rowcount
                                db.session.commit()

                        logger.info(
                            f"[HOOK:SubagentStop] cost granular persistido v2 "
                            f"agent_type={agent_type} cost=${computed_cost:.4f} "
                            f"turns={computed_turns} duration={computed_duration}ms "
                            f"rowcount={rowcount} persist_ok={rowcount > 0}"
                        )
                        # Se AINDA rowcount=0 apos retry: session realmente nao
                        # existe. Log warning para monitoramento.
                        if rowcount == 0:
                            logger.warning(
                                f"[HOOK:SubagentStop] cost granular UPDATE "
                                f"rowcount=0 APOS retry — session_id={session_id[:12]}... "
                                f"nao existe em agent_sessions. Entry perdida: "
                                f"agent_type={agent_type}"
                            )
                except Exception as granular_err:
                    logger.warning(
                        f"[HOOK:SubagentStop] cost granular falhou: "
                        f"{type(granular_err).__name__}: {granular_err}"
                    )
                    # Nao tentar rollback aqui — se o with _app_ctx saiu (via
                    # exception), a session ja fez rollback automatico no
                    # __exit__. Tentar rollback fora de context re-explode.

            # #6 UI — emite subagent_summary via Redis pubsub para o frontend
            # FIX 2026-04-17: anteriormente usava event_queue local, que corrompia
            # protocolo interno do SDK (TypeError: StreamEvent is not a byte).
            # Agora publica no canal agent_sse:<session_id>, mesmo canal usado
            # pelo worker de validacao (#4). SSE generator consome ambos.
            from ..config.feature_flags import USE_SUBAGENT_UI
            if USE_SUBAGENT_UI and session_id and agent_id:
                try:
                    from .subagent_reader import get_subagent_summary
                    from .client import _emit_subagent_summary
                    summary = get_subagent_summary(
                        session_id=session_id,
                        agent_id=agent_id,
                        agent_type=agent_type,
                        include_pii=True,  # sanitizacao na camada 2 (routes/chat.py)
                    )
                    logger.info(
                        f"[HOOK:SubagentStop] get_subagent_summary "
                        f"agent_type={agent_type} status={summary.status} "
                        f"tools_used={len(summary.tools_used)} "
                        f"findings_len={len(summary.findings_text)}"
                    )
                    _emit_subagent_summary(session_id, summary.to_dict())
                except Exception as ui_err:
                    logger.warning(
                        f"[HOOK:SubagentStop] emit UI falhou: {ui_err}"
                    )
            else:
                logger.info(
                    f"[HOOK:SubagentStop] emit UI SKIP "
                    f"USE_SUBAGENT_UI={USE_SUBAGENT_UI} "
                    f"session_id={bool(session_id)} "
                    f"agent_id={bool(agent_id)}"
                )

            # #4 Validacao anti-alucinacao async (enfileira job RQ)
            from ..config.feature_flags import (
                USE_SUBAGENT_VALIDATION,
                SUBAGENT_VALIDATION_THRESHOLD,
            )
            if USE_SUBAGENT_VALIDATION and session_id and agent_id:
                try:
                    # O worker RQ roda em container Render separado (sem acesso
                    # ao /tmp/.claude do web, onde o CLI grava o transcript do
                    # subagente). Computamos o summary AQUI (o web tem o FS) e
                    # o passamos serializado no payload — desacopla o consumidor
                    # do filesystem. Sem isso o job sempre abortava com
                    # status=error em PROD (O0.2 — ver docs/blueprint-agente).
                    summary_payload = None
                    try:
                        from .subagent_reader import get_subagent_summary as _gss
                        _val_summary = _gss(
                            session_id=session_id,
                            agent_id=agent_id,
                            agent_type=agent_type,
                            include_pii=True,
                            max_tool_chars=1000,
                        )
                        if _val_summary.status == 'done':
                            # include_cost=False: o validador nao usa cost_usd;
                            # enxuga o payload RQ.
                            summary_payload = _val_summary.to_dict(
                                include_cost=False
                            )
                            # findings_text pode ter 100KB+ (subagente pesado);
                            # o validador so usa [:3000]. Trunca p/ manter o
                            # payload RQ enxuto no Redis.
                            _ft = summary_payload.get('findings_text') or ''
                            if len(_ft) > 4000:
                                summary_payload['findings_text'] = _ft[:4000]
                    except Exception as _sum_err:
                        logger.debug(
                            f"[HOOK:SubagentStop] summary p/ validacao "
                            f"falhou: {_sum_err}"
                        )

                    import os
                    from rq import Queue
                    import redis

                    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
                    r = redis.from_url(redis_url)
                    q = Queue('agent_validation', connection=r)
                    q.enqueue(
                        'app.agente.workers.subagent_validator.validate_subagent_output',
                        session_id=session_id,
                        agent_id=agent_id,
                        threshold=SUBAGENT_VALIDATION_THRESHOLD,
                        summary_dict=summary_payload,
                        job_timeout=60,
                        # failure_ttl curto: o payload carrega PII (summary com
                        # include_pii=True). Default RQ p/ job falho = 1 ano no
                        # Redis; aqui limitamos a 1h (sucesso expira em ~8min).
                        failure_ttl=3600,
                    )
                    logger.debug(
                        f"[HOOK:SubagentStop] validacao enfileirada "
                        f"(agent_type={agent_type}, agent_id={agent_id[:12]}, "
                        f"summary_payload={summary_payload is not None})"
                    )
                except Exception as val_err:
                    logger.debug(
                        f"[HOOK:SubagentStop] validacao enqueue falhou: {val_err}"
                    )

            # A1 (2026-05-16) — telemetria per-invocacao em agent_invocation_metrics
            # Distinta de USE_SUBAGENT_COST_GRANULAR (que persiste em JSONB
            # da AgentSession). Aqui UMA linha por spawn->stop em tabela
            # dedicada — permite dashboard e analise de regressao cross-deploy.
            # Best-effort: falha NAO quebra stream do agente.
            from ..config.feature_flags import USE_INVOCATION_METRICS_PERSIST

            if USE_INVOCATION_METRICS_PERSIST and agent_id and agent_type:
                try:
                    from contextlib import nullcontext
                    from app import db
                    from ..models import AgentInvocationMetric

                    # Extrair tokens + duration/cost/turns. Preferencia:
                    # last_result.usage (compat SDK <0.1.60 + paths que ainda
                    # emitem ResultMessage em subagent). Fallback:
                    # _compute_subagent_metadata_from_jsonl (SDK 0.1.60+ — onde
                    # subagent NAO emite type:'result' no transcript JSONL).
                    metric_input_tokens = 0
                    metric_output_tokens = 0
                    metric_cache_read = 0
                    metric_cache_create = 0
                    metric_started_at = None
                    # Snapshot dos campos extraidos do last_result (linha 518+).
                    # Quando last_result e None, ficam None — bridge abaixo
                    # sobrescreve com meta[*] do JSONL para evitar NULL no INSERT.
                    metric_duration_ms = duration_ms
                    metric_num_turns = num_turns
                    metric_cost_usd = cost_usd
                    metric_stop_reason = stop_reason

                    if last_result:
                        usage = last_result.get('usage', {}) or {}
                        metric_input_tokens = int(usage.get('input_tokens') or 0)
                        metric_output_tokens = int(usage.get('output_tokens') or 0)
                        metric_cache_read = int(
                            usage.get('cache_read_input_tokens') or 0
                        )
                        metric_cache_create = int(
                            usage.get('cache_creation_input_tokens') or 0
                        )
                    elif transcript_path:
                        try:
                            from .subagent_reader import (
                                _compute_subagent_metadata_from_jsonl
                            )
                            meta = _compute_subagent_metadata_from_jsonl(
                                transcript_path
                            )
                            metric_input_tokens = int(meta.get('input_tokens') or 0)
                            metric_output_tokens = int(meta.get('output_tokens') or 0)
                            metric_cache_read = int(
                                meta.get('cache_read_tokens') or 0
                            )
                            metric_cache_create = int(
                                meta.get('cache_creation_tokens') or 0
                            )
                            # started_at do JSONL (timestamp do 1o turn)
                            metric_started_at = meta.get('started_at')
                            # BRIDGE FIX (2026-05-16): em SDK 0.1.60+ subagent
                            # nao emite ResultMessage, entao duration/cost/turns
                            # ficam None pelo path inicial (linhas 518-520).
                            # Sobrescrever com valores computados do JSONL via
                            # _compute_subagent_metadata_from_jsonl, que ja faz
                            # soma de usage e diff de timestamps. Sem isso,
                            # dashboard A3 zera KPIs e anomaly detection nao
                            # funciona. Resolve gap reportado em PROD 2026-05-16.
                            if metric_duration_ms is None:
                                _m_dur = meta.get('duration_ms')
                                if _m_dur is not None:
                                    metric_duration_ms = int(_m_dur)
                            if metric_num_turns is None:
                                _m_turns = meta.get('num_turns')
                                if _m_turns is not None:
                                    metric_num_turns = int(_m_turns)
                            if metric_cost_usd is None:
                                _m_cost = meta.get('cost_usd')
                                if _m_cost is not None:
                                    metric_cost_usd = float(_m_cost)
                            if not metric_stop_reason:
                                metric_stop_reason = (
                                    meta.get('stop_reason') or 'end_turn'
                                )
                        except Exception as _meta_err:
                            logger.debug(
                                f"[HOOK:SubagentStop] A1 metadata extract: "
                                f"{_meta_err}"
                            )

                    # Flask app context: hook async roda FORA do contexto.
                    # Mesmo padrao usado no bloco JSONB acima e em
                    # memory_injection.py:620-630.
                    # COMMIT GUARD (2026-05-16): flag para saber se criamos
                    # context novo. So comitar quando criamos o context — se
                    # estiver em nullcontext (dentro de request Flask), commit
                    # explicito flusharia writes pendentes do request inteiro
                    # (mesmo motivo do SAVEPOINT pattern documentado em
                    # AgentInvocationMetric.insert_metric:1683-1693).
                    _a1_owns_ctx = False
                    try:
                        from flask import current_app as _app_probe_a1
                        _ = _app_probe_a1.name
                        _a1_app_ctx = nullcontext()
                    except RuntimeError:
                        from app import create_app as _create_app_a1
                        _a1_hook_app = _create_app_a1()
                        _a1_app_ctx = _a1_hook_app.app_context()
                        _a1_owns_ctx = True

                    with _a1_app_ctx:
                        try:
                            metric = AgentInvocationMetric.insert_metric(
                                agent_id=agent_id,
                                agent_type=agent_type,
                                session_id=session_id or None,
                                user_id=user_id if user_id else None,
                                started_at=metric_started_at,
                                duration_ms=metric_duration_ms,
                                num_turns=metric_num_turns,
                                stop_reason=metric_stop_reason or 'end_turn',
                                cost_usd=(
                                    float(metric_cost_usd)
                                    if metric_cost_usd is not None else None
                                ),
                                input_tokens=metric_input_tokens,
                                output_tokens=metric_output_tokens,
                                cache_read_tokens=metric_cache_read,
                                cache_creation_tokens=metric_cache_create,
                                source=AgentInvocationMetric.SOURCE_PRODUCTION,
                            )
                            # Commit GUARD: insert_metric usa begin_nested
                            # (SAVEPOINT). Comitar SO se criamos o app_context
                            # neste hook (path comum, async fora de request).
                            # Em request Flask (nullcontext), o SAVEPOINT
                            # consolida no commit final do request — comitar
                            # aqui faria flush prematuro de outros writes
                            # pendentes (race condition documentada em
                            # AgentInvocationMetric.insert_metric).
                            if _a1_owns_ctx:
                                db.session.commit()
                            if metric is None:
                                logger.debug(
                                    f"[HOOK:SubagentStop] A1 metric duplicada "
                                    f"(agent_id={agent_id[:12]}) — ignorado"
                                )
                            else:
                                logger.info(
                                    f"[HOOK:SubagentStop] A1 metric persistida "
                                    f"agent_type={agent_type} "
                                    f"duration={metric_duration_ms}ms "
                                    f"turns={metric_num_turns} "
                                    f"cost=${metric_cost_usd or 0:.4f} "
                                    f"tokens={metric_input_tokens}/"
                                    f"{metric_output_tokens} "
                                    f"owns_ctx={_a1_owns_ctx}"
                                )
                        except Exception as _ins_err:
                            # Rollback so se for nosso context — caso contrario
                            # poderia abortar transacao do request em curso.
                            if _a1_owns_ctx:
                                try:
                                    db.session.rollback()
                                except Exception:
                                    pass
                            logger.warning(
                                f"[HOOK:SubagentStop] A1 metric insert falhou "
                                f"(best-effort): {_ins_err}"
                            )
                except Exception as a1_err:
                    logger.debug(
                        f"[HOOK:SubagentStop] A1 metric outer suppressed: "
                        f"{a1_err}"
                    )

            return {}
        except Exception as e:
            logger.debug(f"[HOOK:SubagentStop] Suppressed: {e}")
            return {}

    # ─── UserPromptSubmit Hook — injeta memórias + logging ───
    async def _user_prompt_submit_hook(
        hook_input: UserPromptSubmitHookInput, signal, context: HookContext
    ):
        """Hook de submissão: injeta memórias do usuário como contexto adicional.

        SEMPRE ATIVO: A injeção de memória é independente de USE_EXPANDED_HOOKS.
        USE_EXPANDED_HOOKS controla apenas o logging extra.

        Fluxo:
        1. Carrega memórias do usuário do banco via _load_user_memories_for_context
        2. Formata como XML estruturado
        3. Retorna via hookSpecificOutput.additionalContext
        4. SDK injeta automaticamente no contexto da conversa

        Ref: https://platform.claude.com/docs/en/agent-sdk/hooks
        """
        try:
            from ..config.feature_flags import USE_EXPANDED_HOOKS, USE_AUTO_MEMORY_INJECTION

            prompt = hook_input.get('prompt', '')

            # Fase B teams-melhorias: resolver o FALANTE do turno ATUAL.
            # A closure (user_id/user_name) congela no falante que CONECTOU o
            # client do pool — em grupos do Teams, injetaria memorias/gates do
            # falante errado. Decisao Rafael: memorias = do falante do turno.
            turn_user_id, turn_user_name = _turn_user()

            if USE_EXPANDED_HOOKS:
                logger.info(
                    f"[HOOK:UserPromptSubmit] Prompt recebido: "
                    f"prompt_len={len(prompt)} chars"
                )

            # ============================================================
            # Injeção automática de memórias (independente de EXPANDED_HOOKS)
            # ============================================================
            # Log de diagnóstico — confirma propagação de user_id (Teams + Web)
            logger.info(
                f"[HOOK:UserPromptSubmit] user_id={turn_user_id or 'None'} | "
                f"auto_memory={'ON' if USE_AUTO_MEMORY_INJECTION else 'OFF'} | "
                f"prompt_len={len(prompt)} chars"
            )

            additional_context = None
            tail_context = None
            if USE_AUTO_MEMORY_INJECTION and turn_user_id:
                try:
                    # Fix DC-3: Ler model de self.settings (sempre atual)
                    # em vez de options_dict (closure capturada no connect,
                    # fica stale após set_model() no path persistente).
                    # F4.4 PAD-CTX: payload em 2 partes — main (user_rules,
                    # memorias, directives, briefing, routing) + tail
                    # (recent_sessions + pendencias, por ULTIMO na montagem).
                    additional_context, tail_context, injected_mem_ids = (
                        _load_user_memories_for_context(
                            turn_user_id, prompt=prompt,
                            model_name=get_model_name(),
                        )
                    )
                    # Salvar IDs injetados para effectiveness tracking posterior
                    set_injected_ids(injected_mem_ids)
                except Exception as mem_err:
                    logger.warning(
                        f"[HOOK:UserPromptSubmit] Erro ao carregar memórias "
                        f"(ignorado): {mem_err}"
                    )

            # T2-1: Detecção de correção — lembrete para Reflection Bank
            correction_hint = ""
            if prompt and len(prompt) > 10:
                import re as _re
                _correction_patterns = [
                    _re.compile(r'(?i)\b(n[aã]o|errado|incorreto),?\s*(o\s+correct?o|na\s+verdade|deveria)'),
                    _re.compile(r'(?i)^(na verdade|errado|incorreto|n[aã]o[,.]?\s+(é|e)\s+(assim|isso))'),
                    _re.compile(r'(?i)\b(voc[eê]\s+errou|est[aá]\s+errado|isso\s+(est[aá]|tá)\s+errado)'),
                    _re.compile(r'(?i)\b(correct?o\s+[eé]|certo\s+[eé]|deveria\s+ser)'),
                ]
                if any(p.search(prompt) for p in _correction_patterns):
                    correction_hint = (
                        "\n<system_hint>"
                        "O usuário parece estar CORRIGINDO algo. "
                        "Siga o protocolo reflection_bank (R0): identifique o erro, "
                        "reconheça, salve em /memories/corrections/ e aprenda."
                        "</system_hint>"
                    )
                    logger.info(
                        f"[REFLECTION] Correção detectada user_id={turn_user_id} "
                        f"prompt_preview={prompt[:60]}"
                    )

            # ============================================================
            # Debug Mode Context Injection (Camada 2)
            # ============================================================
            debug_context = ""
            try:
                from ..config.permissions import get_debug_mode
                if get_debug_mode():
                    # F4.2 PAD-CTX (R-8): comprimido 9->4 linhas (condicional admin)
                    debug_context = (
                        "\n<debug_mode_context>"
                        "MODO DEBUG ATIVO: memory/session tools aceitam target_user_id=N "
                        "(descobrir via list_session_users ou SQL em usuarios); channel='teams'|'web' filtra sessoes.\n"
                        "SQL: tabelas internas desbloqueadas (agent_sessions, agent_memories, usuarios). "
                        "Todo acesso cross-user e logado.\n"
                        "Fluxo: list_session_users → search_sessions(target_user_id=N) → apresentar."
                        "</debug_mode_context>"
                    )
                    logger.info(
                        f"[HOOK:UserPromptSubmit] Debug mode context injected "
                        f"for user_id={turn_user_id}"
                    )
            except Exception as debug_err:
                logger.debug(f"[HOOK:UserPromptSubmit] Debug mode check failed: {debug_err}")

            # ============================================================
            # SQL Admin Context Injection (Camada 3)
            # ============================================================
            sql_admin_context = ""
            try:
                from app.pessoal import USUARIOS_SQL_ADMIN as _SQL_ADMIN
                if turn_user_id and turn_user_id in _SQL_ADMIN:
                    # F4.2 PAD-CTX (R-8): comprimido 12->6 linhas (condicional admin)
                    sql_admin_context = (
                        "\n<sql_admin_context>"
                        "MODO SQL ADMIN: acesso TOTAL ao banco via mcp__sql__consultar_sql "
                        "(todas as tabelas, incluindo agent_*, pessoal_*, bi_*).\n"
                        "INSERT/UPDATE/DELETE permitidos pela propria tool (backend ativa admin_mode "
                        "pelo seu user_id) — passe o comando SQL como 'pergunta'.\n"
                        "PROIBIDO Bash+Python/SQLAlchemy/psycopg para DML: sem auditoria; a tool MCP registra tudo.\n"
                        "Escrita afeta PRODUCAO: mostre o SQL, obtenha confirmacao explicita ANTES de executar (R3), "
                        "e valide o resultado com SELECT apos."
                        "</sql_admin_context>"
                    )
                    logger.info(
                        f"[HOOK:UserPromptSubmit] SQL admin context injected "
                        f"for user_id={turn_user_id}"
                    )
            except Exception as admin_err:
                logger.debug(f"[HOOK:UserPromptSubmit] SQL admin check failed: {admin_err}")

            # ============================================================
            # Session Context Injection (Camada 0 — cache-safe)
            # Injeta data/hora e identidade do usuario aqui em vez do
            # system prompt, mantendo-o estatico para prompt caching.
            # ============================================================
            session_context = ""
            try:
                from ..config.feature_flags import (
                    USE_PROMPT_CACHE_OPTIMIZATION,
                    USE_CUSTOM_SYSTEM_PROMPT,
                )
                if USE_PROMPT_CACHE_OPTIMIZATION and USE_CUSTOM_SYSTEM_PROMPT and turn_user_id:
                    data_hora = agora_utc_naive().strftime("%d/%m/%Y %H:%M")

                    pessoal_grant = ""
                    try:
                        from app.pessoal import USUARIOS_PESSOAL, USUARIOS_SQL_ADMIN
                        if turn_user_id in USUARIOS_SQL_ADMIN or turn_user_id in USUARIOS_PESSOAL:
                            pessoal_grant = (
                                "\n  <pessoal_access>CONCEDIDO: tabelas pessoal_* "
                                "acessiveis para este usuario.</pessoal_access>"
                            )
                    except ImportError:
                        pass

                    # G1 (2026-04-15): xml_escape em user_name para defense
                    # in depth. user_id e int (safe), data_hora vem de
                    # strftime (safe), pessoal_grant e literal controlado.
                    session_context = (
                        "<session_context>"
                        f"\n  <data_atual>{data_hora}</data_atual>"
                        f"\n  <usuario>{xml_escape(turn_user_name)} (ID: {turn_user_id})</usuario>"
                        f"{pessoal_grant}"
                        "\n</session_context>\n"
                    )
            except Exception as sc_err:
                logger.debug(f"[HOOK:UserPromptSubmit] Session context falhou: {sc_err}")

            # Resume fallback: injetar mensagens JSONB quando resume falhou
            # OU quando a sessao foi rotacionada por idle (reason='rotated' —
            # continuidade de contexto, caso conversa-nacom 2026-06-10)
            resume_fallback_context = ""
            if resume_state.get('failed') and resume_state.get('fallback'):
                _reason = resume_state.get('reason') or 'resume_failed'
                resume_fallback_context = (
                    "\n<resume_fallback_notice>"
                    + _build_resume_fallback_notice(_reason)
                    + "</resume_fallback_notice>\n"
                    + resume_state['fallback'] + "\n"
                )
                logger.info(
                    f"[HOOK:UserPromptSubmit] Resume fallback injetado "
                    f"(reason={_reason}): {len(resume_fallback_context)} chars"
                )
                # Limpar para não reinjetar nos próximos turnos
                resume_state['failed'] = False

            # ============================================================
            # Onda 4 — F4/F5: Skill Hints Advisory (flag-gated)
            # ============================================================
            skill_hints_context = ""
            try:
                from ..config.feature_flags import USE_AGENT_SKILL_RAG
                if USE_AGENT_SKILL_RAG and prompt:
                    from .context_enrichment import build_skill_hints_block
                    _skill_hints = build_skill_hints_block(prompt)
                    if _skill_hints:
                        skill_hints_context = "\n" + _skill_hints
            except Exception as _f4_err:
                logger.debug(f"[HOOK:UserPromptSubmit] F4/F5 skill_hints falhou (best-effort): {_f4_err}")

            # ============================================================
            # Onda 4 — D5: World Model Injection (flag-gated, aditivo)
            # ============================================================
            # _DOMAIN_KEYWORDS em memory_injection.py permanece como fallback
            # cold-start — D5 NUNCA remove routing_context existente.
            world_model_context = ""
            try:
                from ..config.feature_flags import USE_AGENT_WORLD_MODEL_INJECT
                if USE_AGENT_WORLD_MODEL_INJECT and turn_user_id and prompt:
                    from .context_enrichment import build_world_model_block
                    _world_model = build_world_model_block(user_id=turn_user_id, query=prompt)
                    if _world_model:
                        world_model_context = "\n" + _world_model
            except Exception as _d5_err:
                logger.debug(f"[HOOK:UserPromptSubmit] D5 world_model falhou (best-effort): {_d5_err}")

            if session_context or additional_context or tail_context or correction_hint or debug_context or sql_admin_context or resume_fallback_context or skill_hints_context or world_model_context:
                # F4.4 PAD-CTX: montagem na ORDEM-ALVO (funcao pura testavel) —
                # tail (recent_sessions + pendencias) por ULTIMO, colado a mensagem.
                full_context = _compose_hook_context(
                    resume_fallback=resume_fallback_context,
                    session_context=session_context,
                    main_context=additional_context or "",
                    correction_hint=correction_hint,
                    debug_context=debug_context,
                    sql_admin_context=sql_admin_context,
                    skill_hints=skill_hints_context,
                    world_model=world_model_context,
                    tail_context=tail_context or "",
                )
                # B2: Log de context budget por categoria
                memory_tokens_est = len(full_context) // 4
                logger.info(
                    f"[CONTEXT_BUDGET] "
                    f"user_id={turn_user_id or 'None'} | "
                    f"session_ctx_chars={len(session_context)} | "
                    f"memory_chars={len(additional_context or '')} | "
                    f"tail_chars={len(tail_context or '')} | "
                    f"skill_hints_chars={len(skill_hints_context)} | "
                    f"world_model_chars={len(world_model_context)} | "
                    f"total_tokens_est={memory_tokens_est} | "
                    f"prompt_len={len(prompt)}"
                )
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": full_context,
                    }
                }

            return {}
        except Exception as e:
            logger.debug(f"[HOOK:UserPromptSubmit] Suppressed (stream likely closed): {e}")
            return {}

    # ─── Registrar TODOS os hooks ───
    # ORDEM: _keep_stream_open PRIMEIRO (mantem o stream aberto p/ can_use_tool); o enforcement
    # (Fase 3.5, default ON desde I4 2026-06-12) vem DEPOIS — deny so com o stream ja garantido.
    hooks = {
        "PreToolUse": [
            HookMatcher(
                matcher=None,  # Aplica a TODAS as tools
                hooks=[_keep_stream_open, _enforce_mandatory_invariants],
            ),
        ],
        "PostToolUse": [
            HookMatcher(
                matcher="Bash|Skill",
                hooks=[_audit_post_tool_use],
            ),
        ],
        "PostToolUseFailure": [
            HookMatcher(
                matcher=None,  # Todas as tools
                hooks=[_post_tool_use_failure],
            ),
        ],
        "PreCompact": [
            HookMatcher(
                hooks=[_pre_compact_hook],
            ),
        ],
        "Stop": [
            HookMatcher(
                hooks=[_stop_hook],
            ),
        ],
        "UserPromptSubmit": [
            HookMatcher(
                hooks=[_user_prompt_submit_hook],
                timeout=120.0,  # 2 min — memorias + semantic search + contexto operacional
            ),
        ],
    }

    # SDK 0.1.48+: Subagent lifecycle hooks
    hooks["SubagentStart"] = [
        HookMatcher(hooks=[_subagent_start_hook]),
    ]
    hooks["SubagentStop"] = [
        HookMatcher(hooks=[_subagent_stop_hook]),
    ]

    return hooks
