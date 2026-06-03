<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-03
-->
# Teams Bot — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do modulo Teams Bot — bot assincrono do Microsoft Teams via Azure Function bridge.

## Indice

- [Contexto](#contexto)
- [Estrutura](#estrutura)
- [Regras Criticas](#regras-criticas)
  - [R1: Thread non-daemon — `daemon=False` OBRIGATORIO](#r1-thread-non-daemon-daemonfalse-obrigatorio)
  - [R2: Commit com retry — SEMPRE usar `_commit_with_retry()`](#r2-commit-com-retry-sempre-usar-_commit_with_retry)
  - [R3: Re-fetch apos SSL dropped](#r3-re-fetch-apos-ssl-dropped)
  - [R4: `no_autoflush` — SEMPRE antes de query em contexto dirty](#r4-no_autoflush-sempre-antes-de-query-em-contexto-dirty)
  - [R5: Cleanup obrigatorio no `finally`](#r5-cleanup-obrigatorio-no-finally)
  - [R6: TTL usa `updated_at` — NUNCA `created_at`](#r6-ttl-usa-updated_at-nunca-created_at)
  - [R7: CancelledError e BaseException](#r7-cancellederror-e-baseexception)
- [Modelo TeamsTask](#modelo-teamstask)
  - [R8: Fila de mensagens — max 1 por conversa](#r8-fila-de-mensagens-max-1-por-conversa)
- [Endpoints](#endpoints)
- [Gotchas](#gotchas)
  - [Bug Teams #1: Transcript persistence](#bug-teams-1-transcript-persistence)
  - [Bug Teams #2: Race condition `/bot/answer`](#bug-teams-2-race-condition-botanswer)
  - [Dispatch v2 vs v3](#dispatch-v2-vs-v3)
  - [Auto-cadastro de usuarios](#auto-cadastro-de-usuarios)
  - [session_id vs sdk_session_id](#session_id-vs-sdk_session_id)
  - [DC-8: Subprocess zombie apos CancelledError](#dc-8-subprocess-zombie-apos-cancellederror)
  - [Fix 3: App instance do gunicorn](#fix-3-app-instance-do-gunicorn)
- [Feature Flags](#feature-flags)
- [Interdependencias](#interdependencias)

## Contexto

~2.5K LOC, 4 arquivos. Threads non-daemon (concluem durante reciclagem do gunicorn) + retry de SSL + persistencia de transcript. Regras criticas: `daemon=False` obrigatorio em `process_teams_task_async()` e `_commit_with_retry()` sempre (nunca commit direto — Render derruba SSL em idle).

**LOC**: ~2.5K | **Arquivos**: 4 | **Atualizado**: 01/06/2026

Bot assincrono Microsoft Teams via Azure Function bridge. Non-daemon threads + SSL retry + transcript persistence.

---

## Estrutura

```
app/teams/
  ├── __init__.py      # 5 LOC — Blueprint /api/teams
  ├── models.py        # 81 LOC — TeamsTask (lifecycle 6 estados)
  ├── bot_routes.py    # 482 LOC — 5 endpoints + auth HMAC
  └── services.py      # 1,919 LOC — Core: user/session/response/async processing
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
Timeout por inatividade apenas (INACTIVITY_TIMEOUT=300s, renovavel a cada chunk).
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
| v2 | `USE_PERSISTENT_SDK_CLIENT=false` | `asyncio.run()` efemero | **DESLIGADO em 2026-03-27** |
| v3 | `USE_PERSISTENT_SDK_CLIENT=true` (default) | `submit_coroutine()` pool daemon persistente | **ATIVO** |

**v3 (pool persistente) e o caminho ATIVO.** `services.py:738,1300` chamam
`submit_coroutine` HARDCODED (comentario inline: "v2 asyncio.run desligado em
2026-03-27"); o default de `USE_PERSISTENT_SDK_CLIENT` e `true`
(`feature_flags.py:422`). O rollback historico (DC-7, subprocess zombie) foi
superado — a afinidade per-process do SDK passou a ser tratada por outra via
(split Caddy: `/agente*` -> gunicorn-agente com 1 worker).

**CUIDADO (achado avaliacao 360 — A1/CONF-2)**: as rotas `/api/teams/*` NAO
estao no split do Caddy (`Caddyfile` so roteia `/agente*` e `/agente-lojas*`
para :5001). O Teams cai no `handle{}` -> `gunicorn-sistema` (**4 workers**,
:5002). Logo o pool persistente e' **process-local em multi-worker**: uma 2a
mensagem da mesma conversa pode cair em outro worker (cenario DC-7). Mitigado
na pratica por: estado em `TeamsTask` (DB, worker-agnostico) + orphan-kill
(`_cleanup_orphan_claude_processes`). Hardening proposto (nao implementado):
rotear `/api/teams/*` -> :5001. Ver `docs/RELATORIO_AVALIACAO_360_AGENTE_2026-05-29.md` CONF-2.
— FONTE: `services.py:738,1300` (submit_coroutine), `feature_flags.py:422`

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
| `TEAMS_DEFAULT_MODEL` | `claude-opus-4-8` | Modelo LLM (rollback: `claude-opus-4-7`) |
| `TEAMS_ASYNC_MODE` | `true` | Async (thread) vs sync |
| `TEAMS_ASK_USER_TIMEOUT` | `120` | Timeout Adaptive Card (seg) |
| `INACTIVITY_TIMEOUT` | `300` | Sem chunk por 5 min = timeout (DC-9, sem teto absoluto) — era 240s ate 2026-05-25 |
| `TEAMS_PROGRESSIVE_STREAMING` | `true` | Flush parcial ao DB |
| `TEAMS_STREAM_FLUSH_INTERVAL` | `4.0` | Intervalo flush (seg) |
| `USE_PERSISTENT_SDK_CLIENT` | `true` | v3 pool persistente (ATIVO) vs v2 efemero (desligado 2026-03-27) |

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/agente/sdk/` | client, client_pool, session_persistence, pending_questions | Mudanca em qualquer um DEVE ser testada no Teams |
| `app/agente/config/` | permissions (ContextVar), feature_flags | Context vars cross-thread |
| `app/agente/models.py` | AgentSession | JSONB `data` (transcript vive em `claude_session_store` pos-Fase C) |
| `app/auth/models.py` | Usuario | Auto-cadastro FK |

> **REGRA** (de `app/agente/CLAUDE.md:232-234`): Qualquer mudanca em `permissions.py`, `models.py`, `client.py`, `feature_flags.py`, `session_persistence.py` ou `pending_questions.py` DEVE ser testada no Teams bot.
