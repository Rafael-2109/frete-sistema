"""
A4 (Onda 3) — Promoção Automática de Diretriz. Fecha o flywheel.

SHADOW puro + flag-OFF:
    Só LOGA, NÃO escreve no banco. Flag AGENT_DIRECTIVE_PROMOTION OFF por default.
    Sem caller ativo (nenhum hook/D8 invoca este módulo ainda).

Flywheel:
    sinais (E1/E2 em agent_step.outcome_signal)
    → eval gate (A3, eval_gate_service.py, Onda 3)
    → A4: PROMOVE diretriz operacional que funcionou

"Diretriz" = heurística empresa em AgentMemory (user_id=0,
path /memories/empresa/heuristicas/, lida por
memory_injection._build_operational_directives quando
importance_score>=0.7 + nivel>=5).

BLOQUEADO para escrita REAL até:
1. USE_AGENT_PLANNER ON em PROD (base PlanState)
2. Baseline A3 estável (14d de coleta)
3. Coluna directive_status em agent_memories (migration pendente)
   + audit hook Odoo PROD ativo

Anti-gaming (R9 / step_judge._judge_core):
    Se a sessão de origem teve FALHA_ODOO, o sinal ambiental DOMINA.
    Mesmo padrão de step_judge._judge_core: ambiental > texto.
    Na dúvida (erro de consulta): NÃO promove (conservador = True).

Ref: app/agente/workers/step_judge.py (_judge_core heurística ambiental)
Ref: app/agente/services/eval_gate_service.py (eval_gate)
Ref: app/agente/sdk/plan_state.py (PlanState — plano que funcionou)
Ref: app/agente/sdk/memory_injection.py:420 (_build_operational_directives)
"""
import logging
from typing import Optional

logger = logging.getLogger('sistema_fretes')

# Status discriminado no resultado de evaluate_and_promote
_DECISION_WOULD_PROMOTE = 'would_promote'
_DECISION_REJECTED = 'rejected'


# ---------------------------------------------------------------------------
# propose_directive_from_plan
# ---------------------------------------------------------------------------

def propose_directive_from_plan(
    plan_dict: Optional[dict],
    session_id: str,
) -> Optional[dict]:
    """
    Extrai candidata a diretriz de um plano bem-sucedido (todos os steps completed).

    Heurística simples determinística (sem LLM):
    - Título: derivado dos subjects dos steps
    - When: "Quando o agente executa: {subjects dos steps}"
    - Prescrição: "Sequência bem-sucedida: {sujeitos concatenados}"

    PURO (sem DB). Chamado por wiring futuro (Stop hook / D8 cron).

    Args:
        plan_dict: Serialização do PlanState (dict com chave 'steps').
                   Tolerante: None ou dict inválido → None.
        session_id: Identificador da sessão de origem (para rastreabilidade).

    Returns:
        dict candidata com campos:
            titulo, when, prescricao, source_session_id, status='candidata'
        ou None se o plano não for totalmente concluído.
    """
    if not plan_dict or not isinstance(plan_dict, dict):
        return None

    steps = plan_dict.get('steps')
    if not steps or not isinstance(steps, dict):
        return None

    # Todos os steps DEVEM estar completed — qualquer outro status cancela a promoção
    for task_id, step in steps.items():
        status = step.get('status', '')
        if status != 'completed':
            logger.debug(
                f"[directive_promotion] propose: step {task_id!r} "
                f"status={status!r} != 'completed' → plano não concluído"
            )
            return None

    # Extrair subjects para construir a diretriz
    subjects = [
        step.get('subject', '') or step.get('description', '') or f'passo-{tid}'
        for tid, step in steps.items()
    ]
    subjects_clean = [s.strip() for s in subjects if s.strip()]

    if not subjects_clean:
        # Steps existem mas sem subjects úteis — gera título genérico
        subjects_clean = [f'passo-{i + 1}' for i in range(len(steps))]

    # Heurística determinística para campos da candidata
    titulo = _derivar_titulo(subjects_clean)
    when = f"Quando o agente executa: {'; '.join(subjects_clean[:3])}"
    prescricao = (
        f"Sequência bem-sucedida ({len(subjects_clean)} passos): "
        + " → ".join(subjects_clean[:5])
    )
    if len(subjects_clean) > 5:
        prescricao += f" [+{len(subjects_clean) - 5} passos]"

    candidata = {
        'titulo': titulo,
        'when': when,
        'prescricao': prescricao,
        'source_session_id': session_id,
        'status': 'candidata',
    }

    logger.info(
        f"[directive_promotion] propose: candidata extraída "
        f"session={session_id!r} titulo={titulo!r}"
    )
    return candidata


def _derivar_titulo(subjects: list) -> str:
    """Deriva título curto a partir dos subjects dos steps."""
    if not subjects:
        return 'Fluxo de trabalho bem-sucedido'
    # Usa o primeiro subject como base do título
    primeiro = subjects[0][:60].strip()
    if len(subjects) > 1:
        return f"Fluxo: {primeiro} [{len(subjects)} passos]"
    return f"Fluxo: {primeiro}"


# ---------------------------------------------------------------------------
# _query_falha_odoo — separada para facilitar mock em testes
# ---------------------------------------------------------------------------

def _query_falha_odoo(session_id: str) -> list:
    """
    Executa a query em operacao_odoo_auditoria filtrada por session_id.

    Separada de _tem_falha_odoo para permitir mock preciso nos testes
    sem precisar mockar o ORM inteiro.

    Returns:
        Lista de objetos OperacaoOdooAuditoria (pode ser []).

    Raises:
        Exception: qualquer erro de DB ou import é propagado para o caller,
                   que decide o comportamento conservador.
    """
    from app.odoo.models.operacao_odoo_auditoria import OperacaoOdooAuditoria
    return OperacaoOdooAuditoria.query.filter_by(
        session_id=session_id,
        contexto_origem='execute_kw_hook',
    ).all()


# ---------------------------------------------------------------------------
# _tem_falha_odoo
# ---------------------------------------------------------------------------

def _tem_falha_odoo(session_id: str) -> bool:
    """
    Verifica se a sessão de origem teve alguma operação FALHA_ODOO.

    Anti-reward-hacking (R9 / step_judge._judge_core):
    O sinal ambiental DOMINA. Se houve FALHA_ODOO, o contexto da sessão
    foi contaminado por erro operacional — a sequência que "funcionou"
    pode ser espúria (ex: o plano completou porque as operações falharam
    silenciosamente e o modelo seguiu em frente).

    CONSERVADOR: em caso de erro na consulta → True (bloqueia promoção).
    Justificativa: é impossível saber se o ambiente estava limpo.
    Preferir falso positivo (rejeitar candidata válida) a falso negativo
    (promover candidata em sessão contaminada).

    Espelho de step_judge._judge_core linha ~155:
        tem_falha_odoo = any(
            getattr(op, 'status', '') == 'FALHA_ODOO'
            for op in odoo_ops
        )

    Args:
        session_id: UUID da sessão de origem da candidata.

    Returns:
        True se há evidência de FALHA_ODOO OU se a consulta falhar.
        False apenas se a consulta retornar vazia ou todos os registros
        forem EXECUTADO/EXECUTADO_PARCIAL/etc.
    """
    try:
        ops = _query_falha_odoo(session_id)
        resultado = any(
            getattr(op, 'status', '') == 'FALHA_ODOO'
            for op in ops
        )
        logger.debug(
            f"[directive_promotion] _tem_falha_odoo: "
            f"session={session_id!r} ops={len(ops)} resultado={resultado}"
        )
        return resultado
    except Exception as exc:
        # CONSERVADOR: erro → bloqueia. Não sabemos se o ambiente estava limpo.
        logger.warning(
            f"[directive_promotion] _tem_falha_odoo: erro na consulta "
            f"session={session_id!r} → True conservador. Erro: {exc}"
        )
        return True


# ---------------------------------------------------------------------------
# _persist_directive — STUB DOCUMENTADO (não implementado)
# ---------------------------------------------------------------------------

def _persist_directive(candidata: dict) -> None:
    """
    STUB DOCUMENTADO — Persiste diretriz em AgentMemory.

    NÃO implementado intencionalmente. Precisa de:
    1. Coluna directive_status em agent_memories (migration pendente)
    2. USE_AGENT_PLANNER ON em PROD (base PlanState consolidada)
    3. Baseline A3 estável (14d de coleta para comparação de scores)
    4. Revisão manual das primeiras candidatas antes de ativar escrita

    Quando implementado, seguirá o padrão de memory_injection.py:
        AgentMemory(
            user_id=0,  # empresa
            path=f'/memories/empresa/heuristicas/{slug_titulo}.xml',
            content=_formatar_xml(candidata),
            importance_score=0.7,  # threshold de _build_operational_directives
            nivel=5,               # nível de heurística operacional
            directive_status='promoted',
        )

    Por enquanto: NotImplementedError documentada.
    O caller (evaluate_and_promote) usa flag AGENT_DIRECTIVE_PROMOTION
    para decidir se chama este stub — quando OFF (default), nunca é chamado.
    """
    raise NotImplementedError(
        "_persist_directive: stub documentado. "
        "Implementar quando: (1) coluna directive_status em agent_memories, "
        "(2) USE_AGENT_PLANNER ON PROD, (3) baseline A3 14d. "
        "Ver app/agente/services/directive_promotion_service.py docstring."
    )


# ---------------------------------------------------------------------------
# evaluate_and_promote
# ---------------------------------------------------------------------------

def evaluate_and_promote(
    candidate: dict,
    baseline_score: float,
    candidate_score: float,
) -> dict:
    """
    Avalia candidata a diretriz e decide promoção (shadow: só LOGA).

    Pipeline:
        1. Anti-gaming (R9): se _tem_falha_odoo → rejected (ambiental domina)
        2. Regression gate (A3): eval_gate(baseline, candidate, mode='report_only')
           — regressão → rejected (candidata pior que baseline)
        3. SHADOW: se passou → would_promote, só LOGA (NÃO escreve no banco)

    Persistência real (stub): _persist_directive() levanta NotImplementedError.
    Sob AGENT_DIRECTIVE_PROMOTION ON (futuro), o ramo de escrita seria ativado.
    Hoje: flag OFF → evaluate_and_promote não é chamado por nenhum caller ativo.

    Args:
        candidate: dict com campos titulo, when, prescricao,
                   source_session_id, status='candidata'.
        baseline_score: score de referência do eval gate (0-1).
        candidate_score: score da sessão candidata (0-1).

    Returns:
        dict com:
            decision: 'would_promote' | 'rejected'
            reason: str (presente em rejected; ausente ou vazio em would_promote)
            candidata: dict (presente em would_promote)
            gate: dict (resultado do eval_gate — presente quando não bloqueado por anti-gaming)
    """
    session_id = candidate.get('source_session_id', '')

    # ─── 1. Anti-gaming: sinal ambiental DOMINA ──────────────────────────────
    # Verificar ANTES do gate — se há FALHA_ODOO, nem precisamos calcular scores.
    # Espelho de step_judge._judge_core: "If QUALQUER op tem status == 'FALHA_ODOO'"
    if _tem_falha_odoo(session_id):
        logger.warning(
            f"[directive_promotion] REJECTED (falha_odoo_ambiental): "
            f"session={session_id!r} titulo={candidate.get('titulo', '?')!r}"
        )
        return {
            'decision': _DECISION_REJECTED,
            'reason': 'falha_odoo_ambiental',
        }

    # ─── 2. Regression gate (A3, report_only) ────────────────────────────────
    from app.agente.services.eval_gate_service import eval_gate

    gate_result = eval_gate(
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        threshold=0.05,
        mode='report_only',
    )

    if gate_result.get('regression'):
        logger.warning(
            f"[directive_promotion] REJECTED (regressao): "
            f"session={session_id!r} "
            f"baseline={baseline_score:.3f} candidate={candidate_score:.3f} "
            f"delta={gate_result.get('delta', 0):+.3f}"
        )
        return {
            'decision': _DECISION_REJECTED,
            'reason': f"regressao_detectada (delta={gate_result.get('delta', 0):+.3f})",
            'gate': gate_result,
        }

    # ─── 3. SHADOW: só loga, NÃO escreve ─────────────────────────────────────
    # Quando AGENT_DIRECTIVE_PROMOTION ON (futuro):
    #     _persist_directive(candidate)  # escrita real em AgentMemory
    # Por enquanto: stub nunca chamado (flag OFF, sem caller ativo).
    logger.info(
        f"[directive_promotion] WOULD_PROMOTE (shadow): "
        f"session={session_id!r} "
        f"titulo={candidate.get('titulo', '?')!r} "
        f"baseline={baseline_score:.3f} candidate={candidate_score:.3f} "
        f"— flag AGENT_DIRECTIVE_PROMOTION=OFF, NÃO persiste"
    )

    return {
        'decision': _DECISION_WOULD_PROMOTE,
        'candidata': candidate,
        'gate': gate_result,
        'source_session_id': session_id,
    }
