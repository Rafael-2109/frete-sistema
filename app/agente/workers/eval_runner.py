"""
Eval runner — A3 Fase 1, sub-task 3b (wiring REAL do agente no eval gate).

Roda os golden datasets dos subagentes invocando o AGENTE REAL via
`claude -p --agent <nome>` (build_subprocess_invoke_fn) e persiste o score
por-agente em `agent_eval_scores`, comparando contra o baseline (run anterior)
em modo report-only.

POR QUE FILA RQ (e NAO inline no cron):
    A invocacao REAL do agente e' LONGA (20-50min para os 4 datasets, ~35 casos).
    Rodar inline no modulo 28 do scheduler bloquearia o ciclo de sincronizacao.
    Por isso o modulo 28 apenas ENFILEIRA `run_eval_batch` na fila NOVA
    'agent_eval' (classificada PESADA em worker_render.py — so' Workers 1/2
    processam, preservando o slot interativo do Worker 0).

CONSTRAINTS (de reviews anteriores — ver task 3b):
    1. ORDEM BASELINE: get_baseline_score(agent) ANTES de insert_score(agent).
       Senao o "mais recente" seria o proprio run atual → delta sempre ~0.
    2. FILA PESADA: 'agent_eval' (NAO 'agent_judge' que e' leve/interativo).
    3. COMMIT EXPLICITO: insert_score usa SAVEPOINT (begin_nested) que NAO
       commita sozinho no job RQ — o batch faz db.session.commit() ao final.
    4. BEST-EFFORT (INV-6): um agente que explode NAO impede os outros; nada
       propaga exceção que derrube o cron/worker.
    5. FLAG-OFF = no-op: com AGENT_EVAL_GATE=false, enqueue_eval_batch nao
       enfileira nada.

Padrao clonado de: app/agente/workers/triage_shadow.py
  (job orquestrador create_app()+app_context() + enqueuer best-effort).
"""
import logging
import os
import pathlib
import subprocess
from typing import Optional

from app import create_app
from app.agente.services.eval_gate_service import (
    run_evals,
    eval_gate,
    build_subprocess_invoke_fn,
)

logger = logging.getLogger('sistema_fretes')

# Raiz do repo (worker/eval_runner.py → app/agente/workers/ → 4 níveis acima).
# Usado como cwd dos subprocessos (git, claude -p) e para resolver os datasets.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent

# Fila RQ NOVA (PESADA) onde o modulo 28 enfileira run_eval_batch.
# NAO reusa 'agent_judge' (leve/interativo): o eval real e' 20-50min e
# precisa ficar fora do Worker 0 (light-reserved). Classificada em
# FILAS_PESADAS (worker_render.py) → so' Workers 1/2 processam.
EVAL_QUEUE_NAME = 'agent_eval'

# job_timeout generoso — eval real dos 4 datasets pode levar 20-50min.
EVAL_JOB_TIMEOUT = 3600  # 1h


def _current_git_sha() -> Optional[str]:
    """Retorna o SHA do HEAD atual (rastreabilidade cross-deploy), ou None.

    Best-effort: qualquer falha (git ausente, fora de repo) → None.
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, timeout=10,
            cwd=str(_REPO_ROOT),
        )
        if result.returncode == 0:
            return (result.stdout or '').strip() or None
    except Exception as exc:
        logger.debug(f'[EVAL_RUNNER] _current_git_sha falhou (best-effort): {exc}')
    return None


def _default_datasets() -> list:
    """Os 4 golden datasets de subagentes (agent_name, dataset_path).

    Espelha a lista do modulo 28 do scheduler. Resolve a partir da raiz do repo.
    """
    evals_dir = _REPO_ROOT / '.claude' / 'evals' / 'subagents'
    return [
        ('analista-carteira', str(evals_dir / 'analista-carteira' / 'dataset.yaml')),
        ('auditor-financeiro', str(evals_dir / 'auditor-financeiro' / 'dataset.yaml')),
        ('controlador-custo-frete', str(evals_dir / 'controlador-custo-frete' / 'dataset.yaml')),
        ('gestor-motos-assai', str(evals_dir / 'gestor-motos-assai' / 'dataset.yaml')),
    ]


def persist_eval_cases(
    agent_name: str,
    run_result: dict,
    git_sha: Optional[str] = None,
) -> int:
    """A3-R3: persiste 1 AgentEvalCase por caso do run (calibração do judge).

    Espelha a saída de run_evals (`run_result['cases']`), gravando o veredito
    GRANULAR do judge por caso (vs o score AGREGADO de AgentEvalScore). Cada
    linha habilita o spot-check humano de 5-10% (sample_unreviewed) e a métrica
    de concordância (concordance_rate) — eixos/A-flywheel.md:165.

    insert_case usa SAVEPOINT (begin_nested) que NÃO commita sozinho; esta
    função faz db.session.commit() ao final (best-effort, rollback defensivo,
    mesmo pattern do batch). Um caso que explode no insert NÃO impede os demais.

    Args:
        agent_name: Nome do subagente (ex: 'analista-carteira').
        run_result: Dict de run_evals; só `run_result['cases']` é lido.
        git_sha: SHA do código avaliado (rastreabilidade), ou None.

    Returns:
        Número de casos efetivamente inseridos (best-effort; 0 em falha total).
    """
    from app import db
    from app.agente.models import AgentEvalCase

    cases = run_result.get('cases') or []
    inseridos = 0
    for c in cases:
        try:
            entry = AgentEvalCase.insert_case(
                agent_name=agent_name,
                case_id=c.get('id'),
                case_score=c.get('case_score', 0.0),
                status=c.get('status', 'error'),
                git_sha=git_sha,
                n_runs=c.get('n_runs', 1),
                case_score_variance=c.get('case_score_variance', 0.0),
                invoke_failures=c.get('invoke_failures', 0),
                evidence=c.get('evidence'),
            )
            if entry is not None:
                inseridos += 1
        except Exception as exc:
            # best-effort: um caso falhando NÃO impede os demais (INV-6).
            logger.warning(
                f'[EVAL_RUNNER] {agent_name}: erro ao persistir caso '
                f'{c.get("id")}: {exc}'
            )

    try:
        db.session.commit()
    except Exception as commit_err:
        # best-effort (INV-6): nada propaga; descarta os SAVEPOINTs pendentes.
        logger.warning(
            f'[EVAL_RUNNER] {agent_name}: commit de persist_eval_cases falhou '
            f'(best-effort): {commit_err}'
        )
        try:
            db.session.rollback()
        except Exception:
            pass
        return 0

    logger.info(
        f'[EVAL_RUNNER] {agent_name}: persist_eval_cases gravou {inseridos}/'
        f'{len(cases)} casos (A3-R3 calibracao)'
    )
    return inseridos


def run_eval_batch(agent_filter: Optional[str] = None) -> dict:
    """Job RQ: roda o eval REAL dos golden datasets e persiste scores.

    Abre create_app() + app_context() e delega a _run_eval_batch_in_context.
    Best-effort total (INV-6): qualquer exceção e' logada; nunca propaga.

    Args:
        agent_filter: Se passado, roda APENAS este agent_name (ativacao
            supervisionada da Fase 2 — 1 dataset). None → todos os 4.

    Returns:
        {'agentes': int, 'scores': {agent_name: score}} (best-effort).
    """
    logger.info(f'[EVAL_RUNNER] iniciando run_eval_batch (filter={agent_filter or "ALL"})')

    try:
        app = create_app()
        with app.app_context():
            datasets = _default_datasets()
            if agent_filter:
                datasets = [(n, p) for (n, p) in datasets if n == agent_filter]
            return _run_eval_batch_in_context(datasets)
    except Exception as exc:
        logger.error(f'[EVAL_RUNNER] falha inesperada em run_eval_batch: {exc}')
        return {'agentes': 0, 'scores': {}}


def _persist_eval_results(resultados: list, git_sha: Optional[str]) -> dict:
    """FASE 2 (re-executavel): persiste os resultados dos invokes no DB.

    Estruturado como helper IDEMPOTENTE-POR-TENTATIVA para o retry de commit
    do BUG-2: chamado uma vez; se o commit explodir com OperationalError
    (SSL-drop pos-invokes longos), o caller faz rollback (descarta os SAVEPOINTs
    pendentes) e chama ESTE helper DE NOVO, re-executando get_baseline+insert_score
    com a conexao reconectada antes do 2o commit.

    NAO commita — apenas acumula SAVEPOINTs via insert_score. O commit (e o retry)
    sao responsabilidade do caller `_run_eval_batch_in_context`.

    Args:
        resultados: lista de (agent_name, result-dict de run_evals).
        git_sha: SHA do HEAD (rastreabilidade), ou None.

    Returns:
        {agent_name: score} dos agentes cujo insert_score nao explodiu.
    """
    from app.agente.models import AgentEvalScore

    scores = {}
    for agent_name, result in resultados:
        try:
            # CONSTRAINT 1: baseline ANTES de insert_score do MESMO agente
            # (senao o "mais recente" seria o proprio run atual → delta ~0).
            baseline = AgentEvalScore.get_baseline_score(agent_name)

            gate = eval_gate(
                baseline_score=baseline if baseline is not None else 0.0,
                candidate_score=result['score'],
                mode='report_only',
            )

            AgentEvalScore.insert_score(
                agent_name,
                result['score'],
                result['total'],
                result['passed'],
                git_sha=git_sha,
                mode='report_only',
            )

            scores[agent_name] = result['score']

            logger.info(
                f"[EVAL_RUNNER] {agent_name}: score={result['score']:.3f} "
                f"passed={result['passed']}/{result['total']} "
                f"baseline={baseline if baseline is not None else 'N/A'} "
                f"delta={gate['delta']:+.3f} regression={gate['regression']} "
                f"(report-only, nunca bloqueia)"
            )
        except Exception as exc:
            # CONSTRAINT 4: um agente falhando na persistencia NAO impede os demais.
            logger.warning(f'[EVAL_RUNNER] {agent_name}: erro ao persistir score: {exc}')

    return scores


def _run_eval_batch_in_context(datasets: list) -> dict:
    """Executa o eval batch dentro de app_context ativo.

    Separado para testabilidade (espelha _triage_step_shadow_in_context).

    BUG-2 FIX (SSL-drop pos-invokes longos): a conexao Postgres ficava idle
    8-50min durante os invokes `claude -p` e o servidor/SSL a derrubava; o
    commit final explodia com OperationalError e NADA persistia. Solucao:
    separar em 2 FASES e adicionar retry de commit com rollback.

    FASE 1 — INVOKES (sem tocar DB): roda TODOS os run_evals primeiro,
        acumulando os resultados. Nenhuma query DB acontece aqui, entao a
        conexao nao fica idle durante o tempo longo.
    FASE 2 — PERSISTENCIA (conexao fresca): so' depois de TODOS os invokes,
        abre as queries DB (get_baseline + insert_score) e commita. Se o
        commit explodir com OperationalError (SSL-drop residual), faz rollback
        (forca reconexao) e RE-EXECUTA a persistencia + commit UMA vez mais.

    Cada agente roda em try/except ISOLADO (constraint 4); nada propaga (INV-6).
    insert_score usa SAVEPOINT que NAO commita sozinho (constraint 3) — o commit
    explicito ao final do FASE 2 consolida.

    NOTA SEMANTICA (MEDIUM-1 code-review): apos o fix do judge granular (BUG-1),
    `score` passou de "fracao de casos 100%-pass" para "media dos case_score
    parciais". Baselines GRAVADOS antes do fix em agent_eval_scores tem a
    semantica antiga. Na 1a rodada pos-deploy, o candidate (granular, tende a ser
    maior) vs baseline (binario antigo) pode logar um "improvement" falso. Como o
    gate e' report_only (nunca bloqueia) o impacto e' so' 1 relatorio enganoso;
    a partir da 2a rodada o baseline ja' e' granular e a comparacao volta a ser
    apples-to-apples. Nao ha migration — e' reset natural na 1a rodada.
    """
    from app import db
    from sqlalchemy.exc import OperationalError, PendingRollbackError

    git_sha = _current_git_sha()

    # ─── FASE 1 — INVOKES (LENTO, sem tocar DB) ───────────────────────────────
    resultados = []
    for agent_name, dataset_path in datasets:
        try:
            # Wiring REAL do agente. AGENT_EVAL_MODEL opcional (override de modelo).
            # CONSTRAINT (code-review T3b I1): timeout GENEROSO — os subagentes são
            # Opus effort:xhigh fazendo Odoo/SQL real; um run legítimo >120s viraria
            # TimeoutExpired→'error'→score deflacionado→falso-positivo de regressão
            # (envenenaria o baseline). Default 600s (folga vs job_timeout=3600).
            invoke = build_subprocess_invoke_fn(
                agent_name,
                model=os.environ.get('AGENT_EVAL_MODEL') or None,
                timeout=int(os.environ.get('AGENT_EVAL_TIMEOUT', '600')),
            )

            # judge_fn default = Haiku real (mockado nos testes).
            # A3-R1: n_runs domina nao-determinismo do LLM (mediana de N runs).
            # Configuravel via AGENT_EVAL_N_RUNS (custo x estabilidade). Default 3.
            result = run_evals(
                agent_name, dataset_path, invoke_fn=invoke,
                n_runs=int(os.environ.get('AGENT_EVAL_N_RUNS', '3')),
            )
            resultados.append((agent_name, result))
        except Exception as exc:
            # CONSTRAINT 4: um agente falhando NAO impede os demais.
            logger.warning(f'[EVAL_RUNNER] {agent_name}: erro ao rodar evals: {exc}')

    # ─── FASE 2 — PERSISTENCIA (conexao fresca, com retry SSL-drop) ───────────
    # rollback DEFENSIVO antes de qualquer query: limpa estado de conexao
    # morta / transacao invalida deixado pelos 8-50min de idle. Pode falhar se
    # a conexao ja morreu — tudo bem, o proximo uso do pool reconecta.
    try:
        db.session.rollback()
    except Exception as roll_err:
        logger.debug(f'[EVAL_RUNNER] rollback defensivo inicial falhou (ok): {roll_err}')

    scores = _persist_eval_results(resultados, git_sha)

    # CONSTRAINT 3: commit explicito — insert_score usa SAVEPOINT que NAO
    # commita sozinho no job RQ (create_app sem transacao pai).
    try:
        db.session.commit()
    except (OperationalError, PendingRollbackError) as commit_err:
        # BUG-2 + BUG X7 (2026-06-01): SSL-drop no 1o commit. O disconnect apos os
        # invokes longos surge como OperationalError (detectado no statement) OU como
        # PendingRollbackError (code 8s2b, "Can't reconnect until invalid transaction
        # is rolled back") quando um get_baseline ja envenenou a transacao na FASE 2.
        # PendingRollbackError eh IRMA de OperationalError (ambas != hierarquia), entao
        # PRECISA estar no catch — senao cai no except generico e nada persiste (X7).
        # Rollback forca reconexao; RE-EXECUTA a persistencia (rollback descartou os
        # SAVEPOINTs) e tenta o commit 1x mais.
        logger.warning(
            f'[EVAL_RUNNER] commit 1a tentativa falhou (SSL-drop?): {commit_err} — '
            f'rollback + retry'
        )
        try:
            db.session.rollback()
        except Exception as roll_err:
            # HIGH-2 (code-review): no cenario TCP-morto real (o que BUG-2
            # defende), o proprio rollback falha. Nesse caso o SAVEPOINT/insert
            # da 1a tentativa CONTINUA pendente na session — se so' fizermos
            # dispose() do pool, a 2a tentativa insere de novo → DUPLICATA no
            # baseline (pior que agentes=0). Solucao: close() descarta o estado
            # pendente da session E dispose() limpa as conexoes mortas do pool.
            # Ordem: close() (desvincula a session da conexao morta) → dispose()
            # (garante que o pool nao reuse conexao quebrada).
            logger.warning(
                f'[EVAL_RUNNER] rollback pre-retry falhou — close+dispose: {roll_err}'
            )
            for _cleanup in (db.session.close, db.engine.dispose):
                try:
                    _cleanup()
                except Exception as ce:
                    logger.debug(f'[EVAL_RUNNER] cleanup pre-retry falhou (ok): {ce}')

        # 2a tentativa: re-persiste (get_baseline + insert_score) com conexao fresca
        scores = _persist_eval_results(resultados, git_sha)
        try:
            db.session.commit()
        except Exception as retry_err:
            # 2a tentativa tambem falhou → best-effort (INV-6): nao propaga.
            logger.error(f'[EVAL_RUNNER] commit 2a tentativa falhou: {retry_err}')
            try:
                db.session.rollback()
            except Exception:
                pass
            scores = {}
    except Exception as commit_err:
        # Erro de commit nao-SSL (ex: IntegrityError residual) — best-effort.
        logger.error(f'[EVAL_RUNNER] commit falhou: {commit_err}')
        try:
            db.session.rollback()
        except Exception:
            pass
        scores = {}

    logger.info(f'[EVAL_RUNNER] concluido: agentes={len(scores)}')
    return {'agentes': len(scores), 'scores': scores}


def run_eval_regression_gate(
    agent_name: str,
    dataset_path: str,
    sha_baseline: Optional[str] = None,
    n_runs: Optional[int] = None,
) -> dict:
    """A3 GATE DE REGRESSAO: mede se uma MUDANCA DE CODIGO regrediu um subagente.

    Coracao da A3 (spec eixos/A-flywheel.md:186 — "regression-eval contra golden
    dataset confirma que a mudanca nao regrediu"). Compara o score do
    codigo-DEPOIS (candidate = run recem-medido do sha ATUAL) vs o score do
    codigo-ANTES (baseline = score do sha-ANTERIOR ja persistido em
    agent_eval_scores), SEMPRE em modo report-only.

    DESIGN (decisao tomada — NAO usa git worktree temporario): os DOIS scores
    sao identificados por git_sha em agent_eval_scores. Espelha o que
    directive_promotion_service.evaluate_and_promote ja faz (recebe baseline +
    candidate prontos e chama eval_gate).

    Abre create_app()+app_context() e delega a _run_regression_in_context
    (espelha run_eval_batch / _run_eval_batch_in_context).

    Args:
        agent_name: Nome do subagente (ex: 'analista-carteira').
        dataset_path: Caminho do golden dataset.yaml.
        sha_baseline: SHA do codigo-ANTES (baseline). None → fallback para o run
            mais recente (get_baseline_score, ignora sha).
        n_runs: Numero de runs por caso (mediana). None → AGENT_EVAL_N_RUNS ('3').

    Returns:
        Dict com {agent_name, candidate_score, baseline_score, delta,
        regression (bool), blocked (SEMPRE False em report_only),
        git_sha_candidate, git_sha_baseline, cases}. Em falha total →
        dict com 'error' (best-effort INV-6, nunca propaga).
    """
    logger.info(
        f'[EVAL_RUNNER] iniciando run_eval_regression_gate '
        f'(agent={agent_name} sha_baseline={sha_baseline or "AUTO"})'
    )

    try:
        app = create_app()
        with app.app_context():
            return _run_regression_in_context(
                agent_name, dataset_path, sha_baseline=sha_baseline, n_runs=n_runs,
            )
    except Exception as exc:
        # BEST-EFFORT (INV-6): qualquer falha logada, NAO propaga.
        logger.error(
            f'[EVAL_RUNNER] falha inesperada em run_eval_regression_gate '
            f'({agent_name}): {exc}'
        )
        return {
            'agent_name': agent_name,
            'error': str(exc),
            'candidate_score': None,
            'baseline_score': None,
            'delta': None,
            'regression': False,
            'blocked': False,
            'git_sha_candidate': None,
            'git_sha_baseline': sha_baseline,
            'cases': [],
        }


def _run_regression_in_context(
    agent_name: str,
    dataset_path: str,
    sha_baseline: Optional[str] = None,
    n_runs: Optional[int] = None,
) -> dict:
    """Executa o gate de regressao dentro de app_context ativo.

    Separado para testabilidade (espelha _run_eval_batch_in_context).

    Fluxo:
        1. Roda run_evals (invoke REAL via build_subprocess_invoke_fn) → candidate.
        2. Determina baseline:
           - sha_baseline dado → get_score_by_git_sha(agent, sha_baseline).
           - senao → get_baseline_score(agent) (run mais recente, fallback).
           - se None (1a vez) → baseline = candidate (delta 0, sem regressao).
        3. eval_gate(baseline, candidate, mode='report_only') → gate.
        4. Persiste o candidate (insert_score + commit best-effort).

    INVARIANTE (razao de ser da A3): NUNCA bloqueia — mode='report_only' SEMPRE.
    Apenas DETECTA e LOGA regressao (logger.warning com delta dentro do eval_gate).
    """
    from app import db
    from app.agente.models import AgentEvalScore

    try:
        effective_n_runs = (
            int(n_runs) if n_runs is not None
            else int(os.environ.get('AGENT_EVAL_N_RUNS', '3'))
        )

        # ─── 1. CANDIDATE — score do codigo ATUAL (invoke REAL) ────────────────
        invoke = build_subprocess_invoke_fn(
            agent_name,
            model=os.environ.get('AGENT_EVAL_MODEL') or None,
            timeout=int(os.environ.get('AGENT_EVAL_TIMEOUT', '600')),
        )
        candidate = run_evals(
            agent_name, dataset_path, invoke_fn=invoke, n_runs=effective_n_runs,
        )
        candidate_score = candidate['score']

        # ─── 2. BASELINE — score do codigo ANTES ──────────────────────────────
        if sha_baseline:
            baseline_score = AgentEvalScore.get_score_by_git_sha(agent_name, sha_baseline)
        else:
            baseline_score = AgentEvalScore.get_baseline_score(agent_name)

        if baseline_score is None:
            # 1a medicao: nao ha codigo-ANTES com o que comparar. Usa o proprio
            # candidate → delta 0, sem regressao (neutro).
            logger.info(
                f'[EVAL_RUNNER] {agent_name}: sem baseline '
                f'(sha_baseline={sha_baseline or "AUTO"}), primeira medicao — '
                f'usando candidate como baseline (delta 0, sem regressao)'
            )
            baseline_score = candidate_score

        # ─── 3. GATE — report_only SEMPRE (NUNCA bloqueia) ────────────────────
        gate = eval_gate(
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            mode='report_only',
        )

        # ─── 4. PERSISTE o candidate (best-effort, pattern do batch) ──────────
        git_sha_candidate = _current_git_sha()
        try:
            db.session.rollback()
        except Exception as roll_err:
            logger.debug(f'[EVAL_RUNNER] rollback defensivo falhou (ok): {roll_err}')

        try:
            AgentEvalScore.insert_score(
                agent_name,
                candidate['score'],
                candidate['total'],
                candidate['passed'],
                git_sha=git_sha_candidate,
                mode='report_only',
            )
            db.session.commit()
        except Exception as persist_err:
            logger.warning(
                f'[EVAL_RUNNER] {agent_name}: falha ao persistir candidate '
                f'(best-effort): {persist_err}'
            )
            try:
                db.session.rollback()
            except Exception:
                pass

        # ─── 4b. A3-R3 — persistir CASOS para spot-check humano (gated) ───────
        # Import LAZY da flag (permite patch em teste). OFF (default) → só o
        # score agregado é persistido (comportamento A3-R2). ON → grava 1
        # AgentEvalCase por caso (calibração do judge, A-flywheel.md:165).
        from app.agente.config.feature_flags import USE_AGENT_EVAL_CALIBRATION
        if USE_AGENT_EVAL_CALIBRATION:
            try:
                persist_eval_cases(agent_name, candidate, git_sha=git_sha_candidate)
            except Exception as cal_err:
                # best-effort (INV-6): calibração NUNCA derruba o gate.
                logger.warning(
                    f'[EVAL_RUNNER] {agent_name}: persist_eval_cases falhou '
                    f'(best-effort): {cal_err}'
                )
                try:
                    db.session.rollback()
                except Exception:
                    pass

        logger.info(
            f"[EVAL_RUNNER] {agent_name}: GATE REGRESSAO "
            f"candidate={candidate_score:.3f} baseline={baseline_score:.3f} "
            f"delta={gate['delta']:+.3f} regression={gate['regression']} "
            f"blocked={gate['blocked']} (report-only, NUNCA bloqueia)"
        )

        return {
            'agent_name': agent_name,
            'candidate_score': candidate_score,
            'baseline_score': baseline_score,
            'delta': gate['delta'],
            'regression': gate['regression'],
            'blocked': gate['blocked'],  # SEMPRE False em report_only
            'git_sha_candidate': git_sha_candidate,
            'git_sha_baseline': sha_baseline,
            'cases': candidate.get('cases', []),
        }
    except Exception as exc:
        # BEST-EFFORT (INV-6): run_evals/eval_gate explode → dict com 'error'.
        logger.error(
            f'[EVAL_RUNNER] {agent_name}: erro no gate de regressao: {exc}'
        )
        try:
            db.session.rollback()
        except Exception:
            pass
        return {
            'agent_name': agent_name,
            'error': str(exc),
            'candidate_score': None,
            'baseline_score': None,
            'delta': None,
            'regression': False,
            'blocked': False,
            'git_sha_candidate': None,
            'git_sha_baseline': sha_baseline,
            'cases': [],
        }


def enqueue_eval_batch(queue=None) -> dict:
    """Enfileira run_eval_batch na fila NOVA 'agent_eval' (chamado pelo cron M28).

    CONSTRAINT 5: gate LAZY pela flag AGENT_EVAL_GATE (import dentro da funcao
    p/ patch de teste). Se OFF → {'skipped': 'flag_off'}, sem tocar Redis/Queue.

    Best-effort total (INV-6): falha de Redis NAO levanta — retorna
    {'skipped': 'redis_error'}.

    Args:
        queue: Queue RQ injetavel (testes). None → constroi via REDIS_URL.

    Returns:
        {'enfileirado': True} | {'skipped': 'flag_off'|'redis_error'}.
    """
    # CONSTRAINT 5: gate LAZY (permite patch de AGENT_EVAL_GATE em teste).
    from app.agente.config.feature_flags import AGENT_EVAL_GATE
    if not AGENT_EVAL_GATE:
        return {'skipped': 'flag_off'}

    # Constroi fila real inline se nao injetada (best-effort — INV-6).
    if queue is None:
        try:
            from rq import Queue
            import redis

            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            queue = Queue(EVAL_QUEUE_NAME, connection=r)
        except Exception as e:
            logger.error(f'[EVAL_RUNNER] Redis indisponivel, abortando best-effort: {e}')
            return {'skipped': 'redis_error'}

    try:
        queue.enqueue(
            'app.agente.workers.eval_runner.run_eval_batch',
            job_timeout=EVAL_JOB_TIMEOUT,
        )
        logger.info('[EVAL_RUNNER] enfileirado run_eval_batch na fila agent_eval')
        return {'enfileirado': True}
    except Exception as e:
        logger.warning(f'[EVAL_RUNNER] enqueue falhou: {e}')
        return {'skipped': 'enqueue_error'}


def review_eval_cases(
    agent_name: str,
    fraction: float = 0.1,
    seed: Optional[int] = None,
) -> dict:
    """A3-R3 CLI --review: LISTA uma amostra (5-10%) de casos NÃO revisados +
    métrica de concordância atual (spot-check humano).

    V1 = SÓ LEITURA + métrica: imprime os casos a revisar (case_id, case_score,
    status, evidence) e a concordance_rate. A MARCAÇÃO do human_verdict
    (agree/disagree) é MANUAL/FUTURA — via UPDATE direto em agent_eval_case ou
    endpoint futuro. Esta função NÃO escreve veredito humano.

    Abre create_app() + app_context() (espelha run_eval_batch). Best-effort:
    qualquer falha é logada, não propaga.

    Returns:
        {agent_name, sampled: int, cases: list[dict], concordance: dict}.
    """
    try:
        app = create_app()
        with app.app_context():
            from app.agente.models import AgentEvalCase

            amostra = AgentEvalCase.sample_unreviewed(
                agent_name=agent_name, fraction=fraction, seed=seed,
            )
            concordance = AgentEvalCase.concordance_rate(agent_name=agent_name)

            cases = [
                {
                    'id': c.id,
                    'case_id': c.case_id,
                    'case_score': c.case_score,
                    'status': c.status,
                    'evidence': c.evidence,
                }
                for c in amostra
            ]
            return {
                'agent_name': agent_name,
                'sampled': len(cases),
                'cases': cases,
                'concordance': concordance,
            }
    except Exception as exc:
        logger.error(f'[EVAL_RUNNER] review_eval_cases falhou ({agent_name}): {exc}')
        return {
            'agent_name': agent_name, 'sampled': 0, 'cases': [],
            'concordance': {'reviewed': 0, 'agree': 0, 'disagree': 0, 'rate': None},
            'error': str(exc),
        }


if __name__ == '__main__':
    # Ativacao supervisionada manual (Fase 2): roda 1 dataset SINCRONO.
    #   python -m app.agente.workers.eval_runner --agent analista-carteira
    #
    # Gate de regressao (A3 — report-only, NUNCA bloqueia):
    #   python -m app.agente.workers.eval_runner --regression --agent analista-carteira
    #   python -m app.agente.workers.eval_runner --regression --agent X --sha-baseline <sha>
    #
    # Spot-check humano (A3-R3 — calibracao do judge):
    #   python -m app.agente.workers.eval_runner --review --agent analista-carteira
    #   python -m app.agente.workers.eval_runner --review --agent X --fraction 0.1 --seed 42
    #
    #   V1 = LISTA os casos a revisar + imprime concordance_rate. A MARCACAO do
    #   veredito humano (human_verdict='agree'|'disagree') e' MANUAL/FUTURA: via
    #   UPDATE direto em agent_eval_case (set human_verdict, human_note,
    #   reviewed_by, reviewed_at) ou endpoint futuro. Esta CLI NAO escreve verdict.
    import argparse

    parser = argparse.ArgumentParser(
        description='Roda o eval REAL de UM subagente (sincrono, supervisionado).'
    )
    parser.add_argument(
        '--agent', required=True,
        help='Nome do subagente (ex: analista-carteira).',
    )
    parser.add_argument(
        '--regression', action='store_true',
        help='Roda o GATE DE REGRESSAO (candidate vs baseline por git_sha, report-only).',
    )
    parser.add_argument(
        '--sha-baseline', default=None,
        help='SHA do codigo-ANTES (baseline) para o gate de regressao. '
             'Omitido → fallback para o run mais recente.',
    )
    parser.add_argument(
        '--review', action='store_true',
        help='A3-R3 spot-check: LISTA uma amostra (5-10%%) de casos NAO revisados '
             '+ a concordance_rate atual. V1 = SO leitura + metrica; a marcacao do '
             'human_verdict (agree/disagree) e manual/futura (UPDATE direto ou '
             'endpoint).',
    )
    parser.add_argument(
        '--fraction', type=float, default=0.1,
        help='Fracao amostrada no --review (5-10%%). Default 0.1.',
    )
    parser.add_argument(
        '--seed', type=int, default=None,
        help='Seed para amostragem DETERMINISTICA no --review (reprodutivel). '
             'Omitido → amostra simples.',
    )
    args = parser.parse_args()

    if args.review:
        rev = review_eval_cases(args.agent, fraction=args.fraction, seed=args.seed)
        if rev.get('error'):
            print(f"[EVAL_RUNNER] erro no --review: {rev['error']}")
        else:
            print(
                f"[EVAL_RUNNER] SPOT-CHECK {args.agent}: "
                f"{rev['sampled']} caso(s) amostrado(s) para revisao humana "
                f"(fraction={args.fraction}, seed={args.seed})"
            )
            for c in rev['cases']:
                print(
                    f"  - case_id={c['case_id']} score={c['case_score']:.3f} "
                    f"status={c['status']}\n"
                    f"      evidence: {(c['evidence'] or '')[:200]}"
                )
            conc = rev['concordance']
            rate_str = (
                f"{conc['rate']:.1%}" if conc['rate'] is not None
                else 'N/A (0 revisados)'
            )
            print(
                f"[EVAL_RUNNER] CONCORDANCIA judge-vs-humano: rate={rate_str} "
                f"(reviewed={conc['reviewed']} agree={conc['agree']} "
                f"disagree={conc['disagree']})"
            )
            print(
                "[EVAL_RUNNER] Para marcar um veredito (manual/futuro): UPDATE "
                "agent_eval_case SET human_verdict='agree'|'disagree', "
                "reviewed_by=<usuarios.id>, reviewed_at=NOW() WHERE id=<id>;"
            )
    elif args.regression:
        # Resolve o dataset do agente pela mesma lista do batch.
        _datasets = dict(_default_datasets())
        _dataset_path = _datasets.get(args.agent)
        if _dataset_path is None:
            print(f'[EVAL_RUNNER] agente desconhecido: {args.agent} '
                  f'(opcoes: {sorted(_datasets)})')
        else:
            out = run_eval_regression_gate(
                args.agent, _dataset_path, sha_baseline=args.sha_baseline,
            )
            print(
                f"[EVAL_RUNNER] GATE REGRESSAO {args.agent}: "
                f"candidate={out.get('candidate_score')} "
                f"baseline={out.get('baseline_score')} "
                f"delta={out.get('delta')} regression={out.get('regression')} "
                f"blocked={out.get('blocked')}"
            )
            if out.get('error'):
                print(f"[EVAL_RUNNER] erro: {out['error']}")
    else:
        out = run_eval_batch(agent_filter=args.agent)
        print(f'[EVAL_RUNNER] resultado: {out}')
