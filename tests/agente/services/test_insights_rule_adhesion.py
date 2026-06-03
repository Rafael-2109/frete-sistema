"""Fase 3.7 do loop corretivo — painel "adesao de regras" (insights_service).
Reincidencia por error_signature ANTES (correction_count) vs DEPOIS (harmful_count) da promocao."""
import pytest
from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory
from app.agente.services.insights_service import (
    get_rule_adhesion_panel,
    _get_rule_adhesion_section,
)


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    user = Usuario.query.filter_by(email='test_adhesion@test.com').first()
    if user:
        return user
    user = Usuario(email='test_adhesion@test.com', nome='Test Adhesion', perfil='agente', status='ativo')
    user.set_senha('test_password_123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def cleanup(app, test_user):
    ids = []
    yield ids, test_user.id
    try:
        db.session.rollback()
    except Exception:
        pass
    for mid in ids:
        m = AgentMemory.query.get(mid)
        if m:
            db.session.delete(m)
    db.session.commit()


def _mk(user_id, path, *, priority='contextual', cc=0, sig=None, harmful=0):
    mem = AgentMemory.create_file(user_id, path, f'[correcao] x\nDO: y')
    mem.priority = priority
    mem.correction_count = cc
    mem.error_signature = sig
    mem.harmful_count = harmful
    db.session.commit()
    return mem


def test_panel_agrega_total_mandatory_e_assinatura(app, cleanup):
    ids, user_id = cleanup
    # regra dura promovida: reincidiu 9x no total, mas so 1x depois de virar dura (loop funcionando)
    m1 = _mk(user_id, '/memories/corrections/ad1.xml', priority='mandatory', cc=9,
             sig='troca_de_escopo', harmful=1)
    ids.append(m1.id)
    # correcao contextual (nao promovida)
    m2 = _mk(user_id, '/memories/corrections/ad2.xml', priority='contextual', cc=1,
             sig='data_formato', harmful=0)
    ids.append(m2.id)

    data = get_rule_adhesion_panel(days=30, user_id=user_id)
    assert data['total_corrections'] == 2
    assert data['mandatory_count'] == 1
    assert data['mandatory_pct'] == 50.0
    assert data['outcome']['available'] is True
    assert data['outcome']['harmful_total'] == 1

    sigs = {r['error_signature']: r for r in data['top_by_signature']}
    assert sigs['troca_de_escopo']['reincidencia_total'] == 9        # ANTES
    assert sigs['troca_de_escopo']['reincidencia_pos_promocao'] == 1  # DEPOIS
    assert sigs['troca_de_escopo']['promovida'] is True


def test_section_flag_off_retorna_vazio(app, cleanup, monkeypatch):
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_CORRECTION_PROMOTION', False)
    assert _get_rule_adhesion_section(days=30) == {}


def test_panel_degrada_se_coluna_ausente(app, cleanup, monkeypatch):
    """Rollout dual: se a query de outcome falha (coluna Fase 3.1 ausente), outcome.available=False.
    Mira sqlalchemy.text (usado SO na query raw de outcome) — o .count() do ORM segue intacto."""
    ids, user_id = cleanup
    m = _mk(user_id, '/memories/corrections/ad3.xml', priority='mandatory', cc=3, sig='s')
    ids.append(m.id)

    def _boom(*a, **k):
        raise Exception("column error_signature does not exist")
    monkeypatch.setattr('sqlalchemy.text', _boom)

    data = get_rule_adhesion_panel(days=30, user_id=user_id)
    # agregados por path/priority ainda funcionam (usam .count() do ORM, nao text())
    assert data['total_corrections'] >= 1
    assert data['outcome']['available'] is False
