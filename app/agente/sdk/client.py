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
import re
import time
from functools import lru_cache
from typing import AsyncGenerator, Dict, Any, List, Optional, Callable, TYPE_CHECKING
from app.utils.timezone import agora_utc_naive

if TYPE_CHECKING:  # forward-ref p/ o type hint specialist_profile em _build_options (F1)
    from .specialist_profiles import SpecialistProfile

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
# NOTA: basedpyright reporta `reportAssignmentType` aqui como falso positivo
# (duas declaracoes do mesmo nome em escopo de modulo). Em runtime e seguro:
# SDK 0.1.66 (atual) sempre cai no try; o fallback so existiria em downgrade.
try:
    from claude_agent_sdk import MirrorErrorMessage as _MirrorErrorMessageClass
    MirrorErrorMessage = _MirrorErrorMessageClass # type: ignore
except ImportError:
    # SDK < 0.1.64: sentinel inerte. isinstance() contra classe sem instancias
    # reais sempre retorna False — handler abaixo fica inerte sem quebrar.
    class MirrorErrorMessage:  # type: ignore[no-redef]
        """Sentinel inerte para SDK < 0.1.64 (sem SessionStore). Nao e emitida."""
        pass


# SDK 0.1.77+: option `skills` em ClaudeAgentOptions deprecou "Skill" em
# allowed_tools. Quando set, SDK auto-configura "Skill" em allowed_tools E
# setting_sources, alem de filtrar o listing do model. Detectado uma vez no
# import (zero overhead por request).
def _check_options_skills_field() -> bool:
    """Retorna True se ClaudeAgentOptions tem campo `skills` nativo (SDK 0.1.77+)."""
    try:
        import dataclasses
        fields = {f.name for f in dataclasses.fields(ClaudeAgentOptions)}
        return 'skills' in fields
    except Exception:
        return False


_SDK_HAS_OPTIONS_SKILLS = _check_options_skills_field()


@lru_cache(maxsize=1)
def _discover_skills_from_project() -> list[str]:
    """Descobre skills em .claude/skills/ filtrando as delegadas a subagentes.

    Retorna lista ordenada de skill names (basename de diretórios que têm SKILL.md),
    excluindo SKILLS_DELEGADAS_SUBAGENTE — fonte única de verdade em
    `config/skills_whitelist.py`. Inclui HORA, Assai, Odoo-estoque-WRITE e
    SPED (reservadas ao subagente auditor-sped-ecd). Ver Solucao B em
    `config/skills_whitelist.py`.

    Esta função é o input para `skills=list[str]` em ClaudeAgentOptions
    (SDK 0.1.77+, ver SDK_CHANGELOG.md:160-167). Skills não listadas aqui:
    1. Não aparecem no listing do agente principal (reduz a description da
       meta-tool `Skill` abaixo do budget da CLI — evita truncamento, cli.js sY7).
    2. São rejeitadas se o principal tentar invocá-las via Skill tool — mas
       continuam disponíveis ao subagente que as declara via AgentDefinition.skills
       (agent_loader.py:111 — listing independente do principal).

    Returns:
        Lista ordenada de skill names.
    """
    from pathlib import Path
    from app.agente.config.skills_whitelist import SKILLS_DELEGADAS_SUBAGENTE

    # Path do .claude/skills/ relativo ao root do projeto
    # __file__ = app/agente/sdk/client.py → 4 parents = root
    skills_dir = Path(__file__).resolve().parent.parent.parent.parent / ".claude" / "skills"
    if not skills_dir.is_dir():
        return []

    excluidas = SKILLS_DELEGADAS_SUBAGENTE

    discovered: list[str] = []
    for entry in skills_dir.iterdir():
        if not entry.is_dir():
            continue
        if not (entry / "SKILL.md").is_file():
            continue
        if entry.name in excluidas:
            continue
        discovered.append(entry.name)

    return sorted(discovered)


# SDK 0.1.74+: option `strict_mcp_config` em ClaudeAgentOptions. Quando True,
# CLI usa APENAS mcp_servers passados em options, ignorando project/user/global
# config (.mcp.json). Util para determinismo DEV vs PROD. Detectado uma vez no
# import (zero overhead por request).
def _check_strict_mcp_config_field() -> bool:
    """Retorna True se ClaudeAgentOptions tem campo `strict_mcp_config` nativo (SDK 0.1.74+)."""
    try:
        import dataclasses
        fields = {f.name for f in dataclasses.fields(ClaudeAgentOptions)}
        return 'strict_mcp_config' in fields
    except Exception:
        return False


_SDK_HAS_STRICT_MCP_CONFIG = _check_strict_mcp_config_field()

# Fallback para API direta (health check)
import anthropic # noqa: E402
logger = logging.getLogger('sistema_fretes')


# =====================================================================
# F1 — Cache miss alert (Sentry) — observabilidade silent invalidator
# =====================================================================
# Threshold minimo para alertar: requests pequenos nao cacheam por design.
# Anthropic prompt-caching docs: Opus/Haiku >= 4096; Sonnet/Haiku 3.x >= 2048.
_CACHE_MIN_PREFIX_OPUS = 4096
_CACHE_MIN_PREFIX_SONNET = 2048

# Cooldown in-memory: dict[(user_id, model), float_unix_timestamp].
# Evita spam Sentry — captura no maximo 1 alerta a cada 5min por par.
# H1 fix (2026-05-09): Lock previne race condition em multi-thread.
# Gunicorn gthread (4 workers x 2 threads) sem lock pode emitir N alertas
# simultaneos para a mesma chave — duplo Sentry spam.
import threading as _threading # noqa: E402
_cache_miss_cooldown: Dict[tuple, float] = {}
_cache_miss_cooldown_lock = _threading.Lock()
_CACHE_MISS_COOLDOWN_SEC = 300
_CACHE_MISS_COOLDOWN_MAX_ENTRIES = 100  # M1: cleanup quando exceder


def _alert_cache_miss(
    input_tokens: int,
    cache_read_tokens: int,
    cache_creation_tokens: int,
    model: Optional[str],
    user_id: Optional[int],
    session_id: Optional[str],
) -> None:
    """Captura no Sentry quando request grande nao bate cache (silent invalidator).

    Chamado apos ResultMessage.usage parsed. Best-effort: qualquer falha eh
    swallowed (logger.debug). Cooldown 5min por (user_id, model) evita spam.

    Trigger: input_tokens > MIN_PREFIX AND cache_read=0 AND cache_creation=0.
    cache_creation>0 indica primeiro write da sessao (esperado, nao alerta).
    """
    try:
        from app.agente.config.feature_flags import USE_CACHE_MISS_ALERT
        if not USE_CACHE_MISS_ALERT:
            return

        model_str = (model or "").lower()
        # Threshold por familia (Anthropic prompt-caching docs):
        #   Opus 4.x, Haiku 4.5  -> 4096 tokens
        #   Sonnet 4.x, Haiku 3.x (3 e 3.5) -> 2048 tokens
        # IDs reais: claude-3-haiku-20240307, claude-3-5-haiku-20241022,
        # claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-8.
        # Match explicito por familia — substring "haiku-3" NAO casa "3-5-haiku".
        is_haiku_3x = ("3-haiku" in model_str) or ("3-5-haiku" in model_str)
        is_sonnet_4x = "sonnet-4" in model_str
        if is_sonnet_4x or is_haiku_3x:
            min_prefix = _CACHE_MIN_PREFIX_SONNET
        else:
            # Opus 4.x, Haiku 4.5, ou desconhecido -> threshold mais alto (conservador)
            min_prefix = _CACHE_MIN_PREFIX_OPUS

        # Filtros: requests pequenos nao deveriam cachear; primeira write OK.
        if input_tokens < min_prefix:
            return
        if cache_read_tokens > 0 or cache_creation_tokens > 0:
            return

        # Cooldown — H1: check-then-act sob lock para evitar race em gthread.
        # M1: cleanup oportunistico quando dict cresce acima do threshold.
        key = (user_id, model_str)
        now = time.time()
        with _cache_miss_cooldown_lock:
            # M1: cleanup periodico — remove entries com last < (now - cooldown*2)
            if len(_cache_miss_cooldown) > _CACHE_MISS_COOLDOWN_MAX_ENTRIES:
                cutoff = now - (_CACHE_MISS_COOLDOWN_SEC * 2)
                stale = [k for k, v in _cache_miss_cooldown.items() if v < cutoff]
                for k in stale:
                    del _cache_miss_cooldown[k]

            last = _cache_miss_cooldown.get(key, 0.0)
            if (now - last) < _CACHE_MISS_COOLDOWN_SEC:
                logger.debug(
                    f"[CACHE_MISS] cooldown ativo para {key}, suprimindo alerta "
                    f"(input={input_tokens}, ultimo={int(now-last)}s atras)"
                )
                return
            _cache_miss_cooldown[key] = now

        # Sentry capture FORA do lock — evita serializacao de I/O.
        # M2: usar new_scope (push_scope deprecou em sentry_sdk 2.x).
        try:
            import sentry_sdk
            _client = sentry_sdk.get_client()
            if _client is not None and _client.is_active():
                with sentry_sdk.new_scope() as scope:
                    scope.set_tag("cache_miss", "true")
                    scope.set_tag("model", model_str or "unknown")
                    if user_id is not None:
                        scope.set_tag("user_id", str(user_id))
                    scope.set_extra("input_tokens", input_tokens)
                    scope.set_extra("cache_read_tokens", cache_read_tokens)
                    scope.set_extra("cache_creation_tokens", cache_creation_tokens)
                    scope.set_extra("min_prefix_threshold", min_prefix)
                    if session_id:
                        scope.set_extra("session_id", session_id)
                    sentry_sdk.capture_message(
                        f"Cache miss detectado: {input_tokens} input tokens sem "
                        f"cache hit em {model_str or 'modelo desconhecido'}",
                        level="warning",
                    )
        except ImportError:
            pass

        logger.warning(
            f"[CACHE_MISS] input_tokens={input_tokens} cache_read=0 cache_creation=0 "
            f"model={model_str} user_id={user_id} — possivel silent invalidator"
        )
    except Exception as e:
        logger.debug(f"[CACHE_MISS] alert falhou (ignorado): {e}")



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


def _emit_subagent_summary(session_id, summary_dict: dict) -> None: # type: ignore
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

    async def get_context_usage_async(self, session_id: Optional[str] = None, role: str = 'principal') -> Optional[Dict[str, Any]]:
        """
        Uso do context window via SDK get_context_usage() (control request ASYNC).

        Sessao A: indicador de contexto consumido na UI. Disponivel desde SDK 0.1.52,
        mas o metodo do ClaudeSDKClient e ASYNC desde 0.2.x — DEVE ser awaited. A
        versao sync anterior chamava SEM await (comentario obsoleto "sincrono no SDK")
        e retornava SEMPRE None (bug 2026-06-19: coroutine sem .get() -> AttributeError
        -> except). Chamar APOS o turno (CLI idle), de dentro do _sdk_loop (contexto
        async) -> await direto, sem deadlock. Best-effort: None se indisponivel.

        Args:
            session_id: nosso UUID de sessao (pool key). Se None, usa o ContextVar.
            role: papel do cliente no pool (8b). Em turno de especialista
                  ('gestor-recebimento') o client vivo esta sob '{session}::{role}';
                  default 'principal'. Sem ele, mediria o cliente do papel errado.

        Returns:
            {"used": int, "total": int, "percent": float, "categories": [...]} ou None
        """
        try:
            from .client_pool import get_pooled_client
            from ..config.permissions import get_session_id

            pool_key = session_id or get_session_id() or ''
            pooled = get_pooled_client(pool_key, role=role)
            if not pooled or not pooled.connected:
                return None

            sdk_client = pooled.client
            if not hasattr(sdk_client, 'get_context_usage'):
                return None

            raw = await sdk_client.get_context_usage()  # ASYNC no SDK 0.2.x
            if not raw:
                return None

            # ContextUsageResponse (SDK 0.2.x): totalTokens/maxTokens/percentage
            # (fallback used/total p/ retrocompat caso o shape mude).
            used = raw.get('totalTokens') or raw.get('used') or 0
            total = raw.get('maxTokens') or raw.get('total') or 200000
            if not total:
                return None
            percent = raw.get('percentage')
            if percent is None:
                percent = used / total * 100

            # Breakdown por categoria (o que domina a janela) — antes descartado.
            categories = [
                {'name': c.get('name'), 'tokens': c.get('tokens')}
                for c in (raw.get('categories') or [])
                if c.get('tokens')
            ]

            return {
                'used': used,
                'total': total,
                'percent': round(float(percent), 1),
                'categories': categories,
            }

        except Exception as e:
            logger.debug(f"[AGENT_CLIENT] get_context_usage_async falhou (ignorado): {e}")
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

        elif tool_name == 'TaskCreate':
            # SDK 0.2.82+: TodoWrite foi substituido por TaskCreate/TaskUpdate/TaskGet/TaskList
            subject = tool_input.get('subject') or tool_input.get('content') or ''
            if subject:
                return f"Criando tarefa: {subject[:60]}"
            return "Criando tarefa"

        elif tool_name == 'TaskUpdate':
            task_id = tool_input.get('taskId') or tool_input.get('task_id') or ''
            status = tool_input.get('status', '')
            if status and task_id:
                return f"Atualizando tarefa #{task_id} → {status}"
            if task_id:
                return f"Atualizando tarefa #{task_id}"
            return "Atualizando tarefa"

        elif tool_name == 'TaskGet':
            task_id = tool_input.get('taskId') or tool_input.get('task_id') or ''
            if task_id:
                return f"Consultando tarefa #{task_id}"
            return "Consultando tarefa"

        elif tool_name == 'TaskList':
            return "Listando tarefas"

        # Default: usa o nome da ferramenta
        return tool_name

    # ─────────────────────────────────────────────────────────────────
    # Task* tools parser (SDK 0.2.82+: substituiu TodoWrite)
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _extract_task_id_from_text(text: str) -> Optional[str]:
        """Extrai task_id (#N) de output como 'Task #3 created successfully: ...'."""
        match = re.search(r'#(\d+)', text or '')
        return match.group(1) if match else None

    @staticmethod
    def _parse_task_list_output(text: str) -> list:
        """Parseia output multi-linha do TaskList em lista de dicts.

        Formato esperado por linha (do CLI bundled 2.1.142+):
            '#N [status] subject'  ex: '#1 [pending] Estudar fundamentos'
        Retorna lista vazia se nao houver linhas reconheciveis.
        """
        tasks = []
        for line in (text or '').splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r'#(\d+)\s*\[([\w_]+)\]\s*(.+)', line)
            if m:
                tasks.append({
                    'task_id': m.group(1),
                    'status': m.group(2),
                    'subject': m.group(3).strip(),
                })
        return tasks

    def _build_task_event(
        self,
        tool_name: str,
        original_input: dict,
        result_content: str,
    ) -> Optional[Dict[str, Any]]:
        """Constroi payload do evento task_event para frontend.

        Returns None se evento nao deve ser emitido (ex: TaskGet — read-only).
        """
        if tool_name == 'TaskCreate':
            task_id = self._extract_task_id_from_text(result_content)
            if task_id is None:
                return None
            return {
                'action': 'created',
                'task_id': task_id,
                'subject': original_input.get('subject') or original_input.get('content') or '',
                'description': original_input.get('description', ''),
                'status': 'pending',  # CLI cria como pending
            }
        if tool_name == 'TaskUpdate':
            task_id = str(
                original_input.get('taskId')
                or original_input.get('task_id')
                or ''
            )
            if not task_id:
                return None
            evt: Dict[str, Any] = {
                'action': 'updated',
                'task_id': task_id,
            }
            for k in ('status', 'subject', 'description', 'activeForm'):
                if k in original_input:
                    evt[k] = original_input[k]
            return evt
        if tool_name == 'TaskList':
            tasks = self._parse_task_list_output(result_content)
            return {
                'action': 'snapshot',
                'tasks': tasks,
            }
        return None

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

        # ─── Task messages (subagentes) ───
        # IMPORTANTE: TaskStartedMessage/Progress/Notification HERDAM de SystemMessage
        # (claude_agent_sdk.types). Devem ser checados ANTES do branch generico
        # SystemMessage abaixo, ou seriam capturados por ele e o early return
        # impede emissao de eventos task_*.
        # Bug latente fixado em 2026-05-14 (P0.3 + P1.1 implementation).
        if isinstance(message, TaskStartedMessage):
            task_desc = getattr(message, 'description', '') or ''
            task_id = getattr(message, 'task_id', '') or ''
            task_type = getattr(message, 'task_type', '') or ''
            parent_tu_id = getattr(message, 'tool_use_id', None)  # P1.1
            logger.info(
                f"[AGENT_SDK] TaskStarted: {task_desc[:80]} | "
                f"task_id={task_id[:12]} | task_type={task_type} | "
                f"parent_tool_use_id={(parent_tu_id or '')[:12]}"
            )
            events.append(StreamEvent(
                type='task_started',
                content=task_desc,
                metadata={
                    'task_id': task_id,
                    'task_type': task_type,
                    'parent_tool_use_id': parent_tu_id,  # P1.1
                }
            ))
            return events

        if isinstance(message, TaskProgressMessage):
            task_desc = getattr(message, 'description', '') or ''
            task_id = getattr(message, 'task_id', '') or ''
            last_tool = getattr(message, 'last_tool_name', '') or ''
            usage = getattr(message, 'usage', None)  # P0.3 (TaskUsage TypedDict)
            parent_tu_id = getattr(message, 'parent_tool_use_id', None)  # P1.1
            logger.debug(
                f"[AGENT_SDK] TaskProgress: {task_desc[:80]} | "
                f"task_id={task_id[:12]} | last_tool={last_tool} | "
                f"tokens={getattr(usage, 'total_tokens', None) if usage else None}"
            )
            events.append(StreamEvent(
                type='task_progress',
                content=task_desc,
                metadata={
                    'task_id': task_id,
                    'last_tool_name': last_tool,
                    'usage': usage,  # P0.3 — TaskUsage ou None
                    'parent_tool_use_id': parent_tu_id,  # P1.1
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

        # ─── SystemMessage (init do SDK) ───
        # Generic SystemMessage check — DEVE vir DEPOIS dos subclass checks acima.
        if isinstance(message, SystemMessage):
            sdk_sid = message.data.get('session_id') if hasattr(message, 'data') else None
            if sdk_sid:
                state.result_session_id = sdk_sid
                state.got_result_message = True
                logger.info(f"[AGENT_SDK] SDK session_id from init: {sdk_sid[:12]}...")
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

                        # Task* tools emit (SDK 0.2.82+: substituiu TodoWrite — ver SDK_CHANGELOG.md)
                        # Emit no tool_result (UserMessage handler) — task_id e dados completos
                        # vem do output texto formatado.
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
                        raw_result_content = block.content  # preservado p/ parser Task* (sem truncamento)
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

                        # Task* tools emit (SDK 0.2.82+: substituiu TodoWrite)
                        # Usa raw_result_content (texto bruto, sem truncamento) p/ parsear
                        # output formatado do CLI ('Task #N created...', '#N [status] subject').
                        if tool_name in ('TaskCreate', 'TaskUpdate', 'TaskList') and not is_error:
                            try:
                                tool_call_orig = next(
                                    (tc for tc in state.tool_calls if tc.id == tool_use_id),
                                    None
                                )
                                original_input = (
                                    tool_call_orig.input
                                    if tool_call_orig and isinstance(tool_call_orig.input, dict)
                                    else {}
                                )
                                # Normalizar raw para string (lista de blocks ou string direta)
                                if isinstance(raw_result_content, list):
                                    parts = []
                                    for b in raw_result_content:
                                        text = getattr(b, 'text', None)
                                        if text:
                                            parts.append(text)
                                    # Lista sem blocks parseaveis = fallback string vazia
                                    # (str([<object>]) produz texto imparseavel — code-review HIGH).
                                    raw_str = '\n'.join(parts) if parts else ''
                                elif raw_result_content is None:
                                    raw_str = ''
                                else:
                                    raw_str = str(raw_result_content)
                                task_evt = self._build_task_event(tool_name, original_input, raw_str)
                                if task_evt is not None:
                                    events.append(StreamEvent(
                                        type='task_event',
                                        content=task_evt,
                                        metadata={'tool_use_id': tool_use_id}
                                    ))
                            except Exception as e:
                                logger.warning(f"[AGENT_SDK] Falha ao emitir task_event ({tool_name}): {e}")
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

            # SDK 0.1.76+: api_error_status — codigo HTTP (429/500/529) quando is_error=True
            # Permite classificar falhas API granularmente vs apenas inspecao de string em errors[].
            # None se SDK < 0.1.76, sem erro, ou erro nao-API (tool crash, validation, etc.).
            # Compoe com APIStatusError.type ja adotado em scanner/memory_consolidator (anthropic 0.87.0+).
            api_error_status = getattr(message, 'api_error_status', None)

            # Anthropic SDK 0.88.0+ (streaming fix em 0.98.0):
            # stop_details estruturado quando stop_reason == "refusal" — contem
            # category ("cyber"|"bio"|None) + explanation. Propaga ate UI/admin
            # observability para distinguir refusals de safety reais vs falsos
            # positivos. Modulo legado (pre-0.88.0): atributo nao existe → None.
            stop_details_raw = getattr(message, 'stop_details', None)
            stop_details: Optional[Dict[str, Any]] = None
            if stop_details_raw is not None:
                try:
                    if hasattr(stop_details_raw, 'model_dump'):
                        stop_details = stop_details_raw.model_dump()
                    elif isinstance(stop_details_raw, dict):
                        stop_details = stop_details_raw
                    else:
                        stop_details = {
                            'category': getattr(stop_details_raw, 'category', None),
                            'explanation': getattr(stop_details_raw, 'explanation', None),
                        }
                    logger.info(
                        f"[AGENT_SDK] stop_details capturado: "
                        f"stop_reason={stop_reason} category={stop_details.get('category')} "
                        f"explanation={(stop_details.get('explanation') or '')[:200]}"
                    )
                except Exception as _sd_err:
                    logger.debug(f"[AGENT_SDK] stop_details parse falhou (best-effort): {_sd_err}")
                    stop_details = None

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

                # F1 — alerta cache miss (silent invalidator detection)
                # Best-effort: model via settings, user_id via ContextVar tool (memory_mcp).
                try:
                    _user_id = None
                    try:
                        from ..tools.memory_mcp_tool import (
                            get_current_user_id as _get_uid,
                        )
                        _user_id = _get_uid()
                    except Exception:
                        pass  # ContextVar nao setado em path admin/health
                    _alert_cache_miss(
                        input_tokens=state.input_tokens,
                        cache_read_tokens=state.cache_read_tokens,
                        cache_creation_tokens=state.cache_creation_tokens,
                        model=str(self.settings.model) if self.settings else None,
                        user_id=_user_id,
                        session_id=state.result_session_id,
                    )
                except Exception as _cm_err:
                    logger.debug(f"[CACHE_MISS] dispatch falhou (ignorado): {_cm_err}")

            logger.info(
                f"[AGENT_SDK] ResultMessage | "
                f"stop_reason={stop_reason} | "
                f"cost={message.total_cost_usd} | "
                f"usage={message.usage} | turns={message.num_turns} | "
                f"duration={message.duration_ms}ms | "
                f"tokens_captured=({state.input_tokens},{state.output_tokens})"
                f"{f' | http_status={api_error_status}' if api_error_status else ''}"
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
                        # Anthropic SDK 0.88.0+: stop_details estruturado para refusals
                        # ({"category": "cyber"|"bio"|None, "explanation": str|None}).
                        # None se Anthropic SDK < 0.88.0 ou stop_reason nao for refusal.
                        'stop_details': stop_details,
                        # SDK 0.1.76+: codigo HTTP (429/500/529) quando is_error=True.
                        # None se SDK < 0.1.76, sem erro, ou erro nao-API.
                        'api_error_status': api_error_status,
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
        resume_fallback_reason: Optional[str] = None,
        thinking_display: Optional[str] = None,
        agent_role: str = 'principal',
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

        # Fase B teams-melhorias: registra o FALANTE deste turno. Os hooks do
        # client pooled (criados em turno anterior, possivelmente de OUTRO
        # falante em grupos do Teams) resolvem via registry em vez da closure.
        from .turn_context_registry import set_turn_user
        set_turn_user(our_session_id, user_id, user_name)

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
            resume_fallback_reason=resume_fallback_reason,
            thinking_display=thinking_display,
            agent_role=agent_role,
        ):
            yield event

    def _build_options(
        self,
        user_name: str = "Usuário",
        can_use_tool: Optional[Callable] = None,
        max_turns: Optional[int] = None,
        model: Optional[str] = None,
        effort_level: str = "off",
        plan_mode: bool = False,
        user_id: int = None,
        output_format: Optional[Dict[str, Any]] = None,
        our_session_id: Optional[str] = None,
        stderr_queue: Optional['queue.SimpleQueue'] = None,
        resume_state: Optional[Dict] = None,
        thinking_display: Optional[str] = None,
        specialist_profile: Optional['SpecialistProfile'] = None,
    ) -> 'ClaudeAgentOptions':
        """
        Constrói ClaudeAgentOptions para ClaudeSDKClient.

        Configura: model, system_prompt, cwd, allowed_tools (de settings),
        hooks, betas, permission_mode, disallowed_tools, fallback_model.

        Args:
            user_name: Nome do usuário
            can_use_tool: Callback de permissão
            max_turns: Máximo de turnos. None (default) = sem limite — necessário
                para sessões longas com muitos tool_use encadeados. Definir um valor
                explícito (ex: 50) apenas se quiser cap defensivo.
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

        # F1: se for cliente ESPECIALISTA, troca prompt + skills (allow-list propria).
        # specialist_profile (SpecialistProfile) tem system_prompt_path proprio e uma
        # allow-list de skills. Falha de leitura -> fallback transparente ao principal
        # (profile=None), garantindo que o path do principal nunca quebra.
        _spec_skills = None
        _spec_system_prompt = None
        if specialist_profile is not None:
            try:
                with open(specialist_profile.system_prompt_path, 'r', encoding='utf-8') as _f:
                    _spec_prompt = _f.read()
                _spec_system_prompt = self._build_full_system_prompt(_spec_prompt)
                _spec_skills = sorted(specialist_profile.skills)
            except Exception as _sp_err:
                # Alarme explicito (nao silencioso): perfil pedido mas prompt ausente/
                # ilegivel -> o turno cai no PRINCIPAL. Logar role + path para acao.
                logger.warning(
                    f"[specialist] ALARME: perfil '{specialist_profile.role}' nao "
                    f"carregou (path={specialist_profile.system_prompt_path}) -> "
                    f"FALLBACK principal: {_sp_err}"
                )
                specialist_profile = None

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

            # Máximo de turnos — omitido por padrão (sem limite).
            # Bug observado 2026-05-11: max_turns=30 cortava respostas longas
            # com erro `Reached maximum number of turns (30)` (stop_reason=tool_use),
            # frontend ficava preso até READ_TIMEOUT_MS=60s no chat.js.
            # Pattern idêntico a agent_loader.py:434 (subagentes).
            # max_turns injetado abaixo via guard se != None.

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

            # Tools permitidas — lê de settings.py (fonte única de verdade).
            # 'Skill' NÃO está em tools_enabled (deprecation SDK 0.1.77+) —
            # fallback para SDK < 0.1.77 e injetado abaixo via guard.
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

        # max_turns: injetar apenas se explicitamente definido (default None = sem limite).
        # Padrão idêntico a agent_loader.py:434 para subagentes.
        if max_turns is not None:
            options_dict["max_turns"] = max_turns

        # SDK 0.1.77+: option `skills` substitui "Skill" em allowed_tools.
        # `"all"` mantem comportamento atual (todas as skills descobertas
        # via setting_sources=["project"] disponiveis ao model). SDK
        # auto-configura "Skill" em allowed_tools quando este campo esta set.
        # Doc: "context filter, not sandbox" — arquivos das skills continuam
        # acessiveis via Read/Bash; o filtro complementa can_use_tool.
        # Fallback (SDK < 0.1.77): 'Skill' adicionado em allowed_tools manualmente.
        if _SDK_HAS_OPTIONS_SKILLS:
            # Especialista: allow-list propria (como agente_lojas); principal: deny-list.
            options_dict["skills"] = (
                _spec_skills if _spec_skills is not None else _discover_skills_from_project()
            )
            logger.debug(
                f"[AGENT_CLIENT] skills filtradas: {len(options_dict['skills'])} skills "
                f"({'especialista allow-list' if _spec_skills is not None else 'skills delegadas a subagentes excluídas'})"
            )
        else:
            options_dict["allowed_tools"].append("Skill")
            logger.debug(
                "[AGENT_CLIENT] SDK < 0.1.77 detectado — 'Skill' injetado em "
                "allowed_tools (fallback). Atualize requirements.txt para 0.1.77+."
            )

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
        # System Prompt: custom string vs preset claude_code
        # Flag: USE_CUSTOM_SYSTEM_PROMPT (default TRUE — ver feature_flags.py;
        #   rollback: AGENT_CUSTOM_SYSTEM_PROMPT=false → preset claude_code + append).
        # T4.3 (2026-06-06, plano governanca FASE 4): custom MANTIDO. Smoke
        #   empirico (Haiku, dir isolado) provou que migrar ao preset:
        #   (1) imporia identidade "Claude Code" (header yoK, binario CLI fn K98)
        #       ANTES do nosso append → conflito com "Agente Logistico";
        #   (2) somaria ~5.9K tok de coding-guidance irrelevante (+13% tok/request);
        #   (3) exclude_dynamic_sections poda so' ~164 tok (nao salva o caso).
        #   O header neutro "hoK" (You are a Claude agent) so' existe SEM append
        #   → incompativel com injetar system_prompt.md. Ver "Nota FASE 4" no plano.
        # =================================================================
        from ..config.feature_flags import USE_CUSTOM_SYSTEM_PROMPT

        if _spec_system_prompt is not None:
            # F1 especialista: prompt proprio (ja' montado via _build_full_system_prompt
            # a partir do system_prompt_path do perfil). Substitui o do principal.
            options_dict["system_prompt"] = _spec_system_prompt
            logger.info(
                f"[AGENT_CLIENT] System prompt: ESPECIALISTA ({specialist_profile.role})"
            )
        elif USE_CUSTOM_SYSTEM_PROMPT:
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
            USE_STRICT_MCP_CONFIG,
        )

        # Budget Control nativo
        if USE_BUDGET_CONTROL:
            options_dict["max_budget_usd"] = MAX_BUDGET_USD
            logger.info(f"[AGENT_CLIENT] Budget control nativo: max ${MAX_BUDGET_USD}/request")

        # Strict MCP Config (SDK 0.1.74+)
        # Quando True, CLI usa APENAS mcp_servers passados em options — ignora
        # .mcp.json project/user/global. Garante determinismo DEV vs PROD.
        # Forward-compat: SDK < 0.1.74 nao tem o campo, flag e ignorada.
        if USE_STRICT_MCP_CONFIG and _SDK_HAS_STRICT_MCP_CONFIG:
            options_dict["strict_mcp_config"] = True
            logger.info(
                "[AGENT_CLIENT] strict_mcp_config=True — apenas MCP servers em "
                "options sao usados (project/user/.mcp.json ignorados)"
            )
        elif USE_STRICT_MCP_CONFIG and not _SDK_HAS_STRICT_MCP_CONFIG:
            logger.warning(
                "[AGENT_CLIENT] AGENT_STRICT_MCP_CONFIG=true mas SDK < 0.1.74 — "
                "campo strict_mcp_config nao disponivel, flag ignorada. "
                "Atualize claude-agent-sdk para 0.1.74+."
            )

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
                # Fase B teams-melhorias: hooks resolvem o FALANTE do turno via
                # turn_context_registry (client do pool reusado nao reaplica
                # hooks — closure congelava user_name/user_id no 1o falante).
                our_session_id=our_session_id,
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

        # Buscar Tabelas (S1 — descoberta de tabela por intencao; filtra por user_id)
        try:
            from ..tools.buscar_tabelas_tool import (
                buscar_tabelas_server,
                set_current_user_id as set_buscar_tabelas_user_id,
            )
            if _register_mcp("buscar_tabelas", buscar_tabelas_server, set_buscar_tabelas_user_id):
                logger.info("[AGENT_CLIENT] MCP 'buscar_tabelas' registrada (S1 progressive disclosure)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP buscar_tabelas não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP buscar_tabelas: {e}")

        # Sessions (busca em sessões anteriores + transcript cru — 6 operações)
        try:
            from ..tools.session_search_tool import sessions_server
            from ..tools.session_search_tool import set_current_user_id as set_session_search_user_id
            if _register_mcp("sessions", sessions_server, set_session_search_user_id):
                logger.info("[AGENT_CLIENT] MCP 'sessions' registrada (6 operações)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP sessions não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP sessions: {e}")

        # Resolver (resolução de entidades — 1 operação)
        try:
            from ..tools.resolver_mcp_tool import resolver_server
            if _register_mcp("resolver", resolver_server):
                logger.info("[AGENT_CLIENT] MCP 'resolver' registrada (1 operação)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP resolver não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP resolver: {e}")

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
        # F7: registro lazy via flag USE_BROWSER_TOOL (default false). Quando off,
        # playwright_mcp_tool (~1720 LOC) NAO eh importado — reduz cold start + RAM.
        # Subagentes que precisam de browser (gestor-ssw via skill operando-ssw)
        # usam Bash + scripts Python proprios, nao mcp__browser__*.
        from ..config.feature_flags import USE_BROWSER_TOOL
        if USE_BROWSER_TOOL:
            try:
                from ..tools.playwright_mcp_tool import browser_server
                if _register_mcp("browser", browser_server):
                    logger.info("[AGENT_CLIENT] MCP 'browser' registrada (12 operações)")
            except ImportError:
                logger.debug("[AGENT_CLIENT] MCP browser não disponível")
            except Exception as e:
                logger.warning(f"[AGENT_CLIENT] Erro MCP browser: {e}")
        else:
            logger.debug(
                "[AGENT_CLIENT] MCP 'browser' SKIP (AGENT_BROWSER_ENABLED=false). "
                "Ative para registrar playwright_mcp_tool no startup."
            )

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

        # Artifact (bundle.html via skill gerando-artifact — 2026-05-12)
        try:
            from ..tools.artifact_tool import artifact_server
            if _register_mcp("artifact", artifact_server):
                logger.info("[AGENT_CLIENT] MCP 'artifact' registrada (1 operação)")
        except ImportError:
            logger.debug("[AGENT_CLIENT] MCP artifact não disponível")
        except Exception as e:
            logger.warning(f"[AGENT_CLIENT] Erro MCP artifact: {e}")

        # Ontologia canônica (D4 Onda 3 — flag USE_AGENT_ONTOLOGY, default OFF)
        # Quando flag OFF: ontology_server=None → _register_mcp retorna False → sem-op.
        # Quando flag ON:  expõe mcp__ontology__query_ontology ao agente.
        from ..config.feature_flags import USE_AGENT_ONTOLOGY
        if USE_AGENT_ONTOLOGY:
            try:
                from ..tools.ontology_query_tool import ontology_server, set_current_user_id as set_ontology_user_id
                if _register_mcp("ontology", ontology_server, set_ontology_user_id):
                    logger.info("[AGENT_CLIENT] MCP 'ontology' registrada (1 operação: query_ontology)")
            except ImportError:
                logger.debug("[AGENT_CLIENT] MCP ontology não disponível")
            except Exception as e:
                logger.warning(f"[AGENT_CLIENT] Erro MCP ontology: {e}")
        else:
            logger.debug(
                "[AGENT_CLIENT] MCP 'ontology' SKIP (AGENT_ONTOLOGY=false). "
                "Ative AGENT_ONTOLOGY=true para expor query_ontology ao agente."
            )

        # Handoff de sessao — registro gated por should_register_handoff:
        # PRINCIPAL + modo 'on' expoe transferir_para; o ESPECIALISTA (em 'on')
        # expoe SO' devolver_ao_principal (NAO re-delega -> anti multi-spawn).
        # shadow/off NAO registram nada (medicao PURA / behavior-equivalente ao
        # main) — expor transferir_para em shadow poluiria as metricas que o
        # shadow existe para medir limpo (review 2026-06-29).
        try:
            from ..config.feature_flags import resolve_specialist_handoff_mode
            from ..tools.handoff_mcp_tool import should_register_handoff
            _hmode = resolve_specialist_handoff_mode()
            if should_register_handoff(_hmode, specialist_profile):
                from ..tools.handoff_mcp_tool import handoff_server
                _register_mcp('handoff', handoff_server)
            elif _hmode == 'on' and specialist_profile is not None:
                from ..tools.handoff_mcp_tool import handoff_devolver_server
                _register_mcp('handoff', handoff_devolver_server)
        except Exception as _h_err:
            logger.debug(f"[handoff] registro da tool pulado: {_h_err}")

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
        resume_fallback_reason: Optional[str] = None,
        thinking_display: Optional[str] = None,
        agent_role: str = 'principal',
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
        # reason='rotated' (sessao rotacionada por idle): injecao FORCADA no
        # 1o turno — nao ha resume a falhar, a sessao e nova e o contexto da
        # origem vem neste fallback (caso conversa-nacom 2026-06-10).
        _forced = bool(
            resume_fallback_reason == 'rotated' and resume_messages_fallback
        )
        resume_state = {
            'failed': _forced,
            'fallback': resume_messages_fallback,
            'reason': resume_fallback_reason or 'resume_failed',
        }

        # ─── Construir options ───
        # 8b: cliente ESPECIALISTA usa system_prompt + skills proprios (handoff de
        # sessao). Resolve o perfil pelo PAPEL do turno; 'principal' -> None (path
        # atual, byte-equivalente). Papel sem perfil registrado -> None + WARNING
        # (fallback principal, nunca quebra). O proprio _build_options ainda faz
        # fallback transparente se o system_prompt_path do perfil faltar.
        _specialist_profile = None
        if agent_role and agent_role != 'principal':
            try:
                from .specialist_profiles import SPECIALIST_PROFILES
                _specialist_profile = SPECIALIST_PROFILES.get(agent_role)
                if _specialist_profile is None:
                    logger.warning(
                        f"[specialist] papel '{agent_role}' sem perfil em "
                        f"SPECIALIST_PROFILES -> fallback principal"
                    )
            except Exception as _sp_err:
                logger.warning(f"[specialist] resolucao de perfil falhou: {_sp_err}")
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
            specialist_profile=_specialist_profile,
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
            AGENT_SDK_SESSION_STORE_FLUSH,
            AGENT_SDK_SESSION_STORE_LOAD_TIMEOUT_MS,
        )
        if AGENT_SDK_SESSION_STORE_ENABLED:
            try:
                from dataclasses import replace as _dc_replace

                from claude_agent_sdk import project_key_for_directory

                from .session_store_adapter import get_or_create_session_store
                _store = await get_or_create_session_store()
                # claude-agent-sdk 0.1.73+: session_store_flush controla quando o
                # TranscriptMirrorBatcher entrega frames ao store.append().
                # batched (default) = end-of-turn, eager = near-real-time.
                # Flag aplicada via dataclasses.replace para nao quebrar SDK < 0.1.73
                # (campo so existe a partir de 0.1.73; se SDK antigo, replace falha
                # silenciosamente e cai no fallback abaixo sem flush).
                _replace_kwargs: Dict[str, Any] = {
                    "session_store": _store,
                    "load_timeout_ms": AGENT_SDK_SESSION_STORE_LOAD_TIMEOUT_MS,
                }
                try:
                    import dataclasses as _dc
                    _opt_fields = {f.name for f in _dc.fields(options)}
                    if "session_store_flush" in _opt_fields:
                        _replace_kwargs["session_store_flush"] = AGENT_SDK_SESSION_STORE_FLUSH
                except Exception:
                    pass  # introspection falhou — usar flush default do SDK
                options = _dc_replace(options, **_replace_kwargs)
                logger.info(
                    f"[SESSION_STORE] ENABLED: {(our_session_id or 'pending')[:12]}... "
                    f"load_timeout={AGENT_SDK_SESSION_STORE_LOAD_TIMEOUT_MS}ms "
                    f"flush={_replace_kwargs.get('session_store_flush', 'sdk_default')}"
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
        # 8b: cada papel (principal/especialista) tem seu PROPRIO client no pool
        # sob a chave '{session_id}::{role}'. resume_id ja' vem do slot do papel
        # (sdk_session_id role-aware, passo 3); no 1o turno do especialista e' None
        # -> sessao SDK nova, sem --resume.
        existing = get_pooled_client(pool_key, role=agent_role)
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
        # FIX BUG #2 (2026-05-12 R-CLI-CRASH): Respeitar resume_state['failed']
        # setado pelo probe ao session_store em 1911-1917. Antes, o codigo
        # IGNORAVA a flag e tentava --resume mesmo com sessao confirmadamente
        # ausente do store, causando CLI exit code 1 + CLIConnectionError
        # "Failed to write to process stdin" em cascata. Causa raiz observada
        # em logs: probe diz "session nao esta no store" -> resume_state.failed=True
        # -> codigo IGNORA e faz _with_resume -> CLI tenta abrir JSONL inexistente
        # -> crash em 0.5-0.9s -> resposta vazia + 2 retries automaticos falham
        # identicamente porque resume_id continua o mesmo.
        # Solucao: se probe ja confirmou falha, pular --resume e usar fallback
        # XML via hook UserPromptSubmit (que injeta transcript do DB no contexto).
        probe_failed = bool(resume_state and resume_state.get('failed'))
        if not existing and resume_id and not probe_failed:
            options = self._with_resume(options, resume_id)
            logger.info(f"[AGENT_SDK_PERSISTENT] Resuming session: {resume_id[:12]}...")
        elif probe_failed and resume_id:
            logger.warning(
                f"[AGENT_SDK_PERSISTENT] Skip --resume (probe confirmou store miss): "
                f"session={resume_id[:12]}... — usando fallback XML via hook"
            )

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
                    role=agent_role,
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
                        role=agent_role,
                    )
                else:
                    raise  # Re-raise se não é falha de resume

            # ─── Propagar sdk_session_id para o PooledClient (F5: cleanup JSONL) ───
            if resume_id and not pooled.sdk_session_id:
                pooled.sdk_session_id = resume_id

            # current_model: o caller (chat.py web / Teams) ja aplicou a politica
            # de "modelo 1x por sessao" (pick_warm_model: a config persiste, routing
            # so na 1a msg). Aqui so materializamos o valor; a troca REAL e decidida
            # logo abaixo por should_switch_model (bug 2026-06-15).
            current_model = model or self.settings.model
            permission_mode = "plan" if plan_mode else "acceptEdits"

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

            # ─── Enfileiramento estilo terminal (2026-05-25) ───
            # Se lock ocupado por turno anterior, sinaliza ao frontend ANTES
            # de esperar — UX similar ao Claude Code CLI que aceita input
            # enquanto processa. Race entre check e await e aceitavel: pior
            # caso 'queued' nao aparece e a request espera no lock mesmo assim.
            if pooled.lock.locked():
                logger.info(
                    f"[AGENT_SDK_PERSISTENT] queue | session={pool_key[:8]}... "
                    "(turno anterior em andamento, aguardando lock)"
                )
                yield StreamEvent(
                    type='queued',
                    content='Mensagem em fila — aguardando turno anterior...',
                    metadata={'session_id': pool_key},
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
            # asyncio.Lock serializa chamadas no mesmo client (DC-1, R08).
            # FIFO desde Python 3.10 — ordem de chegada preservada.
            async with pooled.lock:
                pooled.last_used = time.time()

                # set_model/set_permission_mode DENTRO do lock (2026-05-25): antes
                # ficavam fora, causando race quando msg B chegava durante stream de A.
                if existing and existing.connected:
                    # set_model CONDICIONAL (bug 2026-06-15): so troca quando o modelo
                    # difere do atual da sessao. O caller nunca rebaixa em sessao
                    # quente (pick_warm_model), entao so a troca EXPLICITA do usuario
                    # (mudou o seletor no web) chega aqui — e custa cache MODEL-SCOPED
                    # conscientemente. Sem o guard, o churn era automatico e o modelo
                    # rebaixado confundia o "Set model to X" do CLI com a tarefa.
                    from .model_router import should_switch_model
                    _session_model = getattr(existing, 'model', None)
                    if should_switch_model(current_model, _session_model):
                        try:
                            await pooled.client.set_model(current_model)
                            existing.model = current_model
                            logger.info(
                                f"[AGENT_SDK_PERSISTENT] modelo trocado "
                                f"{_session_model} -> {current_model} (explicito)"
                            )
                        except Exception as model_err:
                            logger.warning(
                                f"[AGENT_SDK_PERSISTENT] set_model ignorado: {model_err}"
                            )
                    try:
                        await pooled.client.set_permission_mode(permission_mode)
                    except Exception as perm_err:
                        logger.warning(
                            f"[AGENT_SDK_PERSISTENT] set_permission_mode ignorado: {perm_err}"
                        )

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
                    # Renova last_used a cada mensagem: turnos longos (subagente
                    # 15-30 min) não podem parecer "idle" para o cleanup do pool
                    # (bug 2026-06-11 — client morto no meio do turno).
                    pooled.last_used = time.time()
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
                    break # noqa: E701

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
            #
            # Fix Sentry PYTHON-FLASK-CK: aguardar 100ms antes de drenar para
            # dar chance do callback emitir as ultimas linhas (race condition
            # entre subprocess crash e flush do stderr).
            time.sleep(0.1)
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
                # Fix Sentry PYTHON-FLASK-CK: sem stderr real capturado, nao
                # ha info actionable. Loga como WARNING para reduzir ruido em
                # producao (issue era REGRESSED). Quem precisa investigar
                # ProcessError repetido inspeciona o subprocess no Render logs.
                stderr = getattr(e, 'stderr', '') or ''
                logger.warning(
                    f"[AGENT_SDK_PERSISTENT] ProcessError {elapsed_total:.1f}s | "
                    f"exit={exit_code} | stderr={stderr[:500]} | msg={e} | "
                    f"(stderr_q vazia — sem info actionable; ver logs Render)"
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

            # Evictar client morto do pool para que próximo request crie um novo.
            # evict_client usa a chave composta (_pool_key) — pop pela chave crua
            # daria MISS e o client morto sobreviveria connected=True (R-CLI-CRASH).
            try:
                from .client_pool import evict_client
                if evict_client(pool_key, role=agent_role):  # chave composta + papel; ver evict_client
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
            # CLIConnectionError tem 2 causas distintas (diagnosticar antes de tratar):
            # 1. CLI subprocess crashou logo apos spawn (--resume com JSONL ausente,
            #    session store miss): elapsed < 2s, pool_key recente, sem partial_text.
            #    SOLUCAO: retry sem --resume (recuperavel transparentemente).
            # 2. CLI subprocess killed por SIGTERM mid-stream (worker recycling, deploy):
            #    elapsed > 5s OU tem partial_text. NAO recuperavel — emite error+done.
            #
            # Fix BUG #2 (2026-05-12 R-CLI-CRASH): antes, TODA CLIConnectionError
            # virava erro visivel ao usuario com mensagem "reciclagem do servidor".
            # Em 80% dos casos observados em prod era CASO 1 (resume failure) — o
            # subprocess crashava < 1s apos spawn ao tentar abrir JSONL inexistente.
            # Agora detectamos o caso e fazemos retry transparente sem --resume.
            elapsed_total = time.time() - state.stream_start_time
            is_resume_related = (
                resume_id is not None
                and elapsed_total < 5.0
                and not state.full_text
            )

            if is_resume_related and resume_id is not None:
                logger.warning(
                    f"[AGENT_SDK_PERSISTENT] CLIConnectionError {elapsed_total:.1f}s "
                    f"resume-related (resume_id={resume_id[:12]}...) | msg={e} | "
                    f"pool_key={pool_key[:8]}... — fazendo retry SEM resume"
                )

                # Evict dead client + cleanup JSONL stale (igual ao handler ProcessError)
                try:
                    from .client_pool import evict_client
                    evict_client(pool_key, role=agent_role)  # chave composta + papel; ver evict_client
                except Exception as evict_err:
                    logger.debug(f"[AGENT_SDK_PERSISTENT] Pool eviction ignored: {evict_err}")

                # Sinaliza para o hook injetar fallback de mensagens
                if resume_state is not None:
                    resume_state['failed'] = True

                # Cleanup JSONL stale (CLI nao deve achar arquivo corrompido)
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
                except Exception as cleanup_err:
                    logger.debug(f"[AGENT_SDK] Stale JSONL cleanup falhou: {cleanup_err}")

                # Retry: re-tentar todo o stream sem --resume.
                # Como nao podemos re-entrar no metodo de dentro do except, sinalizamos
                # via state.retry_without_resume e propagamos um erro RECUPERAVEL para o
                # caller (Teams services / chat route) que deve re-invocar o stream.
                yield StreamEvent(
                    type='warning',
                    content='Restaurando contexto da sessao anterior...',
                    metadata={
                        'reason': 'resume_failed_retry',
                        'error_type': 'cli_connection_error',
                        'recoverable': True,
                    }
                )
                # Emite done com flag de recovery para que caller saiba que precisa retry.
                # NAO emite type='error' (evita popup ao usuario para erro transparente).
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
                            'recoverable_resume_failure': True,
                        },
                        metadata={'error_type': 'cli_connection_error_resume'}
                    )
                return

            # CASO 2: CLI killed mid-stream (SIGTERM, worker recycling, deploy).
            # Comportamento legacy preservado para casos onde o subprocess realmente
            # foi morto externamente (e.g. graceful shutdown durante deploy).
            logger.warning(
                f"[AGENT_SDK_PERSISTENT] CLIConnectionError {elapsed_total:.1f}s | "
                f"msg={e} | pool_key={pool_key[:8]}... | partial_text_len={len(state.full_text)} | "
                f"Provavel reciclagem de worker (SIGTERM) ou crash mid-stream"
            )

            # Evict dead client from pool to force fresh connection on retry.
            try:
                from .client_pool import evict_client
                if evict_client(pool_key, role=agent_role):  # chave composta + papel; ver evict_client
                    logger.info(f"[AGENT_SDK_PERSISTENT] Dead client evicted from pool: {pool_key[:8]}...")
            except Exception as evict_err:
                logger.debug(f"[AGENT_SDK_PERSISTENT] Pool eviction ignored: {evict_err}")

            # Return partial text if any was collected before the crash
            user_msg = state.full_text if state.full_text else (
                "O processo do agente foi interrompido. Tente novamente em alguns segundos."
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
