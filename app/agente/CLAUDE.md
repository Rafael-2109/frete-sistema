# Agente Logistico Web — Guia de Desenvolvimento

**LOC**: ~20.7K | **Arquivos**: 41 | **Atualizado**: 08/03/2026

Wrapper do Claude Agent SDK: chat web (SSE) + Teams bot (async).

---

## Estrutura

```
app/agente/                          # Root — 5 arquivos
├── __init__.py                      # Blueprint registration
├── CLAUDE.md                        # Este arquivo (guia dev)
├── historia.md                      # Referencia historica (legado, 76K)
├── models.py                        # SQLAlchemy models (AgentSession, AgentMemory, etc.)
├── routes.py                        # Flask routes + SSE streaming
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
├── prompts/                         # Prompts do agente web — 2 arquivos
│   ├── __init__.py
│   └── system_prompt.md             # System prompt do agente (usuarios finais)
├── sdk/                             # Integracao com Claude Agent SDK — 6 arquivos
│   ├── __init__.py
│   ├── client.py                    # Client principal (streaming, hooks, prompt injection)
│   ├── client_pool.py               # Pool de clients reutilizaveis
│   ├── cost_tracker.py              # Rastreamento de custos por sessao
│   ├── pending_questions.py         # AskUserQuestion (dual event: sync + async)
│   └── session_persistence.py       # Persistencia JSONL de sessoes SDK
├── services/                        # Servicos de inteligencia — 13 arquivos (ver services/CLAUDE.md)
│   ├── __init__.py
│   ├── CLAUDE.md                    # Sub-guia com regras R1-R5 dos services
│   ├── friction_analyzer.py         # Analise de friccao de uso
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
└── tools/                           # MCP tools (NAO callables) — 9 arquivos
    ├── __init__.py
    ├── _mcp_enhanced.py             # Wrapper Enhanced (outputSchema + structuredContent)
    ├── memory_mcp_tool.py           # 11 operacoes de memoria
    ├── playwright_mcp_tool.py       # Browser automation (13 tools, SSW + Atacadao)
    ├── render_logs_tool.py          # Consulta logs Render
    ├── routes_search_tool.py        # Busca em rotas Flask
    ├── schema_mcp_tool.py           # Consulta schemas de tabelas
    ├── session_search_tool.py       # 4 operacoes de busca em sessoes
    └── text_to_sql_tool.py          # Text-to-SQL (Enhanced v2.0.0)
```

---

## Regras Criticas

### R1: Dois IDs de sessao — NUNCA confundir
- `session_id` (nosso UUID) → persistencia no banco (`AgentSession.session_id`)
- `sdk_session_id` (efemero do CLI) → armazenado em `data['sdk_session_id']` (JSONB, NAO coluna)
- **Resume** usa `sdk_session_id` (CLI carrega sessao do disco)
- **Banco** usa `session_id` (nosso controle, FK em queries)
- Confundir os dois causa sessao perdida ou mensagens em sessao errada
- `sdk_session_transcript` e TEXT separado (ate 1GB), NAO JSONB — decisao de performance
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
Fluxo cruza 3 arquivos: `pending_questions.py` → `permissions.py` → `routes.py`
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
- SQL tool ja migrada (v2.0.0). Demais tools usam `@tool` + `create_sdk_mcp_server` (standard)
- Ref completa: `.claude/references/MCP_CAPABILITIES_2026.md`

### R7: JSONB — flag_modified
Manter o padrao existente em `models.py`: SEMPRE `flag_modified(session, 'data')` apos modificar JSONB.

---

## Hierarquia de Timeouts

Timeouts em 4 arquivos com **deadline renewal**. DEVEM respeitar esta ordem ou causam cascata de falhas:

| Timeout | Valor | Fonte | Funcao |
|---------|-------|-------|--------|
| Heartbeat SSE | 10s | `routes.py:68` | Keep-alive para proxy |
| AskUser web | 55s | `pending_questions.py:30` | Espera resposta do usuario |
| AskUser Teams | 120s | `feature_flags.py` | Idem, via Adaptive Card |
| **Web inatividade** | 240s | `routes.py:78` | Renovavel a cada evento real (heartbeats NAO renovam) |
| **Teams inatividade** | 240s | `services.py:848` | Renovavel a cada chunk recebido |
| SDK stream_close | 240s | `client.py:547` | Timeout CLI hooks/MCP |
| Web teto absoluto | 540s | `routes.py:77` | Teto absoluto SSE (Render 600s limit) |
| Teams teto absoluto | 600s | `services.py:849` | Teto absoluto Teams |
| Render hard limit | 600s | infra | Request timeout do servidor |

**Deadline renewal**: operacoes longas com progresso continuo NAO sao mais mortas pelo timeout fixo. A cada chunk/evento recebido, o deadline de inatividade (120s) e renovado. Apenas inatividade real (2 min sem progresso) ou teto absoluto disparam timeout.

**REGRA**: `USER_RESPONSE_TIMEOUT` (55s) DEVE ser < timeout do SDK (240s). Se >= SDK, o CLI mata o stream antes do usuario responder.

---

## Gotchas

### system_prompt.md vs CLAUDE.md
`prompts/system_prompt.md` = prompt do agente web (usuarios finais). Este arquivo = Claude Code (dev). NUNCA misturar.

### SDK max_buffer_size: 10MB
`client.py:561` configura `max_buffer_size=10_000_000` (10MB). Default do SDK e 1MB — insuficiente para screenshots base64 (PNG full-page: 1.3-2.6MB). Se reduzir abaixo de 2MB, browser_screenshot volta a crashar com "JSON message exceeded maximum buffer size".

### Screenshot compression: 750KB limit
`playwright_mcp_tool.py:516` comprime PNG → JPEG (quality 80%) se > 750KB. Escalonamento: JPEG 80% → resize 50% → resize 25%. PNG original salvo em disco (URL funciona). Requer Pillow (`pillow` no requirements.txt).

### Prerequisitos de execucao
1. **`set_current_user_id()` ANTES do stream** — MCP tools (`memory_mcp_tool.py:33`, `session_search_tool.py:25`) usam `ContextVar` independentes. Se esquecer: `RuntimeError("user_id nao definido")`. CADA tool tem seu PROPRIO ContextVar.
2. **`get_or_create()` NAO e atomico** (`models.py:380-395`) — query + insert separados, sem `SELECT FOR UPDATE`. Duas threads podem criar sessao duplicada → `IntegrityError`. NUNCA assumir retorno valido sem try/except.
3. **Cascade delete** — `models.py` define `cascade='all, delete-orphan'` nos backrefs (linhas 79, 469, 689). `db.session.query(Model).filter_by(...).delete()` NAO dispara cascade → orphans. DEVE usar `db.session.delete(obj)`.

### Arquivos legados — NAO usar, NAO estender
| Arquivo | Status |
|---------|--------|
| `historia.md` (76K) | Apenas referencia historica |

### Services (12 arquivos, 5.8K LOC)
Guia completo de regras, gotchas e interdependencias: **`services/CLAUDE.md`**
Todos controlados por feature flags em `config/feature_flags.py`.

### MCP Tools de memoria (memory_mcp_tool.py v1.3.0, 11 operacoes)
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

**Admin (debug mode)**: TODAS as 11 tools aceitam `target_user_id=N` para acesso cross-user.
Validacao: `_resolve_user_id(args)` — requer `get_debug_mode() == True`. Todo acesso logado.

### MCP Tools de sessao (session_search_tool.py v3.0.0, 4 operacoes)
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
2. **`routes.py:_process_stream_event()`** — `elif event.type == 'xxx':` → `_sse_event('xxx', ...)`
3. **`static/agente/js/chat.js`** — `case 'xxx':` no switch de SSE

**Se uma camada faltar, o evento e silenciosamente descartado.** Nao ha validacao automatica.

### Mapa de eventos (atualizado 2026-03-15)

| Evento | client.py | routes.py | chat.js | Origem |
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
| `done` | StreamEvent | _sse_event | case | ResultMessage (fim) |
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
- Trigger: routes.py a cada exchange (min 3 msgs, flag `USE_POST_SESSION_EXTRACTION`)
- Custo: ~$0.003 por execucao (Sonnet, volume baixo ~4 sessoes/dia)

### Role Awareness
- system_prompt.md secao `<role_awareness>` instrui agente a salvar PROATIVAMENTE
- Paths empresa: termos/, regras/, usuarios/, correcoes/
- Complementar a extracao pos-sessao (rede de seguranca)

---

## SDK 0.1.48 (CLI 2.1.71)

**Versao**: `claude-agent-sdk==0.1.48` (atualizado 2026-03-08)

### Features adotadas:
- **`ResultMessage.stop_reason`**: Populado automaticamente no StreamEvent `done` e logado. Valores: `"end_turn"`, `"max_turns"`, `"budget_exceeded"`, etc.
- **Task messages** (`TaskStartedMessage`, `TaskProgressMessage`, `TaskNotificationMessage`): Emitidos como SSE events `task_started`/`task_progress` para observabilidade de subagentes. Import com fallback (`_HAS_TASK_MESSAGES`).
- **`agent_id`/`agent_type` em hooks**: `PostToolUseHookInput` (opcionais). Logados no `[AUDIT] PostToolUse`. **NAO disponivel** em `StopHookInput`.
- **`effort` field nativo**: `ClaudeAgentOptions.effort` (Literal["low"|"medium"|"high"|"max"]) — substituiu `max_thinking_tokens` (deprecated)
- **Fix `input_json_delta` streaming** (#644): Corrige parsing de tool use delta events

### Memory leak fixes do CLI 2.1.69+:
- Fix: old message arrays acumulando (~35MB/1000 turns)
- Fix: bridge polling loop, hook events, teammates leaks
- Fix: API 400 errors em forked agents
- Baseline memory ~16MB

---

## Export critico: Teams

`app/teams/` importa de **6 sub-modulos**: permissions, models, SDK client, flags, session_persistence, pending_questions.

**Qualquer mudanca em permissions.py, models.py, client.py, feature_flags.py, session_persistence.py ou pending_questions.py DEVE ser testada no Teams bot.**
