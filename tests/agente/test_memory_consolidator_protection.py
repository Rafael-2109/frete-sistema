"""Tests: memorias priority=mandatory ou effective_count>=50 nao viram cold."""
import pytest
from app import db
from app.agente.models import AgentMemory
from app.agente.services.memory_consolidator import maybe_move_to_cold
from app.auth.models import Usuario


@pytest.fixture(scope='module')
def test_user(app):
    """Cria usuario de teste (module scope)."""
    with app.app_context():
        user = Usuario.query.get(99998)
        if not user:
            user = Usuario(
                id=99998,
                email='test-memory-protection@test.local',
                nome='Test User',
                senha_hash='dummy_hash_for_test'  # Required field
            )
            db.session.add(user)
            db.session.commit()
        return user


@pytest.fixture
def cleanup_memories(db):
    """Limpa memorias de teste criadas."""
    created_ids = []
    yield created_ids
    for mid in created_ids:
        mem = AgentMemory.query.get(mid)
        if mem:
            db.session.delete(mem)
    db.session.commit()


def test_mandatory_memory_not_moved_to_cold(db, test_user, cleanup_memories):
    """Memoria mandatory com eficacia baixa NAO deve ir para cold."""
    mem = AgentMemory.create_file(99998, '/memories/_test_mandatory_cold.xml', 'regra mandatory')
    mem.priority = 'mandatory'
    mem.usage_count = 50  # acima do threshold MIN_USAGE
    mem.effective_count = 2  # eficacia ~4% (normalmente iria cold)
    mem.is_cold = False
    db.session.commit()
    cleanup_memories.append(mem.id)

    maybe_move_to_cold(99998)

    reloaded = AgentMemory.query.get(mem.id)
    assert reloaded.is_cold is False, "Mandatory nao deve virar cold mesmo com baixa eficacia"


def test_high_effective_count_not_moved_to_cold(db, test_user, cleanup_memories):
    """Memoria contextual com effective_count>=50 NAO deve ir para cold."""
    mem = AgentMemory.create_file(99998, '/memories/_test_effective_cold.xml', 'util comprovado')
    mem.priority = 'contextual'
    mem.usage_count = 200
    mem.effective_count = 55  # acima do threshold de proteção
    mem.is_cold = False
    db.session.commit()
    cleanup_memories.append(mem.id)

    maybe_move_to_cold(99998)

    reloaded = AgentMemory.query.get(mem.id)
    assert reloaded.is_cold is False, "effective_count>=50 nao deve virar cold"


def test_contextual_low_effective_moves_to_cold(db, test_user, cleanup_memories):
    """Memoria contextual com baixa eficacia — comportamento original preservado."""
    mem = AgentMemory.create_file(99998, '/memories/_test_contextual_cold.xml', 'pouco util')
    mem.priority = 'contextual'
    mem.usage_count = 50
    mem.effective_count = 2  # eficacia ~4% (deve ir para cold)
    mem.is_cold = False
    db.session.commit()
    cleanup_memories.append(mem.id)

    maybe_move_to_cold(99998)

    reloaded = AgentMemory.query.get(mem.id)
    assert reloaded.is_cold is True, "Contextual ineficaz DEVE ir para cold"
