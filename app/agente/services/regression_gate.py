"""
Gate puro de regressão (baseline × candidate) usado pela promoção A4.

ORIGEM (estratégia R2, 2026-06-12, ESTRATEGIA_ATUADORES_2026-06-06.md):
única função VIVA do antigo `eval_gate_service.py` (A3, aposentado — ROADMAP
O1.4). O resto do módulo A3 (run_evals, eval_runner, golden datasets, judges
Haiku, fila RQ 'agent_eval', flag AGENT_EVAL_GATE) foi REMOVIDO: o eval
periódico nunca atuou (flag default-false e OFF em PROD desde a aposentadoria
do A3 em 2026-06-03 — ver docs/blueprint-agente/EXECUCAO.md).

Esta função é PURA (sem DB/LLM): compara dois scores e decide se houve
regressão. Caller vivo: directive_promotion_service.evaluate_and_promote
(sempre em mode='report_only' — nunca bloqueia).
"""
import logging

logger = logging.getLogger('sistema_fretes')


def eval_gate(
    baseline_score: float,
    candidate_score: float,
    threshold: float = 0.05,
    mode: str = 'report_only',
) -> dict:
    """Compara score candidate vs baseline e decide se bloqueia (gate).

    Args:
        baseline_score: Score de referencia (0-1).
        candidate_score: Score do candidato a avaliar (0-1).
        threshold: Queda minima para ser considerada regressao (default 0.05).
        mode: 'report_only' (default) ou 'enforce'.
            - 'report_only': blocked=False SEMPRE. So' detecta e loga.
            - 'enforce': blocked=True se candidate < baseline - threshold.

    Returns:
        Dict com {regression: bool, blocked: bool, delta: float}

    INVARIANTE: Em mode='report_only', blocked e' SEMPRE False.
    """
    delta = candidate_score - baseline_score
    regression = delta < -threshold

    if mode == 'enforce':
        blocked = regression
    else:
        # report_only (default e qualquer outro valor): NUNCA bloqueia
        blocked = False

    if regression:
        logger.warning(
            f"[eval_gate] REGRESSAO DETECTADA: "
            f"baseline={baseline_score:.3f} candidate={candidate_score:.3f} "
            f"delta={delta:+.3f} threshold={threshold:.3f} "
            f"mode={mode} blocked={blocked}"
        )
    else:
        logger.info(
            f"[eval_gate] Gate OK: "
            f"baseline={baseline_score:.3f} candidate={candidate_score:.3f} "
            f"delta={delta:+.3f}"
        )

    return {
        'regression': regression,
        'blocked': blocked,
        'delta': delta,
    }
