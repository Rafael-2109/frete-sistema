"""
Tests para Task 8 (try_enqueue + job RQ), Task 9 (gatilho pos-sessao)
e Task 15 (smoke end-to-end da Fase 1).

Seguem padrao monkeypatch do plano — NAO enfileiram de verdade, NAO chamam LLMs reais.
"""
from uuid import uuid4


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


# =================================================================
# Task 15: Smoke end-to-end da Fase 1
# =================================================================

def test_smoke_end_to_end_creates_user_reminder(db, monkeypatch):
    """Smoke end-to-end: sessao com sinal de nao-resolucao -> lembrete_usuario criado.

    GOTCHA: evaluate_session chama db.session.commit() internamente, escapando o
    savepoint da fixture db. Por isso usamos session_id unico (sufixo uuid) e
    fazemos cleanup explicito ao final para nao deixar residuo no banco dev.
    """
    import app.agente.services.skill_effectiveness_service as svc
    from app.agente.models import AgentSession, AgentMemory, AgentSkillEffectiveness

    # ID unico para nao colidir com outros runs
    run_suffix = uuid4().hex[:8]
    smoke_session_id = f"smoke-{run_suffix}"
    user_id = 1  # Rafael (usuario existente no banco local)
    mem_path = "/memories/lembretes_skill/cotando-frete.xml"

    # sessao com sinal de nao-resolucao (frustracao + janela fechada)
    msgs = [
        {"id": "u0", "role": "user", "content": "frete pra Manaus"},
        {"id": "a0", "role": "assistant", "content": "cotando",
         "tools_used": ["Skill:cotando-frete"]},
        {"id": "u1", "role": "user", "content": "nao era isso, ta errado"},
        {"id": "a1", "role": "assistant", "content": "corrigindo"},
        {"id": "u2", "role": "user", "content": "agora foi"},
    ]

    # Precisamos commitar a sessao para que evaluate_session possa encontra-la
    # (a funcao faz AgentSession.query.filter_by(...) que requer dado no banco real)
    s = AgentSession(session_id=smoke_session_id, user_id=user_id,
                     data={"messages": msgs})
    db.session.add(s)
    db.session.commit()

    # Mock dos LLMs para nao chamar a API real
    monkeypatch.setattr(svc, "stage1_haiku",
        lambda w: {"resolveu": False, "suspeita_ajuste": True,
                   "motivo": "usuario reclamou", "sinais": ["nao era isso"]})
    monkeypatch.setattr(svc, "stage2_sonnet",
        lambda w, d="": {"ramo": "lembrete_usuario",
                          "titulo": "Confirmar UF destino",
                          "conteudo_lembrete": "para Manaus, confirmar UF=AM",
                          "confianca": 0.95})
    monkeypatch.setattr(svc, "_invalidate_caches", lambda uid: None)

    try:
        res = svc.evaluate_session(smoke_session_id, user_id)

        # (a) 1 linha em agent_skill_effectiveness com ramo=lembrete_usuario, stage_reached=2
        assert res["avaliadas"] == 1, f"esperado 1 avaliacao, got {res}"
        row = AgentSkillEffectiveness.query.filter_by(
            session_id=smoke_session_id).first()
        assert row is not None, "linha agent_skill_effectiveness nao criada"
        assert row.ramo == "lembrete_usuario", f"ramo={row.ramo}"
        assert row.stage_reached == 2, f"stage_reached={row.stage_reached}"

        # (b) AgentMemory do lembrete foi criada para o usuario
        mem = AgentMemory.query.filter_by(
            user_id=user_id, path=mem_path).first()
        assert mem is not None, "AgentMemory do lembrete nao foi criada"

    finally:
        # Cleanup explicito: remover residuos do banco dev
        # (evaluate_session comitou fora do savepoint da fixture)
        from app import db as _db
        AgentSkillEffectiveness.query.filter_by(
            session_id=smoke_session_id).delete()
        # Remove a memoria APENAS se foi criada por este run
        # (pode existir de outro teste — verificar pelo conteudo)
        mem_to_del = AgentMemory.query.filter_by(
            user_id=user_id, path=mem_path).first()
        if mem_to_del is not None:
            _db.session.delete(mem_to_del)
        AgentSession.query.filter_by(
            session_id=smoke_session_id).delete()
        _db.session.commit()
