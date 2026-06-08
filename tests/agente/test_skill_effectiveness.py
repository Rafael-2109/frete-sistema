# tests/agente/test_skill_effectiveness.py
import importlib
import os

import pytest


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


# ---------------------------------------------------------------------------
# Task 2: Modelo AgentSkillEffectiveness
# ---------------------------------------------------------------------------
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
