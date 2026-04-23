"""
AgentLojasClient — wrapper enxuto do Claude Agent SDK para o Agente Lojas HORA.

Usa ClaudeSDKClient diretamente (nao herda do AgentClient do agente logistico)
para manter o codigo deste modulo independente e simples:

    ~250 LOC total vs ~2200 do AgentClient.

M1 nao implementa:
    - Pool persistente (uma conexao por request, sem resume do SDK)
    - Memoria injection (cross-agente contaminante; em M3)
    - Pending questions / ask user (em M2)
    - Output structuring JSON schema (em M2)
    - Cost tracking granular por subagente (em M3)

O que M1 implementa:
    - Stream SSE real via ClaudeSDKClient
    - System prompt proprio (sem briefing do agente logistico)
    - Hook user_prompt_submit injetando <loja_context> + <session_context>
    - Skills via .claude/skills/* (SDK descobre via setting_sources=project)
"""
import logging
import os
from typing import AsyncGenerator, Optional, Dict, Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from app.agente_lojas.config.settings import get_lojas_settings
from app.agente_lojas.sdk.hooks import make_user_prompt_submit_hook

logger = logging.getLogger('sistema_fretes')


# Raiz do projeto (para setting_sources=["project"])
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)


# Tools minimas que o agente de lojas precisa em M1
# - Skill: invocar skills do dominio HORA
# - Bash: executar scripts das skills (consultas SQL via consultando-sql)
# - Read/Glob/Grep: leitura de arquivos do projeto (SKILL.md, schemas, etc.)
# - TodoWrite: feedback visual de tarefas
# NAO incluir Write/Edit/MultiEdit — operador de loja nao modifica codigo.
ALLOWED_TOOLS_M1 = [
    'Skill',
    'Bash',
    'Task',
    'Read',
    'Glob',
    'Grep',
    'TodoWrite',
]


class AgentLojasClient:
    """Cliente SDK enxuto para o Agente Lojas HORA."""

    def __init__(self):
        self.settings = get_lojas_settings()
        self.system_prompt = self._load_file(self.settings.system_prompt_path)
        self.preset = self._load_file(self.settings.operational_preset_path)
        logger.info(
            "[AGENTE_LOJAS] AgentLojasClient inicializado | model=%s",
            self.settings.model,
        )

    def _load_file(self, path: str) -> str:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("[AGENTE_LOJAS] Arquivo nao encontrado: %s", path)
            return ""

    def _build_system_prompt(self) -> str:
        """Monta system prompt estatico (cacheavel). Contexto dinamico
        entra via hook user_prompt_submit para preservar cache."""
        blocks = []
        if self.preset:
            blocks.append(self.preset)
        if self.system_prompt:
            blocks.append(self.system_prompt)
        return "\n\n".join(blocks)

    def build_options(
        self,
        user_id: int,
        user_name: str,
        perfil: str,
        loja_hora_id: Optional[int],
        sdk_session_id: Optional[str] = None,
    ) -> ClaudeAgentOptions:
        """Constroi ClaudeAgentOptions para o turno corrente."""
        submit_hook = make_user_prompt_submit_hook(
            user_id=user_id,
            user_name=user_name,
            perfil=perfil,
            loja_hora_id=loja_hora_id,
        )

        options_kwargs: Dict[str, Any] = {
            "model": self.settings.model,
            "max_turns": 20,
            "max_buffer_size": 10_000_000,  # 10MB para tool_results grandes
            "system_prompt": self._build_system_prompt(),
            "cwd": PROJECT_ROOT,
            "setting_sources": ["project"],  # descobre skills em .claude/skills/
            "allowed_tools": list(ALLOWED_TOOLS_M1),
            "permission_mode": "acceptEdits",
            "fallback_model": "sonnet",
            "disallowed_tools": ["Write", "Edit", "MultiEdit", "NotebookEdit"],
            "hooks": {
                "UserPromptSubmit": [HookMatcher(hooks=[submit_hook])],
            },
        }

        # SDK 0.1.52+: passar nosso session_id para nomear o JSONL
        if sdk_session_id:
            options_kwargs["session_id"] = sdk_session_id

        return ClaudeAgentOptions(**options_kwargs)

    async def stream_response(
        self,
        user_message: str,
        user_id: int,
        user_name: str,
        perfil: str,
        loja_hora_id: Optional[int],
        sdk_session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream de resposta do SDK.

        Yields:
            dicts {type, content, metadata} — formato usado pelo SSE generator
            da route chat.py. Tipos: 'text', 'tool_call', 'tool_result',
            'thinking', 'done', 'error'.
        """
        options = self.build_options(
            user_id=user_id,
            user_name=user_name,
            perfil=perfil,
            loja_hora_id=loja_hora_id,
            sdk_session_id=sdk_session_id,
        )

        logger.info(
            "[AGENTE_LOJAS] stream_response start | user_id=%s loja_id=%s session=%s",
            user_id, loja_hora_id, sdk_session_id,
        )

        try:
            async with ClaudeSDKClient(options=options) as sdk_client:
                await sdk_client.query(user_message)

                async for msg in sdk_client.receive_response():
                    async for event in _parse_message(msg):
                        yield event

        except Exception as e:
            logger.exception("[AGENTE_LOJAS] Erro no stream: %s", e)
            yield {
                'type': 'error',
                'content': str(e),
                'metadata': {'exception_type': type(e).__name__},
            }


async def _parse_message(msg) -> AsyncGenerator[Dict[str, Any], None]:
    """Traduz mensagens do SDK em eventos SSE simples."""
    # Init (SystemMessage com session_id)
    if isinstance(msg, SystemMessage):
        data = getattr(msg, 'data', {}) or {}
        sid = data.get('session_id')
        if sid:
            yield {'type': 'init', 'content': '', 'metadata': {'sdk_session_id': sid}}
        return

    # Assistant: text, tool_call, thinking
    if isinstance(msg, AssistantMessage):
        for block in (msg.content or []):
            if isinstance(block, TextBlock):
                yield {'type': 'text', 'content': block.text, 'metadata': {}}
            elif isinstance(block, ToolUseBlock):
                yield {
                    'type': 'tool_call',
                    'content': '',
                    'metadata': {
                        'tool_name': block.name,
                        'tool_id': block.id,
                        'tool_input': block.input,
                    },
                }
        return

    # User (echo de tool_result)
    if isinstance(msg, UserMessage):
        for block in (msg.content or []):
            if isinstance(block, ToolResultBlock):
                content = block.content
                if isinstance(content, list):
                    # Lista de blocks; extrair texto
                    parts = []
                    for b in content:
                        text = getattr(b, 'text', None)
                        if text:
                            parts.append(text)
                    content = "\n".join(parts) if parts else str(content)
                yield {
                    'type': 'tool_result',
                    'content': str(content or ''),
                    'metadata': {
                        'tool_use_id': block.tool_use_id,
                        'is_error': getattr(block, 'is_error', False),
                    },
                }
        return

    # Done
    if isinstance(msg, ResultMessage):
        usage = getattr(msg, 'usage', None) or {}
        yield {
            'type': 'done',
            'content': '',
            'metadata': {
                'stop_reason': getattr(msg, 'stop_reason', None),
                'input_tokens': usage.get('input_tokens', 0) if isinstance(usage, dict) else 0,
                'output_tokens': usage.get('output_tokens', 0) if isinstance(usage, dict) else 0,
                'total_cost_usd': getattr(msg, 'total_cost_usd', 0),
                'num_turns': getattr(msg, 'num_turns', 0),
            },
        }


# Singleton cacheado
_lojas_client_instance: Optional[AgentLojasClient] = None


def get_lojas_client() -> AgentLojasClient:
    """Retorna singleton de AgentLojasClient."""
    global _lojas_client_instance
    if _lojas_client_instance is None:
        _lojas_client_instance = AgentLojasClient()
    return _lojas_client_instance


async def stream_lojas_chat(
    user_message: str,
    user_id: int,
    user_name: str,
    perfil: str,
    loja_hora_id: Optional[int],
    sdk_session_id: Optional[str] = None,
):
    """High-level helper usado pelo route chat.py. Yields dicts."""
    client = get_lojas_client()
    async for event in client.stream_response(
        user_message=user_message,
        user_id=user_id,
        user_name=user_name,
        perfil=perfil,
        loja_hora_id=loja_hora_id,
        sdk_session_id=sdk_session_id,
    ):
        yield event
