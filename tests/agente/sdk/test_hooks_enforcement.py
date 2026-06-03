"""Fase 3.5 do loop corretivo — HARD enforcement (PreToolUse) de invariantes formalizados.
- _enforce_decision: matching puro (substring case-insensitive do token EXPLICITO).
- _load_enforce_directives: so regras 'mandatory' com 'ENFORCE_DENY_SUBSTR:' viram invariante.
"""
import pytest
from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory
from app.agente.sdk import hooks as hooks_mod
from app.agente.sdk.hooks import _enforce_decision, _load_enforce_directives


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    user = Usuario.query.filter_by(email='test_enforce@test.com').first()
    if user:
        return user
    user = Usuario(email='test_enforce@test.com', nome='Test Enforce', perfil='agente', status='ativo')
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
    hooks_mod._ENFORCE_CACHE.clear()


# ───────────────────────── _enforce_decision (puro) ─────────────────────────

def test_enforce_decision_match_case_insensitive():
    directives = [('qtd_saldo', '/memories/corrections/campo.xml')]
    hit = _enforce_decision(directives, "SELECT QTD_SALDO FROM separacao")
    assert hit == ('qtd_saldo', '/memories/corrections/campo.xml')


def test_enforce_decision_sem_match():
    directives = [('qtd_saldo', '/x.xml')]
    assert _enforce_decision(directives, "SELECT qtd_saldo_produto_pedido FROM carteira") is None or \
        _enforce_decision(directives, "SELECT cod_produto FROM x") is None
    # discriminante: input sem o token -> None
    assert _enforce_decision(directives, "SELECT cod_produto FROM x") is None


def test_enforce_decision_diretivas_vazias():
    assert _enforce_decision([], "qualquer coisa") is None
    assert _enforce_decision(None, "qualquer coisa") is None
    assert _enforce_decision([('x', '/p')], "") is None


# ───────────────────────── _load_enforce_directives (DB) ─────────────────────────

def test_load_directives_so_mandatory_com_token(app, cleanup):
    """Regra mandatory com ENFORCE_DENY_SUBSTR vira invariante; contextual/sem-token nao."""
    ids, user_id = cleanup
    hooks_mod._ENFORCE_CACHE.clear()

    dura = AgentMemory.create_file(
        user_id, '/memories/corrections/inv-campo.xml',
        'NUNCA: usar coluna errada\nENFORCE_DENY_SUBSTR: qtd_saldo\nWHEN: query separacao')
    dura.priority = 'mandatory'
    db.session.commit()
    ids.append(dura.id)

    # regra mandatory SEM token -> nao vira invariante
    sem_token = AgentMemory.create_file(user_id, '/memories/corrections/inv-sem.xml', 'SEMPRE confirmar escopo')
    sem_token.priority = 'mandatory'
    db.session.commit()
    ids.append(sem_token.id)

    # regra com token mas contextual (nao dura) -> nao vira invariante
    contextual = AgentMemory.create_file(user_id, '/memories/corrections/inv-ctx.xml', 'ENFORCE_DENY_SUBSTR: foobar')
    contextual.priority = 'contextual'
    db.session.commit()
    ids.append(contextual.id)

    directives = _load_enforce_directives(user_id)
    tokens = [t for t, _ in directives]
    assert 'qtd_saldo' in tokens
    assert 'foobar' not in tokens  # contextual nao entra
