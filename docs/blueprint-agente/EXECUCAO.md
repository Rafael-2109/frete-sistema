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
| **S0a** | Tabela `agent_step` (1ª classe), granularidade TURNO, `step_uid` UNIQUE=`'{session_id}:{turn_seq}'` (join com costs por session+janela). Populada no fim da thread PRIMARY (R10), nunca no `_stop_hook`. Migration dupla. | — | (schema, sem flag) | M | ✅ **COMPLETO** — model `c13fb31c4` + wiring `8287406fa` (5 testes, spec+quality ✅ nas 2 tasks) |
| **S0b** | Consolidar deny-list dispersa: mover `SPED_SKILLS_RESERVED` (`settings.py:40`) p/ `skills_whitelist.py` (4º grupo); `client.py` lê UMA fonte. | — | — | P | ⬜ |
| **S0c** | Capability Registry DESCRITIVO: `SkillEntry` + `SkillBinding` (aresta N:M skill↔agente — exposure NÃO é escalar). Populado por `agent_loader._parse_skills` + 5 tabelas-catálogo do estoque. Read-only (flag OFF: só descreve). | S0b | `AGENT_CAPABILITY_REGISTRY` | M | ⬜ |

**Wiring S0a**: produtor = `run_async_stream` finally (thread PRIMARY, `client.py`) → grava `agent_step` → consumidores futuros = E1/E2 (sinal), B1 (PlanState), A (recalibração). Reusa: `AgentSessionCost.message_id` UNIQUE (`models.py:1413`), padrão `insert_metric` SAVEPOINT (`models.py:1664-1719`).
**GATE-0 (verde para seguir)**: `agent_step` gravando 1 linha/turno em PROD por ≥48h, joinável com `AgentSessionCost` e `agent_sessions`; zero impacto em latência/erro (Sentry limpo); registry descritivo bate com os 16 frontmatters + catálogos (auditoria read-only).

### ONDA 1 — FUNDAÇÃO SEMÂNTICA (E↔D em paralelo)  ·  GATE-1 destrava Onda 3 (flywheel)
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **E1** | Sinais humanos/implícitos → `agent_step`: capturar `score` que `detect_frustration` já calcula e descarta (`chat.py:560`); promover 👍👎 de `data['feedbacks']` (JSONB não-joinável) p/ a entidade de passo; ressuscitar `_adjust_importance_for_corrections` (deletado v2.2 `memory_injection.py:332`) agora alimentado. | S0a | `AGENT_QUALITY_SPINE` | M | ⬜ |
| **E2/A1** | Componente UNIFICADO `attribution_judge`(=step_quality): judge batch (clona `subagent_validator`), ancorado no audit Odoo R9 (`operacao_odoo_auditoria`), produz por passo de risco `{score, label, componente_culpado, evidência}` (Process Reward Model). Ambiental (R9 + 4 detectores `friction_analyzer`) DOMINA. | S0a, D0.5 | `AGENT_STEP_JUDGE` | G | ⬜ |
| **D0** | Higiene KG + resolução-ao-nó: corrigir leak `:E/:A` (`knowledge_graph_service.py:403`); interceptar merge p/ resolver menção ao nó canônico ANTES do dedup (causa real de `with_key=0`). | — | — | M | ⬜ |
| **D0.5** | DECISÃO ESCOPO `user_id=0` (irreversível): nós canônicos de negócio são da EMPRESA, reusa padrão memória-empresa + `query_graph_memories ANY([user_id,0])`. | — | — | P | ⬜ |

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

## NÃO VERIFICADO (auditar antes da onda correspondente — Blueprint §honestidade)
- Propagação de `Task` a subprocesso de subagente no SDK 0.2.87 → decide risco de B (Onda 2).
- Volume/custo Voyage no bootstrap D2 + judge online em turnos longos Odoo → dimensiona INFRA (workers/sampling), NÃO o valor.
- Conteúdo de `tool_skill_mapper` (service L5) → possível reuso p/ Skill-RAG (Onda 4).
- Campos exatos de agenda/incoterm em `carteira_principal`/`agendamentos_entrega` → D1 valida contra os 298 schemas.

## DECISÕES DE DESIGN (registradas — não re-decidir)
- **2026-05-30 — agent_step granularidade**: TURNO (1 par user→assistant). Chave UNIQUE `step_uid='{session_id}:{turn_seq}'` (`turn_seq` = nº msgs role=user na sessão). Idempotente p/ retry da defesa (R10). Join com `agent_session_costs` por `session_id`+janela temporal (NÃO por igualdade de message_id — granularidades distintas). Aprovado por Rafael. Plano: `docs/superpowers/plans/2026-05-30-onda-0-fundacao.md`.

## BLOQUEIOS ATIVOS
- **S0b (Task 3) + S0c (Task 4) BLOQUEADAS (2026-05-31)**: ambas dependem de `skills_whitelist.py`, que é **WIP NÃO-COMMITADO** do Rafael (não existe no código commitado da `main`/worktree — verificado: `_discover_skills_from_project` em `client.py` filtra só `AgentSettings.SPED_SKILLS_RESERVED` de `settings.py:40`; sem deny-list de subagentes nem skills_whitelist). Implementar criaria o arquivo do zero → duplicação/conflito de merge com o WIP. **Desbloqueio**: Rafael commita `skills_whitelist.py` na main → rebase da `feat/agente-evolucao` → S0b consolida `SPED_SKILLS_RESERVED` nele + S0c lê a deny-list real. S0a (fundação física) NÃO depende disto e está completo.

## LOG DE EXECUÇÃO (append-only — 1 linha por item concluído)
- 2026-05-30 — Onda 0 planejada (plano writing-plans) + design gate da chave resolvido. S0a liberado para Task 1.
- 2026-05-31 — Task 1 (S0a model `AgentStep` + migration dupla) ✅ commit `c13fb31c4`. TDD 3/3 + baseline; spec review ✅ + code quality ✅ (4 melhorias aplicadas); migration local aplicada. Wiring (Task 2) em andamento.
- 2026-05-31 — Task 2 (S0a wiring no PRIMARY + integração) ✅ commit `8287406fa`. 2 testes integração + 21 baseline; spec ✅ + code quality ✅ (guard `if user_message:` de simetria aplicado). **S0a COMPLETO** — `agent_step` grava 1 linha/turno no PRIMARY (web). Pendente: wiring Teams (sub-tarefa S0a-teams, INV-3) + GATE-0 (validação PROD 48h). Próximo: Task 3 (S0b deny-list).
