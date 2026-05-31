"""
Tests for AgentStep.update_outcome — Onda 1 / E1 (Task 3).

Testa:
- merge de 2 patches acumula keys (idempotente no campo, aditivo entre patches)
- step inexistente retorna None sem exception
- effective_count é atualizado quando fornecido
- flag_modified obrigatório (mutação in-place de JSON não detectada pelo ORM)

Espelha setup de test_agent_step.py: módulo-escopo app_ctx + rollback no fim.
step_uid via uuid para isolar runs.
"""
import uuid
import pytest
from app import create_app, db as _db


@pytest.fixture(scope='module')
def app_ctx():
    """Flask app context para testes de modelo (escopo de módulo)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


def test_update_outcome_merge_dois_patches(app_ctx):
    """Dois patches consecutivos acumulam keys em outcome_signal (merge aditivo)."""
    from app.agente.models import AgentStep

    uid = f'test-outcome-merge:{uuid.uuid4().hex[:8]}'
    step = AgentStep.insert_step(
        step_uid=uid,
        session_id='test-session-outcome',
        user_id=1,
        channel='web',
        model='claude-opus-4-8',
        input_tokens=100,
        output_tokens=50,
    )
    assert step is not None
    assert step.outcome_signal is None  # virgem antes de qualquer patch

    # Patch 1: frustration_score
    AgentStep.update_outcome(uid, {'frustration_score': 5})
    _db.session.expire(step)  # força reload do banco
    step = AgentStep.query.filter_by(step_uid=uid).first()
    assert step.outcome_signal == {'frustration_score': 5}

    # Patch 2: feedback — DEVE acumular, não sobrescrever
    AgentStep.update_outcome(uid, {'feedback': 'negative'})
    _db.session.expire(step)
    step = AgentStep.query.filter_by(step_uid=uid).first()
    assert step.outcome_signal == {'frustration_score': 5, 'feedback': 'negative'}

    _db.session.rollback()


def test_update_outcome_step_inexistente_retorna_none(app_ctx):
    """step_uid inexistente -> retorna None sem exception (no-op seguro)."""
    from app.agente.models import AgentStep

    uid_fantasma = f'test-outcome-ghost:{uuid.uuid4().hex[:8]}'
    result = AgentStep.update_outcome(uid_fantasma, {'frustration_score': 7})
    assert result is None

    _db.session.rollback()


def test_update_outcome_effective_count(app_ctx):
    """effective_count é atualizado quando fornecido junto com signal_patch."""
    from app.agente.models import AgentStep

    uid = f'test-outcome-count:{uuid.uuid4().hex[:8]}'
    AgentStep.insert_step(
        step_uid=uid,
        session_id='test-session-outcome-count',
        input_tokens=10,
        output_tokens=5,
    )

    AgentStep.update_outcome(uid, {'feedback': 'positive'}, effective_count=3)
    step = AgentStep.query.filter_by(step_uid=uid).first()
    assert step.outcome_signal == {'feedback': 'positive'}
    assert step.outcome_effective_count == 3

    _db.session.rollback()


def test_update_outcome_patch_vazio_nao_quebra(app_ctx):
    """Patch vazio ou None não quebra o step existente."""
    from app.agente.models import AgentStep

    uid = f'test-outcome-empty:{uuid.uuid4().hex[:8]}'
    AgentStep.insert_step(
        step_uid=uid,
        session_id='test-session-outcome-empty',
        input_tokens=10,
        output_tokens=5,
    )

    result = AgentStep.update_outcome(uid, {})
    assert result is not None  # retorna o step mesmo com patch vazio

    result2 = AgentStep.update_outcome(uid, None)
    assert result2 is not None  # None também é seguro

    _db.session.rollback()
