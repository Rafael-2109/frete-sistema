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
    - Skills via option `skills=` em ClaudeAgentOptions (SDK 0.1.77+):
      filtra o listing do model para apenas SKILLS_PERMITIDAS, reforcando o
      contrato de isolamento HORA documentado em app/hora/CLAUDE.md.
      SDK auto-configura "Skill" em allowed_tools + setting_sources=["project"].
      Fallback (SDK < 0.1.77): "Skill" injetado em allowed_tools manualmente.
"""
import dataclasses
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
from app.agente_lojas.config.skills_whitelist import SKILLS_PERMITIDAS
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
# - Bash: executar scripts das skills (consultas SQL via consultando-sql)
# - Task: invocar subagent `orientador-loja` (M2)
# - Read/Glob/Grep: leitura de arquivos do projeto (SKILL.md, schemas, etc.)
# - TodoWrite: feedback visual de tarefas
# NAO incluir Write/Edit/MultiEdit — operador de loja nao modifica codigo.
# NOTA: 'Skill' NAO esta listada — SDK 0.1.77+ adiciona automaticamente quando
# `skills=` esta set em ClaudeAgentOptions. Fallback (SDK < 0.1.77) injeta
# 'Skill' em build_options() manualmente. Ver _SDK_HAS_SKILLS_OPTION.
ALLOWED_TOOLS_M1 = [
    'Bash',
    'Task',
    'Read',
    'Glob',
    'Grep',
    'TodoWrite',
]


def _check_skills_option() -> bool:
    """Verifica se ClaudeAgentOptions tem campo `skills` nativo (SDK 0.1.77+).

    SDK 0.1.77 deprecou "Skill" em allowed_tools em favor da option
    `skills: list[str] | Literal["all"] | None` em ClaudeAgentOptions.
    Quando set, SDK auto-configura "Skill" em allowed_tools E
    setting_sources, alem de filtrar o listing do model.

    Returns:
        True se SDK >= 0.1.77 (campo skills presente), False caso contrario.
    """
    try:
        fields = {f.name for f in dataclasses.fields(ClaudeAgentOptions)}
        return 'skills' in fields
    except Exception:
        return False


# Detectado uma vez no import — zero overhead por request
_SDK_HAS_SKILLS_OPTION = _check_skills_option()


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

        # Skills: passar lista explicita via SDK option (0.1.77+) reforca
        # contrato de isolamento HORA — skills de Nacom Goya nao aparecem no
        # listing do model. Fallback SDK < 0.1.77: 'Skill' em allowed_tools
        # + setting_sources=["project"] descobre tudo (sem filtro).
        allowed_tools = list(ALLOWED_TOOLS_M1)
        if not _SDK_HAS_SKILLS_OPTION:
            allowed_tools.append('Skill')

        options_kwargs: Dict[str, Any] = {
            "model": self.settings.model,
            "max_turns": 20,
            "max_buffer_size": 10_000_000,  # 10MB para tool_results grandes
            "system_prompt": self._build_system_prompt(),
            "cwd": PROJECT_ROOT,
            "setting_sources": ["project"],  # descobre skills em .claude/skills/
            "allowed_tools": allowed_tools,
            "permission_mode": "acceptEdits",
            "fallback_model": "sonnet",
            "disallowed_tools": ["Write", "Edit", "MultiEdit", "NotebookEdit"],
            "hooks": {
                "UserPromptSubmit": [HookMatcher(hooks=[submit_hook])],
            },
        }

        # SDK 0.1.77+: option `skills` filtra listing do model + auto-config
        # de "Skill" em allowed_tools. Lista ordenada para determinismo.
        # Doc: "context filter, not sandbox" — arquivos das skills continuam
        # acessiveis via Read/Bash; o filtro complementa can_use_tool.
        if _SDK_HAS_SKILLS_OPTION:
            options_kwargs["skills"] = sorted(SKILLS_PERMITIDAS)

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

        except GeneratorExit:
            # Cliente desconectou o SSE (mobile, refresh, navegacao).
            # Re-raise eh obrigatorio para encerrar o async generator.
            # Nao logar como erro — eh fluxo normal.
            logger.info("[AGENTE_LOJAS] stream encerrado (cliente desconectou)")
            raise
        except RuntimeError as e:
            # FIX PYTHON-FLASK-PY: "Event loop is closed" no __aexit__ do
            # ClaudeSDKClient quando o cliente desconecta antes do fim do stream.
            # Eh consequencia do GeneratorExit — nao eh bug real.
            if "Event loop is closed" in str(e):
                logger.info("[AGENTE_LOJAS] stream encerrado (event loop closed)")
                return
            logger.exception("[AGENTE_LOJAS] Erro no stream: %s", e)
            yield {
                'type': 'error',
                'content': str(e),
                'metadata': {'exception_type': type(e).__name__},
            }
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
