# Agente Logistico Web — Guia de Desenvolvimento

**LOC**: ~33.3K | **Arquivos**: 67 | **Atualizado**: 20/04/2026

Wrapper do Claude Agent SDK: chat web (SSE) + Teams bot (async).

---

## Estrutura

```
app/agente/                          # Root ��� 4 arquivos
├── __init__.py                      # Blueprint import de routes/ + init_app()
├── CLAUDE.md                        # Este arquivo (guia dev)
├── historia.md                      # Referencia historica (legado, 76K)
├── models.py                        # SQLAlchemy models (AgentSession, AgentMemory, etc.)
├── routes/                          # Flask routes modularizadas — 17 arquivos
│   ├── __init__.py                  # agente_bp + imports sub-modulos + re-exports Teams
│   ├── _constants.py                # Constantes (timeouts, thresholds, upload)
│   ├── _helpers.py                  # Helpers compartilhados (Teams + cross-module)
│   ├── chat.py                      # Core SSE: api_chat, streaming, interrupt, user_answer
│   ├── sessions.py                  # CRUD sessoes: list, messages, delete, rename, summaries
│   ├── admin_learning.py            # Admin: session messages, generate/save correction
│   ├── admin_subagents.py           # Admin forense: list/messages + smoketest (SDK 0.1.60 fase 2)
│   ├── subagents.py                 # API UI-inline: summary/messages lazy-fetch
│   ├── files.py                     # Upload/download/list/delete + helpers arquivo
│   ├── health.py                    # api_health com cache
│   ├── feedback.py                  # api_feedback 4 tipos
│   ├── insights.py                  # pagina_insights + APIs dados
│   ├── intelligence_report.py       # D7 cron bridge, csrf.exempt
│   ├── improvement_dialogue.py      # D8 cron bridge + admin, csrf.exempt
│   ├── memories.py                  # CRUD memorias + users + review
│   ├── briefing.py                  # api_get_briefing
│   └── _deprecated.py              # Scaffolding async migration (quarentena)
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
├── prompts/                         # Prompts do agente web — 3 arquivos
│   ├── __init__.py
│   ├── preset_operacional.md        # Preset customizado (substitui claude_code preset)
│   └── system_prompt.md             # System prompt do agente (usuarios finais)
├── sdk/                             # Integracao com Claude Agent SDK — 14 arquivos
│   ├── __init__.py
│   ├── _sanitization.py             # Helpers de sanitizacao PII cross-modulo
│   ├── client.py                    # Client principal (streaming, build_options, parse)
│   ├── client_pool.py               # Pool de clients reutilizaveis
│   ├── cost_tracker.py              # Rastreamento de custos por sessao
│   ├── hooks.py                     # 8 SDK hook closures (build_hooks() factory)
│   ├── memory_injection.py          # Pipeline multi-tier de injecao de memorias
│   ├── memory_injection_rules.py    # Regras declarativas de injecao (paths + filtros)
│   ├── pending_questions.py         # AskUserQuestion (dual event: sync + async)
│   ├── pricing.py                   # Tabela precos por modelo (input/output/cache_creation/cache_read)
│   ├── session_archive.py           # Archive tar.gz S3 de sessoes expiradas
│   ├── session_persistence.py       # Persistencia JSONL de sessoes SDK
│   ├── stream_parser.py             # Dataclasses + classificacao de erros de tool
│   └── subagent_reader.py           # Wrapper list_subagents + get_subagent_messages (SDK 0.1.60)
├── services/                        # Servicos de inteligencia — 14 arquivos (ver services/CLAUDE.md)
│   ├── __init__.py
│   ├── CLAUDE.md                    # Sub-guia com regras R1-R5 dos services
│   ├── _utils.py                    # Helpers compartilhados (parse_llm_json_response)
│   ├── friction_analyzer.py         # Analise de friccao de uso
│   ├── improvement_suggester.py     # Dialogo D8 melhoria (batch + real-time)
│   ├── insights_service.py          # Gerador de insights pos-sessao
│   ├── intersession_briefing.py     # Briefing entre sessoes
│   ├── knowledge_graph_service.py   # Grafo de conhecimento (memorias)
│   ├── memory_consolidator.py       # Consolidacao de memorias redundantes
│   ├── pattern_analyzer.py          # Extracao de padroes e conhecimento
│   ├── recommendations_engine.py    # Motor de recomendacoes
│   ├── sentiment_detector.py        # Deteccao de sentimento
│   ├── session_summarizer.py        # Resumo automatico de sessoes
│   ├── suggestion_generator.py      # Gerador de sugestoes proativas
│   └── tool_skill_mapper.py         # Mapeamento tool → skill
├── templates/agente/                # Templates Jinja2 — 2 arquivos
│   ├── chat.html                    # Interface de chat web
│   └── insights.html                # Dashboard de insights
├── tools/                           # MCP tools (NAO callables) — 9 arquivos
│   ├── __init__.py
│   ├── _mcp_enhanced.py             # Wrapper Enhanced (outputSchema + structuredContent)
│   ├── memory_mcp_tool.py           # 12 operacoes de memoria (Enhanced v2.1.0)
│   ├── playwright_mcp_tool.py       # Browser automation (13 tools, SSW + Atacadao)
│   ├── render_logs_tool.py          # Consulta logs Render
│   ├── routes_search_tool.py        # Busca em rotas Flask
│   ├── schema_mcp_tool.py           # Consulta schemas de tabelas
│   ├── session_search_tool.py       # 4 operacoes de busca em sessoes (Enhanced v4.0.0)
│   └── text_to_sql_tool.py          # Text-to-SQL (Enhanced v2.0.0)
├── utils/                           # Helpers de modulo — 2 arquivos
│   └── pii_masker.py                # Mascaramento regex CPF/CNPJ/email (SDK 0.1.60 fase 2)
└── workers/                         # Workers RQ locais — 2 arquivos
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
| Inatividade (renewal) | 240s | Renovavel a cada evento/chunk — timeout se parar de emitir |
| Stream max | 540s (web) / 600s (teams) | Teto absoluto do streaming |
| None sentinel | finally | Garante que SSE generator termina |

NUNCA remover o `yield None` no `finally` do generator — frontend trava esperando eventos.

**`streaming_done_event`** (`client.py:2627`): `asyncio.Event()` que controla o prompt generator. Se NAO chamar `.set()` em QUALQUER error path, o generator fica preso em `done_event.wait(timeout=600)` → processo zombie por 10min. Chamado em 6 locais nos except handlers + 1 bloco `finally` como rede de seguranca.

**DC-8 (CancelledError bypass)**: `asyncio.CancelledError` e `BaseException` (NAO `Exception`) desde Python 3.9. Teams usa `asyncio.wait_for(timeout=chunk_timeout)` per-chunk que cancela via `CancelledError` — bypassa TODOS os 5 except handlers. O bloco `finally` em `_stream_response()` garante que `streaming_done_event.set()` SEMPRE e chamado, mesmo para `CancelledError`, `KeyboardInterrupt` e `SystemExit`. **O path persistente (`_stream_response_persistent`) e IMUNE porque `streaming_done_event = None`.**

**REGRA**: Ao adicionar NOVO error handler em `_stream_response()`, o `finally` block e a rede de seguranca definitiva — NAO precisa chamar `.set()` no novo handler (mas e boa pratica como defense-in-depth).

### R4: AskUserQuestion — blocking cross-arquivo
Fluxo cruza 3 arquivos: `pending_questions.py` → `permissions.py` → `routes/chat.py`
- Web: event_queue SSE → frontend responde → POST `/api/user-answer` → Event.set()
- Teams: TeamsTask.status='awaiting_user_input' → Adaptive Card → POST resposta → Event.set()
- Timeout web: 55s. Timeout Teams: 120s (`TEAMS_ASK_USER_TIMEOUT`)

Alterar um arquivo sem verificar os outros 2 quebra o fluxo silenciosamente.

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

---

## Hierarquia de Timeouts

Timeouts em 4 arquivos com **deadline renewal**. DEVEM respeitar esta ordem ou causam cascata de falhas:

| Timeout | Valor | Fonte | Funcao |
|---------|-------|-------|--------|
| Heartbeat SSE | 10s | `routes/_constants.py` | Keep-alive para proxy |
| AskUser web | 55s | `pending_questions.py:30` | Espera resposta do usuario |
| AskUser Teams | 120s | `feature_flags.py` | Idem, via Adaptive Card |
| **Web inatividade** | 240s | `routes/_constants.py` | Renovavel a cada evento real (heartbeats NAO renovam) |
| **Teams inatividade** | 240s | `services.py:848` | Renovavel a cada chunk recebido |
| SDK stream_close | 240s | `client.py:547` | Timeout CLI hooks/MCP |
| Job `validate_subagent_output` | 60s | `hooks.py:SubagentStop enqueue` | Timeout RQ para validacao Haiku |
| Web teto absoluto | 540s | `routes/_constants.py` | Teto absoluto SSE (margem 60s vs Render) |
| Teams teto absoluto | 600s | `services.py:849` | Teto absoluto Teams |
| Gunicorn timeout | 600s | `start_render.sh` gunicorn_config | Per-request heartbeat gthread (= Render) |
| Render hard limit | 600s | infra | Request timeout do servidor |

**Deadline renewal**: operacoes longas com progresso continuo NAO sao mais mortas pelo timeout fixo. A cada chunk/evento recebido, o deadline de inatividade (120s) e renovado. Apenas inatividade real (2 min sem progresso) ou teto absoluto disparam timeout.

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

### Services (14 arquivos, ~8.6K LOC)
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

### Mapa de eventos (atualizado 2026-04-01)

| Evento | client.py | routes/chat.py | chat.js | Origem |
|--------|-----------|-----------|---------|--------|
| `init` | StreamEvent | _sse_event | case | Streaming paths (v2/v3) |
| `text` | StreamEvent | _sse_event | case | AssistantMessage.TextBlock |
| `thinking` | StreamEvent | _sse_event | case | AssistantMessage.ThinkingBlock |
| `tool_call` | StreamEvent | _sse_event | case | AssistantMessage.ToolUseBlock |
| `tool_result` | StreamEvent | _sse_event | case | UserMessage.ToolResultBlock |
| `todos` | StreamEvent | _sse_event | case | ToolResult (TodoWrite) |
| `error` | StreamEvent | _sse_event | case | API errors, exceptions |
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
| `suggestions` | — | pos-stream | case | suggestion_generator |
| `ask_user_question` | — | AskUserQuestion | case | SDK AskUserQuestion tool |
| `memory_saved` | — | hooks pos-sessao | case | Memoria salva |
| `action_pending` | — | (legacy) | case | Confirmacao pre-acao |

**Hooks SDK (8 registrados)**: PreToolUse, PostToolUse, PostToolUseFailure, PreCompact, Stop, UserPromptSubmit, SubagentStart, SubagentStop.

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

## Export critico: Teams

`app/teams/` importa de **6 sub-modulos**: permissions, models, SDK client, flags, session_persistence, pending_questions.

**Qualquer mudanca em permissions.py, models.py, client.py, feature_flags.py, session_persistence.py ou pending_questions.py DEVE ser testada no Teams bot.**
