<!-- doc:meta
tipo: how-to
camada: L2
sot_de: evolucao da skill gerindo-agente (roadmap por ondas)
hub: .claude/skills/gerindo-agente/SKILL.md
superseded_by: —
atualizado: 2026-06-03
-->
# Roadmap — Evolucao da skill `gerindo-agente` para top-level

> **Papel:** plano vivo (multi-sessao) de evolucao da skill `gerindo-agente`,
> de fachada da geracao CLASSICA para a superficie UNICA de gestao/introspeccao
> do Agente Web (incluindo a camada de evolucao/qualidade que ja roda em PROD).

## Indice

- [Contexto e diagnostico](#contexto-e-diagnostico)
- [Censo PROD](#censo-prod)
- [Decisoes travadas](#decisoes-travadas)
- [Ondas](#ondas)
- [Pendencias de decisao / itens abertos](#pendencias-de-decisao--itens-abertos)
- [Gotchas](#gotchas)

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

### Onda 2 — rede de seguranca + consolidacao
- **P12 (pre-requisito ja iniciado na Onda 1)**: estender pytest com SNAPSHOTS do shape `--json`
  ATUAL de cada subcomando legado, ANTES de refatorar `common.py`. Remover/converter os 2 evals
  orfaos (`evals/evals.json`, `evals/trigger_eval_set.json` — lixo, nenhum harness le).
- **P7**: `diagnostico.py status` (agregador canonico) — consolida stats+memory-metrics+grafo.stats+
  embedding-coverage+health+friction+rule-adhesion+loop-health; elimina 4 duplicacoes de metrica.
  Cuidado: chamar `get_insights_data` 1x e fatiar (nao N vezes).
- **P8**: refator `common.py` — reviver `success_output` (envelope `{ok,command,data,warnings,errors}`),
  `run_handler` (recebe app/ctx do main, fim do contexto-duplo em padrao.analyze/extract/profile),
  `format_datetime` TZ-safe. SO depois do snapshot/pytest travar o shape. 1 script por vez.

### Onda 3 — flywheel WRITE (escrita total autorizada)
- **loop.py** (novo): `directives` (lista shadow), `approve --confirm` (shadow->ativa, com guard
  `directive_status`), `reject --confirm`, `corrections`, `promote-batch --confirm` (wrapper de
  `directive_promotion_service.run_directive_promotion_batch`), `loop-health` (sinaliza PlanState gargalo).
  ALTO RISCO: `approve` muta o prompt PROD em tempo real (AGENT_OPERATIONAL_DIRECTIVES ON).
- **eval.py** (novo): `scores` (agent_eval_scores), `cases` (agent_eval_case — hoje 0), `review --confirm`
  (ESCRITA `human_verdict`/`reviewed_by` — fecha o gap de UPDATE SQL manual, `eval_runner.py:715-783`),
  `run --confirm` (dispara `eval_runner`, custo Haiku, subagente real).
- **melhorias.py** (novo): `list-open`/`list-rejected`/`show` + `respond --confirm` sobre
  `agent_improvement_dialogue` (125 registros) + `intelligence-report` (le `AgentIntelligenceReport.get_latest`
  + serie por `report_date`). **CORRECAO de backing (critica)**: as funcoes de leitura/resposta sao
  metodos do MODELO `AgentImprovementDialogue` + a rota `routes/improvement_dialogue.py` (PUT /<id>/respond,
  GET /pending) — NAO funcoes de `improvement_suggester` (que so tem `executar_batch_improvement`).

### Onda 4 — observabilidade infra + seguranca + ontologia
- **P4**: `subagent-metrics` (metrics_dashboard_service, 11 endpoints, 63 metrics) + `subagent-validations`
  (sessions.data — hoje 0, degradar) ; `cost-breakdown` BLOQUEADO por **OBS-1** (wirar callsite
  `cost_tracker.insert_entry` no caminho principal de `client.py` — agent_session_costs vazia; sessao separada).
- **P10**: `flags`/`gates`/`worker-status` (estado real das 13 flags de evolucao + filas RQ).
- **P13**: gate cross-user via `get_debug_mode()` (**target_file correto: `app/agente/config/permissions.py`**,
  NAO feature_flags.py) — agente web bloqueado, dev livre.
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
