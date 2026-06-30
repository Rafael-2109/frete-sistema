"""8b passo 3: save/resume role-aware em chat.py.

_save_messages_to_db grava o sdk_session_id NO PAPEL do turno (agent_role,
carregado em response_state). Sem isso, o turno do especialista sobrescreveria o
sdk_session_id do principal -> ambos resumiriam a mesma sessao SDK -> colisao na
chave do PostgresSessionStore. O caminho 'principal' (default) permanece
identico e espelha o slot legado.
"""
import uuid
from unittest.mock import patch

from app import db
from app.agente.models import AgentSession
from app.agente.routes import chat as chat_mod


def _call_save(app, sid, sdk_uuid, role):
    with patch.object(chat_mod, 'run_post_session_processing', lambda **k: None):
        return chat_mod._save_messages_to_db(
            app=app, our_session_id=sid, sdk_session_id=sdk_uuid,
            user_id=1, user_message='u', assistant_message='a',
            input_tokens=1, output_tokens=1, tools_used=[],
            model='claude-opus-4-8', session_expired=False,
            agent_role=role,
        )


def _cleanup(sid):
    AgentSession.query.filter_by(session_id=sid).delete()
    db.session.commit()


def test_save_grava_sdk_session_id_no_papel_especialista(app):
    sid = 't-save-role-1'
    sdk_uuid = str(uuid.uuid4())
    ok = _call_save(app, sid, sdk_uuid, 'gestor-recebimento')
    assert ok is True
    with app.app_context():
        r = AgentSession.query.filter_by(session_id=sid).first()
        assert r.get_sdk_session_id(role='gestor-recebimento') == sdk_uuid
        # Papel principal intocado -> sem colisao no SessionStore.
        assert r.get_sdk_session_id(role='principal') is None
        assert r.data.get('sdk_session_id') is None  # slot legado nao poluido
        _cleanup(sid)


def test_save_principal_default_grava_slot_principal_e_legado(app):
    sid = 't-save-role-2'
    sdk_uuid = str(uuid.uuid4())
    ok = _call_save(app, sid, sdk_uuid, 'principal')
    assert ok is True
    with app.app_context():
        r = AgentSession.query.filter_by(session_id=sid).first()
        assert r.get_sdk_session_id(role='principal') == sdk_uuid
        assert r.data.get('sdk_session_id') == sdk_uuid  # espelho legado
        _cleanup(sid)


def test_async_stream_resume_le_papel():
    """O resume-load em _async_stream_sdk_client deve consultar get_sdk_session_id
    com role=agent_role (e nao o slot fixo)."""
    import inspect
    src = inspect.getsource(chat_mod._async_stream_sdk_client)
    assert 'get_sdk_session_id(role=agent_role)' in src


def test_response_state_carrega_agent_role():
    """response_state propaga agent_role para o save dedup."""
    import inspect
    src = inspect.getsource(chat_mod._stream_chat_response)
    assert "'agent_role': agent_role" in src
