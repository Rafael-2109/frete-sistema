"""
Cliente do Claude Agent SDK.

Wrapper que encapsula a comunicação com a API usando o SDK oficial.
Usa query() + resume para streaming (compatível com Flask thread-per-request).

Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/

ARQUITETURA (v2 — query() + resume):
- Cada request HTTP roda em Thread + asyncio.run() que DESTRÓI o event loop.
- ClaudeSDKClient precisa de event loop PERSISTENTE → corrompido entre requests.
- query() é self-contained: spawna CLI process, executa, limpa automaticamente.
- resume=sdk_session_id restaura contexto da conversa anterior (CLI carrega sessão do disco).
"""

import logging
import time
from typing import AsyncGenerator, Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

# SDK Oficial
# Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/
from claude_agent_sdk import (
    query as sdk_query,  # query() standalone — self-contained, sem estado persistente
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    UserMessage,       # Contém resultados de ferramentas
    SystemMessage,     # Mensagem de sistema (init com session_id)
    ToolUseBlock,
    ToolResultBlock,   # Resultado de execução de ferramenta
    TextBlock,
    ThinkingBlock,     # FEAT-002: Extended Thinking
    # SDK 0.1.26+: Error classes especializadas
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
)

# Fallback para API direta (health check)
import anthropic

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Representa uma chamada de ferramenta."""
    id: str
    name: str
    input: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StreamEvent:
    """Evento do stream de resposta."""
    type: str  # 'text', 'tool_call', 'tool_result', 'action_pending', 'done', 'error', 'init'
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Resposta completa do agente."""
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    pending_action: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class AgentClient:
    """
    Cliente do Claude Agent SDK oficial.

    ARQUITETURA (v2 — query() + resume):
    - Usa query() standalone (self-contained, sem estado persistente)
    - Resume via sdk_session_id para manter contexto entre turnos
    - Sem SessionPool, sem locks, sem connect/disconnect
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

        # Streaming com query() + resume
        async for event in client.stream_response("Sua pergunta", sdk_session_id="..."):
            if event.type == 'text':
                print(event.content, end='')
    """

    def __init__(self):
        from ..config import get_settings

        self.settings = get_settings()

        # Carrega system prompt
        self.system_prompt = self._load_system_prompt()

        # Cliente para health check (API direta)
        self._anthropic_client = anthropic.Anthropic(api_key=self.settings.api_key)

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

        Args:
            user_name: Nome do usuário
            user_id: ID do usuário (para Memory Tool)

        Returns:
            System prompt formatado
        """
        prompt = self.system_prompt.replace(
            "{data_atual}",
            datetime.now().strftime("%d/%m/%Y %H:%M")
        )
        prompt = prompt.replace("{usuario_nome}", user_name)

        # Memory Tool: passa user_id para os scripts
        if user_id:
            prompt = prompt.replace("{user_id}", str(user_id))
        else:
            prompt = prompt.replace("{user_id}", "NAO_DISPONIVEL")

        return prompt

    @staticmethod
    async def _self_correct_response(full_text: str) -> Optional[str]:
        """
        D6: Self-Correction — valida coerência da resposta antes de entregar.

        Usa Haiku (20x mais barato) para verificar:
        - Números/valores coerentes entre si
        - Contradições internas na resposta
        - Informação crítica faltante (ex: perguntou X, respondeu sobre Y)

        Args:
            full_text: Texto completo da resposta do agente

        Returns:
            None se a resposta está OK
            String com observação de correção se detectar problema
        """
        from ..config.feature_flags import USE_SELF_CORRECTION

        if not USE_SELF_CORRECTION:
            return None

        # Só validar respostas com conteúdo substancial (>100 chars)
        if not full_text or len(full_text.strip()) < 100:
            return None

        try:
            client = anthropic.Anthropic()

            validation = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": (
                        "Analise esta resposta de um assistente de logística e identifique "
                        "APENAS problemas GRAVES de coerência:\n"
                        "- Números que contradizem entre si (ex: 'total de 5 itens' mas lista 8)\n"
                        "- Valores monetários inconsistentes\n"
                        "- Informação que contradiz a si mesma\n\n"
                        "Se a resposta está coerente, responda EXATAMENTE: OK\n"
                        "Se encontrar problema, descreva em UMA frase curta.\n\n"
                        f"Resposta a validar:\n{full_text[:3000]}"
                    )
                }]
            )

            result = validation.content[0].text.strip()

            if result.upper() == "OK" or len(result) < 5:
                logger.debug("[SELF-CORRECTION] Resposta validada: OK")
                return None

            logger.warning(f"[SELF-CORRECTION] Problema detectado: {result}")
            return result

        except Exception as e:
            # Self-correction é best-effort — falha silenciosa
            logger.debug(f"[SELF-CORRECTION] Erro na validação (ignorado): {e}")
            return None

    async def stream_response(
        self,
        prompt: str,
        user_name: str = "Usuário",
        model: Optional[str] = None,
        thinking_enabled: bool = False,
        plan_mode: bool = False,
        user_id: int = None,
        image_files: Optional[List[dict]] = None,
        sdk_session_id: Optional[str] = None,
        can_use_tool: Optional[Callable] = None,
        # LEGADO: aceitar pooled_client para compatibilidade (ignorado)
        pooled_client: Any = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming usando query() + resume.

        Args:
            prompt: Mensagem do usuário
            user_name: Nome do usuário
            model: Modelo a usar (FEAT-001)
            thinking_enabled: Ativar Extended Thinking (FEAT-002)
            plan_mode: Ativar modo somente-leitura (FEAT-010)
            user_id: ID do usuário (para Memory Tool)
            image_files: Lista de imagens em formato Vision API (FEAT-032)
            sdk_session_id: Session ID do SDK para resume (do DB)
            can_use_tool: Callback de permissão
            pooled_client: LEGADO — ignorado (mantido para compatibilidade)

        Yields:
            StreamEvent com tipo e conteúdo
        """
        async for event in self._stream_response(
            prompt=prompt,
            user_name=user_name,
            model=model,
            thinking_enabled=thinking_enabled,
            plan_mode=plan_mode,
            user_id=user_id,
            image_files=image_files,
            sdk_session_id=sdk_session_id,
            can_use_tool=can_use_tool,
        ):
            yield event

    def _build_options(
        self,
        user_name: str = "Usuário",
        can_use_tool: Optional[Callable] = None,
        max_turns: int = 30,
        model: Optional[str] = None,
        thinking_enabled: bool = False,
        plan_mode: bool = False,
        user_id: int = None,
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
            thinking_enabled: Ativar Extended Thinking
            plan_mode: Ativar modo somente-leitura
            user_id: ID do usuário (para Memory Tool)

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
        permission_mode = "plan" if plan_mode else "default"

        options_dict = {
            # Modelo
            "model": model if model else self.settings.model,

            # Máximo de turnos
            "max_turns": max_turns,

            # System Prompt: preset "claude_code" para ter tools funcionando
            "system_prompt": {
                "type": "preset",
                "preset": "claude_code",
                "append": custom_instructions
            },

            # CWD: Diretório de trabalho para Skills
            "cwd": project_cwd,

            # Setting Sources: Carrega configurações do projeto
            "setting_sources": ["user", "project"],

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
        }

        # Extended Thinking
        if thinking_enabled:
            options_dict["max_thinking_tokens"] = 20000
            logger.info("[AGENT_CLIENT] Extended Thinking ativado (max_thinking_tokens=20000)")

        # Callback de permissão
        if can_use_tool:
            options_dict["can_use_tool"] = can_use_tool

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

        # Extended Context (1M tokens) — apenas Sonnet
        if USE_EXTENDED_CONTEXT:
            current_model = options_dict.get("model", self.settings.model)
            if "sonnet" in str(current_model).lower():
                betas = options_dict.get("betas", [])
                betas.append("context-1m-2025-08-07")
                options_dict["betas"] = betas
                logger.info("[AGENT_CLIENT] Extended Context habilitado (1M tokens)")
            else:
                logger.warning(
                    f"[AGENT_CLIENT] Extended Context IGNORADO — "
                    f"modelo '{current_model}' não suportado (apenas Sonnet)"
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
            from claude_agent_sdk import HookMatcher, PostToolUseHookInput, PreCompactHookInput, HookContext

            async def _audit_post_tool_use(hook_input: PostToolUseHookInput, signal, context: HookContext):
                """Registra execução de tools para auditoria."""
                tool_name = getattr(hook_input, 'tool_name', 'unknown')
                tool_input_str = str(getattr(hook_input, 'tool_input', ''))[:200]
                logger.info(f"[AUDIT] PostToolUse: {tool_name} | input: {tool_input_str}")
                return {}

            async def _pre_compact_hook(hook_input: PreCompactHookInput, signal, context: HookContext):
                """Antes de compactação, instrui modelo a salvar contexto crítico."""
                logger.info("[COMPACTION] PreCompact hook ativado — contexto será compactado")
                return {
                    "custom_instructions": (
                        "O contexto será compactado agora. ANTES de continuar, "
                        "salve informações críticas (pedidos em discussão, clientes, decisões) "
                        "usando mcp__memory__save_memory em /memories/context/session_notes.xml. "
                        "Após compactação, consulte suas memórias para recuperar estado."
                    )
                }

            options_dict["hooks"] = {
                "PostToolUse": [
                    HookMatcher(
                        matcher="Bash|Skill",
                        hooks=[_audit_post_tool_use],
                    ),
                ],
                "PreCompact": [
                    HookMatcher(
                        hooks=[_pre_compact_hook],
                    ),
                ],
            }
            logger.debug("[AGENT_CLIENT] Hooks SDK (PostToolUse + PreCompact) configurados")
        except (ImportError, Exception) as e:
            logger.warning(f"[AGENT_CLIENT] Hooks SDK não disponíveis: {e}")

        # =================================================================
        # MCP Servers (Custom Tools in-process)
        # =================================================================
        try:
            from ..tools.text_to_sql_tool import sql_server
            if sql_server is not None:
                mcp_servers = options_dict.get("mcp_servers", {})
                mcp_servers["sql"] = sql_server
                options_dict["mcp_servers"] = mcp_servers

                # Adicionar tool na allowed_tools
                allowed = options_dict.get("allowed_tools", [])
                if "mcp__sql__consultar_sql" not in allowed:
                    allowed.append("mcp__sql__consultar_sql")
                options_dict["allowed_tools"] = allowed

                logger.info("[AGENT_CLIENT] Custom Tool MCP 'consultar_sql' registrada")
            else:
                logger.debug("[AGENT_CLIENT] sql_server é None — claude_agent_sdk não disponível no módulo tools")
        except ImportError:
            logger.debug("[AGENT_CLIENT] Custom Tool text_to_sql não disponível (módulo não encontrado)")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro ao registrar Custom Tool text_to_sql: {e}")

        # =================================================================
        # MCP Memory Tool (memória persistente do usuário via tool_use)
        # Substitui o padrão anterior de subagente Haiku (PRE/POST-HOOK)
        # =================================================================
        try:
            from ..tools.memory_mcp_tool import memory_server, set_current_user_id

            if memory_server is not None:
                # Definir user_id no contexto para as memory tools
                if user_id:
                    set_current_user_id(user_id)

                mcp_servers = options_dict.get("mcp_servers", {})
                mcp_servers["memory"] = memory_server
                options_dict["mcp_servers"] = mcp_servers

                # Adicionar tools na allowed_tools
                allowed = options_dict.get("allowed_tools", [])
                memory_tool_names = [
                    "mcp__memory__view_memories",
                    "mcp__memory__save_memory",
                    "mcp__memory__update_memory",
                    "mcp__memory__delete_memory",
                    "mcp__memory__list_memories",
                    "mcp__memory__clear_memories",
                ]
                for tool_name in memory_tool_names:
                    if tool_name not in allowed:
                        allowed.append(tool_name)
                options_dict["allowed_tools"] = allowed

                logger.info("[AGENT_CLIENT] Custom Tool MCP 'memory' registrada (6 operações)")
            else:
                logger.debug("[AGENT_CLIENT] memory_server é None — claude_agent_sdk não disponível")
        except ImportError:
            logger.debug("[AGENT_CLIENT] Custom Tool memory não disponível (módulo não encontrado)")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro ao registrar Custom Tool memory: {e}")

        return ClaudeAgentOptions(**options_dict)

    async def _stream_response(
        self,
        prompt: str,
        user_name: str = "Usuário",
        model: Optional[str] = None,
        thinking_enabled: bool = False,
        plan_mode: bool = False,
        user_id: int = None,
        image_files: Optional[List[dict]] = None,
        sdk_session_id: Optional[str] = None,
        can_use_tool: Optional[Callable] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming usando query() + resume.

        ARQUITETURA v2:
        - Cada chamada usa query() standalone (sem ClaudeSDKClient)
        - query() spawna CLI process, executa, limpa automaticamente
        - resume=sdk_session_id restaura contexto da conversa anterior
        - Sem pool, sem locks, sem connect/disconnect

        Args:
            prompt: Mensagem do usuário
            user_name: Nome do usuário
            model: Modelo a usar
            thinking_enabled: Ativar Extended Thinking
            plan_mode: Ativar modo somente-leitura
            user_id: ID do usuário (para Memory Tool)
            image_files: Lista de imagens em formato Vision API
            sdk_session_id: Session ID do SDK para resume (do DB)
            can_use_tool: Callback de permissão

        Yields:
            StreamEvent com tipo e conteúdo
        """
        full_text = ""
        tool_calls = []
        input_tokens = 0
        output_tokens = 0
        last_message_id = None
        done_emitted = False
        result_session_id = None  # Capturado do ResultMessage

        # Diagnostico de tempo
        stream_start_time = time.time()
        last_message_time = stream_start_time
        current_tool_start_time = None
        current_tool_name = None

        # ─── Construir options ───
        options = self._build_options(
            user_name=user_name,
            user_id=user_id,
            model=model,
            thinking_enabled=thinking_enabled,
            plan_mode=plan_mode,
            can_use_tool=can_use_tool,
        )

        # ─── RESUME: Continuar conversa anterior ───
        if sdk_session_id:
            options = self._with_resume(options, sdk_session_id)
            logger.info(f"[AGENT_SDK] Resuming session: {sdk_session_id[:12]}...")

        # ─── Construir prompt como AsyncIterable ───
        # CRÍTICO: can_use_tool EXIGE streaming mode (AsyncIterable, não string)
        # FONTE: _internal/client.py:53-58
        # Portanto SEMPRE usamos AsyncIterable wrapper.
        query_prompt = self._make_streaming_prompt(prompt, image_files)

        # ─── Emitir init sintético ───
        yield StreamEvent(
            type='init',
            content={'session_id': sdk_session_id or 'pending'},
            metadata={
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'resume': bool(sdk_session_id),
            }
        )

        try:
            # ─── STREAMING via query() ───
            # query() é self-contained: spawna CLI process, executa, limpa.
            # Sem background tasks, sem estado persistente.
            # Quando o async for termina, o CLI process é limpo automaticamente.
            async for message in sdk_query(
                prompt=query_prompt,
                options=options,
            ):
                # Diagnostico de tempo
                current_time = time.time()
                elapsed_total = current_time - stream_start_time
                elapsed_since_last = current_time - last_message_time
                last_message_time = current_time

                logger.debug(
                    f"[AGENT_SDK] msg={type(message).__name__} | "
                    f"total={elapsed_total:.1f}s | "
                    f"delta={elapsed_since_last:.1f}s"
                )

                # ─── SystemMessage (init do SDK) ───
                if isinstance(message, SystemMessage):
                    sdk_sid = message.data.get('session_id') if hasattr(message, 'data') else None
                    if sdk_sid:
                        result_session_id = sdk_sid
                        logger.info(f"[AGENT_SDK] SDK session_id from init: {sdk_sid[:12]}...")
                    continue

                # ─── AssistantMessage ───
                if isinstance(message, AssistantMessage):
                    # Captura usage
                    if hasattr(message, 'usage') and message.usage:
                        usage = message.usage
                        if isinstance(usage, dict):
                            input_tokens = usage.get('input_tokens', 0)
                            output_tokens = usage.get('output_tokens', 0)
                        else:
                            input_tokens = getattr(usage, 'input_tokens', 0) or 0
                            output_tokens = getattr(usage, 'output_tokens', 0) or 0

                    # C3: Detectar erros da API
                    if hasattr(message, 'error') and message.error:
                        error_info = message.error
                        error_str = str(error_info).lower()
                        error_type_str = error_info.get('type', 'unknown') if isinstance(error_info, dict) else type(error_info).__name__

                        logger.warning(
                            f"[AGENT_SDK] API error: type={error_type_str}, error={error_info}"
                        )

                        if 'rate_limit' in error_str:
                            yield StreamEvent(
                                type='error',
                                content="Limite de requisições excedido. Aguardando...",
                                metadata={'error_type': 'rate_limit', 'retryable': True}
                            )
                        elif 'too long' in error_str or 'context' in error_str:
                            yield StreamEvent(
                                type='error',
                                content="Conversa muito longa. Tente iniciar uma nova sessão.",
                                metadata={'error_type': 'context_overflow', 'retryable': False}
                            )
                        else:
                            yield StreamEvent(
                                type='error',
                                content=f"Erro da API: {error_info}",
                                metadata={'error_type': error_type_str, 'raw_error': str(error_info)[:500]}
                            )

                    # Message ID para deduplicacao
                    if hasattr(message, 'id') and message.id:
                        last_message_id = message.id

                    if message.content:
                        for block in message.content:
                            # Extended Thinking
                            if isinstance(block, ThinkingBlock):
                                thinking_content = getattr(block, 'thinking', '')
                                if thinking_content:
                                    yield StreamEvent(
                                        type='thinking',
                                        content=thinking_content
                                    )
                                continue

                            # Texto
                            if isinstance(block, TextBlock):
                                text_chunk = block.text
                                full_text += text_chunk
                                yield StreamEvent(
                                    type='text',
                                    content=text_chunk
                                )

                            # Tool call
                            elif isinstance(block, ToolUseBlock):
                                tool_call = ToolCall(
                                    id=block.id,
                                    name=block.name,
                                    input=block.input
                                )
                                tool_calls.append(tool_call)

                                current_tool_start_time = time.time()
                                current_tool_name = block.name
                                logger.info(f"[AGENT_SDK] Tool START: {block.name}")

                                tool_description = self._extract_tool_description(
                                    block.name, block.input
                                )

                                yield StreamEvent(
                                    type='tool_call',
                                    content=block.name,
                                    metadata={
                                        'tool_id': block.id,
                                        'input': block.input,
                                        'description': tool_description
                                    }
                                )

                                # TodoWrite emit
                                if block.name == 'TodoWrite' and block.input:
                                    todos = block.input.get('todos', [])
                                    if todos:
                                        yield StreamEvent(
                                            type='todos',
                                            content={'todos': todos},
                                            metadata={'tool_id': block.id}
                                        )
                    continue

                # ─── UserMessage (tool results) ───
                if isinstance(message, UserMessage):
                    tool_duration_ms = 0
                    if current_tool_start_time:
                        tool_duration_ms = int((time.time() - current_tool_start_time) * 1000)
                        logger.info(
                            f"[AGENT_SDK] Tool DONE: {current_tool_name} {tool_duration_ms}ms"
                        )
                        current_tool_start_time = None

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
                                    (tc.name for tc in tool_calls if tc.id == tool_use_id),
                                    'ferramenta'
                                )

                                if is_error:
                                    expected_errors = ['does not exist', 'not found', 'no such file']
                                    is_expected = any(err in result_content.lower() for err in expected_errors)
                                    if is_expected:
                                        logger.debug(f"[AGENT_SDK] Tool '{tool_name}' (esperado): {result_content[:100]}")
                                    else:
                                        logger.warning(f"[AGENT_SDK] Tool '{tool_name}' erro: {result_content[:200]}")

                                yield StreamEvent(
                                    type='tool_result',
                                    content=result_content,
                                    metadata={
                                        'tool_use_id': tool_use_id,
                                        'tool_name': tool_name,
                                        'is_error': is_error,
                                        'duration_ms': tool_duration_ms,
                                    }
                                )
                    continue

                # ─── ResultMessage (fim) ───
                if isinstance(message, ResultMessage):
                    # CRÍTICO: Capturar session_id REAL do SDK para resume
                    result_session_id = message.session_id

                    if message.result:
                        full_text = message.result

                    # Detectar interrupt
                    is_interrupted = (
                        getattr(message, 'subtype', '') in ('interrupted', 'canceled', 'cancelled')
                        or (message.is_error and 'interrupt' in str(message.result or '').lower())
                    )

                    if is_interrupted and not done_emitted:
                        logger.info(
                            f"[AGENT_SDK] Interrupt detectado | "
                            f"subtype={getattr(message, 'subtype', 'N/A')} | "
                            f"text_so_far={len(full_text)} chars"
                        )
                        yield StreamEvent(
                            type='interrupt_ack',
                            content='Operação interrompida pelo usuário',
                        )

                    if not done_emitted:
                        # D6: Self-Correction (skip se interrupt)
                        correction = None
                        if not is_interrupted:
                            correction = await self._self_correct_response(full_text)
                            if correction:
                                yield StreamEvent(
                                    type='text',
                                    content=f"\n\n⚠️ **Observação de validação**: {correction}",
                                    metadata={'self_correction': True}
                                )

                        done_emitted = True
                        yield StreamEvent(
                            type='done',
                            content={
                                'text': full_text,
                                'input_tokens': input_tokens,
                                'output_tokens': output_tokens,
                                'total_cost_usd': getattr(message, 'total_cost_usd', 0) or 0,
                                # CRÍTICO: session_id REAL do SDK para resume no próximo turno
                                'session_id': result_session_id,
                                'tool_calls': len(tool_calls),
                                'self_corrected': correction is not None if correction else False,
                                'interrupted': is_interrupted,
                            },
                            metadata={'message_id': last_message_id or ''}
                        )

            # ─── Fallback done (sem ResultMessage) ───
            if not done_emitted:
                correction = await self._self_correct_response(full_text)
                if correction:
                    yield StreamEvent(
                        type='text',
                        content=f"\n\n⚠️ **Observação de validação**: {correction}",
                        metadata={'self_correction': True}
                    )

                yield StreamEvent(
                    type='done',
                    content={
                        'text': full_text,
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'session_id': result_session_id,
                        'tool_calls': len(tool_calls),
                        'self_corrected': correction is not None if correction else False,
                    }
                )

            # ─── NÃO PRECISA DESTRUIR NADA ───
            # query() limpa o CLI process automaticamente quando o
            # async for termina. Sem pool, sem disconnect, sem leak.

        except ProcessError as e:
            elapsed_total = time.time() - stream_start_time
            exit_code = getattr(e, 'exit_code', None)
            logger.error(
                f"[AGENT_SDK] ProcessError {elapsed_total:.1f}s | exit={exit_code} | msg={e}"
            )
            yield StreamEvent(
                type='error',
                content=f"Erro de processo (código {exit_code}). Tente novamente." if exit_code else str(e),
                metadata={'error_type': 'process_error', 'exit_code': exit_code,
                          'elapsed_seconds': elapsed_total, 'last_tool': current_tool_name}
            )
            if not done_emitted:
                done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': full_text, 'input_tokens': input_tokens,
                             'output_tokens': output_tokens, 'session_id': result_session_id,
                             'tool_calls': len(tool_calls), 'error_recovery': True},
                    metadata={'error_type': 'process_error'}
                )

        except CLINotFoundError as e:
            elapsed_total = time.time() - stream_start_time
            logger.critical(f"[AGENT_SDK] CLI não encontrada {elapsed_total:.1f}s: {e}")
            yield StreamEvent(
                type='error',
                content="Erro crítico: CLI do agente não encontrada.",
                metadata={'error_type': 'cli_not_found', 'elapsed_seconds': elapsed_total}
            )
            if not done_emitted:
                done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': full_text, 'session_id': result_session_id,
                             'error_recovery': True},
                    metadata={'error_type': 'cli_not_found'}
                )

        except CLIJSONDecodeError as e:
            elapsed_total = time.time() - stream_start_time
            logger.error(f"[AGENT_SDK] JSON decode error {elapsed_total:.1f}s: {e}")
            yield StreamEvent(
                type='error',
                content="Erro ao processar resposta do agente. Tente novamente.",
                metadata={'error_type': 'json_decode_error', 'elapsed_seconds': elapsed_total}
            )
            if not done_emitted:
                done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': full_text, 'session_id': result_session_id,
                             'error_recovery': True},
                    metadata={'error_type': 'json_decode_error'}
                )

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            elapsed_total = time.time() - stream_start_time
            logger.error(
                f"[AGENT_SDK] {error_type} {elapsed_total:.1f}s: {error_msg}",
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
                    'last_tool': current_tool_name,
                }
            )

            if not done_emitted:
                done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={
                        'text': full_text,
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'session_id': result_session_id,
                        'tool_calls': len(tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': error_type}
                )

    @staticmethod
    async def _make_streaming_prompt(text: str, image_files: Optional[List[dict]] = None):
        """
        Converte prompt string em AsyncIterable para compatibilidade com can_use_tool.

        CRÍTICO: can_use_tool exige streaming mode (AsyncIterable, não string).
        FONTE: _internal/client.py:53-58

        Args:
            text: Texto do prompt
            image_files: Lista de imagens em formato Vision API

        Yields:
            Dict no formato esperado pelo SDK streaming mode
        """
        if image_files:
            content_blocks = list(image_files) + [{"type": "text", "text": text}]
        else:
            content_blocks = text

        yield {
            "type": "user",
            "message": {"role": "user", "content": content_blocks}
        }

    @staticmethod
    def _with_resume(options: 'ClaudeAgentOptions', sdk_session_id: str) -> 'ClaudeAgentOptions':
        """
        Retorna cópia do options com resume configurado.

        Usa dataclasses.replace() para criar cópia imutável.

        Args:
            options: ClaudeAgentOptions original
            sdk_session_id: Session ID do SDK para resume

        Returns:
            Novo ClaudeAgentOptions com resume=sdk_session_id
        """
        from dataclasses import replace
        return replace(options, resume=sdk_session_id)

    async def get_response(
        self,
        prompt: str,
        user_name: str = "Usuário",
        model: Optional[str] = None,
        sdk_session_id: Optional[str] = None,
        can_use_tool: Optional[Callable] = None,
        # LEGADO: aceitar pooled_client para compatibilidade (ignorado)
        pooled_client: Any = None,
    ) -> AgentResponse:
        """
        Obtém resposta completa (não streaming).

        Args:
            prompt: Mensagem do usuário
            user_name: Nome do usuário
            model: Modelo a usar
            sdk_session_id: Session ID do SDK para resume
            can_use_tool: Callback de permissão
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

        async for event in self.stream_response(
            prompt=prompt,
            user_name=user_name,
            model=model,
            sdk_session_id=sdk_session_id,
            can_use_tool=can_use_tool,
        ):
            if event.type == 'init':
                result_session_id = event.content.get('session_id')
            elif event.type == 'text':
                full_text += event.content
            elif event.type == 'tool_call':
                tool_calls.append(ToolCall(
                    id=event.metadata.get('tool_id', ''),
                    name=event.content,
                    input=event.metadata.get('input', {})
                ))
            elif event.type == 'done':
                input_tokens = event.content.get('input_tokens', 0)
                output_tokens = event.content.get('output_tokens', 0)
                # Captura session_id real do done
                done_session_id = event.content.get('session_id')
                if done_session_id:
                    result_session_id = done_session_id

        return AgentResponse(
            text=full_text,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=stop_reason,
            session_id=result_session_id,
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Verifica saúde da conexão com API.

        Returns:
            Dict com status da conexão
        """
        try:
            # Usa API direta para health check (mais rápido)
            response = self._anthropic_client.messages.create(
                model=self.settings.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )

            return {
                'status': 'healthy',
                'model': self.settings.model,
                'api_connected': True,
                'sdk': 'claude-agent-sdk',
                'response_id': response.id,
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
