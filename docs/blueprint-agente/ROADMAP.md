<!-- doc:meta
tipo: how-to
camada: L2
sot_de: roadmap sequenciado (ondas + cards com estado-maquina) do sistema de memoria/qualidade do agente + protocolo de sessao anti-perda
hub: docs/blueprint-agente/EXECUCAO.md
superseded_by: —
atualizado: 2026-06-03
-->

# ROADMAP — Memória & Qualidade do Agente (fila sequenciada + protocolo)

> **Papel:** a FILA forward do que falta (ondas ordenadas por valor×risco×dependência) + o
> PROTOCOLO de sessão que garante que nada se perca entre sessões. O histórico/narrativa
> de cada item mora em `EXECUCAO.md`; aqui mora o **estado vivo do que está PENDENTE**.
> Regra de ouro do sequenciamento: **observabilidade ANTES de atuadores** (medir antes de atuar).

## Indice
- Protocolo de sessão (anti-perda)
- Estado-máquina dos cards
- A espinha de dependência
- Ondas 0–7 (a fila)
- Como atualizar (checkpoint)

## Protocolo de sessão (anti-perda)

**SoT** = este ROADMAP (fila) + `EXECUCAO.md` (narrativa). Índice/ponteiro persistente =
memória Claude Code `avaliacao_memoria_agente_2026_06.md`.

Loop fixo de toda sessão (4 passos):
1. **Abrir** — ler a 1ª onda não-fechada; pegar o card de maior prioridade com estado `⬜`/`🟡` cujas dependências estão `✅`.
2. **Executar** — TDD (RED→GREEN), aditivo, flag-gated. **1 commit por card.**
3. **Checkpoint** — atualizar `estado` + `última-sessão` + `próximo-passo` do card AQUI + 1 linha na memória-índice. Se o contexto saturar no meio: o `próximo-passo` É o handoff (escrito no card; sem prompt solto).
4. **Handoff** — o card já carrega onde parou; prompt de continuação só para card grande em andamento.

**Invioláveis:**
- Nada vira `✅` sem o **DoD (que é um TESTE/query verificável)** passar. Progresso = estado do card **no repo**, nunca recall.
- Flag de atuação **nunca vai direto pra `✅`** — sempre `🟢 shadow → 🔵 canary → ✅ live`.
- Em ondas: fechar a onda N (observabilidade) antes de atuar na N+1 que depende dela.

## Estado-máquina dos cards
`⬜ todo → 🟡 wip → 🟢 shadow (código pronto, flag default OFF, TDD verde) → 🔵 canary (ligado p/ 1 user/PROD, observando outcome) → ✅ live (validado por métrica/outcome)`

## A espinha de dependência (por que a ordem é essa)
```
E1 outcome_signal → E2 step_judge → E3 calibração do judge → E4 fused_score
                                                                  │
   (sinal de qualidade CONFIÁVEL)  ──────────────────────────────┘
                                                                  ▼
        atuadores: A2 recalibrar · A5 golden · A4-V2 promoção · G-F2 receita · C2/C3 reflexão
```
Sem `E4` confiável, ligar atuador = promover ruído. Por isso Ondas 1–2 (olhos) vêm antes das Ondas 3+ (mãos).

---

## ONDA 0 — Colher o que já plantamos + fecho rápido (baixo risco) — **AGORA**

| id | card | tipo | flag | gate | DoD (teste/query) | dep |
|---|---|---|---|---|---|---|
| O0.1 | ✅ **DONE** (2026-06-03) — removido `_is_mandatory_trigger`+`_MANDATORY_PATTERNS`+teste; 39 verdes (loop corretivo) | cleanup | — | ✅ | `pytest tests/agente/` verde sem o arquivo; 0 callsite | — |
| O0.7 | **NOVO** (descoberto em O0.1): `_save_personal_insight` — `except` do embed best-effort NÃO dá rollback → sessão abortada (`InFailedSqlTransaction`) envenena o request. Add `db.session.rollback()` + varrer outros callsites de embed best-effort | cleanup | — | ✅ | teste create-path + query-pós passa com `MEMORY_SEMANTIC_SEARCH=true` (default) | — |
| O0.2 | Fila `agent_validation` ausente do `--queues` (worker PROD) | wiring | — | 🔵 | `validate_subagent_output` processado (log) após add em `start_worker_render.sh:301` | — |
| O0.3 | Card frontend do painel de adesão (3.7) em `insights.html` | feature | — | ✅ | `/agente/insights` mostra tabela error_signature × antes/depois | — |
| O0.4 | Ligar `USE_RECURRENCE_SCORE` (3.4B) — pré-req (cc populado) **atendido pelo backfill** | flag-flip | `AGENT_RECURRENCE_SCORE` | 🔵 | 24h sem regressão no health_score; composite de mem cc>0 sobe | — |
| O0.5 | Rodar migrations A3 (`agent_eval_scores`+`agent_eval_case`) no Render Shell | wiring | — | ✅ | `SELECT` confirma as 2 tabelas em PROD | — |
| O0.6 | **Validações passivas F1** (observar ≥1 semana): injeção `[MEMORY_INJECT_RULES] user 18` + Teams + reincidência por assinatura | validation | — | 🔵 | `rule-adhesion?days=7&user_id=18`: recurrence_before>0 e after≤2 | backfill (✅ feito) |

## ONDA 1 — Observabilidade ("dar olhos") — **pré-req de toda atuação**

| id | card | tipo | flag | DoD (teste/query) | dep |
|---|---|---|---|---|---|
| O1.1 | E1: persistir thumbs/frustração em `agent_step.outcome_signal` (`update_outcome`) | feature | `AGENT_QUALITY_SPINE` | `count(outcome_signal IS NOT NULL)>0` 1 semana | — |
| O1.2 | A-A0: persistir 👍👎 + `escalated_to_human`/`user_correction_received` | wiring | `AGENT_QUALITY_SPINE` | `turn_quality.explicit_feedback` = ±1 após clique | — |
| O1.3 | E2: `step_judge` por passo, ancorado no audit Odoo (R9 domina) | wiring | `AGENT_STEP_JUDGE` | `count(agent_step_judgments)>0` 48h; refute<50% | O1.1 |
| O1.4 | A3 Fase 2: `eval_runner --agent analista-carteira` → baseline real | validation | `AGENT_EVAL_GATE` | `agent_eval_scores`≥1 linha (git_sha real); evidence revisado | O0.5 |
| O1.5 | E3: harness de calibração do judge + `agent_eval_case` + `concordance_rate` (corrige viés sem-tool=fail 88%) | feature | `AGENT_EVAL_CALIBRATION` | concordance≥80%; ≥10 casos anotados | O1.4 |
| O1.G | **GATE-1**: ≥1 semana de dados + judge calibrado (destrava confiar no sinal) | validation | — | dados PROD ≥7d + concordance medida | O1.3,O1.5 |

## ONDA 2 — Qualidade como moeda (fused_score)

| id | card | tipo | flag | DoD | dep |
|---|---|---|---|---|---|
| O2.1 | **E4: `fused_score`** substitui `resolution_rate` no health_score + expõe p/ Eixo A | feature | `AGENT_FUSED_SCORE` | health_score usa fused; dashboard mostra custo POR ACERTO | O1.G |
| O2.2 | A-A2: recalibrar `importance`/efetividade por OUTCOME (Bayesian) — coluna `outcome_effective_count` | feature | `AGENT_OUTCOME_RECALIBRATION` | mem em turnos bons sobe vs ruins; cold-move lê nova coluna | O2.1 |
| O2.3 | A-A5: golden dataset auto-crescente (sessão ruim → candidato a caso de eval) | feature | `AGENT_EVAL_AUTOEXPAND` | candidato gerado; dataset do agente principal ≥5 casos | O2.1,O1.4 |

## ONDA 3 — Loops de aprendizado fecham (já com sinal confiável)

| id | card | tipo | flag | DoD | dep |
|---|---|---|---|---|---|
| O3.1 | A4-V2: promoção de diretriz por **judge signal** (desacopla do PlanState) | wiring | `AGENT_DIRECTIVE_PROMOTION` | `[directive_promotion]` candidatos>0; novas `directive_status=shadow` | O1.G |
| O3.2 | **B1 decisão de design** do PlanState (TaskCreate no principal × A4-V2 já resolve) — **GATE Rafael** | decision | `AGENT_PLANNER` | decisão registrada; ou PlanState>0 em PROD | — |
| O3.3 | G-F2: aprendizado procedural **positivo** (tipo `receita` + fechar feedback 👍) | feature | `AGENT_POSITIVE_LEARNING` | ≥1 mem `category=procedural`; ratio receita:armadilha>0 | O2.1 |
| O3.4 | Ligar `AGENT_CORRECTION_DEMOTION` (3.6) quando `harmful_count` acumular | flag-flip | `AGENT_CORRECTION_DEMOTION` | ≥3 casos harmful≥2 + review manual; demote não remove regra legítima | O0.6 |

## ONDA 4 — Recuperação + perfil (cura o sintoma-raiz do Marcus de vez)

| id | card | tipo | flag | DoD | dep |
|---|---|---|---|---|---|
| O4.1 | G-F6: **HyDE** + threshold adaptativo (91% prompts <150 chars → semantic=0) | feature | `AGENT_MEMORY_HYDE` | semantic>0 em ≥60% sessões PROD (era 0% p/ Marcus) | — |
| O4.2 | Ligar `USE_USER_XML_POINTER` + reservar budget Tier 2 (perfil grande zera correção pessoal) | flag-flip | `AGENT_USER_XML_POINTER` | `tier2_chars>0` em sessão do Marcus/Gabriella; agente usa `view_memories` | — |
| O4.3 | Ligar `USE_OPERATIONAL_DIRECTIVES` (heurísticas empresa nível 5 → bloco imperativo) | flag-flip | `AGENT_OPERATIONAL_DIRECTIVES` | revisar candidatas; `<operational_directives>` injeta; sem regressão 24h | — |

## ONDA 5 — KG / ontologia consultável

| id | card | tipo | flag | DoD | dep |
|---|---|---|---|---|---|
| O5.1 | D0: higiene KG — strip sufixo `:E`/`:A` nos nomes de entidade | cleanup | `AGENT_ONTOLOGY` | `count(entity_name LIKE '%:E')=0` pós-backfill | — |
| O5.2 | D-D1: schema de domínio **declarativo** (Pydantic entity/edge types; mata o 62% "conceito") | feature | `AGENT_ONTOLOGY` | 0 entidades novas tipo "conceito" pós-deploy | — |
| O5.3 | D2: bootstrap de ontologia + tool `query_ontology` | wiring | `AGENT_ONTOLOGY` | `count(kg_entities user_id=0)>0`; flag ON staging sem regressão | O5.2 |
| O5.4 | D3 wiring: popular `source_session_id`/`valid_from` nas relações (proveniência=0 hoje) | wiring | `AGENT_ONTOLOGY` | ≥1 relation com `source_session_id` em PROD | — |

## ONDA 6 — Vigilância + bi-temporal (memória que invalida o obsoleto)

| id | card | tipo | flag | DoD | dep |
|---|---|---|---|---|---|
| O6.1 | C0: job offline de coerência (report-only) — varre o corpus, grava contradição/staleness | feature | `AGENT_MEMORY_VIGILANCE` | `memory_vigilance_event` populado; 0 mutação de memória | — |
| O6.2 | C1: bi-temporal em `AgentMemory` (`valid_from`/`valid_to` + invalidação no ingest) | feature | `AGENT_MEMORY_VIGILANCE` | ≥1 mem com `valid_to` preenchido; query filtra vigentes | O6.1 |
| O6.3 | D3 invalidação: fato novo seta `valid_to` no antigo (tabela-de-fatos versionada) | feature | `AGENT_ONTOLOGY`+vig | fato contraditório invalida o antigo; testado staging | O6.1,O5.4 |
| O6.4 | C2/C3: reflexão sleep-time (cita memory_ids) + demote por staleness/TTL | feature | `AGENT_MEMORY_VIGILANCE` | insight cita evidência; mem stale rebaixada | O6.1,O6.2,O2.1 |
| O6.5 | G-F7: anti-contaminação `work_context` por domínio (mata overwrite incondicional) | feature | — | work_context independente por domínio (teste 2 domínios) | O5.2 |
| O6.6 | Ligar `USE_MANDATORY_HARD_ENFORCE` (3.5) — precisa de ≥1 regra com `ENFORCE_DENY_SUBSTR` curada | flag-flip | `AGENT_MANDATORY_HARD_ENFORCE` | regra curada existe; `[ENFORCE]` bloqueia só o token; smoke test | — |

## ONDA 7 — Governança + capacidades novas

| id | card | tipo | flag | DoD | dep |
|---|---|---|---|---|---|
| O7.1 | F2: CI guard + deny-list derivada do registry (enforça `skill_whitelist`) | validation | `AGENT_CAPABILITY_REGISTRY` | pytest falha em skill órfã; `_discover_skills` lê registry | — |
| O7.2 | F3: contrato universal nas 50 SKILL.md (bloco `## Contrato` + `NÃO-FAZ` estruturado) | cleanup | — | todas SKILL.md com contrato; YAML desc ≤600 chars | O7.1 |
| O7.3 | F4: routing **gerado** + árvore enxuta no system_prompt (mata drift dos 3 lugares) | feature | `AGENT_CAPABILITY_REGISTRY` | `system_prompt.md`<700 linhas; ROUTING gerado nunca editado à mão | O7.2 |
| O7.4 | F5: Skill-RAG semântico (de advisory → filtro real do listing top-K) | feature | `AGENT_SKILL_RAG` | meta-tool Skill <8K chars com 100+ skills; recall≥90% | O7.2,O7.3 |
| O7.5 | F9: gate de escrita de memória **empresa** (quem promove user_id=0) | feature | `AGENT_EMPRESA_MEMORY_GATE` | save user_id=0 em sessão com FALHA_ODOO é bloqueado | O7.1 |
| O7.6 | G-F10: injeção de memória em **subagentes** (SubagentStart + additionalContext) | feature | `AGENT_SUBAGENT_MEMORY` | subagente recebe contexto de domínio; sem regressão bug 2026-05-26 | O5.2 |
| O7.7 | B4/B5: verifier como subagente + scatter-gather + encolher system_prompt | feature | `AGENT_PLANNER_SCATTER` | step adversarial via subagente; system_prompt≤650 linhas | O3.2 |

---

## Como atualizar (checkpoint)
- Mudou o estado de um card? edite a célula `estado`/`gate` + adicione `<!-- O?.?: 🟡→🟢 (2026-..); próximo: ... -->` ao lado, e 1 linha no `EXECUCAO.md` (narrativa) + memória-índice.
- Card novo descoberto? adicione na onda certa (não crie tracker paralelo).
- Onda fechada (todos ✅/🔵 estáveis)? marque o título da onda com ✅ e registre no `EXECUCAO.md`.
