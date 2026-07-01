<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-14
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
  - [Identidade unificada (Fase A) — hierarquia de resolucao](#identidade-unificada-fase-a-2026-06-10--hierarquia-de-resolucao)
  - [Falante do turno em grupos (Fase B)](#falante-do-turno-em-grupos-fase-b-2026-06-10)
  - [Entrega continua (Fase E2)](#entrega-continua-fase-e2-2026-06-11)
  - [session_id vs sdk_session_id](#session_id-vs-sdk_session_id)
  - [DC-8: Subprocess zombie apos CancelledError](#dc-8-subprocess-zombie-apos-cancellederror)
  - [Fix 3: App instance do gunicorn](#fix-3-app-instance-do-gunicorn)
- [Feature Flags](#feature-flags)
- [Interdependencias](#interdependencias)

## Contexto

~3.7K LOC, 5 arquivos. Threads non-daemon (concluem durante reciclagem do gunicorn) + retry de SSL + persistencia de transcript + entrega proativa. Regras criticas: `daemon=False` obrigatorio em `process_teams_task_async()` e `_commit_with_retry()` sempre (nunca commit direto — Render derruba SSL em idle).

**LOC**: ~3.7K | **Arquivos**: 5 | **Atualizado**: 14/06/2026

Bot assincrono Microsoft Teams via Azure Function bridge. Non-daemon threads + SSL retry + transcript persistence.

---

## Estrutura

```
app/teams/
  ├── __init__.py      # 5 LOC — Blueprint /api/teams
  ├── models.py        # ~100 LOC — TeamsTask (lifecycle 6 estados + delivered_via/conversation_reference/proactive_partial_chars)
  ├── bot_routes.py    # ~560 LOC — endpoints + auth HMAC + claim de entrega
  ├── proactive.py     # ~270 LOC — entrega proativa final + blocos parciais (POST /api/notify na function)
  └── services.py      # ~2.6K LOC — Core: user/session/response/async/fast-paths/merge
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
- Timeout (Fase C 2026-06-10): `updated_at` > 15 min (pending/processing), > 30 min
  (awaiting_user_input), > 15 min (queued) → `timeout` (lazy cleanup em `bot_message`).
  Heartbeat de 60s renova `updated_at` enquanto a coroutine de stream vive
  (`_stream_with_timeout` — gap de 15 min = thread morta DE FATO).
- Entrega (Fase C): `delivered_via` = claim atomico `'polling'|'proactive'` (NULL =
  nao entregue). `/bot/status` clama polling; `proactive.notify_function_delivery`
  clama proactive (rollback se o POST falhar). Quem ganha entrega; o perdedor ve
  `already_delivered` e desiste.
- Entrega continua (Fase E2 2026-06-11): polling da function dura 8,5 min
  (E1: `POLL_MAX_ATTEMPTS=340` x 1.5s) com progressive update in-place; DEPOIS
  disso o heartbeat (60s) entrega blocos de texto novos como MENSAGENS NOVAS
  via `proactive.notify_function_partial` (tipo='partial', SEM claim).
  `proactive_partial_chars` = offset de chars ja entregues via blocos; a final
  envia so `resposta[offset:]` (status `error` IGNORA offset — texto de erro
  substitui o parcial, nao o continua). Offset avanca SO apos POST 200 (CAS) —
  falha de POST reenvia o bloco (duplicar raro > perder texto). Ver gotcha
  "Entrega continua (Fase E2)".
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
| `/bot/message` | POST | HMAC | Cria task async, retorna `task_id`; payload tem `usuario_id` (AAD), `usuario_email`, `conversation_type`, `conversation_reference` (Fases A/B/C) |
| `/bot/status/<id>` | GET | HMAC | Polling: status + resposta parcial/final + claim `delivered_via='polling'`; responde `already_delivered` se proactive ja entregou |
| `/bot/answer` | POST | HMAC | Responde AskUserQuestion (idempotente) |
| `/bot/health` | GET | — | Diagnostico: threads ativas + orphan processes |
| `{function}/api/notify` | POST | X-API-Key | NA AZURE FUNCTION: backend entrega via `continue_conversation` quando o polling (8,5 min) ja morreu — `tipo='final'` (resposta/delta restante + card) ou `tipo='partial'` (bloco de texto novo, Fase E2) — `app/teams/proactive.py` |

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

**RESOLVIDO (achado avaliacao 360 — A1/CONF-2)**: as rotas `/api/teams/*` agora
SAO roteadas para :5001 no split do Caddy (matcher `@teams`, junto de `/agente*`).
Antes caiam no `handle{}` default -> `gunicorn-sistema` (**4 workers**, :5002),
tornando o pool persistente **process-local em multi-worker**: uma 2a mensagem da
mesma conversa podia cair em outro worker (cenario DC-7). Com o roteamento para
:5001 (**1 worker**), todas as requests Teams caem no mesmo processo -> pool
sempre consistente. Defesa em profundidade preservada: estado em `TeamsTask`
(DB, worker-agnostico) + orphan-kill (`_cleanup_orphan_claude_processes`).
Trade-off aceito: o Teams divide o worker unico de :5001 com o chat web SSE —
mitigado porque o processamento pesado roda em thread de background non-daemon
(nao nos 8 worker-threads do gunicorn) e as requests Teams sao curtas (cria/poll
TeamsTask). Ver `docs/RELATORIO_AVALIACAO_360_AGENTE_2026-05-29.md` CONF-2.
— FONTE: `Caddyfile` (matcher `@teams`), `services.py:738,1300` (submit_coroutine),
`feature_flags.py:422`

### Identidade unificada (Fase A 2026-06-10) — hierarquia de resolucao
`_get_or_create_teams_user(usuario, aad_id, email)`:
1. **AAD object ID vinculado** (`Usuario.find_by_teams_aad_id`) — vinculo por codigo
   de pareamento (tela `/auth/vincular-teams` + fast-path `vincular ABC123`,
   `app/agente/sdk/vincular_teams_fastpath.py`), por email ou por admin.
2. **Auto-match por e-mail corporativo** (TeamsInfo.get_member na function) —
   grava vinculo `origem='email'` se o usuario ainda nao tem `teams_user_id`.
3. **Fallback legacy (fantasma)**: email deterministico
   `teams_{md5[:12]}@teams.nacomgoya.local`, senha aleatoria, perfil='logistica'.
Merge de fantasma -> usuario real: `merge_usuario_teams` (FK discovery dual:
information_schema + tabelas agent%/teams%/claude% SEM FK formal) + script
`scripts/migrations/2026_06_10_merge_usuarios_teams.py` (--dry-run default).
— FONTE: `services.py:_get_or_create_teams_user`, `app/auth/models.py:find_by_teams_aad_id`

### Falante do turno em grupos (Fase B 2026-06-10)
Em `groupChat`/`channel`, o prompt ganha `[Mensagem de: <nome>]`
(`_montar_prompt_teams`) e `add_user_message(author=)` persiste o falante
(fallback XML de resume inclui `author=`). Hooks do SDK resolvem o falante do
turno via `app/agente/sdk/turn_context_registry.py` (client do pool reusado NAO
reaplica hooks — a closure congelava memorias/gates no 1o falante). Msgs
enfileiradas derivam o tipo pela heuristica `conversation_id.startswith('19:')`.
— FONTE: `services.py:_montar_prompt_teams`, `app/agente/sdk/hooks.py:_turn_user`

### Entrega continua (Fase E2 2026-06-11)
Pos-polling (8,5 min), o heartbeat de 60s chama `notify_function_partial` em
`run_in_executor` — NUNCA inline no event loop: `requests.post` (timeout 30s) e
sincrono e o loop do pool e COMPARTILHADO entre todos os streams (bloquear =
congelar tudo). A sessao scoped da thread do executor leva `db.session.remove()`
apos o uso (thread reusada).
Invariantes do offset `proactive_partial_chars`:
1. So avanca APOS POST 200 (CAS sobre o valor lido) — falha de POST reenvia o
   bloco no proximo tick; duplicar bloco raro > perder texto.
2. O alinhamento offset↔texto depende da sanitizacao parcial ser PREFIXO da
   final: `_sanitizar_texto_parcial` faz `strip()` (remove o rabo volatil de
   `\n`) e as demais transformacoes sao locais — NAO adicionar transformacao
   nao-prefix-estavel (ex: substituicao global retroativa) sem repensar E2.
3. `PARTIAL_MIN_DELTA_CHARS=200` tambem filtra o status transitorio de tool
   (`_Consultando..._`) que o flush grava em `resposta` antes do 1o texto real.
4. Status `error` IGNORA o offset (texto de erro SUBSTITUI o parcial).
Limitacao aceita (plano FASE E): o 1o bloco pos-polling repete o texto que a
msg progressiva ja mostrou (offset comeca em 0; mesma duplicacao que a final
da Fase C ja tinha). Refinamento possivel: function informar chars entregues
progressivamente ao fim do polling.
— FONTE: `proactive.py:notify_function_partial`, `services.py:_heartbeat_loop`

### ROOT CAUSE "morre mudo" / cold-start da function (2026-06-12)

**A Azure Function `frete-bot-func` esta no plano CONSUMPTION** (`sku: Dynamic`,
`alwaysOn: false`, `minimumElasticInstanceCount: 0`, SEM `ipSecurityRestrictions`)
-> **escala a zero**. Em cold-start/reciclagem o `POST /api/notify` do backend
para a function leva `[Errno 111] Connection refused` TRANSITORIO (o Azure ainda
nao provisionou a instancia). Sintoma: tasks `completed`/`error` ficam com
`delivered_via IS NULL` e o usuario NUNCA recebe a resposta (tarefas longas, que
ja passaram do polling de 8,5 min, dependem 100% do `/api/notify`). Diagnostico:
~48 orfas em 7 dias; 10/10 entregas OK em dia de uso intenso (function quente) vs
0/2 em dia esparso (function fria). NAO eh firewall/IP (refutado pelo JSON da
function) nem function morta (responde 401 publicamente).

**Defesa em 2 camadas (P0):**
1. **Retry+backoff** (`proactive.py:_post_notify`, `TEAMS_NOTIFY_BACKOFF=2,5,10`):
   a 1a tentativa "cutuca" a function fria; as seguintes pegam ela ja quente.
2. **Reconciliador** (`proactive.py:reconciliar_entregas_pendentes`, job no
   scheduler a cada `TEAMS_RECONCILE_INTERVAL_MIN`): rede de seguranca que
   re-entrega orfas com `delivered_via IS NULL` + `conversation_reference` +
   idade em `[POLLING_WINDOW, TEAMS_RECONCILE_MAX_AGE_MIN]`. Idempotente (claim
   atomico em `delivered_via`).

> Orfas mais velhas que `TEAMS_RECONCILE_MAX_AGE_MIN` (default 6h) NAO sao
> re-entregues (ref velha + resposta fora de contexto). Solucao definitiva da
> FONTE seria Premium/EP1 (always-on, custo fixo) ou trazer `continue_conversation`
> para o backend (elimina a ponte Render->Azure). O P0 absorve o cold-start sem custo.
— FONTE: `proactive.py:_post_notify,reconciliar_entregas_pendentes`,
`app/scheduler/sincronizacao_incremental_definitiva.py:executar_reconciliacao_teams`

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

### Telemetria por-turno — path async grava `agent_step` + `agent_session_costs` (2026-06-14)
O path async (`process_teams_task_async`, ATIVO) grava DUAS telemetrias logo após
`session.model = selected_model`:
- `agent_step` (model + tokens) via `_gravar_agent_step_teams` — **antes só o path
  SYNC (em desuso) chamava**, deixando `agent_step` VAZIO p/ Teams.
- `agent_session_costs` (model + **cache breakdown**) via `_persist_cost_teams` —
  **antes só o canal web gravava** (chat.py `_persist_session_cost`). `message_id`
  sintético `teams:{session}:{turn_seq}` (idempotente via UNIQUE), best-effort/INV-6,
  atrás da flag `USE_COST_TRACKER_PERSIST` (ON em PROD, OFF local).

**Por quê importa:** o prompt cache é MODEL-SCOPED e trocar de modelo invalida o
cache inteiro. Medido em PROD: Teams re-escrevia cache ~4x o web (34% vs 8,7% em
<5min) pela alternância Sonnet↔Opus do smart routing. **Mitigado em 2026-06-16**:
o Teams roda em **Sonnet FIXO + thinking high** (`TEAMS_DEFAULT_MODEL=claude-sonnet-5`,
`TEAMS_SMART_MODEL_ROUTING=false`, `TEAMS_EFFORT_LEVEL=high`) — sem alternância de
modelo. Registrar model+cache na MESMA linha mantém isso mensurável pós-fix.
— FONTE: `services.py:_persist_cost_teams,_gravar_agent_step_teams` (chamados ~L2236);
memória dev `teams_cache_churn_model_routing.md`

> **⚠️ DRIFT (verificado 2026-06-28):** apesar do default de código ser Sonnet desde
> 16/06, **produção roda 100% Opus** (118/118 turnos/30d) — a env var
> `TEAMS_DEFAULT_MODEL=claude-opus-4-8` no Render `sistema-fretes` sobrepõe o default.
> ✅ EFETIVADO 2026-06-28: env var `TEAMS_DEFAULT_MODEL=claude-sonnet-4-6` aplicada no Render (deploy `dep-d90sbskvikkc738omf8g`).
> ⚠️ 2026-06-30: default do código migrado `claude-sonnet-4-6`→`claude-sonnet-5` (Sonnet 5). A env var Render acima **sobrepõe** o default — p/ o Teams migrar de fato, atualizar `TEAMS_DEFAULT_MODEL=claude-sonnet-5` no Render (ou remover a env var p/ herdar o default do código). Mesma consideração vale p/ `AGENT_WEB_FAST_MODEL`/`TEAMS_FAST_MODEL` se estiverem setados no Render.

> **FIX inflação de custo (2026-06-28):** o path Teams gravava `agent_result.cost_usd`
> (= `ResultMessage.total_cost_usd`, ACUMULADO da sessão SDK) cru em `session.total_cost_usd`
> e em `agent_session_costs.cost_usd`, somando o acumulado a cada turno → inflação **~7x**
> (medido: $320,87 gravado vs **$46,65 real** em 30d/Teams, 118 turnos). O fix do web
> `0e9403082` (2026-06-19) NÃO alcançou o Teams. Agora usa `turn_cost_from_cumulative`
> (DELTA do turno) com baseline em `data['_sdk_cost_cumulative']`/`_sdk_cost_session_id`,
> idêntico a `chat.py:_save_messages_to_db`. ✅ BACKFILL HISTÓRICO APLICADO em PROD
> 2026-06-28 ($320,87→$46,65, verificado via MCP): `scripts/migrations/2026_06_28_backfill_teams_cost.py`
> (recalc dos tokens, backup `bkp_teams_cost_backfill_*`, `--revert`). ⚠️ O FIX de código acima
> está no working tree e **ainda NÃO deployado** — até deployar, o dashboard Teams re-infla.
> — FONTE: `services.py` GAP 2 (~L2265)

---

## Feature Flags

| Flag | Default | Impacto |
|------|---------|---------|
| `TEAMS_DEFAULT_MODEL` | `claude-sonnet-5` | Modelo LLM — **Sonnet fixo** (Sonnet 5 no código desde 2026-06-30; ⚠️ env var Render pode sobrepor — ver nota de drift; rollback p/ Opus: `claude-opus-4-8`) |
| `TEAMS_SMART_MODEL_ROUTING` | `false` | Routing dinâmico de modelo — **OFF** (Teams é Sonnet fixo; alternar só trazia churn de cache MODEL-SCOPED). Religar só faz sentido com `TEAMS_DEFAULT_MODEL=claude-opus-4-8` |
| `TEAMS_EFFORT_LEVEL` | `high` | Thinking level (off\|low\|medium\|high\|max) aplicado em `services.py` get_response/stream_response. Rollback: `medium` |
| `TEAMS_ASYNC_MODE` | `true` | Async (thread) vs sync |
| `TEAMS_ASK_USER_TIMEOUT` | `600` | Timeout Adaptive Card (seg) — subido 180→600 em 2026-06-12 (humano demora p/ responder card; resposta tardia levava 400). SEGURO porque a espera virou ASSINCRONA (`permissions.py:async_wait_for_answer`) e nao bloqueia mais o event loop do pool |
| `TEAMS_INACTIVITY_TIMEOUT` | `300` | Sem chunk por 5 min = timeout (DC-9, sem teto absoluto); env configuravel desde Fase C — era constante hardcoded |
| `TEAMS_PROGRESSIVE_STREAMING` | `true` | Flush parcial ao DB |
| `TEAMS_STREAM_FLUSH_INTERVAL` | `4.0` | Intervalo flush (seg) |
| `USE_PERSISTENT_SDK_CLIENT` | `true` | v3 pool persistente (ATIVO) vs v2 efemero (desligado 2026-03-27) |
| `AGENT_VINCULACAO_FASTPATH` | `true` | FASE 3 reducao custo: vincular/desvincular NF×PO (Gabriella) sem subagente gestor-recebimento. Roteamento deterministico (regex N0 + Haiku N1) em `services.py` ANTES do baseline/LLM: `if _vinc -> elif _fp(baseline) -> else LLM`. Ver `app/agente/sdk/vinculacao_fastpath.py` |
| `AGENT_BASELINE_FASTPATH` | `true` | "atualizar baseline" (Marcus) resolvido sem LLM. Ver `app/agente/sdk/baseline_fastpath.py`. Fase A 2026-06-10: fast-paths agora interceptam tambem no path ASYNC (`process_teams_task_async`) — antes so existiam no sync morto |
| `AGENT_TEAMS_VINCULO_FASTPATH` | `true` | Fase A: fast-path `vincular ABC123` (pareamento de identidade, meta-comando sem LLM/sessao). Ver `app/agente/sdk/vincular_teams_fastpath.py` |
| `TEAMS_PROACTIVE_DELIVERY` | `true` | Fases C/E2: entrega proativa pos-polling (final + blocos parciais a cada 60s) via `{TEAMS_FUNCTION_URL}/api/notify` + `continue_conversation`. URL tem default no codigo (`proactive.py`); env `TEAMS_FUNCTION_URL` sobrepoe. Desligar tambem desliga os blocos parciais |
| `TEAMS_NOTIFY_BACKOFF` | `2,5,10` | CSV de segundos ENTRE tentativas do POST `/api/notify` (total = len+1 = 4 POSTs). Absorve o `Connection refused` transitorio de cold-start da function (`proactive.py:_post_notify`) |
| `TEAMS_RECONCILE_ENABLED` | `true` | Reconciliador (rede de seguranca): re-entrega tasks finais orfas (`delivered_via IS NULL`). Rodado pelo scheduler `sincronizacao_incremental_definitiva` a cada `TEAMS_RECONCILE_INTERVAL_MIN`. Rollback total: `false` |
| `TEAMS_RECONCILE_MAX_AGE_MIN` | `360` | Teto de idade (min) da orfa p/ re-entrega (acima disso a resposta perde contexto / ref velha) |
| `TEAMS_RECONCILE_LIMIT` | `50` | Max de orfas processadas por ciclo |
| `TEAMS_RECONCILE_INTERVAL_MIN` | `2` | Intervalo (min) do job no scheduler (`sincronizacao_incremental_definitiva.py:executar_reconciliacao_teams`) |

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/agente/sdk/` | client, client_pool, session_persistence, pending_questions | Mudanca em qualquer um DEVE ser testada no Teams |
| `app/agente/config/` | permissions (ContextVar), feature_flags | Context vars cross-thread |
| `app/agente/models.py` | AgentSession | JSONB `data` (transcript vive em `claude_session_store` pos-Fase C) |
| `app/auth/models.py` | Usuario | Auto-cadastro FK |

> **REGRA** (de `app/agente/CLAUDE.md:232-234`): Qualquer mudanca em `permissions.py`, `models.py`, `client.py`, `feature_flags.py`, `session_persistence.py` ou `pending_questions.py` DEVE ser testada no Teams bot.
