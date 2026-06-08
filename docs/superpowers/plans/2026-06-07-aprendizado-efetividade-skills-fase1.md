<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano executavel da Fase 1 (avaliador de efetividade de skill + inbox de aprovacao)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-07
-->

# Aprendizado por Efetividade de Skill — Fase 1 — Implementation Plan

> **Papel:** plano executavel task-by-task da Fase 1 da spec
> `docs/superpowers/specs/2026-06-07-aprendizado-efetividade-skills-design.md` (ler a
> spec antes). Cobre o avaliador de efetividade de skill (pos-sessao, funil
> estagio0->Haiku->Sonnet), a aplicacao dos 3 ramos, a injecao cirurgica do lembrete e a
> Inbox de Aprovacao unificada (que conserta o `directive_promotion` shadow sem UI).
> Scripts ad-hoc = Fase 2 (spec/plano proprios).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans para implementar task-by-task. Steps usam
> checkbox (`- [ ]`). Toda a Fase 1 vive na worktree
> `.claude/worktrees/agente-skill-efetividade` (branch `feat/agente-skill-efetividade`).

**Goal:** Avaliar, no fim de cada sessao, se as skills invocadas resolveram o problema; quando nao, criar lembrete por-usuario (auto), ou propor lembrete-p/-todos / ajuste de codigo (via Inbox de aprovacao) — sem prescrever solucao de codigo (separacao de competencias).

**Architecture:** Gatilho em `run_post_session_processing` enfileira job RQ na fila `agent_background`; o job monta a janela ancorada na invocacao da skill, passa por funil de 3 estagios (custo-zero -> Haiku -> Sonnet), aplica o ramo decidido e grava 1 linha idempotente em `agent_skill_effectiveness`. O lembrete por-usuario e entregue por injecao cirurgica no PreToolUse quando a skill e invocada. A Inbox de Aprovacao (aba em `/agente/memorias`) lista AgentMemory shadow + ImprovementDialogue proposed e tem botoes Aprovar/Rejeitar.

**Tech Stack:** Python 3.12, Flask 3.1, SQLAlchemy 2.0, RQ 2.6 (fila `agent_background`), anthropic SDK 0.98 (Haiku `claude-haiku-4-5-20251001` / Sonnet `claude-sonnet-4-6`), pytest, Jinja2 + Bootstrap 5.3.

---

## Indice

- [Setup e convencoes](#setup-e-convencoes)
- [Estrutura de arquivos](#estrutura-de-arquivos)
- [Task 1: Feature flags](#task-1-feature-flags)
- [Task 2: Modelo AgentSkillEffectiveness + migration](#task-2-modelo-agentskilleffectiveness-migration)
- [Task 3: Montagem da janela ancorada](#task-3-montagem-da-janela-ancorada)
- [Task 4: Estagio 0 — sinal custo-zero](#task-4-estagio-0-sinal-custo-zero)
- [Task 5: Estagios 1 e 2 — Haiku e Sonnet](#task-5-estagios-1-e-2-haiku-e-sonnet)
- [Task 6: Aplicacao dos ramos](#task-6-aplicacao-dos-ramos)
- [Task 7: evaluate_session — orquestracao + idempotencia](#task-7-evaluate_session-orquestracao-idempotencia)
- [Task 8: try_enqueue + job RQ](#task-8-try_enqueue-job-rq)
- [Task 9: Gatilho em run_post_session_processing](#task-9-gatilho-em-run_post_session_processing)
- [Task 10: Injecao cirurgica do lembrete](#task-10-injecao-cirurgica-do-lembrete)
- [Task 11: Inbox — service](#task-11-inbox-service)
- [Task 12: Inbox — rotas](#task-12-inbox-rotas)
- [Task 13: Inbox — UI (aba memorias.html)](#task-13-inbox-ui-aba-memoriashtml)
- [Task 14: Ajuste do improvement_suggester (D8)](#task-14-ajuste-do-improvement_suggester-d8)
- [Task 15: Smoke + ativacao de flags](#task-15-smoke-ativacao-de-flags)
- [Self-review](#self-review)
- [Execution handoff](#execution-handoff)

---

## Setup e convencoes

- **Ambiente de testes (worktree):** sem `.env`, o `create_app()` cai em SQLite e
  regenera schemas (ruido). Rodar pytest da RAIZ do repo com `DATABASE_URL` apontando
  para o banco local, OU usar o conftest do projeto. Comando base:
  `source .venv/bin/activate && python -m pytest <arquivo> -v`. Se cair em SQLite,
  exportar `DATABASE_URL` da raiz antes.
- **Best-effort (R1 services):** TODO codigo novo de service/worker roda em background
  ou no stream — `try/except Exception: logger.warning(...)`, NUNCA re-raise.
- **Flag-gated (R2 services):** todo caminho novo verifica a flag ANTES de qualquer
  custo (LLM, query pesada).
- **Commits frequentes:** 1 commit por task concluida (test+impl juntos), prefixo
  `feat(agente-skill-eval):`.
- **NAO commitar na main:** trabalhar so na worktree. O 1o commit inclui a spec
  (`docs/superpowers/specs/2026-06-07-aprendizado-efetividade-skills-design.md`) +
  a entrada no `specs/INDEX.md` (ja presentes no working tree da worktree).
- **Logging:** prefixo `[SKILL_EVAL]` (alinhado ao padrao de prefixo unico por service).

## Estrutura de arquivos

| Arquivo | Responsabilidade | Acao |
|---|---|---|
| `app/agente/config/feature_flags.py` | flags da feature | Modificar |
| `app/agente/models.py` | `AgentSkillEffectiveness` | Modificar (append modelo) |
| `scripts/migrations/2026_06_07_agent_skill_effectiveness.py` | migration Python | Criar |
| `scripts/migrations/2026_06_07_agent_skill_effectiveness.sql` | migration SQL idempotente | Criar |
| `app/agente/services/skill_effectiveness_service.py` | janela + 3 estagios + aplicacao + orquestracao | Criar |
| `app/agente/workers/background_jobs.py` | `try_enqueue_skill_effectiveness` + `skill_effectiveness_job` | Modificar |
| `app/agente/routes/_helpers.py` | gatilho em `run_post_session_processing` | Modificar |
| `app/agente/sdk/memory_injection.py` | `get_skill_reminders_for_session` (cache) | Modificar |
| `app/agente/sdk/hooks.py` | injecao cirurgica no `_keep_stream_open` | Modificar |
| `app/agente/services/approval_inbox_service.py` | listar/aprovar/rejeitar pendentes | Criar |
| `app/agente/routes/memories.py` | rotas da inbox (GET/PUT) | Modificar |
| `app/agente/templates/agente/memorias.html` | aba "Pendentes de Aprovacao" | Modificar |
| `app/agente/services/improvement_suggester.py` | ajuste system prompt (separacao competencias) | Modificar |
| `tests/agente/test_skill_effectiveness.py` | testes do service/janela/estagios/aplicacao | Criar |
| `tests/agente/test_skill_eval_worker.py` | testes do enqueue/job/gatilho | Criar |
| `tests/agente/test_approval_inbox.py` | testes da inbox (service + rotas) | Criar |

> Nota de nomenclatura: a spec citou `directive_approval_service.py`; o plano usa
> `approval_inbox_service.py` (mais fiel: a inbox cobre 3 fontes, nao so diretrizes).

---

## Task 1: Feature flags

**Files:**
- Modify: `app/agente/config/feature_flags.py`
- Test: `tests/agente/test_skill_effectiveness.py`

- [ ] **Step 1: Escrever o teste das flags**

```python
# tests/agente/test_skill_effectiveness.py
import importlib
import os


def _reload_flags():
    import app.agente.config.feature_flags as ff
    return importlib.reload(ff)


def test_skill_eval_flags_default_off(monkeypatch):
    for var in ["AGENT_SKILL_EVAL", "AGENT_SKILL_EVAL_SONNET",
                "AGENT_SKILL_EVAL_APPLY_USER"]:
        monkeypatch.delenv(var, raising=False)
    ff = _reload_flags()
    assert ff.AGENT_SKILL_EVAL is False
    # apply_user e sonnet default ON (so atuam quando AGENT_SKILL_EVAL liga o pipeline)
    assert ff.AGENT_SKILL_EVAL_APPLY_USER is True
    assert ff.AGENT_SKILL_EVAL_SONNET is True


def test_skill_eval_flag_on(monkeypatch):
    monkeypatch.setenv("AGENT_SKILL_EVAL", "true")
    ff = _reload_flags()
    assert ff.AGENT_SKILL_EVAL is True
```

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py -k flags -v`
Expected: FAIL (`AttributeError: module ... has no attribute 'AGENT_SKILL_EVAL'`).

- [ ] **Step 3: Adicionar as flags (seguindo o padrao do arquivo, ex. linha 19)**

```python
# app/agente/config/feature_flags.py  (append na secao de flags do agente)

# --- Aprendizado por efetividade de skill (Fase 1) ---
# Liga o gatilho + job de avaliacao pos-sessao. Default OFF (1 ciclo de smoke antes).
AGENT_SKILL_EVAL = os.getenv("AGENT_SKILL_EVAL", "false").lower() == "true"
# Permite escalonar ao Sonnet (estagio 2). Se OFF, para no Haiku (modo observacao).
AGENT_SKILL_EVAL_SONNET = os.getenv("AGENT_SKILL_EVAL_SONNET", "true").lower() == "true"
# Ramo lembrete_usuario aplica auto. Se OFF, vira shadow (vai p/ inbox tambem).
AGENT_SKILL_EVAL_APPLY_USER = os.getenv("AGENT_SKILL_EVAL_APPLY_USER", "true").lower() == "true"
# Limiar de confidence (0-1) do Sonnet p/ auto-aplicar lembrete_usuario.
AGENT_SKILL_EVAL_CONF_MIN = float(os.getenv("AGENT_SKILL_EVAL_CONF_MIN", "0.7"))
# Cap de escalonamentos a Sonnet por sessao (anti-explosao de custo).
AGENT_SKILL_EVAL_MAX_SONNET = int(os.getenv("AGENT_SKILL_EVAL_MAX_SONNET", "3"))
```

- [ ] **Step 4: Rodar o teste e ver passar**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py -k flags -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add app/agente/config/feature_flags.py tests/agente/test_skill_effectiveness.py \
        docs/superpowers/specs/2026-06-07-aprendizado-efetividade-skills-design.md \
        docs/superpowers/specs/INDEX.md \
        docs/superpowers/plans/2026-06-07-aprendizado-efetividade-skills-fase1.md
git commit -m "feat(agente-skill-eval): flags da Fase 1 + spec/plano"
```

---

## Task 2: Modelo AgentSkillEffectiveness + migration

**Files:**
- Modify: `app/agente/models.py` (append do modelo; usar `agora_utc_naive` ja importado)
- Create: `scripts/migrations/2026_06_07_agent_skill_effectiveness.py`
- Create: `scripts/migrations/2026_06_07_agent_skill_effectiveness.sql`
- Test: `tests/agente/test_skill_effectiveness.py`

- [ ] **Step 1: Escrever o teste do modelo (criacao + constraint unica)**

```python
# tests/agente/test_skill_effectiveness.py  (append)
import pytest
from sqlalchemy.exc import IntegrityError


def test_skill_effectiveness_unique_anchor(db):
    """Mesma (session_id, anchor_msg_id) nao pode duplicar."""
    from app.agente.models import AgentSkillEffectiveness

    r1 = AgentSkillEffectiveness(
        user_id=1, session_id="sess-A", skill_name="cotando-frete",
        anchor_msg_id="msg-1", stage_reached=0, resolveu=True,
    )
    db.session.add(r1)
    db.session.flush()  # dispara a constraint sem fechar o savepoint da fixture

    r2 = AgentSkillEffectiveness(
        user_id=1, session_id="sess-A", skill_name="cotando-frete",
        anchor_msg_id="msg-1", stage_reached=0, resolveu=True,
    )
    db.session.add(r2)
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()
```

> NOTA: usa a fixture `db` do `tests/conftest.py:50` (savepoint `begin_nested` + rollback
> ao fim). `flush()` (nao `commit()`) dispara a constraint sem fechar o savepoint.
> `user_id=1` = Rafael (existe no banco local — FK satisfeita). Rodar com `DATABASE_URL`
> do PostgreSQL local (da raiz); sem ele cai em SQLite (FK fraca) — ver Setup.

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py -k unique_anchor -v`
Expected: FAIL (`ImportError: cannot import name 'AgentSkillEffectiveness'`).

- [ ] **Step 3: Adicionar o modelo (append em models.py, perto dos demais Agent*)**

```python
# app/agente/models.py  (append; agora_utc_naive ja esta importado no topo)
class AgentSkillEffectiveness(db.Model):
    """Avaliacao de efetividade de UMA invocacao de skill (1 linha por ancora)."""
    __tablename__ = 'agent_skill_effectiveness'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    skill_name = db.Column(db.String(80), nullable=False, index=True)
    anchor_msg_id = db.Column(db.String(64), nullable=False)
    stage_reached = db.Column(db.SmallInteger, default=0)   # 0/1/2
    resolveu = db.Column(db.Boolean, nullable=True)
    ramo = db.Column(db.String(20), nullable=True)          # lembrete_usuario|lembrete_todos|ajuste_codigo|nada
    confidence = db.Column(db.Float, nullable=True)
    action_ref = db.Column(db.String(120), nullable=True)   # memory:<id> | dialogue:<id> | approval:<id>
    error_signature = db.Column(db.String(64), nullable=True)
    evidencia_json = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())

    __table_args__ = (
        db.UniqueConstraint('session_id', 'anchor_msg_id', name='uq_skill_eff_session_anchor'),
        db.Index('ix_skill_eff_skill_resolveu', 'skill_name', 'resolveu'),
    )

    def __repr__(self):
        return f'<AgentSkillEffectiveness {self.skill_name} sess={self.session_id[:8]} ramo={self.ramo}>'
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py -k unique_anchor -v`
Expected: PASS.

- [ ] **Step 5: Criar a migration SQL idempotente**

```sql
-- scripts/migrations/2026_06_07_agent_skill_effectiveness.sql
CREATE TABLE IF NOT EXISTS agent_skill_effectiveness (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES usuarios(id),
    session_id      VARCHAR(64) NOT NULL,
    skill_name      VARCHAR(80) NOT NULL,
    anchor_msg_id   VARCHAR(64) NOT NULL,
    stage_reached   SMALLINT DEFAULT 0,
    resolveu        BOOLEAN,
    ramo            VARCHAR(20),
    confidence      DOUBLE PRECISION,
    action_ref      VARCHAR(120),
    error_signature VARCHAR(64),
    evidencia_json  JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_skill_eff_session_anchor
    ON agent_skill_effectiveness (session_id, anchor_msg_id);
CREATE INDEX IF NOT EXISTS ix_agent_skill_effectiveness_user_id
    ON agent_skill_effectiveness (user_id);
CREATE INDEX IF NOT EXISTS ix_agent_skill_effectiveness_session_id
    ON agent_skill_effectiveness (session_id);
CREATE INDEX IF NOT EXISTS ix_skill_eff_skill_resolveu
    ON agent_skill_effectiveness (skill_name, resolveu);
```

- [ ] **Step 6: Criar a migration Python (create_app + verificacao before/after)**

```python
# scripts/migrations/2026_06_07_agent_skill_effectiveness.py
"""Cria a tabela agent_skill_effectiveness (Fase 1 aprendizado por efetividade)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app import create_app, db
from sqlalchemy import text, inspect

SQL = open(os.path.join(os.path.dirname(__file__),
           "2026_06_07_agent_skill_effectiveness.sql")).read()


def main():
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        before = 'agent_skill_effectiveness' in insp.get_table_names()
        print(f"[before] tabela existe? {before}")
        for stmt in [s.strip() for s in SQL.split(';') if s.strip()]:
            db.session.execute(text(stmt))
        db.session.commit()
        insp = inspect(db.engine)
        after = 'agent_skill_effectiveness' in insp.get_table_names()
        print(f"[after] tabela existe? {after}")
        assert after, "tabela nao foi criada"


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Rodar a migration no banco local**

Run: `source .venv/bin/activate && python scripts/migrations/2026_06_07_agent_skill_effectiveness.py`
Expected: `[after] tabela existe? True`.

- [ ] **Step 8: Commit**

```bash
git add app/agente/models.py scripts/migrations/2026_06_07_agent_skill_effectiveness.* \
        tests/agente/test_skill_effectiveness.py
git commit -m "feat(agente-skill-eval): modelo AgentSkillEffectiveness + migration"
```

---

## Task 3: Montagem da janela ancorada

**Files:**
- Create: `app/agente/services/skill_effectiveness_service.py`
- Test: `tests/agente/test_skill_effectiveness.py`

Contexto verificado: cada msg em `AgentSession.data['messages']` tem `role`,
`content`, `timestamp`, `tools_used` (lista). A skill invocada vem como `"Skill:<nome>"`
em `tools_used` (FONTE: `app/agente/routes/chat.py:866`). Cada msg tem `id` (`msg_...`,
FONTE: `app/agente/models.py:178-248`).

- [ ] **Step 1: Escrever o teste da montagem da janela**

```python
# tests/agente/test_skill_effectiveness.py  (append)
def test_build_skill_windows_anchors_and_window():
    from app.agente.services.skill_effectiveness_service import build_skill_windows
    msgs = [
        {"id": "u0", "role": "user", "content": "qual frete pra SP?"},
        {"id": "a0", "role": "assistant", "content": "vou cotar", "tools_used": ["Skill:cotando-frete"]},
        {"id": "u1", "role": "user", "content": "nao era isso, ta errado"},
        {"id": "a1", "role": "assistant", "content": "desculpe, corrigindo"},
        {"id": "u2", "role": "user", "content": "agora sim"},
        {"id": "a2", "role": "assistant", "content": "otimo"},
    ]
    wins = build_skill_windows(msgs)
    assert len(wins) == 1
    w = wins[0]
    assert w.skill_name == "cotando-frete"
    assert w.anchor_msg_id == "a0"
    assert w.msg_anterior["id"] == "u0"
    assert [m["id"] for m in w.proximas_user] == ["u1", "u2"]
    assert [m["id"] for m in w.proximas_assistant] == ["a1", "a2"]
    assert w.janela_fechada is True


def test_build_skill_windows_open_window():
    from app.agente.services.skill_effectiveness_service import build_skill_windows
    msgs = [
        {"id": "u0", "role": "user", "content": "x"},
        {"id": "a0", "role": "assistant", "content": "y", "tools_used": ["Skill:cotando-frete"]},
        {"id": "u1", "role": "user", "content": "z"},  # so 1 proxima user -> aberta
    ]
    wins = build_skill_windows(msgs)
    assert wins[0].janela_fechada is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py -k build_skill_windows -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementar a montagem**

```python
# app/agente/services/skill_effectiveness_service.py
"""Avaliador de efetividade de skill (Fase 1). Best-effort, flag-gated.

Pipeline: build_skill_windows -> (estagio0 -> estagio1 Haiku -> estagio2 Sonnet)
-> apply_decision -> grava AgentSkillEffectiveness (idempotente).
Ver spec docs/superpowers/specs/2026-06-07-aprendizado-efetividade-skills-design.md
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
_SKILL_PREFIX = "Skill:"


@dataclass
class SkillWindow:
    skill_name: str
    anchor_msg_id: str
    msg_anterior: Optional[Dict[str, Any]]
    resposta_invocacao: Dict[str, Any]
    proximas_user: List[Dict[str, Any]] = field(default_factory=list)
    proximas_assistant: List[Dict[str, Any]] = field(default_factory=list)
    janela_fechada: bool = False


def _skill_from_tools(tools_used: Any) -> Optional[str]:
    if not isinstance(tools_used, list):
        return None
    for t in tools_used:
        if isinstance(t, str) and t.startswith(_SKILL_PREFIX):
            return t[len(_SKILL_PREFIX):].strip() or None
    return None


def build_skill_windows(messages: List[Dict[str, Any]]) -> List[SkillWindow]:
    """Para cada invocacao de skill, monta a janela (msg anterior + 2 prox user + 2 prox assistant)."""
    windows: List[SkillWindow] = []
    for i, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        skill = _skill_from_tools(msg.get("tools_used"))
        if not skill:
            continue
        # msg do usuario imediatamente anterior
        msg_anterior = None
        for j in range(i - 1, -1, -1):
            if messages[j].get("role") == "user":
                msg_anterior = messages[j]
                break
        prox_user, prox_asst = [], []
        for k in range(i + 1, len(messages)):
            role = messages[k].get("role")
            if role == "user" and len(prox_user) < 2:
                prox_user.append(messages[k])
            elif role == "assistant" and len(prox_asst) < 2:
                prox_asst.append(messages[k])
            if len(prox_user) >= 2 and len(prox_asst) >= 2:
                break
        windows.append(SkillWindow(
            skill_name=skill,
            anchor_msg_id=msg.get("id", f"idx-{i}"),
            msg_anterior=msg_anterior,
            resposta_invocacao=msg,
            proximas_user=prox_user,
            proximas_assistant=prox_asst,
            janela_fechada=len(prox_user) >= 2,
        ))
    return windows
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py -k build_skill_windows -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add app/agente/services/skill_effectiveness_service.py tests/agente/test_skill_effectiveness.py
git commit -m "feat(agente-skill-eval): montagem da janela ancorada na skill"
```

---

## Task 4: Estagio 0 — sinal custo-zero

**Files:**
- Modify: `app/agente/services/skill_effectiveness_service.py`
- Test: `tests/agente/test_skill_effectiveness.py`

Contexto verificado: `sentiment_detector.detect_frustration(message, previous_messages=None,
had_error=False, recent_scores=None) -> Tuple[bool, int]` (FONTE:
`app/agente/services/sentiment_detector.py:101`). `FRUSTRATION_MARKERS` e a lista de
regex (mesmo arquivo). Reusamos a deteccao de frustracao + marcadores de pedido de
ajuste + deteccao de Bash nas proximas respostas do agente.

- [ ] **Step 1: Escrever o teste do estagio 0**

```python
# tests/agente/test_skill_effectiveness.py  (append)
from app.agente.services.skill_effectiveness_service import SkillWindow, stage0_has_signal


def _win(prox_user_texts, prox_asst=None):
    return SkillWindow(
        skill_name="cotando-frete", anchor_msg_id="a0",
        msg_anterior={"id": "u0", "role": "user", "content": "frete sp"},
        resposta_invocacao={"id": "a0", "role": "assistant", "content": "cotando"},
        proximas_user=[{"id": f"u{i}", "role": "user", "content": t} for i, t in enumerate(prox_user_texts, 1)],
        proximas_assistant=prox_asst or [],
        janela_fechada=True,
    )


def test_stage0_no_signal():
    assert stage0_has_signal(_win(["perfeito, obrigado", "valeu"])) is False


def test_stage0_signal_frustration():
    assert stage0_has_signal(_win(["nao era isso", "ta errado"])) is True


def test_stage0_signal_adhoc_bash():
    w = _win(["e a outra rota?"],
             prox_asst=[{"id": "a1", "role": "assistant", "content": "rodando",
                         "tools_used": ["Bash"]}])
    assert stage0_has_signal(w) is True
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py -k stage0 -v`
Expected: FAIL (`ImportError: stage0_has_signal`).

- [ ] **Step 3: Implementar o estagio 0**

```python
# app/agente/services/skill_effectiveness_service.py  (append)
import re

# Pedido explicito de ajuste/correcao relacionado a skill
_ADJUST_MARKERS = [
    r"\bajusta\b", r"\bajustar\b", r"\bcorrig", r"\bnao funcion", r"\bnao resolv",
    r"\bde novo\b", r"\bcontinua (errad|sem)\b", r"\bnao era isso\b", r"\btentou de novo\b",
]


def _texts(msgs: List[Dict[str, Any]]) -> str:
    return " \n ".join(str(m.get("content") or "") for m in msgs).lower()


def _has_bash(msgs: List[Dict[str, Any]]) -> bool:
    for m in msgs:
        tu = m.get("tools_used")
        if isinstance(tu, list) and any(t == "Bash" or str(t).startswith("Bash") for t in tu):
            return True
    return False


def stage0_has_signal(window: SkillWindow) -> bool:
    """Custo-zero: ha sinal de que a skill pode nao ter resolvido?

    Sinais: (1) frustracao detectada nas proximas msgs do usuario;
    (2) marcador explicito de pedido de ajuste/correcao;
    (3) o agente recorreu a Bash (script ad-hoc) logo apos a skill.
    """
    try:
        from app.agente.services.sentiment_detector import detect_frustration
    except Exception:
        detect_frustration = None

    user_msgs = window.proximas_user or []
    blob = _texts(user_msgs)

    # (2) marcadores de ajuste
    for pat in _ADJUST_MARKERS:
        if re.search(pat, blob):
            return True

    # (1) frustracao (usa a 1a proxima msg do usuario como atual)
    if detect_frustration and user_msgs:
        try:
            is_frustrated, _score = detect_frustration(
                str(user_msgs[0].get("content") or ""),
                previous_messages=None,
                had_error=_has_bash(window.proximas_assistant),
            )
            if is_frustrated:
                return True
        except Exception as e:
            logger.debug(f"[SKILL_EVAL] sentiment falhou (ignorado): {e}")

    # (3) script ad-hoc no mesmo turno apos a skill
    if _has_bash(window.proximas_assistant):
        return True

    return False
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py -k stage0 -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add app/agente/services/skill_effectiveness_service.py tests/agente/test_skill_effectiveness.py
git commit -m "feat(agente-skill-eval): estagio 0 custo-zero (sinal de nao-resolucao)"
```

---

## Task 5: Estagios 1 e 2 — Haiku e Sonnet

**Files:**
- Modify: `app/agente/services/skill_effectiveness_service.py`
- Test: `tests/agente/test_skill_effectiveness.py`

Contexto verificado: padrao de chamada `anthropic.Anthropic()` + `client.messages.create(model, max_tokens, system, messages)` (FONTE: `app/agente/workers/step_judge.py:66`). Parser de JSON do LLM: `parse_llm_json_response` (FONTE: `app/agente/services/_utils.py`). Separacao de competencias (spec): no estagio 2, ramo `ajuste_codigo` descreve problema+evidencia, NAO prescreve solucao.

- [ ] **Step 1: Teste dos estagios (mock do `_call_anthropic`)**

```python
# tests/agente/test_skill_effectiveness.py  (append)
def test_stage1_haiku_parses(monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    monkeypatch.setattr(svc, "_call_anthropic",
        lambda *a, **k: '{"resolveu": false, "suspeita_ajuste": true, "motivo": "x", "sinais": ["ajuste"]}')
    out = svc.stage1_haiku(_win(["ajusta isso"]))
    assert out["suspeita_ajuste"] is True
    assert out["resolveu"] is False


def test_stage2_sonnet_routes_branch(monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    monkeypatch.setattr(svc, "_call_anthropic",
        lambda *a, **k: '{"ramo": "lembrete_usuario", "titulo": "T", '
                        '"conteudo_lembrete": "sempre confirmar UF", "confianca": 0.9}')
    out = svc.stage2_sonnet(_win(["nao era isso"]))
    assert out["ramo"] == "lembrete_usuario"
    assert out["confianca"] == 0.9


def test_stage2_invalid_branch_falls_to_nada(monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    monkeypatch.setattr(svc, "_call_anthropic", lambda *a, **k: '{"ramo": "xpto"}')
    assert svc.stage2_sonnet(_win(["x"]))["ramo"] == "nada"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py -k "stage1 or stage2" -v` → FAIL.

- [ ] **Step 3: Implementar estagios + helpers de LLM**

```python
# app/agente/services/skill_effectiveness_service.py  (append)
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
_VALID_RAMOS = ("lembrete_usuario", "lembrete_todos", "ajuste_codigo", "nada")

_STAGE1_SYSTEM = (
    "Voce avalia se uma SKILL resolveu o pedido do usuario, olhando a janela de "
    "conversa logo apos a invocacao. Responda SO JSON: "
    '{"resolveu": bool, "suspeita_ajuste": bool, "motivo": "curto", "sinais": ["..."]}. '
    "suspeita_ajuste=true se o usuario pediu correcao/ajuste, reclamou, repetiu o pedido, "
    "ou o agente recorreu a script ad-hoc para o mesmo assunto. Seja conservador."
)

_STAGE2_SYSTEM = (
    "Voce e um avaliador de solucoes, chamado pela suspeita de necessidade de ajuste numa "
    "skill. Decida o RAMO da solucao. SEPARACAO DE COMPETENCIAS (inviolavel): para "
    "'ajuste_codigo' voce DESCREVE o problema e a evidencia e PEDE ajuda — NUNCA prescreve "
    "a solucao de codigo (isso e trabalho do Claude Code). Responda SO JSON: "
    '{"ramo": "lembrete_usuario|lembrete_todos|ajuste_codigo|nada", "titulo": "...", '
    '"conteudo_lembrete": "texto do lembrete (so ramos lembrete_*)", '
    '"problema": "descricao do problema (so ajuste_codigo)", '
    '"evidencia": "trechos que sustentam (so ajuste_codigo)", '
    '"categoria_codigo": "skill_bug|skill_suggestion|instruction_request|prompt_feedback", '
    '"justificativa": "...", "confianca": 0.0}. '
    "lembrete_usuario = orientacao especifica para ESTE usuario ao usar a skill. "
    "lembrete_todos = vale para todos (empresa). ajuste_codigo = a skill/codigo precisa mudar."
)


def _call_anthropic(model: str, system: str, user: str, max_tokens: int = 600) -> str:
    """Chamada sincrona ao Claude (mesmo padrao de step_judge._call_haiku_judge)."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def _format_window(window: SkillWindow, skill_description: str = "") -> str:
    def _fmt(m): return f"[{m.get('role')}] {str(m.get('content') or '')[:1500]}"
    parts = [f"SKILL: {window.skill_name}"]
    if skill_description:
        parts.append(f"DESCRICAO DA SKILL: {skill_description[:500]}")
    if window.msg_anterior:
        parts.append("PERGUNTA ANTERIOR:\n" + _fmt(window.msg_anterior))
    parts.append("RESPOSTA QUE INVOCOU A SKILL:\n" + _fmt(window.resposta_invocacao))
    if window.proximas_user:
        parts.append("PROXIMAS MSGS DO USUARIO:\n" + "\n".join(_fmt(m) for m in window.proximas_user))
    if window.proximas_assistant:
        parts.append("PROXIMAS RESPOSTAS DO AGENTE:\n" + "\n".join(_fmt(m) for m in window.proximas_assistant))
    return "\n\n".join(parts)


def _parse_json(raw: str) -> Dict[str, Any]:
    try:
        from app.agente.services._utils import parse_llm_json_response
        data = parse_llm_json_response(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def stage1_haiku(window: SkillWindow) -> Dict[str, Any]:
    raw = _call_anthropic(HAIKU_MODEL, _STAGE1_SYSTEM, _format_window(window), max_tokens=300)
    data = _parse_json(raw)
    return {
        "resolveu": bool(data.get("resolveu", True)),
        "suspeita_ajuste": bool(data.get("suspeita_ajuste", False)),
        "motivo": str(data.get("motivo", "")),
        "sinais": data.get("sinais", []) if isinstance(data.get("sinais"), list) else [],
    }


def stage2_sonnet(window: SkillWindow, skill_description: str = "") -> Dict[str, Any]:
    raw = _call_anthropic(SONNET_MODEL, _STAGE2_SYSTEM,
                          _format_window(window, skill_description), max_tokens=800)
    data = _parse_json(raw)
    ramo = data.get("ramo", "nada")
    if ramo not in _VALID_RAMOS:
        ramo = "nada"
    try:
        conf = float(data.get("confianca", 0.0) or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    return {
        "ramo": ramo,
        "titulo": str(data.get("titulo", ""))[:200],
        "conteudo_lembrete": str(data.get("conteudo_lembrete", "")),
        "problema": str(data.get("problema", "")),
        "evidencia": str(data.get("evidencia", "")),
        "categoria_codigo": str(data.get("categoria_codigo", "skill_bug")),
        "justificativa": str(data.get("justificativa", "")),
        "confianca": conf,
    }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py -k "stage1 or stage2" -v` → PASS (3).

- [ ] **Step 5: Commit**

```bash
git add app/agente/services/skill_effectiveness_service.py tests/agente/test_skill_effectiveness.py
git commit -m "feat(agente-skill-eval): estagios Haiku/Sonnet + separacao de competencias"
```

---

## Task 6: Aplicacao dos ramos

**Files:**
- Modify: `app/agente/services/skill_effectiveness_service.py`
- Test: `tests/agente/test_skill_effectiveness.py`

Contexto verificado: `AgentMemory.create_file(user_id, path, content)` add sem commit (FONTE: `models.py:666`); constraint unica `(user_id, path)`. Shadow empresa = `AgentMemory(user_id=0, escopo='empresa', directive_status='shadow', ...)` (FONTE padrao: `directive_promotion_service.py:444`). `AgentImprovementDialogue.create_suggestion(category, severity, title, description, evidence=None, session_ids=None)` (FONTE: `models.py:1250`) — NAO recebe solucao. `invalidate_injection_cache_for_user(user_id)` (FONTE: `memory_injection.py:39`). Flags: `AGENT_SKILL_EVAL_APPLY_USER`, `AGENT_SKILL_EVAL_CONF_MIN`.

- [ ] **Step 1: Teste da aplicacao por ramo (db fixture)**

```python
# tests/agente/test_skill_effectiveness.py  (append)
def test_apply_lembrete_usuario_creates_mandatory_memory(db, monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    from app.agente.models import AgentMemory
    monkeypatch.setattr(svc, "_invalidate_caches", lambda uid: None)
    decision = {"ramo": "lembrete_usuario", "titulo": "Confirmar UF",
                "conteudo_lembrete": "sempre confirmar UF antes de cotar", "confianca": 0.9}
    ref = svc.apply_decision(decision, _win(["nao era isso"]), user_id=1, session_id="s1")
    assert ref.startswith("memory:")
    mem = AgentMemory.query.filter_by(user_id=1,
        path="/memories/lembretes_skill/cotando-frete.xml").first()
    assert mem is not None and mem.priority == "mandatory" and mem.category == "permanent"


def test_apply_ajuste_codigo_has_no_solution(db):
    import app.agente.services.skill_effectiveness_service as svc
    from app.agente.models import AgentImprovementDialogue
    decision = {"ramo": "ajuste_codigo", "titulo": "skill falha em AM",
                "problema": "nao trata UF AM", "evidencia": "usuario repetiu 2x",
                "categoria_codigo": "skill_bug", "confianca": 0.8}
    ref = svc.apply_decision(decision, _win(["ajusta"]), user_id=1, session_id="s2")
    assert ref.startswith("dialogue:")
    d = AgentImprovementDialogue.query.get(int(ref.split(":")[1]))
    assert d.description == "nao trata UF AM"
    assert d.implementation_notes is None  # avaliador NAO prescreve solucao


def test_apply_low_confidence_user_downgrades(db, monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    from app.agente.config import feature_flags as ff
    monkeypatch.setattr(ff, "AGENT_SKILL_EVAL_CONF_MIN", 0.7, raising=False)
    decision = {"ramo": "lembrete_usuario", "titulo": "t", "problema": "p",
                "confianca": 0.3}  # < 0.7 -> vira ajuste_codigo
    ref = svc.apply_decision(decision, _win(["x"]), user_id=1, session_id="s3")
    assert ref.startswith("dialogue:")
```

- [ ] **Step 2: Rodar e ver falhar** → `python -m pytest tests/agente/test_skill_effectiveness.py -k apply -v` → FAIL.

- [ ] **Step 3: Implementar a aplicacao**

```python
# app/agente/services/skill_effectiveness_service.py  (append)
def _xml_escape(s: Optional[str]) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_reminder_xml(skill: str, decision: Dict[str, Any]) -> str:
    titulo = _xml_escape(decision.get("titulo", ""))
    corpo = _xml_escape(decision.get("conteudo_lembrete", "") or decision.get("titulo", ""))
    return (f'<skill_reminder skill="{_xml_escape(skill)}">\n'
            f'  <titulo>{titulo}</titulo>\n'
            f'  <orientacao>{corpo}</orientacao>\n'
            f'</skill_reminder>')


def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-') or 'skill'


def _invalidate_caches(user_id: int) -> None:
    try:
        from app.agente.sdk.memory_injection import (
            invalidate_injection_cache_for_user, invalidate_skill_reminders_cache)
        invalidate_injection_cache_for_user(user_id)
        invalidate_skill_reminders_cache()
    except Exception as e:
        logger.debug(f"[SKILL_EVAL] invalidate cache falhou: {e}")


def _apply_lembrete_usuario(decision, window, user_id, shadow=False) -> str:
    from app import db
    from app.agente.models import AgentMemory
    path = f"/memories/lembretes_skill/{window.skill_name}.xml"
    content = _render_reminder_xml(window.skill_name, decision)
    mem = AgentMemory.query.filter_by(user_id=user_id, path=path).first()
    if mem:
        mem.content = content
    else:
        mem = AgentMemory.create_file(user_id, path, content)
    mem.priority = "mandatory"
    mem.category = "permanent"
    mem.importance_score = 0.9
    mem.directive_status = "shadow" if shadow else None
    db.session.commit()
    _invalidate_caches(user_id)
    return f"memory:{mem.id}"


def _apply_lembrete_todos(decision, window) -> str:
    from app import db
    from app.agente.models import AgentMemory
    path = f"/memories/empresa/lembretes_skill/{_slug(window.skill_name)}.xml"
    existing = AgentMemory.query.filter_by(user_id=0, path=path).first()
    if existing:
        return f"approval:{existing.id}"
    mem = AgentMemory(
        user_id=0, path=path, content=_render_reminder_xml(window.skill_name, decision),
        is_directory=False, importance_score=0.7,
        escopo="empresa", directive_status="shadow", priority="mandatory",
        created_by=None,
    )
    db.session.add(mem)
    db.session.commit()
    return f"approval:{mem.id}"


def _apply_ajuste_codigo(decision, window, session_id) -> str:
    from app import db
    from app.agente.models import AgentImprovementDialogue
    sug = AgentImprovementDialogue.create_suggestion(
        category=decision.get("categoria_codigo", "skill_bug"),
        severity="info",
        title=(decision.get("titulo") or f"skill {window.skill_name}")[:200],
        description=decision.get("problema", ""),          # SO problema (sem solucao)
        evidence={"skill": window.skill_name,
                  "evidencia": decision.get("evidencia", ""),
                  "justificativa": decision.get("justificativa", "")},
        session_ids=[session_id],
    )
    db.session.commit()
    return f"dialogue:{sug.id}"


def apply_decision(decision: Dict[str, Any], window: SkillWindow,
                   user_id: int, session_id: str) -> str:
    """Aplica o ramo decidido. Retorna action_ref ('' se nada)."""
    from app.agente.config import feature_flags as ff
    ramo = decision.get("ramo", "nada")
    conf = decision.get("confianca", 0.0) or 0.0

    # lembrete_usuario de baixa confianca -> rebaixa p/ inbox (codigo)
    if ramo == "lembrete_usuario" and conf < ff.AGENT_SKILL_EVAL_CONF_MIN:
        ramo = "ajuste_codigo"

    if ramo == "lembrete_usuario":
        apply_user = getattr(ff, "AGENT_SKILL_EVAL_APPLY_USER", True)
        return _apply_lembrete_usuario(decision, window, user_id, shadow=not apply_user)
    if ramo == "lembrete_todos":
        return _apply_lembrete_todos(decision, window)
    if ramo == "ajuste_codigo":
        return _apply_ajuste_codigo(decision, window, session_id)
    return ""
```

- [ ] **Step 4: Rodar e ver passar** → `python -m pytest tests/agente/test_skill_effectiveness.py -k apply -v` → PASS (3).

- [ ] **Step 5: Commit**

```bash
git add app/agente/services/skill_effectiveness_service.py tests/agente/test_skill_effectiveness.py
git commit -m "feat(agente-skill-eval): aplicacao dos ramos (memoria/inbox/dialogue)"
```

---

## Task 7: evaluate_session — orquestracao + idempotencia

**Files:**
- Modify: `app/agente/services/skill_effectiveness_service.py`
- Test: `tests/agente/test_skill_effectiveness.py`

Contexto verificado: `AgentSession.query.filter_by(session_id=...)` + `.get_messages()` (FONTE: `models.py:168`). `sanitize_for_json` para campos JSON (FONTE: `app/utils/json_helpers.py`).

- [ ] **Step 1: Teste de orquestracao + idempotencia (mock dos estagios)**

```python
# tests/agente/test_skill_effectiveness.py  (append)
def _make_session(db, session_id, user_id, messages):
    from app.agente.models import AgentSession
    s = AgentSession(session_id=session_id, user_id=user_id, data={"messages": messages})
    db.session.add(s)
    db.session.flush()
    return s


def test_evaluate_session_idempotent(db, monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    from app.agente.models import AgentSkillEffectiveness
    msgs = [
        {"id": "u0", "role": "user", "content": "frete sp"},
        {"id": "a0", "role": "assistant", "content": "ok", "tools_used": ["Skill:cotando-frete"]},
        {"id": "u1", "role": "user", "content": "perfeito"},
        {"id": "a1", "role": "assistant", "content": "de nada"},
        {"id": "u2", "role": "user", "content": "valeu"},
    ]
    _make_session(db, "sess-idem", 1, msgs)
    monkeypatch.setattr(svc, "stage0_has_signal", lambda w: False)  # resolve no estagio 0
    svc.evaluate_session("sess-idem", 1)
    svc.evaluate_session("sess-idem", 1)  # 2a vez nao duplica
    n = AgentSkillEffectiveness.query.filter_by(session_id="sess-idem").count()
    assert n == 1


def test_evaluate_session_skips_open_window(db, monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    from app.agente.models import AgentSkillEffectiveness
    msgs = [
        {"id": "u0", "role": "user", "content": "x"},
        {"id": "a0", "role": "assistant", "content": "y", "tools_used": ["Skill:cotando-frete"]},
        {"id": "u1", "role": "user", "content": "z"},  # janela aberta (1 user)
    ]
    _make_session(db, "sess-open", 1, msgs)
    svc.evaluate_session("sess-open", 1)
    assert AgentSkillEffectiveness.query.filter_by(session_id="sess-open").count() == 0
```

- [ ] **Step 2: Rodar e ver falhar** → `python -m pytest tests/agente/test_skill_effectiveness.py -k evaluate_session -v` → FAIL.

- [ ] **Step 3: Implementar a orquestracao**

```python
# app/agente/services/skill_effectiveness_service.py  (append)
def _window_evidence(w: SkillWindow) -> Dict[str, Any]:
    def _c(m): return {"role": m.get("role"), "content": str(m.get("content") or "")[:500]}
    return {
        "skill": w.skill_name,
        "anterior": _c(w.msg_anterior) if w.msg_anterior else None,
        "proximas_user": [_c(m) for m in w.proximas_user],
    }


def _safe_persist(row, result) -> None:
    from app import db
    from sqlalchemy.exc import IntegrityError
    try:
        db.session.add(row)
        db.session.commit()
        result["avaliadas"] += 1
        if row.ramo:
            result["ramos"][row.ramo] = result["ramos"].get(row.ramo, 0) + 1
    except IntegrityError:
        db.session.rollback()  # corrida: ancora ja gravada por outra execucao


def _evaluate_inner(session_id: str, user_id: int) -> Dict[str, Any]:
    from app import db
    from app.agente.models import AgentSession, AgentSkillEffectiveness
    from app.agente.config import feature_flags as ff
    from app.utils.json_helpers import sanitize_for_json
    result = {"avaliadas": 0, "ramos": {}}

    sess = AgentSession.query.filter_by(session_id=session_id).first()
    if not sess:
        return result
    windows = build_skill_windows(sess.get_messages() or [])
    sonnet_budget = getattr(ff, "AGENT_SKILL_EVAL_MAX_SONNET", 3)

    for w in windows:
        if not w.janela_fechada:
            continue
        if AgentSkillEffectiveness.query.filter_by(
                session_id=session_id, anchor_msg_id=w.anchor_msg_id).first():
            continue
        row = AgentSkillEffectiveness(
            user_id=user_id, session_id=session_id, skill_name=w.skill_name,
            anchor_msg_id=w.anchor_msg_id, stage_reached=0, resolveu=True,
            evidencia_json=sanitize_for_json(_window_evidence(w)),
        )
        if not stage0_has_signal(w):
            _safe_persist(row, result)
            continue
        s1 = stage1_haiku(w)
        row.stage_reached = 1
        row.resolveu = bool(s1.get("resolveu", True))
        if not s1.get("suspeita_ajuste"):
            _safe_persist(row, result)
            continue
        if not getattr(ff, "AGENT_SKILL_EVAL_SONNET", True) or sonnet_budget <= 0:
            _safe_persist(row, result)
            continue
        sonnet_budget -= 1
        s2 = stage2_sonnet(w)
        row.stage_reached = 2
        row.ramo = s2.get("ramo", "nada")
        row.confidence = s2.get("confianca", 0.0)
        row.resolveu = (s2.get("ramo") == "nada")
        try:
            row.action_ref = apply_decision(s2, w, user_id, session_id) or None
        except Exception as e:
            logger.warning(f"[SKILL_EVAL] apply falhou: {e}")
        _safe_persist(row, result)
    return result


def evaluate_session(session_id: str, user_id: int, app=None) -> Dict[str, Any]:
    """Entry point. Best-effort. `app` fornecido => abre app_context (job RQ)."""
    try:
        if app is not None:
            with app.app_context():
                return _evaluate_inner(session_id, user_id)
        return _evaluate_inner(session_id, user_id)
    except Exception as e:
        logger.warning(f"[SKILL_EVAL] evaluate_session falhou (ignorado): {e}")
        return {"avaliadas": 0, "ramos": {}}
```

- [ ] **Step 4: Rodar e ver passar** → `python -m pytest tests/agente/test_skill_effectiveness.py -k evaluate_session -v` → PASS (2). Rodar o arquivo todo: `python -m pytest tests/agente/test_skill_effectiveness.py -v`.

- [ ] **Step 5: Commit**

```bash
git add app/agente/services/skill_effectiveness_service.py tests/agente/test_skill_effectiveness.py
git commit -m "feat(agente-skill-eval): orquestracao evaluate_session + idempotencia"
```

---

## Task 8: try_enqueue + job RQ

**Files:**
- Modify: `app/agente/workers/background_jobs.py`
- Test: `tests/agente/test_skill_eval_worker.py`

Contexto verificado: padrao `_is_rq_enabled()` (le `AGENT_POST_SESSION_VIA_RQ`) + `_get_queue()` (fila `agent_background`) + `try_enqueue_*(args) -> bool` (FONTE: `background_jobs.py:122-200`). Job: `create_app()` + service (FONTE: `background_jobs.py:41-47`).

- [ ] **Step 1: Teste do enqueue (mock da fila) e do job (mock do service)**

```python
# tests/agente/test_skill_eval_worker.py
def test_try_enqueue_skill_effectiveness_disabled(monkeypatch):
    import app.agente.workers.background_jobs as bj
    monkeypatch.setattr(bj, "_is_rq_enabled", lambda: False)
    assert bj.try_enqueue_skill_effectiveness("s1", 1) is False


def test_try_enqueue_skill_effectiveness_enqueues(monkeypatch):
    import app.agente.workers.background_jobs as bj

    class _Q:
        def __init__(self): self.calls = []
        def enqueue(self, *a, **k): self.calls.append((a, k))
    q = _Q()
    monkeypatch.setattr(bj, "_is_rq_enabled", lambda: True)
    monkeypatch.setattr(bj, "_get_queue", lambda: q)
    assert bj.try_enqueue_skill_effectiveness("sess-xyz", 7) is True
    assert q.calls and q.calls[0][0][0] is bj.skill_effectiveness_job
    assert q.calls[0][0][1:] == ("sess-xyz", 7)
```

- [ ] **Step 2: Rodar e ver falhar** → `python -m pytest tests/agente/test_skill_eval_worker.py -v` → FAIL.

- [ ] **Step 3: Implementar job + enqueue (append em background_jobs.py)**

```python
# app/agente/workers/background_jobs.py  (append na secao de jobs)
def skill_effectiveness_job(session_id: str, user_id: int) -> bool:
    """Job RQ: avalia efetividade das skills invocadas na sessao."""
    try:
        from app import create_app
        from app.agente.services.skill_effectiveness_service import evaluate_session
        app = create_app()
        evaluate_session(session_id=session_id, user_id=user_id, app=app)
        return True
    except Exception as e:
        logger.error(f"[RQ_JOB skill_eval] session={session_id[:8]}... erro: {e}", exc_info=True)
        return False


# (append na secao try_enqueue_*)
def try_enqueue_skill_effectiveness(session_id: str, user_id: int) -> bool:
    if not _is_rq_enabled():
        return False
    q = _get_queue()
    if q is None:
        return False
    try:
        q.enqueue(
            skill_effectiveness_job,
            session_id, user_id,
            job_timeout=180,
            description=f"skill_eval {session_id[:8]}",
        )
        return True
    except Exception as e:
        logger.warning(f"[RQ] enqueue skill_eval falhou (fallback inline): {e}")
        return False
```

> Fila `agent_background` ja e monitorada pelos 3 perfis de worker (Worker 0 LIGHT-RESERVED
> inclui `agent_validation`/leves; `agent_background` ja roda hoje p/ summarize/patterns).
> **Nenhuma edicao em `worker_render.py`/`start_worker_render.sh`** (reuso de fila existente).

- [ ] **Step 4: Rodar e ver passar** → `python -m pytest tests/agente/test_skill_eval_worker.py -v` → PASS (2).

- [ ] **Step 5: Commit**

```bash
git add app/agente/workers/background_jobs.py tests/agente/test_skill_eval_worker.py
git commit -m "feat(agente-skill-eval): job RQ + try_enqueue (fila agent_background)"
```

---

## Task 9: Gatilho em run_post_session_processing

**Files:**
- Modify: `app/agente/routes/_helpers.py` (apos o bloco PRD v2.1 de extracao, ~linha 305-345, antes do fim da funcao)
- Test: `tests/agente/test_skill_eval_worker.py`

Contexto verificado: `run_post_session_processing(app, session, session_id, user_id, user_message, assistant_message)` roda com app_context ativo e enfileira via `try_enqueue_*` com fallback inline (FONTE: `_helpers.py:187-316`). **Export critico Teams** — bloco isolado try/except.

- [ ] **Step 1: Teste do gatilho (flag ON enfileira; flag OFF noop)**

```python
# tests/agente/test_skill_eval_worker.py  (append)
def test_post_session_triggers_skill_eval_when_flag_on(monkeypatch):
    import app.agente.routes._helpers as helpers
    called = {}
    monkeypatch.setattr("app.agente.config.feature_flags.AGENT_SKILL_EVAL", True, raising=False)
    monkeypatch.setattr(
        "app.agente.workers.background_jobs.try_enqueue_skill_effectiveness",
        lambda sid, uid: called.setdefault("enq", (sid, uid)) or True)
    helpers._maybe_trigger_skill_eval("sess-1", 5)  # helper extraido (testavel)
    assert called["enq"] == ("sess-1", 5)


def test_post_session_skill_eval_noop_when_flag_off(monkeypatch):
    import app.agente.routes._helpers as helpers
    monkeypatch.setattr("app.agente.config.feature_flags.AGENT_SKILL_EVAL", False, raising=False)
    # nao deve levantar nem chamar nada
    helpers._maybe_trigger_skill_eval("sess-1", 5)
```

- [ ] **Step 2: Rodar e ver falhar** → `python -m pytest tests/agente/test_skill_eval_worker.py -k post_session -v` → FAIL.

- [ ] **Step 3: Implementar o helper + plugar no fluxo**

```python
# app/agente/routes/_helpers.py  (novo helper, perto de run_post_session_processing)
def _maybe_trigger_skill_eval(session_id: str, user_id: int) -> None:
    """Best-effort: enfileira avaliacao de efetividade de skill (Fase 1)."""
    try:
        from app.agente.config.feature_flags import AGENT_SKILL_EVAL
        if not AGENT_SKILL_EVAL:
            return
        from app.agente.workers.background_jobs import try_enqueue_skill_effectiveness
        if not try_enqueue_skill_effectiveness(session_id, user_id):
            from app.agente.services.skill_effectiveness_service import evaluate_session
            evaluate_session(session_id=session_id, user_id=user_id)  # app_context ja ativo
    except Exception as e:
        logger.warning(f"[POST_SESSION] skill effectiveness (ignorado): {e}")
```

```python
# app/agente/routes/_helpers.py  — DENTRO de run_post_session_processing,
# apos o bloco "PRD v2.1: Extracao pos-sessao" (o ultimo try/except da funcao):
    # =================================================================
    # Fase 1: Avaliacao de efetividade de skill (best-effort)
    # =================================================================
    _maybe_trigger_skill_eval(session_id, user_id)
```

- [ ] **Step 4: Rodar e ver passar** → `python -m pytest tests/agente/test_skill_eval_worker.py -k post_session -v` → PASS (2).

- [ ] **Step 5: Commit**

```bash
git add app/agente/routes/_helpers.py tests/agente/test_skill_eval_worker.py
git commit -m "feat(agente-skill-eval): gatilho pos-sessao em run_post_session_processing"
```

---

## Task 10: Injecao cirurgica do lembrete

**Files:**
- Modify: `app/agente/sdk/memory_injection.py` (helper + cache)
- Modify: `app/agente/sdk/hooks.py` (`_keep_stream_open`, novo `elif tool_name == 'Skill'`)
- Test: `tests/agente/test_skill_effectiveness.py`

Contexto verificado: `_keep_stream_open` monta `additional` por `tool_name` e injeta via `hookSpecificOutput.additionalContext` (FONTE: `hooks.py:139-217`); `user_id` disponivel por closure; `get_current_session_id()` (FONTE: `permissions.py:110`, usado em `hooks.py:190`). Lembrete aplicado = `directive_status` NULL/`'ativa'` (shadow NAO injeta).

- [ ] **Step 1: Teste do loader de lembretes (db fixture)**

```python
# tests/agente/test_skill_effectiveness.py  (append)
def test_get_skill_reminders_only_active(db, monkeypatch):
    monkeypatch.setattr("app.agente.config.feature_flags.AGENT_SKILL_EVAL", True, raising=False)
    from app.agente.models import AgentMemory
    from app.agente.sdk.memory_injection import (
        get_skill_reminders_for_session, invalidate_skill_reminders_cache)
    AgentMemory.create_file(1, "/memories/lembretes_skill/cotando-frete.xml", "<x>ativo</x>")
    shadow = AgentMemory.create_file(1, "/memories/lembretes_skill/outra.xml", "<x>shadow</x>")
    shadow.directive_status = "shadow"
    db.session.commit()
    invalidate_skill_reminders_cache()
    rem = get_skill_reminders_for_session(1, "sess-r")
    assert "cotando-frete" in rem and "outra" not in rem  # shadow nao injeta
```

- [ ] **Step 2: Rodar e ver falhar** → `python -m pytest tests/agente/test_skill_effectiveness.py -k get_skill_reminders -v` → FAIL.

- [ ] **Step 3a: Implementar loader + cache (memory_injection.py append)**

```python
# app/agente/sdk/memory_injection.py  (append; usa threading ja importado p/ os outros caches)
_SKILL_REMINDERS_CACHE: dict[str, tuple[dict, float]] = {}
_SKILL_REMINDERS_TTL = 1800
_SKILL_REMINDERS_LOCK = threading.Lock()


def invalidate_skill_reminders_cache() -> None:
    with _SKILL_REMINDERS_LOCK:
        _SKILL_REMINDERS_CACHE.clear()


def get_skill_reminders_for_session(user_id: int, session_id: str) -> dict:
    """{skill_name: conteudo} dos lembretes ATIVOS (NULL/'ativa') do usuario. Cache por sessao."""
    import time
    from app.agente.config.feature_flags import AGENT_SKILL_EVAL
    if not AGENT_SKILL_EVAL:
        return {}
    now = time.time()
    with _SKILL_REMINDERS_LOCK:
        hit = _SKILL_REMINDERS_CACHE.get(session_id)
        if hit and (now - hit[1]) < _SKILL_REMINDERS_TTL:
            return hit[0]
    out: dict = {}
    try:
        from app import db
        from app.agente.models import AgentMemory
        rows = AgentMemory.query.filter(
            AgentMemory.user_id == user_id,
            AgentMemory.path.like('/memories/lembretes_skill/%'),
            db.or_(AgentMemory.directive_status.is_(None),
                   AgentMemory.directive_status == 'ativa'),
        ).all()
        for m in rows:
            skill = m.path.rsplit('/', 1)[-1].replace('.xml', '')
            if skill:
                out[skill] = m.content or ""
    except Exception as e:
        logger.debug(f"[SKILL_EVAL] reminders load falhou: {e}")
    with _SKILL_REMINDERS_LOCK:
        if len(_SKILL_REMINDERS_CACHE) > 500:
            _SKILL_REMINDERS_CACHE.clear()
        _SKILL_REMINDERS_CACHE[session_id] = (out, now)
    return out
```

- [ ] **Step 3b: Injetar no PreToolUse (hooks.py — novo elif apos o bloco Bash/python, ~linha 160)**

```python
# app/agente/sdk/hooks.py  — dentro de _keep_stream_open, na cadeia de elif por tool_name:
        elif tool_name == 'Skill':
            try:
                from ..config.feature_flags import AGENT_SKILL_EVAL
                if AGENT_SKILL_EVAL:
                    tinput = hook_input.get('tool_input', {})
                    skill = tinput.get('skill', '') if isinstance(tinput, dict) else ''
                    if skill:
                        from ..config.permissions import get_current_session_id
                        from .memory_injection import get_skill_reminders_for_session
                        sid = get_current_session_id() or ''
                        rem = get_skill_reminders_for_session(user_id, sid).get(skill)
                        if rem:
                            additional = (
                                f"LEMBRETE para a skill '{skill}' (aprendido de interacoes "
                                f"anteriores deste usuario):\n{rem}")
            except Exception as e:
                logger.debug(f"[SKILL_EVAL] inject reminder falhou: {e}")
```

- [ ] **Step 4: Rodar e ver passar** → `python -m pytest tests/agente/test_skill_effectiveness.py -k get_skill_reminders -v` → PASS. Suite: `python -m pytest tests/agente/test_skill_effectiveness.py -v`.

- [ ] **Step 5: Commit**

```bash
git add app/agente/sdk/memory_injection.py app/agente/sdk/hooks.py tests/agente/test_skill_effectiveness.py
git commit -m "feat(agente-skill-eval): injecao cirurgica do lembrete no PreToolUse (tool=Skill)"
```

---

## Task 11: Inbox — service

**Files:**
- Create: `app/agente/services/approval_inbox_service.py`
- Test: `tests/agente/test_approval_inbox.py`

Contexto verificado: shadow injeta nada; `directive_status='ativa'` injeta (FONTE: `memory_injection.py:505`). `AgentImprovementDialogue` proposed e consumido pelo Claude Code via `/pending` (FONTE: `models.py:1281`). valid statuses incluem `'rejected'` (FONTE: `routes/improvement_dialogue.py:71`). Semantica: **memory shadow** = Aprovar(`ativa`)/Rejeitar(`despromovida`); **dialogue proposed** = so Rejeitar (o Claude Code implementa os que seguem `proposed`).

- [ ] **Step 1: Teste do service**

```python
# tests/agente/test_approval_inbox.py
def test_list_pending_includes_shadow_and_proposed(db):
    from app.agente.models import AgentMemory, AgentImprovementDialogue
    from app.agente.services import approval_inbox_service as inbox
    m = AgentMemory(user_id=0, path="/memories/empresa/lembretes_skill/x.xml",
                    content="<x/>", is_directory=False, escopo="empresa",
                    directive_status="shadow", priority="mandatory")
    db.session.add(m)
    AgentImprovementDialogue.create_suggestion(
        category="skill_bug", severity="info", title="t", description="d")
    db.session.commit()
    items = inbox.list_pending_approvals()
    kinds = {it["kind"] for it in items}
    assert "memory" in kinds and "dialogue" in kinds


def test_approve_memory_activates(db):
    from app.agente.models import AgentMemory
    from app.agente.services import approval_inbox_service as inbox
    m = AgentMemory(user_id=0, path="/memories/empresa/lembretes_skill/y.xml",
                    content="<x/>", is_directory=False, escopo="empresa",
                    directive_status="shadow", priority="mandatory")
    db.session.add(m); db.session.commit()
    assert inbox.approve_item("memory", m.id, reviewer_user_id=1) is True
    assert AgentMemory.query.get(m.id).directive_status == "ativa"


def test_reject_dialogue(db):
    from app.agente.models import AgentImprovementDialogue
    from app.agente.services import approval_inbox_service as inbox
    d = AgentImprovementDialogue.create_suggestion(
        category="skill_bug", severity="info", title="t", description="d")
    db.session.commit()
    assert inbox.reject_item("dialogue", d.id, reviewer_user_id=1) is True
    assert AgentImprovementDialogue.query.get(d.id).status == "rejected"
```

- [ ] **Step 2: Rodar e ver falhar** → `python -m pytest tests/agente/test_approval_inbox.py -v` → FAIL.

- [ ] **Step 3: Implementar o service**

```python
# app/agente/services/approval_inbox_service.py
"""Inbox de Aprovacao unificada: AgentMemory shadow + ImprovementDialogue proposed.
Conserta o gap do directive_promotion (shadow->ativa nunca teve UI). Best-effort nas
leituras; writes commitam. Ver spec 2026-06-07-aprendizado-efetividade-skills-design.md
"""
import logging
logger = logging.getLogger(__name__)


def list_pending_approvals() -> list:
    """Lista itens pendentes de decisao humana (memory shadow + dialogue proposed)."""
    out = []
    try:
        from app.agente.models import AgentMemory, AgentImprovementDialogue
        for m in AgentMemory.query.filter(
                AgentMemory.directive_status == 'shadow').order_by(
                AgentMemory.created_at.desc()).limit(200).all():
            out.append({
                "kind": "memory", "id": m.id, "title": m.path.rsplit('/', 1)[-1],
                "scope": "empresa" if m.user_id == 0 else f"user:{m.user_id}",
                "content": m.content, "created_at": m.created_at.isoformat() if m.created_at else None,
                "can_approve": True,
            })
        for d in AgentImprovementDialogue.query.filter_by(
                status='proposed').order_by(
                AgentImprovementDialogue.created_at.desc()).limit(200).all():
            out.append({
                "kind": "dialogue", "id": d.id, "title": d.title,
                "category": d.category, "content": d.description,
                "evidence": d.evidence_json or {},
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "can_approve": False,  # Claude Code implementa os que seguem 'proposed'
            })
    except Exception as e:
        logger.warning(f"[INBOX] list falhou: {e}")
    return out


def approve_item(kind: str, item_id: int, reviewer_user_id: int) -> bool:
    """Aprova. memory shadow -> 'ativa' (passa a injetar). dialogue: nao aplicavel."""
    from app import db
    if kind != "memory":
        logger.info(f"[INBOX] approve nao aplicavel para kind={kind}")
        return False
    try:
        from app.agente.models import AgentMemory
        from app.agente.sdk.memory_injection import (
            invalidate_injection_cache_for_user, invalidate_skill_reminders_cache)
        m = AgentMemory.query.get(item_id)
        if not m or m.directive_status != 'shadow':
            return False
        m.directive_status = 'ativa'
        m.reviewed_at = _now()
        db.session.commit()
        invalidate_injection_cache_for_user(m.user_id)
        invalidate_skill_reminders_cache()
        logger.info(f"[INBOX] memory {item_id} APROVADA->ativa por user={reviewer_user_id}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.warning(f"[INBOX] approve falhou: {e}")
        return False


def reject_item(kind: str, item_id: int, reviewer_user_id: int) -> bool:
    """Rejeita. memory -> 'despromovida'; dialogue -> status 'rejected'."""
    from app import db
    try:
        if kind == "memory":
            from app.agente.models import AgentMemory
            from app.agente.sdk.memory_injection import invalidate_skill_reminders_cache
            m = AgentMemory.query.get(item_id)
            if not m:
                return False
            m.directive_status = 'despromovida'
            m.reviewed_at = _now()
            db.session.commit()
            invalidate_skill_reminders_cache()
            return True
        elif kind == "dialogue":
            from app.agente.models import AgentImprovementDialogue
            d = AgentImprovementDialogue.query.get(item_id)
            if not d:
                return False
            d.status = 'rejected'
            db.session.commit()
            return True
        return False
    except Exception as e:
        db.session.rollback()
        logger.warning(f"[INBOX] reject falhou: {e}")
        return False


def _now():
    from app.utils.timezone import agora_utc_naive
    return agora_utc_naive()
```

> Verificar o import de `agora_utc_naive` (mesmo usado em `models.py`/`memories.py`).
> Se o path for outro, alinhar ao import ja usado em `routes/memories.py:273`.

- [ ] **Step 4: Rodar e ver passar** → `python -m pytest tests/agente/test_approval_inbox.py -v` → PASS (3).

- [ ] **Step 5: Commit**

```bash
git add app/agente/services/approval_inbox_service.py tests/agente/test_approval_inbox.py
git commit -m "feat(agente-skill-eval): inbox service (shadow->ativa conserta directive_promotion)"
```

---

## Task 12: Inbox — rotas

**Files:**
- Modify: `app/agente/routes/memories.py`
- Test: `tests/agente/test_approval_inbox.py`

Contexto verificado: padrao de rota admin-only (`@login_required` + `current_user.perfil != 'administrador'` -> 403, try/except + jsonify) (FONTE: `memories.py:255-289`). `client` fixture (FONTE: `conftest.py:70`, `LOGIN_DISABLED=True`).

- [ ] **Step 1: Teste das rotas (client)**

```python
# tests/agente/test_approval_inbox.py  (append)
def test_route_list_approvals(client, db, monkeypatch):
    # admin bypass: LOGIN_DISABLED True; forcar perfil admin via current_user mock se preciso
    import app.agente.routes.memories as mem_routes
    monkeypatch.setattr(mem_routes, "_require_admin_json", lambda: None)
    monkeypatch.setattr("app.agente.services.approval_inbox_service.list_pending_approvals",
                        lambda: [{"kind": "memory", "id": 1, "title": "x"}])
    resp = client.get("/agente/api/memories/approvals")
    assert resp.status_code == 200
    assert resp.get_json()["items"][0]["kind"] == "memory"


def test_route_approve_memory(client, monkeypatch):
    import app.agente.routes.memories as mem_routes
    monkeypatch.setattr(mem_routes, "_require_admin_json", lambda: None)
    called = {}
    monkeypatch.setattr("app.agente.services.approval_inbox_service.approve_item",
                        lambda kind, iid, reviewer_user_id: called.setdefault("a", (kind, iid)) or True)
    resp = client.put("/agente/api/memories/approvals/memory/5/approve")
    assert resp.status_code == 200 and called["a"] == ("memory", 5)
```

> NOTA: `_require_admin_json` existe em `memories.py:373`. Se a checagem de admin for
> inline (como em `api_review_memory`), replicar o padrao `current_user.perfil` e ajustar
> o monkeypatch. Verificar o helper real antes.

- [ ] **Step 2: Rodar e ver falhar** → `python -m pytest tests/agente/test_approval_inbox.py -k route -v` → FAIL (404).

- [ ] **Step 3: Implementar as rotas (append em memories.py)**

```python
# app/agente/routes/memories.py  (append; usa _require_admin_json ja existente)
@agente_bp.route('/api/memories/approvals', methods=['GET'])
@login_required
def api_list_approvals():
    """Inbox de Aprovacao: memory shadow + dialogue proposed (admin)."""
    guard = _require_admin_json()
    if guard:
        return guard
    from app.agente.services.approval_inbox_service import list_pending_approvals
    return jsonify({'success': True, 'items': list_pending_approvals()})


@agente_bp.route('/api/memories/approvals/<kind>/<int:item_id>/approve', methods=['PUT'])
@login_required
def api_approve_item(kind: str, item_id: int):
    guard = _require_admin_json()
    if guard:
        return guard
    from app.agente.services.approval_inbox_service import approve_item
    ok = approve_item(kind, item_id, reviewer_user_id=current_user.id)
    return jsonify({'success': ok}), (200 if ok else 400)


@agente_bp.route('/api/memories/approvals/<kind>/<int:item_id>/reject', methods=['PUT'])
@login_required
def api_reject_item(kind: str, item_id: int):
    guard = _require_admin_json()
    if guard:
        return guard
    from app.agente.services.approval_inbox_service import reject_item
    ok = reject_item(kind, item_id, reviewer_user_id=current_user.id)
    return jsonify({'success': ok}), (200 if ok else 400)
```

> Se `_require_admin_json()` retornar `None` quando admin e uma `Response` (403) quando
> nao (padrao tipico), o `if guard: return guard` funciona. Confirmar a semantica em
> `memories.py:373` antes; ajustar se ele lan,car excecao em vez de retornar.

- [ ] **Step 4: Rodar e ver passar** → `python -m pytest tests/agente/test_approval_inbox.py -k route -v` → PASS (2).

- [ ] **Step 5: Commit**

```bash
git add app/agente/routes/memories.py tests/agente/test_approval_inbox.py
git commit -m "feat(agente-skill-eval): rotas da inbox de aprovacao (admin-only)"
```

---

## Task 13: Inbox — UI (aba memorias.html)

**Files:**
- Modify: `app/agente/templates/agente/memorias.html`
- Test: verificacao manual (UI) + a rota GET ja coberta na Task 12

A tela `/agente/memorias` ja esta no menu (`_sidebar.html:878`) e e admin-only — a Inbox e uma ABA nela (sem tela orfa). Seguir os componentes do `GUIA_COMPONENTES_UI.md` (badges/botoes via classes existentes; sem `<style>` inline; cores via tokens).

- [ ] **Step 1: Adicionar a aba e o painel (estrutura)**

Adicionar, junto ao cabecalho de abas/filtros existente em `memorias.html`, um botao de aba
"Pendentes de Aprovacao" e um container:

```html
<!-- aba -->
<button class="btn btn-outline-secondary btn-sm" id="tab-approvals"
        onclick="loadApprovals()">Pendentes de Aprovacao
  <span class="badge bg-warning text-dark" id="approvals-count">0</span>
</button>

<!-- painel -->
<div id="approvals-panel" class="d-none mt-3">
  <table class="table table-sm align-middle">
    <thead><tr><th>Tipo</th><th>Titulo</th><th>Escopo/Cat.</th><th>Conteudo</th><th>Acoes</th></tr></thead>
    <tbody id="approvals-tbody"></tbody>
  </table>
</div>
```

- [ ] **Step 2: Adicionar o JS (fetch + render + acoes)**

```html
<script>
async function loadApprovals() {
  document.getElementById('approvals-panel').classList.remove('d-none');
  const r = await fetch('/agente/api/memories/approvals');
  const data = await r.json();
  const items = (data.items || []);
  document.getElementById('approvals-count').textContent = items.length;
  const tb = document.getElementById('approvals-tbody');
  tb.innerHTML = items.map(it => `
    <tr>
      <td><span class="badge bg-secondary">${it.kind}</span></td>
      <td>${(it.title||'').replace(/</g,'&lt;')}</td>
      <td>${it.scope||it.category||''}</td>
      <td><small>${(it.content||'').slice(0,160).replace(/</g,'&lt;')}</small></td>
      <td>
        ${it.can_approve ? `<button class="btn btn-success btn-sm" onclick="decideApproval('${it.kind}',${it.id},'approve')">Aprovar</button>` : ''}
        <button class="btn btn-outline-danger btn-sm" onclick="decideApproval('${it.kind}',${it.id},'reject')">Rejeitar</button>
      </td>
    </tr>`).join('');
}
async function decideApproval(kind, id, action) {
  if (!confirm(`Confirmar ${action} do item ${kind}:${id}?`)) return;
  const r = await fetch(`/agente/api/memories/approvals/${kind}/${id}/${action}`, {method: 'PUT'});
  if ((await r.json()).success) loadApprovals(); else alert('Falhou.');
}
</script>
```

> Se `memorias.html` ja tem helpers de fetch/CSRF, reusa-los (PUT pode exigir header CSRF —
> verificar o padrao das chamadas existentes na tela; as rotas atuais de memoria usam
> `@login_required` sem CSRF custom no template — alinhar).

- [ ] **Step 3: Verificacao manual**

Subir local (`python run.py`), logar como admin, abrir `/agente/memorias`, clicar
"Pendentes de Aprovacao": a lista carrega; Aprovar uma memory shadow -> some da lista e
`directive_status` vira `ativa` (conferir no banco); Rejeitar um dialogue -> `status='rejected'`.

- [ ] **Step 4: Commit**

```bash
git add app/agente/templates/agente/memorias.html
git commit -m "feat(agente-skill-eval): aba Inbox de Aprovacao em /agente/memorias"
```

---

## Task 14: Ajuste do improvement_suggester (D8)

**Files:**
- Modify: `app/agente/services/improvement_suggester.py` (system prompt do batch, ~linha 55-99)
- Test: `tests/agente/test_approval_inbox.py`

Separacao de competencias vale tambem para o D8 padrao: as sugestoes devem ser
**descricao de problema + pedido de ajuda**, nao solucao prescrita.

- [ ] **Step 1: Teste (guard de que o prompt instrui separacao de competencias)**

```python
# tests/agente/test_approval_inbox.py  (append)
def test_d8_prompt_separates_competencies():
    import app.agente.services.improvement_suggester as m
    blob = " ".join(str(v) for v in vars(m).values() if isinstance(v, str)).lower()
    assert ("pedido de ajuda" in blob) or ("nao prescrev" in blob) or ("descreva o problema" in blob)
```

- [ ] **Step 2: Rodar e ver falhar** → `python -m pytest tests/agente/test_approval_inbox.py -k competencies -v` → FAIL.

- [ ] **Step 3: Editar o system prompt do batch**

Localizar a constante do system prompt do batch (improvement_suggester.py, ~linha 55-99,
a string com `cache_control`) e adicionar ao final dela a clausula:

```text
SEPARACAO DE COMPETENCIAS: descreva o PROBLEMA observado e a EVIDENCIA e faca um PEDIDO
DE AJUDA acionavel. NAO prescreva a solucao de codigo nem passos de implementacao — isso
e trabalho do Claude Code. O campo 'description' deve conter o problema, nao a correcao.
```

- [ ] **Step 4: Rodar e ver passar** → `python -m pytest tests/agente/test_approval_inbox.py -k competencies -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agente/services/improvement_suggester.py tests/agente/test_approval_inbox.py
git commit -m "feat(agente-skill-eval): D8 padrao tambem separa competencias (problema, nao solucao)"
```

---

## Task 15: Smoke + ativacao de flags

**Files:**
- Test: `tests/agente/test_skill_eval_worker.py`

- [ ] **Step 1: Smoke end-to-end (mock LLMs, fluxo completo)**

```python
# tests/agente/test_skill_eval_worker.py  (append)
def test_smoke_end_to_end_creates_user_reminder(db, monkeypatch):
    import app.agente.services.skill_effectiveness_service as svc
    from app.agente.models import AgentSession, AgentMemory, AgentSkillEffectiveness
    # sessao com sinal de nao-resolucao
    msgs = [
        {"id": "u0", "role": "user", "content": "frete pra Manaus"},
        {"id": "a0", "role": "assistant", "content": "cotando", "tools_used": ["Skill:cotando-frete"]},
        {"id": "u1", "role": "user", "content": "nao era isso, ta errado"},
        {"id": "a1", "role": "assistant", "content": "corrigindo"},
        {"id": "u2", "role": "user", "content": "agora foi"},
    ]
    s = AgentSession(session_id="smoke-1", user_id=1, data={"messages": msgs})
    db.session.add(s); db.session.flush()
    monkeypatch.setattr(svc, "stage1_haiku",
        lambda w: {"resolveu": False, "suspeita_ajuste": True, "motivo": "", "sinais": []})
    monkeypatch.setattr(svc, "stage2_sonnet",
        lambda w, d="": {"ramo": "lembrete_usuario", "titulo": "Confirmar UF destino",
                          "conteudo_lembrete": "para Manaus, confirmar UF=AM", "confianca": 0.95})
    monkeypatch.setattr(svc, "_invalidate_caches", lambda uid: None)
    res = svc.evaluate_session("smoke-1", 1)
    assert res["avaliadas"] == 1
    row = AgentSkillEffectiveness.query.filter_by(session_id="smoke-1").first()
    assert row.ramo == "lembrete_usuario" and row.stage_reached == 2
    assert AgentMemory.query.filter_by(
        user_id=1, path="/memories/lembretes_skill/cotando-frete.xml").first() is not None
```

- [ ] **Step 2: Rodar a suite inteira da feature**

Run: `python -m pytest tests/agente/test_skill_effectiveness.py tests/agente/test_skill_eval_worker.py tests/agente/test_approval_inbox.py -v`
Expected: ALL PASS. Anotar a contagem.

- [ ] **Step 3: Commit**

```bash
git add tests/agente/test_skill_eval_worker.py
git commit -m "test(agente-skill-eval): smoke end-to-end (sessao -> lembrete usuario)"
```

- [ ] **Step 4: Checklist de ativacao (PROD) — NAO automatico**

1. Rodar a migration em PROD (Render Shell): `psql ... -f scripts/migrations/2026_06_07_agent_skill_effectiveness.sql` OU o `.py`.
2. Garantir `AGENT_POST_SESSION_VIA_RQ=true` (ja usado pelos demais jobs) — senao o fallback inline roda no request.
3. **Smoke com avaliacao em modo observacao:** ligar `AGENT_SKILL_EVAL=true` + `AGENT_SKILL_EVAL_APPLY_USER=false` (lembrete vira shadow, vai p/ inbox) por 1 ciclo; conferir `agent_skill_effectiveness` populando e a inbox enchendo sem ruido.
4. Validar a Inbox em `/agente/memorias` (aprovar/rejeitar funciona; diretriz shadow ativa).
5. Apos validacao, ligar `AGENT_SKILL_EVAL_APPLY_USER=true` (lembrete_usuario auto).
6. Monitorar custo (funil deve manter Sonnet raro) e logs `[SKILL_EVAL]`.

---

## Self-review

**1. Cobertura da spec (Fase 1):**

| Requisito da spec | Task |
|---|---|
| Gatilho em `run_post_session_processing` | 9 |
| Janela ancorada (anterior + 2 user + 2 assistant) | 3 |
| Funil estagio 0 / Haiku / Sonnet | 4, 5, 7 |
| Separacao de competencias (avaliador descreve, nao prescreve) | 5 (estagio 2), 6 (`_apply_ajuste_codigo`), 14 (D8) |
| Ramo lembrete_usuario (auto, reversivel) | 6 |
| Ramo lembrete_todos (via inbox/shadow) | 6, 11 |
| Ramo ajuste_codigo (improvement dialogue) | 6 |
| Injecao cirurgica no PreToolUse (so na skill) | 10 |
| Tabela `agent_skill_effectiveness` + idempotencia + `confidence` | 2, 7 |
| Inbox unificada (conserta directive shadow) | 11, 12, 13 |
| Flags + custo/cap + dedup | 1, 6, 7 |
| Testes deterministicos (LLM mockado) | todas |

Fora de escopo (Fase 2, spec propria): `agent_adhoc_script`, captura/cluster de scripts ad-hoc.

**2. Placeholder scan:** sem TBD/TODO no codigo. Pontos que pedem "verificar antes"
(`_require_admin_json` semantica, import de `agora_utc_naive`, CSRF do template, ponto
exato de insercao em `_helpers.py`) sao verificacoes de integracao com codigo existente —
o executor confirma a assinatura real antes (NAO inventar). Onde a assinatura ja foi
verificada nesta sessao, o codigo e literal.

**3. Consistencia de tipos:** `SkillWindow` (campos), `stage1_haiku`/`stage2_sonnet`
(dicts com chaves fixas), `apply_decision(decision, window, user_id, session_id)->str`,
`evaluate_session(session_id, user_id, app=None)`, `try_enqueue_skill_effectiveness`/
`skill_effectiveness_job(session_id, user_id)`, inbox `list_pending_approvals()` /
`approve_item(kind,id,reviewer_user_id)` / `reject_item(...)` — nomes batem entre tasks e testes.

---

## Achados do code review final (pos-execucao, 2026-06-07)

Implementacao executada (subagent-driven, 16 commits + 1 fix). Code review final (Opus)
sobre `origin/main..HEAD`. Estado: **32 testes verdes**, flags default OFF.

**Corrigido:**
- **#2/#5 PII masking** — `_format_window` (input do LLM) e `_window_evidence` (persistido +
  exibido na inbox) agora aplicam `app/agente/utils/pii_masker.mask_pii` (CNPJ/CPF/email).
  Era deviacao do edge-case da spec. Commit `24b936d53` + 2 testes.

**Debitos / pre-requisitos de ATIVACAO (nao bloqueiam merge flag-off):**
- **#1 Teams = web-only (PRE-REQ p/ cobrir Teams).** `build_skill_windows` casa `"Skill:<nome>"`
  em `tools_used`, forma gravada SO na web (`chat.py:866`). O Teams grava o bare `"Skill"`
  (`teams/services.py:1294`), entao o gatilho (compartilhado via `run_post_session_processing`)
  roda mas produz zero janelas no Teams (best-effort segura — sem crash). Para cobrir Teams:
  enriquecer o tool_name no branch `tool_call` de `teams/services.py` (espelhar `chat.py:866`,
  nome em `metadata['input']['skill']`) — **export critico Teams: exige teste no Teams bot**
  (nao feito nesta sessao). Decidir na ativacao: enriquecer OU assumir web-only.
- **#4 error_signature NAO populado** — coluna existe (modelo+migration+badge inbox) mas
  `_evaluate_inner` nunca seta. NULL na Fase 1 (dedup do lembrete por `path` unico basta).
  Reservado p/ enriquecimento futuro (dedup por assunto cross-skill via `gerar_error_signature`).
- **#3 stage-2 side-effects sob double-trigger concorrente** — `apply_decision` commita antes do
  `_safe_persist`; `_apply_ajuste_codigo` (create_suggestion) nao e idempotente. Trigger e unico
  (RQ OU inline), entao prob. baixa. Aceito como debito.
- **Debito de teste** — testes de `evaluate_session`/inbox commitam no banco dev (a fixture `db`
  nao contem o `commit()` do service); mitigado com session_id/path unicos + cleanup.
- **UI (Task 13)** — sem teste automatizado; requer validacao manual (abrir `/agente/memorias`,
  aba "Pendentes de Aprovacao", aprovar shadow -> `ativa`, rejeitar dialogue -> `rejected`).

---

## Execution handoff

Plan completo e salvo em
`docs/superpowers/plans/2026-06-07-aprendizado-efetividade-skills-fase1.md` (worktree
`.claude/worktrees/agente-skill-efetividade`). Duas opcoes de execucao:

1. **Subagent-Driven (recomendado)** — um subagente fresco por task, com revisao
   entre tasks (two-stage review). Iteracao rapida; eu reviso cada task antes da proxima.
2. **Inline Execution** — executo as tasks nesta sessao (executing-plans), em lotes com
   checkpoints para sua revisao.

Qual abordagem?
