"""
Triage shadow — B-TRIAGE wiring em SHADOW (Tarefa 2c, Onda 2).

Roda o classificador semântico meta→steps (`triage_meta`, plan_triage.py) em
modo SHADOW para UM step e grava o veredito em outcome_signal['triage'].

PRINCÍPIO:
    `triage_meta` decompõe a META do turno (1ª/N-ésima mensagem role=='user')
    em steps de plano ancorados em entidades reais do KG. O veredito é
    `{'steps': [...], 'grounded_entities': [...]}`. Mesmo um veredito VAZIO
    (`steps=[], grounded_entities=[]`) é VÁLIDO (a meta não decompôs) e é
    gravado — só se PULA o write se a meta for None (sem texto de usuário,
    grava skipped='no_meta' para não re-tentar) ou se triage_meta LEVANTAR
    (caso ~teórico, dado que é best-effort — nesse caso NÃO grava p/ permitir
    retry no próximo ciclo).

SHADOW (off-SSE, flag-OFF):
    Nenhum hook/SSE/loop do agente chama estas funções. O enqueue automático
    vem do varredor batch `enqueue_pending_triages`, gateado pela flag
    USE_AGENT_PLANNER (app/agente/config/feature_flags.py, OFF por default).

Padrão clonado de: app/agente/workers/plan_verifier.py
  (verify_step_shadow + enqueue_pending_verifies — mesmo molde de job-shadow).
CRITICAL-1 replicado: db.session.commit() explícito após update_outcome —
sem ele, o SAVEPOINT do begin_nested()+flush() nunca consolida quando o
app_context do job RQ morre, e o veredito é descartado silenciosamente.
"""
import logging
from datetime import timedelta
from typing import Optional

from app import create_app

logger = logging.getLogger('sistema_fretes')

# Fila RQ (LEVE) onde o varredor batch enfileira triage_step_shadow.
# REUSA a mesma fila do step_judge/plan_verifier ('agent_judge') — todos são
# jobs leves de avaliação pós-turno, classificados fora de FILAS_PESADAS
# (worker_render.py).
TRIAGE_QUEUE_NAME = 'agent_judge'


def _extract_user_message_text(session, turn_seq: Optional[int]) -> Optional[str]:
    """Extrai o texto da META (mensagem do usuário) correspondente ao turno.

    Mapeia turn_seq (sufixo do step_uid após ':') → a N-ésima mensagem do
    USUÁRIO em session.data['messages'].

    Correlação (ver app/agente/routes/chat.py:1836): turn_seq é a CONTAGEM de
    mensagens role=='user' APÓS add_user_message. Para o N-ésimo turno,
    turn_seq=N corresponde à N-ésima mensagem do usuário (1-based) — que é o
    META daquele turno.

    Degrade (best-effort): se turn_seq não mapear com segurança (None, fora de
    range), retorna a ÚLTIMA mensagem do usuário da sessão. Se não houver
    nenhuma → None.

    Espelha plan_verifier._extract_assistant_response_text, mas filtrando
    role=='user'.
    """
    try:
        messages = session.get_messages() if session else []
    except Exception:
        messages = []

    user_msgs = [
        m for m in (messages or [])
        if isinstance(m, dict) and m.get('role') == 'user'
    ]
    if not user_msgs:
        return None

    # Mapeamento direto: turn_seq=N → N-ésima (1-based) mensagem do usuário
    if turn_seq is not None and 1 <= turn_seq <= len(user_msgs):
        content = user_msgs[turn_seq - 1].get('content')
        if content:
            return content

    # Degrade: última mensagem do usuário
    last_content = user_msgs[-1].get('content')
    return last_content or None


def triage_step_shadow(step_uid: str) -> None:
    """Job RQ orquestrador: roda triage_meta (shadow) e persiste veredito.

    Estrutura (mesmo esqueleto de verify_step_shadow):
    1. create_app() + app_context()
    2. Carrega AgentStep pelo step_uid; se None → log + return
    3. Carrega AgentSession por session_id; extrai turn_seq do step_uid;
       extrai meta = N-ésima mensagem do usuário.
    4. Chama triage_meta(meta, user_id) (best-effort — se LEVANTAR, log + return
       SEM gravar, p/ permitir retry no próximo ciclo).
    5. Grava AgentStep.update_outcome({'triage': resultado}) + commit EXPLÍCITO
       (CRITICAL-1 — SAVEPOINT não commita sozinho no job RQ).

    Best-effort total (INV-6): qualquer exceção é logada e o job retorna silencioso.

    SHADOW: enqueue via enqueue_pending_triages sob USE_AGENT_PLANNER (OFF default).
    """
    logger.info(
        f'[triage_shadow] iniciando: step_uid={step_uid[:40] if step_uid else "N/A"}'
    )

    try:
        app = create_app()
        with app.app_context():
            _triage_step_shadow_in_context(step_uid)
    except Exception as exc:
        logger.error(f'[triage_shadow] falha inesperada: {exc}')


def _triage_step_shadow_in_context(step_uid: str) -> None:
    """Executa o triage dentro de app_context ativo.

    Separado para evitar aninhamento em testes (espelha
    plan_verifier._verify_step_shadow_in_context).
    """
    from app.agente.models import AgentStep, AgentSession

    step = AgentStep.query.filter_by(step_uid=step_uid).first()
    if step is None:
        logger.warning(f'[triage_shadow] step_uid={step_uid} não encontrado, abortando')
        return

    # Carrega a sessão (best-effort) para extrair a meta do turno.
    session = None
    try:
        session = AgentSession.query.filter_by(session_id=step.session_id).first()
    except Exception as exc:
        logger.debug(f'[triage_shadow] sessão não carregada (best-effort): {exc}')

    # turn_seq = sufixo do step_uid após ':' (step_uid = '{session_id}:{turn_seq}')
    turn_seq: Optional[int] = None
    try:
        suffix = step_uid.rsplit(':', 1)[-1]
        turn_seq = int(suffix)
    except (ValueError, IndexError):
        turn_seq = None

    meta = _extract_user_message_text(session, turn_seq)

    # Sem texto de usuário → grava veredito skipped='no_meta'. Mantém shape de
    # veredito válido (steps/grounded_entities vazios) para NÃO re-enfileirar
    # eternamente um step sem mensagem de usuário.
    if not meta:
        resultado = {'steps': [], 'grounded_entities': [], 'skipped': 'no_meta'}
    else:
        # triage_meta é best-effort (NUNCA levanta). Ainda assim envolvemos em
        # try/except: se LEVANTAR (caso ~teórico), NÃO gravamos, permitindo
        # retry no próximo ciclo (espelha verify_step_shadow guard de retry).
        try:
            from app.agente.sdk.plan_triage import triage_meta
            resultado = triage_meta(meta, user_id=step.user_id or 0)
        except Exception as exc:
            logger.error(
                f'[triage_shadow] triage_meta levantou para step_uid={step_uid}: {exc} '
                f'— abortando persistencia (permite retry no proximo ciclo)'
            )
            return

    AgentStep.update_outcome(step_uid, {'triage': resultado})

    # CRITICAL-1 (espelha plan_verifier/step_judge): commit explícito obrigatório.
    # update_outcome usa begin_nested()+flush() (SAVEPOINT) — desenhado para
    # rodar DENTRO de transação pai que alguém commita. No job RQ,
    # triage_step_shadow abre create_app()+app_context() SEM transação pai,
    # então o flush nunca commita e o veredito é descartado quando o app_context
    # morre. Replicamos a mesma lição.
    from app import db
    try:
        db.session.commit()
    except Exception as commit_err:
        logger.error(f'[triage_shadow] commit falhou: {commit_err}')
        db.session.rollback()
        return

    n_steps = len(resultado.get('steps', []))
    logger.info(
        f'[triage_shadow] concluído: step_uid={step_uid[:40]} '
        f'steps={n_steps} grounded={len(resultado.get("grounded_entities", []))}'
        f'{" (skipped=no_meta)" if resultado.get("skipped") == "no_meta" else ""}'
    )


def enqueue_pending_triages(queue=None, now=None, lookback_hours=6, limit=50) -> dict:
    """Varredor RQ batch (Tarefa 2c): enfileira triage_step_shadow para steps
    recentes sem veredito 'triage'.

    WIRING shadow sob a flag USE_AGENT_PLANNER (OFF por default). Espelha
    enqueue_pending_verifies (plan_verifier.py) / enqueue_pending_judges.

    Comportamento:
    1. Gate pela flag (import LAZY p/ patch de teste): se OFF, retorna sem
       tocar em Redis/Queue.
    2. Janela: candidatos = steps com created_at em [now-lookback, now].
    3. Filtro Python: candidato = step SEM 'triage' em outcome_signal.
    4. Enfileira triage_step_shadow com job_id determinístico RQ-safe
       (':' → '-', pois RQ 2.6.1 Job.set_id rejeita ':').
    5. Best-effort total (INV-6): falha de Redis NÃO levanta exceção.

    Returns:
        {'enfileirados': int, 'candidatos': int} (+ 'skipped' quando aplicável).
    """
    # 1. Gate — import LAZY (permite patch de USE_AGENT_PLANNER em teste)
    from app.agente.config.feature_flags import USE_AGENT_PLANNER
    if not USE_AGENT_PLANNER:
        return {'enfileirados': 0, 'candidatos': 0, 'skipped': 'flag_off'}

    from app.utils.timezone import agora_utc_naive
    from app.agente.models import AgentStep

    if now is None:
        now = agora_utc_naive()
    corte = now - timedelta(hours=lookback_hours)

    # 2. Query — usa o índice de created_at; janela superior fecha em `now`
    steps = (
        AgentStep.query
        .filter(AgentStep.created_at >= corte)
        .filter(AgentStep.created_at <= now)
        .order_by(AgentStep.created_at.asc())
        .limit(limit)
        .all()
    )

    # 3. Filtro Python — candidato = sem veredito 'triage'
    candidatos = [s for s in steps if 'triage' not in (s.outcome_signal or {})]

    if not candidatos:
        logger.info("[triage_enqueuer] enfileirados=0 candidatos=0")
        return {'enfileirados': 0, 'candidatos': 0}

    # 4. Construir fila real inline se não injetada (best-effort — INV-6)
    if queue is None:
        try:
            import os
            from rq import Queue
            import redis

            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            queue = Queue(TRIAGE_QUEUE_NAME, connection=r)
        except Exception as e:
            logger.error(f"[triage_enqueuer] Redis indisponivel, abortando best-effort: {e}")
            return {
                'enfileirados': 0,
                'candidatos': len(candidatos),
                'skipped': 'redis_error',
            }

    # 5. Enfileirar
    enfileirados = 0
    for step in candidatos:
        try:
            # job_id determinístico p/ RASTREABILIDADE. Sanitiza TODOS os ':':
            # step_uid é '{session_id}:{turn_seq}' (sempre contém ':') e RQ 2.6.1
            # Job.set_id levanta ValueError se ':' in id. Sem o replace, o
            # try/except engoliria a exceção e enfileirados=0 (feature inerte).
            job_id = f"triage-step-{step.step_uid.replace(':', '-')}"
            queue.enqueue(
                'app.agente.workers.triage_shadow.triage_step_shadow',
                step.step_uid,
                job_id=job_id,
                job_timeout=120,
            )
            enfileirados += 1
        except Exception as e:
            logger.warning(
                f"[triage_enqueuer] enqueue falhou para step_uid={step.step_uid}: {e}"
            )

    logger.info(
        f"[triage_enqueuer] enfileirados={enfileirados} candidatos={len(candidatos)}"
    )
    return {'enfileirados': enfileirados, 'candidatos': len(candidatos)}
