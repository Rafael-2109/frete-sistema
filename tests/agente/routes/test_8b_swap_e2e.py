"""8b passo 8: e2e do swap + interrupt por papel + caller do gate de metrica.

Prova ponta-a-ponta do handoff nos pontos que importam (a SDK subprocess em si e'
coberta pelas costuras dos passos 2-7):
  1. decisao de papel: frase de recebimento em 'on' -> especialista + persiste;
  2. save role-aware: sdk_session_id do especialista DISTINTO do principal ->
     chaves do PostgresSessionStore divergem -> SEM corrupcao de transcript;
  3. identidade trocada: _build_options do especialista usa prompt+skills proprios.
Flag default continua 'off' (este teste liga 'on' apenas no proprio escopo).
"""
import uuid
from unittest.mock import patch

from app import db
from app.agente.models import AgentSession
from app.agente.routes import chat as chat_mod
from app.agente.sdk import get_client
from app.agente.sdk.specialist_profiles import SPECIALIST_PROFILES


def _save(app, sid, sdk_uuid, role):
    with patch.object(chat_mod, 'run_post_session_processing', lambda **k: None):
        chat_mod._save_messages_to_db(
            app=app, our_session_id=sid, sdk_session_id=sdk_uuid, user_id=1,
            user_message='u', assistant_message='a', input_tokens=1, output_tokens=1,
            tools_used=[], model='claude-opus-4-8', session_expired=False,
            agent_role=role)


def test_e2e_swap_recebimento(app):
    sid = 't-e2e-swap'
    with app.app_context():
        AgentSession.query.filter_by(session_id=sid).delete()
        db.session.commit()
        db.session.add(AgentSession(session_id=sid, user_id=1, data={}))
        db.session.commit()

    # (1) Em 'on', a frase de recebimento entra no especialista e persiste o papel.
    # _resolve_agent_role consulta o DB -> exige app_context (a rota real fornece).
    with app.app_context():
        with patch.dict('os.environ', {'AGENT_SPECIALIST_HANDOFF': 'on'}, clear=False):
            role = chat_mod._resolve_agent_role(
                sid, "vincular o pedido C2615437 na nota 48862 pelo odoo", is_admin=False)
        assert role == 'gestor-recebimento'
        r = AgentSession.query.filter_by(session_id=sid).first()
        assert r.get_agente_ativo() == 'gestor-recebimento'

    # (2) save role-aware: sdk_session_id por papel -> chaves SessionStore distintas.
    u_principal, u_espec = str(uuid.uuid4()), str(uuid.uuid4())
    _save(app, sid, u_principal, 'principal')
    _save(app, sid, u_espec, 'gestor-recebimento')
    with app.app_context():
        r = AgentSession.query.filter_by(session_id=sid).first()
        assert r.get_sdk_session_id(role='principal') == u_principal
        assert r.get_sdk_session_id(role='gestor-recebimento') == u_espec
        assert u_principal != u_espec  # sem colisao na chave do store

    # (3) identidade trocada: prompt + skills do especialista != principal.
    client = get_client()
    opts_esp = client._build_options(
        specialist_profile=SPECIALIST_PROFILES['gestor-recebimento'])
    opts_pri = client._build_options()
    assert sorted(opts_esp.skills) != sorted(opts_pri.skills)
    assert 'Recebimento' in (opts_esp.system_prompt or '')

    with app.app_context():
        AgentSession.query.filter_by(session_id=sid).delete()
        db.session.commit()


def test_interrupt_usa_client_do_papel_ativo(app, monkeypatch):
    sid = 't-interrupt-role'
    with app.app_context():
        AgentSession.query.filter_by(session_id=sid).delete()
        db.session.commit()
        db.session.add(AgentSession(session_id=sid, user_id=1,
                                    data={'agente_ativo': 'gestor-recebimento'}))
        db.session.commit()

    captured = {}

    class _FakeClient:
        async def interrupt(self):
            return None

    class _FakePooled:
        connected = True
        client = _FakeClient()

    class _FakeFuture:
        def result(self, timeout=None):
            return None

    import app.agente.sdk.client_pool as cp

    def _fake_get(session_id, role='principal'):
        captured['role'] = role
        return _FakePooled()

    monkeypatch.setattr(cp, 'get_pooled_client', _fake_get)
    monkeypatch.setattr(cp, 'submit_coroutine', lambda coro, **k: _FakeFuture())

    resp = app.test_client().post('/agente/api/interrupt', json={'session_id': sid})
    assert resp.status_code == 200
    assert captured['role'] == 'gestor-recebimento'  # interrompeu o papel ATIVO

    with app.app_context():
        AgentSession.query.filter_by(session_id=sid).delete()
        db.session.commit()


def test_gate_handoff_caller_compoe_sem_explodir(app):
    with app.app_context():
        from app.agente.services.specialist_handoff_metrics import gate_handoff
        out = gate_handoff([], [])  # sem sessoes -> inerte, nunca propaga (R1)
        assert {'baseline', 'atual', 'gate'} <= set(out)
        assert out['gate']['passou_gate'] is False  # custo 0 nao < 0
