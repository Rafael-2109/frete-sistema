"""Testes para endpoints novos de subagent UI (Fase 1 + Fase 2).

Spec: docs/superpowers/specs/2026-05-14-subagent-ui-enrichment-design.md (5.1)

Fase 1: POST /pii-toggle, GET /transcript
Fase 2: PATCH /subagents/<aid>, GET /output_file

Fixtures `as_admin` e `as_user` fazem monkeypatch direto de current_user
para bypass de LOGIN_DISABLED=True em tests/conftest.py (code-review #3).
"""
import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm.attributes import flag_modified

from app import db
from app.agente.models import AgentSession
from app.auth.models import Usuario


# ─── Fixtures ───

@pytest.fixture
def admin_user(app):
    """Usuario admin para testes — code-review #3."""
    with app.app_context():
        # Usar email unico para evitar colisao
        email = 'admin-subagent-test@t.local'
        u = Usuario.query.filter_by(email=email).first()
        if u is None:
            u = Usuario(
                nome='Admin SubAg Test',
                email=email,
                perfil='administrador',
                status='ativo',
            )
            u.set_senha('test123')
            db.session.add(u)
            db.session.commit()
        yield u
        # Cleanup
        try:
            db.session.delete(u)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def normal_user(app):
    with app.app_context():
        email = 'user-subagent-test@t.local'
        u = Usuario.query.filter_by(email=email).first()
        if u is None:
            u = Usuario(
                nome='User SubAg Test',
                email=email,
                perfil='operador',
                status='ativo',
            )
            u.set_senha('test123')
            db.session.add(u)
            db.session.commit()
        yield u
        try:
            db.session.delete(u)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def session_owned_by_normal(app, normal_user):
    """AgentSession pertencente ao normal_user."""
    with app.app_context():
        sid = 'a' * 32
        # Cleanup if exists
        AgentSession.query.filter_by(session_id=sid).delete()
        db.session.commit()
        s = AgentSession(
            session_id=sid,
            user_id=normal_user.id,
            data={},
        )
        db.session.add(s)
        db.session.commit()
        yield s
        try:
            db.session.delete(s)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def session_owned_by_admin(app, admin_user):
    """AgentSession pertencente ao admin_user."""
    with app.app_context():
        sid = 'c' * 32
        AgentSession.query.filter_by(session_id=sid).delete()
        db.session.commit()
        s = AgentSession(
            session_id=sid,
            user_id=admin_user.id,
            data={},
        )
        db.session.add(s)
        db.session.commit()
        yield s
        try:
            db.session.delete(s)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def redis_client():
    """Fixture concreta — code-review #4. Limpa chaves test pos-teste."""
    from app.utils.redis_cache import redis_cache
    rc = getattr(redis_cache, 'client', None)
    if rc is None:
        pytest.skip("Redis indisponivel — fixture redis_client nao consegue conectar")
    yield rc
    # Cleanup chaves test
    try:
        for prefix in ['agent:pii_toggle_rate:', 'agent:pii_unmask:',
                       'agent:metrics:subagent_modal']:
            for key in rc.scan_iter(f'{prefix}*'):
                rc.delete(key)
    except Exception:
        pass


@pytest.fixture
def as_admin(monkeypatch, admin_user, app):
    """Bypass de LOGIN_DISABLED=True. Forca current_user=admin_user no module."""
    monkeypatch.setattr('app.agente.routes.subagents.current_user', admin_user)
    return admin_user


@pytest.fixture
def as_user(monkeypatch, normal_user, app):
    """Idem, mas user normal."""
    monkeypatch.setattr('app.agente.routes.subagents.current_user', normal_user)
    return normal_user


# ============================================================
# POST /pii-toggle (Fase 1)
# ============================================================

def test_pii_toggle_403_non_admin(client, as_user, session_owned_by_normal):
    """Non-admin nao pode togglear PII."""
    r = client.post(
        f'/agente/api/sessions/{session_owned_by_normal.session_id}/subagents/{"b"*32}/pii-toggle',
        json={'enabled': True},
    )
    assert r.status_code == 403


def test_pii_toggle_404_se_flag_off(client, as_admin, session_owned_by_normal, monkeypatch):
    """Flag OFF retorna 404."""
    monkeypatch.setattr('app.agente.config.feature_flags.USE_SUBAGENT_MODAL', False)
    r = client.post(
        f'/agente/api/sessions/{session_owned_by_normal.session_id}/subagents/{"b"*32}/pii-toggle',
        json={'enabled': True},
    )
    assert r.status_code == 404


def test_pii_toggle_admin_registra_audit_log(client, as_admin, session_owned_by_normal, app, redis_client):
    """Toggle persiste audit em agent_sessions.data['subagent_pii_audit']."""
    r = client.post(
        f'/agente/api/sessions/{session_owned_by_normal.session_id}/subagents/{"b"*32}/pii-toggle',
        json={'enabled': True},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    payload = r.get_json()
    assert payload['success'] is True
    assert payload.get('expires_in') == 300

    with app.app_context():
        sess = AgentSession.query.filter_by(session_id=session_owned_by_normal.session_id).first()
        audit = sess.data.get('subagent_pii_audit', [])
        assert len(audit) >= 1
        last = audit[-1]
        assert last['enabled'] is True
        assert last['user_id'] == as_admin.id
        assert last['agent_id'] == 'b' * 32


# ============================================================
# GET /transcript (Fase 1)
# ============================================================

def test_transcript_404_flag_off(client, as_user, session_owned_by_normal, monkeypatch):
    monkeypatch.setattr('app.agente.config.feature_flags.USE_SUBAGENT_MODAL', False)
    r = client.get(
        f'/agente/api/sessions/{session_owned_by_normal.session_id}/subagents/{"b"*32}/transcript'
    )
    assert r.status_code == 404


def test_transcript_403_cross_user(client, as_user, session_owned_by_admin):
    """User normal nao pode ver sessao de outro user."""
    r = client.get(
        f'/agente/api/sessions/{session_owned_by_admin.session_id}/subagents/{"b"*32}/transcript'
    )
    assert r.status_code == 403


def test_transcript_dono_pii_mascarada(client, as_user, session_owned_by_normal, monkeypatch):
    """Dono non-admin: PII vem mascarada por default."""
    fake_entry = MagicMock()
    fake_entry.to_dict.return_value = {
        'sequence': 1,
        'kind': 'user_prompt',
        'timestamp': None,
        'content': 'CPF ***.***.***-**',
        'tool_use_id': None,
    }
    monkeypatch.setattr(
        'app.agente.routes.subagents.get_subagent_transcript',
        lambda sid, aid, include_pii=False, **kw: [fake_entry]
    )
    r = client.get(
        f'/agente/api/sessions/{session_owned_by_normal.session_id}/subagents/{"b"*32}/transcript'
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    transcript = r.get_json()['transcript']
    assert '***' in transcript[0]['content']
    assert '123.456.789' not in transcript[0]['content']


def test_transcript_admin_com_token_redis_raw(client, as_admin, session_owned_by_admin, monkeypatch, redis_client):
    """Admin com Redis token agent:pii_unmask:* valido recebe PII raw."""
    sid = session_owned_by_admin.session_id
    aid = 'b' * 32
    # Simula token Redis presente
    redis_client.setex(f'agent:pii_unmask:{as_admin.id}:{sid}:{aid}', 300, '1')

    fake_entry = MagicMock()
    fake_entry.to_dict.return_value = {
        'sequence': 1,
        'kind': 'user_prompt',
        'timestamp': None,
        'content': 'CPF 123.456.789-00',
        'tool_use_id': None,
    }
    monkeypatch.setattr(
        'app.agente.routes.subagents.get_subagent_transcript',
        lambda sid_arg, aid_arg, include_pii=False, **kw: (
            [fake_entry] if include_pii else []
        )
    )
    r = client.get(f'/agente/api/sessions/{sid}/subagents/{aid}/transcript')
    assert r.status_code == 200, r.get_data(as_text=True)
    payload = r.get_json()
    assert payload['include_pii'] is True
    assert '123.456.789-00' in payload['transcript'][0]['content']


def test_transcript_404_se_vazio(client, as_user, session_owned_by_normal, monkeypatch):
    """Transcript vazio = 404 com mensagem clara."""
    monkeypatch.setattr(
        'app.agente.routes.subagents.get_subagent_transcript',
        lambda sid, aid, include_pii=False, **kw: []
    )
    r = client.get(
        f'/agente/api/sessions/{session_owned_by_normal.session_id}/subagents/{"b"*32}/transcript'
    )
    assert r.status_code == 404
    assert 'arquivada' in r.get_data(as_text=True).lower() or 'transcript' in r.get_data(as_text=True).lower()
