# tests/agente/test_skill_effectiveness.py
import importlib

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


# ---------------------------------------------------------------------------
# Task 3: Montagem da janela ancorada
# ---------------------------------------------------------------------------
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
