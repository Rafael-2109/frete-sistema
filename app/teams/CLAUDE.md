# Teams Bot — Guia de Desenvolvimento

**LOC**: ~2.5K | **Arquivos**: 4 | **Atualizado**: 27/04/2026

Bot assincrono Microsoft Teams via Azure Function bridge. Non-daemon threads + SSL retry + transcript persistence.

---

## Estrutura

```
app/teams/
  ├── __init__.py      # 5 LOC — Blueprint /api/teams
  ├── models.py        # 81 LOC — TeamsTask (lifecycle 6 estados)
  ├── bot_routes.py    # 482 LOC — 5 endpoints + auth HMAC
  └── services.py      # 1,895 LOC — Core: user/session/response/async processing
```

## Regras Criticas

### R1: Thread non-daemon — `daemon=False` OBRIGATORIO
`process_teams_task_async()` roda em `Thread(daemon=False)`. Garante conclusao durante reciclagem gunicorn.
Alterar para `daemon=True` = task morre no meio, resposta perdida.
— FONTE: `bot_routes.py:177-183`

### R2: Commit com retry — SEMPRE usar `_commit_with_retry()`
NUNCA `db.session.commit()` direto. Render PostgreSQL derruba SSL apos 30-40s idle → `OperationalError`.
Retorna False se conexao perdida — caller DEVE re-fetch.
— FONTE: `services.py:130-164` (P1-1)

### R3: Re-fetch apos SSL dropped
Apos `_commit_with_retry()` retornar False, objetos SQLAlchemy ficam detached. Commit seria vazio.
DEVE re-fetch do banco + re-aplicar mudancas antes de novo commit.
— FONTE: `services.py:256-271` (P1-A)

### R4: `no_autoflush` — SEMPRE antes de query em contexto dirty
`with db.session.no_autoflush:` antes de queries que podem falhar por flush automatico de objetos parciais.

### R5: Cleanup obrigatorio no `finally`
Thread DEVE chamar: `cleanup_session_context()` + `cleanup_teams_task_context()` + `db.session.remove()`.
Esquecer = context vars poluidas → proxima request ve session/task da anterior.
— FONTE: `services.py:1224-1235`

### R6: TTL usa `updated_at` — NUNCA `created_at`
Task criada 5min atras pode ter recebido AskUserQuestion 30s atras.
Usar `created_at` marca como timeout task esperando resposta do usuario.
— FONTE: `services.py:1253-1258` (P2-C)

### R7: CancelledError e BaseException
`asyncio.CancelledError` e `BaseException` desde Python 3.9. `except Exception` NAO captura.
`asyncio.wait_for(timeout=chunk_timeout)` per-chunk cancela via CancelledError → bypassa TODOS os except handlers.
Timeout por inatividade apenas (INACTIVITY_TIMEOUT=240s, renovavel a cada chunk).
SEM teto absoluto — operacoes com subagentes Odoo podem levar 15-30 min legitimamente (DC-9).
Usar `finally` para garantias (Event.set, cleanup).
— FONTE: `services.py:957,1009-1045` (DC-8, DC-9)

---

## Modelo TeamsTask

> Campos: `.claude/skills/consultando-sql/schemas/tables/teams_tasks.json`

**Lifecycle**:
```
queued ──────────────────────────────────┐
                                         ↓
pending → processing → completed|error|awaiting_user_input|timeout
```
- `queued → processing` (automaticamente quando task anterior completa ou falha)
- `awaiting_user_input → processing` (apos resposta via `/bot/answer`)
- Timeout: `updated_at` > 5 min idle → `timeout` (lazy cleanup em `bot_message`)
- Timeout queued: `updated_at` > 10 min → `timeout`
- Limite: max 1 task `queued` por `conversation_id` (nova msg substitui anterior)

### R8: Fila de mensagens — max 1 por conversa
Quando usuario envia msg durante processamento, msg e enfileirada (`status='queued'`) em vez de rejeitada.
Apos task ativa completar (sucesso ou erro), `_process_queued_task()` verifica fila e processa
na MESMA THREAD (recursao via `process_teams_task_async`). Azure Function inicia polling para task queued.
— FONTE: `bot_routes.py:139-190`, `services.py:_process_queued_task()`

---

## Endpoints

| Endpoint | Metodo | Auth | Funcao |
|----------|--------|------|--------|
| `/bot/message` | POST | HMAC | Cria task async, retorna `task_id` |
| `/bot/status/<id>` | GET | HMAC | Polling: status + resposta parcial/final |
| `/bot/answer` | POST | HMAC | Responde AskUserQuestion (idempotente) |
| `/bot/execute` | POST | HMAC | TODO — nao implementado |
| `/bot/health` | GET | — | Diagnostico: threads ativas + orphan processes |

---

## Gotchas

### Bug Teams #1: Transcript persistence
JSONL de transcript vive no disco (worker efemero). Worker reciclado = arquivo sumiu = resume SDK falha.
Solucao: backup DB↔disco em 4 pontos do codigo.
— FONTE: `services.py:462-474,525-536,826-838,964-975`

### Bug Teams #2: Race condition `/bot/answer`
`submit_answer()` seta Event → `wait_for_answer()` pop() → 2a submissao falha.
Solucao: verifica status task ANTES. Se ja `processing`, trata como sucesso.
— FONTE: `bot_routes.py:285-335`

### Dispatch v2 vs v3
| Versao | Flag | Mecanismo | Status |
|--------|------|-----------|--------|
| v2 | `USE_PERSISTENT_SDK_CLIENT=false` | `asyncio.run()` efemero | **ATIVO (default)** |
| v3 | `USE_PERSISTENT_SDK_CLIENT=true` | `submit_coroutine()` pool daemon | Rollback (DC-7) |

v3 em rollback desde DC-7 (subprocess zombie). Confundir paths = zombie.
— FONTE: `services.py:506-519`, `feature_flags.py:250`

### Auto-cadastro de usuarios
Email deterministico: `teams_{md5[:12]}@teams.nacomgoya.local`, senha aleatoria, perfil='logistica'.
Permite FK em AgentSession/AgentMemory sem login web.
— FONTE: `services.py:24-85`

### session_id vs sdk_session_id
| ID | Escopo | Persistencia | Uso |
|----|--------|-------------|-----|
| `session_id` | Nosso UUID | Banco (`AgentSession`) | FK, queries, TTL 4h |
| `sdk_session_id` | CLI efemero | JSONB `data['sdk_session_id']` | Resume SDK |

Confundir = contexto perdido ou mensagens em sessao errada.

### DC-8: Subprocess zombie apos CancelledError
CancelledError bypassa except → Event nunca set → subprocess zombie 10min.
`_cleanup_orphan_claude_processes()` mata orfaos via `pgrep -P {pid}`.
— FONTE: `services.py:750-780`

### Fix 3: App instance do gunicorn
NUNCA usar `create_app()` na thread. Reutilizar `current_app._get_current_object()`.
`create_app()` cria MCP servers duplicados → conflito de portas.
— FONTE: `bot_routes.py:172-174`, `services.py:1019-1021`

---

## Feature Flags

| Flag | Default | Impacto |
|------|---------|---------|
| `TEAMS_DEFAULT_MODEL` | `claude-opus-4-7` | Modelo LLM (rollback: `claude-opus-4-6`) |
| `TEAMS_ASYNC_MODE` | `true` | Async (thread) vs sync |
| `TEAMS_ASK_USER_TIMEOUT` | `120` | Timeout Adaptive Card (seg) |
| `INACTIVITY_TIMEOUT` | `240` | Sem chunk por 4 min = timeout (DC-9, sem teto absoluto) |
| `TEAMS_PROGRESSIVE_STREAMING` | `true` | Flush parcial ao DB |
| `TEAMS_STREAM_FLUSH_INTERVAL` | `4.0` | Intervalo flush (seg) |
| `USE_PERSISTENT_SDK_CLIENT` | `false` | v3 pool vs v2 efemero (rollback) |

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/agente/sdk/` | client, client_pool, session_persistence, pending_questions | Mudanca em qualquer um DEVE ser testada no Teams |
| `app/agente/config/` | permissions (ContextVar), feature_flags | Context vars cross-thread |
| `app/agente/models.py` | AgentSession | JSONB `data` (transcript vive em `claude_session_store` pos-Fase C) |
| `app/auth/models.py` | Usuario | Auto-cadastro FK |

> **REGRA** (de `app/agente/CLAUDE.md:232-234`): Qualquer mudanca em `permissions.py`, `models.py`, `client.py`, `feature_flags.py`, `session_persistence.py` ou `pending_questions.py` DEVE ser testada no Teams bot.
