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


# ─── get_score_by_git_sha (A3-R2 gate de regressão) ───────────────────────────

def test_get_score_by_git_sha_retorna_run_mais_recente_daquele_sha(app_ctx):
    """
    Com 2 runs em git_shas DIFERENTES, get_score_by_git_sha(sha) retorna o
    score do run MAIS RECENTE daquele sha específico — não confunde com o outro.
    """
    from app.agente.models import AgentEvalScore
    from datetime import timedelta

    agent_name = f'test-agent-sha:{uuid.uuid4().hex[:8]}'
    sha_antigo = 'aaa111'
    sha_novo = 'bbb222'
    base_ts = agora_utc_naive()

    # Run no sha_antigo (score 0.40)
    r_antigo = AgentEvalScore.insert_score(
        agent_name=agent_name, score=0.40, total=10, passed=4, git_sha=sha_antigo,
    )
    r_antigo.recorded_at = base_ts - timedelta(hours=2)

    # Run no sha_novo (score 0.90) — mais recente em geral
    r_novo = AgentEvalScore.insert_score(
        agent_name=agent_name, score=0.90, total=10, passed=9, git_sha=sha_novo,
    )
    r_novo.recorded_at = base_ts
    _db.session.flush()

    # Busca por sha_antigo retorna 0.40 (NAO 0.90, que é o mais recente global)
    assert AgentEvalScore.get_score_by_git_sha(agent_name, sha_antigo) == 0.40
    # Busca por sha_novo retorna 0.90
    assert AgentEvalScore.get_score_by_git_sha(agent_name, sha_novo) == 0.90

    _db.session.rollback()


def test_get_score_by_git_sha_dois_runs_mesmo_sha_pega_o_mais_recente(app_ctx):
    """
    Dois runs no MESMO git_sha → retorna o score do MAIS RECENTE (recorded_at
    DESC, id DESC), espelhando get_baseline_score.
    """
    from app.agente.models import AgentEvalScore
    from datetime import timedelta

    agent_name = f'test-agent-sha2:{uuid.uuid4().hex[:8]}'
    sha = 'ccc333'
    base_ts = agora_utc_naive()

    velho = AgentEvalScore.insert_score(
        agent_name=agent_name, score=0.30, total=10, passed=3, git_sha=sha,
    )
    velho.recorded_at = base_ts - timedelta(hours=1)

    recente = AgentEvalScore.insert_score(
        agent_name=agent_name, score=0.75, total=10, passed=7, git_sha=sha,
    )
    recente.recorded_at = base_ts
    _db.session.flush()

    assert AgentEvalScore.get_score_by_git_sha(agent_name, sha) == 0.75

    _db.session.rollback()


def test_get_score_by_git_sha_none_para_sha_inexistente(app_ctx):
    """sha que não tem nenhum run para o agent_name → None."""
    from app.agente.models import AgentEvalScore

    agent_name = f'test-agent-sha-ghost:{uuid.uuid4().hex[:8]}'
    AgentEvalScore.insert_score(
        agent_name=agent_name, score=0.50, total=10, passed=5, git_sha='real-sha',
    )
    _db.session.flush()

    assert AgentEvalScore.get_score_by_git_sha(agent_name, 'sha-que-nao-existe') is None

    _db.session.rollback()


def test_get_score_by_git_sha_none_para_sha_none_ou_vazio(app_ctx):
    """git_sha None ou vazio → None (sem baseline identificável), sem query."""
    from app.agente.models import AgentEvalScore

    agent_name = f'test-agent-sha-null:{uuid.uuid4().hex[:8]}'
    # Existe ate um run com git_sha=None, mas a busca por None NAO deve retorná-lo.
    AgentEvalScore.insert_score(
        agent_name=agent_name, score=0.50, total=10, passed=5, git_sha=None,
    )
    _db.session.flush()

    assert AgentEvalScore.get_score_by_git_sha(agent_name, None) is None
    assert AgentEvalScore.get_score_by_git_sha(agent_name, '') is None

    _db.session.rollback()
