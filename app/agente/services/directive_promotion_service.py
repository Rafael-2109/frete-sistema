"""
A4 (Onda 3) — Promoção Automática de Diretriz. Fecha o flywheel.

SHADOW puro + flag-OFF:
    evaluate_and_promote() só LOGA (flag OFF), NÃO chama _persist_directive.
    _persist_directive() escreve no banco quando chamado diretamente (Task 3).
    Flag AGENT_DIRECTIVE_PROMOTION OFF por default — nenhum caller ativo ainda.

Flywheel:
    sinais (E1/E2 em agent_step.outcome_signal)
    → eval gate (A3, eval_gate_service.py, Onda 3)
    → A4: PROMOVE diretriz operacional que funcionou

"Diretriz" = heurística empresa em AgentMemory (user_id=0,
path /memories/empresa/heuristicas/, lida por
memory_injection._build_operational_directives quando
importance_score>=0.7 + nivel>=5).

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
import re as _re
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
# _slug_titulo + _formatar_xml_diretriz + _persist_directive
# ---------------------------------------------------------------------------

def _slug_titulo(titulo: str) -> str:
    """Deriva slug URL-safe a partir do título da candidata (max 80 chars)."""
    base = (titulo or 'diretriz').lower().strip()
    base = _re.sub(r'[^a-z0-9]+', '-', base).strip('-')
    return (base or 'diretriz')[:80]


def _formatar_xml_diretriz(candidata: dict) -> str:
    """
    Formata a candidata como XML heurística empresa (formato canônico A4).

    Usa _xml_escape de pattern_analyzer — mesmo helper de escape das heurísticas
    orgânicas extraídas por extrair_conhecimento_sessao().

    Formato XML processado pelo builder via regex XML-first
    (<titulo>/<when>/<prescricao>). Diverge do formato orgânico compacto
    WHEN:/DO: do pattern_analyzer, mas é compatível com
    _build_operational_directives (que aceita AMBOS: regex XML-first e
    fallback WHEN:/DO:).

    O content resultante:
    - Passa _is_nivel_5() via '<nivel>5</nivel>'
    - Tem <prescricao> não-vazia para ser renderável pelo builder
    """
    from .pattern_analyzer import _xml_escape  # mesmo helper das heurísticas orgânicas
    titulo = _xml_escape(candidata.get('titulo', ''))
    when = _xml_escape(candidata.get('when', ''))
    presc = _xml_escape(candidata.get('prescricao', ''))
    origem = _xml_escape(candidata.get('source_session_id', ''))
    return (
        '<heuristica>\n'
        '  <nivel>5</nivel>\n'
        f'  <titulo>{titulo}</titulo>\n'
        f'  <when>{when}</when>\n'
        f'  <prescricao>{presc}</prescricao>\n'
        f'  <origem>promovida automaticamente da sessão {origem}</origem>\n'
        '</heuristica>'
    )


def _persist_directive(candidata: dict) -> int:
    """
    Persiste candidata a diretriz como AgentMemory(user_id=0, directive_status='shadow').

    Idempotente por path (slug do título): segunda chamada com mesmo título
    retorna o id existente sem criar duplicata.

    O registro fica com directive_status='shadow' — NÃO injetado pelo builder
    (_build_operational_directives exclui 'shadow', só injeta NULL ou 'ativa').
    Promoção shadow→ativa requer revisão manual.

    Só é chamado quando AGENT_DIRECTIVE_PROMOTION=ON (futuro caller batch/D8).
    evaluate_and_promote() (flag OFF) NUNCA chama esta função.

    Args:
        candidata: dict com campos titulo, when, prescricao, source_session_id.

    Returns:
        int: id do AgentMemory criado ou já existente.
    """
    from app.agente.models import AgentMemory
    from app import db

    slug = _slug_titulo(candidata.get('titulo', ''))
    path = f'/memories/empresa/heuristicas/{slug}.xml'

    existente = AgentMemory.query.filter_by(user_id=0, path=path).first()
    if existente is not None:
        logger.info(
            f"[directive_promotion] _persist: já existe path={path!r} "
            f"id={existente.id} → no-op"
        )
        return existente.id

    mem = AgentMemory(
        user_id=0,
        path=path,
        content=_formatar_xml_diretriz(candidata),
        is_directory=False,
        importance_score=0.7,
        escopo='empresa',
        directive_status='shadow',
        created_by=None,  # nullable — sem FK obrigatória; user_id=0 já estabelece autoria
    )
    db.session.add(mem)
    db.session.flush()  # popula mem.id; commit fica com o caller (batch)
    logger.info(
        f"[directive_promotion] _persist: criada SHADOW id={mem.id} path={path!r}"
    )
    return mem.id


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

    Persistência real: _persist_directive() escreve AgentMemory(directive_status='shadow').
    Sob AGENT_DIRECTIVE_PROMOTION ON (futuro), seria chamado aqui.
    Hoje: flag OFF → evaluate_and_promote não é chamado por nenhum caller ativo,
    e mesmo quando chamado diretamente, o ramo shadow apenas loga (não chama _persist_directive).

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
