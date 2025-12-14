"""
Cliente do Claude Agent SDK.

Wrapper que encapsula a comunicação com a API usando o SDK oficial.
Suporta streaming, tools, sessions e permissions.

Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/
"""

import logging
import asyncio
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
                "Read",       # Leitura de arquivos (útil para contexto)
                "Glob",       # Busca de arquivos
                "Grep",       # Busca em conteúdo
                "Write",      # Escrita de arquivos (RESTRITO a /tmp via can_use_tool)
                "Edit",       # Edição de arquivos (RESTRITO a /tmp via can_use_tool)
                "TodoWrite",  # Gerenciamento de tarefas (feedback visual)
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

        # Callback de permissão (formato: {behavior, updatedInput, message})
        # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/permissions
        if can_use_tool:
            options_dict["can_use_tool"] = can_use_tool

        return ClaudeAgentOptions(**options_dict)

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
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming usando SDK oficial.

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

        # Gerador assíncrono para o prompt (OBRIGATÓRIO quando can_use_tool é usado)
        # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/streaming-vs-single-mode
        async def prompt_generator():
            yield {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": prompt
                }
            }

        try:
            # Conforme documentação: async for termina naturalmente quando generator é exaurido
            # NÃO usar return/break - deixar o loop terminar sozinho
            async for message in query(prompt=prompt_generator(), options=options):
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
                        done_emitted = True
                        yield StreamEvent(
                            type='done',
                            content={
                                'text': full_text,
                                'input_tokens': input_tokens,
                                'output_tokens': output_tokens,
                                'total_cost_usd': getattr(message, 'total_cost_usd', 0) or 0,
                                'session_id': current_session_id,
                                'tool_calls': len(tool_calls)
                            },
                            metadata={'message_id': last_message_id or ''}
                        )
                    # NÃO usar return - deixar o loop terminar naturalmente

            # Se não recebeu ResultMessage, emite done
            if not done_emitted:
                yield StreamEvent(
                    type='done',
                    content={
                        'text': full_text,
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'session_id': current_session_id,
                        'tool_calls': len(tool_calls)
                    }
                )

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__

            # Log detalhado do erro
            logger.error(
                f"[AGENT_CLIENT] Erro ({error_type}): {error_msg}",
                exc_info=True
            )

            # Mensagem amigável para o usuário
            user_message = error_msg
            if 'timeout' in error_msg.lower():
                user_message = "⏱️ Tempo limite excedido. Tente uma consulta mais simples."
            elif 'connection' in error_msg.lower():
                user_message = "🔌 Erro de conexão com a API. Tente novamente em alguns segundos."
            elif 'permission' in error_msg.lower() or 'denied' in error_msg.lower():
                user_message = f"🚫 Operação não permitida: {error_msg}"
            elif 'rate' in error_msg.lower() and 'limit' in error_msg.lower():
                user_message = "⚠️ Limite de requisições excedido. Aguarde um momento."

            yield StreamEvent(
                type='error',
                content=user_message,
                metadata={
                    'error_type': error_type,
                    'original_error': error_msg[:500]
                }
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
