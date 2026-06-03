"""Fase 3.4 do loop corretivo — testes de:
- _composite_score (3.4B): recorrencia no ranking, flag-gated (OFF = formula historica).
- posicao de <user_rules> (3.4A): regras duras no TOPO ABSOLUTO (antes de <user_memories>),
  com toggle da flag USE_USER_RULES_TOP.
"""
import pytest
from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentMemory
from app.agente.sdk.memory_injection import _composite_score, _load_user_memories_for_context


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def test_user(app):
    user = Usuario.query.filter_by(email='test_memoria_fase3@test.com').first()
    if user:
        return user
    user = Usuario(
        email='test_memoria_fase3@test.com',
        nome='Test Memory Fase3',
        perfil='agente',
        status='ativo',
    )
    user.set_senha('test_password_123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def cleanup_memories(app, test_user):
    created_ids = []
    yield created_ids, test_user.id
    for mid in created_ids:
        mem = AgentMemory.query.get(mid)
        if mem:
            db.session.delete(mem)
    db.session.commit()


# ───────────────────────── 3.4B: _composite_score ─────────────────────────

def test_composite_score_flag_off_preserva_formula_historica(monkeypatch):
    """Flag OFF: formula historica EXATA (0.3 decay + 0.3 imp + 0.4 sim)."""
    monkeypatch.setattr('app.agente.config.feature_flags.USE_RECURRENCE_SCORE', False)
    val = _composite_score(decay=1.0, importance=1.0, similarity=1.0, correction_count=9)
    assert val == pytest.approx(0.3 * 1.0 + 0.3 * 1.0 + 0.4 * 1.0)  # recorrencia ignorada


def test_composite_score_flag_off_fallback_sem_similaridade(monkeypatch):
    """Flag OFF, sem similaridade: 0.3 decay + 0.7 imp."""
    monkeypatch.setattr('app.agente.config.feature_flags.USE_RECURRENCE_SCORE', False)
    val = _composite_score(decay=1.0, importance=1.0, similarity=None, correction_count=9)
    assert val == pytest.approx(0.3 + 0.7)


def test_composite_score_flag_on_recorrencia_eleva_score(monkeypatch):
    """Flag ON: maior correction_count -> maior composite (regra reincidente sobe)."""
    monkeypatch.setattr('app.agente.config.feature_flags.USE_RECURRENCE_SCORE', True)
    baixa = _composite_score(decay=0.5, importance=0.5, similarity=0.5, correction_count=0)
    alta = _composite_score(decay=0.5, importance=0.5, similarity=0.5, correction_count=10)
    assert alta > baixa
    # recorrencia = min(10,10)/10 = 1.0; peso 0.15
    assert alta == pytest.approx(0.25 * 0.5 + 0.25 * 0.5 + 0.35 * 0.5 + 0.15 * 1.0)


def test_composite_score_flag_on_cap_em_10(monkeypatch):
    """Flag ON: correction_count satura em 10 (cap) — 15 == 10."""
    monkeypatch.setattr('app.agente.config.feature_flags.USE_RECURRENCE_SCORE', True)
    cc10 = _composite_score(decay=0.5, importance=0.5, similarity=0.5, correction_count=10)
    cc15 = _composite_score(decay=0.5, importance=0.5, similarity=0.5, correction_count=15)
    assert cc10 == pytest.approx(cc15)


# ───────────────────────── 3.4A: posicao <user_rules> ─────────────────────────

def _seed_regra_e_preferencia(cleanup_ids, user_id):
    """Cria 1 regra mandatory + 1 preferencia protegida (tier1, sempre injetada)."""
    regra = AgentMemory.create_file(user_id, '/memories/fase3_rule.xml', 'SEMPRE confirmar escopo antes de agir')
    regra.priority = 'mandatory'
    db.session.commit()
    cleanup_ids.append(regra.id)
    pref = AgentMemory.get_by_path(user_id, '/memories/preferences.xml')
    if pref is None:
        pref = AgentMemory.create_file(user_id, '/memories/preferences.xml', 'prefere relatorios planos')
        db.session.commit()
        cleanup_ids.append(pref.id)
    return regra, pref


def test_user_rules_no_topo_antes_de_user_memories(app, cleanup_memories, monkeypatch):
    """Flag ON (default): <user_rules> aparece ANTES de <user_memories> (topo absoluto)."""
    monkeypatch.setattr('app.agente.config.feature_flags.USE_USER_RULES_CHANNEL', True)
    monkeypatch.setattr('app.agente.config.feature_flags.USE_USER_RULES_TOP', True)
    cleanup_ids, user_id = cleanup_memories
    _seed_regra_e_preferencia(cleanup_ids, user_id)

    result, _ids = _load_user_memories_for_context(user_id=user_id)
    assert result is not None
    assert '<user_rules' in result
    assert '<user_memories>' in result
    assert result.index('<user_rules') < result.index('<user_memories>')


def test_user_rules_legado_na_cauda_quando_flag_off(app, cleanup_memories, monkeypatch):
    """Flag USE_USER_RULES_TOP OFF: comportamento legado — regras na CAUDA (apos </user_memories>)."""
    monkeypatch.setattr('app.agente.config.feature_flags.USE_USER_RULES_CHANNEL', True)
    monkeypatch.setattr('app.agente.config.feature_flags.USE_USER_RULES_TOP', False)
    cleanup_ids, user_id = cleanup_memories
    _seed_regra_e_preferencia(cleanup_ids, user_id)

    result, _ids = _load_user_memories_for_context(user_id=user_id)
    assert result is not None
    assert '<user_rules' in result
    # legado: regras vem DEPOIS do fechamento de <user_memories>
    assert result.index('</user_memories>') < result.index('<user_rules')
