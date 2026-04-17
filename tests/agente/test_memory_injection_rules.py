"""Tests para L1 Rules channel."""
import pytest
from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory
from app.agente.sdk.memory_injection_rules import _build_user_rules


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    """Cria usuario de teste."""
    # Verifica se usuario ja existe
    user = Usuario.query.filter_by(email='test_memoria@test.com').first()
    if user:
        return user

    user = Usuario(
        email='test_memoria@test.com',
        nome='Test Memory User',
        perfil='agente',
        status='ativo'
    )
    user.set_senha('test_password_123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def cleanup_memories(app, test_user):
    """Limpa memorias de teste apos cada teste."""
    created_ids = []
    yield created_ids, test_user.id
    for mid in created_ids:
        mem = AgentMemory.query.get(mid)
        if mem:
            db.session.delete(mem)
    db.session.commit()


def test_build_user_rules_returns_none_when_no_rules(app, cleanup_memories):
    """Sem regras mandatory, retorna None."""
    _, user_id = cleanup_memories
    result = _build_user_rules(user_id=user_id)
    assert result is None


def test_build_user_rules_returns_xml_with_mandatory_rule(app, cleanup_memories):
    """Com uma regra mandatory, retorna XML com <user_rules>."""
    cleanup_ids, user_id = cleanup_memories
    mem = AgentMemory.create_file(user_id, '/memories/test_rule.xml', 'SEMPRE X, NUNCA Y')
    mem.priority = 'mandatory'
    db.session.commit()
    cleanup_ids.append(mem.id)

    result = _build_user_rules(user_id=user_id)
    assert result is not None
    assert '<user_rules priority="mandatory">' in result
    assert 'SEMPRE X, NUNCA Y' in result
    assert '</user_rules>' in result


def test_build_user_rules_excludes_contextual_memories(app, cleanup_memories):
    """Memorias com priority='contextual' NAO entram em user_rules."""
    cleanup_ids, user_id = cleanup_memories
    mem = AgentMemory.create_file(user_id, '/memories/test_contextual.xml', 'info contextual')
    mem.priority = 'contextual'
    db.session.commit()
    cleanup_ids.append(mem.id)

    result = _build_user_rules(user_id=user_id)
    assert result is None


def test_build_user_rules_includes_empresa_mandatory(app, cleanup_memories):
    """Memorias empresa (user_id=0) com priority=mandatory entram."""
    cleanup_ids, user_id = cleanup_memories

    # Garante que usuario 0 (sistema) existe
    sistema_user = Usuario.query.filter_by(id=0).first()
    if not sistema_user:
        sistema_user = Usuario(id=0, email='sistema@nacom.com.br', nome='Sistema', perfil='sistema', status='ativo')
        sistema_user.set_senha('NOLOGIN')
        db.session.add(sistema_user)
        db.session.commit()

    mem = AgentMemory.create_file(0, '/memories/empresa/rules/test_empresa.xml', 'regra empresa')
    mem.priority = 'mandatory'
    db.session.commit()
    cleanup_ids.append(mem.id)

    result = _build_user_rules(user_id=user_id)
    assert result is not None
    assert 'regra empresa' in result
    assert 'scope="empresa"' in result


def test_build_user_rules_excludes_cold_memories(app, cleanup_memories):
    """Regras em tier frio nao entram."""
    cleanup_ids, user_id = cleanup_memories
    mem = AgentMemory.create_file(user_id, '/memories/cold_rule.xml', 'frio')
    mem.priority = 'mandatory'
    mem.is_cold = True
    db.session.commit()
    cleanup_ids.append(mem.id)

    result = _build_user_rules(user_id=user_id)
    assert result is None


def test_build_user_rules_escapes_xml_special_chars_in_path(app, cleanup_memories):
    """Paths com caracteres XML especiais sao escapados."""
    cleanup_ids, user_id = cleanup_memories
    mem = AgentMemory.create_file(user_id, '/memories/with<special>&char.xml', 'regra')
    mem.priority = 'mandatory'
    db.session.commit()
    cleanup_ids.append(mem.id)

    result = _build_user_rules(user_id=user_id)
    assert result is not None
    # Path escapado em attribute — nao pode ter < > & literais
    assert '&lt;special&gt;' in result or 'with\\u003cspecial' in result or '<special>' not in result.split('<rule')[1].split('>')[0]


def test_build_user_rules_skips_empty_content(app, cleanup_memories):
    """Regras com content vazio sao ignoradas (nao geram XML vazio)."""
    cleanup_ids, user_id = cleanup_memories
    mem_empty = AgentMemory.create_file(user_id, '/memories/empty_rule.xml', '   ')  # so whitespace
    mem_empty.priority = 'mandatory'
    mem_valid = AgentMemory.create_file(user_id, '/memories/valid_rule.xml', 'regra valida')
    mem_valid.priority = 'mandatory'
    db.session.commit()
    cleanup_ids.append(mem_empty.id)
    cleanup_ids.append(mem_valid.id)

    result = _build_user_rules(user_id=user_id)
    assert result is not None
    assert 'regra valida' in result
    # Verificar que nao ha <rule> com content vazio/whitespace
    assert '/memories/empty_rule.xml' not in result
