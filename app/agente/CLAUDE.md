# Agente Logistico Web — Guia de Desenvolvimento

**LOC**: ~41.9K | **Arquivos**: 80 | **Atualizado**: 25/05/2026

Wrapper do Claude Agent SDK: chat web (SSE) + Teams bot (async).

> **Historico SDK** (changelog 0.1.49 → 0.2.87 + anthropic 0.85 → 0.98.1 — features adotadas, breaking changes, bug fixes): ver `SDK_CHANGELOG.md`.

---

## Estrutura

```
app/agente/                          # Root — 6 arquivos
├── __init__.py                      # Blueprint import de routes/ + init_app()
├── CLAUDE.md                        # Este arquivo (guia dev)
├── SDK_CHANGELOG.md                 # Historico SDK 0.1.49 -> 0.2.87 (features, breaking, fixes) — inclui revisao retroativa do 0.2.82 (2 breakings omitidas)
├── ROLLBACK_SESSION_STORE.md        # Procedimento rollback PostgresSessionStore (Fase B)
├── historia.md                      # Referencia historica (legado, 76K)
├── models.py                        # SQLAlchemy models (AgentSession, AgentMemory, etc.)
├── routes/                          # Flask routes modularizadas — 20 arquivos
│   ├── __init__.py                  # agente_bp + imports sub-modulos + re-exports Teams
│   ├── _constants.py                # Constantes (timeouts, thresholds, upload)
│   ├── _helpers.py                  # Helpers compartilhados (Teams + cross-module)
│   ├── chat.py                      # Core SSE: api_chat, streaming, interrupt, user_answer
│   ├── sessions.py                  # CRUD sessoes: list, messages, delete, rename, summaries
│   ├── admin_learning.py            # Admin: session messages, generate/save correction
│   ├── admin_metrics.py             # Dashboard admin telemetria subagent (Fase A — 10 endpoints)
│   ├── admin_session_store.py       # Admin: PostgresSessionStore introspection (Fase B)
│   ├── admin_subagents.py           # Admin forense: list/messages + smoketest (SDK 0.1.60 fase 2)
│   ├── subagents.py                 # API UI-inline: summary/messages lazy-fetch
│   ├── artifacts.py                 # 5 rotas: 3 publicas (page/bundle/status) + API list/by-uuid/url
│   ├── files.py                     # Upload/download/list/delete + helpers arquivo
│   ├── health.py                    # api_health com cache
│   ├── feedback.py                  # api_feedback 4 tipos
│   ├── insights.py                  # pagina_insights + APIs dados
│   ├── intelligence_report.py       # D7 cron bridge, csrf.exempt
│   ├── improvement_dialogue.py      # D8 cron bridge + admin, csrf.exempt
│   ├── memories.py                  # CRUD memorias + users + review
│   ├── briefing.py                  # api_get_briefing
│   └── user_preferences.py          # Preferences API (thinking display, etc.)
├── config/                          # Configuracao e controle de acesso — 6 arquivos
│   ├── __init__.py
│   ├── agent_loader.py              # Carregamento dinamico do agente
│   ├── empresa_briefing.md          # Briefing institucional injetado no prompt
│   ├── feature_flags.py             # Feature flags e timeouts configuraveis
│   ├── permissions.py               # ContextVar session_id, event_queue, thread-safety
│   └── settings.py                  # Constantes e configuracoes do SDK
├── hooks/                           # Hooks do Agent SDK — 2 arquivos
│   ├── __init__.py
│   └── README.md
├── prompts/                         # Prompts do agente web — 4 arquivos
│   ├── __init__.py
│   ├── preset_operacional.md        # Preset customizado (substitui claude_code preset)
│   ├── prompt_inventario.md         # Prompt operacional inventario 2026-05 (NACOM/LF)
│   └── system_prompt.md             # System prompt do agente (usuarios finais)
├── sdk/                             # Integracao com Claude Agent SDK — 17 arquivos
│   ├── __init__.py
│   ├── _sanitization.py             # Helpers de sanitizacao PII cross-modulo
│   ├── client.py                    # Client principal (streaming, build_options, parse)
│   ├── client_pool.py               # Pool de clients reutilizaveis
│   ├── cost_tracker.py              # Rastreamento de custos por sessao
│   ├── hooks.py                     # 8 SDK hook closures (build_hooks() factory)
│   ├── memory_injection.py          # Pipeline multi-tier de injecao de memorias
│   ├── memory_injection_rules.py    # Regras declarativas de injecao (paths + filtros)
│   ├── model_router.py              # Routing de modelo per-request (per-user/preset)
│   ├── pending_questions.py         # AskUserQuestion (dual event: sync + async)
│   ├── pricing.py                   # Tabela precos por modelo (input/output/cache_creation/cache_read)
│   ├── session_archive.py           # Archive tar.gz S3 de sessoes expiradas
│   ├── session_persistence.py       # Persistencia JSONL de sessoes SDK
│   ├── session_store_adapter.py     # Adapter PostgresSessionStore (Fase B cutover)
│   ├── shutdown_state.py            # Flag global atexit (suprime Sentry de RuntimeError shutdown)
│   ├── stream_parser.py             # Dataclasses + classificacao de erros de tool
│   └── subagent_reader.py           # Wrapper list_subagents + get_subagent_messages (SDK 0.1.60)
├── services/                        # Servicos de inteligencia — 17 arquivos (ver services/CLAUDE.md)
│   ├── __init__.py
│   ├── CLAUDE.md                    # Sub-guia com regras R1-R5 dos services
│   ├── _utils.py                    # Helpers compartilhados (parse_llm_json_response)
│   ├── artifact_service.py          # Service de artifacts (rate limit, spec validation, S3)
│   ├── friction_analyzer.py         # Analise de friccao de uso
│   ├── improvement_suggester.py     # Dialogo D8 melhoria (batch + real-time)
│   ├── insights_service.py          # Gerador de insights pos-sessao
│   ├── intersession_briefing.py     # Briefing entre sessoes
│   ├── knowledge_graph_service.py   # Grafo de conhecimento (memorias)
│   ├── memory_consolidator.py       # Consolidacao de memorias redundantes
│   ├── metrics_dashboard_service.py # Dashboard telemetria subagent (Fase A1+A3)
│   ├── pattern_analyzer.py          # Extracao de padroes e conhecimento
│   ├── recommendations_engine.py    # Motor de recomendacoes
│   ├── sentiment_detector.py        # Deteccao de sentimento
│   ├── session_summarizer.py        # Resumo automatico de sessoes
│   ├── sql_evaluator_falses_service.py # Detector de falsos negativos em SQL evaluator
│   ├── suggestion_generator.py      # Gerador de sugestoes proativas
│   └── tool_skill_mapper.py         # Mapeamento tool → skill
├── templates/agente/                # Templates Jinja2 — 5 arquivos
│   ├── admin_metrics.html           # Dashboard telemetria subagent (Chart.js 3.9.1, admin)
│   ├── admin_session_store.html     # Dashboard admin SessionStore (R6 observability)
│   ├── artifact.html                # Pagina render bundle artifact (sandboxed iframe)
│   ├── chat.html                    # Interface de chat web
│   └── insights.html                # Dashboard de insights
├── tools/                           # MCP tools (NAO callables) — 12 arquivos
│   ├── __init__.py
│   ├── _mcp_enhanced.py             # Wrapper Enhanced (outputSchema + structuredContent)
│   ├── artifact_tool.py             # build_artifact MCP tool (Enhanced v1.0)
│   ├── memory_mcp_tool.py           # 12 operacoes de memoria (Enhanced v2.1.0)
│   ├── playwright_mcp_tool.py       # Browser automation (13 tools, SSW + Atacadao)
│   ├── render_logs_tool.py          # Consulta logs Render
│   ├── routes_search_tool.py        # Busca em rotas Flask
│   ├── schema_mcp_tool.py           # Consulta schemas de tabelas
│   ├── session_search_tool.py       # 4 operacoes de busca em sessoes (Enhanced v4.0.0)
│   ├── sql_session_context.py       # Helpers de contexto SQL por sessao
│   ├── teams_card_tool.py           # Adaptive Cards para Teams (rich responses)
│   └── text_to_sql_tool.py          # Text-to-SQL (Enhanced v2.0.0)
├── utils/                           # Helpers de modulo — 2 arquivos
│   └── pii_masker.py                # Mascaramento regex CPF/CNPJ/email (SDK 0.1.60 fase 2)
└── workers/                         # Workers RQ locais — 3 arquivos
    ├── __init__.py
    ├── artifact_worker.py           # build_artifact_job (Vite+React+TS+Tailwind, queue artifacts)
    └── subagent_validator.py        # Haiku anti-alucinacao (SDK 0.1.60 fase 4, queue agent_validation)
```

---

## Arquitetura de Prompts (v3 — 28/03/2026)

### Principio: Separacao Estrutural (DOC-1.md)

Segue o modelo de 5 camadas do Agent SDK (Anthropic):
1. **System prompt** (`system_prompt`) → comportamento e routing (estatico, cacheavel)
2. **Tools** (`mcp_servers`) → capacidades como dados estruturados (auto-descritos)
3. **Skills** (`SKILL.md` filesystem) → conhecimento de dominio (progressive disclosure)
4. **Subagents** (`agents` dict) → alvos de delegacao (cada um com tools/skills proprios)
5. **Control** (hooks + `allowed_tools`) → permissoes e enforcement

### Dois modos (feature flag `USE_CUSTOM_SYSTEM_PROMPT`)

| Flag | System Prompt | Identidade | Tokens |
|------|--------------|------------|--------|
| `false` | `{preset: "claude_code", append: system_prompt.md}` | Claude Code + Agente (conflito) | ~7K |
| `true` (default) | `preset_operacional.md + system_prompt.md` (string) | Apenas Agente (coerente) | ~2.7K |

### Camadas (com flag true)

```
┌──────────────────────────────────────────┐
│ 1. preset_operacional.md (~600 tok)      │ ← Tools, safety, environment
│ 2. system_prompt.md (~2.1K tok)          │ ← Comportamento, routing, regras
│ 3. CLAUDE.md compartilhado (~1.5K tok)   │ ← Indice de referencias (unificado)
│ 4. Dynamic injections (hook)             │ ← Memorias, contexto operacional
└──────────────────────────────────────────┘
```

### Separacao de responsabilidades

| Arquivo | O QUE define | NAO define |
|---------|-------------|------------|
| `preset_operacional.md` | AWARENESS: tool prioritization, safety, /tmp, persistent systems | Identidade, regras de negocio |
| `system_prompt.md` | COMPORTAMENTO: R0-R7, I2-I4, routing strategy, subagent coordination | Tool descriptions (auto-descritas), knowledge_base (no CLAUDE.md) |
| `CLAUDE.md` (raiz) | REFERENCIA: indice unificado de docs, gotchas de modelos, subagentes | Regras dev, CSS, caminhos de modulo (em ~/.claude/CLAUDE.md) |
| `~/.claude/CLAUDE.md` | DEV-ONLY: Quick Start, migrations, CSS, caminhos, refs dev-only | Visivel apenas ao Claude Code |

### O que mudou na v3 (v4.2.0 do system_prompt)

| Mudanca | Racional (DOC-1.md) | Tokens salvos |
|---------|---------------------|---------------|
| R5: tabela MCP removida | Tool descriptions sao auto-descritas — duplicar no prompt e anti-pattern | ~150 |
| P1-P7: inline �� referencia | Agente delega a `analista-carteira`, nao decide P1-P7 sozinho | ~300 |
| knowledge_base: 17 entradas → ponteiro para CLAUDE.md | Root CLAUDE.md ja fornece indice unificado via `setting_sources` | ~200 |
| Subagent reliability: adicionado | Protocolo `/tmp/subagent-findings/` na coordination_protocol | +30 |
| Root CLAUDE.md: reorganizado | Subcategorias (Odoo, SSW, Infra), entradas dev-only movidas | — |
| analista-carteira.md: DRY | P1-P7 referencia REGRAS_P1_P7.md ao inves de inlinar | ~200 |
| Prompt Cache Optimization | `{data_atual}`, `{usuario_nome}`, `{user_id}` extraidos do system_prompt → injecao via hook `session_context`. System prompt estatico → cache hits | ~20 (vars) |
| Enhanced MCP Migration | Memory (11 tools) + Sessions (4 tools) migradas para `@enhanced_tool` com `outputSchema` + `structuredContent` | — |

### Rollback
- `AGENT_CUSTOM_SYSTEM_PROMPT=false` restaura preset claude_code
- `AGENT_PROMPT_CACHE_OPTIMIZATION=false` restaura variaveis dinamicas no system prompt (via prepend)

### Arquivos envolvidos
- `prompts/preset_operacional.md` — preset customizado (~65 linhas)
- `prompts/system_prompt.md` — system prompt operacional (v4.2.0, estatico — sem vars dinamicas)
- `sdk/client.py` — `_format_system_prompt()` (guard cache), `_user_prompt_submit_hook()` (session_context)
- `config/feature_flags.py` — `USE_CUSTOM_SYSTEM_PROMPT`, `USE_PROMPT_CACHE_OPTIMIZATION`
- `config/settings.py` — `operational_preset_path`

---

## Regras Criticas

### R1: Dois IDs de sessao — NUNCA confundir
- `session_id` (nosso UUID) → persistencia no banco (`AgentSession.session_id`)
- `sdk_session_id` (efemero do CLI) → armazenado em `data['sdk_session_id']` (JSONB, NAO coluna)
- **Resume** usa `sdk_session_id` (CLI carrega sessao do disco)
- **Banco** usa `session_id` (nosso controle, FK em queries)
- Confundir os dois causa sessao perdida ou mensagens em sessao errada
- ~~`sdk_session_transcript` e TEXT separado~~ REMOVIDA em Fase C (2026-04-21) — transcript vive em `claude_session_store`
- **GOTCHA restore**: `session_persistence.py:136` — se JSONL existe no disco, NAO re-restaura do banco. JSONL corrompido (crash, escrita parcial) → resume falha silenciosamente, SDK cria sessao nova, contexto perdido sem erro visivel

### R2: Thread-safety — 3 mecanismos distintos
| Mecanismo | Para que | Onde |
|-----------|----------|------|
| `ContextVar` (`_current_session_id`) | `session_id` (isolamento por thread E coroutine) | `permissions.py:46` |
| Dict global `_stream_context` + Lock | `event_queue` (cross-thread) | `permissions.py:40-41` |
| Dict `_teams_task_context` | Associar sessao <> TeamsTask | `permissions.py:98` |

**Fase 1 (Async Migration)**: `threading.local()` substituido por `ContextVar` para session_id.
ContextVar funciona em threads E coroutines. API externa inalterada (`set/get_current_session_id`).
NUNCA substituir ContextVar por variavel global — causa race condition entre threads/coroutines.
`event_queue` PRECISA ser global porque o endpoint SSE acessa de outra thread.

### Async Migration — Dual Event (pending_questions.py)
`PendingQuestion` agora tem `async_event: Optional[asyncio.Event]` alem do `threading.Event`.
- `register_question()` cria `asyncio.Event` se em async context
- `submit_answer()` sinaliza AMBOS events
- `async_wait_for_answer()` suspende coroutine (nao bloqueia thread)
- `cancel_pending()` desbloqueia AMBOS events
- `wait_for_answer()` (sync) mantido como fallback

**CUIDADO**: `asyncio.Event.set()` em `submit_answer()` e chamado de outra thread (Flask route).
No CPython o GIL protege, mas nao e oficialmente thread-safe. Se houver race condition,
substituir por `loop.call_soon_threadsafe(pq.async_event.set)`.

### R3: Stream safety — None sentinel + done_event
| Camada | Timeout | Funcao |
|--------|---------|--------|
| Heartbeat SSE | 10s | Evita proxy/Render matar conexao idle |
| Inatividade (renewal) | 300s | Renovavel a cada evento/chunk — timeout se parar de emitir (era 240s ate 2026-05-25) |
| Stream max | 1740s (web) / sem teto (teams) | Teto absoluto. Era 540s/600s ate 2026-05-25 (3 timeouts em 7d). Render permite 100min ([fonte](https://render.com/articles/real-time-ai-chat-websockets-infrastructure)) |
| None sentinel | finally | Garante que SSE generator termina |

NUNCA remover o `yield None` no `finally` do generator — frontend trava esperando eventos.

**`streaming_done_event`** (`client.py:2627`): `asyncio.Event()` que controla o prompt generator. Se NAO chamar `.set()` em QUALQUER error path, o generator fica preso em `done_event.wait(timeout=600)` → processo zombie por 10min. Chamado em 6 locais nos except handlers + 1 bloco `finally` como rede de seguranca.

**DC-8 (CancelledError bypass)**: `asyncio.CancelledError` e `BaseException` (NAO `Exception`) desde Python 3.9. Teams usa `asyncio.wait_for(timeout=chunk_timeout)` per-chunk que cancela via `CancelledError` — bypassa TODOS os 5 except handlers. O bloco `finally` em `_stream_response()` garante que `streaming_done_event.set()` SEMPRE e chamado, mesmo para `CancelledError`, `KeyboardInterrupt` e `SystemExit`. **O path persistente (`_stream_response_persistent`) e IMUNE porque `streaming_done_event = None`.**

**REGRA**: Ao adicionar NOVO error handler em `_stream_response()`, o `finally` block e a rede de seguranca definitiva — NAO precisa chamar `.set()` no novo handler (mas e boa pratica como defense-in-depth).

### R4: AskUserQuestion — blocking cross-arquivo + cross-worker (Redis)
Fluxo cruza 3 arquivos: `pending_questions.py` → `permissions.py` → `routes/chat.py`
- Web: event_queue SSE → frontend responde → POST `/api/user-answer` → Event.set()
- Teams: TeamsTask.status='awaiting_user_input' → Adaptive Card → POST resposta → Event.set()
- Timeout web: 55s. Timeout Teams: 120s (`TEAMS_ASK_USER_TIMEOUT`)

Alterar um arquivo sem verificar os outros 2 quebra o fluxo silenciosamente.

**R-CLI-CRASH (2026-05-12)**: `client.py:1957` respeita `resume_state['failed']`
setado pelo probe ao session_store. Antes, codigo ignorava a flag e fazia
`--resume X` mesmo com sessao confirmadamente ausente do PostgresSessionStore,
causando CLI exit code 1 + `CLIConnectionError "Failed to write to process stdin"`
em ~0.8s, com 2 retries automaticos do Teams services falhando identicamente
(observado em ~22 ocorrencias/2h em prod). Fix:
- `client.py:1957` (R1): se `probe_failed=True`, pular `_with_resume` e usar fallback
  XML via hook `UserPromptSubmit` (`hooks.py:1036` injeta `resume_state['fallback']`
  no `additionalContext`).
- `client.py:2238` (R2): handler `CLIConnectionError` agora detecta resume-related
  (elapsed < 5s + sem partial_text + resume_id) e emite `done` com
  `recoverable_resume_failure=True` em vez de error visivel. Caller (Teams services
  v2/v3) retenta — segunda tentativa entra com `resume_state['failed']=True`
  novamente e o fix R1 evita o crash.
- Defesa em profundidade: R1 evita 95% dos casos upstream; R2 captura edge cases
  (ex: probe nao executou por excecao, mas CLI ainda crashou).

**R-MULTIWORKER (2026-05-12)**: `pending_questions.py` usa Redis SETEX + pub/sub
para sincronizar entre os 4 workers gunicorn. Antes, `_pending` era dict
process-local → POST `/api/user-answer` caia em worker ≠ do registro em 75%
das tentativas → 404 silencioso + timeout 55s. Solucao:
- `register_question`: marca Redis `agent:pq:{sid}` (TTL 130s) + spawna subscriber
  daemon thread que escuta `agent:pq:answer:{sid}` e `agent:pq:cancel:{sid}`.
- `submit_answer` (qualquer worker): tenta local; se nao encontrar, valida Redis
  EXISTS e faz PUBLISH. Subscriber no worker dono recebe e sinaliza Event LOCAL.
- `get_pending_tool_input` tem fallback cross-worker via Redis GET.
- Feature flag: `AGENT_REDIS_PENDING_QUESTIONS=false` faz rollback p/ memory-only.
- Sem Redis: degrada para legacy (funciona dentro do mesmo worker, falha cross).
- API publica 100% preservada — callsites em `permissions.py`, `chat.py`, `bot_routes.py` nao mudaram.

### R5: MCP tools — NAO callable
Tools em `tools/` sao registros MCP (ToolAnnotations). O agente usa `mcp__X__Y` diretamente.
NUNCA importar e chamar como funcao Python — nao sao callables, gera erro silencioso.

### R6: MCP Enhanced Wrapper
`tools/_mcp_enhanced.py` adiciona `outputSchema` + `structuredContent` (MCP spec 2025-06-18).
- Usar `@enhanced_tool` + `create_enhanced_mcp_server` para tools que precisam de structured output
- Migradas: SQL (v2.0.0), Memory (v2.0.0), Sessions (v4.0.0). Demais usam `@tool` standard
- Ref completa: `.claude/references/MCP_CAPABILITIES_2026.md`

### R7: JSONB — flag_modified
Manter o padrao existente em `models.py`: SEMPRE `flag_modified(session, 'data')` apos modificar JSONB.

### R9: Audit Hook Deterministico Odoo — propagacao via PreToolUse (2026-05-28)

Quando flag `AGENT_ODOO_AUDIT_HOOK=true`:
- `sdk/hooks.py:_keep_stream_open` (PreToolUse) intercepta tool `Bash` e prefixa `command` com `export AGENT_SESSION_ID=<ctx> AGENT_TOOL_USE_ID=<tuid> AGENT_TYPE=<atype> AGENT_USER_NAME=<uname>` antes do command original.
- Subprocess Bash herda as ENV vars → script Python da skill chama `OdooConnection.execute_kw` → hook em `app/utils/odoo_audit_helpers.py` registra em `operacao_odoo_auditoria` correlacionando com sessao.

**Race-free**: usa `hookSpecificOutput.updatedInput` (SDK 0.1.29+, dict[str, Any]) — isolado por tool call, nao depende de `os.environ` global (que quebraria multi-worker gunicorn).

**Cuidados**:
- Hook NUNCA quebra a tool (try/except + log debug)
- shlex.quote escapa valores (defesa contra injection)
- Quando flag OFF, hook nao muta command (zero overhead)
- ContextVar `_current_session_id` em `permissions.py:46` e a fonte de `AGENT_SESSION_ID`

Ver `app/odoo/CLAUDE.md` secao P8 para detalhes do hook lado Odoo.
Migration: `scripts/migrations/2026_05_28_operacao_odoo_auditoria_session.{py,sql}`.

### R10: Persistencia da resposta — PRIMARY (thread daemon) vs DEFESA (generator finally)

No path persistente ha 2 gravacoes da resposta em `agent_sessions.data`:
- **PRIMARY**: `finally` da thread daemon `run_async_stream` — roda quando o turno
  COMPLETA, com `full_text` preenchido. E' quem deve salvar a resposta.
- **DEFESA**: `finally` do generator `_stream_chat_response`
  (`source='finally_generator'`) — rede de seguranca caso o primary falhe/morra.

**INVARIANTE (`_should_persist_in_finally`, 2026-05-29)**: a DEFESA so' persiste se
a thread daemon JA terminou (`not thread.is_alive()`). Se a thread ainda processa
(cliente desconectou mid-turno), a defesa DELEGA ao primary. Persistir na defesa
com a thread viva gravaria `full_text` vazio e marcaria `_persisted=True`,
BLOQUEANDO o primary de salvar a resposta real (race que perdia a resposta —
sessao do Marcus: 6 user / 0 assistant no banco apesar do HOOK:Stop). Como
`add_user_message`/`add_assistant_message` NAO sao idempotentes, a defesa NAO pode
rodar em paralelo ao primary.

**Frontend**: ao cair a conexao mid-turno, `startDeferredResponsePoll` (chat.js)
busca a resposta ja' persistida e a renderiza sem recarga manual (associa a 1a
`assistant` apos a ultima `user` de mesmo conteudo — robusto porque o primary
persiste user+assistant atomicamente no mesmo commit).

---

## Hierarquia de Timeouts

Timeouts em 4 arquivos com **deadline renewal**. DEVEM respeitar esta ordem ou causam cascata de falhas:

| Timeout | Valor | Fonte | Funcao |
|---------|-------|-------|--------|
| Heartbeat SSE | 10s | `routes/_constants.py` | Keep-alive para proxy |
| AskUser web | 55s | `pending_questions.py:30` | Espera resposta do usuario |
| AskUser Teams | 120s | `feature_flags.py` | Idem, via Adaptive Card |
| **Web inatividade** | 300s | `routes/_constants.py` | Renovavel a cada evento real (heartbeats NAO renovam) — era 240s ate 2026-05-25 |
| **Teams inatividade** | 300s | `services.py:1086` | Renovavel a cada chunk recebido — era 240s ate 2026-05-25 |
| SDK stream_close | 240s | `client.py:547` | Timeout CLI hooks/MCP |
| Job `validate_subagent_output` | 60s | `hooks.py:SubagentStop enqueue` | Timeout RQ para validacao Haiku |
| Web teto absoluto | 1740s | `routes/_constants.py` | Teto absoluto SSE (margem 60s vs gunicorn 1800s) — era 540s ate 2026-05-25 |
| Teams teto absoluto | — | — | Sem teto absoluto (DC-9, INACTIVITY_TIMEOUT renovavel) |
| Gunicorn timeout | 1800s | `start_render.sh` gunicorn_config | Per-request heartbeat gthread — era 600s ate 2026-05-25 |
| Render hard limit | 100min (6000s) | infra | Render permite ate 100min ([fonte](https://render.com/articles/real-time-ai-chat-websockets-infrastructure)) |

**Deadline renewal**: operacoes longas com progresso continuo NAO sao mais mortas pelo timeout fixo. A cada chunk/evento recebido, o deadline de inatividade (300s) e renovado. Apenas inatividade real (5 min sem progresso) ou teto absoluto disparam timeout.

**REGRA**: `USER_RESPONSE_TIMEOUT` (55s) DEVE ser < timeout do SDK (240s). Se >= SDK, o CLI mata o stream antes do usuario responder.

---

## Gotchas

### system_prompt.md vs preset_operacional.md vs CLAUDE.md
- `prompts/system_prompt.md` = identidade + regras do agente web (usuarios finais)
- `prompts/preset_operacional.md` = tool instructions + safety (substitui preset claude_code)
- Este arquivo (`CLAUDE.md`) = Claude Code (dev). NUNCA misturar prompts dev com prompts agente.
- Ver secao "Arquitetura de Prompts" acima para detalhes da separacao.

### SDK max_buffer_size: 10MB
`client.py:561` configura `max_buffer_size=10_000_000` (10MB). Default do SDK e 1MB — insuficiente para screenshots base64 (PNG full-page: 1.3-2.6MB). Se reduzir abaixo de 2MB, browser_screenshot volta a crashar com "JSON message exceeded maximum buffer size".

### Screenshot compression: 750KB limit
`playwright_mcp_tool.py:516` comprime PNG → JPEG (quality 80%) se > 750KB. Escalonamento: JPEG 80% → resize 50% → resize 25%. PNG original salvo em disco (URL funciona). Requer Pillow (`pillow` no requirements.txt).

### Prerequisitos de execucao
1. **`set_current_user_id()` ANTES do stream** — MCP tools (`memory_mcp_tool.py:33`, `session_search_tool.py:25`) usam `ContextVar` independentes. Se esquecer: `RuntimeError("user_id nao definido")`. CADA tool tem seu PROPRIO ContextVar.
2. **`get_or_create()` NAO e atomico** (`models.py:380-395`) — query + insert separados, sem `SELECT FOR UPDATE`. Duas threads podem criar sessao duplicada → `IntegrityError`. NUNCA assumir retorno valido sem try/except.
3. **Cascade delete** — `models.py` define `cascade='all, delete-orphan'` nos backrefs (linhas 79, 469, 689). `db.session.query(Model).filter_by(...).delete()` NAO dispara cascade → orphans. DEVE usar `db.session.delete(obj)`.

### S3 Storage (screenshots, archive)

Screenshots Playwright (`playwright-screenshots/{YYYY-MM}/`) e archive de sessoes (`agent-archive/{YYYY-MM}/{session}.tar.gz`) usam S3 compartilhado via `get_file_storage()`. Ambos sao best-effort (falha silenciosa se USE_S3=false ou erro de rede). Detalhes completos: `.claude/references/S3_STORAGE.md`.

### Arquivos legados — NAO usar, NAO estender
| Arquivo | Status |
|---------|--------|
| `historia.md` (76K) | Apenas referencia historica |

### Services (17 arquivos, ~10.5K LOC)
Guia completo de regras, gotchas e interdependencias: **`services/CLAUDE.md`**
Todos controlados por feature flags em `config/feature_flags.py`.

### MCP Tools de memoria (memory_mcp_tool.py v2.1.0 Enhanced, 12 operacoes)
| Tool | O que faz |
|------|-----------|
| `view_memories` | Le memoria por path |
| `save_memory` | Cria/atualiza memoria |
| `update_memory` | Atualiza conteudo existente |
| `delete_memory` | Remove memoria |
| `list_memories` | Lista todas as memorias |
| `clear_memories` | Limpa TODAS (destrutivo) |
| `search_cold_memories` | Busca no tier frio |
| `view_memory_history` | Consulta historico de versoes de uma memoria |
| `restore_memory_version` | Restaura versao anterior (backup automatico do atual) |
| `resolve_pendencia` | Marca pendencia como resolvida (desaparece do briefing) |
| `log_system_pitfall` | Registra armadilha/gotcha do sistema (max 20, category=structural) |
| `register_improvement` | Registra sugestao de melhoria real-time para Claude Code (skill_bug, skill_suggestion, etc.) |

**Admin (debug mode)**: TODAS as 12 tools aceitam `target_user_id=N` para acesso cross-user.
Validacao: `_resolve_user_id(args)` — requer `get_debug_mode() == True`. Todo acesso logado.

### MCP Tools de sessao (session_search_tool.py v4.0.0 Enhanced, 4 operacoes)
| Tool | O que faz |
|------|-----------|
| `search_sessions` | Busca textual (ILIKE) em sessoes anteriores |
| `list_recent_sessions` | Lista sessoes recentes com titulo, data, resumo |
| `semantic_search_sessions` | Busca semantica via embeddings (fallback ILIKE) |
| `list_session_users` | Lista usuarios com sessoes — **admin-only, debug mode** |

**Admin (debug mode)**: `search_sessions`, `list_recent_sessions` e `semantic_search_sessions`
aceitam `target_user_id=N` para busca cross-user. `channel='teams'|'web'` filtra por canal.
Pattern: `_resolve_user_id(args)` espelha `memory_mcp_tool.py`.

### Debug Mode — Injecao de Contexto (client.py)

O hook `_user_prompt_submit_hook` injeta `<debug_mode_context>` quando debug mode esta ativo.
Isso permite ao Agent SABER que pode usar `target_user_id`, `channel`, e `list_session_users`.

Sem essa injecao, o Agent opera com debug mode nos bastidores mas NAO sabe que pode usar
as capacidades extras — resultado: falha em investigacao cross-user.

---

## Pipeline SSE — Contrato de 3 Camadas

### R8: Novo evento = atualizar TODAS as 3 camadas

Ao adicionar novo tipo de evento, **OBRIGATORIO** atualizar:

1. **`sdk/client.py:_parse_sdk_message()`** — emitir `StreamEvent(type='xxx', ...)`
2. **`routes/chat.py:_process_stream_event()`** — `elif event.type == 'xxx':` → `_sse_event('xxx', ...)`
3. **`static/agente/js/chat.js`** — `case 'xxx':` no switch de SSE

**Se uma camada faltar, o evento e silenciosamente descartado.** Nao ha validacao automatica.

### Excecao R8: eventos emitidos de `can_use_tool` (raw SSE via event_queue)

`ask_user_question` (`config/permissions.py:419`) e `destructive_action_warning` (`config/permissions.py:620`) violam o contrato de 3 camadas **por design**:

- Sao emitidos de DENTRO do callback `can_use_tool` do SDK (pre-tool hook), nao durante parsing de mensagens.
- `can_use_tool` roda em thread separada, sem acesso a instancia `AgentClient` nem ao parser `_parse_sdk_message`.
- Usam `event_queue.put(f"event: {type}\ndata: {json}\n\n")` diretamente — raw SSE string via `queue.Queue` cross-thread.
- SSE generator em `routes/chat.py` dreva o `event_queue` e repassa para o frontend.
- camada 3 (chat.js case) e mantida normalmente.

**Regra**: ao adicionar novo evento emitido de `can_use_tool` ou outro callback async, usar o mesmo padrao `event_queue.put(raw_sse_string)` — NAO tentar passar por `StreamEvent` (nao ha contexto).

### Mapa de eventos (atualizado 2026-05-25)

| Evento | client.py | routes/chat.py | chat.js | Origem |
|--------|-----------|-----------|---------|--------|
| `init` | StreamEvent | _sse_event | case | Streaming paths (v2/v3) |
| `queued` | StreamEvent | _sse_event | case | Enfileiramento estilo terminal (2026-05-25) — `pooled.lock.locked()` antes de aguardar |
| `text` | StreamEvent | _sse_event | case | AssistantMessage.TextBlock |
| `thinking` | StreamEvent | _sse_event | case | AssistantMessage.ThinkingBlock |
| `tool_call` | StreamEvent | _sse_event | case | AssistantMessage.ToolUseBlock |
| `tool_result` | StreamEvent | _sse_event | case | UserMessage.ToolResultBlock |
| `todos` | StreamEvent | _sse_event | case | ToolResult (TodoWrite) — DEPRECATED SDK <= 0.1.81, mantido back-compat |
| `task_event` | StreamEvent | _sse_event | case | ToolResult (TaskCreate/TaskUpdate/TaskList) — SDK 0.2.82+ |
| `error` | StreamEvent | _sse_event | case | API errors, exceptions. `error_type` ∈ {cli_connection_error, thread_died, timeout, process_error} → frontend classifica transiente (auto-retry/aviso calmo) vs final (card ❌). Ver `_isTransientError` em chat.js (2026-05-29) |
| `interrupt_ack` | StreamEvent | _sse_event | case | ResultMessage (interrupted) |
| `task_started` | StreamEvent | _sse_event | case | TaskStartedMessage (subagente) |
| `task_progress` | StreamEvent | _sse_event | case | TaskProgressMessage (subagente) |
| `task_notification` | StreamEvent | _sse_event | case | TaskNotificationMessage (subagente) |
| `subagent_summary` | StreamEvent | _sse_event | case | SubagentStop hook (#6) |
| `subagent_validation` | StreamEvent (Redis pubsub) | _sse_event | case | validator worker (#4, fase 4) |
| `stderr` | StreamEvent | _sse_event | case | SDK stderr callback (debug, admin-only) |
| `done` | StreamEvent | _sse_event | case | ResultMessage (fim, inclui structured_output) |
| `start` | — | SSE generator | case | Inicio do SSE stream |
| `heartbeat` | — | SSE generator | case | Keep-alive 10s |
| `processing` | — | SSE generator | case | Inatividade com thread VIVA = turno em andamento (NAO "travou"). Renova deadline + indicador persistente (2026-05-29) |
| `suggestions` | — | pos-stream | case | suggestion_generator |
| `ask_user_question` | — | AskUserQuestion | case | SDK AskUserQuestion tool |
| `memory_saved` | — | hooks pos-sessao | case | Memoria salva |
| `action_pending` | — | (legacy) | case | Confirmacao pre-acao |

**Hooks SDK (8 registrados)**: PreToolUse, PostToolUse, PostToolUseFailure, PreCompact, Stop, UserPromptSubmit, SubagentStart, SubagentStop.

---

## Artifacts (2026-05-12)

Bundle.html auto-contido renderizado em modal no chat web (NAO no Teams).
Build assincrono via fila RQ `artifacts` (reutiliza `worker_render` —
prioridade logo apos `hora_nfe`).

### Componentes

| Camada | Arquivo |
|---|---|
| Modelo | `app/agente/models.py` (AgenteArtifact) |
| Migration | `scripts/migrations/2026_05_12_agente_artifacts.{py,sql}` |
| Service | `app/agente/services/artifact_service.py` |
| Worker job | `app/agente/workers/artifact_worker.py` (build_artifact_job) |
| Worker entry | Reusa `worker_render.py` (prod) e `worker_atacadao.py` (dev) — fila `artifacts` adicionada em `start_worker_render.sh` |
| Endpoints | `app/agente/routes/artifacts.py` (5 rotas: 3 publicas + 2 API: list + by-uuid/url) |
| Tool MCP | `app/agente/tools/artifact_tool.py` (build_artifact, Enhanced v1.0) |
| Skill | `.claude/skills/gerando-artifact/` (SKILL.md + scripts) |
| Frontend modal | `app/agente/templates/agente/chat.html` (#artifact-modal + #artifacts-drawer) |
| Frontend JS | `app/static/agente/js/chat.js` (secao ARTIFACTS no final) |
| Frontend CSS | `app/static/agente/css/artifact.css` |

### Fluxo

```
1. Usuario: "monte um dashboard de X"
2. Skill `gerando-artifact` orienta agente a preparar spec
3. Agente chama tool build_artifact({titulo, spec={components, dependencies?}})
4. Tool cria AgenteArtifact (status=queued) + enfileira RQ
5. Tool retorna {token, render_url, status_url, marker: "[ARTIFACT:<token>]"}
6. Agente responde texto + marker
7. Frontend (chat.js): regex detecta marker, renderiza card inline + polling
8. Worker: init-artifact.sh + escreve componentes + bundle-artifact.sh
9. Worker: upload S3 (agente/artifacts/{user_id}/{uuid}.html), status=ready
10. Frontend: card vira "Abrir visualizacao" → clique → modal com iframe sandboxed
```

### Seguranca

- Token HMAC via `itsdangerous.URLSafeTimedSerializer` (TTL 7d)
- iframe `sandbox="allow-scripts allow-forms allow-popups"` (sem `allow-same-origin`)
- CSP restritivo no /bundle endpoint
- Status/page exigem login + ownership (current_user.id == artifact.user_id)
- /bundle endpoint sem login (necessario para iframe) — auth e via token assinado
- Rate limit: 5 artifacts/user/hora (Redis)
- Limite 5MB bundle final + 200KB por arquivo componente
- Spec validada antes de salvar (path traversal bloqueado)

### Gotchas

- **Apenas chat web**: tool retorna erro se invocada fora de sessao web (Teams ignora marker)
- **V1 sem shadcn/ui**: scripts criam apenas Vite+React+TS+Tailwind. shadcn/ui em V2.
- **Node requerido**: `start_worker_render.sh` faz NVM install lazy de Node 20 se nao detectado (necessario para `npm` + Parcel no build_artifact_job). Tambem prepende `node` bin ao `PATH` exportado antes do `exec python worker_render.py` — sem isso subprocess do worker recebe PATH sem Node. Defesa em profundidade: `artifact_worker._ensure_node_in_path()` re-resolve NVM dir antes de cada subprocess.
- **Fila prioritaria**: `artifacts` esta entre `hora_nfe` (alta) e `atacadao` em `start_worker_render.sh` — usuario aguarda no chat (30-60s). NAO mover para baixa prioridade.
- **Persistencia indefinida (2026-05-12 v2)**: artifacts NAO expiram automaticamente. `expires_at` default = now + 100 anos (sem TTL efetivo). Bundle S3 mantido para sempre — sem cleanup job. Token assinado tem TTL 1 ano; usuario pode regerar via `/agente/api/artifact/by-uuid/<uuid>/url` (login + ownership). Drawer no chat (`#artifacts-drawer`) lista galeria do usuario via `/agente/api/artifacts` — clica e abre modal com bundle.
- **Anti-starvation por perfis de worker** (`worker_render.py:184+` refatorado 2026-05-12): 3 workers paralelos com responsabilidades isoladas:
  - **Worker 0 [LIGHT-RESERVED]**: pega apenas filas leves (`high, hora_nfe, artifacts, atacadao, default, agent_validation`). NUNCA pega `impostos`/`odoo_lancamento`/`recebimento`/`hora_backfill`. Garante que `hora_nfe` (operador interativo) e `artifacts` (usuario chat web) sempre tem capacidade.
  - **Worker 1 [FULL]**: pega TUDO, incluindo `impostos` (fila exclusiva). Unico worker que processa `impostos` — serializa contention no Odoo.
  - **Worker 2 [GENERAL]**: pega tudo exceto `impostos`. Absorve carga pesada nao-exclusiva.
  - Pesadas (`impostos`, `odoo_lancamento`, `recebimento`, `hora_backfill`) ficam capadas em max 2 workers; usuario interativo nunca espera build/Odoo terminar.
- **Rate limit atomico**: `artifact_service.check_rate_limit` usa pipeline MULTI/EXEC (SET NX+EX + INCR) para evitar race condition INCR+EXPIRE que poderia deixar contador permanente (sem TTL).
- **S3 obrigatorio**: bundle.html grande demais para DB. USE_S3=true obrigatorio em prod.

---

## Telemetria per-invocacao de subagent (A1+A2+A3, 2026-05-16)

Roadmap **Fase A — Instrumentacao**: baseline numerico per-agent antes de
qualquer otimizacao (B/C/D). UMA linha por spawn->stop em tabela dedicada,
distinta de `agent_session_costs` (per-message do CostTracker).

### Componentes

| Camada | Arquivo |
|---|---|
| Modelo | `app/agente/models.py:AgentInvocationMetric` |
| Migration | `scripts/migrations/2026_05_16_agent_invocation_metrics.{py,sql}` |
| Hook prod (Web + Teams) | `app/agente/sdk/hooks.py:_subagent_stop_hook` (bloco A1, linha ~864) |
| Hook dev (Claude Code CLI) | `.claude/hooks/agent_metrics_dev_hook.py` (PostToolUse matcher=Agent) |
| Ingestor dev -> tabela | `scripts/migrations/2026_05_16_agent_invocation_metrics_dev_ingestor.py` |
| Service dashboard | `app/agente/services/metrics_dashboard_service.py` |
| Routes | `app/agente/routes/admin_metrics.py` (10 endpoints) |
| Template | `app/agente/templates/agente/admin_metrics.html` (Chart.js 3.9.1) |
| Link menu | `app/templates/base.html` -> `agente.admin_metrics_page` (admin only) |

### Fluxo

```
Web/Teams subagent stop
  -> SubagentStop hook (mesmo factory build_hooks(), get_client() singleton)
  -> A1: extrai cost/duration/tokens via last_result.usage OU
         _compute_subagent_metadata_from_jsonl(transcript_path)
  -> AgentInvocationMetric.insert_metric(...) SAVEPOINT pattern
  -> persiste source='production'

Claude Code CLI Agent tool stop
  -> .claude/hooks/agent_metrics_dev_hook.py (PostToolUse stdin payload)
  -> append /tmp/agent_invocation_metrics_dev/{YYYY-MM-DD}.jsonl
  -> manual: python scripts/migrations/2026_05_16_..._dev_ingestor.py
  -> persiste source='dev' (agent_id determinstico via SHA256)

Dashboard
  -> GET /agente/admin/metrics (admin only)
  -> 10 endpoints JSON com filtros (period, source, agent_types, user_ids)
```

### Feature flags

| Flag | Default | Efeito |
|---|---|---|
| `AGENT_INVOCATION_METRICS_PERSIST` | `true` | Hook A1 persiste em `agent_invocation_metrics` |
| `USE_SUBAGENT_COST_GRANULAR` | (separado) | Persiste em `AgentSession.data->subagent_costs` (JSONB) — paralelo, NAO substitui A1 |

### Gotchas

- **BRIDGE FIX (2026-05-16)**: subagent SDK 0.1.60+ NAO emite `type:'result'` no transcript JSONL.
  Path original do hook (`hooks.py:518-522`) deixa `cost_usd=None`, `duration_ms=None`,
  `num_turns=None`. O bloco A1 (linha ~890+) AGORA sobrescreve essas variaveis com valores
  computados via `_compute_subagent_metadata_from_jsonl` quando `last_result` ausente.
  **Sem esse bridge, dashboard zera KPIs e anomaly detection nao funciona** (observado em PROD).
- **COMMIT GUARD (2026-05-16)**: `db.session.commit()` em A1 so executa quando hook criou
  app_context novo (`_a1_owns_ctx=True`). Em request Flask (`nullcontext`), commit explicito
  flusharia writes pendentes — SAVEPOINT do `insert_metric` ja garante isolamento, o request
  final consolida. Mesma logica documentada em `AgentInvocationMetric.insert_metric:1683-1693`.
- **Hook dev sem transcript**: Claude Code CLI nao expoe `agent_transcript_path` via
  PostToolUse, entao `cache_read/cache_create` ficam 0 e `num_turns` NULL nas linhas dev.
  Tokens (`input_tokens`/`output_tokens`) vem do `tool_response.usage` do payload do hook.
- **agent_id determinstico (dev)**: ingestor gera `dev_<sha256[:24]>` de `(timestamp, session_id,
  agent_type, tokens)` — mesma linha JSONL gera mesmo agent_id. Permite reingestao sem dup.
- **Teams + Web compartilham hook**: `get_client()` singleton -> `build_hooks()` factory unica.
  Bug ou feature em `_subagent_stop_hook` afeta os dois canais.
- **Backfill Fase D**: `escalated_to_human` (default false) e `user_correction_received`
  (default NULL) ficam para D (loop fechado). NAO usar em queries antes da Fase D.
- **source=`dev`|`production`**: separa uso real (Rafael+equipe via web/Teams) de
  desenvolvimento (Rafael em Claude Code CLI). Dashboard tem toggle (T2).

### Roadmap (Fase A em curso)

| Item | Status |
|---|---|
| A1 — Migration + model | ✅ aplicada PROD 2026-05-16 |
| A2 — Hook prod + dev | ✅ ativo (flag default ON) |
| A3 — Dashboard admin | ✅ funcional, requer fix bridge para nao-zerar |
| A3+ — Ingestor dev | ✅ manual (Fase A nao exige cron) |
| A4/A5 — Coleta 14d + baseline | em coleta |

Apos baseline numerico estavel: prosseguir para **Fase B (Quality)**.

---

## Memoria Compartilhada (PRD v2.1)

### Conceito
- **Memorias pessoais** (`escopo='pessoal'`): pertencentes a um user_id, comportamento original
- **Memorias empresa** (`escopo='empresa'`): pertencentes a user_id=0 (Sistema), visiveis para todos
- Paths `/memories/empresa/*` automaticamente salvos com user_id=0

### Tabela usuarios: id=0 = "Sistema"
- Perfil `sistema`, email `sistema@nacom.com.br`, senha `NOLOGIN`
- Migration: `scripts/migrations/memoria_compartilhada_escopo.py`

### Colunas adicionadas em agent_memories
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `escopo` | VARCHAR(20) DEFAULT 'pessoal' | 'pessoal' ou 'empresa' |
| `created_by` | INTEGER nullable FK usuarios.id | Quem originou (auditoria) |

### Busca inclui user_id=0
- `service.py:_search_pgvector_memories()` → `WHERE user_id = ANY([user_id, 0])`
- `service.py:_search_fallback_memories()` → `.filter(user_id.in_([user_id, 0]))`
- `client.py` fallback recencia → `.filter(user_id.in_([user_id, 0]))`
- `knowledge_graph_service.py:query_graph_memories()` → `WHERE user_id = ANY([user_id, 0])`

### Extracao pos-sessao
- `pattern_analyzer.py:extrair_conhecimento_sessao()` — via Sonnet em daemon thread (background)
- Contexto: TODAS as mensagens da sessao (trunca per-msg a 3K chars, safety cap 40K chars)
- Categorias: term_definitions, role_identifications, business_rules, corrections
- Trigger: routes/_helpers.py a cada exchange (min 3 msgs, flag `USE_POST_SESSION_EXTRACTION`)
- Custo: ~$0.003 por execucao (Sonnet, volume baixo ~4 sessoes/dia)

### Role Awareness
- system_prompt.md secao `<role_awareness>` instrui agente a salvar PROATIVAMENTE
- Paths empresa: termos/, regras/, usuarios/, correcoes/
- Complementar a extracao pos-sessao (rede de seguranca)

---

## Versao SDK atual

- **claude-agent-sdk**: `0.2.87` | **CLI bundled**: 2.1.150 | **anthropic**: `0.98.1`
- **Task* tools** (SDK 0.2.82+): TodoWrite substituido por `TaskCreate`/`TaskUpdate`/`TaskGet`/`TaskList`.
  Emit via `task_event` SSE (3 actions: created/updated/snapshot). Orientacao em `system_prompt.md`
  bloco `<task_management>`. Parser em `client.py:_build_task_event` (Nacom) e
  `agente_lojas/sdk/client.py:_build_task_event_from_result` (Lojas, detecta por regex no output).
- **Floor**: `mcp>=1.19.0` (fix `CallToolResult` silenciosamente perdido em 0.1.70)
- **Modelo default**: `claude-opus-4-8` (Opus 4.8, $5/$25 per MTok, adaptive thinking, 1M context)
- **Rollback rapido**: `AGENT_MODEL=claude-opus-4-7` + `TEAMS_DEFAULT_MODEL=claude-opus-4-7` (ou `claude-opus-4-6`)
- **SessionStore**: `PostgresSessionStore` source-of-truth (Fase B cutover 2026-04-21)
  - Tabela `claude_session_store`, flag `AGENT_SDK_SESSION_STORE_ENABLED` default ON
  - Pool asyncpg LAZY per-worker, min=1/max=3
  - **Flush mode** (SDK 0.1.73): `AGENT_SDK_SESSION_STORE_FLUSH` env var (`batched`|`eager`),
    default `batched`. Eager habilita live-tailing/crash-durability mas exige profiling antes
    (impacto pool DB). Ver `SDK_CHANGELOG.md` para criterios de ativacao.
- **Thinking display**: toggle per-user via `Usuario.preferences['agent_thinking_display']`
  - Default global `AGENT_THINKING_DISPLAY=omitted`
- **Refusal observability**: `stop_details` estruturado (anthropic 0.88.0+) propagado em
  `StreamEvent('done').content['stop_details']` e SSE `done_payload`. Logado como WARNING
  quando `category` (`cyber`/`bio`) preenchido.
- **Erro Anthropic granular**: `APIStatusError.type` adotado em `app/scanner/service.py` e
  `app/agente/services/memory_consolidator.py` para classificacao por tipo
  (`rate_limit_error`, `overloaded_error`, `billing_error`, etc.).
- **API error HTTP status** (SDK 0.1.76): `ResultMessage.api_error_status` capturado em
  `client.py`, propagado em `StreamEvent('done').content['api_error_status']` e SSE
  `done_payload`. Sentry tag `anthropic_http_status` (e `anthropic_http_5xx=true` quando
  >= 500) para classificar 429/500/529 sem inspecao de string em `errors[]`.
- **Effort xhigh per-subagente** (SDK 0.1.74): 7 subagentes Opus pesados (`analista-carteira`,
  `auditor-financeiro`, `desenvolvedor-integracao-odoo`, `especialista-odoo`,
  `gestor-recebimento`, `gestor-motos-assai`, `raio-x-pedido`) marcados `effort: xhigh` no
  frontmatter. `agent_loader.py` parseia com forward-compat (`_SDK_HAS_EFFORT_FIELD`
  introspection). Sonnet ignorado (xhigh fallback para high = no-op).
- **`skills` option** (SDK 0.1.77, deprecou `"Skill"` em allowed_tools): `agente_lojas`
  passa `skills=sorted(SKILLS_PERMITIDAS)` (filtro real do listing — defesa em
  profundidade do contrato HORA); `agente` Nacom passa `skills="all"` (centralizacao).
  Forward-compat via `_SDK_HAS_OPTIONS_SKILLS` (introspection).
- **Actionable error messages** (SDK 0.1.77): `ProcessError` carrega texto real do
  CLI (ex: "Reached maximum number of turns") em vez de generico "exit code 1".
  Adocao gratis via upgrade.

> **Historico completo de adocoes, breaking changes, bug fixes e features NAO adotadas**:
> ver `SDK_CHANGELOG.md` (changelog 0.1.49 → 0.2.87 + anthropic 0.85 → 0.98.1 com fluxos detalhados, gotchas e arquitetura).

---

## Export critico: Teams

`app/teams/` importa de **6 sub-modulos**: permissions, models, SDK client, flags, session_persistence, pending_questions.

**Qualquer mudanca em permissions.py, models.py, client.py, feature_flags.py, session_persistence.py ou pending_questions.py DEVE ser testada no Teams bot.**
