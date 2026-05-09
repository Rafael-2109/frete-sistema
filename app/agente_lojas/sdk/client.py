"""
AgentLojasClient — wrapper enxuto do Claude Agent SDK para o Agente Lojas HORA.

Usa ClaudeSDKClient diretamente (nao herda do AgentClient do agente logistico)
para manter o codigo deste modulo independente e simples:

    ~350 LOC total vs ~2200 do AgentClient.

O que M2 implementa (atualizado 2026-05-09):
    - Stream SSE real via ClaudeSDKClient
    - System prompt proprio (sem briefing do agente logistico)
    - Hook user_prompt_submit injetando <loja_context> + <session_context>
    - Hook PreToolUse `_keep_stream_open` (requerido pelo SDK para
      can_use_tool funcionar)
    - can_use_tool callback intercepta AskUserQuestion e roteia para
      pending_questions / event_queue
    - Skills via option `skills=` em ClaudeAgentOptions (SDK 0.1.77+):
      filtra o listing do model para apenas SKILLS_PERMITIDAS, reforcando o
      contrato de isolamento HORA documentado em app/hora/CLAUDE.md.
      SDK auto-configura "Skill" em allowed_tools + setting_sources.
      Fallback (SDK < 0.1.77): "Skill" injetado em allowed_tools manualmente.

Pendente (M3):
    - Pool persistente (Fase B: criar client_pool.py enxuto)
    - Memoria injection (cross-agente contaminante; em M3)
    - Cost tracking granular por subagente (em M3)
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
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from app.agente_lojas.config.settings import get_lojas_settings
from app.agente_lojas.config.skills_whitelist import SKILLS_PERMITIDAS
from app.agente_lojas.config.permissions import (
    can_use_tool as lojas_can_use_tool,
    set_current_session_id,
    set_event_queue,
    cleanup_session_context,
)
from app.agente_lojas.sdk.hooks import (
    make_user_prompt_submit_hook,
    _keep_stream_open,
)

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
        """Constroi ClaudeAgentOptions para o turno corrente.

        NOTA: can_use_tool e injetado em stream_response (apos
        set_current_session_id), nao aqui — e callback global do modulo
        permissions.py que le session_id via ContextVar.
        """
        submit_hook = make_user_prompt_submit_hook(
            user_id=user_id,
            user_name=user_name,
            perfil=perfil,
            loja_hora_id=loja_hora_id,
        )

        # Skills: passar lista explicita via SDK option (0.1.77+) reforca
        # contrato de isolamento HORA. SDK injeta patterns granulares
        # `Skill(name)` no allowed_tools (verificado em
        # _internal/transport/subprocess_cli.py:165-201:_apply_skills_defaults) —
        # filtro forte real, NAO apenas listing filter. Skills nao listadas
        # sao rejeitadas pelo Skill tool. Fallback SDK < 0.1.77: 'Skill'
        # em allowed_tools (sem filtro per-skill).
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
            # can_use_tool: validacao dinamica de tools. Roteia AskUserQuestion
            # para pending_questions + event_queue. Callback global le session_id
            # da ContextVar setada em stream_response().
            "can_use_tool": lojas_can_use_tool,
            # Hooks: UserPromptSubmit (contexto loja) + PreToolUse (keep-alive
            # OBRIGATORIO para can_use_tool funcionar — doc SDK).
            "hooks": {
                "UserPromptSubmit": [HookMatcher(hooks=[submit_hook])],
                "PreToolUse": [HookMatcher(hooks=[_keep_stream_open])],
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
        our_session_id: Optional[str] = None,
        event_queue: Optional[Any] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream de resposta do SDK.

        Args:
            our_session_id: Nosso UUID de sessao (AgentSession.session_id).
                Setado em ContextVar para can_use_tool encontrar event_queue.
                Distinto de sdk_session_id (UUID nomeando o JSONL do SDK).
            event_queue: Queue thread-safe usada pelo can_use_tool para emitir
                eventos `ask_user_question` ao SSE generator. Se None,
                AskUserQuestion sera negado pelo can_use_tool.

        Yields:
            dicts {type, content, metadata} — formato usado pelo SSE generator
            da route chat.py. Tipos: 'text', 'tool_call', 'tool_result',
            'thinking', 'done', 'error'.
        """
        # Registrar session_id e event_queue ANTES de iniciar o stream para
        # que can_use_tool (rodando em thread daemon do SDK) consiga emitir
        # eventos ask_user_question via event_queue cross-thread.
        if our_session_id:
            set_current_session_id(our_session_id)
            if event_queue is not None:
                set_event_queue(our_session_id, event_queue)

        options = self.build_options(
            user_id=user_id,
            user_name=user_name,
            perfil=perfil,
            loja_hora_id=loja_hora_id,
            sdk_session_id=sdk_session_id,
        )

        logger.info(
            "[AGENTE_LOJAS] stream_response start | user_id=%s loja_id=%s "
            "our_session=%s sdk_session=%s ask_user=%s",
            user_id, loja_hora_id,
            (our_session_id or '')[:8], (sdk_session_id or '')[:8],
            'yes' if event_queue is not None else 'no',
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
        finally:
            # Cleanup: cancelar pending_questions + remover stream_context.
            # Garante que se cliente desconectou no meio de AskUserQuestion,
            # a thread daemon do SDK desbloqueia (cancel_pending sinaliza event).
            if our_session_id:
                try:
                    from app.agente.sdk.pending_questions import cancel_pending
                    cancel_pending(our_session_id)
                except Exception:
                    pass
                cleanup_session_context(our_session_id)


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
            elif isinstance(block, ThinkingBlock):
                # ThinkingBlock so eh emitido se thinking_display=summarized.
                # Default do agente_lojas (heran ado de AgentSettings) e omitted —
                # nesses casos esse branch nunca dispara.
                yield {
                    'type': 'thinking',
                    'content': getattr(block, 'thinking', '') or '',
                    'metadata': {},
                }
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
    our_session_id: Optional[str] = None,
    event_queue: Optional[Any] = None,
):
    """High-level helper usado pelo route chat.py. Yields dicts.

    Args:
        our_session_id: AgentSession.session_id (UUID nosso). Usado para
            registrar event_queue cross-thread em can_use_tool.
        event_queue: Queue thread-safe para eventos `ask_user_question`.
    """
    client = get_lojas_client()
    async for event in client.stream_response(
        user_message=user_message,
        user_id=user_id,
        user_name=user_name,
        perfil=perfil,
        loja_hora_id=loja_hora_id,
        sdk_session_id=sdk_session_id,
        our_session_id=our_session_id,
        event_queue=event_queue,
    ):
        yield event
