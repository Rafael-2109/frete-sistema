# Onda 1 — Fundação Semântica (E↔D) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps usam checkbox.
> **Branch**: `feat/agente-evolucao` (worktree `.claude/worktrees/agente-evolucao`). NÃO push.
> **Spec**: `docs/blueprint-agente/EXECUCAO.md` Onda 1 + `eixos/E-qualidade.md` + `eixos/D-ontologia.md`.

**Goal:** Dar ao agente um sinal de QUALIDADE step-level (não só custo) e higienizar o KG, tudo flag-OFF — fundação para o flywheel (Onda 3).

**Architecture:** Sinais humanos/implícitos (frustração + 👍👎) e um judge batch (ancorado no audit Odoo) gravam em `agent_step.outcome_signal`; KG higienizado (nomes canônicos) e escopo-empresa (`user_id=0`) confirmado.

**Tech Stack:** Flask, SQLAlchemy, RQ (Haiku judge), Postgres JSONB, feature flags.

---

## AUDITORIA DE PREMISSAS (2026-05-31 — recon `/tmp/subagent-findings/onda1-recon.md`)

Premissas do blueprint CORRIGIDAS por recon real (Zero-Assunção):
1. **D0 leak `:E/:A`**: CONFIRMADO em `knowledge_graph_service.py:396-405` — `parse_contextual_response` retém o sufixo no `ename` ("downstream hint" nunca consumido); `_upsert_entity` (:439) NÃO faz strip → grava `"Atacadão:E"`. **Fix confirmado.**
2. **D0 `entity_key=0`**: a hipótese "corrida do merge LLM-keyless" NÃO se confirma. `_upsert_entity` retorna 0 quando `_normalize_name` resulta vazio (guard). A distribuição real de `entity_key`/`'conceito'` catch-all exige análise de DADOS PROD → **DIFERIDO** (não codar resolução canônica sobre premissa não-confirmada).
3. **D0.5 `user_id=0`**: JÁ implementado — leitura `query_graph_memories:797` (`user_ids=[user_id,0]`) + escrita empresa via `memory_mcp_tool`. **Vira verificação + teste**, não nova feature.
4. **E1 `_adjust_importance_for_corrections`**: DELETADO na v2.2 (dead code; `correction_count=0` em 197/197). NÃO ressuscitar a função antiga. E1 = capturar `detect_frustration` score (`sentiment_detector.py:76`, hoje só in-memory `_session_scores`) + 👍👎 (`AgentSession.data['feedbacks']`, hoje não-joinável a turno) → `agent_step.outcome_signal`.
5. **E2/A1 judge**: `subagent_validator.validate_subagent_output` (`workers/subagent_validator.py:114`, RQ fila `agent_validation`, Haiku→JSON→persist→Redis SSE, ATIVO) é o esqueleto a clonar. Âncora ambiental = `operacao_odoo_auditoria` (`session_id`+`tool_use_id`+`agent_type` indexados) MAS `USE_ODOO_AUDIT_HOOK` OFF → judge usa âncora SE disponível; senão degrada p/ sinais `friction_analyzer`.
6. **`AgentStep`**: `insert_step` NÃO grava `outcome_*`. Precisa de método novo `update_outcome(step_uid, ...)` (UPDATE best-effort, SAVEPOINT).

---

## File Structure
- `app/agente/config/feature_flags.py` — +3 flags OFF (`AGENT_QUALITY_SPINE`, `AGENT_STEP_JUDGE`, `AGENT_ONTOLOGY`).
- `app/agente/services/knowledge_graph_service.py` — D0: strip `:E/:A`; D0.5: teste.
- `app/agente/models.py` — `AgentStep.update_outcome()`.
- `app/agente/sdk/memory_injection.py` ou callsites — E1: captura frustração no turno.
- `app/agente/routes/feedback.py` — E1: linkar 👍👎 ao `step_uid` + update outcome.
- `app/agente/workers/step_judge.py` (NOVO) — E2/A1: judge batch clonando `subagent_validator`.
- Testes: `tests/agente/services/`, `tests/agente/models/`, `tests/agente/workers/`.

---

## Task 1 — D0: higiene KG (strip do sufixo :E/:A) + 3 flags Onda 1

**Files:**
- Modify: `app/agente/config/feature_flags.py` (final do arquivo, após `USE_CAPABILITY_REGISTRY`)
- Modify: `app/agente/services/knowledge_graph_service.py` (`parse_contextual_response` ~:396-405 e/ou `_upsert_entity` ~:439-455)
- Test: `tests/agente/services/test_kg_entity_name_hygiene.py`

- [ ] **Step 1: Flags** — adicionar ao fim de `feature_flags.py`:
```python
# ====================================================================
# Onda 1 — Quality Spine + Ontologia (todas OFF por default; ativam em deploy)
# ====================================================================
USE_AGENT_QUALITY_SPINE = os.getenv("AGENT_QUALITY_SPINE", "false").lower() == "true"
USE_AGENT_STEP_JUDGE = os.getenv("AGENT_STEP_JUDGE", "false").lower() == "true"
USE_AGENT_ONTOLOGY = os.getenv("AGENT_ONTOLOGY", "false").lower() == "true"
```

- [ ] **Step 2: Teste que falha** (`tests/agente/services/test_kg_entity_name_hygiene.py`):
```python
"""Onda 1 / D0 — nome de entidade nao deve reter sufixo :E/:A do parsing."""
from app.agente.services.knowledge_graph_service import parse_contextual_response


def test_parse_remove_sufixo_essencial_acidental_do_nome():
    texto = "RESPOSTA: ok\nENTIDADES: cliente:Atacadão:E|produto:Palmito:A"
    _resp, entidades, _rel = parse_contextual_response(texto)
    nomes = {e[1] for e in entidades}
    assert "Atacadão" in nomes, f"esperado nome limpo, veio {nomes}"
    assert "Palmito" in nomes
    assert not any(n.endswith(':E') or n.endswith(':A') for n in nomes), \
        f"sufixo vazou para o nome: {nomes}"


def test_parse_preserva_dois_pontos_legitimo_no_nome():
    # ':' que NAO e' flag E/A deve permanecer (ex.: prioridade:alta)
    texto = "RESPOSTA: ok\nENTIDADES: atributo:prioridade:alta"
    _resp, entidades, _rel = parse_contextual_response(texto)
    nomes = {e[1] for e in entidades}
    assert "prioridade:alta" in nomes
```

- [ ] **Step 3: Rodar e ver falhar** — `python -m pytest tests/agente/services/test_kg_entity_name_hygiene.py -q` → 1º teste FALHA (`Atacadão:E`).

- [ ] **Step 4: Implementar** — em `parse_contextual_response`, quando `maybe_flag` é `E`/`A`, usar o nome LIMPO (`name_part.strip()`) como `ename` (NÃO concatenar o sufixo). Opcionalmente capturar o flag num 3º elemento, mas como nenhum consumer o usa (dead hint, ver auditoria), basta limpar. Garantir que `:` legítimo (não-E/A) permanece.

- [ ] **Step 5: Rodar** — testes verdes + `python -m pytest tests/agente/ -q` (baseline 349 passed / 2 pre-existentes).

- [ ] **Step 6: Commit** — `feat(agente-onda1): D0 higiene KG (strip sufixo :E/:A) + flags Onda 1 OFF`

---

## Task 2 — D0.5: confirmar escopo-empresa (user_id=0) com teste de regressão

**Files:**
- Test: `tests/agente/services/test_kg_empresa_scope.py`
- (sem mudança de código — D0.5 já está implementado; este task BLINDA com teste)

- [ ] **Step 1: Teste** que prova que `query_graph_memories` busca entidades de `user_id` E `user_id=0` (empresa):
```python
"""Onda 1 / D0.5 — escopo empresa (user_id=0) ja' implementado; blindar com teste."""
import inspect
from app.agente.services import knowledge_graph_service as kg


def test_query_inclui_user_id_zero_empresa():
    src = inspect.getsource(kg.query_graph_memories)
    # Invariante D0.5: a query une o user e o escopo-empresa (0).
    assert "user_id, 0" in src or "[user_id, 0]" in src, \
        "query_graph_memories deve unir user_id com escopo empresa (0)"
```

- [ ] **Step 2: Rodar** — verde imediato (documenta a invariante D0.5). `python -m pytest tests/agente/services/test_kg_empresa_scope.py -q`.

- [ ] **Step 3: Commit** — `test(agente-onda1): D0.5 blinda escopo-empresa user_id=0 (ja implementado)`

> NOTA: bootstrap de ontologia das tabelas-mestre (D2, Onda 3) é que CRIA nós empresa em massa — aí o `user_id=0` "morde". Aqui só confirmamos o caminho de leitura/escrita já existente.

---

## Task 3 — E1: capturar sinais (frustração + 👍👎) em `agent_step.outcome_signal`

**Files:**
- Modify: `app/agente/models.py` — `AgentStep.update_outcome()` (novo classmethod)
- Modify: `app/agente/routes/chat.py` — incluir `frustration_score` no insert (web) sob flag
- Modify: `app/teams/services.py` — idem (teams) sob flag
- Modify: `app/agente/routes/feedback.py` — linkar 👍👎 ao `step_uid` + `update_outcome`
- Test: `tests/agente/models/test_agent_step_outcome.py`, `tests/agente/routes/test_feedback_step_link.py`

- [ ] **Step 1: Teste que falha (model)** — `AgentStep.update_outcome(step_uid, signal_patch)` faz merge no JSON `outcome_signal` (best-effort, idempotente, SAVEPOINT):
```python
def test_update_outcome_merge_jsonb(app_ctx):
    from app.agente.models import AgentStep
    import uuid
    sid = f'sig-{uuid.uuid4().hex}'; uid = f'{sid}:1'
    AgentStep.insert_step(step_uid=uid, session_id=sid, user_id=1, channel='web', model='m')
    AgentStep.update_outcome(uid, {'frustration_score': 4})
    AgentStep.update_outcome(uid, {'feedback': 'thumbs_down'})
    step = AgentStep.query.filter_by(step_uid=uid).first()
    assert step.outcome_signal.get('frustration_score') == 4
    assert step.outcome_signal.get('feedback') == 'thumbs_down'
    db.session.rollback()


def test_update_outcome_step_inexistente_nao_quebra(app_ctx):
    from app.agente.models import AgentStep
    AgentStep.update_outcome('nao:existe', {'x': 1})  # sem excecao
```

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar `update_outcome`** em `models.py` (espelha SAVEPOINT de `insert_step`):
```python
    @classmethod
    def update_outcome(cls, step_uid: str, signal_patch: dict,
                       effective_count: Optional[int] = None) -> Optional['AgentStep']:
        """Onda 1 — merge best-effort de sinais em outcome_signal (JSONB).

        Idempotente/seguro: step inexistente -> no-op. SAVEPOINT isola falha.
        flag_modified obrigatorio (mutacao in-place de JSON nao e' detectada).
        """
        try:
            with db.session.begin_nested():
                step = cls.query.filter_by(step_uid=step_uid).first()
                if step is None:
                    return None
                from sqlalchemy.orm.attributes import flag_modified
                merged = dict(step.outcome_signal or {})
                merged.update(signal_patch or {})
                step.outcome_signal = merged
                flag_modified(step, 'outcome_signal')
                if effective_count is not None:
                    step.outcome_effective_count = effective_count
                db.session.flush()
            return step
        except Exception:
            return None
```

- [ ] **Step 4: Wiring frustração (web)** — em `chat.py::_save_messages_to_db`, sob `if feature_flags.USE_AGENT_QUALITY_SPINE:`, ler o score de frustração do turno via `sentiment_detector` (cache `_session_scores` da sessão — expor helper `get_last_score(session_id)` se necessário) e incluir em `outcome_signal` na gravação do step (via `update_outcome` logo após `insert_step`, ou passar no insert). Best-effort.

- [ ] **Step 5: Wiring frustração (teams)** — idem em `_gravar_agent_step_teams` sob a mesma flag.

- [ ] **Step 6: Wiring 👍👎 (feedback.py)** — quando o front envia feedback, aceitar `step_uid` (ou `turn_seq`) no payload; sob flag, `AgentStep.update_outcome(step_uid, {'feedback': type, 'error_category': ...})`. Manter o append legado em `data['feedbacks']` (retrocompat). Documentar que o front precisa enviar `step_uid` (degrada gracioso se ausente).

- [ ] **Step 7: Testes** — model + feedback-link (mock request) verdes; `tests/agente/ -q` baseline.

- [ ] **Step 8: Commit** — `feat(agente-onda1): E1 captura frustracao+feedback em agent_step.outcome_signal (flag OFF)`

---

## Task 4 — E2/A1: judge batch por passo (`step_judge`) ancorado no audit Odoo

**Files:**
- Create: `app/agente/workers/step_judge.py` (clona padrão de `subagent_validator.py`)
- Modify: `app/agente/config/feature_flags.py` (flag `AGENT_STEP_JUDGE` já criada no Task 1)
- Test: `tests/agente/workers/test_step_judge.py`

- [ ] **Step 1: Ler** `app/agente/workers/subagent_validator.py` inteiro (esqueleto: `_call_haiku`, `_parse_haiku_json`, persist, Redis SSE) + a query de `operacao_odoo_auditoria` por `session_id`.

- [ ] **Step 2: Teste que falha** — `judge_step(step_uid)` (job RQ) produz veredito `{score, label, componente_culpado, evidencia}` e grava em `agent_step.outcome_signal` via `update_outcome`. Mockar Haiku + a query de auditoria:
```python
def test_judge_step_grava_veredito(app_ctx, monkeypatch):
    from app.agente.models import AgentStep
    import uuid
    from app.agente.workers import step_judge
    sid = f'judge-{uuid.uuid4().hex}'; uid = f'{sid}:1'
    AgentStep.insert_step(step_uid=uid, session_id=sid, user_id=1, channel='web',
                          model='m', tools_used=['consultando-sql'])
    monkeypatch.setattr(step_judge, '_call_haiku_judge',
                        lambda *a, **k: {'score': 85, 'label': 'ok',
                                         'componente_culpado': None, 'evidencia': '...'})
    step_judge.judge_step(uid)
    step = AgentStep.query.filter_by(step_uid=uid).first()
    assert step.outcome_signal.get('judge', {}).get('score') == 85
    db.session.rollback()
```

- [ ] **Step 3: Implementar `step_judge.py`** — função `judge_step(step_uid)`:
  1. carrega o `AgentStep` + (best-effort) o trecho de transcript da sessão + as linhas de `operacao_odoo_auditoria` por `session_id` (âncora ambiental; se `USE_ODOO_AUDIT_HOOK` OFF → lista vazia → judge usa só sinais textuais).
  2. monta prompt de Process Reward Model (componente ambiental DOMINA: se houve `FALHA_ODOO`, score baixo independente do texto).
  3. `_call_haiku_judge(...)` → JSON `{score, label, componente_culpado, evidencia}`.
  4. `AgentStep.update_outcome(step_uid, {'judge': veredito})`.
  - Guard: TODA a função sob `if not feature_flags.USE_AGENT_STEP_JUDGE: return` no enqueuer (o job só roda em shadow quando ligado). Best-effort.

- [ ] **Step 4: Enqueuer em SHADOW** — NÃO disparar no path SSE. Documentar que o enqueue (futuro) virá de um varredor RQ batch (Onda 3 A3) ou do `_stop_hook` em modo shadow. Nesta task, só a FUNÇÃO + teste; sem wiring ativo (flag OFF + sem enqueue automático).

- [ ] **Step 5: Testes** — `tests/agente/workers/test_step_judge.py` verde; `tests/agente/ -q` baseline.

- [ ] **Step 6: Commit** — `feat(agente-onda1): E2/A1 step_judge (Process Reward Model, shadow, flag OFF)`

---

## Self-Review
1. **Cobertura Onda 1**: D0 (Task 1) · D0.5 (Task 2) · E1 (Task 3) · E2/A1 (Task 4). ✓
2. **Premissas auditadas** (não-assumidas): escopos corrigidos vs blueprint na seção AUDITORIA. ✓
3. **Flag OFF**: tudo novo atrás de `AGENT_QUALITY_SPINE`/`AGENT_STEP_JUDGE`/`AGENT_ONTOLOGY` (D0 leak-fix é bug-fix sem flag — não muda comportamento, só limpa dado novo). ✓
4. **Sem PROD-dependência codada**: judge degrada sem audit hook; bootstrap massivo de nós (D2) fica na Onda 3. ✓

## GATE-1 (antes da Onda 3)
Sinal step-level gravado e auditável ≥1 semana em PROD; judge calibrado (concordância com spot-check humano em held-out); E↔D validado. Requer deploy + flags ON em shadow.
