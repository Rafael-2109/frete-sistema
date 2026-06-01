# Plano — A3 como GATE DE REGRESSÃO (fiel à spec)

> Telos da A3 (eixos/A-flywheel.md:257-266): fechar Ruptura #5 (golden dataset fora do loop)
> e Ruptura #3 (verified = opinião do Sonnet, sem baseline antes/depois). A A3 NÃO é vestibular
> que dá nota — é GATE DE REGRESSÃO no fluxo de commit do D8, report-only → enforce.
> Cadência: subagent-driven (TDD + spec-review + code-review). Flag-OFF. NÃO push.

---

## FIDELIDADE À SPEC (o que a A3 deve ser, com fonte)

1. **`A-flywheel.md:257-260`**: "run_eval.py que executa os dataset.yaml via judge calibrado.
   Adicionar PASSO ao dominio-8: rodar eval ANTES do commit; report-only antes de enforce."
2. **`A-flywheel.md:186`**: "regression-eval contra golden dataset confirma que a mudança NÃO
   REGREDIU antes de ligar em produção." → mede Δ (antes vs depois), não score absoluto.
3. **`A-flywheel.md:165`**: "Calibração obrigatória: spot-check humano de 5-10% das notas do judge."
4. **`run_eval.md:121`**: "Resposta inconsistente entre runs: LLMs são não-determinísticos.
   **Rodar 3x e considerar o comportamento predominante.**" → N-runs já prescrito.
5. **`run_eval.md:131-133`**: a automação prevista = "script lê dataset → invoca claude --agent →
   LLM-as-judge → integração pre-commit". É exatamente o que A3 fecha.
6. **`critica/A-flywheel.md:111-116`**: "judge scores são flaky tests até provados estáveis;
   processo EXTERNO ao agente avaliado (réu não preside o júri)." → o runner roda `claude -p`
   num subprocesso isolado, não dentro do agente. JÁ ATENDIDO por build_subprocess_invoke_fn.

## O QUE JÁ EXISTE (não reinventar)

- `run_evals` + `eval_gate` (report_only) + `build_subprocess_invoke_fn` (`claude -p --agent`).
- `agent_eval_scores` (baseline persistido). Judge granular + SSL-drop (commits desta sessão).
- `evaluate_and_promote` (A4) JÁ chama `eval_gate(baseline, candidate)` e JÁ tem a hierarquia
  correta: `_tem_falha_odoo` (âncora R9) ANTES do gate de score (anti-reward-hacking da spec).
- 4 datasets, formato expected_behavior/must_not.

## O QUE FALTA vs spec (os 4 itens do plano)

---

### A3-R1 — run_eval N-runs + agregação (domar o flaky)  [Task #4]

**Por quê**: `run_eval.md:121` manda rodar 3x. Hoje `run_evals` roda 1x → o Δ do gate seria
dominado por ruído não-determinístico (provado nesta sessão: ac-01 oscilou pass→0.75 entre runs).

**Onde**: `eval_gate_service.py` `run_evals`.
**Como**:
- Novo param `n_runs: int = 3`. Para cada caso, invoca o agente `n_runs` vezes, agrega os
  case_scores por **mediana** (robusta a outlier; "comportamento predominante" da spec).
- Reporta `case_score_variance` por caso (sinal de instabilidade — caso com variância alta
  é flaky e o gate deve descontá-lo / sinalizar).
- Retrocompat: `n_runs=1` reproduz o comportamento atual (os testes existentes não mudam).
- Best-effort: um run que falha (invoke erro) não derruba os outros do mesmo caso.
**Custo**: 3× invokes. Mitigação: `n_runs` configurável via env `AGENT_EVAL_N_RUNS`.
**TDD**: mock invoke_fn que retorna scores variáveis por chamada → mediana correta + variância.
27+ testes existentes verdes (n_runs default não quebra, mas mexe na agregação — cuidar).

---

### A3-R2 — gate de regressão Δ (código-antes vs código-depois)  [Task #5]

**Por quê**: a A3 é regression-eval (`A-flywheel.md:186`). Mede se uma MUDANÇA DE CÓDIGO
(o que o D8 commita) regrediu o agente. Variável = git_sha (não diretriz — isso é A4).

**Onde**: novo `run_eval_regression_gate` em `eval_runner.py` (ou módulo novo `eval_regression.py`).
**Como**:
- Assinatura: `run_eval_regression_gate(agent_name, sha_baseline, sha_candidate, n_runs=3)`.
- Roda os datasets do agente em DOIS checkouts: faz `git worktree add` temporário no sha_baseline,
  roda `run_evals` lá; roda `run_evals` no sha_candidate (cwd atual); compara.
  - ALTERNATIVA mais simples (decidir no spec-review): se o baseline já está em `agent_eval_scores`
    com o mesmo dataset+n_runs, reusa o score persistido como baseline (evita re-rodar o antigo).
    Só re-roda o candidate. Mais barato; risco = baseline velho. Híbrido: reusa se sha bate.
- Chama `eval_gate(baseline_score, candidate_score, mode='report_only')` → Δ + regression flag.
- Persiste o resultado (qual sha, Δ, regrediu?) — reusa `agent_eval_scores` + git_sha (já tem coluna).
- **Report-only SEMPRE nesta fase** (a spec: report-only → enforce; enforce é decisão futura).
**TDD**: mock run_evals retornando scores diferentes por sha → Δ correto, regression detectada
quando candidate < baseline - threshold. git worktree mockado/skipado no teste unit.
**Invariante**: NUNCA bloqueia (report_only). O `eval_gate` já garante `blocked=False` em report_only.

---

### A3-R3 — calibração do judge (spot-check humano 5-10%)  [Task #6]

**Por quê**: `A-flywheel.md:165` exige spot-check humano de 5-10% das notas do judge. Sem isso,
o judge não é "calibrado" (a spec chama o runner de "judge CALIBRADO", `A-flywheel.md:198`).
Sem calibração, trocamos um proxy cego (eco) por outro (Sonnet/Haiku não-auditado) — exatamente
o que `A-flywheel.md:318` adverte.

**Onde**: novo mecanismo de persistência dos vereditos do judge + revisão.
**Como** (V1 mínimo, fiel sem over-engineering):
- O `run_evals` já produz `cases[].evidence` (o veredito do judge granular: passed/total + failing).
- Persistir esses vereditos numa estrutura consultável (reusa `agent_eval_scores` ou tabela leve
  `agent_eval_case` 1 linha por caso/run com {agent, case_id, git_sha, case_score, evidence,
  human_verdict NULL}). Decidir no spec-review: coluna JSON em agent_eval_scores vs tabela nova.
- Mecanismo de spot-check: um modo CLI `--review` que amostra 5-10% dos casos sem human_verdict
  e os apresenta (input + output + veredito do judge) para o humano marcar concorda/discorda.
  Reusa o pattern de `sql_evaluator_falses_service` (discordância vira contra-exemplo).
- Métrica de calibração: % de concordância judge vs humano. Se < limiar (ex 80%, `A-flywheel.md:155`
  cita "85% concordância c/ humano"), o judge precisa de ajuste de prompt.
- **Reusa** `register_improvement` (MCP tool) como canal de discordância — `critica/E-qualidade.md:174`
  sugere isso explicitamente (não construir UI nova no V1).
**TDD**: persistência do veredito; amostragem determinística (seed) de 5-10%; cálculo de concordância.
**Flag-OFF**: `AGENT_EVAL_CALIBRATION`.

---

### A3-R4 — PASSO de gate no dominio-8 (report-only)  [Task #7]

**Por quê**: `A-flywheel.md:260` — "Adicionar PASSO ao dominio-8: rodar eval do(s) agente(s)
afetado(s) ANTES do commit; bloquear/registrar `regressed` se falhar." Hoje o D8 commita DIRETO
em main (`dominio-8:13`) SEM eval nenhuma (a Ruptura #5/#3).

**Onde**: `.claude/atualizacoes/dominios/dominio-8-improvement-dialogue.md` (doc do cron headless).
**Como**:
- Novo PASSO entre o PASSO 3 (IMPLEMENTAR via feature-dev) e o commit: se a mudança tocou um
  agente com golden dataset (analista-carteira, auditor-financeiro, controlador-custo-frete,
  gestor-motos-assai), rodar `run_eval_regression_gate(agent, sha_antes, sha_depois)`.
- **Report-only**: registra `regressed=true` no `AgentImprovementDialogue` (lifecycle ganha
  `measuring → verified|regressed`, conforme `A-flywheel.md:203`), mas NÃO bloqueia o commit
  nesta fase. Mesma estratégia do `ui_policy_lint` report→enforce (`critica/A-flywheel.md:105`).
- O `verified` do diálogo deixa de ser "Sonnet acha que resolveu" e passa a incluir o Δ medido
  (fecha Ruptura #3).
**Risco mapeado** (`critica/A-flywheel.md:109-116`): eval flaky pode travar o único atuador de
código autônomo → por isso report-only primeiro, e N-runs (R1) para reduzir o flaky.
**Sem código novo de produção** — é doc + (opcional) um helper que o cron chama.

---

## ORDEM (dependência)

R1 (N-runs) → R2 (gate Δ usa R1) → R3 (calibração, paralela a R2) → R4 (wiring D8 usa R2).
R3 pode começar em paralelo a R2 (ambas dependem só de R1).

## O QUE NÃO É A3 (não fazer aqui — fuga de escopo)
- **A/B com-diretiva vs sem-diretiva** = A4 (`A-flywheel.md:184`). A3 varia CÓDIGO (git_sha), A4 varia DIRETRIZ.
- **Reescrever datasets para "alinhar ao ambiente"** = trata sintoma errado. No Δ antes/depois,
  o viés constante do dataset (ex ac-05 sempre 0.43) SE CANCELA. A3 não precisa de dataset "realista".
- **verified = Δ quality_signal de PRODUÇÃO** = depende de A1 (agent_turn_quality), que NÃO existe
  (E1/E2 são shadow). A3 usa o Δ do GOLDEN DATASET (offline), que é o que a spec permite começar
  (`A-flywheel.md:266`: "pode começar A3 com gate puramente offline em paralelo a A1").

## DoD (por item)
TDD verde + retrocompat (testes existentes intactos) + flag-OFF + code-review + EXECUCAO.md + sem push.
Migration dupla SE R3 criar tabela nova (decidir no spec-review).
