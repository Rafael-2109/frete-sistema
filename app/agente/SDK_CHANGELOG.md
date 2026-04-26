# Agente Web — SDK Changelog (0.1.49 → 0.1.66)

> Historico de adocoes, breaking changes, bug fixes e features NAO adotadas do
> Claude Agent SDK. Extraido de `CLAUDE.md` para reducao de ruido.
>
> **Atualizado**: 2026-04-23 (SDK 0.1.66)

---

## SDK 0.1.66 (atualizado 2026-04-23) — Thinking display override

**Versao**: `claude-agent-sdk==0.1.66`
**CLI bundled**: 2.1.119

### Feature adotada: `ThinkingConfig.display` (SDK 0.1.65)

**MECANICA REAL**: `display` controla se o modelo gera texto SUMARIZADO do
raciocinio. Thinking real (chain-of-thought interno) acontece identico nos dois
casos; o que muda e o modelo gerar ou nao o resumo legivel:

| Valor | Comportamento | Custo | Qualidade |
|-------|---------------|-------|-----------|
| `summarized` | Modelo gera resumo do raciocinio + resposta | Tokens extras + latencia | Mesma da resposta final |
| `omitted` | Modelo pula o resumo, entrega so resposta | Mais rapido, mais barato | Identica |

**Arquitetura adotada**: toggle per-user persistente.

- **Default global**: `AGENT_THINKING_DISPLAY=omitted` (velocidade + economia).
- **Override per-user**: `Usuario.preferences['agent_thinking_display']` (JSONB).
  - Toggle no header do chat (icone cerebro): OFF=omitted, ON=summarized.
  - Persistido via `POST /agente/api/user-preferences`; lido por `api_chat` e
    propagado em `_stream_chat_response` -> `_async_stream_sdk_client` ->
    `client.stream_response` -> `client._build_options`.
  - Precedencia: user pref > env flag > skip.
- **Teams bot**: sem toggle (Teams nao processa `StreamEvent('thinking')`).
  Default `omitted` protege — zero impacto.
- **Debug panel (admin)**: respeita a preference do proprio admin (opcao b).
  Sem forcar `summarized` implicito.

**Arquivos criados/modificados**:

- `scripts/migrations/2026_04_23_add_usuarios_preferences.{py,sql}`: adiciona
  coluna `usuarios.preferences` JSONB default `'{}'`.
- `app/auth/models.py`: coluna + helpers `get_preference`/`set_preference` (usa
  `flag_modified` para JSONB mutation).
- `app/agente/routes/user_preferences.py`: rotas GET/POST com whitelist
  `_VALID_PREFERENCES` (rejeita chave/valor desconhecido com 400).
- `app/agente/sdk/client.py`: param `thinking_display` em `stream_response`,
  `_stream_response_persistent`, `_build_options`. Lido em precedencia
  user_pref > AGENT_THINKING_DISPLAY env.
- `app/agente/routes/chat.py:api_chat`: le `current_user.get_preference`
  e propaga em toda a cadeia de streaming.
- `app/agente/templates/agente/chat.html`: toggle `#thinking-display-toggle`.
- `app/static/agente/js/chat.js`: GET preference no DOMContentLoaded (localStorage
  mirror para render instantaneo), POST on change (rollback UI se backend falhar).

**Rollback**:
- `AGENT_THINKING_DISPLAY=off` + redeploy: nao passa campo, SDK/CLI decidem default (comportamento pre-0.1.65).
- User toggle: mudar para OFF, persiste omitted (ou limpar pref via SQL direto).

**Teste local** (2026-04-23):
- Migration executada (466 usuarios, preferences='{}' default, 0 NULL).
- `get_preference`/`set_preference` + rollback de transacao validados.
- Rotas GET/POST registradas em `/agente/api/user-preferences`.
- 5 arquivos Python compilam sem erro.

### Features 0.1.65 nao adotadas

- **`list_session_summaries()` protocol method** + `fold_session_summary()` helper: sem consumidor. Rota `/api/sessions/summaries` (`routes/sessions.py:251`) usa `AgentSession.summary` do DB nativo (mais rapido que parse JSONL). Adapter `PostgresSessionStore` mantem nao-implementado (linha 265).
- **`import_session_to_store()` helper**: migration local→store ja executada em Fase B (2026-04-21). Utilidade marginal.
- **`AdvisorToolResultBlock`**: nao usamos advisor MCP tool.

### Fix grátis via upgrade

- **`ServerToolUseBlock` + `ServerToolResultBlock` parser fix** (#836): antes `AssistantMessage(content=[])` quando mensagem tinha só server-side tool call. `WebSearch`/`WebFetch` na whitelist `allowed_tools` (`settings.py:52-53`) beneficiam — fix automatico via SDK upgrade.
- **Bounded retry em mirror append + UUID idempotency** (#857): esperamos menos `MirrorErrorMessage` no Sentry. Handler em `client.py:616` permanece como safety net.
- **`--debug-to-stderr` detection removida do transport**: stderr piping agora depende só de callback registrado. Nossa pipeline (`client.py:1279`) sempre registra callback quando `stderr_queue is not None` → zero impacto. Ainda passamos `extra_args: {"debug-to-stderr": None}` (CLI 2.1.118/2.1.119 aceitam; removal CLI é futuro).

### 0.1.66

Apenas bump CLI 2.1.119 (sem mudancas de API Python).

---

## SDK 0.1.64 (atualizado 2026-04-21) — SessionStore Fase B (cutover)

**Versao**: `claude-agent-sdk==0.1.64`, `asyncpg==0.30.0` (novo driver async)
**CLI bundled**: 2.1.116

### Feature: PostgresSessionStore (source-of-truth)

Tabela `claude_session_store` substituiu `session_persistence.py` — SDK 0.1.64 nativo via `TranscriptMirrorBatcher` (escrita) + `materialize_resume_session` (resume).

- **Adapter**: `app/agente/sdk/session_store_adapter.py` — `PostgresSessionStore` (5 dos 6 metodos do protocol)
- **Tabela**: `claude_session_store` (migration `2026_04_21_claude_session_store.{sql,py}`)
- **Conformance**: `tests/agente/sdk/test_session_store_conformance.py` — 13 contratos do harness oficial SDK 0.1.64
- **Flag**: `AGENT_SDK_SESSION_STORE_ENABLED` (default **ON** apos Fase B)
- **Timeout**: `AGENT_SDK_SESSION_STORE_LOAD_TIMEOUT_MS` (default 30000ms)

### Historico de fases

| Fase | Data | Estado |
|------|------|--------|
| A (dual-run) | 2026-04-21 15:00-16:30 | Flag OFF default, session_persistence.py em paralelo, criterio C4 "apenas sessions novas" |
| **B (cutover)** | 2026-04-21 17:00 | Flag ON default, 6 callsites legados removidos, session_persistence.py reduzido a helpers de path, migration batch populou store |

### Rollback

- `AGENT_SDK_SESSION_STORE_ENABLED=false` + redeploy (0 downtime)
- `session_persistence.py` NAO e tocado em Fase A — continua funcionando em paralelo (belt + suspenders)
- Dados orfaos em `claude_session_store` nao afetam performance (indexed)

### Pool asyncpg

- **LAZY per-worker** via `asyncio.Lock` — evita sockets compartilhados em gunicorn fork (C2 adversarial)
- `min_size=1, max_size=3` por worker — 4 workers × 3 = 12 conn asyncpg + 4 × 15 psycopg2 = ~72/~197 Render Basic 4GB
- DSN parsed: `_prepare_dsn()` remove `client_encoding` e `options=-c ...` (psycopg2-specific, asyncpg ignora)
- Shutdown: `close_session_store_pool()` disponivel (best-effort, nao bloqueia)

### Integracao (`client.py`)

1. `_build_options` (sync) — inalterada; retorna `ClaudeAgentOptions` base
2. `_stream_response_persistent` (async, linha ~1422) — apos `options = self._build_options(...)`, se flag ON E session NOVA: `options = replace(options, session_store=store, load_timeout_ms=...)` via `dataclasses.replace`
3. `_parse_sdk_message` (linha ~547) — handler `MirrorErrorMessage` (subclass SystemMessage): log ERROR + Sentry, NAO propagado como SSE

### Encoding `project_key`

- `project_key_for_directory('/home/rafaelnascimento/projetos/frete_sistema')` = `-home-rafaelnascimento-projetos-frete-sistema`
- **Identico ao regex atual** de `session_persistence.py` (verificado empirico via SDK)
- Sem migracao de dados — sessions legadas e novas usam mesma chave

### MirrorErrorMessage

- Subclass de `SystemMessage` em SDK 0.1.64+
- Emitida quando `store.append()` falha — contrato at-most-once (batch perdido, nao retentado)
- Disco local continua durable — session nao quebra
- Import condicional (try/except) em `client.py:47-57` para compat com SDK < 0.1.64

### Fase B (EXECUTADA 2026-04-21)

- ✅ `session_persistence.py` reduzido a helpers de path (`_get_session_path` mantido para cleanup stale JSONL em client.py/client_pool.py)
- ✅ 6 callsites legados removidos: `chat.py:321,1311` (pre/pos-stream) + `teams/services.py:579,641,950,1154` (streaming + non-streaming)
- ✅ Flag `AGENT_SDK_SESSION_STORE_ENABLED` default **ON**; criterio C4 "apenas sessions novas" removido (flag universal)
- ✅ Migration batch `scripts/migrations/2026_04_21_migrar_session_persistence_to_store.py` populou store (rodar manualmente no Render Shell com `--project-key=-opt-render-project-src`)
- ✅ 81/81 testes existentes passaram pos-cutover
- Fallback defense in depth: se store falhar, `UserPromptSubmit` hook (`chat.py:341-360`) reinjeta contexto XML das ultimas 10 msgs do `AgentSession.data['messages']` JSONB

### Fase C (cleanup) — EXECUTADA 2026-04-21

- ✅ `ALTER TABLE agent_sessions DROP COLUMN sdk_session_transcript` via `scripts/migrations/2026_04_21_drop_sdk_session_transcript.{py,sql}` (libera ~66MB)
- ✅ `AgentSession.save_transcript()` / `get_transcript()` removidos (`models.py` — zero callers verificados antes do drop)
- ✅ `session_store_adapter.session_has_legacy_transcript()` e `session_has_store_entries()` removidas (helpers do criterio C4 dual-run, orfas pos-Fase B)
- ✅ `session_turn_indexer.py` removido `defer(AgentSession.sdk_session_transcript)` — nao mais necessario
- ⏳ `session_persistence.py` mantido como helpers de path (2 funcoes) — remocao completa exige realocar `_get_session_path` usado em cleanup stale JSONL

### Referencias

- Plano adversarial-revised: `/tmp/subagent-findings/20260421-sessionstore-60ddbe70/phase3/plan-v2-final.md`
- Rollback runbook: `app/agente/ROLLBACK_SESSION_STORE.md`
- Reference adapter oficial: `anthropics/claude-agent-sdk-python/examples/session_stores/postgres_session_store.py`
- Conformance harness: `claude_agent_sdk.testing.run_session_store_conformance`

---

## SDK 0.1.60 (atualizado 2026-04-16)

**Versao**: `claude-agent-sdk==0.1.60`
**Modelo default**: `claude-opus-4-7` (migrado de 4.6 em 2026-04-16)

### Migracao Opus 4.6 → 4.7 (2026-04-16)
- `config/settings.py:31`: default `model="claude-opus-4-7"` (mesmo preco $5/$25 per MTok, adaptive thinking, 1M context, 128K max output).
- `config/settings.py:MODEL_PRICING`: adicionado `'claude-opus-4-7': (5.00, 25.00)`; 4.6 e 4.5 mantidos como legado.
- `config/feature_flags.py:322`: `TEAMS_DEFAULT_MODEL` default `claude-opus-4-7`.
- **Rollback instantaneo** via env vars: `AGENT_MODEL=claude-opus-4-6` + `TEAMS_DEFAULT_MODEL=claude-opus-4-6`.
- **Breaking changes aplicaveis**: thinking `{"type": "enabled"}` removido (nao usavamos — ja usavamos `effort` nativo); `temperature/top_p/top_k` removidos (nao usados em Opus — Sonnet/Haiku em services nao sao afetados); prefill de assistant removido (nao usado); thinking `display: "omitted"` default (risco UX — CLI 2.1.111 pode exibir normalmente via `effort`; monitorar eventos `thinking` na pipeline SSE).
- **Comportamento**: tokenizer novo (~0-35% mais tokens por texto), respostas calibradas pela complexidade, mais literal, tom mais direto, spawna menos subagentes por default, usa menos tools por default (steerable via `effort=high` ou prompt).
- **Features novas disponiveis nao adotadas**: `xhigh` effort level (SDK 0.1.60 nao expõe no Literal type — via `extra_args` se necessario), `task_budget` beta (`task-budgets-2026-03-13` — campo ja existe em `ClaudeAgentOptions`), alta resolucao de imagem (2576px automatico, irrelevante para screenshots Playwright ja comprimidos).

### Features adotadas (0.1.56–0.1.60):
- **`list_subagents()`/`get_subagent_messages()`** (0.1.60): Helpers para inspecionar cadeias de mensagens de subagentes spawnados. Exportados no top-level. **NAO adotado ainda** — candidato a endpoint admin de debug.
- **Distributed tracing W3C** (0.1.60): `TRACEPARENT`/`TRACESTATE` propagados para subprocess CLI quando span OpenTelemetry ativo. **NAO adotado** (projeto nao usa OTEL).
- **Cascading `delete_session()`** (0.1.60): Agora remove diretorios de transcript de subagentes irmaos. **NAO aplicavel** (projeto nao usa `delete_session()` do SDK, usa fluxo DB proprio).
- **`setting_sources=[]` fix** (0.1.60): Lista vazia passada nao e mais silenciosamente descartada — desabilita todos os settings do filesystem corretamente. Adotado automaticamente via upgrade.
- **CLI empacotado 2.1.111** (0.1.60): Base para comportamento Opus 4.7 + correcoes diversas.
- **`thinking={"type": "adaptive"}` mapping fix** (0.1.57): Comportamento alinhado com TS SDK. **Critico para Opus 4.7** (que depende de adaptive thinking). Adotado automaticamente.
- **`exclude_dynamic_sections` em `SystemPromptPreset`** (0.1.57): Move secoes dinamicas per-user para fora do system prompt → cross-user cache hits. **NAO adotado** — arquitetura atual usa string direta com hook `session_context` (`USE_PROMPT_CACHE_OPTIMIZATION`), ja otimizada. Mudaria o fluxo.
- **`"auto"` em `PermissionMode`** (0.1.57): **NAO adotado** — projeto usa `can_use_tool` callback customizado em `permissions.py`.
- **`maxResultSizeChars` MCP fix** (0.1.55): Resultados MCP grandes nao sao mais truncados silenciosamente. CLI 2.1.91.

### Features adotadas (0.1.51–0.1.53):
- **`typing.Annotated` em MCP tools** (0.1.52): Descriptions por parametro no JSON Schema. `_mcp_enhanced.py:_python_type_to_json_schema()` processa `Annotated[str, "desc"]` → `{"type": "string", "description": "desc"}`. Aplicado em 34 tools (7 MCP servers). Modelo recebe instrucoes por parametro em vez de adivinhar pelo nome.
- **`ToolPermissionContext.tool_use_id/agent_id`** (0.1.52): `can_use_tool()` agora recebe `agent_id` (UUID instancia do subagente) e `tool_use_id` (ID unico da tool call). `permissions.py` registra mapa `agent_id→agent_type` via `SubagentStart` hook. Infraestrutura de politicas por subagente pronta (`_SUBAGENT_DENY_POLICIES`, vazio por default — `tools` whitelist ja restringe). Audit trail com agent_type em cada permissao.
- **`AgentDefinition.disallowedTools/maxTurns/initialPrompt`** (0.1.51): `agent_loader.py` parseia `disallowed_tools`, `max_turns`, `initial_prompt` do frontmatter. Disponivel para uso nos `.claude/agents/*.md` quando necessario — nao aplicado por padrao.
- **`ClaudeAgentOptions.session_id`** (0.1.52): Pre-declara UUID do JSONL. `_build_options()` passa `our_session_id` como `session_id` → naming deterministico. Resume usa `our_session_id` como fallback se `sdk_session_id` ausente. **NOTA**: Issue #560 (aberta) — `ClaudeSDKClient` nao usa `session_id` para isolamento; nosso pool resolve via instancias separadas.
- **`ResultMessage.errors`** (0.1.51): Campo `errors` logado no ResultMessage handler e propagado no StreamEvent `done`.
- **`fork_session()`/`delete_session()`** (0.1.51, NAO usadas): APIs de sessao. Disponiveis para uso futuro.
- **`task_budget`** (0.1.51, NAO usado): Limite de tokens por task/subagent.
- **`SystemPromptFile`** (0.1.51, NAO usado): System prompt via arquivo. Nosso prompt e ~3KB string — sem necessidade.
- **`get_context_usage()`** (0.1.52, NAO implementado): Monitoramento de context window. Requer wiring 3-layer (client→routes→chat.js).
- **`stderr` callback** (0.1.53, implementado 2026-04-01): Captura debug output do CLI subprocess em real-time. Pipeline 3-layer: `_build_options(stderr_queue)` → `StreamEvent('stderr')` → SSE → debug panel (admin-only). Flag: `USE_STDERR_CALLBACK`. Requer `debug_mode=true` no request E flag ativa. `extra_args: {"debug-to-stderr": None}` habilita output no CLI.
- **`output_format`** (0.1.53, frontend implementado 2026-04-01): Structured output com JSON Schema. Backend ja estava wired (`_build_options` + done event). Frontend agora renderiza `structured_output` como tabela (arrays), badges (fields simples), ou JSON collapsible (fallback). Request param: `output_format: {type: "json_schema", schema: {...}}`.

### Features adotadas (anteriores, mantidas):
- **`ResultMessage.stop_reason`**: Populado automaticamente no StreamEvent `done` e logado.
- **Task messages** (`TaskStartedMessage`, `TaskProgressMessage`, `TaskNotificationMessage`): SSE events para observabilidade de subagentes.
- **`agent_id`/`agent_type` em hooks**: `PostToolUseHookInput` logados no `[AUDIT] PostToolUse`.
- **`effort` field nativo**: `ClaudeAgentOptions.effort` — substituiu `max_thinking_tokens`.
- **`RateLimitEvent`** (0.1.50): Pipeline 3-layer: client.py → routes/chat.py → chat.js (toast).
- **`HookMatcher.timeout`** (0.1.50): `UserPromptSubmit` usa 120s.
- **`AgentDefinition.skills`** (0.1.49): Skills nativas via `_SDK_HAS_NATIVE_FIELDS`.

### Features adotadas (2026-04-16 — SDK 0.1.60 fases 1-2):
- **`sdk/subagent_reader.py`**: Wrapper de `list_subagents` + `get_subagent_messages`. Fundacao usada por #1, #3, #5, #6. Retorna `SubagentSummary` com tools cronologicas, cost, tokens, findings_text. Aplica mascaramento PII por default (regex brasileiro em `utils/pii_masker.py`).
- **Endpoint admin debug forense** (`routes/admin_subagents.py`, #1): 3 rotas admin-only — `/api/admin/sessions/<id>/subagents[/<aid>[/messages]]`. Flag `USE_SUBAGENT_DEBUG_ENDPOINT` (default true).
- **Cost tracking granular** (`hooks.py` + `models.py` + `services/insights_service.py`, #3): SubagentStop persiste entry em `AgentSession.data['subagent_costs']` (JSONB v1, indice GIN em `scripts/migrations/agent_session_subagent_costs_idx.{py,sql}`). Classmethod `AgentSession.top_subagents_by_cost(days, limit)`. Flag `USE_SUBAGENT_COST_GRANULAR`.
- **UI linha inline expansivel** (`routes/subagents.py` + `static/agente/js/chat.js` + `static/agente/css/_subagent-inline.css`, #6): Linha dentro do fluxo da conversa com estados running/done/expanded. Lazy-fetch em `/api/sessions/<id>/subagents/<aid>/summary`. PII sanitizada via `_sanitize_subagent_summary_for_user()` em `routes/chat.py` para non-admin. Admin ve cost + raw. Flag `USE_SUBAGENT_UI`.
- **Memory mining cross-subagent** (`services/pattern_analyzer.py`, #5): `extrair_conhecimento_sessao(include_subagents=True, session_id=...)` injeta findings dos especialistas antes da conversa principal no prompt Sonnet. Cap 2K chars/subagent. Flag `USE_SUBAGENT_MEMORY_MINING`.

### Features adotadas (2026-04-17 — SDK 0.1.60 fase 4):
- **Validacao anti-alucinacao async** (`workers/subagent_validator.py` + `sdk/hooks.py` enqueue + `routes/chat.py` pubsub subscriber, #4): `SubagentStop` hook enfileira job RQ em queue `agent_validation` (processada por `worker_render.py` e `worker_atacadao.py`). Worker carrega summary via `subagent_reader`, chama Haiku 4.5 (`claude-haiku-4-5-20251001`) com prompt estruturado comparando tool_results vs `findings_text`, parseia JSON `{score, reason, flagged_claims}` e persiste em `AgentSession.data['subagent_validations']` (JSONB v1). Se `score < SUBAGENT_VALIDATION_THRESHOLD` (default 70, env var), publica evento `subagent_validation` no canal Redis `agent_sse:<session_id>`. SSE generator em `routes/chat.py` subscreve esse canal via non-blocking `pubsub.get_message(timeout=0.0)` e emite evento ao frontend. `chat.js` renderiza icone ⚠ amarelo na linha do subagent (CSS `.validation-warning`). Flag `USE_SUBAGENT_VALIDATION` controla enqueue + subscribe. Custo: ~$0.0005/call.

**PII sanitization** (`utils/pii_masker.py`): Regex conservadora CPF/CNPJ/email formatados e sem formatacao. Preserva DV/filial/dominio. Admin pula sanitizacao via `_sanitize_subagent_summary_for_user()` em `routes/chat.py`.

**GOTCHA**: Global exception handler em `app/__init__.py:511` re-raise HTTPException (exceto 404). `abort(403)` NAO funciona em rotas deste app — usar `return jsonify({'success': False, 'error': '...'}), 403` inline (pattern de `admin_learning.py`).

**Pendente** (fase 3): #2 aposentar `/tmp/subagent-findings/` (soft, mantem fallback).

### Bugs corrigidos na Fase 2 (2026-04-17)

Diagnosticados via logs Render: **19/19 sessoes em 48h com `subagent_costs` VAZIO** antes do fix. 3 bugs de raiz + 1 descoberto durante investigacao:

- **Bug 1 — `cost_usd=None` sempre**: JSONL de SUBAGENT nao contem `type:'result'` (SDK 0.1.60 exclui `result` de `_TRANSCRIPT_ENTRY_TYPES` em `sessions.py:791-794`). Solucao: novo helper `_compute_subagent_metadata_from_jsonl()` em `subagent_reader.py` soma `usage` de cada `AssistantMessage` + diff de timestamps. `_read_result_metadata()` ainda tenta `type:'result'` primeiro (compat forward).

- **Bug 2 — `subscribers=0` em 60% dos publishes**: race condition hook async (`spawn_task`) vs SSE close em 3s pos-`done`. Solucao T7: `_emit_subagent_summary` (`client.py:73`) publica em pubsub **E** `RPUSH` em `agent_sse_buffer:<session_id>` (TTL 5min, cap 20). SSE generator dreva buffer com `LRANGE 0 -1` antes de subscribir pubsub (`routes/chat.py:963-1010`).

- **Bug 3 — `list_subagents` retornando vazio**: REFUTADO em producao. `CLAUDE_CONFIG_DIR=/tmp/.claude` ja setado como env var no Render; SDK default funciona.

- **Bug 4 — parser de blocks retorna 0 tools**: `SessionMessage.message` do SDK 0.1.60 e dict Anthropic `{role, content, ...}` — parser antigo acessava `msg.content` direto (sempre None). Fix em `subagent_reader.py:_extract_content_list()` usa `msg.message.get('content')`. Log de 2026-04-17 12:20:13 mostrava `status=done tools_used=0 findings_len=0` apesar de JSONL de 131KB com 24 linhas — era este bug.

**Pricing correto com cache** (`sdk/pricing.py` novo): tabela por modelo distinguindo `input`, `output`, `cache_creation` (1.25x input), `cache_read` (0.10x input). Ex Opus 4.7: $5/$25 per MTok.

**Persistencia v2** (`hooks.py:528-610`): entries em `AgentSession.data->'subagent_costs'->'entries'` agora tem `schema_version='v2'`, escritas via `UPDATE ... jsonb_set(..., || :entry_json::jsonb)` SQL raw — atomico, elimina lost-update de subagents concorrentes que afetava v1 silenciosamente.

**Smoketest endpoint** (`routes/admin_subagents.py:api_admin_subagent_smoketest`): `GET /agente/api/admin/debug/subagent-smoketest` valida pipeline end-to-end (list_subagents + get_subagent_summary + SQL entries). Healthy requer `status=done` + `num_turns>0 OU cost_usd>0` + `tools_used>0 OU findings_len>0`.

### Bug fixes criticos (0.1.51–0.1.53):
- **`is_error` MCP propagado** (0.1.51): Modelo sabe quando MCP tool falhou (antes interpretava erro como sucesso)
- **`SIGKILL` fallback nativo** (0.1.51): SDK agora mata subprocess zombie. `_force_kill_subprocess()` em `client_pool.py` pode ser simplificado
- **`control_cancel_request`** (0.1.52): Hooks in-flight cancelados corretamente (antes ficavam zombie)
- **Cross-task `RuntimeError` fix** (0.1.51): `disconnect()` nao falha mais ao ser chamado de task diferente
- **`--setting-sources` fix** (0.1.53): Lista vazia nao corrompe flags do CLI
- **Deadlock `query()`+hooks fix** (0.1.53): Afeta apenas path v2 (codigo morto)

### NAO usadas (mantidas para referencia):
- **Session Management APIs** (0.1.50): `list_sessions()`, `get_session_info()`, etc.
- **MCP Runtime Control** (0.1.50): `get_mcp_status()`, `toggle_mcp_server()`, etc.
- **`AgentDefinition.mcpServers`** (0.1.49): Apenas para servers EXTERNOS.
- **`AgentDefinition.memory`** (0.1.49): Conflita com sistema custom PostgreSQL.
