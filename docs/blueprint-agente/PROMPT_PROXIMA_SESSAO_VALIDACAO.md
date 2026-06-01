# PROMPT — Validação de Funcionamento + Medição de Resultados (Evolução do Agente, Ondas 0-4)

> Estado em 2026-06-01. Todo o blueprint (22 itens, Ondas 0-4 + wiring + A3 gate + A4 promoção)
> está MERGEADO em `main` e DEPLOYED em PROD. Várias flags shadow estão ON. **NADA foi medido ainda
> de forma sistemática** — esta sessão é para isso. Fonte da verdade: `docs/blueprint-agente/EXECUCAO.md`.

---

## REGRA INVIOLÁVEL DESTA SESSÃO: **VERIFICAR, NÃO ASSUMIR**

Na sessão de deploy da A4 o Claude **assumiu** que `AGENT_OPERATIONAL_DIRECTIVES` estava OFF (pelo default
do código e pelo blueprint) e construiu uma narrativa inteira sobre "segurar a flag de injeção". Os logs
PROD provaram que ela **JÁ estava ON** (o agente vinha injetando 5 heurísticas legado nos prompts).
**Lição:** o estado REAL de PROD (valor de flag, dado em tabela, comportamento em log) só vale se for
**verificado**. Nesta sessão de medição: toda afirmação sobre "está ligado / está funcionando / produziu X"
exige **evidência consultada** (query, log, dado) — nunca o default do código nem o que "deveria" estar.

**Outras disciplinas (mantidas do projeto):**
- Dados PROD: **MCP Render** (workspace `tea-d01amimuk2gs73dhlup0` — selecionar sem perguntar). NÃO usar dados locais.
- `agent_step.outcome_signal` é coluna **`json`** (não `jsonb`): `outcome_signal ? 'judge'` FALHA →
  usar `jsonb_exists(outcome_signal::jsonb,'judge')` ou `outcome_signal::jsonb ? 'judge'`.
- READ-ONLY: esta é sessão de **medição**, não de mudança. NÃO ligar flags novas, NÃO ativar `shadow→ativa`,
  NÃO rodar enforce. Só medir e reportar. Mudanças = decisão do Rafael APÓS a medição.
- Subagentes read-only (Explore) para varrer; o Claude sintetiza com fontes citadas.

---

## PRIMEIRO PASSO (não pular): mapear o que existe + o estado real

1. **Ler `docs/blueprint-agente/EXECUCAO.md`** — seção "ONDAS E ITENS" (inventário dos 22 itens, flag de cada,
   status) + "LOG DE EXECUÇÃO" (o que foi feito por sessão) + o CHECKPOINT mais recente.
2. **Enumerar o estado REAL das flags em PROD** (não assumir). Conhecidas como ON (confirmar): `AGENT_STEP_JUDGE`,
   `AGENT_VERIFY`, `AGENT_PLANNER`, `AGENT_EVAL_GATE`, `AGENT_ODOO_AUDIT_HOOK`, `AGENT_QUALITY_SPINE`,
   `AGENT_DIRECTIVE_PROMOTION`, `AGENT_OPERATIONAL_DIRECTIVES`. A verificar (estado desconhecido): `AGENT_ONTOLOGY`
   (D2/D3/D4), `AGENT_CAPABILITY_REGISTRY` (S0c), `AGENT_SKILL_RAG` (F4/F5), `AGENT_WORLD_MODEL_INJECT` (D5),
   `AGENT_EVAL_CALIBRATION`.
   - **Como verificar sem get-env MCP:** (a) pedir ao Rafael / dashboard Render env vars; OU (b) **inferir do dado/log**:
     ex. se há `outcome_signal['judge']` gravado → `AGENT_STEP_JUDGE` ON; se há `[OPERATIONAL_DIRECTIVES] directives=N`
     no log do agente → `AGENT_OPERATIONAL_DIRECTIVES` ON; se `query_ontology` aparece nas tools → `AGENT_ONTOLOGY` ON.
3. **Datar a janela de coleta:** desde quando cada flag está ON (1ª gravação em `agent_step`/logs) → define quantos
   dias de dado shadow existem. Lembrar: fim de semana ~0 tráfego; dias úteis ~15-18 sessões/dia.

---

## PARTE 1 — VALIDAÇÃO DE FUNCIONAMENTO (a maquinaria produz dado?)

Para cada camada: confirmar com EVIDÊNCIA que está gravando/rodando. Tabela de checagem (Postgres PROD via MCP,
`id` = `dpg-d13m38vfte5s738t6p50-a`):

| Camada (item) | Flag | Como validar que FUNCIONA | Sinal de OK |
|---|---|---|---|
| **S0a** agent_step (turno) | (schema) | `SELECT channel, count(*), max(created_at) FROM agent_step GROUP BY channel` | grava ~1 linha/turno web E teams; recente |
| **E1** quality spine | `AGENT_QUALITY_SPINE` | `agent_step.outcome_signal::jsonb ? 'frustration_score'` + 👍👎 (link feedback→step) | frustration_score presente; feedbacks ligados |
| **E2** judge (PRM) | `AGENT_STEP_JUDGE` | `outcome_signal->'judge'->>'score'`, `->>'label'`, `->>'componente_culpado'` | vereditos gravados; FALHA_ODOO→score≤35 |
| **B2** verify (3 verifiers) | `AGENT_VERIFY` | `outcome_signal->'verify'` (adversarial/arithmetic/domain) | refuted/ok por verifier |
| **B-TRIAGE** | `AGENT_PLANNER` | `outcome_signal->'triage'->>'steps'` | decomposição gravada |
| **B1** PlanState | `AGENT_PLANNER` | `agent_sessions.data::jsonb ? 'plan'` (count 14d) | **⚠️ era 0 em 2026-06-01 — INVESTIGAR (ver Parte 3)** |
| **A3** eval gate | `AGENT_EVAL_GATE` | `SELECT * FROM agent_eval_scores`; logs `[EVAL_GATE]` | baseline por agente (após Fase 2) |
| **A3-R3** calibração | `AGENT_EVAL_CALIBRATION` | `SELECT * FROM agent_eval_case` (human_verdict) | casos com spot-check humano |
| **A4** directive batch | `AGENT_DIRECTIVE_PROMOTION` | logs `[directive_promotion] batch concluído`; `agent_memories WHERE directive_status IS NOT NULL` | batch roda; shadow persistido (quando houver PlanStates) |
| **A4** injeção | `AGENT_OPERATIONAL_DIRECTIVES` | logs `[OPERATIONAL_DIRECTIVES] directives=N chars=M` | injeta só NULL/ativa (shadow excluída) |
| **R9** âncora Odoo | `AGENT_ODOO_AUDIT_HOOK` | `operacao_odoo_auditoria WHERE contexto_origem='execute_kw_hook'` recente | operações correlacionadas a sessão |
| **D2/D4** ontologia | `AGENT_ONTOLOGY` | `agent_memory_entities` (user_id=0) povoado; tool `query_ontology` registrada | substrato bootstrapado |
| **D3** bi-temporal | `AGENT_ONTOLOGY` | colunas `valid_from`/`source_session_id` em relations/links com dado | proveniência gravada |
| **S0c** registry | `AGENT_CAPABILITY_REGISTRY` | CLI `python -m app.agente.config.capability_registry` (50 skills/116 bindings) | descreve corretamente |
| **F4/F5 + D5** skill-hints/world_model | `AGENT_SKILL_RAG`/`AGENT_WORLD_MODEL_INJECT` | logs `<skill_hints>`/`<world_model>` injetados | bloco presente (se flag ON) |

**Queries-base prontas** (corrigir json→jsonb):
```sql
-- cobertura de sinais por step (volume + recência)
SELECT count(*) AS total,
       count(*) FILTER (WHERE jsonb_exists(outcome_signal::jsonb,'judge'))  AS com_judge,
       count(*) FILTER (WHERE jsonb_exists(outcome_signal::jsonb,'verify')) AS com_verify,
       count(*) FILTER (WHERE jsonb_exists(outcome_signal::jsonb,'triage')) AS com_triage,
       count(*) FILTER (WHERE jsonb_exists(outcome_signal::jsonb,'frustration_score')) AS com_frustration,
       min(created_at), max(created_at)
FROM agent_step;

-- distribuição do judge score (saúde do sinal de qualidade)
SELECT (outcome_signal::jsonb->'judge'->>'score')::numeric AS score,
       outcome_signal::jsonb->'judge'->>'label' AS label,
       outcome_signal::jsonb->'judge'->>'componente_culpado' AS culpado, created_at
FROM agent_step WHERE jsonb_exists(outcome_signal::jsonb,'judge') ORDER BY created_at DESC LIMIT 50;

-- anti-gaming R9: sessões com FALHA_ODOO devem ter judge score baixo
-- (cruzar agent_step.session_id com operacao_odoo_auditoria.status='FALHA_ODOO')
```

---

## PARTE 2 — MEDIÇÃO DE RESULTADOS (o telos: QUALIDADE, não só atividade)

O Eixo A inteiro existe para fechar o "fio de qualidade" (o agente fica mais CORRETO, não só mais consistente).
Medir, com a janela de dado disponível (declarar se é preliminar por baixo volume):

1. **O sinal de qualidade é são?** (E2/judge)
   - Distribuição dos judge scores (não tudo 50/default; varia com a trajetória?).
   - **Calibração:** amostrar 5-10% dos vereditos e comparar com julgamento humano (Rafael) — concordância ≥X%?
   - **Anti-reward-hacking (R9):** sessões com FALHA_ODOO no `operacao_odoo_auditoria` resultaram em judge score baixo
     (≤35) E `componente_culpado='odoo'`? (a âncora ambiental DOMINA?)
2. **O flywheel está fechando?** (A3+A4)
   - `agent_eval_scores`: existe baseline? (se 0 → A3 Fase 2 nunca rodou em PROD — ver Parte 3).
   - A4 batch: quantas candidatas propostas? quantas `would_promote` vs `rejected` (anti-gaming)? Há `directive_status='shadow'`
     em `agent_memories`? (depende de PlanStates — provavelmente 0 ainda).
3. **A injeção de diretrizes ajuda ou atrapalha?** (`AGENT_OPERATIONAL_DIRECTIVES` ON — 5 legado injetadas)
   - As 5 diretrizes injetadas são boas? (listar; `effective_count`/utilidade real, não só eco).
   - Comparar friction/erros/feedback 👎 ANTES vs DEPOIS de a flag ter ligado — degradou ou melhorou a qualidade das respostas?
   - (Ruptura #1 do blueprint: `effective_count` = eco semântico, não acerto — o judge agora dá um número mais honesto;
     cruzar as memórias injetadas com o judge score do turno.)
4. **Regressão geral?**
   - Sentry limpo (sem novos erros pós-deploy além do `/e/20/gkpj` PRÉ-EXISTENTE)?
   - Latência/custo por turno (AgentInvocationMetric, agent_session_costs) — o judge/verify batch não inflou nada inline?
   - `escalated_to_human`/`user_correction_received` (campos antes mortos) começaram a ser escritos?

**KPIs a reportar (tabela):** cobertura de sinal (% de turns com judge), score médio/distribuição, concordância de
calibração, nº candidatas A4 (proposta/promovida/rejeitada), Δ friction antes/depois das flags, regressões (0 esperado).

---

## PARTE 3 — GAPS CONHECIDOS A INVESTIGAR (prioridade)

1. **🔴 0 PlanStates apesar de `AGENT_PLANNER` ON** (B1). Em 2026-06-01, `agent_sessions.data->'plan'` = 0 em 14d.
   O batch A4 e o triage dependem disso. Investigar: o B1 captura `Task*` via stream (`_process_stream_event`→
   `_save_messages_to_db`) — o agente está EMITINDO Task*/usando o planejador? Ou o guard `USE_AGENT_PLANNER` não
   está no caminho certo? **Este é o gargalo do flywheel** (sem PlanState, A4 é no-op eterno).
2. **A3 Fase 2 (eval real) nunca rodou em PROD** → `agent_eval_scores` provavelmente vazio. Decidir com o Rafael:
   rodar `python -m app.agente.workers.eval_runner --agent analista-carteira` (custa API; CAVEAT I2: inspecionar
   `cases[].evidence` — stdout vazio rc=0 vira 'fail' falso). Sem baseline, A4 gate e A3 enforce não têm referência.
3. **Tráfego/volume:** se a coleta tem poucos dias úteis, a medição é PRELIMINAR — declarar e dizer quanto mais tempo
   de shadow seria preciso para conclusões (held-out anti-gaming pede ≥2 semanas — GATE-3 do EXECUCAO.md).
4. **B3 (replan/escalate) ADIADO** — caller pendente de super-loop INLINE (ver memória `b3-escalate-adiado-premissa`).
   Validar só que a LÓGICA existe; não é esperado produzir dado.
5. **build.sh lento** (memória `deploy-web-build-lento`) — NÃO é desta sessão (Rafael trata à parte). Só não re-investigar.

---

## SAÍDA ESPERADA DESTA SESSÃO

Um **relatório de validação + medição** (e atualizar o EXECUCAO.md com os achados + GATE status), respondendo:
- **Funciona?** Por camada: produz dado (sim/não/parcial) com evidência.
- **Resultados?** O sinal de qualidade é são e calibrado? O flywheel fecha? A injeção ajuda? Regressão?
- **Decisões para o Rafael:** o que está pronto para avançar (A3 Fase 2 / enforce; A4 ativação shadow→ativa;
  cold-move sobre `effective_count` honesto; ligar flags D/F que estão OFF) — cada uma GATED na medição, NÃO antes.
- Honestidade: separar "maquinaria funciona" (produz dado) de "resultado é bom" (qualidade melhorou) — o 2º exige
  sinal calibrado + volume; se o dado é fino, dizer que é preliminar.

## SETUP
```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
# PROD: MCP Render (workspace tea-d01amimuk2gs73dhlup0). Postgres id = dpg-d13m38vfte5s738t6p50-a.
# Web srv-d13m38vfte5s738t6p60 · Worker srv-d2muidggjchc73d4segg.
```

## PONTEIROS
- Inventário + estado + LOG: `docs/blueprint-agente/EXECUCAO.md`
- Design por eixo: `docs/blueprint-agente/eixos/*.md` + crítica `critica/*.md` (Eixo A = telos do flywheel)
- Plano A4: `docs/superpowers/plans/2026-06-01-a4-promocao-diretriz.md`
- Guia dev do módulo: `app/agente/CLAUDE.md` (aponta para este diretório)
- Memórias: `avaliacao-360-agente-2026-05-29` (estado do blueprint), `deploy-web-build-lento`, `b3-escalate-adiado-premissa`, `wiring-agente-tarefa-1-2`, `a3-baseline-fase2-2026-05-31`
