"""
Tests for AgentEvalScore model — A3 Fase 1, sub-task 3a (baseline de eval).

Testa:
- insert_score cria linha com campos corretos
- get_baseline_score retorna None sem runs prévios
- get_baseline_score retorna o score do run MAIS RECENTE quando há múltiplos
- insert_score em erro não propaga (SAVEPOINT isola) — best-effort

Espelha setup de test_agent_step.py: módulo-escopo app_ctx + rollback no fim.
agent_name via uuid para isolar runs (evita falso-negativo caso o banco de
teste persista linhas entre execuções).
"""
import uuid
import pytest
from app import create_app, db as _db
from app.utils.timezone import agora_utc_naive


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


def test_insert_score_cria_linha_campos_corretos(app_ctx):
    """Insere um score e verifica id + todos os campos."""
    from app.agente.models import AgentEvalScore

    agent_name = f'test-agent-insert:{uuid.uuid4().hex[:8]}'
    score = AgentEvalScore.insert_score(
        agent_name=agent_name,
        score=0.85,
        total=20,
        passed=17,
        git_sha='abc123def',
        mode='report_only',
    )

    assert score is not None
    assert score.id is not None
    assert score.agent_name == agent_name
    assert score.score == 0.85
    assert score.total == 20
    assert score.passed == 17
    assert score.git_sha == 'abc123def'
    assert score.mode == 'report_only'
    assert score.recorded_at is not None

    _db.session.rollback()


def test_get_baseline_score_none_sem_runs_previos(app_ctx):
    """Sem nenhum run prévio para o agent_name -> retorna None."""
    from app.agente.models import AgentEvalScore

    agent_name = f'test-agent-ghost:{uuid.uuid4().hex[:8]}'
    baseline = AgentEvalScore.get_baseline_score(agent_name)
    assert baseline is None

    _db.session.rollback()


def test_get_baseline_score_retorna_run_mais_recente(app_ctx):
    """
    Com múltiplos runs, get_baseline_score retorna o score do run com
    recorded_at MAIS RECENTE (ORDER BY recorded_at DESC LIMIT 1).
    """
    from app.agente.models import AgentEvalScore
    from datetime import timedelta

    agent_name = f'test-agent-multi:{uuid.uuid4().hex[:8]}'
    base_ts = agora_utc_naive()

    # Run antigo (score 0.50)
    antigo = AgentEvalScore.insert_score(
        agent_name=agent_name, score=0.50, total=10, passed=5,
    )
    antigo.recorded_at = base_ts - timedelta(hours=2)

    # Run intermediário (score 0.70)
    meio = AgentEvalScore.insert_score(
        agent_name=agent_name, score=0.70, total=10, passed=7,
    )
    meio.recorded_at = base_ts - timedelta(hours=1)

    # Run mais recente (score 0.90) — este é o baseline esperado
    recente = AgentEvalScore.insert_score(
        agent_name=agent_name, score=0.90, total=10, passed=9,
    )
    recente.recorded_at = base_ts
    _db.session.flush()

    baseline = AgentEvalScore.get_baseline_score(agent_name)
    assert baseline == 0.90

    _db.session.rollback()


def test_insert_score_erro_nao_propaga(app_ctx):
    """
    insert_score com argumento inválido (NOT NULL violado) não propaga
    exception — retorna None e o SAVEPOINT isola, deixando a sessão usável.
    """
    from app.agente.models import AgentEvalScore

    agent_name = f'test-agent-erro:{uuid.uuid4().hex[:8]}'

    # score=None viola NOT NULL -> IntegrityError isolado pelo savepoint
    result = AgentEvalScore.insert_score(
        agent_name=agent_name, score=None, total=10, passed=5,
    )
    assert result is None

    # SEM rollback manual — sessão deve continuar usável
    ok = AgentEvalScore.insert_score(
        agent_name=agent_name, score=0.60, total=10, passed=6,
    )
    assert ok is not None
    assert ok.score == 0.60

    _db.session.rollback()
