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
| **B1** | PlanState durável + Plan tools (promover Task* cosméticos `client.py:696`) em `AgentSession.data['plan']`, reusa `flag_modified` + `output_format` nativo. | S0a | `AGENT_PLANNER` | M | ⬜ |
| **B-TRIAGE** | Classificador semântico NOVO (NÃO reusar `model_router` — é o inverso): decompõe meta em steps sobre entidades do KG. | B1, D2 | `AGENT_PLANNER` | M | ⬜ |
| **B2** | VERIFY como gate real, 3 verifiers: `arithmetic` (promove `_self_correct_response`), `adversarial` (promove `subagent_validator` a veredito lido pelo loop), **`domain`** (valida contra ontologia D + guards codificados). Rodar em SOMBRA antes de virar gate. | B1, D2 | `AGENT_VERIFY` | G | ⬜ |
| **B3** | REPLAN com budget + escalate → escreve `escalated_to_human` (campo morto `models.py:1647`). | B1, B2 | `AGENT_PLANNER` | M | ⬜ |

**Wiring B**: B emite eventos de plano (SSE) → se novo evento, R8 = 3 camadas (`client.py`→`routes/chat.py`→`chat.js`). VERIFY consome ontologia (D) + guards (código). Aprovação de plano = **Web-only na largada** (INV-3). Reusa: `_self_correct_response` (`client.py:792`), `subagent_validator`, guards de estoque, `pending_questions.py` (R-MULTIWORKER) p/ aprovação.
**GATE-2**: super-loop rodando em tarefas reais com VERIFY em shadow; `escalated_to_human` sendo escrito; zero regressão em tarefas single-shot existentes.

### ONDA 3 — FECHAR O FLYWHEEL  ·  (muda comportamento ativo — só sobre fundações confiáveis)
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **A3** | Eval runner automatizado + gate no D8 (golden datasets `evals/`). Processo EXTERNO ao agente avaliado, report-only→enforce. | GATE-1 | `AGENT_EVAL_GATE` | M | ⬜ |
| **A4** | Promoção automática de diretriz (liga `USE_OPERATIONAL_DIRECTIVES` com segurança): candidata→shadow/A-B→regression-gate→promove→monitora-drift→auto-despromove. Plano que funcionou (B§5) é o artefato promovível. Reusa `_build_operational_directives` (`memory_injection.py:420`). | A3, GATE-2 | `USE_OPERATIONAL_DIRECTIVES` + `AGENT_DIRECTIVE_PROMOTION` | G | ⬜ |
| **D2** | Bootstrap ontologia das TABELAS-mestre corretas (`carteira_principal`/`transportadoras`, NÃO `entity_indexer`→`contas_a_pagar`). | D0, D0.5 | `AGENT_ONTOLOGY` | G | ⬜ |
| **D3** | Fatos bi-temporais + episode subgraph de proveniência (reusa `session_turn_indexer.py`). | D2 | `AGENT_ONTOLOGY` | M | ⬜ |
| **D4** | Tool MCP `query_ontology` (agente consulta o modelo de mundo). | D2 | `AGENT_ONTOLOGY` | M | ⬜ |

**GATE-3**: flywheel fechado em shadow (promoção sugere, não aplica) por ≥2 semanas com held-out anti-gaming OK; ontologia consultável validada contra os ~298 schemas.

### ONDA 4 — TETO DE ESCALA
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **F4/F5** | Routing gerado + Skill-RAG por domínio (resolve budget da meta-tool estruturalmente); registry como espaço de estados do planejador (pré/pós-condições viram operadores; fluxos L3 viram planos cacheados). Separar catálogo-gerável de boundaries comportamentais críticas (ficam no prompt). | S0c, B2, D2 | `AGENT_SKILL_RAG` | G | ⬜ |
| **D5** | `<world_model>` substitui `_DOMAIN_KEYWORDS` mantendo-o como fallback (cold start). | D2, F4/F5 | `AGENT_WORLD_MODEL_INJECT` | M | ⬜ |

---

## BASELINE CONHECIDO (herdado da main — NÃO causado pela Onda 0)
- **2× falha em `tests/agente/sdk/test_pending_questions.py`** (`TestSubmitAnswer::test_submit_answer_signals_both_events`, `TestCancelPending::test_cancel_pending_unblocks_async_event`): `pq.async_event.is_set()` retorna False (o `threading.Event` é setado mas o `asyncio.Event` não — bridge threading↔asyncio do R-MULTIWORKER). **Verificado**: falha idêntica na `main` @ `88e59dfb1`; nenhum commit da Onda 0 tocou `pending_questions.py` (diff vazio). Fora do escopo da Onda 0, MAS **relevante à Onda 2** (B usa `pending_questions.py` p/ aprovação de plano, INV-3). Triar antes de B1/B2. Suíte agente baseline: **349 passed / 2 failed** (eram 337 antes da Onda 0).

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
- 2026-05-31 — **FECHAMENTO ONDA 0**: limpeza de imports (`b73739108`) + **2 code-reviewers adversariais** (lente correção/invariantes + lente qualidade/segurança). Veredito: **0 CRITICAL**; invariantes INV-1/INV-3/INV-6, timezone, SAVEPOINT, idempotência, migration, `outcome_effective_count` sem colisão → **todas PASSAM**. 2 achados MED corrigidos (`8fc20169f`): (A) guard do `agent_step` Teams alinhado ao web (captura turno mesmo sem texto final → dataset consistente entre canais); (M1) `SKILLS_DELEGADAS_SUBAGENTE` virou `frozenset`. 1 achado (db.JSON vs JSONB) é convenção do projeto → NÃO alterado, anotado p/ Onda 1 se `outcome_signal` precisar GIN. Suíte final: **349 passed / 2 failed** (as 2 = baseline pending_questions herdado da main). **ONDA 0 CODE-COMPLETE na branch.** Falta só GATE-0 (deploy PROD ≥48h — ação do Rafael).
