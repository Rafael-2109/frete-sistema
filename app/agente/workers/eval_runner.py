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
    from sqlalchemy.exc import OperationalError

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
            result = run_evals(agent_name, dataset_path, invoke_fn=invoke)
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
    except OperationalError as commit_err:
        # BUG-2: SSL-drop no 1o commit. Rollback forca reconexao; RE-EXECUTA a
        # persistencia (rollback descartou os SAVEPOINTs) e tenta o commit 1x mais.
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
