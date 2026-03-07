# Agente Logistico Web — Guia de Desenvolvimento

**LOC**: ~15.4K | **Arquivos**: 35 | **Atualizado**: 27/02/2026

Wrapper do Claude Agent SDK: chat web (SSE) + Teams bot (async).

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

### R3: Thread-safety — 3 mecanismos distintos
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

### R5: Stream safety — None sentinel + done_event
| Camada | Timeout | Funcao |
|--------|---------|--------|
| Heartbeat SSE | 10s | Evita proxy/Render matar conexao idle |
| SDK inactivity | 240s | Timeout se CLI para de emitir |
| Stream max | 540s | Teto absoluto do streaming |
| None sentinel | finally | Garante que SSE generator termina |

NUNCA remover o `yield None` no `finally` do generator — frontend trava esperando eventos.

**`streaming_done_event`** (`client.py:1319`): `asyncio.Event()` que controla o prompt generator. Se NAO chamar `.set()` em QUALQUER error path, o generator fica preso em `done_event.wait(timeout=600)` → processo zombie por 10min. Chamado em 6 locais: ResultMessage (1617), ProcessError (1674), CLINotFoundError (1695), CLIJSONDecodeError (1716), BaseExceptionGroup (1773), Generic Exception (1820). **Ao adicionar NOVO error handler em `_stream_response()`, DEVE chamar `streaming_done_event.set()`.**

### AskUserQuestion: blocking cross-arquivo
Fluxo cruza 3 arquivos: `pending_questions.py` → `permissions.py` → `routes.py`
- Web: event_queue SSE → frontend responde → POST `/api/user-answer` → Event.set()
- Teams: TeamsTask.status='awaiting_user_input' → Adaptive Card → POST resposta → Event.set()
- Timeout web: 55s. Timeout Teams: 120s (`TEAMS_ASK_USER_TIMEOUT`)

Alterar um arquivo sem verificar os outros 2 quebra o fluxo silenciosamente.

### MCP tools: NAO callable
Tools em `tools/` sao registros MCP (ToolAnnotations). O agente usa `mcp__X__Y` diretamente.
NUNCA importar e chamar como funcao Python — nao sao callables, gera erro silencioso.

### MCP Enhanced Wrapper
`tools/_mcp_enhanced.py` adiciona `outputSchema` + `structuredContent` (MCP spec 2025-06-18).
- Usar `@enhanced_tool` + `create_enhanced_mcp_server` para tools que precisam de structured output
- SQL tool ja migrada (v2.0.0). Demais tools usam `@tool` + `create_sdk_mcp_server` (standard)
- Ref completa: `.claude/references/MCP_CAPABILITIES_2026.md`

### JSONB: flag_modified
Manter o padrao existente em `models.py`: SEMPRE `flag_modified(session, 'data')` apos modificar JSONB.

---

## Hierarquia de Timeouts

Seis timeouts em 4 arquivos. **DEVEM respeitar esta ordem** ou causam cascata de falhas:

| Timeout | Valor | Fonte | Funcao |
|---------|-------|-------|--------|
| Heartbeat SSE | 10s | `routes.py:68` | Keep-alive para proxy |
| AskUser web | 55s | `pending_questions.py:30` | Espera resposta do usuario |
| AskUser Teams | 120s | `feature_flags.py` | Idem, via Adaptive Card |
| SDK stream_close | 240s | `client.py:547` | Timeout CLI hooks/MCP |
| Stream max | 540s | `routes.py:75` | Teto absoluto SSE |
| Render hard limit | 600s | infra | Request timeout do servidor |

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

### Services opcionais (ativos, controlados por flag)
| Service | Flag | Default | O que faz |
|---------|------|---------|-----------|
| `services/pattern_analyzer.py` | `USE_PATTERN_LEARNING` | `true` | Analisa sessoes via Sonnet — gera patterns PRESCRITIVOS (error_patterns, anti_patterns, entity_defaults) em `/memories/learned/patterns.xml`. Input: sessoes + memorias com correction_count>0 |
| `services/sentiment_detector.py` | `USE_SENTIMENT_DETECTION` | `false` | Detecta frustracao via regex, injeta instrucao de tom. Zero custo API |
| `services/memory_consolidator.py` | `USE_MEMORY_CONSOLIDATION` | `true` | Consolida memorias redundantes via Sonnet quando >15 arquivos ou >6000 chars. Custo ~$0.006. 395 LOC |
| `services/knowledge_graph_service.py` | `MEMORY_KNOWLEDGE_GRAPH` | `true` | Extrai entidades + relacoes de memorias (3 layers: regex/Voyage/Sonnet). Query multi-hop. 806 LOC. `strip_xml_tags()` exportada para uso externo |
| (routes.py + pattern_analyzer.py) | `USE_POST_SESSION_EXTRACTION` | `true` | Extrai conhecimento organizacional pos-sessao via Sonnet (background). Salva termos/cargos/regras como memorias empresa (user_id=0). Trigger: a cada exchange (min 3 msgs) |
| `services/insights_service.py` | `USE_AGENT_INSIGHTS` | `true` | Metricas de memoria (utilization, decay, orphans). Endpoint `/insights/memory`. 841 LOC |
| `services/intersession_briefing.py` | `USE_COMMIT_BRIEFING` | `true` | Injeta commits recentes (git log -5) no briefing inter-sessao. Custo zero |
| (client.py) | `PENDENCIA_TTL_DAYS` | `7` | Pendencias de sessoes mais antigas que N dias sao auto-removidas |

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

## SDK 0.1.46 (CLI 2.1.69)

**Versao**: `claude-agent-sdk==0.1.46` (atualizado 2026-03-05)

### Features adotadas:
- **`ResultMessage.stop_reason`**: Populado automaticamente no StreamEvent `done` e logado. Valores: `"end_turn"`, `"max_turns"`, `"budget_exceeded"`, etc.
- **Task messages** (`TaskStartedMessage`, `TaskProgressMessage`, `TaskNotificationMessage`): Emitidos como SSE events `task_started`/`task_progress` para observabilidade de subagentes. Import com fallback (`_HAS_TASK_MESSAGES`).
- **`agent_id`/`agent_type` em hooks**: `PostToolUseHookInput` (opcionais). Logados no `[AUDIT] PostToolUse`. **NAO disponivel** em `StopHookInput`.

### Memory leak fixes do CLI 2.1.69:
- Fix: old message arrays acumulando (~35MB/1000 turns)
- Fix: bridge polling loop, hook events, teammates leaks
- Fix: API 400 errors em forked agents
- Baseline memory ~16MB

---

## Export critico: Teams

`app/teams/` importa de **6 sub-modulos**: permissions, models, SDK client, flags, session_persistence, pending_questions.

**Qualquer mudanca em permissions.py, models.py, client.py, feature_flags.py, session_persistence.py ou pending_questions.py DEVE ser testada no Teams bot.**
