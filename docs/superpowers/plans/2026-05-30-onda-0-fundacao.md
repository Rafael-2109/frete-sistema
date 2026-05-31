# Onda 0 — Fundação Física (entidade de passo + registry descritivo) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development para implementar task-by-task (1 subagente fresco/tarefa + review entre tarefas). Steps usam checkbox `- [ ]`.

**Goal:** Criar a fundação física que destrava os eixos A/E/B — uma entidade de passo/turno (`agent_step`) joinável e gravada no PRIMARY (R10), + consolidar a deny-list de skills numa fonte única, + um Capability Registry descritivo (read-only).

**Architecture:** `agent_step` é uma tabela aditiva (sem FK, igual a `AgentSessionCost` — preserva histórico pós-cascade), escrita DENTRO de `_save_messages_to_db` (`routes/chat.py:1695`, o PRIMARY protegido pelo lock `_persisted`) via `AgentStep.insert_step()` espelhando o SAVEPOINT pattern de `AgentSessionCost.insert_entry` (`models.py:1439-1490`). O registry (S0c) parseia o que já existe (16 frontmatters + 5 tabelas-catálogo do estoque) e não muda comportamento (flag OFF).

**Tech Stack:** Flask-SQLAlchemy 2.0, Postgres 18, pytest (rodar da worktree `feat/agente-evolucao`, venv do projeto), migration dupla DDL `.sql` idempotente + Python `create_app()`.

**Invariantes a preservar (EXECUCAO.md §regressão):** INV-1 (escrita no PRIMARY, NUNCA `_stop_hook`), INV-2 (chave por nosso UUID + `message_id`, nunca SDK session_id), INV-6 (best-effort: falha de `agent_step` NÃO quebra o stream — try/except + savepoint).

---

## DECISÃO DE DESIGN BLOQUEANTE (resolver com Rafael ANTES da Task 1)

> A fundação inteira depende desta chave. Errar custa caro (re-migration). **Ponto de review obrigatório.**

**Questão:** qual a granularidade e a chave UNIQUE de `agent_step`?

`_save_messages_to_db` NÃO recebe um `message_id` do SDK — recebe `our_session_id`, `user_message`, `assistant_message`, tokens, model, cost. O `AgentSessionCost.message_id` (UNIQUE, candidato do blueprint) é **por-mensagem-SDK** e pode haver N por turno; ele é gravado em outro caminho (`cost_tracker`).

**Recomendação (a confirmar):** `agent_step` = granularidade **TURNO** (1 par user→assistant). Chave UNIQUE = coluna `step_uid TEXT` = `f"{our_session_id}:{turn_seq}"`, onde `turn_seq` = nº de mensagens `role='user'` na sessão APÓS adicionar a atual (derivável de `AgentSession.data['messages']`). Estável e idempotente: o retry da DEFESA (R10) recomputa o mesmo `step_uid` → `insert_step` retorna `None` (UNIQUE), sem duplicar. Join com `agent_session_costs`: por `session_id` + janela `recorded_at` do turno (agregação), NÃO por igualdade de `message_id` (granularidades diferentes — documentar isto).

**Alternativa:** granularidade message-SDK reusando `message_id` direto — rejeitada porque o sinal de qualidade (Onda 1) e o plano (Onda 2) raciocinam por TURNO, não por mensagem-SDK.

→ **Se Rafael aprovar a recomendação, seguir. Se não, ajustar o schema da Task 1 antes de codar.**

---

## File Structure

- Create: `scripts/migrations/2026_05_30_agent_step.sql` — DDL idempotente (`CREATE TABLE IF NOT EXISTS` + índices).
- Create: `scripts/migrations/2026_05_30_agent_step.py` — migration Python (`create_app()` + verificação before/after).
- Modify: `app/agente/models.py` — adicionar `class AgentStep(db.Model)` + `insert_step()` (após `AgentSessionCost`, ~linha 1490).
- Modify: `app/agente/routes/chat.py:1695` (`_save_messages_to_db`) — chamar `AgentStep.insert_step()` após `add_assistant_message`, antes do commit, best-effort.
- Create: `tests/agente/models/test_agent_step.py` — testes do model + insert + idempotência.
- Create: `tests/agente/routes/test_agent_step_wiring.py` — teste de INTEGRAÇÃO (turno real grava 1 linha joinável).
- Modify: `app/agente/config/skills_whitelist.py` — 4º grupo `SKILLS_SPED_RESERVED` (S0b).
- Modify: `app/agente/sdk/client.py:112` — `_discover_skills_from_project` lê a fonte consolidada (S0b).
- Modify: `app/agente/config/settings.py:40` — `SPED_SKILLS_RESERVED` passa a re-exportar de `skills_whitelist` (S0b, retrocompat).
- Create: `app/agente/config/capability_registry.py` — `SkillEntry` + `SkillBinding` + `build_registry()` (S0c, read-only).
- Create: `tests/agente/config/test_capability_registry.py` — registry bate com frontmatters + catálogos.

---

## Task 1 — Model `AgentStep` + migration dupla (S0a parte 1)

**Files:**
- Create: `app/agente/models.py` (classe nova após `AgentSessionCost`, ~1490)
- Create: `scripts/migrations/2026_05_30_agent_step.{sql,py}`
- Test: `tests/agente/models/test_agent_step.py`

- [ ] **Step 1 (DESIGN GATE):** confirmar a decisão de chave acima com Rafael. Só prosseguir após "ok".

- [ ] **Step 2: Escrever o teste que falha** (`tests/agente/models/test_agent_step.py`):

```python
"""Onda 0 / S0a — model AgentStep (entidade de passo/turno)."""
import pytest
from app import create_app, db
from app.agente.models import AgentStep


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


def test_insert_step_basico(app_ctx):
    step = AgentStep.insert_step(
        step_uid='sess-abc:1', session_id='sess-abc', user_id=5,
        channel='web', model='claude-opus-4-8',
        input_tokens=100, output_tokens=50,
    )
    assert step is not None and step.id is not None
    assert step.step_uid == 'sess-abc:1'
    db.session.rollback()


def test_insert_step_idempotente_por_step_uid(app_ctx):
    """Retry da DEFESA (R10) recomputa o mesmo step_uid -> None, sem duplicar."""
    AgentStep.insert_step(step_uid='sess-x:1', session_id='sess-x', user_id=1)
    db.session.flush()
    dup = AgentStep.insert_step(step_uid='sess-x:1', session_id='sess-x', user_id=1)
    assert dup is None  # UNIQUE step_uid bloqueia
    db.session.rollback()


def test_insert_step_falha_nao_poisona_sessao(app_ctx):
    """SAVEPOINT (begin_nested): UNIQUE violation nao aborta a transacao do caller."""
    AgentStep.insert_step(step_uid='sess-y:1', session_id='sess-y', user_id=1)
    AgentStep.insert_step(step_uid='sess-y:1', session_id='sess-y', user_id=1)  # dup -> None
    # sessao continua usavel SEM rollback manual:
    ok = AgentStep.insert_step(step_uid='sess-y:2', session_id='sess-y', user_id=1)
    assert ok is not None
    db.session.rollback()
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `source .venv/bin/activate && python -m pytest tests/agente/models/test_agent_step.py -q`
Expected: FAIL — `ImportError: cannot import name 'AgentStep'`.

- [ ] **Step 4: Implementar o model** (em `models.py`, espelhando `AgentSessionCost` `:1394-1490`):

```python
class AgentStep(db.Model):
    """Onda 0 / S0a — entidade de PASSO/TURNO de 1a classe.

    Fundacao fisica que destrava os eixos A (flywheel), E (qualidade) e
    B (planejador): granularidade de TURNO (1 par user->assistant), joinavel
    com agent_session_costs (por session_id+janela) e agent_sessions.
    Sem FK (preserva historico pos-cascade, igual AgentSessionCost).
    Escrita no PRIMARY (_save_messages_to_db), NUNCA no _stop_hook (INV-1/R10).
    """
    __tablename__ = 'agent_step'
    id = db.Column(db.BigInteger, primary_key=True)
    step_uid = db.Column(db.Text, nullable=False, unique=True)  # f"{session_id}:{turn_seq}"
    session_id = db.Column(db.Text, nullable=True, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    channel = db.Column(db.Text, nullable=True)  # 'web' | 'teams'
    model = db.Column(db.Text, nullable=True)
    input_tokens = db.Column(db.Integer, nullable=False, default=0)
    output_tokens = db.Column(db.Integer, nullable=False, default=0)
    tools_used = db.Column(db.JSON, nullable=True)
    # Colunas de OUTCOME (Onda 1 preenche; criadas agora, NULL ate la):
    outcome_signal = db.Column(db.JSON, nullable=True)        # {human, ambiental, judge}
    outcome_effective_count = db.Column(db.Integer, nullable=True)  # coluna NOVA (nao redefinir effective_count!)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: agora_utc_naive(), index=True)

    @classmethod
    def insert_step(cls, step_uid, session_id=None, user_id=None, channel=None,
                    model=None, input_tokens=0, output_tokens=0, tools_used=None):
        """SAVEPOINT pattern (igual AgentSessionCost.insert_entry:1456). Best-effort:
        IntegrityError (step_uid dup) rollba so o savepoint, preserva a transacao do caller."""
        from sqlalchemy.exc import IntegrityError
        entry = cls(step_uid=step_uid, session_id=session_id, user_id=user_id,
                    channel=channel, model=model, input_tokens=input_tokens,
                    output_tokens=output_tokens, tools_used=tools_used)
        try:
            with db.session.begin_nested():
                db.session.add(entry)
                db.session.flush()
            return entry
        except IntegrityError:
            return None
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/agente/models/test_agent_step.py -q`
Expected: 3 passed (tabela criada por `db.create_all()` no app de teste; em PROD via migration).

- [ ] **Step 6: Migration dupla.** Criar `2026_05_30_agent_step.sql`:

```sql
-- Onda 0 / S0a — entidade de passo/turno
CREATE TABLE IF NOT EXISTS agent_step (
    id BIGSERIAL PRIMARY KEY,
    step_uid TEXT NOT NULL UNIQUE,
    session_id TEXT, user_id INTEGER, channel TEXT, model TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    tools_used JSONB, outcome_signal JSONB, outcome_effective_count INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo')
);
CREATE INDEX IF NOT EXISTS ix_agent_step_session_id ON agent_step (session_id);
CREATE INDEX IF NOT EXISTS ix_agent_step_user_id ON agent_step (user_id);
CREATE INDEX IF NOT EXISTS ix_agent_step_created_at ON agent_step (created_at);
```

E `2026_05_30_agent_step.py` (espelhar `scripts/migrations/2026_05_09_agent_session_costs.py`: `sys.path.insert`, `create_app()`, executar SQL, verificar `to_regclass('agent_step')` before/after). Rodar local: `python scripts/migrations/2026_05_30_agent_step.py`.

- [ ] **Step 7: Commit**

```bash
git add app/agente/models.py tests/agente/models/test_agent_step.py scripts/migrations/2026_05_30_agent_step.*
git commit -m "feat(agente-onda0): model AgentStep + migration (S0a parte 1)"
```

---

## Task 2 — Wiring: gravar `agent_step` no PRIMARY + teste de integração (S0a parte 2)

**Files:**
- Modify: `app/agente/routes/chat.py:1695` (`_save_messages_to_db`)
- Test: `tests/agente/routes/test_agent_step_wiring.py`

- [ ] **Step 1: Teste de INTEGRAÇÃO que falha** (`tests/agente/routes/test_agent_step_wiring.py`) — prova que o sinal ATRAVESSA (DoD wiring): após `_save_messages_to_db` de um turno, existe exatamente 1 `agent_step` joinável por `session_id`.

```python
"""Onda 0 / S0a — wiring: _save_messages_to_db grava 1 agent_step por turno."""
import pytest
from app import create_app, db
from app.agente.models import AgentStep, AgentSession
from app.agente.routes.chat import _save_messages_to_db


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


def test_save_messages_grava_agent_step_joinavel(app_ctx):
    app = app_ctx
    ok = _save_messages_to_db(
        app=app, our_session_id='wire-sess-1', sdk_session_id='sdk-1',
        user_id=7, user_message='tem palmito?', assistant_message='Sim, 120 cx.',
        input_tokens=200, output_tokens=40, tools_used=['consultar-estoque'],
        model='claude-opus-4-8', session_expired=False,
    )
    assert ok is True
    steps = AgentStep.query.filter_by(session_id='wire-sess-1').all()
    assert len(steps) == 1
    assert steps[0].user_id == 7 and steps[0].channel == 'web'
    # joinavel com agent_sessions:
    sess = AgentSession.query.filter_by(session_id='wire-sess-1').first()
    assert sess is not None
    db.session.rollback()


def test_save_messages_idempotente_nao_duplica_step(app_ctx):
    """Defesa R10 chama 2x -> step_uid igual -> 1 linha so."""
    app = app_ctx
    for _ in range(2):
        _save_messages_to_db(app=app, our_session_id='wire-sess-2', sdk_session_id='s',
                             user_id=1, user_message='oi', assistant_message='ola',
                             input_tokens=1, output_tokens=1, tools_used=None,
                             model='m', session_expired=False)
    assert AgentStep.query.filter_by(session_id='wire-sess-2').count() == 1
    db.session.rollback()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/agente/routes/test_agent_step_wiring.py -q`
Expected: FAIL — `len(steps) == 0` (escrita ainda não existe).

- [ ] **Step 3: Implementar o wiring** dentro de `_save_messages_to_db` (`chat.py`), DEPOIS do bloco `add_assistant_message` (~`:1767`) e DENTRO do `with app.app_context()`, ANTES do commit. Best-effort (INV-6) — derivar `turn_seq` de `len([m for m in session.data['messages'] if m['role']=='user'])`:

```python
            # Onda 0 / S0a — entidade de passo (INV-1: PRIMARY, nao _stop_hook).
            # Best-effort: falha NAO quebra a persistencia da resposta (INV-6).
            try:
                from app.agente.models import AgentStep
                _msgs = (session.data or {}).get('messages', [])
                _turn_seq = sum(1 for m in _msgs if m.get('role') == 'user')
                AgentStep.insert_step(
                    step_uid=f"{our_session_id}:{_turn_seq}",
                    session_id=our_session_id, user_id=user_id,
                    channel='web', model=model,
                    input_tokens=input_tokens, output_tokens=output_tokens,
                    tools_used=tools_used or None,
                )
            except Exception as e:
                logger.warning(f"[AGENTE] agent_step nao gravado (best-effort): {e}")
```

> **Wiring contract verificado**: produtor `_save_messages_to_db` (PRIMARY) → `agent_step` → consumidores Onda 1 (E) / Onda 2 (B). `channel='web'` aqui; o caminho Teams (`services.py`) recebe wiring análogo numa sub-tarefa Teams (INV-3 — caminho próprio, não reusar cego).

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/agente/routes/test_agent_step_wiring.py tests/agente/models/test_agent_step.py -q`
Expected: 5 passed.

- [ ] **Step 5: Não-regressão** — rodar a suíte de chat/sessão:

Run: `python -m pytest tests/agente/ -q`
Expected: baseline mantido (nenhum teste novo vermelho).

- [ ] **Step 6: Commit**

```bash
git add app/agente/routes/chat.py tests/agente/routes/test_agent_step_wiring.py
git commit -m "feat(agente-onda0): grava agent_step no PRIMARY (S0a parte 2, wiring + integracao)"
```

> **Sub-tarefa Teams (S0a-teams):** replicar a escrita em `app/teams/services.py` no ponto onde a resposta é persistida (`channel='teams'`), com teste próprio. Tratada como item separado no EXECUCAO.md (INV-3). NÃO fazer inline aqui.

---

## Task 3 — Consolidar deny-list de skills numa fonte única (S0b)

**Files:**
- Modify: `app/agente/config/skills_whitelist.py` (4º grupo)
- Modify: `app/agente/config/settings.py:40` (re-exporta, retrocompat)
- Modify: `app/agente/sdk/client.py:112` (lê fonte consolidada)
- Test: estender `tests/agente/` (teste de discovery)

- [ ] **Step 1: Ler o estado atual** — `settings.py:40` (`SPED_SKILLS_RESERVED` frozenset) e `client.py:83-120` (`_discover_skills_from_project`). Confirmar os nomes exatos das skills SPED no frozenset.

- [ ] **Step 2: Teste que falha** — `SKILLS_DELEGADAS_SUBAGENTE` (já em `skills_whitelist.py`) passa a incluir as SPED, e `_discover_skills_from_project` exclui o conjunto consolidado:

```python
def test_sped_skills_no_conjunto_consolidado():
    from app.agente.config.skills_whitelist import SKILLS_DELEGADAS_SUBAGENTE, SKILLS_SPED_RESERVED
    assert SKILLS_SPED_RESERVED  # nao vazio
    assert SKILLS_SPED_RESERVED <= SKILLS_DELEGADAS_SUBAGENTE  # subconjunto
```

- [ ] **Step 3: Implementar** — adicionar em `skills_whitelist.py` o grupo `SKILLS_SPED_RESERVED` (copiar nomes do frozenset de `settings.py:40`) e somá-lo a `SKILLS_DELEGADAS_SUBAGENTE`. Em `settings.py:40`, trocar o literal por `from app.agente.config.skills_whitelist import SKILLS_SPED_RESERVED as SPED_SKILLS_RESERVED` (retrocompat — `client.py:112` continua funcionando). Verificar que `client.py` agora exclui via fonte única.

- [ ] **Step 4: Rodar testes** — `python -m pytest tests/agente/ -q` (baseline mantido + novo verde).

- [ ] **Step 5: Commit** — `git commit -m "refactor(agente-onda0): fonte unica de deny-list de skills (S0b)"`

---

## Task 4 — Capability Registry descritivo (S0c)

**Files:**
- Create: `app/agente/config/capability_registry.py`
- Modify: `app/agente/config/feature_flags.py` (flag `AGENT_CAPABILITY_REGISTRY=false`)
- Test: `tests/agente/config/test_capability_registry.py`

- [ ] **Step 1: Ler** `agent_loader.py:239-272` (`_parse_skills`) e a estrutura dos frontmatters em `.claude/agents/*.md` + as 5 tabelas-catálogo em `app/odoo/estoque/CLAUDE.md`.

- [ ] **Step 2: Teste que falha** — `build_registry()` retorna `SkillEntry` por skill e `SkillBinding` N:M (skill↔agente). Validar que `consultando-sql` aparece com MÚLTIPLOS bindings (≥2 agentes) — prova que exposure NÃO é escalar:

```python
def test_registry_skill_binding_n_para_m(app_ctx):
    from app.agente.config.capability_registry import build_registry
    reg = build_registry()
    assert reg.skills  # SkillEntry por skill
    binds = [b for b in reg.bindings if b.skill_name == 'consultando-sql']
    assert len(binds) >= 2  # declarada por varios agentes — exposure e' aresta, nao escalar
```

- [ ] **Step 3: Implementar** `capability_registry.py` — dataclasses `SkillEntry` (name, description, intrinsic props) e `SkillBinding` (skill_name, agent_name). `build_registry()` parseia `.claude/agents/*.md` (reusa `_parse_skills`) + skills do principal. READ-ONLY: flag `AGENT_CAPABILITY_REGISTRY` OFF → função existe mas nada no runtime a consome ainda (só testes/auditoria).

- [ ] **Step 4: Rodar** — `python -m pytest tests/agente/config/test_capability_registry.py -q` + `tests/agente/ -q` (baseline).

- [ ] **Step 5: Auditoria read-only** — script ad-hoc que imprime registry vs frontmatters, conferir manualmente que bate (DoD: registry reflete a realidade).

- [ ] **Step 6: Commit** — `git commit -m "feat(agente-onda0): Capability Registry descritivo read-only (S0c)"`

---

## Self-Review (executar após escrever, antes de implementar)

1. **Cobertura da Onda 0 (EXECUCAO.md):** S0a (Tasks 1+2) ✓ · S0b (Task 3) ✓ · S0c (Task 4) ✓. Sub-tarefa Teams de S0a sinalizada como item separado (INV-3) ✓.
2. **Placeholders:** os testes têm código real; a implementação do model tem código real; o wiring tem o trecho exato + ponto (`chat.py:1767`). S0b/S0c referenciam o padrão a copiar (`_parse_skills`, frozenset) — engenheiro lê o arquivo citado. Sem "TODO/implementar depois".
3. **Consistência de tipos:** `step_uid` (TEXT UNIQUE), `insert_step()` assinatura igual entre model (Task 1) e wiring (Task 2). `outcome_effective_count` é coluna NOVA (nunca redefine `effective_count` — risco transversal do EXECUCAO.md).
4. **DoD por tarefa:** cada uma tem teste TDD + (Task 2) teste de integração de wiring + não-regressão + migration dupla (Task 1) + flag OFF (Task 4) + commit. Falta só code-review (subagent-driven faz entre tarefas) e o GATE-0 (validação PROD pós-deploy).

## GATE-0 (antes de iniciar a Onda 1)
`agent_step` gravando 1 linha/turno em PROD por ≥48h (web E teams), joinável com `agent_session_costs`+`agent_sessions`, zero impacto em latência/erro (Sentry limpo); registry descritivo audita-bate com frontmatters. Marcar no `EXECUCAO.md`.

## Execution Handoff
Plano salvo. Cadência escolhida: **subagent-driven**. Próximo: resolver o DESIGN GATE (chave/granularidade) com Rafael → depois disparar Task 1 num subagente fresco, review, Task 2, etc.
