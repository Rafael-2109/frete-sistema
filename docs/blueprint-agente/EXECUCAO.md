# EXECUÇÃO — Evolução do Agente (rastreador vivo)

> **Este é o ÍNDICE DE VERDADE do projeto.** Sobrevive entre sessões. NENHUMA onda começa
> sem consultar os gates aqui; NENHUM item é "done" sem marcar o checklist aqui.
> Spec de design: `BLUEPRINT_MESTRE.md` (+ `eixos/*.md` detalhe, `critica/*.md` revisão).
> Planos executáveis por onda: `docs/superpowers/plans/` (formato writing-plans, TDD).
> Branch do projeto: `feat/agente-evolucao` (worktree isolada). Cadência: **subagent-driven**.

---

## COMO USAR (protocolo inviolável)

1. **Ordem por DEPENDÊNCIA, não por esforço.** Os gates abaixo são duros. Não inicie a onda N+1
   sem o GATE da onda N verde (verificado em PROD/shadow, não só pytest local).
2. **1 item = 1 PR pequeno atrás de flag OFF.** Cada item tem um plano writing-plans próprio
   (gerado just-in-time quando a onda chega) executado subagent-driven (1 subagente/tarefa + review).
3. **Definition of Done (DoD) GLOBAL** — um item só vira ✅ quando TODOS batem (ver checklist abaixo).
4. **Atualizar este arquivo a cada item** (status + data + nº do PR/commit). É o que garante "não pular/esquecer".
5. **Flag OFF default** em tudo. Comportamento novo valida em SHADOW antes de virar gate/ativo.

### Definition of Done (DoD) — checklist por item
- [ ] Teste TDD verde (failing test escrito ANTES da implementação)
- [ ] **Wiring contract verificado por teste de INTEGRAÇÃO** (o sinal atravessa produtor→consumidor, não só unit)
- [ ] Migration dupla se houver schema: `scripts/migrations/NOME.{py,sql}` (SQL idempotente `IF NOT EXISTS`)
- [ ] Invariantes da área intactas (ver checklist de regressão abaixo)
- [ ] pytest baseline mantido ou aumentado (não baixa o nº de verdes)
- [ ] Flag OFF por default em `config/feature_flags.py`
- [ ] code-review aprovado (`/code-review` ou workflow adversarial nos itens críticos)
- [ ] Se comportamental (muda resposta/ação): validado em SHADOW antes de ligar a flag
- [ ] Status atualizado neste arquivo

### Checklist de REGRESSÃO — invariantes a NUNCA quebrar (Blueprint §5)
Verificar em TODO PR que toca a área correspondente:
- **INV-1 (R10)**: escrita de turno/passo/resposta no fim da thread PRIMARY, NUNCA no `_stop_hook` (corrida).
- **INV-2 (identidade)**: chave = nosso UUID + `AgentSessionCost.message_id` (UNIQUE `models.py:1413`), NUNCA o SDK session_id efêmero.
- **INV-3 (canais)**: separação Web/Teams — aprovação de plano e feedback explícito nascem Web-only; Teams (Adaptive Card R4) tem caminho próprio.
- **INV-4 (constituição estoque)**: "1 skill = 1 objeto", `--dry-run` first, fluxos>>skills (`estoque/CLAUDE.md`). Verifier `domain` (B) e registry (F) GENERALIZAM, não violam.
- **INV-5 (guards de domínio)**: G021/G031/G-MO-01, direção-MIGRAÇÃO por `diff_qtd`, CICLAMATO, GTIN/SEFAZ G035 são a verdade logística que o verifier `domain` checa.
- **INV-6 (best-effort + thread-safety)**: services em RQ/APScheduler, NUNCA no path SSE; ContextVar por thread; except não-propagado.
- **INV-7 (caching Camada 1)**: `<operational_directives>` e `<world_model>` injetados via hook (dinâmico), fora do system_prompt estático cacheável.

### Riscos transversais (mitigação obrigatória nos itens marcados)
- **Reward-hacking** (Ondas 1,3): judge produz LAUDO causal justificado; componente ambiental não-gameável (audit Odoo R9) DOMINA a decisão de promoção; held-out + spot-check humano 5-10%.
- **`effective_count` semântica** (Onda 1): coluna NOVA `outcome_effective_count`, NUNCA redefinir in-place (3 consumidores acoplados).
- **Recursão de subagente solta** (Onda 2): verificar propagação de `Task` no SDK 0.2.87 ANTES de B4 (instrução contraditória `gestor-estoque-odoo.md:73`).
- **Gate travando atuador autônomo** (Onda 3): eval do D8 = processo EXTERNO + report-only→enforce.

---

## GRAFO DE DEPENDÊNCIAS (resumo — ver Blueprint §2)

```
S0 (entidade passo + registry descritivo)  ──┬─► E (qualidade) ◄──► D (ontologia)   [E↔D ciclo]
   FUNDAÇÃO FÍSICA                            │        │                │
                                              │        ▼                ▼
                              F (registry) ───┴─► A (flywheel) ◄─── B (planejador)
                                  sustenta           │ consome sinal E   │ consome mundo D
                                  e É o espaço        └── promove plano ──┘ produz sinal p/ E
                                  de estados de B
```
Fundações: (i) **S0 schema de passo** (física) · (ii) **par E↔D** (semântica) · (iii) **F registry** (estrutural).

---

## ESTADO DE ATIVAÇÃO (2026-05-31) — FUNCIONAL vs WIRING PENDENTE

> Os 22 itens estão **code-complete + testados + flag-OFF**. Mas "funcional" (roda no loop vivo)
> ≠ "code-complete". Por design GATED (shadow→wire→ativa), parte tem o MECANISMO pronto mas
> SEM caller no loop vivo ainda. Esta tabela é a VERDADE para a fase de wiring.

### ✅ Funcional ao ligar a flag (caller ativo — ativados em PROD 2026-05-31)
| Feature | Flag | Caller ativo |
|---------|------|--------------|
| S0a `agent_step` | — (schema) | `chat.py::_save_messages_to_db` + `teams::_gravar_agent_step_teams` (todo turno) |
| E1 quality spine | `AGENT_QUALITY_SPINE` | `chat.py`/`teams` (frustração) + `feedback.py` (👍👎) |
| D2 bootstrap | `AGENT_ONTOLOGY` | `build.sh 26c` / `scripts/agente/bootstrap_ontologia.py` |
| D4 `query_ontology` | `AGENT_ONTOLOGY` | tool MCP exposta ao agente (`client.py` registro) |
| D3 proveniência | `AGENT_ONTOLOGY` | `memory_mcp_tool` (save de memória) |
| B1 PlanState | `AGENT_PLANNER` | `chat.py` captura Task* events do stream |
| F4/F5 skill-hints | `AGENT_SKILL_RAG` | hook `_user_prompt_submit_hook` |
| D5 world_model | `AGENT_WORLD_MODEL_INJECT` | hook `_user_prompt_submit_hook` |

### 🟡 Shadow scaffolding — lógica+testes prontos, SEM caller no loop (precisa WIRING)
| Feature | O que JÁ existe | O que FALTA wirar (a fase de ativação) |
|---------|----------------|-----------------------------------------|
| **E2** step_judge | `workers/step_judge.py` (`judge_step` job RQ + `_judge_core` + **`enqueue_pending_judges`**) | ✅ **WIRADO CODE-COMPLETE** (`918d7e7af`, flag-OFF) — **módulo 29** D8 (`sincronizacao_incremental_definitiva.py`, por-ciclo 30min, report-only) chama `enqueue_pending_judges` (janela `created_at` 6h + cap 50, filtro Python `'judge' not in outcome_signal`, best-effort). Fila RQ nova `agent_judge` (LEVE, prioridade mínima) nos 3 arquivos. Reusa flag `AGENT_STEP_JUDGE`; âncora `AGENT_ODOO_AUDIT_HOOK` é ideal (judge degrada sem ela). **Pendente: deploy+shadow (GATE-2).** |
| **B2** verifiers | `sdk/verifiers.py` + `workers/plan_verifier.py` (`verify_step_shadow` + `enqueue_pending_verifies`) | ✅ **WIRADO CODE-COMPLETE** (`15b681a8e`, flag-OFF) — job RQ `verify_step_shadow` roda os 3 verifiers (adversarial+arithmetic+domain) e grava combinado em `outcome_signal['verify']`; **módulo 30** D8 (`enqueue_pending_verifies`, por-ciclo, report-only) varre steps sem verify → enfileira (fila `agent_judge`, gate `AGENT_VERIFY`). **Pendente: deploy+shadow (GATE-2).** Nota: domain verify lê `data['plan']['steps']` (B1, sem entities) → mostly skip; consumir entities do triage é integração futura. |
| **B-TRIAGE** | `sdk/plan_triage.py` (`triage_meta`) + `workers/triage_shadow.py` | ✅ **WIRADO CODE-COMPLETE** (`edf72cf7f`, flag-OFF) — job RQ `triage_step_shadow` roda `triage_meta` no meta (msg do usuário) do turno e grava em `outcome_signal['triage']` (NÃO `data['plan']` — B1 clobra a cada turno); **módulo 31** D8 (`enqueue_pending_triages`, gate `AGENT_PLANNER`). **Pendente: deploy+shadow.** |
| **B3** replan-loop | `plan_state.py` (`mark_step_failed`/`should_escalate`/`steps_to_retry`) + `AgentInvocationMetric.marcar_escalonamento` | ⏸️ **ADIADO COM PREMISSA** (decisão Rafael 2026-05-31). Mismatch real: `marcar_escalonamento` escreve em **AgentInvocationMetric** (linha por spawn de SUBAGENTE), mas o `PlanState` em shadow vem de eventos **Task\*** (tarefas do agente principal, SEM `agent_id` de subagente). **PREMISSA p/ wirar**: super-loop INLINE onde os steps de plano SÃO invocações de subagente com `agent_id` — só aí o mapeamento step-falho→AgentInvocationMetric existe. Em shadow batch, chamar `marcar_escalonamento` é prematuro/mal-definido. NÃO esquecer (ver memória `b3-escalate-adiado-premissa`). |
| **A3** eval-gate | `eval_gate_service.py` (`run_evals`/`eval_gate`) + módulo 28 D8 | **INVOKE REAL**: substituir o seam `invoke_fn` stub pela invocação real do agente (SDK) contra os golden cases; estabelecer baseline; report-only→enforce. |
| **A4** promoção | `directive_promotion_service.py` (`propose_directive_from_plan`/`evaluate_and_promote`) | **BATCH**: job (D8) que varre PlanStates bem-sucedidos → propõe candidata → `evaluate_and_promote` (gate A3 + anti-gaming R9) → (gated) promove. + coluna/estado `directive_status`. Pré-req: baseline A3. |

### Ordem GATED de WIRING (recomendada — cada fase depende da anterior validada em PROD)
1. **Fundação** (S0a/E1/B1/D*/F4-F5) validada em PROD — **em teste agora** (GATE-0/1).
2. **E2-enqueuer** ✅ CODE-COMPLETE na branch (`918d7e7af`, flag-OFF) — pendente deploy+shadow do Rafael. (judge em shadow, gravando vereditos; depois de agent_step OK + audit hook.)
3. **Super-loop do planejador** (shadow): ✅ **2a** fix `pending_questions` (`b31c18760`, baseline 2 falhas → 0) + ✅ **2b** B2 verify shadow (`15b681a8e`) + ✅ **2c** B-TRIAGE shadow (`edf72cf7f`) CODE-COMPLETE na branch (flags OFF). **B3 replan/escalate ADIADO COM PREMISSA** (super-loop inline com steps=subagentes). Pendente deploy+shadow (GATE-2) do Rafael.
4. **A3-invoke** (eval real) → baseline → **A4-batch** (fecha o flywheel ativo) — GATE-3.

> Detalhe de design por eixo: `eixos/A-flywheel.md` (E2/A3/A4), `eixos/B-planejador.md` (B2/B-TRIAGE/B3).

---

## ONDAS E ITENS

> Status: ⬜ pending · 🟡 em progresso · 🔵 shadow (código pronto, validando comportamento) · ✅ done
> Esforço relativo (P/M/G) é orientativo — NÃO é critério de ordem.

### ONDA 0 — FUNDAÇÃO FÍSICA  ·  GATE-0 destrava Ondas 1 e 2
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **S0a** | Tabela `agent_step` (1ª classe), granularidade TURNO, `step_uid` UNIQUE=`'{session_id}:{turn_seq}'` (join com costs por session+janela). Populada no fim da thread PRIMARY (R10), nunca no `_stop_hook`. Migration dupla. | — | (schema, sem flag) | M | ✅ **COMPLETO** — model `c13fb31c4` + wiring web `8287406fa` + **wiring Teams `dbe0e8700`** (S0a-teams, INV-3: helper `_gravar_agent_step_teams` nos 2 pontos de persistência, idempotente). 9 testes (web+teams). |
| **S0b** | Consolidar deny-list dispersa: mover `SPED_SKILLS_RESERVED` (`settings.py:40`) p/ `skills_whitelist.py` (4º grupo); `client.py` lê UMA fonte. | — | — | P | ✅ **COMPLETO** — commit `f3f6227eb`: `SKILLS_SPED_RESERVED` em `skills_whitelist.py` somado à união; `settings` re-exporta (retrocompat); `client.py` lê `SKILLS_DELEGADAS_SUBAGENTE` (fonte única). 4 testes novos; 12 testes SPED verdes; baseline 337→341. |
| **S0c** | Capability Registry DESCRITIVO: `SkillEntry` + `SkillBinding` (aresta N:M skill↔agente — exposure NÃO é escalar). Populado por `agent_loader._parse_skills` + 5 tabelas-catálogo do estoque. Read-only (flag OFF: só descreve). | S0b | `AGENT_CAPABILITY_REGISTRY` | M | ✅ **COMPLETO** — commit `b3a89f97e`: `capability_registry.py` (50 skills, 116 bindings, 17 agentes; `consultando-sql`=11). Flag `AGENT_CAPABILITY_REGISTRY` OFF. 4 testes; baseline 341→345. **Escopo:** enriquecimento via 5 tabelas-catálogo do estoque DIFERIDO p/ F4/D2 (contrato N:M não depende). Nit pendente: `Optional` não-usado → limpeza no fechamento. |

**Wiring S0a**: produtor = `run_async_stream` finally (thread PRIMARY, `client.py`) → grava `agent_step` → consumidores futuros = E1/E2 (sinal), B1 (PlanState), A (recalibração). Reusa: `AgentSessionCost.message_id` UNIQUE (`models.py:1413`), padrão `insert_metric` SAVEPOINT (`models.py:1664-1719`).
**GATE-0 (verde para seguir)**: `agent_step` gravando 1 linha/turno em PROD por ≥48h, joinável com `AgentSessionCost` e `agent_sessions`; zero impacto em latência/erro (Sentry limpo); registry descritivo bate com os 16 frontmatters + catálogos (auditoria read-only).

### ONDA 1 — FUNDAÇÃO SEMÂNTICA (E↔D em paralelo)  ·  GATE-1 destrava Onda 3 (flywheel)
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **E1** | Sinais humanos/implícitos → `agent_step`: capturar `score` de `detect_frustration` (`sentiment_detector.py`, hoje só in-memory) + 👍👎 (`data['feedbacks']` não-joinável) na entidade de passo. (`_adjust_importance_for_corrections` NÃO ressuscitada — era dead-code.) | S0a | `AGENT_QUALITY_SPINE` | M | ✅ **COMPLETO** — commit `4e3de61f8`: `AgentStep.update_outcome` (merge JSONB SAVEPOINT) + `get_last_frustration_score` + wiring web/teams (mesmo step_uid, sob flag) + link 👍👎→step. 8 testes (incl. prova flag-OFF=zero write). baseline→360. |
| **E2/A1** | Componente UNIFICADO `attribution_judge`(=step_quality): judge batch (clona `subagent_validator`), ancorado no audit Odoo R9 (`operacao_odoo_auditoria`), produz por passo de risco `{score, label, componente_culpado, evidência}` (Process Reward Model). Ambiental (R9) DOMINA. | S0a, D0.5 | `AGENT_STEP_JUDGE` | G | ✅ **COMPLETO** — `f06ee60fc` + fix `de0e27158`: `workers/step_judge.py` (`_judge_core` testável + `judge_step` job RQ); FALHA_ODOO força score≤35+componente='odoo' (não-gameável); SHADOW (sem enqueue ativo); flag OFF. 11 testes. **Code-review CRITICAL-1**: faltava `commit` no job RQ → corrigido. |
| **D0** | Higiene KG: corrigir leak `:E/:A` (`knowledge_graph_service.py:403`). ~~resolução-ao-nó/`with_key=0`~~ DIFERIDO (premissa não-confirmada — é guard de nome-vazio, precisa dados PROD). | — | — | P | ✅ **COMPLETO** — commit `fb2ecd77b`: strip do sufixo em `parse_contextual_response` (1 linha; `else` preserva `:` legítimo). 2 testes + 3 flags Onda 1 OFF. Resolução canônica diferida. |
| **D0.5** | ESCOPO `user_id=0`: nós canônicos = EMPRESA, `query_graph_memories ANY([user_id,0])`. | — | — | P | ✅ **COMPLETO** — commit `03d0601b9`: JÁ implementado (`query_graph_memories:797` + escrita empresa); blindado com teste de regressão. Bootstrap massivo (onde a irreversibilidade morde) fica na D2/Onda 3 atrás de flag. |

**Wiring E1/E2**: produtor = callsite `detect_frustration` (`chat.py:560`) + `feedback.py` (Web) + judge batch (RQ) → grava em `agent_step.outcome_*` → consumidor = A (recalibração) na Onda 3. Reusa: `subagent_validator` (esqueleto), `friction_analyzer` (4 detectores), `operacao_odoo_auditoria` (R9), `_adjust_importance_for_corrections` (estacionado), `sql_evaluator_falses_service` (calibração).
**GATE-1**: sinal de qualidade step-level gravado e auditável por ≥1 semana; judge calibrado (concordância ≥X% com spot-check humano em held-out); E↔D validado (ontologia não piora retrieval medido pelo sinal).

### ONDA 2 — ATUADOR DE PLANEJAMENTO  ·  GATE-2 destrava promoção de plano (Onda 3 A4)
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **B1** | PlanState durável + Plan tools (promover Task* cosméticos) em `AgentSession.data['plan']`, reusa `flag_modified`. | S0a | `AGENT_PLANNER` | M | ✅ **COMPLETO** — `286134082`: `sdk/plan_state.py` (PlanState puro) + captura Task* via stream (`_process_stream_event`→`_save_messages_dedup`→`_save_messages_to_db`, seguindo padrão `tools_used`), 3 guards `USE_AGENT_PLANNER` em série. 18 testes + flag-OFF=zero write. |
| **B-TRIAGE** | Classificador semântico NOVO (NÃO reusar `model_router` — é o inverso): decompõe meta em steps sobre entidades do KG. | B1, D2 | `AGENT_PLANNER` | M | ✅ **COMPLETO** — `561ce71cd`: `sdk/plan_triage.py` (`triage_meta` LLM-decompõe + ancora via `query_ontology_entities`). 13 testes, shadow, degrada sem ontologia/LLM. |
| **B2** | VERIFY, 3 verifiers: `arithmetic` (promove `_self_correct_response`), `adversarial` (job RQ cético), **`domain`** (ontologia D + guards — DIFERIDO pós-D2). Rodar em SOMBRA. | B1, (D2 p/ domain) | `AGENT_VERIFY` | G | ✅ **arith+adv COMPLETO** — `9691d9e62`: `sdk/verifiers.py` (`verify_arithmetic`) + `workers/plan_verifier.py` (`verify_plan_adversarial` job RQ cético, commit explícito). 13 testes, shadow. **`domain` ✅** `cd4f9b893`: `verify_domain` valida step contra ontologia (`query_ontology_entities`); NÃO duplica guards estoque (ficam no dry-run executor); hook `extra_checks`. 9 testes. **B2 completo (3 verifiers).** |
| **B3** | REPLAN com budget + escalate → escreve `escalated_to_human` (campo morto `models.py:1647`). | B1, B2 | `AGENT_PLANNER` | M | ✅ **COMPLETO** — `7ea589f65`: `PlanState` +`mark_step_failed`/`should_escalate`/`steps_to_retry` (budget) + `AgentInvocationMetric.marcar_escalonamento` (SAVEPOINT+commit). 22 testes (+18 B1 intactos). Chamador no loop = shadow sob flag. |

**Wiring B**: B emite eventos de plano (SSE) → se novo evento, R8 = 3 camadas (`client.py`→`routes/chat.py`→`chat.js`). VERIFY consome ontologia (D) + guards (código). Aprovação de plano = **Web-only na largada** (INV-3). Reusa: `_self_correct_response` (`client.py:792`), `subagent_validator`, guards de estoque, `pending_questions.py` (R-MULTIWORKER) p/ aprovação.
**GATE-2**: super-loop rodando em tarefas reais com VERIFY em shadow; `escalated_to_human` sendo escrito; zero regressão em tarefas single-shot existentes.

> **ONDA 2 — STATUS (2026-05-31)**: subconjunto buildável (B1, B2-arith, B2-adv, B3) ✅ COMPLETO + revisado. **B-TRIAGE e B2-domain DIFERIDOS** (dependem de D2/ontologia, Onda 3) — fazer após D2. Code-review: 0 CRITICAL; **H1** (`marcar_escalonamento` commitava — inverso do CRITICAL-1: caller é request Flask que já commita → removido, espelha `insert_metric`) + **I1** (import morto) corrigidos em `31aa9496c`. Suíte agente+teams **425 passed / 2 failed** (baseline pending_questions). Tudo flag-OFF. GATE-2 pendente de deploy/shadow.

### ONDA 3 — FECHAR O FLYWHEEL  ·  (muda comportamento ativo — só sobre fundações confiáveis)
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **A3** | Eval runner automatizado + gate no D8 (golden datasets `evals/`). Processo EXTERNO ao agente avaliado, report-only→enforce. | GATE-1 | `AGENT_EVAL_GATE` | M | ✅ **COMPLETO** — `f5883709b`: `services/eval_gate_service.py` (`load_golden_dataset`/`run_evals`/`eval_gate`; invoke do agente = SEAM injetável, Haiku-as-judge) + módulo 28 no D8 (`sincronizacao_incremental_definitiva.py`, flag `AGENT_EVAL_GATE` OFF = no-op, try/except isolado, **report-only NUNCA bloqueia**). 27 testes (sem API). Enforce + wiring real do invoke = ativação pós-deploy. |
| **A4** | Promoção automática de diretriz (liga `USE_OPERATIONAL_DIRECTIVES` com segurança): candidata→shadow/A-B→regression-gate→promove→monitora-drift→auto-despromove. Plano que funcionou (B§5) é o artefato promovível. Reusa `_build_operational_directives` (`memory_injection.py:420`). | A3, GATE-2 | `USE_OPERATIONAL_DIRECTIVES` + `AGENT_DIRECTIVE_PROMOTION` | G | ✅ **COMPLETO (shadow)** — `83d6ce61c`: `services/directive_promotion_service.py` (`propose_directive_from_plan` plano-completed→candidata; `evaluate_and_promote` etapa1 anti-gaming R9 DOMINA → etapa2 gate A3 → shadow só-LOGA). `_persist_directive`=stub documentado (precisa coluna+PROD). 23 testes. **FLYWHEEL FECHADO em shadow** (E1/E2→A3→A4). Flag OFF, sem caller. |
| **D2** | Bootstrap ontologia das TABELAS-mestre corretas (`carteira_principal`/`transportadoras`, NÃO `entity_indexer`→`contas_a_pagar`). | D0, D0.5 | `AGENT_ONTOLOGY` | G | ✅ **COMPLETO** — `5ac8ecafc`: `services/ontology_bootstrap.py` (cliente/produto/transportadora → `_upsert_entity` user_id=0, idempotente, **ZERO Voyage**) + CLI `scripts/agente/bootstrap_ontologia.py` (`--dry-run`/`--force`, não auto-run). 23 testes. Read path = D4. |
| **D3** | Fatos bi-temporais + episode subgraph de proveniência (reusa `session_turn_indexer.py`). | D2 | `AGENT_ONTOLOGY` | M | ✅ **COMPLETO** — `b75d90b78`: migration dupla (`2026_05_31_kg_bitemporal`, +valid_from/valid_to/source_session_id/source_step_uid em relations, +source_* em links; aplicada local). `_upsert_relation`/`_link_entity_to_memory`/`extract_and_link_entities` ganham params opcionais (backward-compat None); população de proveniência gated por `AGENT_ONTOLOGY` em `memory_mcp_tool` (flag OFF=NULL); ON CONFLICT 1ª-origem-vence. 8 testes; KG intactos. `valid_to`/`source_step_uid` NULL no MVP (invalidação + ContextVar step_uid = fase posterior). |
| **D4** | Tool MCP `query_ontology` (agente consulta o modelo de mundo). | D2 | `AGENT_ONTOLOGY` | M | ✅ **COMPLETO** — `d36752073`: `tools/ontology_query_tool.py` (`query_ontology_entities` busca DIRETA user_id IN [uid,0]) + tool MCP `query_ontology` registrada flag-gated em `client.py` (invisível com flag OFF). 12 testes (prova busca direta sem HOP-1). **Fecha o gap D2 → destrava B-TRIAGE+B2-domain.** |

**GATE-3**: flywheel fechado em shadow (promoção sugere, não aplica) por ≥2 semanas com held-out anti-gaming OK; ontologia consultável validada contra os ~298 schemas.

#> **2026-05-31 — BLUEPRINT CODE-COMPLETE + 100% REVISADO (22 itens, Ondas 0-4)**: D3 `b75d90b78` · A3 `f5883709b` · A4 `83d6ce61c` (flywheel fechado shadow) · Onda 4 F4/F5+D5 `7ccae5f56`. **Code-review final** (D3/A3/A4/Onda4, `/tmp/subagent-findings/review-final.md`): 0 CRITICAL; **HIGH-1** (`valid_from` sem COALESCE no ON CONFLICT → descartado silenciosamente; inconsistente c/ proveniência) corrigido `1c321e232`. Confirmados OK: migration idempotente, SQL sem-injeção, A3 cron isolado/report-only, A4 anti-gaming, hook Onda 4 best-effort por bloco, flags-OFF=zero mudança, timezone. **Suíte final 572 passed / 2 failed** (baseline `pending_questions`, herdado da main). 71 commits, 32 de código. **TUDO flag-OFF — pendente só os GATEs (deploy do Rafael).**

## ONDA 4 — TETO DE ESCALA
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **F4/F5** | Routing gerado + Skill-RAG por domínio. | S0c, B2, D2 | `AGENT_SKILL_RAG` | G | ✅ **COMPLETO (advisory)** — `7ccae5f56`: `sdk/context_enrichment.py` (`rank_skills_for_query` token-overlap sobre registry S0c + `build_skill_hints_block`) injeta `<skill_hints>` via hook. **GAP SDK honesto**: `skills=` fixo no `connect()` (sem `set_skills()` por turno) → versão ADVISORY (aconselha, não filtra o listing). 22 testes (compart. D5). Flag OFF. |
| **D5** | `<world_model>` substitui `_DOMAIN_KEYWORDS` mantendo-o como fallback (cold start). | D2, F4/F5 | `AGENT_WORLD_MODEL_INJECT` | M | ✅ **COMPLETO** — `7ccae5f56`: `build_world_model_block` (ontologia D4 via `query_ontology_entities`) injeta `<world_model>` via MESMO hook `UserPromptSubmit` (INV-7). ADITIVO: `_DOMAIN_KEYWORDS`/`_build_routing_context` intactos = fallback cold-start. Flag OFF = zero mudança. |

---

## BASELINE CONHECIDO (herdado da main — NÃO causado pela Onda 0)
- ~~**2× falha em `tests/agente/sdk/test_pending_questions.py`**~~ ✅ **RESOLVIDO 2026-05-31 (Tarefa 2a, `b31c18760`)**: causa real diagnosticada — NÃO era o `call_soon_threadsafe` ausente (já existia); era `_signal_async_event` SEMPRE agendar via `call_soon_threadsafe` mesmo quando chamado de DENTRO da thread do loop dono (testes chamam submit/cancel no próprio loop e checam `is_set()` síncrono, sem `await` → callback agendado não rodou). Fix: quando `asyncio.get_running_loop() is pq._loop`, `set()` direto (imediato); cross-thread (Flask/subscriber) mantém `call_soon_threadsafe` (produção inalterada). **`tests/agente/sdk/` agora 196 passed / 0 failed.** Testado no Teams (sem impacto).

## NÃO VERIFICADO (auditar antes da onda correspondente — Blueprint §honestidade)
- Propagação de `Task` a subprocesso de subagente no SDK 0.2.87 → decide risco de B (Onda 2).
- Volume/custo Voyage no bootstrap D2 + judge online em turnos longos Odoo → dimensiona INFRA (workers/sampling), NÃO o valor.
- Conteúdo de `tool_skill_mapper` (service L5) → possível reuso p/ Skill-RAG (Onda 4).
- Campos exatos de agenda/incoterm em `carteira_principal`/`agendamentos_entrega` → D1 valida contra os 298 schemas.

## DECISÕES DE DESIGN (registradas — não re-decidir)
- **2026-05-30 — agent_step granularidade**: TURNO (1 par user→assistant). Chave UNIQUE `step_uid='{session_id}:{turn_seq}'` (`turn_seq` = nº msgs role=user na sessão). Idempotente p/ retry da defesa (R10). Join com `agent_session_costs` por `session_id`+janela temporal (NÃO por igualdade de message_id — granularidades distintas). Aprovado por Rafael. Plano: `docs/superpowers/plans/2026-05-30-onda-0-fundacao.md`.

## BLOQUEIOS ATIVOS
- _(nenhum — S0b/S0c desbloqueadas)_ — **RESOLVIDO 2026-05-31**: Rafael commitou `skills_whitelist.py` na main (commit `18e57919c`, Solução B allow→deny-list). `feat/agente-evolucao` mergeou main (merge limpo, exit 0), trazendo `skills_whitelist.py` (3 grupos + união) + `client.py` lendo-o. S0b consolidou SPED nele; S0c segue.
- **GATE-0 (fora do meu alcance)**: exige `agent_step` gravando em PROD ≥48h (web E teams) → depende de PUSH/DEPLOY do Rafael. Onda 1 NÃO inicia antes (protocolo §COMO USAR). Implementação Onda 0 fica code-complete na branch, sem push.

## LOG DE EXECUÇÃO (append-only — 1 linha por item concluído)
- 2026-05-30 — Onda 0 planejada (plano writing-plans) + design gate da chave resolvido. S0a liberado para Task 1.
- 2026-05-31 — Task 1 (S0a model `AgentStep` + migration dupla) ✅ commit `c13fb31c4`. TDD 3/3 + baseline; spec review ✅ + code quality ✅ (4 melhorias aplicadas); migration local aplicada. Wiring (Task 2) em andamento.
- 2026-05-31 — Task 2 (S0a wiring no PRIMARY + integração) ✅ commit `8287406fa`. 2 testes integração + 21 baseline; spec ✅ + code quality ✅ (guard `if user_message:` de simetria aplicado). **S0a COMPLETO** — `agent_step` grava 1 linha/turno no PRIMARY (web). Pendente: wiring Teams (sub-tarefa S0a-teams, INV-3) + GATE-0 (validação PROD 48h). Próximo: Task 3 (S0b deny-list).
- 2026-05-31 — **DESBLOQUEIO**: Rafael commitou `skills_whitelist.py` (`18e57919c`). Merge main→`feat/agente-evolucao` LIMPO (trouxe skills_whitelist + client.py + BUG-1/2/DOC-1 das quick-wins, sem conflito com AgentStep).
- 2026-05-31 — Task 3 (S0b deny-list fonte única) ✅ commit `f3f6227eb`. `SKILLS_SPED_RESERVED` em `skills_whitelist.py` somado à união; `settings.SPED_SKILLS_RESERVED` re-exporta (retrocompat, 12 testes SPED verdes); `client.py` exclui via `SKILLS_DELEGADAS_SUBAGENTE` (1 fonte). 4 testes novos; baseline 337→341 verdes. Verificado por mim: diff no escopo, sem import circular, falhas restantes (2× `pending_questions`) são PRÉ-EXISTENTES (falham em isolamento, arquivo idêntico pai↔HEAD, S0b não tocou) → triar separado no fechamento. Próximo: Task 4 (S0c registry).
- 2026-05-31 — S0a-teams (wiring agent_step canal Teams, INV-3) ✅ commit `dbe0e8700`. Helper `_gravar_agent_step_teams` (best-effort, idempotente) chamado nos 2 pontos de persistência do Teams: PRIMÁRIO (antes de `_commit_with_retry`, services.py:440) + FALLBACK pós-SSL-drop (antes de `db.session.commit()`, services.py:467). user_id FK via Rafael(1) no teste. 4 testes teams; baseline 345→349. Verificado por mim: call sites nos lugares certos, R1-R8 intactos. **GATE-0 agora cobre web E teams.**
- 2026-05-31 — Task 4 (S0c Capability Registry descritivo) ✅ commit `b3a89f97e`. `capability_registry.py` (`SkillEntry`/`SkillBinding`/`CapabilityRegistry` frozen + `build_registry()` + CLI de auditoria `__main__`); flag `USE_CAPABILITY_REGISTRY` OFF. Auditoria CLI (verdade-base por mim): 50 skills, 116 bindings, 17 agentes, `consultando-sql`=11 agentes (N:M comprovado), 25 skills no principal. 4 testes; baseline 341→345. Discrepância 11 vs 13 explicada (2 agentes citam no corpo, não no campo `skills:`). Próximo: S0a-teams (wiring Teams) + fechamento.
- 2026-05-31 — **ONDA 1 planejada** (`docs/superpowers/plans/2026-05-31-onda-1-quality-spine.md`) APÓS auditoria de premissas (recon `/tmp/subagent-findings/onda1-recon.md`). Escopos CORRIGIDOS vs blueprint: **D0** reduzido ao leak `:E/:A` (confirmado `knowledge_graph_service.py:396-405`); `entity_key=0` por corrida = premissa NÃO-confirmada (é guard de nome-vazio) → DIFERIDO p/ análise de dados PROD. **D0.5** já implementado (`query_graph_memories:797` + escrita empresa) → vira teste de regressão. **E1** NÃO ressuscita `_adjust_importance_for_corrections` (deletada por dead-code) → captura `detect_frustration` score + 👍👎 em `agent_step.outcome_signal` (novo `AgentStep.update_outcome`). **E2/A1** clona `subagent_validator` (esqueleto ATIVO); âncora `operacao_odoo_auditoria` existe mas `USE_ODOO_AUDIT_HOOK` OFF (judge degrada sem ela). Pré-build atrás de flags OFF (decisão Rafael 2026-05-31). Iniciando Task 1 (D0+flags).
- 2026-05-31 — **ONDA 1 CODE-COMPLETE + revisada**: D0 (`fb2ecd77b`), D0.5 (`03d0601b9`), E1 (`4e3de61f8`), E2/A1 (`f06ee60fc`). **Code-review adversarial Onda 1** (`/tmp/subagent-findings/review-onda1.md`): 0 inválidos; **HIGH-1** (`e8afb153a`) sufixo confiança `:alta/:media/:baixa` vazava no destino de RELACOES (mesma família D0) — corrigido + teste; **CRITICAL-1** (`de0e27158`) `step_judge` fazia flush sem `commit` no job RQ → veredito se perderia em PROD (teste mascarava via sessão de teste compartilhada) — corrigido + teste spy-passthrough + cleanup de órfãos. Demais invariantes (flag-OFF=zero write, INV-6 best-effort, SAVEPOINT, step_uid consistente, timezone, shadow) confirmadas OK. Suíte agente+teams: **372 passed / 2 failed** (baseline pending_questions). Tudo flag-OFF. **GATE-1 (deploy+shadow ≥1sem) pendente do Rafael.** Próximo: Onda 2 (planejador).
- 2026-05-31 — **ONDA 2 planejada** (`docs/superpowers/plans/2026-05-31-onda-2-planejador.md`) após recon/auditoria (`/tmp/subagent-findings/onda2-recon.md`). **Premissa crítica resolvida**: subagentes NÃO têm `Task` (sem recursão) → verifier adversarial (B2) = JOB RQ, não subagente spawnado. **Ordenação cross-onda descoberta**: B-TRIAGE + B2-domain dependem de D2 (ontologia, Onda 3) → DIFERIDOS; buildáveis agora: B1, B2-arith, B2-adv, B3. `escalated_to_human` é de `AgentInvocationMetric` (morta). Iniciando B1 (PlanState).
- 2026-05-31 — **B-TRIAGE + B2-domain + code-review pós-D2** ✅. B-TRIAGE (`561ce71cd`), B2-domain (`cd4f9b893`). Code-review consolidado (D2/D4/B-TRIAGE/B2-domain, `/tmp/subagent-findings/review-posd2.md`): 0 CRITICAL; **HIGH-1** (bootstrap inflava `mention_count` em re-run → `_upsert_entity(increment_mentions=False)`), **HIGH-2** (teste zero-voyage era teatro → assert estrutural por regex de import), **HIGH-3** (helper morto) + nits — todos corrigidos `bea3203c9`. SQL parametrizado/sem-injeção confirmado; flag-OFF/shadow/read-only OK. **483 passed / 2 failed**. **ONDA 2 = 6 itens COMPLETOS.** Próximo: D3.
- 2026-05-31 — **ONDA 3 planejada** (`docs/superpowers/plans/2026-05-31-onda-3-flywheel-ontologia.md`) após recon D2 (`/tmp/subagent-findings/d2-recon.md`). Tabelas-mestre corretas: produto=`cadastro_palletizacao`, transportadora=`transportadoras`, cliente=`carteira_principal`/`contas_a_receber` (cnpj raiz 8d). `entity_indexer` atual é o ERRADO (financial_entity_embeddings, não KG). Tipos cliente/produto/transportadora já válidos; `_upsert_entity(user_id=0)` idempotente; Voyage trivial (<$0.01). **GAP CRÍTICO não-no-blueprint**: nós canônicos sem link de memória NÃO são achados pelo HOP-1 de `query_graph_memories` → **resolução: read path = tool `query_ontology` (D4), não HOP-1**; D2 bootstrapa substrato, D4 consome. D2+D4 destravam B-TRIAGE+B2-domain. Iniciando D2.
- 2026-05-31 — **ONDA 2 (subconjunto) CODE-COMPLETE + revisada**: B1 PlanState (`286134082`), B2 verifiers arith+adv (`9691d9e62`), B3 replan+escalate (`7ea589f65`). Code-review Onda 2 (`/tmp/subagent-findings/review-onda2.md`): 0 CRITICAL; H1+I1 corrigidos (`31aa9496c`); wiring B1 end-to-end (formato SSE) confirmado OK, jobs RQ commitam, flag-OFF=zero write, 18 testes B1 intactos. **425 passed / 2 failed**. B-TRIAGE + B2-domain DIFERIDOS pós-D2. Próximo: D2 (bootstrap ontologia, Onda 3).
- 2026-05-31 — **FECHAMENTO ONDA 0**: limpeza de imports (`b73739108`) + **2 code-reviewers adversariais** (lente correção/invariantes + lente qualidade/segurança). Veredito: **0 CRITICAL**; invariantes INV-1/INV-3/INV-6, timezone, SAVEPOINT, idempotência, migration, `outcome_effective_count` sem colisão → **todas PASSAM**. 2 achados MED corrigidos (`8fc20169f`): (A) guard do `agent_step` Teams alinhado ao web (captura turno mesmo sem texto final → dataset consistente entre canais); (M1) `SKILLS_DELEGADAS_SUBAGENTE` virou `frozenset`. 1 achado (db.JSON vs JSONB) é convenção do projeto → NÃO alterado, anotado p/ Onda 1 se `outcome_signal` precisar GIN. Suíte final: **349 passed / 2 failed** (as 2 = baseline pending_questions herdado da main). **ONDA 0 CODE-COMPLETE na branch.** Falta só GATE-0 (deploy PROD ≥48h — ação do Rafael).
- 2026-05-31 — **WIRING Tarefa 1 / E2-enqueuer** ✅ CODE-COMPLETE (`918d7e7af`, base `ec61021bb`). Subagent-driven: implementer TDD → spec-review ✅ → code-review adversarial. `enqueue_pending_judges` novo em `workers/step_judge.py` (gate `USE_AGENT_STEP_JUDGE` lazy, janela `created_at` indexada 6h + cap 50, filtro Python `'judge' not in outcome_signal` — evita gotcha `?`/psycopg2, `job_id` RQ-safe, best-effort INV-6). **Módulo 29** em `app/scheduler/sincronizacao_incremental_definitiva.py` (espelha módulo 28: por-ciclo 30min SEM hour-guard, try/except isolado, fora de `modulos_sync` = report-only). Fila RQ nova `agent_judge` LEVE (prioridade mínima antes de `default`) nos 3 arquivos (`worker_render.py`/`start_worker_render.sh`/`worker_atacadao.py`); `FILAS_PESADAS` intacto. Decisões do Rafael: fila LEVE + cadência por-ciclo. **Code-review pegou CRITICAL-C1** (`job_id='judge-step:{step_uid}'` continha `:` → RQ 2.6.1 `Job.set_id` levantava ValueError → feature inerte quando ligada; MagicMock mascarou nos testes) → fix `:`→`-` + regression test que falha contra o código antigo; **I1** (prioridade da fila em PROD estava alta/inconsistente) + **I2** (docstring "dedup" enganoso — RQ 2.6.1 não tem `unique=True`) corrigidos. Re-review ✅ (validado empiricamente vs Redis real). 18 testes `test_step_judge.py` (+1 C1), 2 falhas = baseline `pending_questions`. Flag OFF, sem push. **GATE-2 (deploy + shadow ≥1sem gravando vereditos) pendente do Rafael.** Próximo: Super-loop do planejador (B-TRIAGE+B2+B3).
- 2026-05-31 — **WIRING Tarefa 2 / Super-loop (shadow)** ✅ CODE-COMPLETE. Subagent-driven (implementer TDD + spec/code-review por sub-task + minha verificação). **2a** (`b31c18760`): fix `_signal_async_event` (set direto na thread do loop dono) → **baseline `pending_questions` 2 falhas → 0** (`tests/agente/sdk/` 196 passed); code-review threading ✅ 0 issues; testado Teams (inalterado). **2b** (`b8e46f8f0`+guard `15b681a8e`): B2 verify shadow — job RQ `verify_step_shadow` roda os 3 verifiers (adversarial+arithmetic+domain) → `outcome_signal['verify']` combinado; varredor `enqueue_pending_verifies` + **módulo 30** D8 (gate `AGENT_VERIFY`, fila `agent_judge`). Lição C1 carregada (job_id `:`→`-`). Code-review ✅ (1 Minor corrigido: guard `if not verify` p/ permitir retry). **2c** (`edf72cf7f`): B-TRIAGE shadow — job RQ `triage_step_shadow` roda `triage_meta` no meta do turno → `outcome_signal['triage']`; varredor `enqueue_pending_triages` + **módulo 31** D8 (gate `AGENT_PLANNER`). Code-review ✅ (mapeamento turn_seq→user msg exato por construção; merge preserva judge/verify). **B3 (replan/escalate) ADIADO COM PREMISSA** (super-loop inline com steps=subagentes/`agent_id` — `marcar_escalonamento` escreve em AgentInvocationMetric, incompatível com PlanState-Task* atual; registrado aqui + memória `b3-escalate-adiado-premissa`). 49 testes workers verdes. 3 sinais (judge/verify/triage) coexistem em `outcome_signal`. Tudo flag-OFF, sem push. **GATE-2 (deploy+shadow) pendente do Rafael.** Próximo: A3-invoke (eval real) → A4-batch.
