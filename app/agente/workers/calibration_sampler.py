"""
Sampler de calibração do ONLINE judge (E3 re-apontado — GATE-1).

Após a aposentadoria do A3 (2026-06-03, eval LLM caro VETADO), a calibração do
judge deixa de ser alimentada pelo `eval_runner` (morto) e passa a popular
`agent_eval_case` a partir dos vereditos do ONLINE judge gravados em
`agent_step.outcome_signal['judge']` (vivo em PROD via step_judge.py).

Habilita:
  - spot-check humano de 5-10% (AgentEvalCase.sample_unreviewed);
  - métrica de concordância judge-vs-humano (AgentEvalCase.concordance_rate).

PRIORIZAÇÃO (achado Task 3 — `plans/2026-06-03-gate1-calibracao-judge-online.md`):
os casos `judge.label='success' ∧ verify.adversarial.refuted=true` são discordâncias
de ALTO VALOR de calibração (o judge diz bom, o cético substantivo refuta) — sinalizam
o viés de CREDULIDADE do judge. São marcados (prioridade + razão do adversarial na
evidence) para a UI de revisão (Task 5) destacá-los.

Gate: USE_AGENT_EVAL_CALIBRATION (OFF por default). Best-effort total (INV-6).
SHADOW: o wiring (módulo D8 no scheduler) é a Task 4 Step 3 — sem caller automático
nesta versão.
"""
import logging
from datetime import timedelta
from typing import Optional

logger = logging.getLogger('sistema_fretes')

# agent_name marcador dos casos de calibração do online judge (o A3/subagentes
# morreu — sem conflito com os antigos casos por-subagente do eval_runner).
CALIBRATION_AGENT_NAME = '__online_judge__'
PASS_THRESHOLD = 0.70  # case_score >= -> status 'pass' (success~0.85 vs partial~0.45)


def _map_judge_to_case_fields(step) -> Optional[dict]:
    """Mapeia o veredito do online judge para os campos de AgentEvalCase.

    Função PURA (sem DB) — testável com um step falso. Retorna None se o step não
    tem veredito 'judge' em outcome_signal.

    Chaves retornadas: agent_name, case_id, case_score, status, evidence, prioridade.
    (`prioridade` é metadado p/ o varredor — NÃO é coluna; o sinal de prioridade
    fica também embutido na `evidence` via marcador ⚠ADVERSARIAL.)
    """
    outcome = step.outcome_signal or {}
    judge = outcome.get('judge')
    if not judge:
        return None

    label = str(judge.get('label', '?'))
    try:
        score = float(judge.get('score', 0) or 0)
    except (TypeError, ValueError):
        score = 0.0
    case_score = round(score / 100.0, 4)
    status = 'pass' if case_score >= PASS_THRESHOLD else 'fail'
    evidencia = str(judge.get('evidencia', '') or '')

    # Discordância de ALTO VALOR (Task 3): judge=success refutado pelo adversarial.
    adversarial = (outcome.get('verify') or {}).get('adversarial') or {}
    adv_refuted = adversarial.get('refuted') is True
    prioridade = (label == 'success') and adv_refuted

    evidence = f"label={label} score={int(score)} | {evidencia[:400]}"
    if prioridade:
        adv_reason = str(adversarial.get('reason', '') or '')[:300]
        evidence += f" | ⚠ADVERSARIAL REFUTOU: {adv_reason}"

    return {
        'agent_name': CALIBRATION_AGENT_NAME,
        'case_id': step.step_uid,
        'case_score': case_score,
        'status': status,
        'evidence': evidence,
        'prioridade': prioridade,
    }


def populate_calibration_cases(now=None, lookback_hours=24, limit=200) -> dict:
    """Varredor (E3): popula `agent_eval_case` a partir dos steps com veredito do
    online judge — substitui a fonte morta (`eval_runner`/A3).

    Comportamento (espelha `step_judge.enqueue_pending_judges`, mas SÍNCRONO —
    insert direto em DB, sem RQ, pois é leve):
    1. Gate USE_AGENT_EVAL_CALIBRATION (import LAZY p/ patch de teste). OFF = no-op.
    2. Janela: steps com `created_at` em [now-lookback, now].
    3. Mapeia (via `_map_judge_to_case_fields`) só os que têm veredito judge.
    4. Dedup: pula `case_id` (=step_uid) já presente em `agent_eval_case` (idempotente).
    5. insert_case (SAVEPOINT) + commit explícito. Best-effort (INV-6).

    Returns: {'inseridos': int, 'candidatos': int, 'prioritarios': int} (+ 'skipped').
    """
    from app.agente.config.feature_flags import USE_AGENT_EVAL_CALIBRATION
    if not USE_AGENT_EVAL_CALIBRATION:
        return {'inseridos': 0, 'candidatos': 0, 'prioritarios': 0, 'skipped': 'flag_off'}

    from app.utils.timezone import agora_utc_naive
    from app.agente.models import AgentStep, AgentEvalCase
    from app import db

    if now is None:
        now = agora_utc_naive()
    corte = now - timedelta(hours=lookback_hours)

    steps = (
        AgentStep.query
        .filter(AgentStep.created_at >= corte)
        .filter(AgentStep.created_at <= now)
        .order_by(AgentStep.created_at.asc())
        .limit(limit)
        .all()
    )

    mapeados = [f for f in (_map_judge_to_case_fields(s) for s in steps) if f is not None]
    if not mapeados:
        logger.info("[CALIBRATION_SAMPLER] inseridos=0 candidatos=0")
        return {'inseridos': 0, 'candidatos': 0, 'prioritarios': 0}

    # Dedup: case_ids já existentes para o agente de calibração.
    case_ids = [m['case_id'] for m in mapeados]
    existentes = set()
    try:
        rows = (
            AgentEvalCase.query
            .filter(AgentEvalCase.agent_name == CALIBRATION_AGENT_NAME)
            .filter(AgentEvalCase.case_id.in_(case_ids))
            .with_entities(AgentEvalCase.case_id)
            .all()
        )
        existentes = {r[0] for r in rows}
    except Exception as e:
        logger.debug(f"[calibration_sampler] dedup query falhou (best-effort): {e}")

    inseridos = 0
    prioritarios = 0
    for m in mapeados:
        if m['case_id'] in existentes:
            continue
        entry = AgentEvalCase.insert_case(
            agent_name=m['agent_name'],
            case_id=m['case_id'],
            case_score=m['case_score'],
            status=m['status'],
            evidence=m['evidence'],
        )
        if entry is not None:
            inseridos += 1
            if m['prioridade']:
                prioritarios += 1

    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"[calibration_sampler] commit falhou: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass

    logger.info(
        f"[CALIBRATION_SAMPLER] inseridos={inseridos} candidatos={len(mapeados)} "
        f"prioritarios={prioritarios}"
    )
    return {'inseridos': inseridos, 'candidatos': len(mapeados), 'prioritarios': prioritarios}
