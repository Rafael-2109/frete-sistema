<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/blueprint-agente/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# PROMPT — Aposentar o A3 (eval LLM caro): reverter fix + desligar flag + re-framing do GATE-1

> Estado em 2026-06-03 (tarde). A sessão de re-verificação PROD descobriu que o **A3 (eval-gate de
> golden datasets) é um eval LLM caro que o Rafael VETOU**. Esta sessão executa a aposentadoria.
> Fonte da verdade: `docs/blueprint-agente/EXECUCAO.md` (CHECKPOINT 2026-06-03 tarde + BLOQUEIOS ATIVOS).
> Regra de memória: `[[feedback_evals_llm_caros_preferir_pytest]]`.

## Por que (contexto curto, já verificado em PROD)

- `agent_eval_scores` tem 16 linhas, **TODAS `score=0/passed=0`**. Causa: o `eval_runner` invoca
  `claude -p --agent` mas o CLI `claude` NÃO está no PATH do worker (`[Errno 2] No such file or
  directory: 'claude'`) → todo caso falha (não é o bug X7/transação nem o caveat I2).
- **`AGENT_EVAL_GATE` JÁ está `true` em PROD** (módulo 28 do scheduler, 1×/dia às 11h). Como o CLI
  falha, as ~105 invocações abortam em ms (ANTES da API) → custo atual ~zero, mas grava lixo `score=0`.
- Foi feito um fix (`_resolve_claude_cli` resolve o CLI **bundled** do SDK em `_bundled/claude`) — MAS
  consertar isso **transformaria** o no-op gratuito em **~105 invocações Opus xhigh reais/dia (~$20/dia)**.
  O Rafael vetou evals LLM caros (já havia dito; ver memória). **DECISÃO: NÃO ativar o A3.**
- O sinal de qualidade que IMPORTA já existe e é barato: **judge (E2) + verify (B2)** avaliam cada
  turno real em PROD com Haiku, off-path, já ativos. O **GATE-1 deve depender da calibração do judge
  (E3)**, não do A3 caro.

## Estado do working tree (deixado de propósito para REVERTER)

Confirmar com `git status`. MODIFICADOS e NÃO commitados (são o fix a reverter):
- `app/agente/services/eval_gate_service.py` — `_resolve_claude_cli()` + uso no `build_subprocess_invoke_fn`.
- `tests/agente/services/test_build_invoke_fn.py` — classe `TestResolveClaudeCli` (3 testes) + ajuste do assert `cmd[0]`.

Os demais modificados/untracked (`docs/superpowers/plans/2026-06-03-evolucao-gerindo-agente.md`,
`.claude/skills/gerindo-agente/scripts/loop.py`, `docs/industrializacao-fb-lf/scripts/s8_hipotese_i_grounding.py`)
são de OUTRAS frentes do Rafael — **NÃO tocar**.

## Tarefas (ordem)

1. **Reverter o fix** (código-zumbi — destrava um eval vetado):
   `git restore app/agente/services/eval_gate_service.py tests/agente/services/test_build_invoke_fn.py`
   Confirmar `git diff` limpo nesses 2 arquivos.
2. **Desligar `AGENT_EVAL_GATE` em PROD** (limpeza, NÃO ativação): `update_environment_variables` no
   web `srv-d13m38vfte5s738t6p60` → `AGENT_EVAL_GATE=false`. Confirmar `enabled=False` no boot do
   scheduler e que `agent_eval_scores` para de crescer. Opcional (decidir): `DELETE` das 16 linhas
   `score=0`.
3. **Re-framing do GATE-1 no `EXECUCAO.md`**:
   - Tabela ONDA 1 (GATE-1) + tabela A3 (ONDA 3): marcar A3 como **🛑 NÃO ATIVAR (eval LLM caro vetado)**;
     remover A3 do caminho crítico do GATE-1.
   - Redefinir GATE-1 = **judge calibrado (E3)**: spot-check humano 5-10% (`agent_eval_case`, hoje 0) +
     ≥1 semana de sinal step-level; reconciliar judge↔adversarial (discordam 63%); investigar o bug
     suspeito em `verify.arithmetic.ok` (42/201 `false` com texto de evidência "OK").
   - Atualizar o BLOQUEIO A3 e o checkpoint para "aposentado/desligado".
4. **Decisão sobre o código do A3** (`eval_runner.py`, `eval_gate_service.py`, módulo 28 do scheduler):
   deprecar/remover (zumbi) OU manter OFF + documentado? Recomendar e executar com OK do Rafael.
5. **Avançar para E3** (a frente REAL do GATE-1, barata — Haiku + amostra humana): plano de calibração
   do judge. **NÃO rodar evals LLM caros.**

## Verificação (sempre PROD via MCP Render)

- PG `dpg-d13m38vfte5s738t6p50-a` · web `srv-d13m38vfte5s738t6p60` · worker `srv-d2muidggjchc73d4segg`.
- Confirmar: `AGENT_EVAL_GATE` desligado, `agent_eval_scores` não cresce, judge/verify (E2/B2)
  continuam gravando intactos, Sentry limpo. Disciplina TZ (created_at Brasil-naive vs now() UTC).

## Regra inviolável

NÃO reativar o A3. NÃO rodar evals LLM caros (`claude -p --agent` em lote). Medição de qualidade =
judge/verify (Haiku, já ativos) + calibração humana barata (E3). Ver `[[feedback_evals_llm_caros_preferir_pytest]]`.
