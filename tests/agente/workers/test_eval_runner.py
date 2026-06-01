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


# ─── BUG-2: SSL-drop na persistencia (FASE 1 invokes / FASE 2 persistencia) ────

def test_run_eval_batch_invokes_antes_de_qualquer_query_db(app_ctx, monkeypatch):
    """BUG-2 ORDEM: todos os run_evals (invokes LENTOS, sem tocar DB) acontecem
    ANTES de qualquer get_baseline_score (1a query DB). Antes do fix, a conexao
    abria em get_baseline_score e ficava idle 8-50min durante os invokes → SSL-drop.

    Captura a ordem-de-chamada via lista compartilhada: cada run_evals e cada
    get_baseline_score anotam seu nome. Espera-se TODOS os 'run_evals:*' ANTES
    do primeiro 'baseline:*'.
    """
    from app.agente.workers import eval_runner
    from app.agente.models import AgentEvalScore

    agent_a = _mk_agent_name('orderA-')
    agent_b = _mk_agent_name('orderB-')

    monkeypatch.setattr(eval_runner, 'create_app', lambda: app_ctx)
    monkeypatch.setattr(
        eval_runner, 'build_subprocess_invoke_fn',
        lambda *a, **k: (lambda x: 'mock'),
    )

    ordem = []

    def _run_evals(agent_name, dataset_path, invoke_fn=None, judge_fn=None):
        ordem.append(f'run_evals:{agent_name}')
        return {'agent_name': agent_name, 'score': 0.55, 'total': 4, 'passed': 2, 'cases': []}

    monkeypatch.setattr(eval_runner, 'run_evals', _run_evals)

    # Spy em get_baseline_score (1a query DB da FASE 2)
    real_get_baseline = AgentEvalScore.get_baseline_score.__func__

    def _spy_get_baseline(cls, agent_name):
        ordem.append(f'baseline:{agent_name}')
        return real_get_baseline(cls, agent_name)

    monkeypatch.setattr(
        AgentEvalScore, 'get_baseline_score',
        classmethod(_spy_get_baseline),
    )

    datasets = [(agent_a, '/tmp/fake_a.yaml'), (agent_b, '/tmp/fake_b.yaml')]

    try:
        eval_runner._run_eval_batch_in_context(datasets)

        # Ha 2 run_evals e 2 baseline
        run_idx = [i for i, e in enumerate(ordem) if e.startswith('run_evals:')]
        base_idx = [i for i, e in enumerate(ordem) if e.startswith('baseline:')]
        assert len(run_idx) == 2, ordem
        assert len(base_idx) == 2, ordem

        # INVARIANTE BUG-2: TODOS os invokes ANTES de QUALQUER query DB
        assert max(run_idx) < min(base_idx), (
            f'invokes devem ocorrer ANTES de get_baseline_score; ordem={ordem}'
        )
    finally:
        monkeypatch.undo()
        _cleanup_scores(agent_a, agent_b)


def test_run_eval_batch_ssl_drop_retry_persiste_na_2a_tentativa(app_ctx, monkeypatch):
    """BUG-2 RETRY: OperationalError (SSL-drop) no PRIMEIRO commit → rollback →
    re-executa a persistencia (insert_score 2x) → 2o commit succeeds → score
    persistido.

    Antes do fix: o commit explodia com OperationalError e NADA persistia
    ('agentes=0'). Agora ha 1 retry com rollback (forca reconexao) entre as
    tentativas.
    """
    from sqlalchemy.exc import OperationalError
    from app.agente.workers import eval_runner
    from app.agente.models import AgentEvalScore

    agent = _mk_agent_name('ssl-')

    monkeypatch.setattr(eval_runner, 'create_app', lambda: app_ctx)
    monkeypatch.setattr(
        eval_runner, 'build_subprocess_invoke_fn',
        lambda *a, **k: (lambda x: 'mock'),
    )
    monkeypatch.setattr(
        eval_runner, 'run_evals',
        lambda agent_name, dataset_path, invoke_fn=None, judge_fn=None: {
            'agent_name': agent_name, 'score': 0.65, 'total': 8, 'passed': 5, 'cases': [],
        },
    )

    # commit: explode na 1a chamada (OperationalError), sucede na 2a.
    commit_calls = [0]
    real_commit = _db.session.commit

    def _spy_commit():
        commit_calls[0] += 1
        if commit_calls[0] == 1:
            raise OperationalError('SSL connection has been closed unexpectedly', None, None)
        return real_commit()

    monkeypatch.setattr(_db.session, 'commit', _spy_commit)

    # rollback: conta as chamadas (deve haver pelo menos 1 entre tentativas)
    rollback_calls = [0]
    real_rollback = _db.session.rollback

    def _spy_rollback():
        rollback_calls[0] += 1
        return real_rollback()

    monkeypatch.setattr(_db.session, 'rollback', _spy_rollback)

    # insert_score: conta as chamadas (re-executado na 2a tentativa).
    insert_calls = [0]
    real_insert = AgentEvalScore.insert_score.__func__

    def _spy_insert(cls, *a, **k):
        insert_calls[0] += 1
        return real_insert(cls, *a, **k)

    monkeypatch.setattr(
        AgentEvalScore, 'insert_score',
        classmethod(_spy_insert),
    )

    datasets = [(agent, '/tmp/fake_ssl.yaml')]

    try:
        result = eval_runner._run_eval_batch_in_context(datasets)

        # 2 commits (1o falhou OperationalError, 2o sucedeu)
        assert commit_calls[0] == 2, f'esperado 2 commits, foi {commit_calls[0]}'
        # rollback foi chamado para forcar reconexao
        assert rollback_calls[0] >= 1, f'rollback nao foi chamado: {rollback_calls[0]}'
        # insert_score re-executado: 1x por tentativa = 2x (1 agente x 2 tentativas)
        assert insert_calls[0] == 2, f'esperado 2 insert_score, foi {insert_calls[0]}'

        # score persistido na 2a tentativa — e SEM duplicata (o rollback descartou
        # o SAVEPOINT da 1a tentativa, entao ha EXATAMENTE 1 linha).
        rows = AgentEvalScore.query.filter_by(agent_name=agent).all()
        assert len(rows) == 1, f'esperado 1 linha (sem duplicata), foi {len(rows)}'
        row = rows[0]
        assert row.score == 0.65
        assert row.total == 8
        assert row.passed == 5

        assert result['agentes'] == 1
        assert result['scores'].get(agent) == 0.65
    finally:
        monkeypatch.undo()
        _cleanup_scores(agent)


def test_run_eval_batch_ssl_drop_rollback_falha_forca_dispose(app_ctx, monkeypatch):
    """HIGH-2 (code-review): no cenario TCP-morto real, o proprio rollback
    pre-retry falha. O fix forca db.engine.dispose() para descartar a conexao
    morta do pool, e a 2a tentativa de persistencia/commit sucede.

    Sem o dispose, a 2a tentativa rodaria sobre a mesma conexao quebrada.
    """
    from sqlalchemy.exc import OperationalError
    from app.agente.workers import eval_runner
    from app.agente.models import AgentEvalScore

    agent = _mk_agent_name('disp-')

    monkeypatch.setattr(eval_runner, 'create_app', lambda: app_ctx)
    monkeypatch.setattr(
        eval_runner, 'build_subprocess_invoke_fn',
        lambda *a, **k: (lambda x: 'mock'),
    )
    monkeypatch.setattr(
        eval_runner, 'run_evals',
        lambda agent_name, dataset_path, invoke_fn=None, judge_fn=None: {
            'agent_name': agent_name, 'score': 0.7, 'total': 5, 'passed': 4, 'cases': [],
        },
    )

    # commit: explode na 1a (OperationalError), sucede na 2a.
    commit_calls = [0]
    real_commit = _db.session.commit

    def _spy_commit():
        commit_calls[0] += 1
        if commit_calls[0] == 1:
            raise OperationalError('SSL connection has been closed unexpectedly', None, None)
        return real_commit()

    monkeypatch.setattr(_db.session, 'commit', _spy_commit)

    # rollback: o PRE-RETRY (2a chamada) falha → deve disparar engine.dispose().
    rollback_calls = [0]
    real_rollback = _db.session.rollback

    def _spy_rollback():
        rollback_calls[0] += 1
        if rollback_calls[0] == 2:  # rollback pre-retry (apos o commit falho)
            raise OperationalError('connection already closed', None, None)
        return real_rollback()

    monkeypatch.setattr(_db.session, 'rollback', _spy_rollback)

    # close + dispose: ambos devem ser chamados quando o rollback pre-retry falha.
    # close() descarta o insert pendente da session (senao a 2a tentativa
    # DUPLICA a linha); dispose() limpa a conexao morta do pool.
    cleanup_calls = {'close': 0, 'dispose': 0}
    real_close = _db.session.close
    real_dispose = _db.engine.dispose

    def _spy_close(*a, **k):
        cleanup_calls['close'] += 1
        return real_close(*a, **k)

    def _spy_dispose(*a, **k):
        cleanup_calls['dispose'] += 1
        return real_dispose(*a, **k)

    monkeypatch.setattr(_db.session, 'close', _spy_close)
    monkeypatch.setattr(_db.engine, 'dispose', _spy_dispose)

    datasets = [(agent, '/tmp/fake_disp.yaml')]

    try:
        result = eval_runner._run_eval_batch_in_context(datasets)

        # close E dispose foram chamados porque o rollback pre-retry falhou (HIGH-2)
        assert cleanup_calls['close'] >= 1, f'session.close nao chamado: {cleanup_calls}'
        assert cleanup_calls['dispose'] >= 1, f'engine.dispose nao chamado: {cleanup_calls}'
        # 2 commits (1o falhou, 2o sucedeu apos cleanup)
        assert commit_calls[0] == 2, f'esperado 2 commits, foi {commit_calls[0]}'
        # score persistido na 2a tentativa
        assert result['scores'].get(agent) == 0.7
        # SEM duplicata: close() descartou o insert pendente da 1a tentativa
        rows = AgentEvalScore.query.filter_by(agent_name=agent).all()
        assert len(rows) == 1, f'esperado 1 linha (sem duplicata), foi {len(rows)}'
    finally:
        monkeypatch.undo()
        _cleanup_scores(agent)


def test_run_eval_batch_ssl_drop_ambas_tentativas_falham_best_effort(app_ctx, monkeypatch):
    """BUG-2 BEST-EFFORT (INV-6): se AMBAS as tentativas de commit falharem com
    OperationalError, NAO propaga exceção (nao derruba o cron) — retorna o que
    tiver (best-effort)."""
    from sqlalchemy.exc import OperationalError
    from app.agente.workers import eval_runner
    from app.agente.models import AgentEvalScore

    agent = _mk_agent_name('ssl2x-')

    monkeypatch.setattr(eval_runner, 'create_app', lambda: app_ctx)
    monkeypatch.setattr(
        eval_runner, 'build_subprocess_invoke_fn',
        lambda *a, **k: (lambda x: 'mock'),
    )
    monkeypatch.setattr(
        eval_runner, 'run_evals',
        lambda agent_name, dataset_path, invoke_fn=None, judge_fn=None: {
            'agent_name': agent_name, 'score': 0.50, 'total': 2, 'passed': 1, 'cases': [],
        },
    )

    # commit SEMPRE explode com OperationalError (1a e 2a tentativa)
    commit_calls = [0]

    def _always_boom_commit():
        commit_calls[0] += 1
        raise OperationalError('SSL connection has been closed unexpectedly', None, None)

    monkeypatch.setattr(_db.session, 'commit', _always_boom_commit)

    datasets = [(agent, '/tmp/fake_ssl2x.yaml')]

    try:
        # NAO deve propagar (best-effort total INV-6)
        result = eval_runner._run_eval_batch_in_context(datasets)

        # ambas as tentativas de commit ocorreram
        assert commit_calls[0] == 2, f'esperado 2 commits (ambos falham), foi {commit_calls[0]}'

        # retornou estrutura valida (best-effort) — nada persistido pois commit falhou
        assert 'agentes' in result
        assert 'scores' in result
    finally:
        monkeypatch.undo()
        # Limpeza: garante sessao limpa apos OperationalError simulado
        try:
            _db.session.rollback()
        except Exception:
            pass
        _cleanup_scores(agent)


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
