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
    # SDK error classes especializadas (F1.3) — handlers no stream_response.
    CLINotFoundError,
    ProcessError,
    CLIConnectionError,
    CLIJSONDecodeError,
)

# Infra compartilhada do SDK (PURA, sem dominio Nacom) — reuso por import de
# submodulo. NUNCA `from app.agente.sdk import ...` (puxa AgentClient + pool).
from app.agente.sdk.sdk_runtime import build_subprocess_env

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
    _post_tool_use_audit,
    _subagent_start_audit,
    _subagent_stop_audit,
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
# - TaskCreate/TaskUpdate/TaskGet/TaskList: feedback visual de tarefas (SDK 0.2.82+: substituiu TodoWrite)
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
    'TaskCreate',
    'TaskUpdate',
    'TaskGet',
    'TaskList',
]


# Deteccao do campo `skills` (SDK 0.1.77+) — modulo compartilhado sdk_compat
# (mesma logica do agente web). Alias preserva o nome local usado em
# build_options (:222, :266). Import de submodulo (sem circular).
from app.agente.sdk.sdk_compat import SDK_HAS_SKILLS_OPTION as _SDK_HAS_SKILLS_OPTION


# =============================================================================
# Feature flags via env var. SessionStore default ON (2026-06-26): o resume
# multi-turno (FIX S1) depende do historico estar materializavel; com o store
# ligado o {id}.jsonl e materializado do Postgres antes do subprocess, tornando
# o resume robusto cross-worker (4 gunicorn). Init tem fallback gracioso para o
# JSONL local se o store falhar. Rollback: AGENT_LOJAS_SESSION_STORE_ENABLED=false.
# =============================================================================
def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name, '').strip().lower()
    if not val:
        return default
    return val in ('true', '1', 'yes', 'on')


_LOJAS_SESSION_STORE_ENABLED: bool = _env_bool(
    'AGENT_LOJAS_SESSION_STORE_ENABLED', default=True,
)
# Timeout em ms para load() do session_store (default 30s — mesmo que Nacom).
_LOJAS_SESSION_STORE_LOAD_TIMEOUT_MS: int = int(
    os.getenv('AGENT_LOJAS_SESSION_STORE_LOAD_TIMEOUT_MS', '30000') or '30000'
)
# Flush mode: 'batched' (default end-of-turn) ou 'eager' (near-real-time).
# Eager util para live-tailing UI / crash durability — exige profiling Postgres.
_LOJAS_SESSION_STORE_FLUSH: str = os.getenv(
    'AGENT_LOJAS_SESSION_STORE_FLUSH', 'batched',
).strip().lower() or 'batched'
if _LOJAS_SESSION_STORE_FLUSH not in ('batched', 'eager'):
    _LOJAS_SESSION_STORE_FLUSH = 'batched'


def _drain_stderr(stderr_queue) -> str:
    """Drena best-effort o stderr capturado do CLI (diagnostico de ProcessError)."""
    if stderr_queue is None:
        return ''
    linhas = []
    while True:
        try:
            linhas.append(stderr_queue.get_nowait())
        except Exception:
            break
    return '\n'.join(linhas)


def _build_error_recovery_events(msg: str, error_type: str, exc: Exception,
                                 extra: Optional[Dict[str, Any]] = None):
    """Par (error, done) que reporta o erro ao usuario E destrava o frontend.

    O `done` com error_recovery=True e OBRIGATORIO: sem ele o SSE generator
    termina sem sinalizar fim e o frontend fica preso esperando o evento de fim.
    Espelha o agente web (client.py:2515-2530).
    """
    meta_err: Dict[str, Any] = {
        'error_type': error_type,
        'exception_type': type(exc).__name__,
    }
    if extra:
        meta_err.update(extra)
    return [
        {'type': 'error', 'content': msg, 'metadata': meta_err},
        {'type': 'done', 'content': '',
         'metadata': {'error_type': error_type, 'error_recovery': True}},
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
        our_session_id: Optional[str] = None,
        output_format: Optional[Dict[str, Any]] = None,
        stderr_queue: Optional[Any] = None,
    ) -> ClaudeAgentOptions:
        """Constroi ClaudeAgentOptions para o turno corrente.

        Args:
            output_format: JSON Schema para structured output (SDK nativo).
                Ex: {"type": "json_schema", "schema": {...}}. ResultMessage
                trara o output parseado em `structured_output`.
            stderr_queue: queue.SimpleQueue para captura de stderr do CLI
                (debug ProcessError). Quando None, stderr nao eh capturado.

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
            # max_turns OMITIDO (sem limite) — alinha ao agente web. max_turns
            # fixo cortava respostas multi-step ("Reached maximum number of turns"
            # + frontend preso); cada tool_use/Skill/subagente conta turno, e o
            # antigo 20 estourava facil. Guarda de runaway = max_budget_usd
            # (default abaixo) + timeouts.
            "max_buffer_size": 10_000_000,  # 10MB para tool_results grandes
            "system_prompt": self._build_system_prompt(),
            "cwd": PROJECT_ROOT,
            "setting_sources": ["project"],  # descobre skills em .claude/skills/
            "allowed_tools": allowed_tools,
            "permission_mode": "acceptEdits",
            "fallback_model": "sonnet",
            "disallowed_tools": ["Write", "Edit", "MultiEdit", "NotebookEdit"],
            # env do subprocesso CLI — helper compartilhado com o agente web
            # (sdk_runtime.build_subprocess_env): HOME=/tmp (Render read-only) +
            # CLAUDE_CODE_STREAM_CLOSE_TIMEOUT (hooks/MCP 240s vs default 60s).
            "env": build_subprocess_env(),
            # can_use_tool: validacao dinamica de tools. Roteia AskUserQuestion
            # para pending_questions + event_queue. Callback global le session_id
            # da ContextVar setada em stream_response().
            "can_use_tool": lojas_can_use_tool,
            # Hooks SDK:
            # - UserPromptSubmit: contexto loja injetado por turno
            # - PreToolUse: keep-alive (OBRIGATORIO p/ can_use_tool — doc SDK)
            # - PostToolUse: audit log estruturado de execucoes
            # - SubagentStart/Stop: audit de delegacao para orientador-loja
            "hooks": {
                "UserPromptSubmit": [HookMatcher(hooks=[submit_hook])],
                "PreToolUse": [HookMatcher(hooks=[_keep_stream_open])],
                "PostToolUse": [HookMatcher(hooks=[_post_tool_use_audit])],
                "SubagentStart": [HookMatcher(hooks=[_subagent_start_audit])],
                "SubagentStop": [HookMatcher(hooks=[_subagent_stop_audit])],
            },
        }

        # SDK 0.1.77+: option `skills` filtra listing do model + auto-config
        # de "Skill" em allowed_tools. Lista ordenada para determinismo.
        # Doc: "context filter, not sandbox" — arquivos das skills continuam
        # acessiveis via Read/Bash; o filtro complementa can_use_tool.
        if _SDK_HAS_SKILLS_OPTION:
            options_kwargs["skills"] = sorted(SKILLS_PERMITIDAS)

        # Continuidade multi-turno (FIX S1 2026-06-26).
        # - Turno 1 (sem sdk_session_id): o SDK gera o id; capturado no init
        #   (_parse_message) e persistido. Nao setamos nada aqui.
        # - Turno 2+ (sdk_session_id UUID valido): RESUME. `resume` -> --resume
        #   CARREGA o {id}.jsonl; `session_id` -> --session-id apenas NOMEIA.
        #   Antes este modulo passava SO session_id reusando o id do turno
        #   anterior, o que NAO carregava o historico (amnesia) e colidia com o
        #   JSONL ja criado. Espelha _with_resume do agente web
        #   (app/agente/sdk/client.py:2842): resume=X SEM session_id, pois
        #   --session-id + --resume exige --fork-session e forkar X->X = exit 1.
        #   O probe ao session_store em stream_response remove o resume se a
        #   sessao nao existir (evita --resume de JSONL inexistente / crash).
        if sdk_session_id:
            try:
                import uuid as _uuid_check
                _uuid_check.UUID(str(sdk_session_id))
                options_kwargs["resume"] = sdk_session_id
            except (ValueError, AttributeError, TypeError):
                logger.warning(
                    "[AGENTE_LOJAS] sdk_session_id invalido (nao UUID), "
                    "ignorando resume: %s", str(sdk_session_id)[:20],
                )
        elif our_session_id:
            # Turno 1 (sem sdk_session_id): pre-nomeia o JSONL com NOSSO UUID via
            # --session-id (apenas NOMEIA; SEM --resume -> sem conflito de fork).
            # Elimina a captura assincrona do id via SystemMessage, fragil em race:
            # se o SystemMessage nao chega, o sdk_session_id fica None e o turno 2
            # perde o resume -> amnesia. Espelha o web (client.py:1655-1663).
            # ADITIVO: so ativa quando our_session_id e passado; callers legados
            # sem o arg mantem o comportamento de deixar o SDK gerar o id. NUNCA
            # cai aqui no turno 2+ (o ramo `if sdk_session_id` ja tratou o resume),
            # preservando o invariante FIX S1 (--session-id + --resume = exit 1).
            try:
                import uuid as _uuid_check
                _uuid_check.UUID(str(our_session_id))
                options_kwargs["session_id"] = our_session_id
            except (ValueError, AttributeError, TypeError):
                logger.debug(
                    "[AGENTE_LOJAS] our_session_id nao-UUID, CLI gerara proprio "
                    "id: %s", str(our_session_id)[:20],
                )

        # Structured output (SDK nativo). ResultMessage.structured_output
        # contera o JSON parseado. Util para skills que retornam tabelas.
        if output_format:
            options_kwargs["output_format"] = output_format

        # Stderr callback: captura stderr do CLI subprocess para diagnostico
        # de ProcessError (SDK 0.1.77+ ja propaga texto real, mas stderr eh
        # complementar para ver erros do CLI antes do crash).
        if stderr_queue is not None:
            def _stderr_callback(line: str):
                try:
                    stderr_queue.put_nowait(line)
                except Exception:
                    pass
            options_kwargs["stderr"] = _stderr_callback
            options_kwargs["extra_args"] = {"debug-to-stderr": None}

        # Budget control nativo: protege contra runaway sessions. Configuravel
        # via env var (default 1.5 USD por request — operadores de loja tipicamente
        # gastam <0.10 USD; valor alto eh sinal de loop ou ferramenta travada).
        # Budget guard de runaway (substitui o teto de max_turns removido acima).
        # Default 1.5 USD/request — operador de loja gasta tipicamente <0.10 USD;
        # valor alto = loop ou ferramenta travada. Override via env var; <=0
        # desliga o guard explicitamente.
        max_budget = 1.5
        max_budget_env = os.getenv('AGENT_LOJAS_MAX_BUDGET_USD')
        if max_budget_env:
            try:
                max_budget = float(max_budget_env)
            except (ValueError, TypeError):
                logger.warning(
                    "[AGENTE_LOJAS] AGENT_LOJAS_MAX_BUDGET_USD invalido: %s "
                    "(esperado float, ex: 1.5) — usando default 1.5", max_budget_env,
                )
                max_budget = 1.5
        if max_budget > 0:
            options_kwargs["max_budget_usd"] = max_budget

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
        output_format: Optional[Dict[str, Any]] = None,
        stderr_queue: Optional[Any] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream de resposta do SDK.

        Args:
            our_session_id: Nosso UUID de sessao (AgentSession.session_id).
                Setado em ContextVar para can_use_tool encontrar event_queue.
                Distinto de sdk_session_id (UUID nomeando o JSONL do SDK).
            event_queue: Queue thread-safe usada pelo can_use_tool para emitir
                eventos `ask_user_question` ao SSE generator. Se None,
                AskUserQuestion sera negado pelo can_use_tool.
            output_format: JSON Schema opcional para structured output.
            stderr_queue: queue.SimpleQueue opcional para stderr do CLI.

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
            our_session_id=our_session_id,
            output_format=output_format,
            stderr_queue=stderr_queue,
        )

        # PostgresSessionStore (SDK 0.1.64+) — multi-worker safe + observability.
        # Flag-gated com fallback gracioso. Se desativado ou erro, SDK usa JSONL
        # local nativo (default). Tabela `claude_session_store` eh compartilhada
        # com agente Nacom (project_key + session_id UUID e chave unica — sem
        # colisao entre agentes).
        if _LOJAS_SESSION_STORE_ENABLED:
            try:
                import dataclasses as _dc
                from app.agente.sdk.session_store_adapter import (
                    get_or_create_session_store,
                )
                _store = await get_or_create_session_store()
                _replace_kwargs: Dict[str, Any] = {
                    "session_store": _store,
                    "load_timeout_ms": _LOJAS_SESSION_STORE_LOAD_TIMEOUT_MS,
                }
                # SDK 0.1.73+: session_store_flush eh batched/eager. Aplicado
                # via introspection forward-compat.
                _opt_fields = {f.name for f in _dc.fields(options)}
                if "session_store_flush" in _opt_fields:
                    _replace_kwargs["session_store_flush"] = _LOJAS_SESSION_STORE_FLUSH
                options = _dc.replace(options, **_replace_kwargs)
                logger.info(
                    "[AGENTE_LOJAS] SessionStore enabled: session=%s flush=%s",
                    (our_session_id or 'pending')[:12],
                    _replace_kwargs.get('session_store_flush', 'sdk_default'),
                )

                # Probe anti-crash (FIX S1): se vamos resumir (options.resume set),
                # confirmar que a sessao existe no store. Se NAO existir (turno 1
                # nao mirrorou, ou sessao de outro project_key), REMOVER o resume
                # para o CLI iniciar sessao nova em vez de crashar com --resume de
                # JSONL inexistente (exit code 1). Espelha o probe do agente web
                # (app/agente/sdk/client.py:2187-2208).
                if getattr(options, 'resume', None):
                    try:
                        from claude_agent_sdk import project_key_for_directory
                        _pk = (
                            project_key_for_directory(options.cwd)
                            if options.cwd else project_key_for_directory()
                        )
                        _existing = await _store.load({
                            "project_key": _pk,
                            "session_id": options.resume,
                        })
                        if _existing is None:
                            logger.warning(
                                "[AGENTE_LOJAS] probe: sessao %s nao esta no "
                                "store — iniciando nova (sem --resume)",
                                str(options.resume)[:12],
                            )
                            options = _dc.replace(options, resume=None)
                    except Exception as _probe_err:
                        logger.debug(
                            "[AGENTE_LOJAS] probe session_store falhou "
                            "(ignorado): %s", _probe_err,
                        )
            except Exception as _store_err:
                logger.error(
                    "[AGENTE_LOJAS] SessionStore init falhou — fallback "
                    "para JSONL local nativo do SDK: %s", _store_err,
                    exc_info=True,
                )

        logger.info(
            "[AGENTE_LOJAS] stream_response start | user_id=%s loja_id=%s "
            "our_session=%s sdk_session=%s ask_user=%s",
            user_id, loja_hora_id,
            (our_session_id or '')[:8], (sdk_session_id or '')[:8],
            'yes' if event_queue is not None else 'no',
        )

        # Dict acumula tool_use_id -> tool_name ao longo do stream.
        # Necessario para Task* tool parser correlacionar tool_result com tool_name
        # (evita falsos positivos em outros tools com texto similar).
        tool_use_to_name: Dict[str, str] = {}

        try:
            async with ClaudeSDKClient(options=options) as sdk_client:
                await sdk_client.query(user_message)

                async for msg in sdk_client.receive_response():
                    async for event in _parse_message(msg, tool_use_to_name=tool_use_to_name):
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
        except ProcessError as e:
            # CLI crashou (exit code != 0). Drena o stderr capturado p/ a causa raiz.
            exit_code = getattr(e, 'exit_code', None)
            stderr_tail = _drain_stderr(stderr_queue)
            logger.error(
                "[AGENTE_LOJAS] ProcessError exit=%s | msg=%s | stderr=%s",
                exit_code, e, stderr_tail[:1000],
            )
            for _ev in _build_error_recovery_events(
                msg=(f"Erro de processo (codigo {exit_code}). Tente novamente."
                     if exit_code else "Erro de processo. Tente novamente."),
                error_type='process_error', exc=e, extra={'exit_code': exit_code},
            ):
                yield _ev
        except CLINotFoundError as e:
            # CLI do Agent SDK ausente no ambiente (deploy quebrado). Critico.
            logger.critical(
                "[AGENTE_LOJAS] CLI do Agent SDK nao encontrado (deploy?): %s", e,
            )
            for _ev in _build_error_recovery_events(
                msg="Servico do agente indisponivel (CLI ausente). Avise o suporte.",
                error_type='cli_not_found', exc=e,
            ):
                yield _ev
        except CLIConnectionError as e:
            # Process death (SIGTERM) ou falha de resume — sibling de ProcessError.
            logger.warning(
                "[AGENTE_LOJAS] CLIConnectionError (process death/resume): %s", e,
            )
            for _ev in _build_error_recovery_events(
                msg="Conexao com o agente caiu. Tente novamente.",
                error_type='cli_connection_error', exc=e,
            ):
                yield _ev
        except CLIJSONDecodeError as e:
            # Output do CLI malformado (JSON invalido no stream).
            logger.error(
                "[AGENTE_LOJAS] CLIJSONDecodeError (output malformado do CLI): %s", e,
            )
            for _ev in _build_error_recovery_events(
                msg="Resposta malformada do agente. Tente novamente.",
                error_type='cli_json_decode_error', exc=e,
            ):
                yield _ev
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


import re as _re_module  # module-level (evita re-import no hot-path)


def _build_task_event_from_result(
    content: Any,
    expected_tool_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Constroi task_event a partir de tool_result texto formatado.

    SDK 0.2.82+ substituiu TodoWrite por Task* tools. Output do CLI eh texto
    formatado (nao JSON), entao detectamos via regex no conteudo.

    Formatos esperados (do CLI bundled 2.1.142+):
      - TaskCreate:  'Task #N created successfully: <subject>'
      - TaskUpdate:  'Updated task #N status' (e variantes, sempre comeca com 'Updated task #')
      - TaskList:    linhas '#N [status] subject' (uma por task; pode ser vazia para 0 tasks)

    Args:
        content: tool_result content (str ou estrutura conversivel).
        expected_tool_name: se fornecido, restringe parsing ao tool especifico
            (evita falsos positivos quando output de outro tool contem padroes
            de tarefa, ex: Bash logando 'Updated task #5'). Recomendado SEMPRE.

    Returns:
        Dict com {action, task_id?, subject?, tasks?, status?} ou None.

    Nota: este parser NAO tem acesso ao input original do tool_call (handler
    standalone), entao perde 'description' do TaskCreate e detalhes extras do
    TaskUpdate. UI compensa via snapshot do TaskList.
    """
    # Normalizar para string (sem early return — TaskList vazio precisa
    # emitir snapshot vazio para frontend limpar UI, mesmo com content='').
    s = (str(content).strip() if content else '')

    # TaskList: SEMPRE emite snapshot quando expected_tool_name=='TaskList'.
    # Sem expected_tool_name (legacy fallback), so emite snapshot se linhas
    # casam padrao (evita falso positivo de outros tools com formato similar).
    if expected_tool_name == 'TaskList':
        tasks = []
        for ln in s.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            m = _re_module.match(r'#(\d+)\s*\[([\w_]+)\]\s*(.+)', ln)
            if m:
                tasks.append({
                    'task_id': m.group(1),
                    'status': m.group(2),
                    'subject': m.group(3).strip(),
                })
        # Snapshot incondicional quando tool confirmado (CR HIGH #3)
        return {'action': 'snapshot', 'tasks': tasks}

    # Legacy fallback (sem expected_tool_name): so emite snapshot se TODAS
    # as linhas (>=1) casam padrao TaskList. Sem isso, qualquer Bash output
    # multi-linha sem '#N [status]' geraria snapshot vazio incorreto.
    if expected_tool_name is None and s:
        lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
        if lines and all(_re_module.match(r'#\d+\s*\[[\w_]+\]', ln) for ln in lines):
            tasks = []
            for ln in lines:
                m = _re_module.match(r'#(\d+)\s*\[([\w_]+)\]\s*(.+)', ln)
                if m:
                    tasks.append({
                        'task_id': m.group(1),
                        'status': m.group(2),
                        'subject': m.group(3).strip(),
                    })
            if tasks:
                return {'action': 'snapshot', 'tasks': tasks}

    # Sem conteudo e nao-TaskList: nada a parsear
    if not s:
        return None

    # TaskCreate: 'Task #N created successfully: <subject>' (anchored com re.match)
    if expected_tool_name in (None, 'TaskCreate'):
        m_create = _re_module.match(
            r'Task\s+#(\d+)\s+created\s+successfully\s*:\s*(.+)',
            s, _re_module.IGNORECASE
        )
        if m_create:
            return {
                'action': 'created',
                'task_id': m_create.group(1),
                'subject': m_create.group(2).strip(),
                'status': 'pending',
            }

    # TaskUpdate: 'Updated task #N ...' (anchored com re.match — evita falso
    # positivo em qualquer texto que contenha 'Updated task #N' em meio).
    if expected_tool_name in (None, 'TaskUpdate'):
        m_upd = _re_module.match(r'Updated\s+task\s+#(\d+)', s, _re_module.IGNORECASE)
        if m_upd:
            return {
                'action': 'updated',
                'task_id': m_upd.group(1),
            }

    return None


async def _parse_message(
    msg,
    tool_use_to_name: Optional[Dict[str, str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Traduz mensagens do SDK em eventos SSE simples.

    Args:
        msg: SDK message (SystemMessage, AssistantMessage, UserMessage, ResultMessage).
        tool_use_to_name: dict mutavel {tool_use_id: tool_name} mantido pelo
            chamador (stream_response) — populado em AssistantMessage e
            consultado em UserMessage para correlacionar tool_result com tool_name.
            Necessario para filtro de Task* tools no parser (evita falsos positivos
            quando outros tools tem output contendo 'Updated task #N' etc.).
    """
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
                # Registrar tool_use_id -> tool_name para correlacao posterior
                # com tool_result (Task* tools precisam saber qual tool foi).
                if tool_use_to_name is not None and getattr(block, 'id', None):
                    tool_use_to_name[block.id] = block.name
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

                # Task* tools (SDK 0.2.82+): detecta tool_result de TaskCreate,
                # TaskUpdate e TaskList via parser de texto formatado. Emite
                # evento dedicado 'task_event' para renderizacao no UI.
                # Mesmo padrao do agente Nacom Goya (client.py:_build_task_event).
                tool_use_id = getattr(block, 'tool_use_id', '') or ''
                expected_tool = (
                    (tool_use_to_name or {}).get(tool_use_id)
                    if tool_use_to_name is not None else None
                )
                # CR HIGH: so chama parser se tool_name confirmado como Task*
                # (evita falso positivo em Bash output que contem "Updated task #N").
                # Se tool_use_to_name nao foi populado (fallback legacy), chama
                # sem filtro — comportamento degradado mas funcional.
                if expected_tool is None or expected_tool in (
                    'TaskCreate', 'TaskUpdate', 'TaskList',
                ):
                    task_evt = None
                    try:
                        task_evt = _build_task_event_from_result(
                            content, expected_tool_name=expected_tool
                        )
                    except Exception as e:
                        # CR HIGH: NUNCA propagar excecao do parser (R1 services).
                        logger.warning(
                            "[AGENTE_LOJAS] Falha ao parsear task_event (%s): %s",
                            expected_tool or 'unknown', e
                        )
                    if task_evt is not None:
                        yield {
                            'type': 'task_event',
                            'content': '',
                            'metadata': task_evt,
                        }
                        # Nao emite tool_result generico para evitar duplicacao
                        # (UI renderiza so o evento 'task_event').
                        continue

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
        meta: Dict[str, Any] = {
            'stop_reason': getattr(msg, 'stop_reason', None),
            'input_tokens': usage.get('input_tokens', 0) if isinstance(usage, dict) else 0,
            'output_tokens': usage.get('output_tokens', 0) if isinstance(usage, dict) else 0,
            'total_cost_usd': getattr(msg, 'total_cost_usd', 0),
            'num_turns': getattr(msg, 'num_turns', 0),
            # SDK 0.1.76+: HTTP status code de erros API (forward-compat).
            'api_error_status': getattr(msg, 'api_error_status', None),
            # SDK 0.1.65+: structured output JSON parseado quando output_format
            # foi passado em build_options (forward-compat — pode ser None).
            'structured_output': getattr(msg, 'structured_output', None),
        }
        yield {
            'type': 'done',
            'content': '',
            'metadata': meta,
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
    output_format: Optional[Dict[str, Any]] = None,
    stderr_queue: Optional[Any] = None,
):
    """High-level helper usado pelo route chat.py. Yields dicts.

    Args:
        our_session_id: AgentSession.session_id (UUID nosso). Usado para
            registrar event_queue cross-thread em can_use_tool.
        event_queue: Queue thread-safe para eventos `ask_user_question`.
        output_format: JSON Schema opcional (structured output).
        stderr_queue: queue.SimpleQueue opcional para stderr CLI.
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
        output_format=output_format,
        stderr_queue=stderr_queue,
    ):
        yield event
