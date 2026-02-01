"""
Cliente do Claude Agent SDK.

Wrapper que encapsula a comunicação com a API usando o SDK oficial.
Suporta streaming, tools, sessions e permissions.

Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/
"""

import logging
import asyncio
import time
from typing import AsyncGenerator, Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime

# SDK Oficial
# Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    UserMessage,       # Contém resultados de ferramentas
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
    timestamp: datetime = field(default_factory=datetime.utcnow)


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

    ARQUITETURA (conforme melhores práticas Anthropic):
    - Usa SKILLS para funcionalidades (.claude/skills/)
    - Skills são invocadas automaticamente baseado na descrição
    - Scripts são executados via Bash tool
    - NÃO usa Custom Tools MCP (evita duplicação)

    Referências:
    - https://platform.claude.com/docs/pt-BR/agent-sdk/skills
    - https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
    - https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

    Implementa:
    - Streaming com query() async generator
    - Sessions automáticas com resume
    - Skills via setting_sources=["project"]
    - Callback canUseTool para permissões
    - Rastreamento de custos

    Uso:
        client = AgentClient()

        # Streaming
        async for event in client.stream_response("Sua pergunta"):
            if event.type == 'text':
                print(event.content, end='')

        # Com sessão existente
        async for event in client.stream_response("Continue...", session_id="xyz"):
            ...
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

    def _build_options(
        self,
        session_id: Optional[str] = None,
        user_name: str = "Usuário",
        allowed_tools: Optional[List[str]] = None,
        permission_mode: str = "default",
        can_use_tool: Optional[Callable] = None,
        max_turns: int = 10,
        fork_session: bool = False,
        model: Optional[str] = None,
        thinking_enabled: bool = False,
        user_id: int = None,
    ) -> ClaudeAgentOptions:
        """
        Constrói ClaudeAgentOptions conforme documentação oficial Anthropic.

        ARQUITETURA (conforme melhores práticas):
        - Usa SKILLS para funcionalidades (.claude/skills/)
        - Skills são invocadas automaticamente baseado na descrição
        - Scripts são executados via Bash tool
        - NÃO usa Custom Tools MCP (evita duplicação)

        Referências:
        - https://platform.claude.com/docs/pt-BR/agent-sdk/skills
        - https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
        - https://platform.claude.com/docs/pt-BR/agent-sdk/permissions

        Args:
            session_id: ID de sessão para retomar (do SDK)
            user_name: Nome do usuário
            allowed_tools: Lista de tools permitidas
            permission_mode: Modo de permissão (default, acceptEdits, plan, bypassPermissions)
            can_use_tool: Callback de permissão (retorna {behavior, updatedInput})
            max_turns: Máximo de turnos
            fork_session: Se deve bifurcar a sessão
            model: Modelo a usar (FEAT-001) - sobrescreve settings.model
            thinking_enabled: Ativar Extended Thinking (FEAT-002)
            user_id: ID do usuário (para Memory Tool)

        Returns:
            ClaudeAgentOptions configurado
        """
        import os

        # System prompt customizado (com user_id para Memory Tool)
        custom_instructions = self._format_system_prompt(user_name, user_id)

        # Diretório do projeto para carregar Skills
        # Skills estão em: .claude/skills/
        project_cwd = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            )
        )  # Raiz do projeto: /home/.../frete_sistema

        options_dict = {
            # ========================================
            # CONFIGURAÇÃO CONFORME DOCUMENTAÇÃO SDK
            # https://platform.claude.com/docs/pt-BR/agent-sdk/modifying-system-prompts
            # https://platform.claude.com/docs/pt-BR/agent-sdk/skills
            # ========================================

            # FEAT-001: Modelo a ser usado (usa o passado por parâmetro ou o padrão)
            "model": model if model else self.settings.model,

            # Máximo de turnos (quantas vezes o agente pode responder)
            "max_turns": max_turns,

            # System Prompt: OBRIGATÓRIO usar preset "claude_code" para ter tools funcionando!
            # Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/modifying-system-prompts
            # "O Agent SDK usa um prompt do sistema vazio por padrão"
            # "Para usar funcionalidades completas, especifique preset: 'claude_code'"
            "system_prompt": {
                "type": "preset",
                "preset": "claude_code",
                "append": custom_instructions
            },

            # CWD: Diretório de trabalho para Skills
            # CRÍTICO: Skills só funcionam se cwd apontar para raiz do projeto
            "cwd": project_cwd,

            # Setting Sources: Carrega configurações do projeto e usuário
            # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/skills
            # OBRIGATÓRIO para habilitar Skills - sem isso, Skills não carregam!
            "setting_sources": ["user", "project"],
        }

        # Retomar sessão existente (SDK gerencia sessions)
        # Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
        if session_id:
            options_dict["resume"] = session_id
            if fork_session:
                options_dict["fork_session"] = True

        # Tools permitidas - APENAS as necessárias para Skills funcionarem
        # Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/skills
        # "Skill" é OBRIGATÓRIO para Claude invocar Skills
        # "Bash" é necessário para executar scripts das Skills
        if allowed_tools:
            options_dict["allowed_tools"] = allowed_tools
        else:
            # Default: Tools necessárias para Skills funcionarem
            # NOTA: Write e Edit são validados no can_use_tool para permitir APENAS /tmp
            options_dict["allowed_tools"] = [
                "Skill",      # OBRIGATÓRIO - permite Claude invocar Skills
                "Bash",       # OBRIGATÓRIO - executa scripts Python das Skills
                "Task",       # Invocar subagentes (.claude/agents/ e programáticos)
                "Read",       # Leitura de arquivos (útil para contexto)
                "Glob",       # Busca de arquivos
                "Grep",       # Busca em conteúdo
                "Write",      # Escrita de arquivos (RESTRITO a /tmp via can_use_tool)
                "Edit",       # Edição de arquivos (RESTRITO a /tmp via can_use_tool)
                "TodoWrite",  # Gerenciamento de tarefas (feedback visual)
                "Memory",     # Memória persistente do usuário (DatabaseMemoryTool)
            ]

        # Modo de permissão
        # Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/permissions
        if permission_mode in ['default', 'acceptEdits', 'plan', 'bypassPermissions']:
            options_dict["permission_mode"] = permission_mode
        else:
            options_dict["permission_mode"] = "default"

        # FEAT-002: Extended Thinking (Pensamento Profundo)
        # Referência: Parâmetro max_thinking_tokens do ClaudeAgentOptions
        # Quando ativado, o Claude usa mais tokens para raciocinar antes de responder
        if thinking_enabled:
            # Budget de 20.000 tokens para thinking (ajustável)
            options_dict["max_thinking_tokens"] = 20000
            logger.info("[AGENT_CLIENT] Extended Thinking ativado (max_thinking_tokens=20000)")

        # Callback de permissão (SDK 0.1.26+: 3 params, retorno tipado)
        # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/permissions
        if can_use_tool:
            options_dict["can_use_tool"] = can_use_tool

        # SDK 0.1.26+: Fallback model para resiliência em produção
        # Se o modelo principal falhar (rate limit, indisponibilidade),
        # o SDK automaticamente usa o fallback
        options_dict["fallback_model"] = "sonnet"
        logger.info("[AGENT_CLIENT] Fallback model configurado: sonnet")

        # SDK 0.1.26+: Barreira real de segurança
        # allowed_tools SOZINHO não bloqueia — agente pode pedir permissão
        # disallowed_tools impede completamente o acesso
        options_dict["disallowed_tools"] = [
            "NotebookEdit",   # Não há Jupyter notebooks no sistema
        ]

        # =================================================================
        # FEATURE FLAGS: Quick Wins (ativados via env vars)
        # =================================================================
        from ..config.feature_flags import (
            USE_BUDGET_CONTROL, MAX_BUDGET_USD,
            USE_EXTENDED_CONTEXT,
            USE_CONTEXT_CLEARING,
            USE_PROMPT_CACHING,
        )

        # C1: Budget Control nativo (disponível desde SDK v0.1.6)
        if USE_BUDGET_CONTROL:
            options_dict["max_budget_usd"] = MAX_BUDGET_USD
            logger.info(f"[AGENT_CLIENT] Budget control nativo: max ${MAX_BUDGET_USD}/request")

        # C2: Extended Context (1M tokens)
        # RESTRICAO: Só funciona com Sonnet 4/4.5 — NÃO com Opus
        if USE_EXTENDED_CONTEXT:
            current_model = options_dict.get("model", self.settings.model if hasattr(self, 'settings') else "")
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

        # C4: Context Clearing automático
        if USE_CONTEXT_CLEARING:
            betas = options_dict.get("betas", [])
            betas.extend([
                "clear-thinking-20251015",
                "clear-tool-uses-20250919",
            ])
            options_dict["betas"] = betas
            logger.info("[AGENT_CLIENT] Context Clearing habilitado")

        # C6: Prompt Caching (economia de 50-90% tokens input)
        if USE_PROMPT_CACHING:
            betas = options_dict.get("betas", [])
            betas.append("prompt-caching-2024-07-31")
            options_dict["betas"] = betas
            logger.info("[AGENT_CLIENT] Prompt Caching habilitado")

        # =================================================================
        # FEATURE FLAGS: Architecture (Fase 3)
        # =================================================================
        from ..config.feature_flags import USE_PROGRAMMATIC_AGENTS

        # D4: Subagentes programáticos via AgentDefinition
        # Coexiste com .claude/agents/*.md (filesystem)
        # NOTA: Subagentes NÃO podem spawnar outros subagentes
        if USE_PROGRAMMATIC_AGENTS:
            try:
                from claude_agent_sdk import AgentDefinition
                options_dict["agents"] = {
                    "consulta-rapida": AgentDefinition(
                        description=(
                            "Consulta rápida de dados logísticos (pedidos, estoque, NFs). "
                            "Use para perguntas simples que NÃO exigem análise complexa."
                        ),
                        prompt=(
                            "Você é um assistente de consultas rápidas de logística. "
                            "Responda de forma direta e concisa. "
                            "Use as Skills disponíveis para buscar dados reais."
                        ),
                        tools=["Bash", "Read", "Skill", "Glob", "Grep"],
                        model="haiku",  # 20x mais barato que Opus
                    ),
                }
                logger.info("[AGENT_CLIENT] Subagentes programáticos habilitados")
            except (ImportError, Exception) as e:
                logger.warning(
                    f"[AGENT_CLIENT] Subagentes programáticos desabilitados: {e}"
                )

        # =================================================================
        # D5: Hooks SDK formais para auditoria
        # PostToolUse: Registra execução de Bash/Skill
        # PreCompact: Preserva informações críticas antes de compactação
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
                """Antes de compactação, loga aviso."""
                logger.info("[COMPACTION] PreCompact hook ativado — contexto será compactado")
                return {}

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

        return ClaudeAgentOptions(**options_dict)

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
                model="claude-haiku-4-5-20250514",
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
        session_id: Optional[str] = None,
        user_name: str = "Usuário",
        allowed_tools: Optional[List[str]] = None,
        can_use_tool: Optional[Callable] = None,
        max_turns: int = 10,
        model: Optional[str] = None,
        thinking_enabled: bool = False,
        plan_mode: bool = False,
        user_id: int = None,
        image_files: Optional[List[dict]] = None,
        pooled_client: Optional[Any] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming usando SDK oficial.

        Dispatcher dual-mode:
        - USE_SDK_CLIENT=false: Usa query() (comportamento legado via _stream_response_query)
        - USE_SDK_CLIENT=true: Usa ClaudeSDKClient (canal bidirecional via _stream_response_sdk_client)

        Args:
            prompt: Mensagem do usuário
            session_id: ID de sessão para retomar (apenas query() path)
            user_name: Nome do usuário
            allowed_tools: Lista de tools permitidas
            can_use_tool: Callback de permissão
            max_turns: Máximo de turnos
            model: Modelo a usar (FEAT-001)
            thinking_enabled: Ativar Extended Thinking (FEAT-002)
            plan_mode: Ativar modo somente-leitura (FEAT-010)
            user_id: ID do usuário (para Memory Tool)
            image_files: Lista de imagens em formato Vision API (FEAT-032)
            pooled_client: PooledClient do SessionPool (apenas ClaudeSDKClient path)

        Yields:
            StreamEvent com tipo e conteúdo
        """
        from ..config.feature_flags import USE_SDK_CLIENT

        if USE_SDK_CLIENT and pooled_client is not None:
            async for event in self._stream_response_sdk_client(
                prompt=prompt,
                pooled_client=pooled_client,
                user_name=user_name,
                can_use_tool=can_use_tool,
                max_turns=max_turns,
                model=model,
                thinking_enabled=thinking_enabled,
                plan_mode=plan_mode,
                user_id=user_id,
                image_files=image_files,
            ):
                yield event
        else:
            async for event in self._stream_response_query(
                prompt=prompt,
                session_id=session_id,
                user_name=user_name,
                allowed_tools=allowed_tools,
                can_use_tool=can_use_tool,
                max_turns=max_turns,
                model=model,
                thinking_enabled=thinking_enabled,
                plan_mode=plan_mode,
                user_id=user_id,
                image_files=image_files,
            ):
                yield event

    async def _stream_response_query(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        user_name: str = "Usuário",
        allowed_tools: Optional[List[str]] = None,
        can_use_tool: Optional[Callable] = None,
        max_turns: int = 10,
        model: Optional[str] = None,
        thinking_enabled: bool = False,
        plan_mode: bool = False,
        user_id: int = None,
        image_files: Optional[List[dict]] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming usando query() — path legado.

        Este metodo contem a implementacao original usando a funcao query()
        do SDK. Mantido intacto para rollback via feature flag.

        Args:
            prompt: Mensagem do usuário
            session_id: ID de sessão para retomar
            user_name: Nome do usuário
            allowed_tools: Lista de tools permitidas
            can_use_tool: Callback de permissão
            max_turns: Máximo de turnos
            model: Modelo a usar (FEAT-001)
            thinking_enabled: Ativar Extended Thinking (FEAT-002)
            plan_mode: Ativar modo somente-leitura (FEAT-010)
            user_id: ID do usuário (para Memory Tool)
            image_files: Lista de imagens em formato Vision API (FEAT-032)

        Yields:
            StreamEvent com tipo e conteúdo
        """
        # FEAT-010: Plan Mode força permission_mode="plan"
        permission_mode = "plan" if plan_mode else "default"

        options = self._build_options(
            session_id=session_id,
            user_name=user_name,
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            can_use_tool=can_use_tool,
            max_turns=max_turns,
            model=model,
            thinking_enabled=thinking_enabled,
            user_id=user_id,
        )

        current_session_id = session_id
        full_text = ""
        tool_calls = []
        input_tokens = 0
        output_tokens = 0
        last_message_id = None  # Para deduplicação conforme documentação
        done_emitted = False  # Controle para emitir done apenas uma vez

        # =================================================================
        # DIAGNÓSTICO: Rastreamento de tempo para identificar travamentos
        # =================================================================
        stream_start_time = time.time()
        last_message_time = stream_start_time
        current_tool_start_time = None
        current_tool_name = None

        # Gerador assíncrono para o prompt (OBRIGATÓRIO quando can_use_tool é usado)
        # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/streaming-vs-single-mode
        # FEAT-032: Suporte a Vision API - imagens são enviadas como content blocks
        async def prompt_generator():
            # Construir content com texto + imagens (se houver)
            if image_files:
                content_blocks = []
                # Adicionar imagens primeiro (para Claude "ver" antes de ler o texto)
                for img in image_files:
                    content_blocks.append(img)
                # Adicionar texto
                content_blocks.append({
                    "type": "text",
                    "text": prompt
                })
                content = content_blocks
                logger.info(f"[AGENT_CLIENT] Enviando {len(image_files)} imagem(ns) via Vision API")
            else:
                # Manter compatibilidade: texto simples quando não há imagens
                content = prompt

            yield {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": content
                }
            }

        try:
            # Conforme documentação: async for termina naturalmente quando generator é exaurido
            # NÃO usar return/break - deixar o loop terminar sozinho
            async for message in query(prompt=prompt_generator(), options=options):
                # =================================================================
                # DIAGNÓSTICO: Log de tempo entre mensagens
                # =================================================================
                current_time = time.time()
                elapsed_total = current_time - stream_start_time
                elapsed_since_last = current_time - last_message_time
                last_message_time = current_time

                logger.debug(
                    f"[AGENT_CLIENT] Mensagem recebida | "
                    f"tipo={type(message).__name__} | "
                    f"total={elapsed_total:.1f}s | "
                    f"desde_última={elapsed_since_last:.1f}s"
                )

                # Mensagem de sistema (contém session_id no subtype='init')
                # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
                if hasattr(message, 'subtype') and message.subtype == 'init':
                    if hasattr(message, 'data') and message.data:
                        current_session_id = message.data.get('session_id')
                        yield StreamEvent(
                            type='init',
                            content={'session_id': current_session_id},
                            metadata={'timestamp': datetime.utcnow().isoformat()}
                        )
                    continue

                # Mensagem do assistente
                # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking
                if isinstance(message, AssistantMessage):
                    # Captura usage de AssistantMessage (conforme documentação Anthropic)
                    # usage pode ser dict ou objeto com atributos
                    if hasattr(message, 'usage') and message.usage:
                        usage = message.usage
                        if isinstance(usage, dict):
                            input_tokens = usage.get('input_tokens', 0)
                            output_tokens = usage.get('output_tokens', 0)
                        else:
                            # Objeto com atributos
                            input_tokens = getattr(usage, 'input_tokens', 0) or 0
                            output_tokens = getattr(usage, 'output_tokens', 0) or 0

                    # C3: Detectar erros da API (rate limits, context overflow, etc.)
                    # Campo .error fixado no SDK 0.1.16
                    # ATENCAO: SDK NÃO levanta exceptions — erros chegam como campo
                    if hasattr(message, 'error') and message.error:
                        error_info = message.error
                        error_str = str(error_info).lower()
                        error_type_str = error_info.get('type', 'unknown') if isinstance(error_info, dict) else type(error_info).__name__

                        logger.warning(
                            f"[AGENT_CLIENT] API error detectado: type={error_type_str}, error={error_info}"
                        )

                        # Classificar erro para tratamento diferenciado
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

                    # Captura message.id para deduplicação (conforme documentação)
                    if hasattr(message, 'id') and message.id:
                        last_message_id = message.id

                    if message.content:
                        for block in message.content:
                            # FEAT-002: Extended Thinking (mostra raciocínio)
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

                            # Chamada de ferramenta
                            elif isinstance(block, ToolUseBlock):
                                tool_call = ToolCall(
                                    id=block.id,
                                    name=block.name,
                                    input=block.input
                                )
                                tool_calls.append(tool_call)

                                # =================================================================
                                # DIAGNÓSTICO: Marca início da execução da tool
                                # =================================================================
                                current_tool_start_time = time.time()
                                current_tool_name = block.name
                                logger.info(f"[AGENT_CLIENT] Tool INICIADA: {block.name}")

                                # FEAT-024: Extrai descrição amigável do input
                                tool_description = self._extract_tool_description(
                                    block.name,
                                    block.input
                                )

                                yield StreamEvent(
                                    type='tool_call',
                                    content=block.name,
                                    metadata={
                                        'tool_id': block.id,
                                        'input': block.input,
                                        'description': tool_description  # FEAT-024
                                    }
                                )

                                # FEAT-024: Se for TodoWrite, emite evento de todos
                                if block.name == 'TodoWrite' and block.input:
                                    todos = block.input.get('todos', [])
                                    if todos:
                                        yield StreamEvent(
                                            type='todos',
                                            content={'todos': todos},
                                            metadata={'tool_id': block.id}
                                        )
                    continue

                # Mensagem do usuário (contém resultados de ferramentas executadas)
                # Quando o SDK executa uma ferramenta, o resultado vem como UserMessage
                if isinstance(message, UserMessage):
                    # =================================================================
                    # DIAGNÓSTICO: Calcula duração da tool
                    # =================================================================
                    tool_duration_ms = 0
                    if current_tool_start_time:
                        tool_duration_ms = int((time.time() - current_tool_start_time) * 1000)
                        logger.info(
                            f"[AGENT_CLIENT] Tool COMPLETADA: {current_tool_name} em {tool_duration_ms}ms"
                        )
                        current_tool_start_time = None

                    content = getattr(message, 'content', None)
                    if content and isinstance(content, list):
                        for block in content:
                            if isinstance(block, ToolResultBlock):
                                # Extrai conteúdo do resultado (pode ser string ou lista)
                                result_content = block.content
                                is_error = getattr(block, 'is_error', False) or False
                                tool_use_id = getattr(block, 'tool_use_id', '')

                                if isinstance(result_content, list):
                                    # Se for lista de dicts, converte para string
                                    result_content = str(result_content)[:500]
                                elif result_content:
                                    result_content = str(result_content)[:500]
                                else:
                                    result_content = "(sem resultado)"

                                # Encontra o nome da tool pelo tool_use_id
                                tool_name = next(
                                    (tc.name for tc in tool_calls if tc.id == tool_use_id),
                                    'ferramenta'
                                )

                                # MELHORIA: Log detalhado de erros de tools
                                # Erros esperados (arquivo não existe) usam debug
                                # Erros inesperados usam warning
                                if is_error:
                                    expected_errors = [
                                        'does not exist',
                                        'not found',
                                        'no such file',
                                    ]
                                    is_expected = any(
                                        err in result_content.lower()
                                        for err in expected_errors
                                    )
                                    if is_expected:
                                        logger.debug(
                                            f"[AGENT_CLIENT] Tool '{tool_name}' (esperado): "
                                            f"{result_content[:100]}"
                                        )
                                    else:
                                        logger.warning(
                                            f"[AGENT_CLIENT] Tool '{tool_name}' retornou erro: "
                                            f"{result_content[:200]}"
                                        )

                                yield StreamEvent(
                                    type='tool_result',
                                    content=result_content,
                                    metadata={
                                        'tool_use_id': tool_use_id,
                                        'tool_name': tool_name,
                                        'is_error': is_error,
                                        'duration_ms': tool_duration_ms,  # DIAGNÓSTICO
                                    }
                                )
                    continue

                # Mensagem de resultado final
                # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking
                if isinstance(message, ResultMessage):
                    # ✅ NÃO emite texto aqui - já foi emitido pelos TextBlocks do AssistantMessage
                    # O ResultMessage.result contém o texto completo, mas duplicaria o que já foi enviado
                    # Apenas captura o texto final para métricas
                    if message.result:
                        full_text = message.result

                    # Session ID do resultado
                    if hasattr(message, 'session_id') and message.session_id:
                        current_session_id = message.session_id

                    # Emite evento done com métricas (apenas uma vez)
                    if not done_emitted:
                        # D6: Self-Correction antes de entregar resposta
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
                                'session_id': current_session_id,
                                'tool_calls': len(tool_calls),
                                'self_corrected': correction is not None,
                            },
                            metadata={'message_id': last_message_id or ''}
                        )
                    # NÃO usar return - deixar o loop terminar naturalmente

            # Se não recebeu ResultMessage, emite done
            if not done_emitted:
                # D6: Self-Correction (fallback path)
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
                        'session_id': current_session_id,
                        'tool_calls': len(tool_calls),
                        'self_corrected': correction is not None,
                    }
                )

        # =================================================================
        # SDK 0.1.26+: Error Classes especializadas (antes do genérico)
        # =================================================================
        except CLINotFoundError as e:
            elapsed_total = time.time() - stream_start_time
            logger.critical(
                f"[AGENT_CLIENT] CLI não encontrada após {elapsed_total:.1f}s: {e}"
            )
            yield StreamEvent(
                type='error',
                content="Erro crítico: CLI do agente não encontrada. Reinstale o SDK.",
                metadata={'error_type': 'cli_not_found', 'elapsed_seconds': elapsed_total}
            )
            if not done_emitted:
                done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': full_text, 'session_id': current_session_id,
                             'error_recovery': True},
                    metadata={'error_type': 'cli_not_found'}
                )

        except ProcessError as e:
            elapsed_total = time.time() - stream_start_time
            exit_code = getattr(e, 'exit_code', None)
            logger.error(
                f"[AGENT_CLIENT] Process error após {elapsed_total:.1f}s | "
                f"exit_code={exit_code} | mensagem={e}"
            )
            user_message = str(e)
            if exit_code:
                user_message = f"Erro de processo (código {exit_code}). Tente novamente."
            yield StreamEvent(
                type='error',
                content=user_message,
                metadata={'error_type': 'process_error', 'exit_code': exit_code,
                          'elapsed_seconds': elapsed_total, 'last_tool': current_tool_name}
            )
            if not done_emitted:
                done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': full_text, 'input_tokens': input_tokens,
                             'output_tokens': output_tokens, 'session_id': current_session_id,
                             'tool_calls': len(tool_calls), 'error_recovery': True},
                    metadata={'error_type': 'process_error'}
                )

        except CLIJSONDecodeError as e:
            elapsed_total = time.time() - stream_start_time
            logger.error(
                f"[AGENT_CLIENT] JSON decode error após {elapsed_total:.1f}s: {e}"
            )
            yield StreamEvent(
                type='error',
                content="Erro ao processar resposta do agente. Tente novamente.",
                metadata={'error_type': 'json_decode_error', 'elapsed_seconds': elapsed_total}
            )
            if not done_emitted:
                done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': full_text, 'session_id': current_session_id,
                             'error_recovery': True},
                    metadata={'error_type': 'json_decode_error'}
                )

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__

            # =================================================================
            # DIAGNÓSTICO: Log detalhado com contexto de tempo
            # =================================================================
            elapsed_total = time.time() - stream_start_time
            logger.error(
                f"[AGENT_CLIENT] EXCEÇÃO após {elapsed_total:.1f}s | "
                f"tipo={error_type} | mensagem={error_msg}",
                exc_info=True
            )

            # Se estava executando uma tool, loga qual era
            if current_tool_name:
                logger.error(f"[AGENT_CLIENT] Tool em execução quando falhou: {current_tool_name}")

            # Mensagem amigável para o usuário
            user_message = error_msg
            if 'timeout' in error_msg.lower():
                user_message = "Tempo limite excedido. Tente uma consulta mais simples."
            elif 'connection' in error_msg.lower():
                user_message = "Erro de conexão com a API. Tente novamente em alguns segundos."
            elif 'permission' in error_msg.lower() or 'denied' in error_msg.lower():
                user_message = f"Operação não permitida: {error_msg}"
            elif 'rate' in error_msg.lower() and 'limit' in error_msg.lower():
                user_message = "Limite de requisições excedido. Aguarde um momento."

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

            # =================================================================
            # GARANTIA: Emite done mesmo em caso de erro
            # =================================================================
            # Isso garante que o frontend não fica esperando eternamente.
            # O routes.py depende do evento 'done' para finalizar corretamente.
            # =================================================================
            if not done_emitted:
                done_emitted = True
                logger.warning("[AGENT_CLIENT] Emitindo 'done' após exceção para evitar travamento")
                yield StreamEvent(
                    type='done',
                    content={
                        'text': full_text,
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'session_id': current_session_id,
                        'tool_calls': len(tool_calls),
                        'error_recovery': True,  # Flag indicando que veio de erro
                    },
                    metadata={'error_type': error_type}
                )

    def _build_options_for_client(
        self,
        user_name: str = "Usuário",
        can_use_tool: Optional[Callable] = None,
        max_turns: int = 10,
        model: Optional[str] = None,
        thinking_enabled: bool = False,
        plan_mode: bool = False,
        user_id: int = None,
        allowed_tools: Optional[List[str]] = None,
    ) -> 'ClaudeAgentOptions':
        """
        Constroi ClaudeAgentOptions para criacao de ClaudeSDKClient.

        Reutiliza toda logica de _build_options() mas:
        - NAO inclui 'resume' (ClaudeSDKClient gerencia sessao internamente)
        - NAO inclui 'fork_session'
        - Mantem: model, system_prompt, cwd, allowed_tools, hooks, betas, agents, etc.

        Returns:
            ClaudeAgentOptions configurado para ClaudeSDKClient
        """
        # Reutilizar _build_options sem session_id (nao faz resume)
        options = self._build_options(
            session_id=None,  # Sem resume — ClaudeSDKClient gerencia sessao
            user_name=user_name,
            allowed_tools=allowed_tools,
            permission_mode="plan" if plan_mode else "default",
            can_use_tool=can_use_tool,
            max_turns=max_turns,
            model=model,
            thinking_enabled=thinking_enabled,
            user_id=user_id,
        )
        return options

    async def _stream_response_sdk_client(
        self,
        prompt: str,
        pooled_client: Any,  # PooledClient (import circular evitado)
        user_name: str = "Usuário",
        can_use_tool: Optional[Callable] = None,
        max_turns: int = 10,
        model: Optional[str] = None,
        thinking_enabled: bool = False,
        plan_mode: bool = False,
        user_id: int = None,
        image_files: Optional[List[dict]] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming usando ClaudeSDKClient — path bidirecional.

        O ClaudeSDKClient mantem sessao persistente no pool. Cada chamada a
        query() preserva contexto das mensagens anteriores automaticamente.

        Diferencas vs _stream_response_query():
        - NAO cria options (ja aplicadas na criacao do client no pool)
        - NAO tem prompt_generator() (envia prompt direto ao client.query())
        - NAO tem resume (client ja mantem sessao)
        - Emite 'init' sintetico (ClaudeSDKClient nao emite init como query())

        Args:
            prompt: Mensagem do usuario
            pooled_client: PooledClient do SessionPool
            user_name: Nome do usuario
            can_use_tool: Callback de permissao (nao usado aqui — ja no client)
            max_turns: Maximo de turnos (nao usado aqui — ja no client)
            model: Modelo (pode mudar via set_model se diferente do client)
            thinking_enabled: Extended Thinking (nao mutavel apos criacao)
            plan_mode: Modo somente-leitura (nao mutavel apos criacao)
            user_id: ID do usuario
            image_files: Lista de imagens em formato Vision API (FEAT-032)

        Yields:
            StreamEvent com tipo e conteudo
        """
        full_text = ""
        tool_calls = []
        input_tokens = 0
        output_tokens = 0
        last_message_id = None
        done_emitted = False

        # Diagnostico de tempo
        stream_start_time = time.time()
        last_message_time = stream_start_time
        current_tool_start_time = None
        current_tool_name = None

        # Emitir init sintetico (ClaudeSDKClient nao emite evento init)
        yield StreamEvent(
            type='init',
            content={'session_id': pooled_client.session_id},
            metadata={'timestamp': datetime.utcnow().isoformat(), 'sdk_client': True}
        )

        # Se modelo mudou desde a criacao do client, atualizar
        if model and hasattr(pooled_client.client, 'set_model'):
            try:
                await pooled_client.client.set_model(model)
            except Exception as e:
                logger.warning(f"[AGENT_CLIENT_SDK] Erro ao mudar modelo: {e}")

        # Construir prompt com imagens (FEAT-032)
        if image_files:
            # ClaudeSDKClient.query() aceita AsyncIterable de dicts (mesmo formato que query())
            content_blocks = []
            for img in image_files:
                content_blocks.append(img)
            content_blocks.append({"type": "text", "text": prompt})

            async def prompt_with_images():
                yield {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": content_blocks
                    }
                }

            query_prompt = prompt_with_images()
        else:
            query_prompt = prompt

        try:
            # Serializar: apenas 1 query por vez no mesmo client
            async with pooled_client.lock:
                pooled_client.touch()

                # Enviar query ao ClaudeSDKClient
                await pooled_client.client.query(query_prompt)

                # Receber resposta (mesmos tipos de mensagem que query())
                async for message in pooled_client.client.receive_response():
                    # Diagnostico de tempo
                    current_time = time.time()
                    elapsed_total = current_time - stream_start_time
                    elapsed_since_last = current_time - last_message_time
                    last_message_time = current_time

                    logger.debug(
                        f"[AGENT_CLIENT_SDK] Mensagem recebida | "
                        f"tipo={type(message).__name__} | "
                        f"total={elapsed_total:.1f}s | "
                        f"desde_última={elapsed_since_last:.1f}s"
                    )

                    # Mensagem de sistema (init) — ja emitimos sintetico acima
                    if hasattr(message, 'subtype') and message.subtype == 'init':
                        continue

                    # Mensagem do assistente
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
                                f"[AGENT_CLIENT_SDK] API error: type={error_type_str}, error={error_info}"
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
                                    logger.info(f"[AGENT_CLIENT_SDK] Tool INICIADA: {block.name}")

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

                    # Tool result
                    if isinstance(message, UserMessage):
                        tool_duration_ms = 0
                        if current_tool_start_time:
                            tool_duration_ms = int((time.time() - current_tool_start_time) * 1000)
                            logger.info(
                                f"[AGENT_CLIENT_SDK] Tool COMPLETADA: {current_tool_name} em {tool_duration_ms}ms"
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
                                            logger.debug(f"[AGENT_CLIENT_SDK] Tool '{tool_name}' (esperado): {result_content[:100]}")
                                        else:
                                            logger.warning(f"[AGENT_CLIENT_SDK] Tool '{tool_name}' erro: {result_content[:200]}")

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

                    # ResultMessage — final
                    if isinstance(message, ResultMessage):
                        if message.result:
                            full_text = message.result

                        # Detectar interrupt: subtype indica interrupcao
                        is_interrupted = (
                            getattr(message, 'subtype', '') in ('interrupted', 'canceled', 'cancelled')
                            or (message.is_error and 'interrupt' in str(message.result or '').lower())
                        )

                        if is_interrupted and not done_emitted:
                            # Emitir interrupt_ack ANTES do done
                            logger.info(
                                f"[AGENT_CLIENT_SDK] Interrupt detectado | "
                                f"subtype={getattr(message, 'subtype', 'N/A')} | "
                                f"text_so_far={len(full_text)} chars"
                            )
                            yield StreamEvent(
                                type='interrupt_ack',
                                content='Operação interrompida pelo usuário',
                                metadata={'sdk_client': True}
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
                                    'session_id': pooled_client.session_id,
                                    'tool_calls': len(tool_calls),
                                    'self_corrected': correction is not None if correction else False,
                                    'interrupted': is_interrupted,
                                },
                                metadata={'message_id': last_message_id or '', 'sdk_client': True}
                            )

                # Fallback: se nao recebeu ResultMessage
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
                            'session_id': pooled_client.session_id,
                            'tool_calls': len(tool_calls),
                            'self_corrected': correction is not None if correction else False,
                        }
                    )

        except ProcessError as e:
            elapsed_total = time.time() - stream_start_time
            exit_code = getattr(e, 'exit_code', None)
            logger.error(
                f"[AGENT_CLIENT_SDK] Process error após {elapsed_total:.1f}s | "
                f"exit_code={exit_code} | mensagem={e}"
            )
            pooled_client.connected = False  # Marcar como morto
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
                             'output_tokens': output_tokens, 'session_id': pooled_client.session_id,
                             'tool_calls': len(tool_calls), 'error_recovery': True},
                    metadata={'error_type': 'process_error', 'sdk_client': True}
                )
            # Re-raise para que routes.py destrua o client no pool e retente
            raise

        except CLINotFoundError as e:
            elapsed_total = time.time() - stream_start_time
            logger.critical(f"[AGENT_CLIENT_SDK] CLI nao encontrada após {elapsed_total:.1f}s: {e}")
            pooled_client.connected = False
            yield StreamEvent(
                type='error',
                content="Erro crítico: CLI do agente não encontrada.",
                metadata={'error_type': 'cli_not_found', 'elapsed_seconds': elapsed_total}
            )
            if not done_emitted:
                done_emitted = True
                yield StreamEvent(
                    type='done',
                    content={'text': full_text, 'session_id': pooled_client.session_id,
                             'error_recovery': True},
                    metadata={'error_type': 'cli_not_found', 'sdk_client': True}
                )
            raise

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            elapsed_total = time.time() - stream_start_time
            logger.error(
                f"[AGENT_CLIENT_SDK] EXCEÇÃO após {elapsed_total:.1f}s | "
                f"tipo={error_type} | mensagem={error_msg}",
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
                logger.warning("[AGENT_CLIENT_SDK] Emitindo 'done' após exceção")
                yield StreamEvent(
                    type='done',
                    content={
                        'text': full_text,
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'session_id': pooled_client.session_id,
                        'tool_calls': len(tool_calls),
                        'error_recovery': True,
                    },
                    metadata={'error_type': error_type, 'sdk_client': True}
                )

    async def get_response(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        user_name: str = "Usuário",
        allowed_tools: Optional[List[str]] = None,
    ) -> AgentResponse:
        """
        Obtém resposta completa (não streaming).

        Args:
            prompt: Mensagem do usuário
            session_id: ID de sessão
            user_name: Nome do usuário
            allowed_tools: Lista de tools permitidas

        Returns:
            AgentResponse completa
        """
        full_text = ""
        tool_calls = []
        input_tokens = 0
        output_tokens = 0
        stop_reason = ""
        result_session_id = session_id

        async for event in self.stream_response(
            prompt=prompt,
            session_id=session_id,
            user_name=user_name,
            allowed_tools=allowed_tools,
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
