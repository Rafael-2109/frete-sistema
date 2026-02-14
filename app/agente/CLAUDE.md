# Agente Logistico Web — Guia de Desenvolvimento

**LOC**: 11.9K | **Arquivos**: 37 | **Atualizado**: 14/02/2026

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
| `threading.local()` | `session_id` (isolamento por thread) | `permissions.py:46` |
| Dict global `_stream_context` + Lock | `event_queue` (cross-thread) | `permissions.py:40-41` |
| Dict `_teams_task_context` | Associar sessao <> TeamsTask | `permissions.py:98` |

NUNCA substituir `threading.local()` por variavel global — causa race condition entre threads.
`event_queue` PRECISA ser global porque o endpoint SSE acessa de outra thread.

### R5: Stream safety — None sentinel + done_event
| Camada | Timeout | Funcao |
|--------|---------|--------|
| Heartbeat SSE | 10s | Evita proxy/Render matar conexao idle |
| SDK inactivity | 240s | Timeout se CLI para de emitir |
| Stream max | 540s | Teto absoluto do streaming |
| None sentinel | finally | Garante que SSE generator termina |

NUNCA remover o `yield None` no `finally` do generator — frontend trava esperando eventos.

**`streaming_done_event`** (`client.py:1199`): `asyncio.Event()` que controla o prompt generator. Se NAO chamar `.set()` em QUALQUER error path, o generator fica preso em `done_event.wait(timeout=600)` → processo zombie por 10min. Chamado atualmente em 3 locais: linhas 1489, 1636, 1683. **Ao adicionar NOVO error handler em `_stream_response()`, DEVE chamar `streaming_done_event.set()`.**

### AskUserQuestion: blocking cross-arquivo
Fluxo cruza 3 arquivos: `pending_questions.py` → `permissions.py` → `routes.py`
- Web: event_queue SSE → frontend responde → POST `/api/user-answer` → Event.set()
- Teams: TeamsTask.status='awaiting_user_input' → Adaptive Card → POST resposta → Event.set()
- Timeout web: 55s. Timeout Teams: 120s (`TEAMS_ASK_USER_TIMEOUT`)

Alterar um arquivo sem verificar os outros 2 quebra o fluxo silenciosamente.

### MCP tools: NAO callable
Tools em `tools/` sao registros MCP (ToolAnnotations). O agente usa `mcp__X__Y` diretamente.
NUNCA importar e chamar como funcao Python — nao sao callables, gera erro silencioso.

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
| `services/pattern_analyzer.py` | `USE_PATTERN_LEARNING` | `true` | Analisa sessoes via Haiku a cada 10 sessoes, salva patterns em `/memories/learned/patterns.xml` |
| `services/sentiment_detector.py` | `USE_SENTIMENT_DETECTION` | `false` | Detecta frustracao via regex, injeta instrucao de tom. Zero custo API |

---

## Export critico: Teams

`app/teams/` importa de **6 sub-modulos**: permissions, models, SDK client, flags, session_persistence, pending_questions.

**Qualquer mudanca em permissions.py, models.py, client.py, feature_flags.py, session_persistence.py ou pending_questions.py DEVE ser testada no Teams bot.**
