"""
Cliente do Claude Agent SDK.

Wrapper que encapsula a comunicação com a API usando o SDK oficial.
Usa ClaudeSDKClient persistente via client_pool (daemon thread pool).

Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/

ARQUITETURA (v3 — ClaudeSDKClient persistente):
- ClaudeSDKClient mantido em pool (daemon thread com event loop proprio).
- Resume via sdk_session_id restaura contexto da conversa anterior.
- Pool gerenciado por client_pool.py (idle cleanup, force-kill).
"""

import logging
import queue
import time
from typing import AsyncGenerator, Dict, Any, List, Optional, Callable
from app.utils.timezone import agora_utc_naive

# SDK Oficial
# Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    UserMessage,       # Contém resultados de ferramentas
    SystemMessage,     # Mensagem de sistema (init com session_id)
    ToolUseBlock,
    ToolResultBlock,   # Resultado de execução de ferramenta
    TextBlock,
    ThinkingBlock,     # FEAT-002: Extended Thinking
    # SDK 0.1.31: Error classes especializadas
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
    CLIConnectionError,  # SIGTERM/process death — sibling of ProcessError
    # SDK 0.1.46+: Task messages para observabilidade de subagentes
    TaskStartedMessage,
    TaskProgressMessage,
    TaskNotificationMessage,
    # SDK 0.1.50: Rate limit events
    RateLimitEvent,
)

# SDK 0.1.64+: MirrorErrorMessage (SessionStore append falhou).
# Import condicional — quando SDK < 0.1.64 instalado, classe nao existe.
# isinstance contra tuple vazia = sempre False → handler e skipped graciosamente.
try:
    from claude_agent_sdk import MirrorErrorMessage as _MirrorErrorMessageClass
    MirrorErrorMessage = _MirrorErrorMessageClass
except ImportError:
    # SDK < 0.1.64: sentinel inerte. isinstance() contra classe sem instancias
    # reais sempre retorna False — handler abaixo fica inerte sem quebrar.
    class MirrorErrorMessage:  # type: ignore[no-redef]
        """Sentinel inerte para SDK < 0.1.64 (sem SessionStore). Nao e emitida."""
        pass

# Fallback para API direta (health check)
import anthropic
logger = logging.getLogger('sistema_fretes')



# =====================================================================
# Módulos extraídos — imports diretos nos módulos que precisam.
# Hooks: sdk/hooks.py | Memória: sdk/memory_injection.py
# Stream types: sdk/stream_parser.py
# =====================================================================



# =====================================================================
# STREAM PARSER — extraído para stream_parser.py
# Re-exports para backward compatibility (testes patcham estes nomes
# via patch.multiple('app.agente.sdk.client', ...)).
# =====================================================================
from .stream_parser import (  # noqa: E402 — re-exports para tests (patch.multiple)
    ToolCall,
    StreamEvent,
    AgentResponse,
    _StreamParseState,
)


def _emit_subagent_summary(session_id, summary_dict: dict) -> None:
    """
    Emite evento 'subagent_summary' via Redis pubsub + buffer FIFO.

    Chamado pelo _subagent_stop_hook apos persistir cost granular. O SSE
    generator em routes/chat.py subscreve `agent_sse:<session_id>` (delivery
    quente) e dreva `agent_sse_buffer:<session_id>` no startup (replay).

    FIX 2026-04-17: anteriormente usava event_queue.put_nowait(StreamEvent(...))
    mas event_queue espera bytes/strings (protocolo SDK interno), causando
    TypeError em sessoes com subagent que termina em status=error.

    T7 (2026-04-17 parte 2): adicionado buffer Redis LIST com TTL 5min.
    Resolve race condition onde hook publica DEPOIS do SSE fechar
    (3/5 casos em producao tinham subscribers=0). Usa RPUSH (FIFO) para
    preservar ordem cronologica.

    No-op se session_id for falsy ou Redis falhar (best-effort, R1).
    """
    if not session_id:
        logger.warning("[emit_subagent_summary] session_id vazio, skip")
        return
    try:
        import json
        import os
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        channel = f'agent_sse:{session_id}'
        buffer_key = f'agent_sse_buffer:{session_id}'
        payload = json.dumps({
            'type': 'subagent_summary',
            'data': summary_dict,
        })
        # Pub: delivery quente (clientes conectados)
        n_subs = r.publish(channel, payload)
        # Buffer: replay em reconnect (TTL 5min — suficiente para UX normal,
        # nao acumula indefinidamente em sessoes longas)
        try:
            r.rpush(buffer_key, payload)  # FIFO: RPUSH + LRANGE 0 -1
            r.expire(buffer_key, 300)
            # Cap defensivo: manter apenas ultimos 20 eventos por sessao.
            r.ltrim(buffer_key, -20, -1)
        except Exception as buf_err:
            logger.debug(f"[emit_subagent_summary] buffer falhou: {buf_err}")
        logger.info(
            f"[emit_subagent_summary] published channel={channel} "
            f"agent_type={summary_dict.get('agent_type')} "
            f"status={summary_dict.get('status')} subscribers={n_subs}"
        )
    except Exception as e:
        logger.warning(f"[emit_subagent_summary] falhou: {e}")


class AgentClient:
    """
    Cliente do Claude Agent SDK oficial.

    ARQUITETURA (v3 — ClaudeSDKClient persistente):
    - Usa ClaudeSDKClient mantido em pool (client_pool.py)
    - Resume via sdk_session_id para manter contexto entre turnos
    - Skills para funcionalidades (.claude/skills/)
    - Custom Tools MCP in-process para text-to-sql
    - Callback canUseTool para permissões
    - Rastreamento de custos

    Referências:
    - https://platform.claude.com/docs/pt-BR/agent-sdk/skills
    - https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
    - https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

    Uso:
        client = AgentClient()

        async for event in client.stream_response("Sua pergunta", sdk_session_id="..."):
            if event.type == 'text':
                print(event.content, end='')
    """

    def __init__(self):
        from ..config import get_settings

        self.settings = get_settings()

        # Carrega system prompt
        self.system_prompt = self._load_system_prompt()

        # Carrega preset operacional (para USE_CUSTOM_SYSTEM_PROMPT)
        self.operational_preset = self._load_preset_operacional()

        # Carrega briefing institucional (empresa_briefing.md) — injetado no
        # system_prompt como bloco estatico cacheavel (vocabulario + cadeia
        # de valor + gargalos + sistemas).
        self.empresa_briefing = self._load_empresa_briefing()

        # Cliente para health check (API direta)
        self._anthropic_client = anthropic.Anthropic(api_key=self.settings.api_key)

        # IDs de memórias injetadas no último turno (para effectiveness tracking)
        self._last_injected_memory_ids: list[int] = []

        # Contador de falhas por tool na sessão (para detecção de repetição)
        self._tool_failure_counts: dict[str, int] = {}

        # B2: Buffer do ultimo thinking block para auditoria de deliberacao
        # Acessivel por _parse_sdk_message (escrita) e hooks (leitura)
        self._last_thinking_content: Optional[str] = None

        logger.info(
            f"[AGENT_CLIENT] Inicializado | "
            f"Modelo: {self.settings.model} | "
            f"SDK: claude-agent-sdk"
        )

    def _load_system_prompt(self) -> str:
        """Carrega system prompt do arquivo."""
        try:
            with open(self.settings.system_prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(
                f"[AGENT_CLIENT] System prompt não encontrado: "
                f"{self.settings.system_prompt_path}"
            )
            return self._get_default_system_prompt()

    def _load_preset_operacional(self) -> str:
        """Carrega preset operacional do arquivo.

        Substitui o preset claude_code quando USE_CUSTOM_SYSTEM_PROMPT=true.
        Contém apenas: tool instructions, safety, environment, persistent systems.
        NÃO contém identidade dev, git, CSS, migrations.
        """
        preset_path = self.settings.operational_preset_path
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(
                    f"[AGENT_CLIENT] Preset operacional carregado: "
                    f"{preset_path} ({len(content)} chars)"
                )
                return content
        except FileNotFoundError:
            logger.warning(
                f"[AGENT_CLIENT] preset_operacional.md nao encontrado: {preset_path}"
            )
            return ""

    def _load_empresa_briefing(self) -> str:
        """Carrega briefing institucional da Nacom Goya.

        Conteudo: identificacao da empresa, cadeia de valor, tabelas-chave,
        sistemas, gargalos recorrentes, vocabulario de dominio. Injetado no
        system_prompt como bloco estatico para que o agente principal tenha
        acesso ao vocabulario operacional (ex: 'matar pedido', 'ruptura',
        'completude', 'bonificacao', 'travando a carteira', etc).

        Returns:
            String com o conteudo do briefing, ou string vazia se ausente.
        """
        briefing_path = self.settings.empresa_briefing_path
        try:
            with open(briefing_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(
                    f"[AGENT_CLIENT] Empresa briefing carregado: "
                    f"{briefing_path} ({len(content)} chars)"
                )
                return content
        except FileNotFoundError:
            logger.warning(
                f"[AGENT_CLIENT] empresa_briefing.md nao encontrado: {briefing_path}"
            )
            return ""

    def get_context_usage(self) -> Optional[Dict[str, Any]]:
        """
        Retorna uso do context window via SDK get_context_usage().

        Sessao A: Indicador de contexto consumido na UI.
        Disponivel desde SDK 0.1.52. Best-effort: retorna None se indisponivel.

        Returns:
            {"used": int, "total": int, "percent": float} ou None
        """
        try:
            from .client_pool import get_pooled_client
            from ..config.permissions import get_session_id

            pool_key = get_session_id() or ''
            pooled = get_pooled_client(pool_key)

            if not pooled or not pooled.connected:
                return None

            sdk_client = pooled.client
            if not hasattr(sdk_client, 'get_context_usage'):
                return None

            # get_context_usage() e sincrono no SDK — retorna dict direto
            usage = sdk_client.get_context_usage()
            if not usage:
                return None

            used = usage.get('used', 0)
            total = usage.get('total', 200000)
            if total == 0:
                return None

            return {
                'used': used,
                'total': total,
                'percent': round(used / total * 100, 1),
            }

        except Exception as e:
            logger.debug(f"[AGENT_CLIENT] get_context_usage falhou (ignorado): {e}")
            return None

    def _build_full_system_prompt(self, custom_instructions: str) -> str:
        """Concatena preset operacional + system_prompt formatado + empresa_briefing.

        Retorna string única que SUBSTITUI o preset claude_code.
        Economia estimada: ~3-4K tokens input por request.

        Ordem (tudo estatico para maximizar cache hits):
          1. preset_operacional.md  — tool instructions, safety, environment
          2. system_prompt.md        — identidade, regras R0-R10, routing
          3. empresa_briefing.md     — cadeia de valor, vocabulario, gargalos

        Args:
            custom_instructions: System prompt formatado (_format_system_prompt output)

        Returns:
            String completa para system_prompt (sem preset claude_code)
        """
        preset = self.operational_preset
        briefing = self.empresa_briefing

        if not preset:
            logger.warning(
                "[AGENT_CLIENT] Preset operacional vazio — usando apenas system_prompt.md"
            )
            base = custom_instructions
        else:
            base = f"{preset}\n\n{custom_instructions}"

        if briefing:
            return (
                f"{base}\n\n"
                f"<empresa_briefing>\n"
                f"Contexto institucional Nacom Goya (vocabulario, cadeia de valor, "
                f"sistemas, gargalos) — use como referencia para interpretar pedidos "
                f"do usuario e traduzir termos operacionais.\n\n"
                f"{briefing}\n"
                f"</empresa_briefing>"
            )
        return base

    def _get_default_system_prompt(self) -> str:
        """Retorna system prompt padrão."""
        return """Você é um assistente logístico especializado.
Ajude o usuário com consultas sobre pedidos, estoque e separações.
Use as ferramentas disponíveis para buscar dados reais do sistema.
Nunca invente informações."""

    def _extract_tool_description(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """
        FEAT-024: Extrai descrição amigável do tool_call.

        Em vez de mostrar "Read" ou "Bash", mostra uma descrição
        do que a ferramenta está fazendo, similar ao Claude Code.

        Args:
            tool_name: Nome da ferramenta (Read, Bash, Skill, etc.)
            tool_input: Input da ferramenta

        Returns:
            Descrição amigável da ação
        """
        if not tool_input:
            return tool_name

        # Mapeamento de ferramentas para descrições
        if tool_name == 'Read':
            file_path = tool_input.get('file_path', '')
            if file_path:
                # Extrai apenas o nome do arquivo
                file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                return f"Lendo {file_name}"
            return "Lendo arquivo"

        elif tool_name == 'Bash':
            # Bash tem campo description explícito
            description = tool_input.get('description', '')
            if description:
                return description
            command = tool_input.get('command', '')
            if command:
                # Extrai comando principal
                cmd_parts = command.split()
                if cmd_parts:
                    main_cmd = cmd_parts[0]
                    if main_cmd == 'python':
                        return "Executando script Python"
                    elif main_cmd in ('pip', 'npm', 'yarn'):
                        return f"Instalando dependências ({main_cmd})"
                    elif main_cmd == 'git':
                        return f"Git: {' '.join(cmd_parts[1:3])}"
                    else:
                        return f"Executando {main_cmd}"
            return "Executando comando"

        elif tool_name == 'Skill':
            skill_name = tool_input.get('skill', '')
            if skill_name:
                return f"Usando skill: {skill_name}"
            return "Invocando skill"

        elif tool_name == 'Glob':
            pattern = tool_input.get('pattern', '')
            if pattern:
                return f"Buscando arquivos: {pattern}"
            return "Buscando arquivos"

        elif tool_name == 'Grep':
            pattern = tool_input.get('pattern', '')
            if pattern:
                return f"Buscando: {pattern[:30]}..."
            return "Buscando no código"

        elif tool_name == 'Write':
            file_path = tool_input.get('file_path', '')
            if file_path:
                file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                return f"Escrevendo {file_name}"
            return "Escrevendo arquivo"

        elif tool_name == 'Edit':
            file_path = tool_input.get('file_path', '')
            if file_path:
                file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                return f"Editando {file_name}"
            return "Editando arquivo"

        elif tool_name == 'TodoWrite':
            todos = tool_input.get('todos', [])
            if todos:
                # Conta tarefas por status
                in_progress = sum(1 for t in todos if t.get('status') == 'in_progress')
                if in_progress > 0:
                    current = next((t for t in todos if t.get('status') == 'in_progress'), None)
                    if current:
                        return current.get('activeForm', 'Atualizando tarefas')
                return f"Gerenciando {len(todos)} tarefas"
            return "Atualizando tarefas"

        # Default: usa o nome da ferramenta
        return tool_name

    def _format_system_prompt(
        self,
        user_name: str = "Usuário",
        user_id: int = None
    ) -> str:
        """
        Formata system prompt com variáveis.

        Quando USE_PROMPT_CACHE_OPTIMIZATION=true (default):
        Variáveis dinâmicas ({data_atual}, {usuario_nome}, {user_id}) NÃO existem
        no template — são injetadas via _user_prompt_submit_hook como session_context.
        System prompt fica estático entre usuários/turnos → prompt caching hits no CLI.

        Quando USE_PROMPT_CACHE_OPTIMIZATION=false (rollback):
        Prepend bloco dinâmico ao prompt para compatibilidade.

        Args:
            user_name: Nome do usuário
            user_id: ID do usuário

        Returns:
            System prompt formatado
        """
        from ..config.feature_flags import USE_PROMPT_CACHE_OPTIMIZATION

        prompt = self.system_prompt

        if not USE_PROMPT_CACHE_OPTIMIZATION:
            # Rollback: variáveis foram removidas do template (system_prompt.md),
            # então prepend bloco dinâmico para manter contexto de data/usuário
            data_hora = agora_utc_naive().strftime("%d/%m/%Y %H:%M")
            dynamic_block = (
                f"<current_context_dynamic>\n"
                f"  Data: {data_hora}\n"
                f"  Usuário: {user_name} (ID: {user_id or 'NAO_DISPONIVEL'})\n"
                f"</current_context_dynamic>\n\n"
            )
            prompt = dynamic_block + prompt

            # Módulo Pessoal + SQL Admin: remoção inline da restrição (modo legado)
            restricao_pessoal = ", acessar ou mencionar tabelas pessoal_* (financas pessoais — dados privados, acesso restrito)"
            try:
                from app.pessoal import USUARIOS_PESSOAL, USUARIOS_SQL_ADMIN
                if user_id and (user_id in USUARIOS_SQL_ADMIN or user_id in USUARIOS_PESSOAL):
                    prompt = prompt.replace(restricao_pessoal, "")
            except ImportError:
                pass  # restrição permanece — seguro por default

        return prompt

    @staticmethod
    async def _self_correct_response(full_text: str) -> Optional[str]:
        """
        D6: Self-Correction — valida coerência aritmética em respostas tabulares.

        Reescrito para Sonnet 4.6 com escopo reduzido (vs Haiku que gerava falsos positivos):
        - Valida APENAS respostas com tabelas contendo dados numéricos
        - Critérios: inconsistências aritméticas (soma não bate, % diverge de absolutos)
        - Threshold: 500 chars (ignora respostas curtas/conversacionais)

        Args:
            full_text: Texto completo da resposta do agente

        Returns:
            None se a resposta está OK ou não precisa de validação
            String com observação de correção se detectar problema aritmético
        """
        from ..config.feature_flags import USE_SELF_CORRECTION

        if not USE_SELF_CORRECTION:
            return None

        # Threshold alto — só validar respostas substanciais
        if not full_text or len(full_text.strip()) < 500:
            return None

        # Só validar respostas que contenham tabelas com dados numéricos
        # Indicadores: linhas com pipe (tabela markdown) + dígitos
        import re
        has_table = bool(re.search(r'\|.*\d.*\|', full_text))
        if not has_table:
            return None

        try:
            client = anthropic.Anthropic()

            validation = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": (
                        "Verifique APENAS inconsistências ARITMÉTICAS nesta resposta:\n"
                        "- Soma de itens não bate com total declarado\n"
                        "- Percentual diverge dos valores absolutos\n"
                        "- Contagem de linhas contradiz quantidade mencionada\n\n"
                        "NÃO avalie: qualidade da escrita, completude, formatação ou "
                        "informações que não envolvem cálculos.\n\n"
                        "Se não há erro aritmético, responda EXATAMENTE: OK\n"
                        "Se encontrar, descreva em UMA frase curta (ex: 'Total diz 5 itens mas tabela tem 8').\n\n"
                        f"Resposta:\n{full_text[:3000]}"
                    )
                }]
            )

            result = validation.content[0].text.strip()

            if result.upper() == "OK" or len(result) < 5:
                logger.debug("[SELF-CORRECTION] Validação aritmética: OK")
                return None

            logger.warning(f"[SELF-CORRECTION] Inconsistência aritmética detectada: {result}")
            return result

        except Exception as e:
            # Self-correction é best-effort — falha silenciosa
            logger.debug(f"[SELF-CORRECTION] Erro na validação (ignorado): {e}")
            return None

    async def _parse_sdk_message(
        self,
        message: Any,
        state: '_StreamParseState',
    ) -> List[StreamEvent]:
        """Parse de uma mensagem SDK em StreamEvents.

        Método reutilizável por ambos os paths (query() e ClaudeSDKClient).
        Modifica `state` in-place (full_text, tokens, tool_calls, etc.).
        Retorna lista de StreamEvents a emitir (pode ser vazia).

        INVARIANTE: O comportamento é IDÊNTICO ao código inline que existia
        em _stream_response() linhas 1960-2262 antes da extração.

        Args:
            message: Mensagem do SDK (SystemMessage, AssistantMessage, etc.)
            state: Estado mutável do stream (compartilhado entre mensagens)

        Returns:
            Lista de StreamEvent (pode ser vazia para mensagens sem output)
        """
        events: List[StreamEvent] = []

        # ─── Diagnóstico de tempo ───
        current_time = time.time()
        elapsed_total = current_time - state.stream_start_time
        elapsed_since_last = current_time - state.last_message_time
        state.last_message_time = current_time

        if not state.first_message_logged:
            state.first_message_logged = True
            logger.info(
                f"[AGENT_SDK] Primeira mensagem recebida: {type(message).__name__} | "
                f"{elapsed_total:.1f}s apos inicio"
            )
        else:
            logger.debug(
                f"[AGENT_SDK] msg={type(message).__name__} | "
                f"total={elapsed_total:.1f}s | "
                f"delta={elapsed_since_last:.1f}s"
            )

        # ─── MirrorErrorMessage (SessionStore append falhou) ───
        # Subclass de SystemMessage (so importada no topo — ver imports).
        # Emitida quando batcher.store.append() falha. Contrato at-most-once: batch
        # e perdido (nao retentado). Disco local continua durable, session nao quebra.
        # Log ERROR + Sentry para visibilidade. NAO propaga como SSE (infra, nao UX).
        if isinstance(message, MirrorErrorMessage):
            _key = getattr(message, 'key', None)
            _error_msg = getattr(message, 'error', 'unknown')
            _sid = (
                (_key.get('session_id') or '?')[:12] + '...'
                if _key else '?'
            )

            # FIX 2026-04-27 (PP/PN): suprime Sentry capture quando o erro
            # vem da race de shutdown do ThreadPoolExecutor. Esses erros sao
            # inerentes ao SIGTERM do worker Teams e nao indicam bug acionavel —
            # ja foram triados como "fora de escopo" 4 ciclos seguidos.
            from .shutdown_state import is_interpreter_shutting_down, is_shutdown_error
            _is_shutdown_race = (
                is_interpreter_shutting_down() or is_shutdown_error(_error_msg)
            )

            if _is_shutdown_race:
                # Shutdown race — log warning local, NAO capturar Sentry
                logger.warning(
                    f"[SESSION_STORE] mirror_error durante shutdown (suprimido Sentry): "
                    f"session_id={_sid} error={_error_msg}"
                )
                return events

            logger.error(
                f"[SESSION_STORE] mirror_error — batch perdido "
                f"(disco local OK, store inconsistente): "
                f"session_id={_sid} error={_error_msg}"
            )
            try:
                # FIX P2 (FaseB.3 review): Sentry SDK 2.x API — Hub.current.client
                # foi depreciado, usar get_client().is_active() + top-level capture.
                import sentry_sdk
                _client = sentry_sdk.get_client()
                if _client is not None and _client.is_active():
                    sentry_sdk.capture_message(
                        f"SessionStore mirror_error: {_error_msg}",
                        level="error",
                    )
            except ImportError:
                pass
            except Exception as _sentry_err:
                logger.debug(
                    f"[SESSION_STORE] Sentry capture falhou (ignorado): {_sentry_err}"
                )
            return events

        # ─── SystemMessage (init do SDK) ───
        if isinstance(message, SystemMessage):
            sdk_sid = message.data.get('session_id') if hasattr(message, 'data') else None
            if sdk_sid:
                state.result_session_id = sdk_sid
                state.got_result_message = True
                logger.info(f"[AGENT_SDK] SDK session_id from init: {sdk_sid[:12]}...")
            return events

        # ─── Task messages (subagentes) ───
        if isinstance(message, TaskStartedMessage):
            task_desc = getattr(message, 'description', '') or ''
            task_id = getattr(message, 'task_id', '') or ''
            task_type = getattr(message, 'task_type', '') or ''
            logger.info(
                f"[AGENT_SDK] TaskStarted: {task_desc[:80]} | "
                f"task_id={task_id[:12]} | task_type={task_type}"
            )
            events.append(StreamEvent(
                type='task_started',
                content=task_desc,
                metadata={
                    'task_id': task_id,
                    'task_type': task_type,
                }
            ))
            return events

        if isinstance(message, TaskProgressMessage):
            task_desc = getattr(message, 'description', '') or ''
            task_id = getattr(message, 'task_id', '') or ''
            last_tool = getattr(message, 'last_tool_name', '') or ''
            logger.debug(
                f"[AGENT_SDK] TaskProgress: {task_desc[:80]} | "
                f"task_id={task_id[:12]} | last_tool={last_tool}"
            )
            events.append(StreamEvent(
                type='task_progress',
                content=task_desc,
                metadata={
                    'task_id': task_id,
                    'last_tool_name': last_tool,
                }
            ))
            return events

        if isinstance(message, TaskNotificationMessage):
            summary = getattr(message, 'summary', '') or ''
            status = getattr(message, 'status', '') or ''
            task_id = getattr(message, 'task_id', '') or ''
            usage = getattr(message, 'usage', None)
            logger.info(
                f"[AGENT_SDK] TaskNotification: {summary[:80]} | "
                f"status={status} | task_id={task_id[:12]} | "
                f"usage={usage}"
            )
            events.append(StreamEvent(
                type='task_notification',
                content=summary,
                metadata={
                    'task_id': task_id,
                    'status': status,
                    'usage': usage if isinstance(usage, dict) else None,
                }
            ))
            return events

        # ─── RateLimitEvent (SDK 0.1.50) ───
        if isinstance(message, RateLimitEvent):
            rate_info = message.rate_limit_info
            data = {
                'status': rate_info.status,
                'utilization': rate_info.utilization,
                'resets_at': rate_info.resets_at,
                'rate_limit_type': getattr(rate_info, 'rate_limit_type', None),
            }
            if rate_info.status == 'allowed_warning':
                logger.warning(
                    f"[RATE_LIMIT] Warning: "
                    f"{rate_info.utilization:.0%} utilizado, "
                    f"reseta em {rate_info.resets_at}"
                )
            elif rate_info.status == 'rejected':
                # WARNING (não ERROR): rate limit é tratável e esperado em picos
                logger.warning(
                    f"[RATE_LIMIT] REJEITADO: "
                    f"tipo={getattr(rate_info, 'rate_limit_type', 'unknown')}, "
                    f"reseta em {rate_info.resets_at}"
                )
            events.append(StreamEvent(
                type='rate_limit',
                content='',
                metadata=data,
            ))
            return events

        # ─── AssistantMessage ───
        if isinstance(message, AssistantMessage):
            # Captura usage
            if hasattr(message, 'usage') and message.usage:
                usage = message.usage
                if isinstance(usage, dict):
                    state.input_tokens = usage.get('input_tokens', 0)
                    state.output_tokens = usage.get('output_tokens', 0)
                else:
                    state.input_tokens = getattr(usage, 'input_tokens', 0) or 0
                    state.output_tokens = getattr(usage, 'output_tokens', 0) or 0

            # C3: Detectar erros da API
            if hasattr(message, 'error') and message.error:
                error_info = message.error
                error_str = str(error_info).lower()
                error_type_str = error_info.get('type', 'unknown') if isinstance(error_info, dict) else type(error_info).__name__

                logger.warning(
                    f"[AGENT_SDK] API error: type={error_type_str}, error={error_info}"
                )

                if 'rate_limit' in error_str:
                    events.append(StreamEvent(
                        type='error',
                        content="Limite de requisições excedido. Aguardando...",
                        metadata={'error_type': 'rate_limit', 'retryable': True}
                    ))
                elif 'too long' in error_str or 'context' in error_str:
                    events.append(StreamEvent(
                        type='error',
                        content="Conversa muito longa. Tente iniciar uma nova sessão.",
                        metadata={'error_type': 'context_overflow', 'retryable': False}
                    ))
                else:
                    events.append(StreamEvent(
                        type='error',
                        content=f"Erro da API: {error_info}",
                        metadata={'error_type': error_type_str, 'raw_error': str(error_info)[:500]}
                    ))

            # Message ID para deduplicacao
            if hasattr(message, 'id') and message.id:
                state.last_message_id = message.id

            if message.content:
                for block in message.content:
                    # Extended Thinking
                    if isinstance(block, ThinkingBlock):
                        thinking_content = getattr(block, 'thinking', '')
                        if thinking_content:
                            # B2: Buffer para auditoria de deliberacao (instancia)
                            self._last_thinking_content = thinking_content
                            events.append(StreamEvent(
                                type='thinking',
                                content=thinking_content
                            ))
                        continue

                    # Texto
                    if isinstance(block, TextBlock):
                        text_chunk = block.text
                        # Adiciona separador entre segmentos de texto (após tool calls)
                        if state.full_text and state.had_tool_between_texts:
                            text_chunk = '\n\n' + text_chunk
                        state.full_text += text_chunk
                        state.had_tool_between_texts = False
                        events.append(StreamEvent(
                            type='text',
                            content=text_chunk
                        ))

                    # Tool call
                    elif isinstance(block, ToolUseBlock):
                        state.had_tool_between_texts = True
                        tool_call = ToolCall(
                            id=block.id,
                            name=block.name,
                            input=block.input
                        )
                        state.tool_calls.append(tool_call)

                        state.current_tool_start_time = time.time()
                        state.current_tool_name = block.name
                        logger.info(f"[AGENT_SDK] Tool START: {block.name}")

                        tool_description = self._extract_tool_description(
                            block.name, block.input
                        )

                        events.append(StreamEvent(
                            type='tool_call',
                            content=block.name,
                            metadata={
                                'tool_id': block.id,
                                'input': block.input,
                                'description': tool_description
                            }
                        ))

                        # TodoWrite emit
                        if block.name == 'TodoWrite' and block.input:
                            todos = block.input.get('todos', [])
                            if todos:
                                events.append(StreamEvent(
                                    type='todos',
                                    content={'todos': todos},
                                    metadata={'tool_id': block.id}
                                ))
            return events

        # ─── UserMessage (tool results) ───
        if isinstance(message, UserMessage):
            tool_duration_ms = 0
            if state.current_tool_start_time:
                tool_duration_ms = int((time.time() - state.current_tool_start_time) * 1000)
                logger.info(
                    f"[AGENT_SDK] Tool DONE: {state.current_tool_name} {tool_duration_ms}ms"
                )
                state.current_tool_start_time = None

            content = getattr(message, 'content', None)
            if content and isinstance(content, list):
                for block in content:
                    if isinstance(block, ToolResultBlock):
                        result_content = block.content
                        is_error = getattr(block, 'is_error', False) or False
                        tool_use_id = getattr(block, 'tool_use_id', '')

                        if isinstance(result_content, list):
                            result_content = str(result_content)[:500]
                        elif result_content:
                            result_content = str(result_content)[:500]
                        else:
                            result_content = "(sem resultado)"

                        tool_name = next(
                            (tc.name for tc in state.tool_calls if tc.id == tool_use_id),
                            'ferramenta'
                        )

                        if is_error:
                            expected_errors = ['does not exist', 'not found', 'no such file']
                            is_expected = any(err in result_content.lower() for err in expected_errors)
                            if is_expected:
                                logger.debug(f"[AGENT_SDK] Tool '{tool_name}' (esperado): {result_content[:100]}")
                            else:
                                logger.warning(f"[AGENT_SDK] Tool '{tool_name}' erro: {result_content[:200]}")

                        events.append(StreamEvent(
                            type='tool_result',
                            content=result_content,
                            metadata={
                                'tool_use_id': tool_use_id,
                                'tool_name': tool_name,
                                'is_error': is_error,
                                'duration_ms': tool_duration_ms,
                            }
                        ))
            return events

        # ─── ResultMessage (fim) ───
        if isinstance(message, ResultMessage):
            # CRÍTICO: Capturar session_id REAL do SDK para resume
            state.result_session_id = message.session_id
            state.got_result_message = True

            # SDK 0.1.46+: stop_reason indica motivo do encerramento
            stop_reason = getattr(message, 'stop_reason', '') or ''

            # SDK 0.1.51+: errors detalhados (API errors, tool crashes, validation fails)
            result_errors = getattr(message, 'errors', []) or []

            if message.result:
                state.full_text = message.result

            # Capturar usage do ResultMessage (única fonte confiável)
            # G2 (2026-04-15): Extrair tambem cache_read_input_tokens e
            # cache_creation_input_tokens para instrumentar cache hit rate.
            # Campos oficiais do Anthropic API conforme prompt-caching docs.
            if message.usage:
                usage = message.usage
                if isinstance(usage, dict):
                    state.input_tokens = usage.get('input_tokens', state.input_tokens)
                    state.output_tokens = usage.get('output_tokens', state.output_tokens)
                    state.cache_read_tokens = usage.get('cache_read_input_tokens', 0) or 0
                    state.cache_creation_tokens = usage.get('cache_creation_input_tokens', 0) or 0
                else:
                    state.input_tokens = getattr(usage, 'input_tokens', state.input_tokens) or state.input_tokens
                    state.output_tokens = getattr(usage, 'output_tokens', state.output_tokens) or state.output_tokens
                    state.cache_read_tokens = getattr(usage, 'cache_read_input_tokens', 0) or 0
                    state.cache_creation_tokens = getattr(usage, 'cache_creation_input_tokens', 0) or 0

            logger.info(
                f"[AGENT_SDK] ResultMessage | "
                f"stop_reason={stop_reason} | "
                f"cost={message.total_cost_usd} | "
                f"usage={message.usage} | turns={message.num_turns} | "
                f"duration={message.duration_ms}ms | "
                f"tokens_captured=({state.input_tokens},{state.output_tokens})"
                f"{f' | errors={result_errors}' if result_errors else ''}"
            )

            # Detectar interrupt
            is_interrupted = (
                getattr(message, 'subtype', '') in ('interrupted', 'canceled', 'cancelled')
                or (message.is_error and 'interrupt' in str(message.result or '').lower())
            )

            if is_interrupted and not state.done_emitted:
                logger.info(
                    f"[AGENT_SDK] Interrupt detectado | "
                    f"subtype={getattr(message, 'subtype', 'N/A')} | "
                    f"text_so_far={len(state.full_text)} chars"
                )
                events.append(StreamEvent(
                    type='interrupt_ack',
                    content='Operação interrompida pelo usuário',
                ))

            if not state.done_emitted:
                # D6: Self-Correction (skip se interrupt)
                correction = None
                if not is_interrupted:
                    correction = await self._self_correct_response(state.full_text)
                    if correction:
                        events.append(StreamEvent(
                            type='text',
                            content=f"\n\n⚠️ **Observação de validação**: {correction}",
                            metadata={'self_correction': True}
                        ))

                # SDK nativo: structured_output (quando output_format configurado)
                structured_output = getattr(message, 'structured_output', None)
                if structured_output is not None:
                    logger.info(
                        f"[AGENT_SDK] Structured output recebido: "
                        f"type={type(structured_output).__name__} | "
                        f"keys={list(structured_output.keys()) if isinstance(structured_output, dict) else 'N/A'}"
                    )

                state.done_emitted = True
                events.append(StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        # G2 (2026-04-15): cache tokens propagados ate chat.js
                        # para medicao de cache hit rate no dashboard
                        'cache_read_tokens': state.cache_read_tokens,
                        'cache_creation_tokens': state.cache_creation_tokens,
                        'total_cost_usd': getattr(message, 'total_cost_usd', 0) or 0,
                        'session_id': state.result_session_id,
                        'tool_calls': len(state.tool_calls),
                        'self_corrected': correction is not None if correction else False,
                        'interrupted': is_interrupted,
                        'stop_reason': stop_reason,
                        'structured_output': structured_output,
                        'errors': result_errors if result_errors else None,
                    },
                    metadata={'message_id': state.last_message_id or ''}
                ))

            return events

        # Mensagem desconhecida — ignorar silenciosamente
        logger.debug(f"[AGENT_SDK] Mensagem ignorada: {type(message).__name__}")
        return events

    async def stream_response(
        self,
        prompt: str,
        user_name: str = "Usuário",
        model: Optional[str] = None,
        effort_level: str = "off",
        plan_mode: bool = False,
        user_id: int = None,
        document_files: Optional[List[dict]] = None,
        sdk_session_id: Optional[str] = None,
        can_use_tool: Optional[Callable] = None,
        our_session_id: Optional[str] = None,
        output_format: Optional[Dict[str, Any]] = None,
        debug_mode: bool = False,
        resume_messages_fallback: Optional[str] = None,
        thinking_display: Optional[str] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming.

        Usa ClaudeSDKClient persistente via client_pool (daemon thread pool).

        Args:
            prompt: Mensagem do usuário
            user_name: Nome do usuário
            model: Modelo a usar
            effort_level: Nível de esforço do thinking ("off"|"low"|"medium"|"high"|"max")
            plan_mode: Ativar modo somente-leitura
            user_id: ID do usuário (para Memory Tool)
            document_files: Lista de content blocks (image + document) para Vision/PDF nativo
            sdk_session_id: Session ID do SDK para resume (do DB)
            can_use_tool: Callback de permissão
            our_session_id: Nosso UUID de sessão (usado pelo path persistente como pool key)
            output_format: JSON Schema para structured output (SDK nativo)
            debug_mode: Se true E flag USE_STDERR_CALLBACK ativo, captura stderr do CLI
            resume_messages_fallback: XML com mensagens JSONB para injetar se resume falhar

        Yields:
            StreamEvent com tipo e conteúdo
        """
        # Reset contador de falhas por turno (cada turno começa limpo)
        self._tool_failure_counts.clear()

        # ClaudeSDKClient persistente via client_pool.
        async for event in self._stream_response_persistent(
            prompt=prompt,
            user_name=user_name,
            model=model,
            effort_level=effort_level,
            plan_mode=plan_mode,
            user_id=user_id,
            document_files=document_files,
            sdk_session_id=sdk_session_id,
            can_use_tool=can_use_tool,
            our_session_id=our_session_id,
            output_format=output_format,
            debug_mode=debug_mode,
            resume_messages_fallback=resume_messages_fallback,
            thinking_display=thinking_display,
        ):
            yield event

    def _build_options(
        self,
        user_name: str = "Usuário",
        can_use_tool: Optional[Callable] = None,
        max_turns: int = 30,
        model: Optional[str] = None,
        effort_level: str = "off",
        plan_mode: bool = False,
        user_id: int = None,
        output_format: Optional[Dict[str, Any]] = None,
        our_session_id: Optional[str] = None,
        stderr_queue: Optional['queue.SimpleQueue'] = None,
        resume_state: Optional[Dict] = None,
        thinking_display: Optional[str] = None,
    ) -> 'ClaudeAgentOptions':
        """
        Constrói ClaudeAgentOptions para ClaudeSDKClient.

        Configura: model, system_prompt, cwd, allowed_tools (de settings),
        hooks, betas, permission_mode, disallowed_tools, fallback_model.

        Args:
            user_name: Nome do usuário
            can_use_tool: Callback de permissão
            max_turns: Máximo de turnos
            model: Modelo a usar (sobrescreve settings.model)
            effort_level: Nível de esforço do thinking ("off"|"low"|"medium"|"high"|"max")
            plan_mode: Ativar modo somente-leitura
            user_id: ID do usuário (para Memory Tool)
            output_format: JSON Schema para structured output (SDK nativo)
            our_session_id: Nosso UUID de sessão — SDK 0.1.52+ usa como nome do JSONL

        Returns:
            ClaudeAgentOptions configurado
        """
        import os

        # System prompt customizado (com user_id para Memory Tool)
        custom_instructions = self._format_system_prompt(user_name, user_id)

        # Diretório do projeto para carregar Skills
        project_cwd = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            )
        )  # Raiz do projeto: /home/.../frete_sistema

        # Modo de permissão
        # Em ambiente headless (servidor), usar "acceptEdits" para evitar prompts interativos.
        # "default" faz o CLI tentar prompts no stdin (que não existe em servidor)
        # → timeout → "Stream closed" → "Claude Code has been suspended".
        # "acceptEdits" auto-aprova edições; can_use_tool callback controla permissões reais.
        # "bypassPermissions" seria alternativa mas remove TODAS as barreiras de segurança.
        permission_mode = "plan" if plan_mode else "acceptEdits"

        options_dict = {
            # Modelo
            "model": model if model else self.settings.model,

            # Máximo de turnos
            "max_turns": max_turns,

            # Buffer size para JSON messages do subprocess CLI.
            # Default do SDK: 1MB (1_048_576 bytes) — insuficiente para
            # tool results grandes (screenshots base64, HTML pesado).
            # Um screenshot PNG full-page (1280x720) em base64 gera ~1.3-2.6MB.
            # 10MB acomoda screenshots + margem para JSON envelope.
            # FONTE: claude_agent_sdk/_internal/subprocess_cli.py:29
            "max_buffer_size": 10_000_000,  # 10MB

            # System Prompt: depende de USE_CUSTOM_SYSTEM_PROMPT (configurado abaixo)
            # Placeholder — preenchido pelo guard de feature flag
            "system_prompt": None,

            # CWD: Diretório de trabalho para Skills
            "cwd": project_cwd,

            # Setting Sources: Em headless (servidor), carregar apenas "project" para
            # habilitar descoberta de skills (.claude/skills/*/SKILL.md), CLAUDE.md,
            # hooks e permissions do projeto. NÃO carregar "user" para evitar que
            # enabledPlugins pessoais (pyright-lsp, etc.) causem hang no servidor.
            # Ref: https://platform.claude.com/docs/en/agent-sdk/skills
            "setting_sources": ["project"] if permission_mode == "acceptEdits" else ["user", "project"],

            # Tools permitidas — lê de settings.py (fonte única de verdade)
            "allowed_tools": list(self.settings.tools_enabled),

            # Modo de permissão
            "permission_mode": permission_mode,

            # SDK 0.1.26+: Fallback model para resiliência
            "fallback_model": "sonnet",

            # SDK 0.1.26+: Barreira real de segurança
            "disallowed_tools": [
                "NotebookEdit",   # Não há Jupyter notebooks no sistema
            ],

            # Env vars passadas ao subprocess CLI do SDK
            # CLAUDE_CODE_STREAM_CLOSE_TIMEOUT: timeout para hooks/MCP (default 60s).
            # Em ambiente cloud (Render), MCP tools podem demorar mais (API calls, DB queries).
            # Skills complexas (cotação, SQL analítico, Odoo) podem levar até 4 min.
            # FONTE: claude_agent_sdk/_internal/query.py:116
            "env": {
                "CLAUDE_CODE_STREAM_CLOSE_TIMEOUT": "240000",  # 240s (4 min) em ms
                # HOME gravável — Render usa HOME=/opt/render (read-only).
                # CLI tenta salvar .claude.json em $HOME → ENOENT.
                # /tmp é sempre gravável em qualquer ambiente.
                "HOME": "/tmp",
            },
        }

        # SDK 0.1.52+: session_id nativo — pre-declara o UUID do JSONL
        # Permite naming deterministico: JSONL sera ~/.claude/projects/.../{our_session_id}.jsonl
        # Elimina necessidade de capturar sdk_session_id do SystemMessage.
        # IMPORTANTE: CLI exige UUID valido. Sessions Teams usam formato "teams_{id}"
        # que NAO e UUID → CLI rejeita com "Invalid session ID" (exit code 1).
        # Apenas passar session_id quando for UUID valido.
        if our_session_id:
            try:
                import uuid as _uuid
                _uuid.UUID(our_session_id)
                options_dict["session_id"] = our_session_id
            except (ValueError, AttributeError):
                logger.debug(
                    f"[AGENT_CLIENT] session_id '{our_session_id[:20]}...' "
                    "não é UUID válido — CLI gerará próprio ID"
                )

        # =================================================================
        # System Prompt: preset claude_code vs preset operacional
        # Flag: USE_CUSTOM_SYSTEM_PROMPT (default false para rollback seguro)
        # =================================================================
        from ..config.feature_flags import USE_CUSTOM_SYSTEM_PROMPT

        if USE_CUSTOM_SYSTEM_PROMPT:
            # Prompt Architecture v2: string pura (preset_operacional + system_prompt)
            # Elimina ~3-4K tokens do preset claude_code (git, CSS, dev identity)
            options_dict["system_prompt"] = self._build_full_system_prompt(custom_instructions)
            logger.info(
                "[AGENT_CLIENT] System prompt: custom (preset_operacional.md + system_prompt.md)"
            )
        else:
            # Original: preset claude_code + append system_prompt.md
            options_dict["system_prompt"] = {
                "type": "preset",
                "preset": "claude_code",
                "append": custom_instructions
            }
            logger.info("[AGENT_CLIENT] System prompt: preset claude_code + append")

        # =================================================================
        # Agents customizados (.claude/agents/*.md)
        # Permite que sub-agents definidos localmente funcionem via SDK web.
        # Sem isso, Task(subagent_type="raio-x-pedido") falha com
        # "Agent type not found" porque setting_sources=[] impede
        # o CLI de descobrir agents por conta propria.
        # =================================================================
        try:
            from ..config.agent_loader import load_agent_definitions

            agents_dir = os.path.join(project_cwd, ".claude", "agents")
            if os.path.isdir(agents_dir):
                agent_definitions = load_agent_definitions(agents_dir)
                if agent_definitions:
                    options_dict["agents"] = agent_definitions
                    logger.info(
                        f"[AGENT_CLIENT] {len(agent_definitions)} agents carregados: "
                        f"{list(agent_definitions.keys())}"
                    )
        except ImportError:
            logger.debug("[AGENT_CLIENT] agent_loader nao disponivel — agents ignorados")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro ao carregar agents customizados: {e}")

        # Adaptive Thinking via campo nativo `effort` do ClaudeAgentOptions
        # SDK 0.1.36+: `effort` é campo typed no dataclass (Literal["low"|"medium"|"high"|"max"])
        # Substitui o workaround anterior via extra_args["effort"] → --effort CLI flag.
        # Opus tier (4.5, 4.6, 4.7): suporta todos os níveis (low/medium/high/max)
        # Sonnet 4.6/Haiku 4.5: suportam low/medium/high (max → fallback para high no CLI)
        # Opus 4.7: introduz `xhigh` (entre high e max, ideal para coding/agentic) —
        # ainda nao exposto no Literal type do SDK 0.1.60; passar via extra_args se necessario.
        if effort_level and effort_level != "off":
            options_dict["effort"] = effort_level
            logger.info(f"[AGENT_CLIENT] Effort level: {effort_level}")

            # Thinking display (SDK 0.1.65+): controla se o modelo gera texto
            # sumarizado do raciocinio. 'summarized' = tokens extras + latencia.
            # 'omitted' = pula a geracao (mesmo resultado final, mais rapido).
            #
            # Precedencia: thinking_display (param, normalmente user preference)
            # > AGENT_THINKING_DISPLAY (flag env, default "omitted") > off (skip).
            from ..config.feature_flags import AGENT_THINKING_DISPLAY
            effective_display = (
                (thinking_display or "").lower()
                or AGENT_THINKING_DISPLAY
            )
            if effective_display in ("summarized", "omitted"):
                options_dict["thinking"] = {
                    "type": "adaptive",
                    "display": effective_display,
                }
                logger.info(
                    f"[AGENT_CLIENT] Thinking display: {effective_display} "
                    f"(source={'user_pref' if thinking_display else 'env_flag'}, "
                    "SDK 0.1.65+ --thinking-display)"
                )

        # Callback de permissão
        if can_use_tool:
            options_dict["can_use_tool"] = can_use_tool

        # Structured Output (SDK nativo)
        # Força a resposta final do agente a seguir um JSON Schema.
        # Útil para fluxos programáticos (API, dashboard, automação).
        # ResultMessage.structured_output conterá o JSON parseado.
        if output_format:
            options_dict["output_format"] = output_format
            logger.info(f"[AGENT_CLIENT] Structured output ativo: {output_format.get('type', 'unknown')}")

        # Stderr Callback (SEMPRE ativo)
        # Registra callback sincrono que captura linhas do CLI subprocess stderr.
        # Linhas vao para a stderr_queue (thread-safe SimpleQueue), drenada no
        # loop de streaming. Em debug_mode, enviadas como StreamEvent(type='stderr').
        # Em modo normal, apenas logadas para diagnostico de ProcessError.
        # NOTA: Antes condicional (debug_mode + USE_STDERR_CALLBACK). Agora sempre
        # ativo para capturar causa raiz de exit=1 (SDK hardcoda "Check stderr..."
        # no ProcessError e nunca propaga o stderr real).
        if stderr_queue is not None:
            def _stderr_callback(line: str):
                stderr_queue.put_nowait(line)
            options_dict["stderr"] = _stderr_callback
            options_dict["extra_args"] = {"debug-to-stderr": None}
            logger.debug("[AGENT_CLIENT] Stderr callback ativo com debug-to-stderr")

        # =================================================================
        # FEATURE FLAGS: Quick Wins (ativados via env vars)
        # =================================================================
        from ..config.feature_flags import (
            USE_BUDGET_CONTROL, MAX_BUDGET_USD,
            USE_EXTENDED_CONTEXT,
            USE_CONTEXT_CLEARING,
            USE_PROMPT_CACHING,
        )

        # Budget Control nativo
        if USE_BUDGET_CONTROL:
            options_dict["max_budget_usd"] = MAX_BUDGET_USD
            logger.info(f"[AGENT_CLIENT] Budget control nativo: max ${MAX_BUDGET_USD}/request")

        # Extended Context (1M tokens)
        # Opus 4.7/4.6 e Sonnet 4.6: 1M tokens NATIVO — sem beta header necessário.
        # Opus 4.7 mantém 1M context window ao mesmo preço padrão (sem long-context premium).
        # Flag mantida apenas para log/documentação. Modelos atuais usam 1M automaticamente.
        if USE_EXTENDED_CONTEXT:
            current_model = str(options_dict.get("model", self.settings.model)).lower()
            logger.info(
                f"[AGENT_CLIENT] Extended Context: modelo '{current_model}' — "
                f"1M tokens nativo (Opus 4.7/4.6, Sonnet 4.6), sem beta header"
            )

        # Context Clearing automático
        # NOTA: clear-thinking e clear-tool-uses foram promovidos a GA.
        # Não precisam mais de beta header (removidos em 2026-02).
        if USE_CONTEXT_CLEARING:
            logger.info("[AGENT_CLIENT] Context Clearing habilitado (GA — sem beta header)")

        # Prompt Caching
        # NOTA: prompt-caching foi promovido a GA.
        # Não precisa mais de beta header (removido em 2026-02).
        if USE_PROMPT_CACHING:
            logger.info("[AGENT_CLIENT] Prompt Caching habilitado (GA — sem beta header)")

        # =================================================================
        # Hooks SDK formais para auditoria
        # =================================================================
        try:
            from .hooks import build_hooks
            options_dict["hooks"] = build_hooks(
                user_id=user_id,
                user_name=user_name,
                tool_failure_counts=self._tool_failure_counts,
                get_last_thinking=lambda: self._last_thinking_content,
                get_model_name=lambda: str(self.settings.model),
                set_injected_ids=lambda ids: setattr(self, '_last_injected_memory_ids', ids),
                resume_state=resume_state,
            )
            hooks_list = list(options_dict["hooks"].keys())
            logger.debug(
                f"[AGENT_CLIENT] Hooks SDK configurados: {', '.join(hooks_list)}"
            )
        except (ImportError, Exception) as e:
            logger.warning(f"[AGENT_CLIENT] Hooks SDK não disponíveis: {e}")

        # =================================================================
        # MCP Servers (Custom Tools in-process)
        # Helper + glob patterns — CLI resolve "mcp__name__*" automaticamente
        # =================================================================
        def _register_mcp(name: str, server, user_id_setter=None) -> bool:
            """Registra MCP server com glob pattern em allowed_tools."""
            if server is None:
                logger.debug(f"[AGENT_CLIENT] {name}_server é None — módulo não disponível")
                return False
            if user_id and user_id_setter:
                user_id_setter(user_id)
            options_dict.setdefault("mcp_servers", {})[name] = server
            options_dict.setdefault("allowed_tools", []).append(f"mcp__{name}__*")
            return True

        # SQL (Text-to-SQL com bloqueio condicional de tabelas pessoal_*)
        try:
            from ..tools.text_to_sql_tool import sql_server, set_current_user_id as set_sql_user_id
            if _register_mcp("sql", sql_server, set_sql_user_id):
                logger.info("[AGENT_CLIENT] MCP 'sql' registrada")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP sql não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP sql: {e}")

        # Memory (memória persistente — 11 operações)
        try:
            from ..tools.memory_mcp_tool import memory_server, set_current_user_id
            if _register_mcp("memory", memory_server, set_current_user_id):
                logger.info("[AGENT_CLIENT] MCP 'memory' registrada (11 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP memory não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP memory: {e}")

        # Schema (descoberta de schema — 2 operações)
        try:
            from ..tools.schema_mcp_tool import schema_server
            if _register_mcp("schema", schema_server):
                logger.info("[AGENT_CLIENT] MCP 'schema' registrada (2 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP schema não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP schema: {e}")

        # Sessions (busca em sessões anteriores — 4 operações)
        try:
            from ..tools.session_search_tool import sessions_server
            from ..tools.session_search_tool import set_current_user_id as set_session_search_user_id
            if _register_mcp("sessions", sessions_server, set_session_search_user_id):
                logger.info("[AGENT_CLIENT] MCP 'sessions' registrada (4 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP sessions não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP sessions: {e}")

        # Render (logs e métricas — 3 operações)
        try:
            from ..tools.render_logs_tool import render_server
            if _register_mcp("render", render_server):
                logger.info("[AGENT_CLIENT] MCP 'render' registrada (3 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP render não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP render: {e}")

        # Browser (Playwright headless — SSW + Atacadão, 12 operações)
        try:
            from ..tools.playwright_mcp_tool import browser_server
            if _register_mcp("browser", browser_server):
                logger.info("[AGENT_CLIENT] MCP 'browser' registrada (12 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP browser não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP browser: {e}")

        # Routes (busca semântica de rotas — 1 operação)
        try:
            from ..tools.routes_search_tool import routes_server
            if _register_mcp("routes", routes_server):
                logger.info("[AGENT_CLIENT] MCP 'routes' registrada (1 operação)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP routes não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP routes: {e}")

        # Teams Card (Adaptive Cards estruturados — Fase 1 MVP 2026-04-22)
        try:
            from ..tools.teams_card_tool import teams_card_server
            if _register_mcp("teams_card", teams_card_server):
                logger.info("[AGENT_CLIENT] MCP 'teams_card' registrada (1 operação)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP teams_card não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP teams_card: {e}")

        # Log de diagnóstico — útil para validar configuração em produção
        logger.info(
            f"[AGENT_CLIENT] Options: model={options_dict.get('model')}, "
            f"permission_mode={permission_mode}, "
            f"mcp_servers={list(options_dict.get('mcp_servers', {}).keys())}, "
            f"allowed_tools_count={len(options_dict.get('allowed_tools', []))}"
        )

        return ClaudeAgentOptions(**options_dict)

    async def _stream_response_persistent(
        self,
        prompt: str,
        user_name: str = "Usuário",
        model: Optional[str] = None,
        effort_level: str = "off",
        plan_mode: bool = False,
        user_id: int = None,
        document_files: Optional[List[dict]] = None,
        sdk_session_id: Optional[str] = None,
        can_use_tool: Optional[Callable] = None,
        our_session_id: Optional[str] = None,
        output_format: Optional[Dict[str, Any]] = None,
        debug_mode: bool = False,
        resume_messages_fallback: Optional[str] = None,
        thinking_display: Optional[str] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming usando ClaudeSDKClient persistente.

        ARQUITETURA v3 (flag USE_PERSISTENT_SDK_CLIENT=true):
        - ClaudeSDKClient mantido vivo entre turnos (daemon thread pool)
        - get_or_create_client() obtém ou cria client para a sessão
        - client.query() envia prompt, receive_response() recebe mensagens
        - ~2x menor latência vs query() (sem overhead spawn/destroy CLI)
        - Sem streaming_done_event (eliminado com v2)

        INVARIANTE: Emite os MESMOS StreamEvents na MESMA ordem que _stream_response().

        Args:
            prompt: Mensagem do usuário
            user_name: Nome do usuário
            model: Modelo a usar
            effort_level: Nível de esforço do thinking ("off"|"low"|"medium"|"high"|"max")
            plan_mode: Ativar modo somente-leitura
            user_id: ID do usuário (para Memory Tool)
            document_files: Lista de content blocks (image + document) para Vision/PDF nativo
            sdk_session_id: SDK session ID para resume (na primeira conexão)
            can_use_tool: Callback de permissão
            our_session_id: Nosso UUID de sessão (chave do pool)
            resume_messages_fallback: XML com mensagens JSONB para injetar se resume falhar

        Yields:
            StreamEvent com tipo e conteúdo
        """
        from .client_pool import get_or_create_client, get_pooled_client

        # ─── Estado de parsing ───
        state = _StreamParseState()

        # ─── Stderr callback queue (SEMPRE ativo) ───
        # SimpleQueue é thread-safe: callback (sync, CLI thread) → put_nowait()
        # Loop de streaming (async) → get_nowait() entre mensagens SDK
        # NOTA: Antes era condicional (debug_mode + USE_STDERR_CALLBACK).
        # Agora sempre ativo para capturar causa raiz de ProcessError exit=1,
        # cujo stderr era perdido (hardcoded "Check stderr output for details" na SDK).
        # Em modo normal, linhas de stderr são apenas logadas (não enviadas ao frontend).
        # Em debug_mode, também são enviadas como StreamEvent('stderr').
        stderr_q: queue.SimpleQueue = queue.SimpleQueue()

        # ─── Estado compartilhado: resume fallback ───
        # Dict mutável: se resume falhar, stream seta failed=True.
        # Hook UserPromptSubmit injeta fallback no additionalContext.
        resume_state = {
            'failed': False,
            'fallback': resume_messages_fallback,
        }

        # ─── Construir options ───
        options = self._build_options(
            user_name=user_name,
            user_id=user_id,
            model=model,
            effort_level=effort_level,
            plan_mode=plan_mode,
            can_use_tool=can_use_tool,
            output_format=output_format,
            our_session_id=our_session_id,
            stderr_queue=stderr_q,
            resume_state=resume_state,
            thinking_display=thinking_display,
        )

        # ─── SDK 0.1.64 SessionStore (Fase B cutover — flag default ON) ───
        # Injecao async APOS _build_options (sync) via dataclasses.replace.
        # Fase B (2026-04-21): criterio C4 removido, flag aplica UNIVERSALMENTE.
        # Sessions pre-existentes foram migradas pelo script
        # scripts/migrations/2026_04_21_migrar_session_persistence_to_store.py.
        #
        # Rollback: AGENT_SDK_SESSION_STORE_ENABLED=false + redeploy (0 downtime).
        from ..config.feature_flags import (
            AGENT_SDK_SESSION_STORE_ENABLED,
            AGENT_SDK_SESSION_STORE_LOAD_TIMEOUT_MS,
        )
        if AGENT_SDK_SESSION_STORE_ENABLED:
            try:
                from dataclasses import replace as _dc_replace

                from claude_agent_sdk import project_key_for_directory

                from .session_store_adapter import get_or_create_session_store
                _store = await get_or_create_session_store()
                options = _dc_replace(
                    options,
                    session_store=_store,
                    load_timeout_ms=AGENT_SDK_SESSION_STORE_LOAD_TIMEOUT_MS,
                )
                logger.info(
                    f"[SESSION_STORE] ENABLED: {(our_session_id or 'pending')[:12]}... "
                    f"load_timeout={AGENT_SDK_SESSION_STORE_LOAD_TIMEOUT_MS}ms"
                )

                # FIX P1 (FaseB.2 review): probe store.load() quando resume_id
                # setado — se store vazio (session pre-existente nao migrada OU
                # fora do criterio), marcar resume_state['failed']=True para
                # disparar fallback XML ANTES do subprocess spawnar sem --resume.
                # Sem isso, SDK materialize retorna None silenciosamente e
                # subprocess spawna como sessao nova SEM dispatch de ProcessError —
                # fallback XML nunca ativa e contexto e perdido.
                if sdk_session_id:
                    try:
                        import uuid as _uuid_probe
                        _uuid_probe.UUID(sdk_session_id)  # valida UUID
                        _pk = project_key_for_directory(options.cwd) if options.cwd else project_key_for_directory()
                        _existing = await _store.load({
                            "project_key": _pk,
                            "session_id": sdk_session_id,
                        })
                        if _existing is None and resume_state is not None:
                            resume_state['failed'] = True
                            logger.warning(
                                f"[SESSION_STORE] probe: session {sdk_session_id[:12]}... "
                                f"nao esta no store — marcando resume_state['failed']=True "
                                f"para acionar fallback XML"
                            )
                    except (ValueError, AttributeError):
                        pass  # UUID invalido — nao e session do store
                    except Exception as _probe_err:
                        logger.debug(
                            f"[SESSION_STORE] probe falhou (ignorado): {_probe_err}"
                        )
            except Exception as _store_err:
                # Em caso de falha: SDK spawna sem session_store, sinalizar
                # fallback XML para o hook UserPromptSubmit injetar contexto.
                if resume_state is not None:
                    resume_state['failed'] = True
                logger.error(
                    f"[SESSION_STORE] init falhou — stream sem store "
                    f"(fallback XML via UserPromptSubmit hook): {_store_err}",
                    exc_info=True,
                )

        # ─── RESUME: só na primeira conexão ───
        # Se o client já existe no pool (reutilização), o CLI subprocess
        # já tem o contexto da conversa. Resume só é necessário quando
        # criamos um novo client (primeiro turno ou após idle cleanup).
        # IMPORTANTE: Só resume se sdk_session_id vier do DB (sessão real).
        # Fallback para our_session_id causava --resume com JSONL inexistente
        # em sessões novas → CLI exit code 1 (ProcessError).
        pool_key = our_session_id or ''
        existing = get_pooled_client(pool_key)
        resume_id = sdk_session_id
        # Validar que resume_id é UUID válido — dados envenenados no DB
        # (ex: "teams_19:xxx") causam exit code 1 permanente se não filtrados.
        if resume_id:
            try:
                import uuid as _uuid_check
                _uuid_check.UUID(resume_id)
            except (ValueError, AttributeError):
                logger.warning(
                    f"[AGENT_SDK_PERSISTENT] sdk_session_id inválido (não UUID), "
                    f"ignorando resume: {resume_id[:20]}..."
                )
                resume_id = None
        if not existing and resume_id:
            options = self._with_resume(options, resume_id)
            logger.info(f"[AGENT_SDK_PERSISTENT] Resuming session: {resume_id[:12]}...")

        # ─── Emitir init sintético ───
        state.result_session_id = sdk_session_id or our_session_id
        yield StreamEvent(
            type='init',
            content={'session_id': sdk_session_id or 'pending'},
            metadata={
                'timestamp': agora_utc_naive().isoformat(),
                'resume': bool(sdk_session_id),
                'persistent': True,
            }
        )

        try:
            # ─── Obter ou criar client do pool ───
            # Fix 3: Se connect() com resume falha (JSONL inexistente após
            # reciclagem de worker), retry sem resume para quebrar ciclo vicioso.
            # Sem isso: resume falha → sem transcript → próximo resume falha → loop.
            try:
                pooled = await get_or_create_client(
                    session_id=pool_key,
                    options=options,
                    user_id=user_id or 0,
                )
            except ProcessError as pe:
                exit_code = getattr(pe, 'exit_code', None)
                # Drenar stderr para diagnostico do resume failure
                _resume_stderr = []
                while True:
                    try:
                        _resume_stderr.append(stderr_q.get_nowait())
                    except queue.Empty:
                        break
                if _resume_stderr:
                    logger.warning(
                        f"[AGENT_SDK_PERSISTENT] Resume stderr "
                        f"({len(_resume_stderr)} lines):\n"
                        f"{chr(10).join(_resume_stderr)[:1000]}"
                    )
                if resume_id and exit_code == 1:
                    logger.warning(
                        f"[AGENT_SDK_PERSISTENT] Resume falhou (exit={exit_code}), "
                        f"retentando sem resume | session={pool_key[:8]}..."
                    )
                    # Notificar frontend que o contexto foi perdido
                    yield StreamEvent(
                        type='warning',
                        content='Não foi possível restaurar o contexto da sessão anterior. '
                                'A conversa continua sem o histórico completo.',
                        metadata={'reason': 'resume_failed', 'exit_code': exit_code}
                    )
                    # Sinalizar para o hook injetar fallback de mensagens
                    resume_state['failed'] = True
                    from dataclasses import replace as _dc_replace
                    options = _dc_replace(options, resume=None, fork_session=False, session_id=None)
                    # Deletar JSONLs stale para evitar que CLI ache arquivo corrompido
                    try:
                        from .session_persistence import _get_session_path
                        import os as _os
                        for _stale_id in [pool_key, resume_id]:
                            if _stale_id:
                                _stale_path = _get_session_path(_stale_id)
                                if _os.path.exists(_stale_path):
                                    _os.remove(_stale_path)
                                    logger.info(
                                        f"[AGENT_SDK_PERSISTENT] Stale JSONL deleted: "
                                        f"{_stale_id[:8]}..."
                                    )
                    except Exception as e:
                        logger.debug(f"[AGENT_SDK] Stale JSONL cleanup falhou (ignorado): {e}")
                    pooled = await get_or_create_client(
                        session_id=pool_key,
                        options=options,
                        user_id=user_id or 0,
                    )
                else:
                    raise  # Re-raise se não é falha de resume

            # ─── Propagar sdk_session_id para o PooledClient (F5: cleanup JSONL) ───
            if resume_id and not pooled.sdk_session_id:
                pooled.sdk_session_id = resume_id

            # ─── Ajustar model/permission se client já existia ───
            current_model = model or self.settings.model
            if existing and existing.connected:
                # Client reutilizado — stderr callback nao pode ser reaplicado.
                # O ClaudeSDKClient foi criado com as options originais (primeira conexao).
                # Stderr lines da sessao anterior podem ir para queue anterior (memory leak leve).
                if debug_mode:
                    yield StreamEvent(
                        type='stderr',
                        content='[INFO] Client reutilizado do pool. '
                                'Stderr capturado pela conexao original.'
                    )
                # Client reutilizado — aplicar mudanças de configuração
                try:
                    await pooled.client.set_model(current_model)
                except Exception as model_err:
                    logger.warning(
                        f"[AGENT_SDK_PERSISTENT] set_model ignorado: {model_err}"
                    )
                permission_mode = "plan" if plan_mode else "acceptEdits"
                try:
                    await pooled.client.set_permission_mode(permission_mode)
                except Exception as perm_err:
                    logger.warning(
                        f"[AGENT_SDK_PERSISTENT] set_permission_mode ignorado: {perm_err}"
                    )

            # ─── Preparar prompt para query() ───
            if document_files:
                # Content blocks (image + document) requerem AsyncIterable
                async def _content_prompt():
                    content_blocks = list(document_files) + [{"type": "text", "text": prompt}]
                    yield {"type": "user", "message": {"role": "user", "content": content_blocks}}
                query_prompt = _content_prompt()
            else:
                # Texto puro: string é suficiente
                query_prompt = prompt

            # ─── STREAMING: query() + receive_response() ───
            # asyncio.Lock serializa chamadas no mesmo client (DC-1, R08)
            async with pooled.lock:
                pooled.last_used = time.time()

                logger.info(
                    f"[AGENT_SDK_PERSISTENT] query() | "
                    f"session={pool_key[:8]}... | "
                    f"model={current_model} | "
                    f"reuse={'yes' if (existing and existing.connected) else 'new'} | "
                    f"blocks={len(document_files) if document_files else 0}"
                )

                # Enviar prompt
                await pooled.client.query(query_prompt)

                # Receber resposta (termina após ResultMessage)
                async for message in pooled.client.receive_response():
                    # Drenar stderr lines acumuladas (thread-safe SimpleQueue)
                    while True:
                        try:
                            line = stderr_q.get_nowait()
                            if debug_mode:
                                yield StreamEvent(type='stderr', content=line)
                        except queue.Empty:
                            break
                    for event in await self._parse_sdk_message(message, state):
                        yield event
                    # Propagar sdk_session_id para o PooledClient (F5: cleanup JSONL)
                    if state.result_session_id and not pooled.sdk_session_id:
                        pooled.sdk_session_id = state.result_session_id

            # ─── Drain final de stderr (últimas linhas após receive_response) ───
            while True:
                try:
                    line = stderr_q.get_nowait()
                    if debug_mode:
                        yield StreamEvent(type='stderr', content=line)
                except queue.Empty:
                        break

            # ─── Fallback done (sem ResultMessage) ───
            if not state.done_emitted:
                correction = await self._self_correct_response(state.full_text)
                if correction:
                    yield StreamEvent(
                        type='text',
                        content=f"\n\n⚠️ **Observação de validação**: {correction}",
                        metadata={'self_correction': True}
                    )

                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id if state.got_result_message else None,
                        'tool_calls': len(state.tool_calls),
                        'self_corrected': correction is not None if correction else False,
                    }
                )

        except ProcessError as e:
            elapsed_total = time.time() - state.stream_start_time
            exit_code = getattr(e, 'exit_code', None)

            # Drenar stderr_q para capturar causa raiz REAL do crash.
            # A SDK hardcoda "Check stderr output for details" no ProcessError.stderr
            # mas o stderr real foi capturado pelo callback → stderr_q.
            # Sem este drain, as ultimas linhas (que explicam o crash) sao perdidas.
            real_stderr_lines = []
            while True:
                try:
                    line = stderr_q.get_nowait()
                    real_stderr_lines.append(line)
                except queue.Empty:
                    break

            if real_stderr_lines:
                real_stderr = '\n'.join(real_stderr_lines)
                logger.error(
                    f"[AGENT_SDK_PERSISTENT] ProcessError {elapsed_total:.1f}s | "
                    f"exit={exit_code} | REAL stderr ({len(real_stderr_lines)} lines):\n"
                    f"{real_stderr[:2000]}"
                )
                if debug_mode:
                    for line in real_stderr_lines:
                        yield StreamEvent(type='stderr', content=line)
            else:
                stderr = getattr(e, 'stderr', '') or ''
                logger.error(
                    f"[AGENT_SDK_PERSISTENT] ProcessError {elapsed_total:.1f}s | "
                    f"exit={exit_code} | stderr={stderr[:500]} | msg={e}"
                )
            yield StreamEvent(
                type='error',
                content=f"Erro de processo (código {exit_code}). Tente novamente." if exit_code else str(e),
                metadata={'error_type': 'process_error', 'exit_code': exit_code,
                          'elapsed_seconds': elapsed_total, 'last_tool': state.current_tool_name}
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': state.full_text, 'input_tokens': state.input_tokens,
                             'output_tokens': state.output_tokens, 'total_cost_usd': 0,
                             'session_id': state.result_session_id if state.got_result_message else None,
                             'tool_calls': len(state.tool_calls), 'error_recovery': True},
                    metadata={'error_type': 'process_error'}
                )

            # Evictar client morto do pool para que próximo request crie um novo
            try:
                from .client_pool import _registry, _registry_lock
                with _registry_lock:
                    evicted = _registry.pop(pool_key, None)
                if evicted:
                    evicted.connected = False
                    logger.info(
                        f"[AGENT_SDK_PERSISTENT] Dead client evicted after ProcessError: "
                        f"{pool_key[:8]}..."
                    )
            except Exception as e:
                logger.debug(f"[AGENT_SDK] Pool eviction falhou (ignorado): {e}")

        except CLINotFoundError as e:
            # CLINotFoundError é subclasse de CLIConnectionError — DEVE vir antes
            elapsed_total = time.time() - state.stream_start_time
            logger.critical(f"[AGENT_SDK_PERSISTENT] CLI não encontrada {elapsed_total:.1f}s: {e}")
            yield StreamEvent(
                type='error',
                content="Erro crítico: CLI do agente não encontrada.",
                metadata={'error_type': 'cli_not_found', 'elapsed_seconds': elapsed_total}
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': state.full_text, 'input_tokens': state.input_tokens,
                             'output_tokens': state.output_tokens, 'total_cost_usd': 0,
                             'session_id': state.result_session_id if state.got_result_message else None,
                             'error_recovery': True},
                    metadata={'error_type': 'cli_not_found'}
                )


        except CLIConnectionError as e:
            # Fix PYTHON-FLASK-J/H: CLI subprocess killed by SIGTERM (gunicorn worker
            # recycling). Catch explicitly to: (1) log as warning not error since it's
            # expected during deploys, (2) evict dead client from pool, (3) emit clean
            # error+done so Teams stream terminates immediately instead of timing out
            # (fixes PYTHON-FLASK-G cascade).
            elapsed_total = time.time() - state.stream_start_time
            logger.warning(
                f"[AGENT_SDK_PERSISTENT] CLIConnectionError {elapsed_total:.1f}s | "
                f"msg={e} | pool_key={pool_key[:8]}... | "
                f"Provável reciclagem de worker (SIGTERM)"
            )

            # Evict dead client from pool to force fresh connection on retry.
            # Subprocess already dead — just remove registry entry (no disconnect needed).
            try:
                from .client_pool import _registry, _registry_lock
                with _registry_lock:
                    evicted = _registry.pop(pool_key, None)
                if evicted:
                    evicted.connected = False
                    logger.info(f"[AGENT_SDK_PERSISTENT] Dead client evicted from pool: {pool_key[:8]}...")
            except Exception as evict_err:
                logger.debug(f"[AGENT_SDK_PERSISTENT] Pool eviction ignored: {evict_err}")

            # Return partial text if any was collected before the crash
            user_msg = state.full_text if state.full_text else (
                "O processo do agente foi interrompido (reciclagem do servidor). "
                "Tente novamente."
            )
            yield StreamEvent(
                type='error',
                content=user_msg if not state.full_text else (
                    "O processo do agente foi interrompido. Resposta parcial acima."
                ),
                metadata={
                    'error_type': 'cli_connection_error',
                    'elapsed_seconds': elapsed_total,
                    'last_tool': state.current_tool_name,
                    'partial_text_len': len(state.full_text),
                }
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id if state.got_result_message else None,
                        'tool_calls': len(state.tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': 'cli_connection_error'}
                )


        except CLIJSONDecodeError as e:
            elapsed_total = time.time() - state.stream_start_time
            logger.error(f"[AGENT_SDK_PERSISTENT] JSON decode error {elapsed_total:.1f}s: {e}")
            yield StreamEvent(
                type='error',
                content="Erro ao processar resposta do agente. Tente novamente.",
                metadata={'error_type': 'json_decode_error', 'elapsed_seconds': elapsed_total}
            )
            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': state.full_text, 'input_tokens': state.input_tokens,
                             'output_tokens': state.output_tokens, 'total_cost_usd': 0,
                             'session_id': state.result_session_id if state.got_result_message else None,
                             'error_recovery': True},
                    metadata={'error_type': 'json_decode_error'}
                )

        except BaseExceptionGroup as eg:
            elapsed_total = time.time() - state.stream_start_time
            sub_exceptions = list(eg.exceptions)
            sub_messages = [f"{type(se).__name__}: {se}" for se in sub_exceptions]

            logger.error(
                f"[AGENT_SDK_PERSISTENT] ExceptionGroup {elapsed_total:.1f}s | "
                f"{len(sub_exceptions)} sub-exceptions: {'; '.join(sub_messages[:3])}",
                exc_info=True
            )

            first_error = sub_exceptions[0] if sub_exceptions else eg
            error_msg = str(first_error)

            user_message = "Erro temporário ao executar ferramentas. Tente novamente."
            if 'timeout' in error_msg.lower():
                user_message = "Tempo limite excedido. Tente uma consulta mais simples."
            elif 'connection' in error_msg.lower():
                user_message = "Erro de conexão com a API. Tente novamente em alguns segundos."

            yield StreamEvent(
                type='error',
                content=user_message,
                metadata={
                    'error_type': 'exception_group',
                    'sub_exception_count': len(sub_exceptions),
                    'original_error': error_msg[:500],
                    'elapsed_seconds': elapsed_total,
                    'last_tool': state.current_tool_name,
                }
            )

            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id if state.got_result_message else None,
                        'tool_calls': len(state.tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': 'exception_group'}
                )

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            elapsed_total = time.time() - state.stream_start_time
            logger.error(
                f"[AGENT_SDK_PERSISTENT] {error_type} {elapsed_total:.1f}s: {error_msg}",
                exc_info=True
            )

            user_message = error_msg
            if 'timeout' in error_msg.lower():
                user_message = "Tempo limite excedido. Tente uma consulta mais simples."
            elif 'connection' in error_msg.lower():
                user_message = "Erro de conexão com a API. Tente novamente em alguns segundos."

            yield StreamEvent(
                type='error',
                content=user_message,
                metadata={
                    'error_type': error_type,
                    'original_error': error_msg[:500],
                    'elapsed_seconds': elapsed_total,
                    'last_tool': state.current_tool_name,
                }
            )

            if not state.done_emitted:
                state.done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={
                        'text': state.full_text,
                        'input_tokens': state.input_tokens,
                        'output_tokens': state.output_tokens,
                        'total_cost_usd': 0,
                        'session_id': state.result_session_id if state.got_result_message else None,
                        'tool_calls': len(state.tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': error_type}
                )

    # ─── v2 dead code removido (2026-04-04) ───
    # _stream_response() e _make_streaming_prompt() deletados.
    # Eram o path v2 (query() + resume), desligado em 2026-03-27.
    # Para referencia historica: git log --all -p -- app/agente/sdk/client.py

    # ─── Metodos utilitarios ───

    @staticmethod
    def _with_resume(options: 'ClaudeAgentOptions', sdk_session_id: str) -> 'ClaudeAgentOptions':
        """
        Retorna cópia do options com resume configurado.

        Resume limpo: --resume X sem --session-id (evita --fork-session).

        Contexto: session_id é setado em build_options (SDK 0.1.52+) para naming
        deterministico do JSONL no primeiro turno. Mas ao resumir, --session-id +
        --resume exige --fork-session, e "forkar X para X" causa exit code 1.
        Solução: limpar session_id ao resumir. --resume X sozinho é suficiente —
        CLI carrega {X}.jsonl e continua a mesma sessão.

        Args:
            options: ClaudeAgentOptions original
            sdk_session_id: Session ID do SDK para resume

        Returns:
            Novo ClaudeAgentOptions com resume=sdk_session_id (session_id limpo)
        """
        from dataclasses import replace
        return replace(options, resume=sdk_session_id, session_id=None, fork_session=False)

    async def get_response(
        self,
        prompt: str,
        user_name: str = "Usuário",
        model: Optional[str] = None,
        effort_level: str = "off",
        sdk_session_id: Optional[str] = None,
        can_use_tool: Optional[Callable] = None,
        user_id: Optional[int] = None,
        our_session_id: Optional[str] = None,
        resume_messages_fallback: Optional[str] = None,
        # LEGADO: aceitar pooled_client para compatibilidade (ignorado)
        pooled_client: Any = None,
    ) -> AgentResponse:
        """
        Obtém resposta completa (não streaming).

        Args:
            prompt: Mensagem do usuário
            user_name: Nome do usuário
            model: Modelo a usar
            effort_level: Nível de esforço do thinking ("off"|"low"|"medium"|"high"|"max")
            sdk_session_id: Session ID do SDK para resume
            can_use_tool: Callback de permissão
            user_id: ID do usuário (para Memory Tool e hooks)
            our_session_id: Nosso UUID de sessão (chave do pool para path persistente)
            resume_messages_fallback: XML com ultimas 10 msgs JSONB para injetar
                via UserPromptSubmit hook se resume falhar (defense in depth —
                FaseB.1 review fix, previne perda de contexto em sessions Teams
                nao migradas ao store).
            pooled_client: LEGADO — ignorado

        Returns:
            AgentResponse completa
        """
        full_text = ""
        tool_calls = []
        input_tokens = 0
        output_tokens = 0
        stop_reason = ""
        result_session_id = sdk_session_id
        errors = []  # Fix 2c: Capturar error events
        # Fase 4 (2026-04-21): cache tokens + custo para observabilidade granular
        cache_read_tokens = 0
        cache_creation_tokens = 0
        total_cost_usd = 0.0

        async for event in self.stream_response(
            prompt=prompt,
            user_name=user_name,
            model=model,
            effort_level=effort_level,
            sdk_session_id=sdk_session_id,
            can_use_tool=can_use_tool,
            user_id=user_id,
            our_session_id=our_session_id,
            resume_messages_fallback=resume_messages_fallback,
        ):
            if event.type == 'init':
                result_session_id = event.content.get('session_id')
            elif event.type == 'text':
                full_text += event.content
            elif event.type == 'error':
                # Fix 2c: Capturar mensagens de erro para montar texto sintetico
                error_content = event.content if isinstance(event.content, str) else str(event.content)
                errors.append(error_content)
                logger.warning(f"[AGENT_CLIENT] Error event em get_response: {error_content[:200]}")
            elif event.type == 'tool_call':
                tool_calls.append(ToolCall(
                    id=event.metadata.get('tool_id', ''),
                    name=event.content,
                    input=event.metadata.get('input', {})
                ))
            elif event.type == 'done':
                input_tokens = event.content.get('input_tokens', 0)
                output_tokens = event.content.get('output_tokens', 0)
                stop_reason = event.content.get('stop_reason', '')
                # Fase 4 (2026-04-21): extrair cache + custo do done event
                cache_read_tokens = event.content.get('cache_read_tokens', 0) or 0
                cache_creation_tokens = event.content.get('cache_creation_tokens', 0) or 0
                total_cost_usd = event.content.get('total_cost_usd', 0.0) or 0.0
                # Captura session_id real do done
                done_session_id = event.content.get('session_id')
                if done_session_id:
                    result_session_id = done_session_id

        # Fix 2c: Se full_text vazio mas houve errors, montar texto sintetico
        # Evita retornar AgentResponse(text="") que vira repr() no Teams
        if not full_text and errors:
            full_text = "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente."
            logger.warning(
                f"[AGENT_CLIENT] get_response: text vazio com {len(errors)} errors. "
                f"Usando texto sintetico. Errors: {'; '.join(errors[:3])}"
            )

        return AgentResponse(
            text=full_text,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=stop_reason,
            session_id=result_session_id,
            cache_read_tokens=cache_read_tokens,
            cache_creation_tokens=cache_creation_tokens,
            total_cost_usd=total_cost_usd,
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde da conexão com API.

        Usa models.retrieve() (zero tokens, ~200ms) em vez de
        messages.create() (~2s, gasta tokens).

        Returns:
            Dict com status da conexão
        """
        try:
            model_info = self._anthropic_client.models.retrieve(
                model_id=self.settings.model
            )

            return {
                'status': 'healthy',
                'model': model_info.id,
                'api_connected': True,
                'sdk': 'claude-agent-sdk',
            }

        except anthropic.AuthenticationError:
            return {
                'status': 'unhealthy',
                'error': 'API key inválida',
                'api_connected': False,
            }

        except anthropic.APIError as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'api_connected': False,
            }


# Singleton do cliente
_client: Optional[AgentClient] = None


def get_client() -> AgentClient:
    """
    Obtém instância do cliente (singleton).

    Returns:
        Instância de AgentClient
    """
    global _client
    if _client is None:
        _client = AgentClient()
    return _client


def reset_client() -> None:
    """Reseta o singleton do cliente."""
    global _client
    _client = None
