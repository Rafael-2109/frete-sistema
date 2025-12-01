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
    ToolUseBlock,
    TextBlock,
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
    - Usa SKILLS para funcionalidades (.claude/skills/agente-logistico/)
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

    def _format_system_prompt(
        self,
        user_name: str = "Usuário",
        extra_context: str = ""
    ) -> str:
        """
        Formata system prompt com variáveis.

        Args:
            user_name: Nome do usuário
            extra_context: Contexto adicional

        Returns:
            System prompt formatado
        """
        prompt = self.system_prompt.replace(
            "{data_atual}",
            datetime.now().strftime("%d/%m/%Y %H:%M")
        )
        prompt = prompt.replace("{usuario_nome}", user_name)

        if extra_context:
            prompt = prompt.replace("{conhecimento_negocio}", extra_context)
        else:
            prompt = prompt.replace("{conhecimento_negocio}", "")

        return prompt

    def _build_options(
        self,
        session_id: Optional[str] = None,
        user_name: str = "Usuário",
        extra_context: str = "",
        allowed_tools: Optional[List[str]] = None,
        permission_mode: str = "default",
        can_use_tool: Optional[Callable] = None,
        max_turns: int = 10,
        fork_session: bool = False,
    ) -> ClaudeAgentOptions:
        """
        Constrói ClaudeAgentOptions conforme documentação oficial Anthropic.

        ARQUITETURA (conforme melhores práticas):
        - Usa SKILLS para funcionalidades (.claude/skills/agente-logistico/)
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
            extra_context: Contexto adicional
            allowed_tools: Lista de tools permitidas
            permission_mode: Modo de permissão (default, acceptEdits, plan, bypassPermissions)
            can_use_tool: Callback de permissão (retorna {behavior, updatedInput})
            max_turns: Máximo de turnos
            fork_session: Se deve bifurcar a sessão

        Returns:
            ClaudeAgentOptions configurado
        """
        import os

        # System prompt customizado
        custom_instructions = self._format_system_prompt(user_name, extra_context)

        # Diretório do projeto para carregar Skills
        # Skills estão em: .claude/skills/agente-logistico/
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

            # Modelo a ser usado
            "model": self.settings.model,

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
            # Default: Apenas tools necessárias para Skills funcionarem
            options_dict["allowed_tools"] = [
                "Skill",  # OBRIGATÓRIO - permite Claude invocar Skills
                "Bash",   # OBRIGATÓRIO - executa scripts Python das Skills
                "Read",   # Leitura de arquivos (útil para contexto)
                "Glob",   # Busca de arquivos
                "Grep",   # Busca em conteúdo
            ]

        # Modo de permissão
        # Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/permissions
        if permission_mode in ['default', 'acceptEdits', 'plan', 'bypassPermissions']:
            options_dict["permission_mode"] = permission_mode
        else:
            options_dict["permission_mode"] = "default"

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
        extra_context: str = "",
        allowed_tools: Optional[List[str]] = None,
        can_use_tool: Optional[Callable] = None,
        max_turns: int = 10,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Gera resposta em streaming usando SDK oficial.

        Args:
            prompt: Mensagem do usuário
            session_id: ID de sessão para retomar
            user_name: Nome do usuário
            extra_context: Contexto adicional
            allowed_tools: Lista de tools permitidas
            can_use_tool: Callback de permissão
            max_turns: Máximo de turnos

        Yields:
            StreamEvent com tipo e conteúdo
        """
        options = self._build_options(
            session_id=session_id,
            user_name=user_name,
            extra_context=extra_context,
            allowed_tools=allowed_tools,
            can_use_tool=can_use_tool,
            max_turns=max_turns,
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

                                yield StreamEvent(
                                    type='tool_call',
                                    content=block.name,
                                    metadata={
                                        'tool_id': block.id,
                                        'input': block.input
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
            logger.error(f"[AGENT_CLIENT] Erro: {e}")
            yield StreamEvent(
                type='error',
                content=str(e)
            )

    async def get_response(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        user_name: str = "Usuário",
        extra_context: str = "",
        allowed_tools: Optional[List[str]] = None,
    ) -> AgentResponse:
        """
        Obtém resposta completa (não streaming).

        Args:
            prompt: Mensagem do usuário
            session_id: ID de sessão
            user_name: Nome do usuário
            extra_context: Contexto adicional
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
            extra_context=extra_context,
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
