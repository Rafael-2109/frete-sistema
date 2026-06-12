<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/skills/gerindo-agente/SKILL.md
superseded_by: —
atualizado: 2026-06-12
-->
# SCRIPTS.md — Referencia Unificada de Parametros

> **Papel:** SCRIPTS.md — Referencia Unificada de Parametros.

## Indice

- [Argumentos Comuns (todos os scripts)](#argumentos-comuns-todos-os-scripts)
- [memoria.py](#memoriapy)
  - [view](#view)
  - [save](#save)
  - [update](#update)
  - [delete](#delete)
  - [list](#list)
  - [clear](#clear)
  - [search-cold](#search-cold)
  - [versions](#versions)
  - [restore](#restore)
  - [resolve-pendencia](#resolve-pendencia)
  - [log-pitfall](#log-pitfall)
  - [stats](#stats)
  - [aposentar](#aposentar)
- [sessao.py](#sessaopy)
  - [list](#list)
  - [search](#search)
  - [semantic](#semantic)
  - [view](#view)
  - [summary](#summary)
  - [users](#users)
  - [delete](#delete)
- [padrao.py](#padraopy)
  - [patterns](#patterns)
  - [pitfalls](#pitfalls)
  - [analyze](#analyze)
  - [extract](#extract)
  - [empresa](#empresa)
- [grafo.py](#grafopy)
  - [query](#query)
  - [entities](#entities)
  - [links](#links)
  - [relations](#relations)
  - [stats](#stats)
- [diagnostico.py](#diagnosticopy)
  - [insights](#insights)
  - [memory-metrics](#memory-metrics)
  - [health](#health)
  - [effectiveness](#effectiveness)
  - [cold-candidates](#cold-candidates)
  - [promotion-candidates](#promotion-candidates)
  - [conflicts](#conflicts)
  - [embedding-coverage](#embedding-coverage)
  - [friction](#friction)
  - [briefing](#briefing)
  - [step-quality](#step-quality)
  - [step-coverage](#step-coverage)
  - [rule-adhesion](#rule-adhesion)
  - [routing](#routing)
  - [recommendations](#recommendations)
  - [status](#status)
- [manutencao.py](#manutencaopy)
  - [consolidate](#consolidate)
  - [cold-move](#cold-move)
  - [summarize](#summarize)
  - [reindex-memories](#reindex-memories)
  - [reindex-sessions](#reindex-sessions)
  - [cleanup-orphans](#cleanup-orphans)
- [loop.py (flywheel A4 — READ)](#looppy-flywheel-a4--read)
  - [directives](#directives)
  - [corrections](#corrections)
  - [loop-health](#loop-health)
- [eval.py (eval-gate A3 — READ)](#evalpy-eval-gate-a3--read)
  - [scores](#scores)
  - [cases](#cases)
- [melhorias.py (dialogo D8 + report D7 — READ)](#melhoriaspy-dialogo-d8--report-d7--read)
  - [list-open](#list-open)
  - [show](#show)
  - [intelligence-report](#intelligence-report)
- [infra.py (observabilidade infra e seguranca — READ, P10)](#infrapy-observabilidade-infra-e-seguranca--read-p10)
  - [flags](#flags)
  - [gates](#gates)
  - [worker-status](#worker-status)
- [WRITE (dev-only — fase 3b)](#write-dev-only--fase-3b)
  - [loop.approve / loop.reject](#loopapprove--loopreject)
  - [loop.promote-batch](#looppromote-batch)
  - [eval.review](#evalreview)
  - [eval.run](#evalrun)
  - [melhorias.respond](#melhoriasrespond)

## Argumentos Comuns (todos os scripts)

| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--user-id` | int | Sim | — | ID do usuario no banco |
| `--json` | flag | Nao | false | Saida em formato JSON |
| `--limit` | int | Nao | 20 | Limite de resultados |

---

## memoria.py

### view
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Nao | /memories | Path da memoria |

### save
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |
| `--content` | str | Sim | — | Conteudo da memoria |
| `--skip-dedup` | flag | Nao | false | Pular verificacao de duplicata |

Apos salvar, executa best-effort: dedup check (warning se duplicata), embedding Voyage AI, e pitfall hint detection. Paridade com MCP tool `save_memory`.

### update
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |
| `--old` | str | Sim | — | Texto a substituir (match unico) |
| `--new` | str | Sim | — | Texto novo |

### delete
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |
| `--confirm` | flag | Sim | false | Confirmar exclusao |

### list
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--include-cold` | flag | Nao | false | Incluir tier frio |
| `--category` | str | Nao | None | Filtrar por categoria |

### clear
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--confirm` | flag | Sim | false | Confirmar limpeza total |

### search-cold
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--query` | str | Sim | — | Termo de busca |

### versions
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |

### restore
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |
| `--version` | int | Sim | — | Numero da versao |

### resolve-pendencia
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--description` | str | Sim | — | Descricao da pendencia |

### log-pitfall
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--area` | str | Sim | — | Area (odoo, ssw, banco, api, deploy, sistema) |
| `--description` | str | Sim | — | Descricao do pitfall |

### stats
Sem argumentos adicionais.

### aposentar
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |
| `--promovida-para` | str | Sim | — | Artefato destino (reference/codigo) que absorveu o conteudo |
| `--user-id` | int | Nao | **0** | Dono da memoria (override do comum; 0 = empresa) |
| `--confirmar` | flag | Nao | false | Efetiva (sem isso = **dry-run**, mostra before/after) |

WRITE com **dry-run DEFAULT**. Aposenta memoria promovida a reference/codigo (trilho
memoria→reference do PAD-CTX): versiona o conteudo ANTES de mutar
(`changed_by='aposentadoria-manual'`), seta `is_cold=True` + `meta.promovida_para`
(`flag_modified`) e commita. A memoria sai da injecao/busca semantica; historico segue
via `search-cold`/`versions`. Fila de candidatas: `diagnostico.py promotion-candidates`.
Criterios/fluxo: `ARQUITETURA_CONTEXTO_AGENTE.md` §Memorias + `MEMORY_PROTOCOL.md`
§Promocao Memoria -> Reference.

---

## sessao.py

### list
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--channel` | str | Nao | None | Filtrar: teams ou web |

### search
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--query` | str | Sim | — | Termo de busca |
| `--channel` | str | Nao | None | Filtrar: teams ou web |

### semantic
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--query` | str | Sim | — | Consulta semantica |

### view
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--session-id` | str | Sim | — | ID da sessao |

### summary
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--session-id` | str | Sim | — | ID da sessao |

### users
Sem argumentos adicionais (admin).

### delete
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--session-id` | str | Sim | — | ID da sessao |
| `--confirm` | flag | Sim | false | Confirmar exclusao |

---

## padrao.py

### patterns
Sem argumentos adicionais.

### pitfalls
Sem argumentos adicionais.

### analyze
Sem argumentos adicionais. Chama Sonnet (~$0.006).

### extract
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--session-id` | str | Sim | — | ID da sessao |

### empresa
Sem argumentos adicionais. Lista memorias com user_id=0.

---

## grafo.py

### query
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--prompt` | str | Sim | — | Consulta em linguagem natural |

### entities
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--type` | str | Nao | None | Tipo de entidade |

### links
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--entity-id` | int | Sim | — | ID da entidade |

### relations
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--entity-name` | str | Nao | None | Filtrar por nome |

### stats
Sem argumentos adicionais.

---

## diagnostico.py

### insights
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |

### memory-metrics
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |

### health
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |

### effectiveness
Sem argumentos adicionais.

### cold-candidates
Sem argumentos adicionais.

### promotion-candidates
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--min-effective` | int | Nao | 2 | Minimo de `effective_count` |
| `--idade-dias` | int | Nao | 30 | Idade minima desde `created_at` (dias) |
| `--limit` | int | Nao | **30** | Limite de resultados (override do comum) |

Fila de candidatas a **promocao memoria→reference** (trilho PAD-CTX, cadencia quinzenal).
Query READ-only sobre memorias EMPRESA (`user_id=0`): `correction_count >= 2 OU
effective_count >= --min-effective`, idade >= `--idade-dias`, nao-cold, nao-diretorio e
SEM `meta.promovida_para` (ja promovidas saem da fila). Output: path | kind/dominio |
effective | correction | idade_dias | titulo. A query SUGERE; quem promove e revisao
humana — pos-promocao, aposentar a origem com `memoria.py aposentar`. Custo $0.

### conflicts
Sem argumentos adicionais.

### embedding-coverage
Sem argumentos adicionais.

### friction
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |

Mostra 5 sinais de friccao: queries repetidas, sessoes abandonadas, sinais de frustracao, sessoes sem tools, e score geral (0-100). Controlado pela flag `USE_FRICTION_ANALYSIS`.

### briefing
Sem argumentos adicionais.

Mostra o briefing intersessao atual (XML): erros Odoo, falhas de importacao, alertas de memoria, commits recentes e ultimo intent. Controlado pela flag `USE_INTERSESSION_BRIEFING`.

### step-quality
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |
| `--all` | flag | Nao | false | Escopo do sistema inteiro (todos os usuarios) |

Le `agent_step.outcome_signal` (gravado por `workers/step_judge.py` + `plan_verifier.py`). Agrega judge score/label, contagem de `componente_culpado`, adversarial refutado, frustracao alta, e o contraste **judge=success MAS adversarial refutou** (vies sem-tool). Distingue `empty` de erro. READ-only, custo $0.

### step-coverage
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |
| `--all` | flag | Nao | false | Escopo do sistema inteiro (todos os usuarios) |

Cobertura de sinal por canal (web/teams) + gargalo PlanState (sessoes com `data->'plan'`). Revela lacunas estruturais: canal Teams nao instrumentado em `agent_step`, e B1 (PlanState ~0 -> promocao A4 vira no-op). READ-only, custo $0.

### rule-adhesion
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |
| `--all` | flag | Nao | false | Escopo do sistema inteiro (todos os usuarios) |

Chama `insights_service.get_rule_adhesion_panel`. Mede o loop corretivo pessoal (sintoma Marcus): reincidencia por `error_signature` ANTES (`correction_count`) vs DEPOIS (`harmful_count`) da promocao a regra dura (`mandatory`). Degrada com graca se as colunas da Fase 3.1 ausentes. READ-only, custo $0.

### routing
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |
| `--all` | flag | Nao | false | Escopo do sistema inteiro (todos os usuarios) |

Chama `insights_service.get_routing_metrics`. Taxa de ambiguidade (AskUserQuestion), sessoes struggling (volume alto de msgs, poucos tools), distribuicao de skills, instrumentacao. Distribuicao completa via `--json`. READ-only, custo $0.

### recommendations
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |
| `--all` | flag | Nao | false | Escopo do sistema inteiro (todos os usuarios) |

Compoe `insights_service.get_insights_data` + `recommendations_engine.generate_recommendations` — lista COMPLETA (ate 5, ordenada por severidade), diferente de `insights` que trunca a 3. READ-only, custo $0.

### status
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |
| `--all` | flag | Nao | false | Escopo do sistema inteiro (todos os usuarios) |

**Agregador canonico** (Onda 2). Chama `get_insights_data` UMA UNICA vez e fatia health/friction/resolution/adoption/overview/deltas/recommendations/rule_adhesion — eliminando as 3 chamadas redundantes de `insights`/`health`/`recommendations`. Soma `memory-metrics` (+ grafo stats via `knowledge_graph`), `embedding-coverage` e loop-health/PlanState (sinaliza gargalo B1). Em `--json` emite o **envelope canonico** `{ok, command, data, warnings, errors}`. READ-only, custo $0.

---

## manutencao.py

### consolidate
Sem argumentos adicionais. Chama Sonnet (~$0.006).

### cold-move
Sem argumentos adicionais.

### summarize
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--session-id` | str | Sim | — | ID da sessao |

### reindex-memories
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--reindex` | flag | Nao | false | Forcar reindexacao total |

### reindex-sessions
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--reindex` | flag | Nao | false | Forcar reindexacao total |

### cleanup-orphans
Sem argumentos adicionais.

---

## loop.py (flywheel A4 — READ)

> **READ-only (Onda 3 fase 3a).** Inspeciona a camada A4 (Distill -> Deploy) do
> blueprint. A ESCRITA (`approve` shadow->ativa, `reject`, `promote-batch`) e
> **dev-only** e NAO existe aqui — `approve` muta o prompt PROD em tempo real (fase 3b).

### directives
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--status` | str | Nao | all | Filtra por status: `shadow`/`ativa`/`legado`/`candidata`/`despromovida`/`all` |

Funil de diretrizes-empresa (`user_id=0`, paths `/heuristicas/` e `/protocolos/`). Espelha o filtro de `memory_injection._build_operational_directives`: mostra o que ESTA sendo injetado no prompt (status `NULL`/legado ou `ativa`, `importance>=0.7`, nao-cold) vs o que aguarda revisao (`shadow`/`candidata`) ou foi rebaixado (`despromovida`). `por_status` tem schema fixo; `injetaveis` e um teto (antes do filtro de conteudo nivel-5). READ-only, custo $0.

### corrections
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Janela por `created_at` em dias |
| `--all` | flag | Nao | false | Escopo do sistema inteiro (todos os usuarios) |

Correcoes (`/memories/corrections/`) candidatas a regra dura. `promovivel` = `correction_count >= AGENT_CORRECTION_PROMOTION_THRESHOLD` (default 2) e `priority != mandatory` e nao-cold — espelha `directive_promotion_service.promover_correcoes_recorrentes`. READ-only, custo $0.

### loop-health
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Janela por `created_at` em dias |
| `--all` | flag | Nao | false | Escopo do sistema inteiro (todos os usuarios) |

Saude do flywheel: PlanState (`% de sessoes com data->'plan'`; `<5%` => gargalo B1, promocao A4 vira no-op) + funil de diretrizes + prontidao de promocao + estado das flags (`AGENT_DIRECTIVE_PROMOTION`, `USE_AGENT_PLANNER`, `AGENT_CORRECTION_PROMOTION`). READ-only, custo $0.

---

## eval.py (eval-gate A3 — READ)

> **READ-only (Onda 3 fase 3a).** A ESCRITA (`review` `human_verdict`, `run` que
> dispara `eval_runner` com custo Haiku+Opus) e **dev-only** e fica para a fase 3b.
> `--user-id` e exigido por uniformidade do skill (R1, valida o chamador) mas **NAO filtra**:
> `agent_eval_scores`/`agent_eval_case` sao system-wide (use `--agent` para filtrar por agente).

### scores
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--agent` | str | Nao | — | Filtra por `agent_name` (default: todos) |

Ultimo run por agente (`agent_eval_scores`) + `delta_vs_prev` vs o run anterior (baseline, `models.py:get_baseline_score`) + modo (`report_only`/`enforce`) + contagem de runs. READ-only, custo $0.

### cases
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--agent` | str | Nao | — | Filtra por `agent_name` |
| `--status` | str | Nao | — | Filtra por `pass`/`fail`/`error` |

Casos por run (`agent_eval_case`) + `human_verdict` + taxa de concordancia judge-vs-humano (`concordance_rate`, calibracao). Em PROD a tabela hoje tem 0 linhas (`USE_AGENT_EVAL_CALIBRATION` OFF) — degrada para lista vazia sem erro. READ-only, custo $0.

---

## melhorias.py (dialogo D8 + report D7 — READ)

> **READ-only (Onda 3 fase 3a).** A ESCRITA (`respond` accept/reject) e **dev-only**
> (fase 3b). Backing da resposta = `AgentImprovementDialogue.upsert_response`
> (`models.py:1334`) / rota PUT `/<id>/respond` — **NAO** `improvement_suggester`.
> `--user-id` e exigido por uniformidade do skill (R1, valida o chamador) mas **NAO filtra**:
> `agent_improvement_dialogue`/`agent_intelligence_reports` sao system-wide.

### list-open
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--category` | str | Nao | — | Filtra por categoria (`skill_suggestion`/`instruction_request`/...) |

Sugestoes abertas (`status in proposed/responded`, `version=1`) ordenadas por severidade — fonte `AgentImprovementDialogue.get_open_by_category`. READ-only, custo $0.

### show
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--key` | str | **Sim** | — | `suggestion_key` (ex: `IMP-2026-06-03-001`) |

Historico completo (v1/v2/v3) de uma `suggestion_key`: author, status, title, description, `affected_files`, `implementation_notes`. Shape estavel (`found` + `versions[]`). READ-only, custo $0.

### intelligence-report
Sem argumentos adicionais (usa `--limit` para o tamanho da serie).

Relatorio D7 mais recente (`AgentIntelligenceReport.get_latest`) + serie por `report_date` (montada por query — o modelo nao tem `get_series`) + top 5 recomendacoes de `report_json['recommendations']`. `latest` tem schema fixo (escalares null sem report) + flag `has_report`. READ-only, custo $0.

---

## infra.py (observabilidade infra e seguranca — READ, P10)

> **READ-only (Onda 4 / P10).** Estado operacional do Agente Web. **HONESTIDADE DE AMBIENTE**:
> flags e Redis sao lidos do AMBIENTE DO PROCESSO (rodado pelo agente web em PROD = reflete PROD;
> rodado por dev local = reflete LOCAL). O **banco** e a unica fonte PROD-verdadeira quando rodado
> local (`DATABASE_URL` aponta p/ PROD) — por isso `flags` cruza o declarado `[this-process]` com
> `db_evidence` `[PROD via DB]`. O campo `scope` em cada subcomando rotula a procedencia.

### flags
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Janela (dias) p/ a evidencia time-bound (`agent_step`/PlanState) |

Flags de evolucao (blueprint Ondas 0-4 + atuador + loop corretivo — fonte: secoes rotuladas em `feature_flags.py`). Por flag: `declared` (valor NESTE processo), `env_var`, `default` e **`db_evidence`** — o estado EFETIVO em PROD inferido do rastro no BANCO (env-INDEPENDENTE). `db_evidence.kind`: `activity` (a atividade da flag escreve a metrica -> rastro>0 = flag EFETIVA em PROD: ex. `agent_step` judged, `agent_eval_scores`, diretrizes `shadow`) vs `readiness` (atuador de injecao SEM rastro de injecao no DB -> a metrica mede o CONTEUDO pronto p/ injetar, NAO o estado da flag: `USE_OPERATIONAL_DIRECTIVES`/`USE_USER_RULES_CHANNEL`). Flags sem rastro DB limpo -> `db_evidence: null` (honesto, sem proxy enganoso). READ-only, custo $0. **Supersede a tabela estatica "FEATURE FLAGS RELEVANTES" da SKILL.md** (que driftava).

### gates
Sem argumentos adicionais.

Gates de acesso runtime (`permissions.py` + flags de enforcement): `gerindo_write` (NEGA o agente web/Teams executar via Bash os WRITE da skill — `always_deny`), `estoque_restricao` (+ allow-list `ESTOQUE_RESTRICAO_ALLOWED_USER_IDS`, kill-switch `AGENT_ESTOQUE_RESTRICAO_ENFORCEMENT`), `debug_mode` (ContextVar por sessao — `enabled=null`, so admin), `reversibility_check` (`USE_REVERSIBILITY_CHECK`), `mandatory_hard_enforce` (`USE_MANDATORY_HARD_ENFORCE`). Cada gate: `enforcement`/`enabled`/`flag`/`allow_list`/`blocks`/`source` (shape homogeneo). enforcement/flags sao `[this-process]`. READ-only, custo $0.

### worker-status
Sem argumentos adicionais.

Filas RQ do agente (`agent_judge`/`agent_eval`/`agent_validation`/`agent_background`/`artifacts`) com profundidade (`queued`/`started`/`failed`) + workers vivos (`Worker.all`). Le o Redis DESTE processo (`scope.redis_target` rotula local vs PROD). **Degrada com graca** se Redis off: `reachable=false` + `queues`/`workers` vazios + warning (shape FIXO — nunca `status=query_error`). READ-only, custo $0.

---

## WRITE (dev-only — fase 3b)

> **NAO exposto ao agente web** (Opcao A — fora do decision tree da SKILL.md). Operado pelo
> Claude Code via CLI. **`--dry-run` e o DEFAULT**: sem `--confirm`, o handler mostra o PREVIEW
> do que mudaria e NAO escreve. Com `--confirm`, efetiva + commita. Todos validados end-to-end
> contra o banco local (review fase 3b).
>
> **Gate TECNICO** (nao so a nota acima): `can_use_tool` (`app/agente/config/permissions.py`
> `_classify_gerindo_write`) NEGA qualquer Bash do agente web/Teams que invoque um destes
> subcomandos. O Claude Code CLI nao passa por `can_use_tool` -> dev livre. Cobertura:
> `tests/agente/test_gerindo_write_gate.py`. Mutacoes em `permissions.py` sao exportadas ao Teams.

### loop.approve / loop.reject
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--id` | int | **Sim** | — | ID da AgentMemory (diretriz) |
| `--confirm` | flag | Nao | false | Efetiva (sem isso = dry-run/preview) |

`approve`: shadow -> **ativa** — **MUTA O PROMPT VIVO** (todos os usuarios). So aceita status `shadow`.
O preview mostra o `<do>` + se a diretriz REALMENTE sera injetada (`will_inject` = nivel-5 + importance>=0.7 +
nao-cold, espelha `_build_operational_directives`); avisa se for NO-OP de injecao. Seta `directive_status='ativa'`
+ `reviewed_at` (AgentMemory **nao tem** `reviewed_by` — o "quem" fica no log da CLI). `reject`: shadow/candidata
-> `despromovida` (nao injetada).

### loop.promote-batch
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--lookback-hours` | int | Nao | 24 | Janela do batch em horas |
| `--confirm` | flag | Nao | false | Executa (sem isso = preview do estado) |

Roda `directive_promotion_service.run_directive_promotion_batch`. Cria shadows (PlanState/judge — nao
injetadas) **E promove correcoes recorrentes a `mandatory`** (estas SAO injetadas via `<user_rules>`).
Usa `--limit` (comum, default 20) como teto do batch. O batch commita internamente.

### eval.review
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--case-id` | int | **Sim** | — | ID do agent_eval_case |
| `--verdict` | str | **Sim** | — | `agree` ou `disagree` (concorda/discorda do judge) |
| `--note` | str | Nao | — | Nota livre |
| `--confirm` | flag | Nao | false | Grava o veredito |

Fecha o gap do UPDATE manual (`eval_runner.py:715-783`). Seta `human_verdict`/`human_note`/`reviewed_by`/`reviewed_at`.

### eval.run
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--confirm` | flag | Nao | false | Enfileira na RQ `agent_eval` |

Chama `enqueue_eval_batch`. **CUSTO**: ~105 chamadas Haiku + invokes Opus dos 4 subagentes (20-50min).
Gated por `AGENT_EVAL_GATE` (OFF -> `{skipped: flag_off}`). Requer worker na fila `agent_eval` (Workers 1/2 PROD).

### melhorias.respond
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--key` | str | **Sim** | — | suggestion_key (v1 deve existir) |
| `--status` | str | **Sim** | — | responded\|rejected\|needs_revision\|verified\|closed |
| `--description` | str | **Sim** | — | Texto da resposta |
| `--notes` | str | Nao | — | implementation_notes |
| `--files` | str | Nao | — | affected_files separados por virgula |
| `--confirm` | flag | Nao | false | Grava a resposta |

Cria v2 (`author='claude_code'`) via `AgentImprovementDialogue.upsert_response` (models.py:1334). **CASCADE**:
gravar a v2 tambem atualiza o status da v1. Backing = MODELO + rota, **NAO** `improvement_suggester`.

---

## Cobertura de testes

| Arquivo | Tipo | O que cobre |
|---------|------|-------------|
| `tests/agente/test_gerindo_agente_skill.py` | ZERO-DB (importlib + inspect) | Contrato: paridade SUBCOMMANDS/HANDLERS, args, destrutivas exigem `--confirm`, envelope `success_output`, `format_datetime` TZ-safe, `run_handler`, ausencia de contexto-duplo em `padrao`. **Fase 3b**: handlers READ sem escrita; WRITE exigem `--confirm` e guardam a escrita atras de `if not args.confirm:` (efeito apos o guard). |
| `tests/agente/test_gerindo_agente_snapshots.py` | DB-bound (subprocess), skippa sem `.env` | Rede de seguranca P12: trava o shape `--json` (esqueleto de tipos) de cada subcomando READ pelo caminho real `main()`/`run_handler`. Golden: `tests/agente/snapshots/gerindo_agente_json_shapes.json`. Regravar: `GERINDO_SNAPSHOT_RECORD=1 pytest ...`. |
| `tests/agente/test_gerindo_aposentar_db.py` | DB-bound (subprocess), skippa sem `.env` | T1.4 `memoria.aposentar`: dry-run NAO muta; `--confirmar` muta (`is_cold` + `meta.promovida_para`) + cria versao. Memoria de teste criada/limpa pelo proprio teste. |
