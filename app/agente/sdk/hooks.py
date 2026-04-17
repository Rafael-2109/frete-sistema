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


def build_hooks(
    user_id: int,
    user_name: str,
    tool_failure_counts: dict,
    get_last_thinking: callable,
    get_model_name: callable,
    set_injected_ids: callable,
    resume_state: dict = None,
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

        if additional:
            return {
                "continue_": True,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": additional,
                },
            }

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
        """
        try:
            agent_id = hook_input.get('agent_id', '')
            agent_type = hook_input.get('agent_type', '')

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

            # Contexto para o modelo: saber que subagente foi acionado
            return {
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "additionalContext": (
                        f"Subagente '{agent_type}' iniciado (id={agent_id[:12] if agent_id else 'N/A'}). "
                        f"Aguarde resultado antes de responder ao usuario."
                    ),
                }
            }
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
            if USE_SUBAGENT_COST_GRANULAR and session_id and cost_usd is not None:
                try:
                    from app import db
                    from ..models import AgentSession
                    from sqlalchemy.orm.attributes import flag_modified

                    input_tokens = 0
                    output_tokens = 0
                    cache_read = 0
                    if last_result:
                        usage = last_result.get('usage', {}) or {}
                        input_tokens = usage.get('input_tokens') or 0
                        output_tokens = usage.get('output_tokens') or 0
                        cache_read = usage.get('cache_read_input_tokens') or 0

                    sess = AgentSession.query.filter_by(
                        session_id=session_id
                    ).first()
                    if sess is not None:
                        data = sess.data or {}
                        bucket = data.setdefault('subagent_costs', {
                            'version': 1, 'entries': []
                        })
                        bucket['entries'].append({
                            'agent_id': agent_id,
                            'agent_type': agent_type,
                            'cost_usd': float(cost_usd),
                            'input_tokens': int(input_tokens),
                            'output_tokens': int(output_tokens),
                            'cache_read_tokens': int(cache_read),
                            'duration_ms': int(duration_ms or 0),
                            'num_turns': int(num_turns or 0),
                            'stop_reason': stop_reason or 'end_turn',
                            'started_at': None,
                            'ended_at': agora_utc_naive().isoformat(),
                        })
                        sess.data = data
                        flag_modified(sess, 'data')
                        db.session.commit()
                        logger.debug(
                            f"[HOOK:SubagentStop] cost granular persistido "
                            f"em sess.data (agent_type={agent_type})"
                        )
                except Exception as granular_err:
                    logger.debug(
                        f"[HOOK:SubagentStop] cost granular falhou: {granular_err}"
                    )

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
                        job_timeout=60,
                    )
                    logger.debug(
                        f"[HOOK:SubagentStop] validacao enfileirada "
                        f"(agent_type={agent_type}, agent_id={agent_id[:12]})"
                    )
                except Exception as val_err:
                    logger.debug(
                        f"[HOOK:SubagentStop] validacao enqueue falhou: {val_err}"
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
                f"[HOOK:UserPromptSubmit] user_id={user_id or 'None'} | "
                f"auto_memory={'ON' if USE_AUTO_MEMORY_INJECTION else 'OFF'} | "
                f"prompt_len={len(prompt)} chars"
            )

            additional_context = None
            if USE_AUTO_MEMORY_INJECTION and user_id:
                try:
                    # Fix DC-3: Ler model de self.settings (sempre atual)
                    # em vez de options_dict (closure capturada no connect,
                    # fica stale após set_model() no path persistente).
                    additional_context, injected_mem_ids = _load_user_memories_for_context(
                        user_id, prompt=prompt,
                        model_name=get_model_name(),
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
                        f"[REFLECTION] Correção detectada user_id={user_id} "
                        f"prompt_preview={prompt[:60]}"
                    )

            # ============================================================
            # Debug Mode Context Injection (Camada 2)
            # ============================================================
            debug_context = ""
            try:
                from ..config.permissions import get_debug_mode
                if get_debug_mode():
                    debug_context = (
                        "\n<debug_mode_context>"
                        "MODO DEBUG ATIVO. Capacidades extras disponiveis:\n"
                        "- Memory tools: use target_user_id=N para acessar memorias de outro usuario\n"
                        "- Session tools: use target_user_id=N + channel='teams'|'web' para buscar sessoes de outro usuario\n"
                        "- list_session_users: lista usuarios com sessoes (para descobrir target_user_id)\n"
                        "- SQL tool: tabelas internas desbloqueadas (agent_sessions, agent_memories, usuarios)\n"
                        "- Para encontrar user_id: list_session_users ou SQL 'SELECT id, nome, email FROM usuarios'\n"
                        "- Todo acesso cross-user e logado para auditoria.\n"
                        "Fluxo recomendado: list_session_users → search_sessions(target_user_id=N) → apresentar."
                        "</debug_mode_context>"
                    )
                    logger.info(
                        f"[HOOK:UserPromptSubmit] Debug mode context injected "
                        f"for user_id={user_id}"
                    )
            except Exception as debug_err:
                logger.debug(f"[HOOK:UserPromptSubmit] Debug mode check failed: {debug_err}")

            # ============================================================
            # SQL Admin Context Injection (Camada 3)
            # ============================================================
            sql_admin_context = ""
            try:
                from app.pessoal import USUARIOS_SQL_ADMIN as _SQL_ADMIN
                if user_id and user_id in _SQL_ADMIN:
                    sql_admin_context = (
                        "\n<sql_admin_context>"
                        "MODO SQL ADMIN: voce tem acesso TOTAL ao banco via mcp__sql__consultar_sql.\n"
                        "- Todas as tabelas desbloqueadas (incluindo agent_sessions, pessoal_*, bi_*)\n"
                        "- INSERT, UPDATE, DELETE permitidos\n"
                        "- CUIDADO: operacoes de escrita afetam producao. Confirme com o usuario ANTES de executar.\n"
                        "- Para escrita, gere o SQL e mostre ao usuario antes de executar."
                        "</sql_admin_context>"
                    )
                    logger.info(
                        f"[HOOK:UserPromptSubmit] SQL admin context injected "
                        f"for user_id={user_id}"
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
                if USE_PROMPT_CACHE_OPTIMIZATION and USE_CUSTOM_SYSTEM_PROMPT and user_id:
                    data_hora = agora_utc_naive().strftime("%d/%m/%Y %H:%M")

                    pessoal_grant = ""
                    try:
                        from app.pessoal import USUARIOS_PESSOAL, USUARIOS_SQL_ADMIN
                        if user_id in USUARIOS_SQL_ADMIN or user_id in USUARIOS_PESSOAL:
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
                        f"\n  <usuario>{xml_escape(user_name)} (ID: {user_id})</usuario>"
                        f"{pessoal_grant}"
                        "\n</session_context>\n"
                    )
            except Exception as sc_err:
                logger.debug(f"[HOOK:UserPromptSubmit] Session context falhou: {sc_err}")

            # Resume fallback: injetar mensagens JSONB quando resume falhou
            resume_fallback_context = ""
            if resume_state.get('failed') and resume_state.get('fallback'):
                resume_fallback_context = (
                    "\n<resume_fallback_notice>"
                    "IMPORTANTE: A sessão anterior não pôde ser restaurada via resume. "
                    "Abaixo está o histórico recente da conversa extraído do banco de dados. "
                    "Use este contexto para continuar a conversa de forma coerente. "
                    "O usuário pode não saber que o contexto foi perdido."
                    "</resume_fallback_notice>\n"
                    + resume_state['fallback'] + "\n"
                )
                logger.info(
                    f"[HOOK:UserPromptSubmit] Resume fallback injetado: "
                    f"{len(resume_fallback_context)} chars"
                )
                # Limpar para não reinjetar nos próximos turnos
                resume_state['failed'] = False

            if session_context or additional_context or correction_hint or debug_context or sql_admin_context or resume_fallback_context:
                full_context = resume_fallback_context + session_context + (additional_context or "") + correction_hint + debug_context + sql_admin_context
                # B2: Log de context budget por categoria
                memory_tokens_est = len(full_context) // 4
                logger.info(
                    f"[CONTEXT_BUDGET] "
                    f"user_id={user_id or 'None'} | "
                    f"session_ctx_chars={len(session_context)} | "
                    f"memory_chars={len(additional_context or '')} | "
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
    hooks = {
        "PreToolUse": [
            HookMatcher(
                matcher=None,  # Aplica a TODAS as tools
                hooks=[_keep_stream_open],
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
