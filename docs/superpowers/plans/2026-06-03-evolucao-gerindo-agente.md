<!-- doc:meta
tipo: how-to
camada: L2
sot_de: evolucao da skill gerindo-agente (roadmap por ondas)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Roadmap — Evolucao da skill `gerindo-agente` para top-level

> **Papel:** plano vivo (multi-sessao) de evolucao da skill `gerindo-agente`,
> de fachada da geracao CLASSICA para a superficie UNICA de gestao/introspeccao
> do Agente Web (incluindo a camada de evolucao/qualidade que ja roda em PROD).

## Indice

- [Como continuar (proxima sessao)](#como-continuar-proxima-sessao)
- [Contexto e diagnostico](#contexto-e-diagnostico)
- [Censo PROD](#censo-prod)
- [Decisoes travadas](#decisoes-travadas)
- [Ondas](#ondas)
- [Pendencias de decisao / itens abertos](#pendencias-de-decisao--itens-abertos)
- [Gotchas](#gotchas)

## Como continuar (proxima sessao)

> **Entrada de continuidade — leia isto primeiro.** Atualizado 2026-06-03 pos-Onda 4 P10.

**CORRECAO DE ESTADO (2026-06-03, verificado)**: o handoff anterior dizia que os commits 3a/3b
estavam "NAO pushados / aguardando push+deploy do Rafael". **Isso ficou STALE**: `HEAD==origin/main`
(0/0) e o deploy `dep-d8g865eq1p3s73erk4m0` (commit `4b17efa6c`) esta **LIVE em PROD desde 19:47 de
03/06** — como `4b17efa6c` esta no topo de `72e0467d1`(3b)+`0332b8f95`(3a), **toda a Onda 3 (READ+WRITE+
gate) JA esta em PROD**. Logo o canary REAL (B) ja esta DESBLOQUEADO (nao depende mais de push/deploy).

**Onda 4 P10 FEITA (2026-06-03, commit `b716076e2`)**: `infra.py` (flags/gates/worker-status, READ).
O `flags` cruza DECLARADO [this-process] x **db_evidence [PROD via DB]** (env-independente) — fecha o
blind spot de que flags/Redis lidos LOCAL != PROD (medido: STEP_JUDGE/EVAL_GATE/DIRECTIVE_PROMOTION
declaradas OFF no .env local mas EFETIVAS em PROD via rastro DB). 66 ZERO-DB + 3 snapshot; review
adversarial (16 achados: 2 HIGH+5 MED+9 LOW) TODOS fechados. **P13 (gate cross-user) ja foi entregue
no 3b** via `_classify_gerindo_write`. Pendente da Onda 4: P4 (subagent-metrics, OBS-1 bloqueia
cost-breakdown), P11 (ontologia D4), P9 (rede destrutivas).

**Estado atual**: Ondas 0/1/2/3 LIVE em PROD; Onda 4 P10 commitado (`b716076e2`, NAO pushado por mim — push=Rafael).
**Onda 3 COMPLETA** (fase 3a READ + fase 3b WRITE, commits locais, NAO pushados):
- 3a (READ): `loop` (directives/corrections/loop-health), `eval` (scores/cases),
  `melhorias` (list-open/show/intelligence-report). Commit `0332b8f95`.
- 3b (WRITE dev-only, dry-run default + `--confirm`): `loop` (approve/reject/promote-batch),
  `eval` (review/run), `melhorias` (respond). **Gate TECNICO** em `can_use_tool`
  (`permissions.py` `_classify_gerindo_write`) NEGA o WRITE pelo agente web/Teams.
- Cobertura: **71 testes ZERO-DB** (54 skill + 17 gate) + **34 snapshots**. WRITE validado
  end-to-end contra banco local (approve shadow->ativa, review, respond+cascade). Review
  adversarial 3a (9 findings) + 3b (9 findings) — TODOS fechados.

**Verificacoes da sessao (perguntas do Rafael, confirmadas com fonte):**
- **Cache do prompt NAO e comprometido pelo `approve`** — diretrizes injetadas DINAMICAMENTE via hook
  `UserPromptSubmit` (`hooks.py:1460`), DEPOIS do prefixo estatico cacheado (`client.py:1663`/`:377`);
  `memory_injection.py:428-431` documenta a intencao. Alinhado a Anthropic.
- **Migration NAO falta** — PROD ja tem `directive_status` + Fase 3.1 + indice (acao Rafael = ZERO).
- **`debug_mode` nao reinventado** — e so transporte do bit admin (`permissions.py:86-98`); o gate WRITE
  usa allow-list/deny em `can_use_tool` (espelha `_classify_estoque_restricao`), NAO debug_mode.

**Gotchas fase 3b descobertos**: (a) `AgentMemory` NAO tem `reviewed_by` (so `reviewed_at`) — `AgentEvalCase`
TEM. (b) `_will_inject` deve espelhar TODO o filtro de `_build_operational_directives`: flag
`USE_OPERATIONAL_DIRECTIVES` + importance>=`MANDATORY_IMPORTANCE_THRESHOLD` + nivel-5 + `<prescricao>`/`DO:`
(senao o preview mente). (c) correcoes->mandatory injetam via canal L1 `<user_rules>` (`USE_USER_RULES_CHANNEL`),
INDEPENDENTE de `AGENT_OPERATIONAL_DIRECTIVES`. (d) `permissions.py` e exportado ao Teams.

**Proximo**: restante da Onda 4 (**P4** subagent-metrics — OBS-1 bloqueia cost-breakdown; **P11** ontologia
D4; **P9** rede de seguranca das destrutivas) OU **canary REAL do WRITE em PROD** (JA DESBLOQUEADO — deploy
live). Para o canary: usar `infra.py flags` primeiro (db_evidence confirma flags PROD), depois READ do funil +
preview do `<do>`; dos 5 shadows so o **id=846** ("Verificar pedidos com entrega vencida [3 passos]", eff=17)
e candidato real — os outros 4 sao auto-capturas de prompt cru ("Abordagem validada pelo judge: BOM DIA"...).

**RE-LER antes de codar (anti-drift)**:
- Esta secao + [Decisoes travadas](#decisoes-travadas) + [Ondas](#ondas) Onda 3 + [Gotchas](#gotchas).
- **Correcao critica de backing**: as funcoes de leitura/resposta do dialogo de melhoria sao
  metodos do MODELO `AgentImprovementDialogue` + a rota `app/agente/routes/improvement_dialogue.py`
  (PUT `/<id>/respond`, GET `/pending`) — **NAO** funcoes de `improvement_suggester` (que so tem
  `executar_batch_improvement`).
- **Guard `directive_status`** (gotcha `docs/blueprint-agente/EXECUCAO.md:373`): ligar
  `AGENT_OPERATIONAL_DIRECTIVES` sem a coluna desliga TODAS as diretrizes — `approve` muta o
  prompt PROD em tempo real (ALTO RISCO).
- `app/agente/CLAUDE.md`: ANTES de mexer em qualquer item do flywheel (judge/verify/triage/
  eval-gate A3/promocao A4), LER a spec do eixo (`docs/blueprint-agente/eixos/*.md`) + a critica.
- **Padroes reusaveis da Onda 2**: `common.run_handler` (boilerplate de main), `success_output`
  (envelope `{ok,command,data,warnings,errors}` — padrao para subcomandos NOVOS), `format_datetime`
  TZ-safe, fim de contexto-duplo via `current_app._get_current_object()`. Snapshot: regravar golden
  com `GERINDO_SNAPSHOT_RECORD=1 pytest tests/agente/test_gerindo_agente_snapshots.py`.

**Coordenacao (frente paralela ativa)**: Rafael trabalha em paralelo no `app/agente/`
(subagent_validator/hooks + `docs/blueprint-agente/*` + painel insights O0.3). Commitar com
`git commit -- <paths>` (only-mode) para nao varrer arquivos alheios; NAO entrar no territorio do
blueprint-agente. Push/deploy = decisao do Rafael (HEADs vem com `[skip render]`; deploy manual via
api/dashboard).

**Pendencias abertas** (ver [secao](#pendencias-de-decisao--itens-abertos)): OBS-1 (cost-breakdown
bloqueado por callsite `cost_tracker.insert_entry` nao-wired — sessao do agente web); subagent_validations
vazio (Rafael atacando via O0.2 "worker desacoplado do FS"); Eixo C vigilancia (NAO criar placeholder).

## Contexto e diagnostico

A skill (6 scripts, ~46 subcomandos) cobre bem o eixo CLASSICO (memorias, sessoes,
grafo HOP-1, diagnosticos derivados de `insights_service`), mas era **estruturalmente
cega** a toda a camada de evolucao/qualidade (Ondas 0-4 do blueprint, LIVE em PROD).

Verificacao dura (confirmada): `grep` dos termos `agent_step|outcome_signal|directive_status|
PlanState|agent_eval_scores|agent_invocation_metrics|subagent_validations|improvement_dialogue|
intelligence_report` nos 6 scripts retornava **ZERO**. `success_output` (common.py:138) e codigo
morto. Bug latente: `manutencao.summarize` chamava `summarize_session(app, ...)` (assinatura real
`summarize_session(messages, session_id)` -> TypeError; correto = `summarize_and_save(app, session_id, user_id)`).

Estudo completo (8 dimensoes, matriz de 29 gaps, critica adversarial): workflow
`evoluir-gerindo-agente` (run `wf_502874f6-823`, 2026-06-03). Findings detalhados estavam
em `/tmp/gerindo-agente-evo/` (efemeros).

## Censo PROD

(2026-06-03, banco `dpg-d13m38vfte5s738t6p50-a`) — calibra o que entrega valor hoje.

| Camada | Dado em PROD | Veredito |
|---|---|---|
| `agent_step` judge/verify/triage | **181 passos, 100% julgados** (3 dias, web-only; teams=0) | ALTO valor |
| PlanState (`agent_sessions.data.plan`) | **1 / 749** | gargalo B1 confirmado |
| directives shadow->ativa | 3 shadow / **0 ativa** / 5 mandatory | flywheel travado em Distill |
| rule-adhesion (`error_signature`) | 19 errsig, 4 corrections | sintoma Marcus mensuravel |
| `agent_improvement_dialogue` | **125** | ALTO valor |
| `agent_invocation_metrics` | 63 (10 subagentes) | tem dado |
| `agent_intelligence_reports` | 5 (ate 01/06) | serie existe |
| `agent_eval_scores` / `agent_eval_case` | 8 / **0** | score sim; calibracao nao rodou |
| `agent_session_costs` | **0** | OBS-1: cost-breakdown vazio (callsite nao wired) |
| `subagent_validations` (sessions.data) | **0** | vazio — investigar onde o worker grava |
| KG | 3617 ent / 7204 rel / 124 versions | rico |

Achado vivo: 1 step real teve `judge=success/85` MAS `verify.adversarial.refuted=true`
("ausencia de ferramenta nao justificavel em auditoria") — o vies sem-tool da avaliacao 360.

## Decisoes travadas

(Rafael, 2026-06-03)

1. **Escrita total** do flywheel via CLI (inclusive `approve shadow->ativa` e `promote-batch`),
   atras de `--confirm` + guard da coluna `directive_status` (gotcha EXECUCAO.md:373 —
   ligar `AGENT_OPERATIONAL_DIRECTIVES` sem a coluna desliga TODAS as diretrizes).
2. **Observar + disparar** workers (run-eval, promote-batch, rejudge) atras de `--confirm` + aviso de custo.
3. **Gate cross-user** para o agente web (espelha `get_debug_mode()` em `app/agente/config/permissions.py:96`),
   **livre para o dev** (Claude Code).
4. Sequencia **Censo PROD -> Onda READ** (censo feito).

## Ondas

### Onda 1 — READ alto valor + bugfix (FEITA, 2026-06-03)
- `diagnostico.py`: +`step-quality`, +`step-coverage`, +`rule-adhesion`, +`routing`, +`recommendations`
  (todos com `--days` e `--all`; distinguem `empty`/`query_error` de zero).
- `manutencao.py`: bugfix `summarize` (-> `summarize_and_save`, reusa app context, fim do contexto-duplo).
- `tests/agente/test_gerindo_agente_skill.py`: 18 testes deterministicos (ZERO DB/token; importlib + contrato + bugfix + safety).
- SKILL.md (description + decision tree + tabela) e SCRIPTS.md (TOC + corpo) atualizados.
- Validado: 5 subcomandos rodam end-to-end contra o banco local; 18/18 pytest verdes.

### Onda 2 — rede de seguranca + consolidacao (FEITA, 2026-06-03)
- **P12** ✅ rede de seguranca de snapshot: `tests/agente/test_gerindo_agente_snapshots.py`
  trava o shape `--json` (esqueleto de tipos, valores ignorados) de 26 subcomandos READ pelo
  caminho REAL `main()`/`run_handler` (subprocess, NAO in-process — para exercitar o codigo que o
  P8 refatora). Golden: `tests/agente/snapshots/gerindo_agente_json_shapes.json`. DB-bound, SKIPa
  sem `.env` (preserva o fast-path ZERO-DB). Tolerante a dado esparso (open-map `<map>` / empty-list
  `<empty>` / null) SEM mascarar regressao estrutural (null so tolera escalar — fix do review). Os
  2 evals orfaos foram removidos (commit `2dfc16b00`). Baseline gravado PRE-refactor; compare
  pos-refactor PROVOU 25/25 legados inalterados.
- **P7** ✅ `diagnostico.py status` (agregador canonico): chama `get_insights_data` 1x + `get_memory_metrics`
  1x (traz grafo stats via `knowledge_graph`) + `_memoria_stats` + `_embedding_coverage` + `_loop_health`
  — consolida os 8 (stats+memory-metrics+grafo.stats+embedding-coverage+health+friction+rule-adhesion+
  loop-health), elimina as 3 chamadas redundantes a `get_insights_data` (insights/health/recommendations).
  `--all`-safe (`(:uid IS NULL OR ...)`); sinaliza gargalo B1; emite envelope canonico em `--json`.
- **P8** ✅ refator `common.py`: `success_output` revivido como envelope `{ok,command,data,warnings,errors}`
  (era codigo morto), `run_handler` (centraliza parse->1 ctx->resolve->dispatch), `format_datetime`
  TZ-safe (aware->BRT, naive inalterado=snapshot-safe), `error_exit` -> `NoReturn`. `padrao.py` migrado
  (1 script por vez): fim do contexto-duplo em analyze/extract/profile via `current_app._get_current_object()`
  — mesmo padrao da Onda 1 (`manutencao.summarize`), NAO `run_handler`-passa-app (menor churn, snapshot-safe).
- **Cobertura**: 24 testes ZERO-DB (contrato) + 26 snapshots DB-bound. Review adversarial (5 dims +
  verificacao cetica): 4 dims aprovadas; 1 HIGH (null wildcard mascarava crescimento estrutural) + 1
  MEDIUM (RECORD podia gravar shape de erro) + 1 LOW (memoria-stats) — TODOS fechados.

### Onda 3 fase 3a — flywheel READ-first (FEITA, 2026-06-03)
3 scripts novos SOMENTE LEITURA (escrita = fase 3b). Padrao Onda 2 (`run_handler` + envelope
`success_output` + degradacao graciosa + LAZY `from app import db`). Dicts data-driven evitados
(schema FIXO em `por_status`/`by_status`/`directive_funnel`/`latest`+`has_report`) — snapshot estavel
local-vs-PROD. `melhorias.show` FORA do snapshot (shape exists/nao-exists, so contrato ZERO-DB).
- **loop.py**: `directives` (funil shadow/ativa/legado, espelha `_build_operational_directives`),
  `corrections` (candidatas a `mandatory`, threshold `AGENT_CORRECTION_PROMOTION_THRESHOLD`),
  `loop-health` (PlanState gargalo B1 + funil + prontidao promocao + flags).
- **eval.py**: `scores` (agent_eval_scores + delta vs baseline), `cases` (agent_eval_case + concordancia).
- **melhorias.py**: `list-open` (`get_open_by_category`), `show --key` (historico v1/v2/v3),
  `intelligence-report` (`get_latest` + serie por `report_date` + top recs).
- **Cobertura**: 45 testes ZERO-DB + 33 snapshots DB-bound (golden regravado cirurgicamente, 26
  legados intactos). Validado local + cross-check PROD. SKILL.md/SCRIPTS.md atualizados (so READ).

### Onda 3 fase 3b — flywheel WRITE (dev-only) — FEITA (2026-06-03)
Padrao universal: **dry-run e o DEFAULT**; so escreve com `--confirm` (preview sem ele).
- **loop.py**: `approve` (shadow->`ativa`, **ALTO RISCO** prompt vivo — preview com `_will_inject` fiel
  ao filtro real + TOCTOU `with_for_update` + try/except commit), `reject` (->`despromovida`),
  `promote-batch` (wrapper de `run_directive_promotion_batch:790`; preview do funil + flags incl.
  `USE_USER_RULES_CHANNEL`). `AgentMemory` NAO tem `reviewed_by` — so `reviewed_at`.
- **eval.py**: `review` (ESCRITA `human_verdict`/`reviewed_by` em `agent_eval_case` — fecha gap
  `eval_runner.py:715-783`; aviso de sobrescrita), `run` (enqueue `enqueue_eval_batch`, custo Haiku+Opus,
  gated `AGENT_EVAL_GATE`).
- **melhorias.py**: `respond` via `AgentImprovementDialogue.upsert_response:1334` (cascade p/ v1; aviso de
  sobrescrita de v2). Backing = MODELO + rota, NAO `improvement_suggester`.
- **Gate TECNICO** (review 3b finding HIGH): `can_use_tool` `_classify_gerindo_write` (`permissions.py`)
  NEGA o WRITE pelo agente web/Teams (Bash). Dev-CLI livre (nao passa por can_use_tool). Teste
  `tests/agente/test_gerindo_write_gate.py`. `permissions.py` e exportado ao Teams.
- Cobertura: 71 ZERO-DB + 34 snapshots; WRITE validado end-to-end contra banco local.

### Onda 4 — observabilidade infra + seguranca + ontologia
- **P4**: `subagent-metrics` (metrics_dashboard_service, 11 endpoints, 63 metrics) + `subagent-validations`
  (sessions.data — hoje 0, degradar) ; `cost-breakdown` BLOQUEADO por **OBS-1** (wirar callsite
  `cost_tracker.insert_entry` no caminho principal de `client.py` — agent_session_costs vazia; sessao separada).
- **P10** ✅ FEITA (2026-06-03, commit `b716076e2`): `infra.py` `flags`/`gates`/`worker-status` (READ).
  - `flags`: EVOLUTION_FLAGS (19: Ondas 0-4 + atuador + loop corretivo, fonte `feature_flags.py`) com
    DECLARADO [this-process] x **db_evidence [PROD via DB]** (env-independente — fecha o blind spot).
    `kind` activity (rastro=flag EFETIVA: judge/verify/frustration agent_step, eval_scores, shadows,
    mandatory) vs readiness (atuador injecao sem rastro: directives_injetaveis, mandatory_rules) vs None.
  - `gates`: gerindo_write (always_deny dos 6 WRITE), estoque_restricao (+allow-list), debug_mode,
    reversibility (warn), hard_enforce — shape homogeneo, `[this-process]`.
  - `worker-status`: filas RQ agente + workers; degrada se Redis off (shape fixo, nunca query_error).
  - Gotchas/anti-drift codificados: db_evidence homogeneo (snapshot nao colapsa); confronto text-only
    de EVOLUTION_FLAGS + GERINDO_WRITE_BLOCKED contra a fonte; deteccao PROD inclui host interno Render
    (`dpg-`/`red-`/`RENDER` env). Review adversarial 16 achados (2 HIGH+5 MED+9 LOW) fechados.
- **P13** ✅ FEITA (entregue na Onda 3 fase 3b): gate cross-user via `_classify_gerindo_write` em
  `app/agente/config/permissions.py` — NEGA WRITE pelo agente web/Teams, dev-CLI livre. O subcomando
  `gates` (P10) agora EXPOE esse gate. Nada a fazer aqui.
- **P11**: `grafo.py` ontologia D4 (`query_ontology`) + provenance bi-temporal + bootstrap (WRITE idempotente)
  + fix `grafo.relations` (target nao aparece) e filtro `user_id` em `grafo.query`.
- **P9**: rede de seguranca destrutivas (pre-contagem + export + cascade) + `gc-cold`/`gc-all`/`cleanup-empresa`.
  Fix cascade no delete = item ISOLADO com teste-contra-banco (maior risco de regressao).

### Onda 5 — posicionamento
- **P14**: revisar description (budget 16K), ROUTING_SKILLS.md, `tool_skill_mapper.py`; mover
  `SCRIPTS.md` para `references/SCRIPTS.md`; SKILL.md FEATURE FLAGS -> apontar para subcomando `flags`.

## Pendencias de decisao / itens abertos
- **OBS-1**: wirar `cost_tracker.insert_entry` no caminho principal e pre-requisito de `cost-breakdown` (Onda 4)
  — confirmar se entra no escopo desta frente ou e sessao do agente web.
- **subagent_validations vazio**: investigar onde `subagent_validator.py:168` realmente grava (sessions.data=0 em PROD).
- **Eixo C (vigilancia temporal)**: destino designado e `gerindo-agente`, mas `memory_vigilance_event`/job
  ainda NAO existem — NAO criar placeholder que finge vigilancia inexistente.

## Gotchas

(codificar nos subcomandos)

- TZ: `agent_step.created_at` e UTC-naive (`agora_utc_naive`); `agent_sessions.created_at` pode ser BRT-naive
  (gap falso ~3h). Usar `app.utils.timezone.agora_utc_naive` (hook `ban_datetime_now` bloqueia `datetime.now/utcnow`).
- `outcome_signal` e `db.JSON` -> castar `::jsonb` nas queries.
- Scripts importam `app` LAZY (dentro de funcoes) -> pytest via importlib NAO dispara create_app.
- `agent_sessions` NAO tem coluna `channel` (Teams = prefixo `teams_` no `session_id`).
