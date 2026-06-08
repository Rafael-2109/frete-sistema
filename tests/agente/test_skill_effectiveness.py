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
