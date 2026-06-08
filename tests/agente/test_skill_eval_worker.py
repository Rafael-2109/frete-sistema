"""
Tests para Task 8 (try_enqueue + job RQ) e Task 9 (gatilho pos-sessao).

Seguem padrao monkeypatch do plano — NAO enfileiram de verdade.
"""


# =================================================================
# Task 8: job RQ + try_enqueue
# =================================================================

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


# =================================================================
# Task 9: gatilho em run_post_session_processing
# =================================================================

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
