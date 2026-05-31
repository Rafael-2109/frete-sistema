"""
Tests for AgentStep model — Onda 0 Task 1 (S0a.1).

Testa: insert_step (básico, idempotência por step_uid, não-poisona sessão).

step_uid gerado via uuid em cada teste para isolar runs (evita falso-negativo
caso o banco de teste persista linhas entre execuções).
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


def test_insert_step_basico(app_ctx):
    """Insere um step básico e verifica id + step_uid."""
    from app.agente.models import AgentStep

    uid = f'test-basico:{uuid.uuid4().hex[:8]}'
    step = AgentStep.insert_step(
        step_uid=uid,
        session_id='test-session-basico',
        user_id=1,
        channel='web',
        model='claude-opus-4-8',
        input_tokens=100,
        output_tokens=50,
        tools_used=['Bash'],
    )

    assert step is not None
    assert step.id is not None
    assert step.step_uid == uid

    _db.session.rollback()


def test_insert_step_idempotente_por_step_uid(app_ctx):
    """Segunda inserção com mesmo step_uid retorna None (UNIQUE constraint)."""
    from app.agente.models import AgentStep

    # MESMO uid para as 2 inserções (testa a UNIQUE constraint)
    uid = f'test-idempotente:{uuid.uuid4().hex[:8]}'

    step1 = AgentStep.insert_step(
        step_uid=uid,
        session_id='test-session-idempotente',
        input_tokens=10,
        output_tokens=5,
    )
    assert step1 is not None

    step2 = AgentStep.insert_step(
        step_uid=uid,
        session_id='test-session-idempotente',
        input_tokens=10,
        output_tokens=5,
    )
    assert step2 is None

    _db.session.rollback()


def test_insert_step_falha_nao_poisona_sessao(app_ctx):
    """
    Após falha de UNIQUE (retorna None via savepoint), a sessão
    continua utilizável — insere step_uid diferente com sucesso.
    Nenhum rollback manual é necessário pelo caller.
    """
    from app.agente.models import AgentStep

    token = uuid.uuid4().hex[:8]
    # MESMO uid_dup nas 2 primeiras inserções (força o IntegrityError);
    # uid_novo distinto para provar que a sessão segue usável depois.
    uid_dup = f'test-nao-poisona:{token}'
    uid_novo = f'test-nao-poisona-novo:{token}'

    # Inserção inicial
    step_a = AgentStep.insert_step(step_uid=uid_dup, input_tokens=5, output_tokens=2)
    assert step_a is not None

    # Inserção duplicada — retorna None, savepoint rollback'd internamente
    step_dup = AgentStep.insert_step(step_uid=uid_dup, input_tokens=5, output_tokens=2)
    assert step_dup is None

    # SEM rollback manual — sessão deve continuar usável
    step_b = AgentStep.insert_step(step_uid=uid_novo, input_tokens=8, output_tokens=3)
    assert step_b is not None
    assert step_b.step_uid == uid_novo

    _db.session.rollback()
