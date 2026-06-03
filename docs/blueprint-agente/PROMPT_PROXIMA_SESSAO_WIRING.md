<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/blueprint-agente/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# PROMPT — Testar + Continuar o WIRING do Agente

> Cole isto como mensagem inicial da próxima sessão. Estado em 2026-05-31.
> Fonte da verdade viva: `docs/blueprint-agente/EXECUCAO.md` (seção ESTADO DE ATIVAÇÃO + CHECKPOINT).

---

## CONTEXTO (o que já está pronto)

Fase de WIRING da evolução do agente: tornar funcionais as features que estavam em "shadow scaffolding".
Worktree isolada: `.claude/worktrees/agente-evolucao` (branch `feat/agente-evolucao`). **13 commits, NÃO pushados, `main` intocada, 607 passed / 0 failed, todas as flags OFF.**

Já wirado (code-complete na branch, cadência subagent-driven com spec+code-review por sub-task):
- **Tarefa 1 — E2-enqueuer:** varredor D8 (módulo 29) enfileira `judge_step` → `outcome_signal['judge']`. Fila `agent_judge` (LEVE). Flag `AGENT_STEP_JUDGE`.
- **Tarefa 2 — Super-loop shadow:** **2a** fix `_signal_async_event` (baseline `pending_questions` 2 falhas → 0); **2b** `verify_step_shadow` (3 verifiers) → `outcome_signal['verify']` (módulo 30, flag `AGENT_VERIFY`); **2c** `triage_step_shadow` → `outcome_signal['triage']` (módulo 31, flag `AGENT_PLANNER`). **B3 (replan/escalate) ADIADO COM PREMISSA** (ver memória `b3-escalate-adiado-premissa`).
- **Tarefa 3 — A3-invoke FASE 1:** tabela `agent_eval_scores` + model `AgentEvalScore` (migration aplicada local); `build_subprocess_invoke_fn` (`claude -p --agent <nome>`); job RQ `run_eval_batch` (fila `agent_eval` PESADA); módulo 28 passa a ENFILEIRAR. Flag `AGENT_EVAL_GATE`. **Verificada por MOCK (zero API).**

**Os 4 sinais coexistem em `AgentStep.outcome_signal`** (merge): `judge`/`verify`/`triage` + a tabela `agent_eval_scores` (eval-gate).

---

## ETAPA A — TESTAR o que foi construído (local, baixo risco)

**Setup do ambiente (gotcha conhecido):** a worktree não tem `.env` próprio — pytest sem `DATABASE_URL` cai em SQLite fallback ("no such table"). Use o venv da raiz e garanta o DATABASE_URL do Postgres local:
```bash
cd /home/rafaelnascimento/projetos/frete_sistema/.claude/worktrees/agente-evolucao
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
# DATABASE_URL deve apontar para o Postgres local (herdado do ambiente da raiz)
```

**1. Suíte completa (deve dar 607 passed / 0 failed):**
```bash
python -m pytest tests/agente/ -q
```

**2. Smoke dos jobs shadow (sem Redis/worker — testa a lógica):**
```bash
python -m pytest tests/agente/workers/test_step_judge.py \
                 tests/agente/workers/test_plan_verifier.py \
                 tests/agente/workers/test_triage_shadow.py \
                 tests/agente/workers/test_eval_runner.py \
                 tests/agente/services/test_eval_gate.py \
                 tests/agente/services/test_build_invoke_fn.py \
                 tests/agente/models/test_agent_eval_score.py -v
```

**3. Smoke dos varredores (com flag ON local + Queue mockada) — opcional:**
Cada enquecedor (`enqueue_pending_judges`/`_verifies`/`_triages`) com `queue=MagicMock()` + `patch` da flag ON enfileira só os steps recentes sem o sinal correspondente. Ver os testes `test_*_wiring_produtor_consumidor`.

**4. Queries de observação (quando as flags estiverem ON em PROD/shadow — ver `VALIDACAO.md`):**
```sql
-- judge / verify / triage por step
SELECT step_uid,
       outcome_signal->'judge'->>'score'     AS judge_score,
       outcome_signal->'verify'->'adversarial'->>'refuted' AS verify_refuted,
       outcome_signal->'triage'->>'steps'     AS triage_steps
FROM agent_step
WHERE outcome_signal ?| array['judge','verify','triage']
ORDER BY created_at DESC LIMIT 20;

-- baseline de eval por agente
SELECT agent_name, score, passed, total, mode, recorded_at
FROM agent_eval_scores ORDER BY recorded_at DESC LIMIT 20;

-- prova flag-OFF (deve ser tudo 0 enquanto não ligar)
SELECT count(*) FILTER (WHERE outcome_signal ? 'judge')  AS com_judge,
       count(*) FILTER (WHERE outcome_signal ? 'verify') AS com_verify,
       count(*) FILTER (WHERE outcome_signal ? 'triage') AS com_triage
FROM agent_step;
```

---

## ETAPA B — A3 FASE 2 (supervisionada — custa API, valida o headless)

Objetivo: provar que `claude -p --agent <nome>` roda headless contra os golden cases e produz scores sensatos → estabelecer o baseline real.

```bash
# 1 dataset por vez (analista-carteira tem 5 casos; comece por ele)
python -m app.agente.workers.eval_runner --agent analista-carteira
```
**CAVEAT I2 (inviolável):** ANTES de confiar no baseline, inspecione `cases[].evidence` de cada caso. Um `stdout` vazio com `rc=0` (agente não-encontrado, sem tools no headless, etc.) é julgado `fail` pelo Haiku-judge SEM sinalizar erro de infra → score falso-baixo. Se vários casos tiverem evidence vazio/estranho, o invoke headless precisa de ajuste (ex: `--mcp-config` para as tools, ou `AGENT_EVAL_MODEL`/`AGENT_EVAL_TIMEOUT`).

Decisões a confirmar com o Rafael na Fase 2: modelo do invoke (`AGENT_EVAL_MODEL`, default = frontmatter do subagente), timeout (`AGENT_EVAL_TIMEOUT` default 600s), e se as tools MCP precisam ser injetadas.

---

## ETAPA C — GATEs (ação do Rafael; destrava o resto)

1. **Push/deploy** da branch `feat/agente-evolucao` (= deploy PROD). **NÃO faça push sem decisão explícita do Rafael.**
2. **Ligar flags em shadow** e coletar vereditos ≥1 semana:
   `AGENT_STEP_JUDGE=true` · `AGENT_VERIFY=true` · `AGENT_PLANNER=true` · `AGENT_EVAL_GATE=true`.
   (Ideal: `AGENT_ODOO_AUDIT_HOOK=true` p/ a âncora ambiental do judge.)
3. Observar as queries da Etapa A.4 + logs `[JUDGE_ENQUEUER]`/`[VERIFY_ENQUEUER]`/`[TRIAGE_ENQUEUER]`/`[EVAL_GATE]` no Render.

---

## ETAPA D — CONTINUAR a implementação (A4 — a última)

Quando o baseline A3 estiver estabelecido, peça: **"recon + plano da A4"**. A4 = promoção automática de diretriz:
job D8 que varre PlanStates bem-sucedidos → `propose_directive_from_plan` → `evaluate_and_promote` (gate A3 + anti-gaming R9) → (gated) promove. Requer migration dupla `directive_status`. **É a mais arriscada (muda comportamento ATIVO do agente).** Reusa `directive_promotion_service.py` (lógica já existe shadow) + `_build_operational_directives`.

E, quando existir o super-loop INLINE (steps = subagentes com `agent_id`): wirar **B3** (replan/escalate). Ver `b3-escalate-adiado-premissa`.

---

## REGRAS DA CADÊNCIA (mantidas)

- **Subagent-driven:** 1 subagente/tarefa + spec-review + code-review; minha verificação (pytest + diff) entre etapas.
- **TUDO flag-OFF/shadow primeiro.** Migration dupla se houver schema. TDD.
- **NÃO fazer push sem autorização** (push = deploy PROD). Trabalhar na worktree `feat/agente-evolucao`.
- Best-effort em tudo (INV-6); âncora ambiental Odoo R9 DOMINA (anti-reward-hacking).
- Atualizar `EXECUCAO.md` a cada item.
- **Lição cara desta sessão:** RQ 2.6.1 `Job.set_id` rejeita `:` no id — qualquer `job_id` derivado de `step_uid` (que é `{session_id}:{turn_seq}`) DEVE sanitizar `:`→`-`. Teste com `assert ':' not in job_id` (MagicMock não pega).
