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
import subprocess
from typing import Optional

from app import create_app
from app.agente.services.eval_gate_service import (
    run_evals,
    eval_gate,
    build_subprocess_invoke_fn,
)

logger = logging.getLogger('sistema_fretes')

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
    import pathlib
    evals_dir = (
        pathlib.Path(__file__).resolve().parent.parent.parent.parent
        / '.claude' / 'evals' / 'subagents'
    )
    return [
        ('analista-carteira', str(evals_dir / 'analista-carteira' / 'dataset.yaml')),
        ('auditor-financeiro', str(evals_dir / 'auditor-financeiro' / 'dataset.yaml')),
        ('controlador-custo-frete', str(evals_dir / 'controlador-custo-frete' / 'dataset.yaml')),
        ('gestor-motos-assai', str(evals_dir / 'gestor-motos-assai' / 'dataset.yaml')),
    ]


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


def _run_eval_batch_in_context(datasets: list) -> dict:
    """Executa o eval batch dentro de app_context ativo.

    Separado para testabilidade (espelha _triage_step_shadow_in_context).
    Cada agente roda em try/except ISOLADO (constraint 4). Ao final, UM
    db.session.commit() consolida todos os SAVEPOINTs de insert_score
    (constraint 3); rollback em caso de erro no commit.
    """
    from app import db
    from app.agente.models import AgentEvalScore

    git_sha = _current_git_sha()
    scores = {}

    for agent_name, dataset_path in datasets:
        try:
            # CONSTRAINT 1: baseline ANTES de insert_score (senao o "mais
            # recente" seria o proprio run atual → delta sempre ~0).
            baseline = AgentEvalScore.get_baseline_score(agent_name)

            # Wiring REAL do agente. AGENT_EVAL_MODEL opcional (override de modelo).
            invoke = build_subprocess_invoke_fn(
                agent_name,
                model=os.environ.get('AGENT_EVAL_MODEL') or None,
            )

            # judge_fn default = Haiku real (mockado nos testes).
            result = run_evals(agent_name, dataset_path, invoke_fn=invoke)

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
            # CONSTRAINT 4: um agente falhando NAO impede os demais.
            logger.warning(f'[EVAL_RUNNER] {agent_name}: erro ao rodar evals: {exc}')

    # CONSTRAINT 3: commit explicito — insert_score usa SAVEPOINT que NAO
    # commita sozinho no job RQ (create_app sem transacao pai).
    try:
        db.session.commit()
    except Exception as commit_err:
        logger.error(f'[EVAL_RUNNER] commit falhou: {commit_err}')
        try:
            db.session.rollback()
        except Exception:
            pass

    logger.info(f'[EVAL_RUNNER] concluido: agentes={len(scores)}')
    return {'agentes': len(scores), 'scores': scores}


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


if __name__ == '__main__':
    # Ativacao supervisionada manual (Fase 2): roda 1 dataset SINCRONO.
    #   python -m app.agente.workers.eval_runner --agent analista-carteira
    import argparse

    parser = argparse.ArgumentParser(
        description='Roda o eval REAL de UM subagente (sincrono, supervisionado).'
    )
    parser.add_argument(
        '--agent', required=True,
        help='Nome do subagente (ex: analista-carteira).',
    )
    args = parser.parse_args()

    out = run_eval_batch(agent_filter=args.agent)
    print(f'[EVAL_RUNNER] resultado: {out}')
