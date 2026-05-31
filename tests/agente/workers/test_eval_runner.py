"""
A3 Fase 1, sub-task 3b — testes do worker eval_runner (run_eval_batch + enqueue).

Wira a invocacao REAL do agente no eval gate, mas EXECUTADA em fila RQ NOVA
'agent_eval' (PESADA) — NAO inline no cron (eval real e' 20-50min). Os testes
NUNCA chamam API/CLI real: `build_subprocess_invoke_fn` e o judge sao mockados,
ou `run_evals` e' mockado direto.

Cobertura:
- run_eval_batch persiste score em agent_eval_scores + commit (spy) + log report-only
- run_eval_batch chama get_baseline_score ANTES de insert_score (constraint 1):
  INTEGRACAO de 2 runs sequenciais — baseline do 2o run == score do 1o run
- run_eval_batch best-effort: um agente que explode NAO impede os outros
- enqueue_eval_batch flag-OFF (AGENT_EVAL_GATE=False) -> NAO enfileira
- enqueue_eval_batch flag-ON -> enfileira run_eval_batch na fila agent_eval

Espelha o pattern de test_triage_shadow (monkeypatch create_app=app_ctx +
mock Queue/redis + patch da flag).
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app import create_app, db as _db


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def app_ctx():
    """Flask app context para testes do eval_runner (escopo de módulo)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


def _mk_agent_name(suffix=''):
    return f'eval-test-{suffix}{uuid.uuid4().hex[:8]}'


def _cleanup_scores(*agent_names):
    """Remove os registros agent_eval_scores criados nos testes."""
    from app.agente.models import AgentEvalScore
    try:
        for name in agent_names:
            AgentEvalScore.query.filter_by(agent_name=name).delete()
        _db.session.commit()
    except Exception:
        _db.session.rollback()


# ─── run_eval_batch ───────────────────────────────────────────────────────────

def test_run_eval_batch_persiste_score_e_commita(app_ctx, monkeypatch):
    """run_eval_batch grava AgentEvalScore + commit explicito + log report-only.

    Mocka run_evals (zero API/CLI) e create_app (reusa app_ctx do teste).
    Spy no commit prova o CRITICAL: SAVEPOINT do insert_score nao commita sozinho.
    """
    from app.agente.workers import eval_runner

    agent = _mk_agent_name('persist-')

    monkeypatch.setattr(eval_runner, 'create_app', lambda: app_ctx)
    # _default_datasets devolve o agente de teste (nao os 4 reais) — o filtro
    # de run_eval_batch casa pelo agent_name.
    monkeypatch.setattr(
        eval_runner, '_default_datasets',
        lambda: [(agent, '/tmp/fake_persist.yaml')],
    )

    # run_evals mockado: score determinístico (zero API)
    monkeypatch.setattr(
        eval_runner, 'run_evals',
        lambda agent_name, dataset_path, invoke_fn=None, judge_fn=None: {
            'agent_name': agent_name, 'score': 0.80, 'total': 10, 'passed': 8, 'cases': [],
        },
    )
    # build_subprocess_invoke_fn nao deve disparar CLI — retorna closure inerte
    monkeypatch.setattr(
        eval_runner, 'build_subprocess_invoke_fn',
        lambda *a, **k: (lambda x: 'mock'),
    )

    commit_calls = [0]
    real_commit = _db.session.commit

    def _spy_commit():
        commit_calls[0] += 1
        return real_commit()

    monkeypatch.setattr(_db.session, 'commit', _spy_commit)

    try:
        result = eval_runner.run_eval_batch(agent_filter=agent)

        # commit explicito ocorreu (constraint 3)
        assert commit_calls[0] >= 1

        # score persistido
        from app.agente.models import AgentEvalScore
        row = AgentEvalScore.query.filter_by(agent_name=agent).first()
        assert row is not None
        assert row.score == 0.80
        assert row.total == 10
        assert row.passed == 8
        assert row.mode == 'report_only'

        assert result['agentes'] == 1
        assert agent in result['scores']
    finally:
        monkeypatch.undo()
        _cleanup_scores(agent)


def test_run_eval_batch_baseline_antes_de_insert(app_ctx, monkeypatch):
    """INTEGRACAO ordem baseline (constraint 1): 2 runs sequenciais do MESMO
    agente — o baseline observado no 2o run DEVE ser o score do 1o run.

    Se get_baseline_score fosse chamado DEPOIS de insert_score, o baseline do
    2o run seria o proprio score do 2o run (delta ~0). Capturamos o baseline
    de cada run via spy no eval_gate.
    """
    from app.agente.workers import eval_runner
    from app.agente.models import AgentEvalScore

    agent = _mk_agent_name('baseline-')

    monkeypatch.setattr(eval_runner, 'create_app', lambda: app_ctx)
    monkeypatch.setattr(
        eval_runner, '_default_datasets',
        lambda: [(agent, '/tmp/fake_baseline.yaml')],
    )
    monkeypatch.setattr(
        eval_runner, 'build_subprocess_invoke_fn',
        lambda *a, **k: (lambda x: 'mock'),
    )

    # scores controlados por run: 1o=0.40, 2o=0.90
    scores_seq = iter([0.40, 0.90])
    monkeypatch.setattr(
        eval_runner, 'run_evals',
        lambda agent_name, dataset_path, invoke_fn=None, judge_fn=None: {
            'agent_name': agent_name, 'score': next(scores_seq),
            'total': 10, 'passed': 0, 'cases': [],
        },
    )

    # Spy no eval_gate p/ capturar o baseline_score visto em cada run
    baselines_vistos = []
    real_eval_gate = eval_runner.eval_gate

    def _spy_eval_gate(baseline_score, candidate_score, **kw):
        baselines_vistos.append(baseline_score)
        return real_eval_gate(baseline_score=baseline_score, candidate_score=candidate_score, **kw)

    monkeypatch.setattr(eval_runner, 'eval_gate', _spy_eval_gate)

    try:
        # 1o run — sem baseline previo (None -> 0.0)
        eval_runner.run_eval_batch(agent_filter=agent)
        # 2o run — baseline DEVE ser o score do 1o run (0.40)
        eval_runner.run_eval_batch(agent_filter=agent)

        assert len(baselines_vistos) == 2
        assert baselines_vistos[0] == 0.0   # sem run previo (None -> 0.0)
        assert baselines_vistos[1] == 0.40  # score do 1o run, NAO 0.90

        # E ha 2 linhas persistidas (uma por run)
        rows = AgentEvalScore.query.filter_by(agent_name=agent).all()
        assert len(rows) == 2
    finally:
        monkeypatch.undo()
        _cleanup_scores(agent)


def test_run_eval_batch_best_effort_um_agente_explode(app_ctx, monkeypatch):
    """best-effort (constraint 4): um agente que explode em run_evals NAO impede
    o processamento dos demais. O agente OK ainda persiste seu score."""
    from app.agente.workers import eval_runner
    from app.agente.models import AgentEvalScore

    agent_ok = _mk_agent_name('ok-')
    agent_boom = _mk_agent_name('boom-')

    monkeypatch.setattr(eval_runner, 'create_app', lambda: app_ctx)
    monkeypatch.setattr(
        eval_runner, 'build_subprocess_invoke_fn',
        lambda *a, **k: (lambda x: 'mock'),
    )

    def _run_evals(agent_name, dataset_path, invoke_fn=None, judge_fn=None):
        if agent_name == agent_boom:
            raise RuntimeError('explosao simulada em run_evals')
        return {'agent_name': agent_name, 'score': 0.70, 'total': 5, 'passed': 3, 'cases': []}

    monkeypatch.setattr(eval_runner, 'run_evals', _run_evals)

    # Filtro precisa processar AMBOS: passamos lista via _run_eval_batch_in_context
    # diretamente, com os 2 datasets fakes.
    datasets = [(agent_boom, '/tmp/fake_boom.yaml'), (agent_ok, '/tmp/fake_ok.yaml')]

    try:
        result = eval_runner._run_eval_batch_in_context(datasets)

        # agente OK persistiu mesmo com o boom antes/depois
        row_ok = AgentEvalScore.query.filter_by(agent_name=agent_ok).first()
        assert row_ok is not None
        assert row_ok.score == 0.70

        # agente boom NAO persistiu (mas nao derrubou o batch)
        row_boom = AgentEvalScore.query.filter_by(agent_name=agent_boom).first()
        assert row_boom is None

        assert result['scores'].get(agent_ok) == 0.70
    finally:
        monkeypatch.undo()
        _cleanup_scores(agent_ok, agent_boom)


# ─── enqueue_eval_batch ───────────────────────────────────────────────────────

def test_enqueue_eval_batch_flag_off_nao_enfileira(app_ctx):
    """AGENT_EVAL_GATE=False -> enqueue_eval_batch NAO toca a fila."""
    from app.agente.workers import eval_runner

    mock_queue = MagicMock()
    with patch('app.agente.config.feature_flags.AGENT_EVAL_GATE', False):
        result = eval_runner.enqueue_eval_batch(queue=mock_queue)

    mock_queue.enqueue.assert_not_called()
    assert result.get('skipped') == 'flag_off'


def test_enqueue_eval_batch_flag_on_enfileira_run_eval_batch(app_ctx):
    """AGENT_EVAL_GATE=True -> enfileira run_eval_batch na fila agent_eval."""
    from app.agente.workers import eval_runner

    mock_queue = MagicMock()
    with patch('app.agente.config.feature_flags.AGENT_EVAL_GATE', True):
        result = eval_runner.enqueue_eval_batch(queue=mock_queue)

    assert mock_queue.enqueue.call_count == 1
    call = mock_queue.enqueue.call_args
    # 1o arg = path do job run_eval_batch
    assert call.args[0] == 'app.agente.workers.eval_runner.run_eval_batch'
    # job_timeout generoso (eval real e' longo)
    assert call.kwargs.get('job_timeout', 0) >= 3600
    assert result.get('enfileirado') is True


def test_enqueue_eval_batch_redis_down_best_effort(app_ctx):
    """Flag ON mas Redis indisponivel -> skipped='redis_error', sem raise."""
    from app.agente.workers import eval_runner

    with patch('app.agente.config.feature_flags.AGENT_EVAL_GATE', True), \
         patch('redis.from_url', side_effect=Exception('redis down')):
        result = eval_runner.enqueue_eval_batch(queue=None)

    assert result.get('skipped') == 'redis_error'


def test_eval_queue_name_constante(app_ctx):
    """EVAL_QUEUE_NAME == 'agent_eval' (fila NOVA PESADA — constraint 2)."""
    from app.agente.workers import eval_runner
    assert eval_runner.EVAL_QUEUE_NAME == 'agent_eval'
