<!-- doc:meta
tipo: explanation
camada: L2
sot_de: Agente Web — Subsistemas (detalhe)
hub: app/agente/CLAUDE.md
superseded_by: —
atualizado: 2026-06-07
-->
# Agente Web — Subsistemas (detalhe)

> **Papel:** detalhe completo (componentes, fluxos, gotchas) dos subsistemas do Agente Web que sao tocados isoladamente. **Abra quando:** for editar um destes subsistemas — o guia [`CLAUDE.md`](CLAUDE.md) traz o resumo + o gatilho e aponta para a secao certa aqui.

## Contexto

Progressive disclosure do modulo: o [`CLAUDE.md`](CLAUDE.md) carrega sempre (regras criticas R1-R10, hierarquia de timeouts, pipeline SSE, estrutura); este arquivo so e lido sob demanda — ao mexer em Artifacts, telemetria de subagent, memoria compartilhada, avaliador de efetividade de skill ou no inventario de eventos SSE. Nada aqui se sobrepoe ao guia: e o detalhe que sairia do topo e diluiria o sinal.

## Indice

- [Mapa de eventos SSE](#mapa-de-eventos-sse)
- [Artifacts](#artifacts)
- [Telemetria de subagent](#telemetria-de-subagent)
- [Memoria Compartilhada](#memoria-compartilhada)
- [Avaliador de Efetividade de Skill](#avaliador-de-efetividade-de-skill)

## Mapa de eventos SSE

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


## Artifacts

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


## Telemetria de subagent

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


## Memoria Compartilhada

> **Canonico do sistema de memoria** (ciclo de vida, categorias, decay, paths padrao, criterios de qualidade): `.claude/references/MEMORY_PROTOCOL.md`. Abaixo, somente o *delta de escopo* (empresa vs pessoal) implementado neste modulo.

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
- `app/embeddings/service.py:_search_pgvector_memories()` → `WHERE user_id = ANY([user_id, 0])`
- `app/embeddings/service.py:_search_fallback_memories()` → `.filter(user_id.in_([user_id, 0]))`
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


## Avaliador de Efetividade de Skill

Avalia pos-sessao se as skills invocadas resolveram o problema; quando nao, cria lembrete
por-usuario (auto) OU propoe lembrete-todos / ajuste de codigo (via Inbox). **EM PROD desde
2026-06-07** (flag `AGENT_SKILL_EVAL=true` no web `sistema-fretes`). Spec/plano:
`docs/superpowers/specs/2026-06-07-aprendizado-efetividade-skills-design.md` +
`docs/superpowers/plans/2026-06-07-aprendizado-efetividade-skills-fase1.md`.

**Fluxo**: `run_post_session_processing` -> `_maybe_trigger_skill_eval` (flag-gated) -> RQ
`agent_background` -> `skill_effectiveness_job` -> `evaluate_session`: `build_skill_windows`
(msg anterior + 2 prox user + 2 prox assistant; so janela fechada) -> funil estagio0 custo-zero
(sentiment+regex+Bash) -> Haiku -> Sonnet (cap `MAX_SONNET`) -> `apply_decision` -> grava
`AgentSkillEffectiveness` (idempotente por `session_id`+`anchor_msg_id`). Entrega do lembrete:
`_keep_stream_open` (PreToolUse) injeta `additionalContext` SO quando a skill e reinvocada
(cache 30min; shadow NAO injeta).

### Componentes

| Camada | Arquivo |
|---|---|
| Modelo + migration | `models.py:AgentSkillEffectiveness` · `scripts/migrations/2026_06_07_agent_skill_effectiveness.{py,sql}` |
| Service nucleo | `services/skill_effectiveness_service.py` (janela/estagios/aplicacao/orquestracao) |
| Service inbox | `services/approval_inbox_service.py` (list/approve/reject) |
| Gatilho | `routes/_helpers.py:_maybe_trigger_skill_eval` (em `run_post_session_processing`) |
| Worker | `workers/background_jobs.py:skill_effectiveness_job` (+`try_enqueue_skill_effectiveness`, fila `agent_background`) |
| Injecao | `sdk/hooks.py:_keep_stream_open` (elif `tool_name=='Skill'`) + `sdk/memory_injection.py:get_skill_reminders_for_session` |
| Inbox rotas+UI | `routes/memories.py` (`/api/memories/approvals*`, admin) · `templates/agente/memorias.html` (aba "Pendentes de Aprovacao") |
| D8 | `services/improvement_suggester.py` (clausula separacao de competencias) |

### Feature flags (`config/feature_flags.py`)

`AGENT_SKILL_EVAL` (OFF -> ON PROD 2026-06-07) · `AGENT_SKILL_EVAL_SONNET` (true) ·
`AGENT_SKILL_EVAL_APPLY_USER` (true = lembrete_usuario auto; false = shadow -> Inbox) ·
`AGENT_SKILL_EVAL_CONF_MIN` (0.7) · `AGENT_SKILL_EVAL_MAX_SONNET` (3).

### Gotchas

- **Separacao de competencias (inviolavel)**: o avaliador (Haiku/Sonnet) DESCREVE o problema +
  evidencia e PEDE ajuda; ramo `ajuste_codigo` NUNCA prescreve solucao
  (`implementation_notes`/`affected_files` ficam None — quem resolve codigo e o Claude Code).
  Vale tambem p/ o D8 (`improvement_suggester`).
- **Conserta gap pre-existente**: `directive_promotion` criava `directive_status='shadow'` sem
  UI de ativacao; a Inbox e a UNICA via `shadow -> ativa` (aprovar) / `despromovida` (rejeitar).
- **Teams: cobertura LIGADA (debito RESOLVIDO 2026-06-08)**: `build_skill_windows` casa
  `"Skill:<nome>"`; o Teams agora enriquece o tool_name no loop de streaming via
  `_enrich_tool_name` (`teams/services.py`, espelha `chat.py:861-870`) -> grava `"Skill:<nome>"`
  em `tools_used` -> o avaliador encontra janelas no canal Teams. Antes gravava o bare `"Skill"`
  (zero janelas). Cobertura: `tests/teams/test_enrich_tool_name.py`.
- **PII**: `_format_window` (input do LLM) e `_window_evidence` (persistido + exibido na inbox)
  aplicam `utils/pii_masker.mask_pii` (CNPJ/CPF/email).
- **Teste**: a fixture `db` (conftest:50) NAO contem o `commit()` do service -> testes usam
  `session_id` unico + cleanup explicito (resíduo no banco dev se faltar).

