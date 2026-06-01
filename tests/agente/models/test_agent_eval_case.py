"""
Tests for AgentEvalCase model — A3-R3 (calibração do judge de eval).

Testa:
- insert_case grava todos os campos corretos (SAVEPOINT, retorna a entry)
- insert_case em erro não propaga (SAVEPOINT isola) — best-effort
- sample_unreviewed só retorna human_verdict IS NULL
- sample_unreviewed é DETERMINÍSTICA por seed (mesma amostra p/ mesmo seed)
- sample_unreviewed respeita fraction (clampada) + min_n
- concordance_rate calcula agree/reviewed correto (e None se 0 revisados)

Espelha setup de test_agent_eval_score.py: módulo-escopo app_ctx + rollback no
fim. agent_name via uuid para isolar runs (evita falso-negativo caso o banco de
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


def _mk_agent():
    return f'test-evalcase:{uuid.uuid4().hex[:8]}'


# ─── insert_case ──────────────────────────────────────────────────────────────

def test_insert_case_grava_campos_corretos(app_ctx):
    """Insere um caso e verifica id + todos os campos."""
    from app.agente.models import AgentEvalCase

    agent = _mk_agent()
    entry = AgentEvalCase.insert_case(
        agent_name=agent,
        case_id='ac-01',
        case_score=0.80,
        status='pass',
        git_sha='abc123',
        n_runs=3,
        case_score_variance=0.0123,
        invoke_failures=1,
        evidence='mediana=0.800 de 3 run(s), var=0.0123',
    )

    assert entry is not None
    assert entry.id is not None
    assert entry.agent_name == agent
    assert entry.case_id == 'ac-01'
    assert entry.case_score == 0.80
    assert entry.status == 'pass'
    assert entry.git_sha == 'abc123'
    assert entry.n_runs == 3
    assert abs(entry.case_score_variance - 0.0123) < 1e-9
    assert entry.invoke_failures == 1
    assert entry.evidence == 'mediana=0.800 de 3 run(s), var=0.0123'
    # não revisado por default
    assert entry.human_verdict is None
    assert entry.reviewed_by is None
    assert entry.reviewed_at is None
    assert entry.recorded_at is not None

    _db.session.rollback()


def test_insert_case_defaults(app_ctx):
    """Campos opcionais ausentes → defaults (n_runs=1, variance=0.0, failures=0)."""
    from app.agente.models import AgentEvalCase

    agent = _mk_agent()
    entry = AgentEvalCase.insert_case(
        agent_name=agent, case_id='c1', case_score=0.5, status='fail',
    )
    _db.session.flush()

    assert entry is not None
    assert entry.n_runs == 1
    assert entry.case_score_variance == 0.0
    assert entry.invoke_failures == 0
    assert entry.git_sha is None
    assert entry.evidence is None

    _db.session.rollback()


def test_insert_case_erro_nao_propaga(app_ctx):
    """case_score=None viola NOT NULL → SAVEPOINT isola, retorna None, sessão
    continua usável (best-effort)."""
    from app.agente.models import AgentEvalCase

    agent = _mk_agent()
    result = AgentEvalCase.insert_case(
        agent_name=agent, case_id='bad', case_score=None, status='pass',
    )
    assert result is None

    # SEM rollback manual — sessão deve continuar usável
    ok = AgentEvalCase.insert_case(
        agent_name=agent, case_id='good', case_score=0.7, status='pass',
    )
    assert ok is not None
    assert ok.case_score == 0.7

    _db.session.rollback()


# ─── sample_unreviewed ────────────────────────────────────────────────────────

def test_sample_unreviewed_so_retorna_human_verdict_null(app_ctx):
    """Só casos com human_verdict IS NULL entram na amostra (revisados ficam de
    fora)."""
    from app.agente.models import AgentEvalCase

    agent = _mk_agent()
    # 4 não revisados + 2 revisados
    for i in range(4):
        AgentEvalCase.insert_case(agent, f'unrev-{i}', 0.5, 'fail')
    rev_a = AgentEvalCase.insert_case(agent, 'rev-a', 0.9, 'pass')
    rev_b = AgentEvalCase.insert_case(agent, 'rev-b', 0.1, 'fail')
    rev_a.human_verdict = AgentEvalCase.VERDICT_AGREE
    rev_b.human_verdict = AgentEvalCase.VERDICT_DISAGREE
    _db.session.flush()

    # fraction 1.0 → pega TODOS os candidatos (todos não-revisados)
    amostra = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=1.0)
    ids = {c.case_id for c in amostra}
    assert ids == {'unrev-0', 'unrev-1', 'unrev-2', 'unrev-3'}
    assert 'rev-a' not in ids and 'rev-b' not in ids
    # todos retornados têm human_verdict None
    assert all(c.human_verdict is None for c in amostra)

    _db.session.rollback()


def test_sample_unreviewed_deterministica_por_seed(app_ctx):
    """Mesmo seed sobre o mesmo conjunto → MESMA amostra (reprodutível)."""
    from app.agente.models import AgentEvalCase

    agent = _mk_agent()
    for i in range(20):
        AgentEvalCase.insert_case(agent, f'c-{i:02d}', 0.5, 'fail')
    _db.session.flush()

    a1 = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=0.25, seed=42)
    a2 = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=0.25, seed=42)
    # 25% de 20 = 5 casos
    assert len(a1) == 5
    assert [c.case_id for c in a1] == [c.case_id for c in a2]

    # seed diferente → tende a amostra diferente (não garantido SEMPRE, mas com
    # 20 candidatos e 5 escolhidos a colisão total é improvável)
    a3 = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=0.25, seed=7)
    assert [c.case_id for c in a1] != [c.case_id for c in a3]

    _db.session.rollback()


def test_sample_unreviewed_respeita_fraction(app_ctx):
    """size ≈ round(fraction * total); fraction clampada a [0,1]."""
    from app.agente.models import AgentEvalCase

    agent = _mk_agent()
    for i in range(100):
        AgentEvalCase.insert_case(agent, f'c-{i:03d}', 0.5, 'fail')
    _db.session.flush()

    # 10% de 100 = 10
    a10 = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=0.10, seed=1)
    assert len(a10) == 10

    # 5% de 100 = 5
    a5 = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=0.05, seed=1)
    assert len(a5) == 5

    # fraction > 1.0 é clampada a 1.0 → todos os 100
    aall = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=5.0, seed=1)
    assert len(aall) == 100

    # code-review M4: fraction == 0.0 é intenção EXPLÍCITA de não amostrar →
    # lista vazia, MESMO com min_n=1 (o piso só vale quando frac > 0).
    azero = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=0.0, seed=1, min_n=1)
    assert azero == []

    # fraction < 0 também é clampada a 0.0 → vazio (não 1)
    aneg = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=-1.0, seed=1, min_n=1)
    assert aneg == []

    _db.session.rollback()


def test_sample_unreviewed_respeita_min_n(app_ctx):
    """Mesmo com fraction minúscula, min_n garante o piso (se houver
    candidatos)."""
    from app.agente.models import AgentEvalCase

    agent = _mk_agent()
    for i in range(10):
        AgentEvalCase.insert_case(agent, f'c-{i}', 0.5, 'fail')
    _db.session.flush()

    # 1% de 10 = 0.1 → round = 0, mas min_n=3 eleva p/ 3
    a = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=0.01, seed=1, min_n=3)
    assert len(a) == 3

    # min_n maior que o total → clampado ao total disponível
    a2 = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=0.01, seed=1, min_n=999)
    assert len(a2) == 10

    _db.session.rollback()


def test_sample_unreviewed_vazio_sem_candidatos(app_ctx):
    """Sem casos não-revisados para o agent → lista vazia."""
    from app.agente.models import AgentEvalCase

    agent = _mk_agent()  # nenhum caso inserido
    a = AgentEvalCase.sample_unreviewed(agent_name=agent, fraction=0.1, min_n=5)
    assert a == []

    _db.session.rollback()


def test_sample_unreviewed_filtra_por_agent_name(app_ctx):
    """agent_name filtra os candidatos (não vaza casos de outro agente)."""
    from app.agente.models import AgentEvalCase

    agent_a = _mk_agent()
    agent_b = _mk_agent()
    for i in range(5):
        AgentEvalCase.insert_case(agent_a, f'a-{i}', 0.5, 'fail')
    for i in range(5):
        AgentEvalCase.insert_case(agent_b, f'b-{i}', 0.5, 'fail')
    _db.session.flush()

    a = AgentEvalCase.sample_unreviewed(agent_name=agent_a, fraction=1.0)
    assert len(a) == 5
    assert all(c.agent_name == agent_a for c in a)

    _db.session.rollback()


# ─── concordance_rate ─────────────────────────────────────────────────────────

def test_concordance_rate_calcula_agree_sobre_reviewed(app_ctx):
    """rate = agree/reviewed sobre os casos com human_verdict NOT NULL."""
    from app.agente.models import AgentEvalCase

    agent = _mk_agent()
    # 3 agree, 1 disagree → reviewed=4, rate=0.75. + 2 não revisados (ignorados).
    verdicts = [
        AgentEvalCase.VERDICT_AGREE,
        AgentEvalCase.VERDICT_AGREE,
        AgentEvalCase.VERDICT_AGREE,
        AgentEvalCase.VERDICT_DISAGREE,
    ]
    for i, v in enumerate(verdicts):
        c = AgentEvalCase.insert_case(agent, f'rev-{i}', 0.5, 'pass')
        c.human_verdict = v
    # 2 não revisados
    AgentEvalCase.insert_case(agent, 'unrev-0', 0.5, 'fail')
    AgentEvalCase.insert_case(agent, 'unrev-1', 0.5, 'fail')
    _db.session.flush()

    conc = AgentEvalCase.concordance_rate(agent_name=agent)
    assert conc['reviewed'] == 4
    assert conc['agree'] == 3
    assert conc['disagree'] == 1
    assert abs(conc['rate'] - 0.75) < 1e-9

    _db.session.rollback()


def test_concordance_rate_none_se_zero_revisados(app_ctx):
    """Nenhum caso revisado → rate None (sem ground-truth, taxa indefinível)."""
    from app.agente.models import AgentEvalCase

    agent = _mk_agent()
    AgentEvalCase.insert_case(agent, 'c0', 0.5, 'fail')
    AgentEvalCase.insert_case(agent, 'c1', 0.5, 'fail')
    _db.session.flush()

    conc = AgentEvalCase.concordance_rate(agent_name=agent)
    assert conc['reviewed'] == 0
    assert conc['agree'] == 0
    assert conc['disagree'] == 0
    assert conc['rate'] is None

    _db.session.rollback()


def test_concordance_rate_filtra_por_agent_name(app_ctx):
    """concordance_rate(agent_name) só conta casos daquele agente."""
    from app.agente.models import AgentEvalCase

    agent_a = _mk_agent()
    agent_b = _mk_agent()
    ca = AgentEvalCase.insert_case(agent_a, 'a0', 0.5, 'pass')
    ca.human_verdict = AgentEvalCase.VERDICT_AGREE
    cb = AgentEvalCase.insert_case(agent_b, 'b0', 0.5, 'pass')
    cb.human_verdict = AgentEvalCase.VERDICT_DISAGREE
    _db.session.flush()

    conc_a = AgentEvalCase.concordance_rate(agent_name=agent_a)
    assert conc_a['reviewed'] == 1
    assert conc_a['agree'] == 1
    assert conc_a['rate'] == 1.0

    _db.session.rollback()
