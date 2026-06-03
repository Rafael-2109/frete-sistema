<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# GATE-1 — Calibração do Judge Online (E3 re-apontado) + correção de bugs do verify — Implementation Plan

> **Papel:** plano executável para FECHAR o GATE-1 (destrava a Onda 3 do flywheel) tornando o sinal de qualidade do online judge CONFIÁVEL, após a aposentadoria do A3.
> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:executing-plans` (inline) ou `superpowers:subagent-driven-development`. Steps usam checkbox (`- [ ]`).

## Indice

- [Cabeçalho do plano (goal / arquitetura / stack)](#cabecalho)
- [Estado de PROD ancorado](#estado-de-prod-ancorado)
- [Mapa da espinha após aposentadoria do A3](#mapa-da-espinha)
- [File Structure](#file-structure)
- [Task 1 — Reconciliar ROADMAP](#task-1)
- [Task 2 — Fix bug do parser verify_arithmetic](#task-2)
- [Task 3 — Reconciliar judge x adversarial](#task-3)
- [Task 4 — E3 re-apontado: sampler de calibração](#task-4)
- [Task 5 — UI de spot-check humano + concordance](#task-5)
- [Task 6 — Ligar flag + deploy + GATE-1](#task-6)
- [Ordem de execução e o que é "fim do plano"](#ordem-de-execucao)
- [Self-Review](#self-review)

## Cabeçalho

**Goal:** Tornar o sinal de qualidade do agente CONFIÁVEL o suficiente para fechar o GATE-1 — corrigindo os bugs de parser dos verifiers (arithmetic/adversarial), reconciliando judge↔adversarial, e re-apontando a calibração (E3) do A3 morto para o **online judge** (`agent_step.outcome_signal['judge']`), com spot-check humano e `concordance_rate`.

**Architecture:** O A3 (eval offline caro) foi APOSENTADO (2026-06-03). O sinal vivo em PROD é o online judge (`workers/step_judge.py`) + verify (`workers/plan_verifier.py` + `sdk/verifiers.py`), gravado por step em `agent_step.outcome_signal`. A infra de calibração R3 (`AgentEvalCase`, `sample_unreviewed`, `concordance_rate` — genéricas) estava sendo populada SÓ pelo `eval_runner` (A3 morto) → nunca mais alimentada. Este plano re-aponta a fonte da calibração para os vereditos do online judge e corrige os bugs que tornam o sinal ruidoso.

**Tech Stack:** Python 3.12, Flask 3.1, SQLAlchemy 2.0, RQ (fila `agent_judge`), Anthropic SDK (Haiku judge / Sonnet verifier), pytest. Flags em `app/agente/config/feature_flags.py`. UI Jinja2 (`templates/agente/insights.html` + `routes/insights.py`).

**Branch/worktree:** `worktree-feat+gate1-calibracao-judge` (`.claude/worktrees/feat+gate1-calibracao-judge`), base `origin/main`@`418a717d3`.

**Regra inviolável:** NÃO reativar o A3 nem rodar evals LLM caros (`claude -p --agent` em lote). Toda medição = Haiku/Sonnet (judge/verify, já em PROD) + rotulagem humana barata. Cada card: TDD (RED→GREEN), aditivo, flag-gated, 1 commit. Atualizar ROADMAP/EXECUCAO a cada card.

## Estado de PROD ancorado

> Verificado 2026-06-03 via MCP Render PG `dpg-d13m38vfte5s738t6p50-a`.

- `agent_step`: 201 steps / 3 dias úteis; judge/verify/frustration 201/201, triage 200/201.
- `verify.arithmetic.ok=false` em **42/201** — confirmado como **bug de parser** (não inconsistência real, na maioria): o Sonnet raciocina passo-a-passo e conclui com "OK"/✓, mas o parser exige `resultado.upper()=='OK'` exato (`verifiers.py:104-105`). Mix (alguns dos 42 são reais, ex. step 194).
- judge↔adversarial discordam **63%** (127/201) — causa a investigar (Task 3): provável mesma classe de bug de parser no adversarial + critérios divergentes.
- `agent_eval_case` = **0 casos** (a fonte — `eval_runner`/A3 — foi aposentada).
- GATE-1 = ❌ (sinal não-confiável + 0 calibração humana).

## Mapa da espinha

Após aposentadoria do A3:

```
E1 outcome_signal (PROD) -> E2 step_judge (PROD shadow) -> E3 calibracao do judge ONLINE -> E4 fused_score
                                                              | (este plano)
GATE-1 = E2 confiavel (bugs corrigidos) + >=1 semana de dados + concordance humana >=80%
```

O card O1.4 (A3 baseline) do ROADMAP está MORTO (A3 aposentado). O O1.5 (E3) re-aponta para o online judge.

## File Structure

| Arquivo | Responsabilidade | Ação |
|---|---|---|
| `docs/blueprint-agente/ROADMAP.md` | Fila viva — reconciliar A3 morto + re-apontar O1.5/O1.G | Modify (Task 1) |
| `docs/blueprint-agente/EXECUCAO.md` | Narrativa — registrar progresso | Modify (cada card) |
| `app/agente/sdk/verifiers.py` | `verify_arithmetic` + `ARITHMETIC_SYSTEM_PROMPT` — fix do parser | Modify (Task 2) |
| `tests/agente/sdk/test_verifiers.py` | testes do fix arithmetic | Create/Modify (Task 2) |
| `app/agente/workers/plan_verifier.py` | `verify_plan_adversarial` + `ADVERSARIAL_SYSTEM_PROMPT` + agregação verify | Modify (Task 3) |
| `app/agente/workers/calibration_sampler.py` (NOVO) | varredor que popula `agent_eval_case` a partir de `agent_step.outcome_signal.judge` | Create (Task 4) |
| `app/agente/scheduler/sincronizacao_incremental_definitiva.py` | novo módulo D8 que enfileira/roda o sampler | Modify (Task 4) |
| `app/agente/models.py` | `AgentEvalCase` — helper extra se necessário | Modify (Task 4, se preciso) |
| `app/agente/routes/insights.py` + `templates/agente/insights.html` | UI admin de spot-check + concordance | Modify (Task 5) |
| `app/agente/config/feature_flags.py` | `AGENT_EVAL_CALIBRATION` (já existe) + nova flag do sampler | Modify (Task 4/6) |

## Task 1

**Reconciliar ROADMAP (aposentadoria do A3 + re-apontar E3).** Files: Modify `docs/blueprint-agente/ROADMAP.md`

- [ ] **Step 1:** Atualizar card O1.4 — marcar A3 baseline ❌ APOSENTADO (eval LLM caro vetado), removê-lo como dependência de O1.5.
- [ ] **Step 2:** Re-escrever card O1.5 (E3) — fonte da calibração = ONLINE judge (`agent_step.outcome_signal.judge`), NÃO `eval_runner`. Dep: O1.3 (não O1.4). DoD: concordance≥80% sobre ≥10 steps rotulados.
- [ ] **Step 3:** Atualizar O1.G (GATE-1) — dep = O1.3 + O1.5 re-apontado.
- [ ] **Step 4:** Atualizar a "espinha de dependência" removendo o A3.
- [ ] **Step 5:** Commit — `docs(roadmap): reconcilia E3 pós-aposentadoria A3 (calibra online judge)`.

## Task 2

**Fix bug do parser `verify_arithmetic` (falso-positivo 42/201).** Files: Modify `app/agente/sdk/verifiers.py` (`ARITHMETIC_SYSTEM_PROMPT` :26-37, `verify_arithmetic` :60-115); Test `tests/agente/sdk/test_verifiers.py`.

**Root cause:** o parser confia que o Sonnet responde "OK" literal (`resultado.upper()=='OK'`, :104), mas o Sonnet raciocina e conclui com "OK"/✓ → cai no `else` → `ok=False` com o raciocínio como issue. Fix defense-in-depth: prompt determinístico (`ERRO:` só se há erro) + parser por **presença do marcador `ERRO`**.

- [ ] **Step 1: Escrever testes falhando** (`tests/agente/sdk/test_verifiers.py`):

```python
from unittest.mock import patch
from app.agente.sdk.verifiers import verify_arithmetic


class TestVerifyArithmeticParser:
    """Bug 2026-06-03: Sonnet raciocina e conclui com 'OK'/checkmark (aritmetica
    correta), mas o parser exigia 'OK' EXATO -> falso-positivo ok=False (42/201)."""

    def _run(self, fake_out):
        with patch('app.agente.sdk.verifiers._call_sonnet_verifier', return_value=fake_out):
            return verify_arithmetic("resposta qualquer com numeros")

    def test_ok_literal(self):
        assert self._run("OK") == {'ok': True, 'issues': []}

    def test_raciocinio_concluindo_ok_e_correto(self):
        out = "Verificando: 1.549 + 290 + 2 + 25 = 1.866 OK\n\nOK"
        assert self._run(out)['ok'] is True

    def test_raciocinio_sem_erro(self):
        out = "41 + 37 + 3 = 81, confere com o total declarado.\n\nOK"
        assert self._run(out)['ok'] is True

    def test_erro_real_marcado(self):
        r = self._run("ERRO: total diz 5 itens mas a tabela tem 8")
        assert r['ok'] is False and 'ERRO' in r['issues'][0]

    def test_erro_real_apos_raciocinio(self):
        out = "Soma: 10 + 20 = 30, mas o texto diz 35.\nERRO: 30 != 35"
        assert self._run(out)['ok'] is False

    def test_vazio_e_ok(self):
        assert self._run("") == {'ok': True, 'issues': []}
```

- [ ] **Step 2: Rodar para falhar** — `python -m pytest tests/agente/sdk/test_verifiers.py::TestVerifyArithmeticParser -v`. Esperado FAIL em `test_raciocinio_concluindo_ok_e_correto` e `test_raciocinio_sem_erro`.
- [ ] **Step 3: Corrigir o prompt** (`verifiers.py:34-36`): trocar "responda EXATAMENTE: OK" por instrução determinística — "Pode raciocinar. Só use o prefixo 'ERRO:' SE houver erro aritmético (ex: 'ERRO: total diz 5 mas tabela tem 8'). Sem erro: NÃO use a palavra 'ERRO'."
- [ ] **Step 4: Corrigir o parser** (`verify_arithmetic` :100-110): substituir o teste `== 'OK'` por presença do marcador:

```python
        raw = _call_sonnet_verifier(prompt)
        resultado = raw.strip() if raw else ''
        import re
        # Parser robusto a raciocinio (bug 2026-06-03): sem marcador 'ERRO' = sem inconsistencia,
        # mesmo que o Sonnet conclua com raciocinio longo + 'OK'/checkmark.
        if not resultado or not re.search(r'\bERRO\b', resultado, re.IGNORECASE):
            logger.debug('[verify_arithmetic] OK')
            return {'ok': True, 'issues': []}
        logger.warning(f'[verify_arithmetic] inconsistencia: {resultado}')
        return {'ok': False, 'issues': [resultado]}
```

- [ ] **Step 5: Rodar testes** — `python -m pytest tests/agente/sdk/test_verifiers.py -v`. Esperado PASS.
- [ ] **Step 6: Regressão** — `python -m pytest tests/agente/services/test_eval_gate.py tests/agente/workers/ -q`. Baseline mantido.
- [ ] **Step 7: Commit** — `fix(verify): parser de verify_arithmetic robusto a raciocinio do Sonnet (falso-positivo 42/201)`.

## Task 3

**Investigar judge↔adversarial (discordância 63%) — ✅ RECON CONCLUÍDO 2026-06-03.**

**Resultado do recon (PROD, 201 steps com judge+adversarial):**
- O adversarial usa o campo `refuted` (não `ok`); parser = JSON robusto (`_parse_adversarial_json`) — **NÃO é a mesma classe de bug do arithmetic.**
- 127/201 (63%) `refuted=true`. Distribuição vs `judge.label`: 51 refuta `failure` (concordam: ruim), **39 refuta `success`** (discorda do judge), 41 aceita `failure`.
- **Amostra dos 39 `reason` (refuta success) = SUBSTANTIVOS, não viés genérico**: "agente disse 'agora exporto' mas não confirmou salvamento real"; "judge deu 92 só pela saída do Bash, sem verificar se os 25 são realmente 'sem match'"; "Bash não valida operações Odoo, score alto por interpretação vaga ('certo')".

**Decisão (registrada — anti-drift):** a discordância **é SINAL, não ruído**. O adversarial aponta um **viés de CREDULIDADE do judge** (dá `success` quando tools rodam, sem exigir evidência de que a conclusão foi validada/persistida) — alinhado ao eixo E §2.4 (judge deve medir *correctness vs intenção*, não só faithfulness). **NÃO mexer no `JUDGE_SYSTEM_PROMPT` agora** (mudar o prompt do judge sem veredito humano = especular, pode piorar). A reconciliação se materializa na **Task 4**: o sampler de calibração **prioriza** para spot-check humano os casos `judge=success ∧ adversarial.refuted=true` (maior valor de calibração — onde os dois sinais disputam). O humano decide; o resultado (concordance + few-shot, eixo E §2.5) é que informará um eventual re-prompt do judge (frente futura O2/E4).

**Sem mudança de código de produção nesta task** (decisão = não especular). Materializa-se na Task 4.

**DoD:** achado + decisão documentados (aqui + EXECUCAO.md); priorização incorporada na Task 4.

## Task 4

**E3 re-apontado: sampler de calibração do online judge.** Files: Create `app/agente/workers/calibration_sampler.py`; Modify scheduler + feature_flags; Test `tests/agente/workers/test_calibration_sampler.py`.

**Decisão de design:** reusar `AgentEvalCase` (genérica) como store dos casos a rotular, populada a partir dos STEPS julgados pelo online judge. Mapeamento: `case_id=step_uid`, `case_score=judge_score/100`, `evidence=judge_reason`, campos eval-offline (`n_runs`/`variance`/`invoke_failures`) com default. `sample_unreviewed`/`concordance_rate` (genéricos) funcionam sem mudança.

- [ ] **Step 0 (recon):** confirmar estrutura de `outcome_signal['judge']` (`step_judge.py:_judge_core` + 2-3 linhas PROD).
- [ ] **Step 1 (TDD):** `populate_calibration_cases(window_hours, cap)` — varre `agent_step` com judge presente, sem caso correspondente em `agent_eval_case` (dedup por `case_id=step_uid`), insere via `insert_case`. Flag `AGENT_EVAL_CALIBRATION`. Best-effort (INV-6). **PRIORIZAÇÃO (materializa a Task 3):** ordenar/selecionar primeiro os steps `judge.label='success' ∧ verify.adversarial.refuted=true` (discordância de alto valor) e os de `frustration_score` alto — são os casos onde a rotulagem humana mais calibra o judge. Gravar a razão da prioridade em `evidence` (ex: incluir o `adversarial.reason`).
- [ ] **Step 2:** implementar (espelha `enqueue_pending_judges` `step_judge.py:310+`).
- [ ] **Step 3:** wirar módulo D8 (espelha módulos 29/30/31; por-ciclo; report-only; try/except).
- [ ] **Step 4:** testes verdes + commit `feat(e3): sampler de calibracao popula agent_eval_case do online judge`.

**DoD:** com `AGENT_EVAL_CALIBRATION=true`, `agent_eval_case` cresce a partir dos steps julgados em PROD.

## Task 5

**UI de spot-check humano + concordance.** Files: Modify `routes/insights.py` + `templates/agente/insights.html` (+ JS); Test `tests/agente/routes/test_insights_calibration.py`.

**Decisão:** reusar o dashboard insights (admin), espelhando o card "Adesão de Regras" (O0.3). POST grava `human_verdict`/`human_note`/`reviewed_by`/`reviewed_at` (padrão `sql_evaluator_falses_service.record_false_positive`).

- [ ] **Step 0 (recon):** ler `routes/insights.py` + `insights.html` (padrão O0.3) + auth admin.
- [ ] **Step 1 (TDD):** GET retorna amostra + concordance; POST grava verdict (admin-only).
- [ ] **Step 2:** implementar rota + template + link no menu (tela sem acesso UI é proibida — regra do projeto).
- [ ] **Step 3:** lint UI `python scripts/audits/ui_policy_lint.py --enforce-new` = 0.
- [ ] **Step 4:** testes + commit `feat(e3): UI admin de spot-check do judge + concordance_rate`.

**DoD:** `/agente/insights` permite rotular agree/disagree e mostra `concordance_rate`.

## Task 6

**Ligar `AGENT_EVAL_CALIBRATION` + deploy + abertura do GATE-1** (operacional).

- [ ] **Step 1:** Merge da branch em main (pós code-review) + push → deploy.
- [ ] **Step 2:** Migration — `agent_eval_case` já existe em PROD (O0.5); sem DDL nova (a menos que Task 4 adicione coluna → migration dupla .py+.sql).
- [ ] **Step 3:** Ligar `AGENT_EVAL_CALIBRATION=true` no web (srv-d13m38vfte5s738t6p60).
- [ ] **Step 4:** Verificar PROD — `agent_eval_case` cresce; UI lista; rotular 5-10 casos; medir `concordance_rate`.
- [ ] **Step 5 (validação — tempo/humano):** ≥1 semana de dados úteis + concordance≥80% sobre ≥10 casos. Infra fica 100% pronta+ligada; resta coleta.

**DoD GATE-1:** bugs verify corrigidos (Task 2/3) + sampler ativo (Task 4) + UI (Task 5) + ≥1 semana + concordance≥80%. As 3 primeiras são CÓDIGO (fecháveis agora).

## Ordem de execucao

Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6.

**"Fim do plano" entregável por código:** Tasks 1-5 mergeadas+deployadas + flag ligada (Task 6 steps 1-4). O GATE-1 formal (Task 6 step 5) depende SÓ de coleta (≥1 semana + rotulagem humana) — sem código pendente. É isso que impede a frente de "ficar incompleta": ao fim, NÃO há código pela metade, só dado a acumular.

## Self-Review

- Cobertura GATE-1 (O1.G) = bugs verify (Task 2/3) + E3 re-apontado (Task 4) + spot-check (Task 5) + ligar (Task 6). OK.
- Aposentadoria do A3 reconciliada (Task 1). OK.
- Tasks 3/4/5 têm Step 0 de recon explícito (decisão de design depende de evidência — não placeholder). OK.
- Reuso: `AgentEvalCase`/`sample_unreviewed`/`concordance_rate` (genéricos), padrão `enqueue_pending_judges`, card O0.3 (UI), `sql_evaluator_falses_service` (calibração avançada futura). OK.
