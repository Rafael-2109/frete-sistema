<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Plano — Fix A3: Judge Granular + SSL-drop na persistência

> **Papel:** Plano — Fix A3: Judge Granular + SSL-drop na persistência.

> Origem: A3 Fase 2 (2026-05-31) expôs 2 bugs reais. Baseline analista-carteira deu 0.600 (3/5),
> mas inspeção I2 provou que ac-03/ac-04 são FALSOS-NEGATIVOS do judge binário (agente acertou).
> Cadência: subagent-driven (implementer TDD + spec-review + code-review + verificação Rafael/Claude).
> Flag-OFF (path já gateado por AGENT_EVAL_GATE). SEM migration (nenhum schema muda). NÃO push.

---

## BUG-1 — Judge binário subestima o agente

**Onde**: `app/agente/services/eval_gate_service.py`
- `_call_haiku_eval` (`:48-67`): system prompt retorna SÓ "pass"/"fail".
- `_judge_case` (`:218-220`): `status = 'pass' if verdict=='pass' else 'fail'`.
- `run_evals` (`:304-308`): `passed += 1 if status=='pass'` → `score = passed/total`.

**Problema**: 1 item de `expected_behavior` faltando (ou must_not equivalente-superior) zera o caso inteiro.
ac-03 (limite carreta) e ac-04 (devolução) atenderam ~4/5 itens mas viraram fail binário.

**Fix**:
1. Novo `_call_haiku_eval_granular(prompt) -> dict`: system prompt instrui o Haiku a retornar
   JSON `{"passed_items": int, "total_items": int, "failing": [str]}` — CONTA itens atendidos.
   Tolerante a comportamento equivalente-superior (item considerado atendido se a INTENÇÃO foi cumprida,
   mesmo com fraseado diferente).
2. `_judge_case`: calcula `case_score = passed_items/total_items` (0.0 se total=0).
   `status = 'pass' if case_score >= PASS_THRESHOLD else 'fail'`, `PASS_THRESHOLD = 0.80` (decisão Rafael).
   Mantém `evidence` = resumo (passed/total + failing).
3. `run_evals`: `score = mean(case_scores)` (não `passed/total`). `passed` = nº de casos com status='pass'
   (retrocompat com o campo). Adiciona `case_score` a cada item de `cases[]`.

**Retrocompat (INVIOLÁVEL — 27 testes existentes)**:
- `judge_fn` default passa a ser `_call_haiku_eval_granular`, MAS `_judge_case` aceita AMBOS:
  se `judge_fn` retorna str "pass"/"fail" (os mocks dos 27 testes), mapeia para case_score 1.0/0.0
  (pass→1.0→status pass; fail→0.0→status fail). Detecção: `isinstance(verdict, str)` vs `dict`.
- Os 27 testes de test_eval_gate.py usam `mock_judge_fn -> 'pass'/'fail'` → continuam verdes
  (1.0≥0.8=pass, 0.0<0.8=fail). Score agregado deles (binário) inalterado.

**Testes novos (TDD, escrever ANTES)**:
- judge granular: mock retorna `{passed_items:4, total_items:5}` → case_score 0.8 → status pass.
- mock `{passed_items:2, total_items:5}` → 0.4 → status fail.
- run_evals com 2 casos (0.8 e 0.4) → score agregado 0.6 (média), passed=1.
- retrocompat: mock str 'pass' → case_score 1.0; str 'fail' → 0.0.
- total_items=0 (dataset sem expected) → case_score 0.0 sem ZeroDivisionError.

---

## BUG-2 — SSL-drop ao persistir após invokes longos

**Onde**: `app/agente/workers/eval_runner.py` `_run_eval_batch_in_context` (`:118-192`).
**Sequência atual**: `get_baseline_score` (`:136`, abre conexão) → `run_evals` (`:150`, ~8min SEM tocar DB)
→ `insert_score` (`:158`) + `commit` (`:183`) na conexão IDLE → `OperationalError: SSL connection closed`.
**Em PROD**: 4 datasets, 20-50min idle → falha garantida. Observado nesta sessão: `agentes=0`, nada gravado.

**Fix** (espelha workaround validado em /tmp/a3_inspect.py — persistiu 0.600 com sucesso):
1. Reordenar: para cada agente, rodar `run_evals` (invokes) ANTES de tocar o DB.
   Guardar resultados em lista `[(agent_name, result), ...]`.
2. SÓ DEPOIS de todos os invokes: bloco de persistência com `db.session.rollback()` defensivo
   (limpa conexão potencialmente morta) + 1 retry. Para cada (agent, result):
   `get_baseline_score` → `eval_gate` (log) → `insert_score`. `commit` final.
3. Retry: se o 1º `commit`/`get_baseline` levanta `OperationalError`, `db.session.rollback()`
   (força reconexão no próximo uso do pool) e repete UMA vez. Best-effort INV-6: 2ª falha → log + `agentes=0`.
4. **Constraint 1 preservada**: `get_baseline_score` ainda ANTES de `insert_score` do mesmo agente
   (agora ambos no bloco final, mas baseline lido antes do insert na mesma iteração).

**Testes novos (TDD)**:
- simula `OperationalError` no 1º `get_baseline_score` (ou commit) via mock → `rollback` chamado →
  2ª tentativa sucede → score persistido. Spy em rollback+commit.
- 7 testes existentes de test_eval_runner.py verdes (run_evals mockado, ordem preservada).

---

## Arquivos (numerado)

1. `app/agente/services/eval_gate_service.py` — judge granular + _judge_case score parcial + run_evals média.
2. `app/agente/workers/eval_runner.py` — reordenar invokes-antes-DB + rollback/retry na persistência.
3. `tests/agente/services/test_eval_gate.py` — +5 testes granular/retrocompat (27 existentes verdes).
4. `tests/agente/workers/test_eval_runner.py` — +1 teste SSL-retry (7 existentes verdes).

**Migration**: NENHUMA (score já é float em agent_eval_scores).
**Flag**: nenhuma nova; só atua no path AGENT_EVAL_GATE (já OFF).
**DoD**: TDD verde + 34 testes (27+7) intactos + code-review + EXECUCAO.md atualizado + re-baseline local.

## Verificação final
Re-rodar A3 local (analista-carteira) com judge granular → baseline confiável (esperado ~0.9+,
pois ac-03/ac-04 sobem). Comparar com 0.600 binário. NÃO push (deploy = decisão Rafael).
