# Onda 2 — Atuador de Planejamento (super-loop + VERIFY) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps usam checkbox.
> **Branch**: `feat/agente-evolucao` (worktree). NÃO push. Tudo flag-OFF.
> **Spec**: `docs/blueprint-agente/EXECUCAO.md` Onda 2 + `eixos/B-planejador.md`.

**Goal:** Dar ao agente um PlanState durável e um gate VERIFY (verificadores) — transformar o roteador single-shot num planejador multi-step com auto-verificação, tudo flag-OFF.

**Tech Stack:** Flask, SQLAlchemy JSONB, RQ (verifier adversarial), Claude Agent SDK (Task* tools, output_format), feature flags.

---

## AUDITORIA DE PREMISSAS (2026-05-31 — recon `/tmp/subagent-findings/onda2-recon.md`)
1. **Recursão de subagente (premissa crítica B2)**: subagentes NÃO declaram `Task` em `tools` (`.claude/agents/*.md`) → NÃO spawnam sub-subagentes; SDK 0.2.87 sem proteção explícita (controle por omissão). A "instrução contraditória" em `gestor-estoque-odoo.md` (INV-7) manda usar `Task` sem ela estar nas tools — inexecutável pelo subagente. **DECISÃO: o verifier adversarial (B2) roda como JOB RQ** (padrão `subagent_validator`/`step_judge`), nunca como subagente spawnado pelo loop. Zero risco de recursão.
2. **Task\* cosméticos**: `TaskCreate/Update/List/Get` em `tools_enabled` (`settings.py:66-69`), ZERO invocações reais, nada persiste. B1 os "promove" capturando os `tool_use` events no loop SSE → persiste em `data['plan']`.
3. **`AgentSession.data`**: chaves existentes `messages/total_tokens/sdk_session_id/feedbacks/subagent_validations/deliberation_log/subagent_metadata/s3_archive`. `data['plan']` é novo; usa padrão `flag_modified`.
4. **Verifiers (bases)**: arithmetic = `_self_correct_response` (`client.py:790`, OFF `USE_SELF_CORRECTION`); adversarial = `subagent_validator` (RQ); domain = guards em `app/odoo/estoque/scripts/*.py` (métodos de serviço, não funções puras — CLI via Bash).
5. **`escalated_to_human`**: coluna de `AgentInvocationMetric` (`models.py:1647`), morta, default False. B3 a escreve.
6. **`pending_questions`**: API completa cross-worker (register/submit/wait/cancel) + `AskUserQuestion` SDK → aprovação de plano Web-only (INV-3).
7. **`model_router`** (`model_router.py:104`): roteador DOWNGRADE Opus→Sonnet por regex — inverso do B-TRIAGE (não reusar).
8. Flags `AGENT_PLANNER`, `AGENT_VERIFY` NÃO existem (criar).

## DEPENDÊNCIA CROSS-ONDA (registrada)
- **B-TRIAGE** ("decompõe meta em steps sobre entidades do KG") e **B2-domain** ("valida contra ontologia D") dependem de **D2** (bootstrap ontologia, Onda 3). → **DIFERIDOS** para depois de D2.
- Buildáveis agora (sem D2): **B1**, **B2-arithmetic**, **B2-adversarial**, **B3**.

---

## Task 1 — B1: PlanState durável + flag AGENT_PLANNER/AGENT_VERIFY

**Files:**
- Modify: `app/agente/config/feature_flags.py` (+`AGENT_PLANNER`, +`AGENT_VERIFY`, OFF)
- Create: `app/agente/sdk/plan_state.py` (PlanState schema + helpers de mutação em `data['plan']`)
- Modify: `app/agente/sdk/client.py` — sob `USE_AGENT_PLANNER`, capturar `tool_use` de `TaskCreate/TaskUpdate` no loop de stream e espelhar em `data['plan']` (best-effort, flag_modified).
- Test: `tests/agente/sdk/test_plan_state.py`

- [ ] **Step 1: Flags** — adicionar após as 3 da Onda 1:
```python
# Onda 2 — Planejador + Verify (OFF por default)
USE_AGENT_PLANNER = os.getenv("AGENT_PLANNER", "false").lower() == "true"
USE_AGENT_VERIFY = os.getenv("AGENT_VERIFY", "false").lower() == "true"
```

- [ ] **Step 2: Teste que falha** (`tests/agente/sdk/test_plan_state.py`) — PlanState aplica eventos Task e persiste idempotente:
```python
def test_plan_state_aplica_task_create_e_update():
    from app.agente.sdk.plan_state import PlanState
    ps = PlanState()
    ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'consultar X'})
    ps.apply_task_event({'tool': 'TaskUpdate', 'taskId': '1', 'status': 'completed'})
    d = ps.to_dict()
    assert d['steps']['1']['subject'] == 'consultar X'
    assert d['steps']['1']['status'] == 'completed'

def test_plan_state_roundtrip_dict():
    from app.agente.sdk.plan_state import PlanState
    ps = PlanState(); ps.apply_task_event({'tool':'TaskCreate','taskId':'2','subject':'y'})
    ps2 = PlanState.from_dict(ps.to_dict())
    assert ps2.to_dict() == ps.to_dict()
```

- [ ] **Step 3: Implementar `plan_state.py`** — classe `PlanState` pura (sem DB): `steps: dict[taskId -> {subject, status, ...}]`, `apply_task_event(event)`, `to_dict()`/`from_dict()`. Determinístico, sem efeito colateral.

- [ ] **Step 4: Recon + wiring em client.py** — LER como `ToolUseBlock` é processado no loop de stream (procurar `ToolUseBlock`, `TaskCreate`, `block.name`). Sob `if USE_AGENT_PLANNER:`, quando o tool_use é `TaskCreate/TaskUpdate/TaskGet/TaskList`, alimentar um `PlanState` da sessão e persistir em `session.data['plan'] = ps.to_dict()` + `flag_modified` no ponto de persistência (`_save_messages_to_db`). Best-effort. (Se a captura no stream for inviável sem refactor grande, persistir a partir do snapshot `TaskList` no fim do turno — documente a escolha.)

- [ ] **Step 5: Testes** verdes + `pytest tests/agente/ -q` baseline (só 2 pending_questions).

- [ ] **Step 6: Commit** — `feat(agente-onda2): B1 PlanState durável em data['plan'] (flag AGENT_PLANNER OFF)`

---

## Task 2 — B2 arithmetic + adversarial verifiers (SHADOW, flag AGENT_VERIFY)

**Files:**
- Create: `app/agente/sdk/verifiers.py` (orquestrador de verifiers + arithmetic)
- Modify: `app/agente/workers/` — promover `subagent_validator` a veredito lido pelo loop (adversarial), OU novo `plan_verifier.py` (RQ job)
- Test: `tests/agente/sdk/test_verifiers.py`

- [ ] **Step 1: arithmetic** — promover `_self_correct_response` (`client.py:790`) a um verifier `verify_arithmetic(response_text) -> {ok, issues}` em `verifiers.py`. Reusa a lógica de auto-correção (Sonnet), mas como VEREDITO estruturado (não injeção advisory). Flag `USE_AGENT_VERIFY`.
- [ ] **Step 2: adversarial** — job RQ `verify_plan_adversarial(session_id, step_uid)` (clona `subagent_validator`/`step_judge`): Haiku tenta REFUTAR a conclusão do passo; retorna `{refuted: bool, reason}`. Grava em `agent_step.outcome_signal['verify']` (reusa `update_outcome`). SHADOW (sem gate ativo no loop).
- [ ] **Step 3: Testes** (mock Haiku) + baseline.
- [ ] **Step 4: Commit** — `feat(agente-onda2): B2 verifiers arithmetic+adversarial (shadow, flag AGENT_VERIFY OFF)`

> **B2-domain DIFERIDO** (depende de D2/ontologia). Quando D2 existir: verifier `domain` que valida o passo contra a ontologia + guards (`app/odoo/estoque`). Registrar no EXECUCAO.

---

## Task 3 — B3: replan + escalate (escreve escalated_to_human)

**Files:**
- Modify: `app/agente/sdk/plan_state.py` (replan: marca step falho, gera retry/escalate)
- Modify: ponto de métrica que grava `AgentInvocationMetric.escalated_to_human`
- Test: `tests/agente/sdk/test_replan_escalate.py`

- [ ] **Step 1: Teste** — quando um step falha N vezes (budget), PlanState marca `escalate=True`; e `AgentInvocationMetric.escalated_to_human` é setável.
- [ ] **Step 2: Implementar** replan com budget (max retries por step) + ao estourar, marcar escalate + (sob flag) gravar `escalated_to_human=True` na métrica do turno. Aprovação/escalonamento via `pending_questions`/`AskUserQuestion` (Web-only, INV-3) — apenas o CAMINHO, sem ativar.
- [ ] **Step 3: Testes** + baseline.
- [ ] **Step 4: Commit** — `feat(agente-onda2): B3 replan+escalate escreve escalated_to_human (flag OFF)`

---

## DIFERIDOS (pós-D2)
- **B-TRIAGE** — classificador semântico meta→steps sobre entidades do KG (precisa ontologia D2).
- **B2-domain** — verifier que valida passo contra ontologia + guards.

## Self-Review
- Premissa de recursão auditada → adversarial = RQ job (não subagente). ✓
- Buildável-agora isolado de D2; cross-dep registrada. ✓
- Tudo flag-OFF (`AGENT_PLANNER`/`AGENT_VERIFY`); shadow para verifiers. ✓

## GATE-2 (antes de promover plano na Onda 3)
Super-loop em tarefas reais com VERIFY em shadow; `escalated_to_human` sendo escrito; zero regressão single-shot. Requer deploy + flags shadow.
