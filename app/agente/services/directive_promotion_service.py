"""
A4 (Onda 3) — Promoção Automática de Diretriz. Fecha o flywheel.

V1 offline + flag-OFF:
    _persist_directive() é REAL: escreve directive_status='shadow' (persistida,
    NUNCA injetada — o builder injeta só NULL/'ativa'; e está gated por
    AGENT_OPERATIONAL_DIRECTIVES OFF). Dupla segurança.
    Caller = run_directive_promotion_batch (D8 módulo 32), gated por
    AGENT_DIRECTIVE_PROMOTION (OFF default). Flag ON → o batch persiste shadow.

Flywheel:
    sinais (E1/E2 em agent_step.outcome_signal)
    → gate de regressão (regression_gate.py — herdado do A3 aposentado)
    → A4 batch (módulo 32): PROMOVE (shadow) diretriz operacional que funcionou

"Diretriz" = heurística empresa em AgentMemory (user_id=0,
path /memories/empresa/heuristicas/, lida por
memory_injection._build_operational_directives quando
importance_score>=0.7 + nivel>=5).

Anti-gaming (R9 / step_judge._judge_core):
    Se a sessão de origem teve FALHA_ODOO, o sinal ambiental DOMINA.
    Mesmo padrão de step_judge._judge_core: ambiental > texto.
    Na dúvida (erro de consulta): NÃO promove (conservador = True).

Ref: app/agente/workers/step_judge.py (_judge_core heurística ambiental)
Ref: app/agente/services/regression_gate.py (eval_gate — gate puro de regressão)
Ref: app/agente/sdk/plan_state.py (PlanState — plano que funcionou)
Ref: app/agente/sdk/memory_injection.py:420 (_build_operational_directives)
"""
import logging
import re as _re
from typing import Optional

from app.agente.config.feature_flags import (
    AGENT_DIRECTIVE_PROMOTION,
    AGENT_DIRECTIVE_JUDGE_SOURCE,
    AGENT_DIRECTIVE_MIN_QUALITY,
)

logger = logging.getLogger('sistema_fretes')

# Status discriminado no resultado de evaluate_and_promote
_DECISION_WOULD_PROMOTE = 'would_promote'
_DECISION_REJECTED = 'rejected'


# ---------------------------------------------------------------------------
# propose_directive_from_plan
# ---------------------------------------------------------------------------

# Saudacoes/cortesia — detectam prompt trivial que NAO descreve uma tarefa.
_SAUDACOES_CORTESIA = frozenset({
    'bom', 'dia', 'boa', 'tarde', 'noite', 'ola', 'oi', 'oie', 'ei', 'opa',
    'hello', 'hi', 'hey', 'obrigado', 'obrigada', 'obg', 'valeu', 'vlw', 'blz',
    'beleza', 'ok', 'okay', 'tudo', 'bem', 'td', 'por', 'favor', 'pf', 'entao',
})


def _meta_tarefa_trivial(meta: str) -> bool:
    """True se a 1a msg do usuario NAO descreve uma tarefa (saudacao/cortesia/curtissima).

    Evita que uma sessao trivial validada pelo judge vire diretriz-empresa
    ('Abordagem validada pelo judge: BOM DIA') — reward-hacking embrionario
    (ver critica/A-flywheel.md secao C1). Conservador: so barra o claramente
    nao-acionavel (sobra < 2 palavras de conteudo apos remover saudacoes/cortesia).
    """
    if not meta:
        return False
    norm = _re.sub(r'[^a-z0-9à-ÿ\s]', ' ', meta.strip().lower())
    conteudo = [p for p in norm.split() if p and p not in _SAUDACOES_CORTESIA]
    return len(conteudo) < 2


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

    # Endurecimento (auditoria 2026-06-06): min 2 passos com subject real. 1 passo e acao
    # unica hiper-especifica (ex: 'Cancelar payment 33439 no Odoo'), nao fluxo transferivel.
    if len(subjects_clean) < 2:
        logger.debug(
            f"[directive_promotion] propose(plan): {len(subjects_clean)} subject(s) util(eis) "
            f"< 2 — descartado (session={session_id!r})"
        )
        return None

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
# propose_directive_from_judge_session (A4 V2 / Opção B)
# Fonte de candidata vinda do JUDGE signal (E2), INDEPENDENTE de PlanState.
# O batch só achava candidata em sessões COM plano concluído (0 PlanStates →
# no-op eterno). Fiel à spec eixos/A-flywheel.md §2.3: o critério de promoção é
# o quality_signal (judge), não o plano. Mesmo pipeline a jusante
# (evaluate_and_promote: R9 anti-gaming + gate A3 report-only).
# ---------------------------------------------------------------------------

def propose_directive_from_judge_session(
    session_id: str,
    judge_steps: list,
    user_meta: Optional[str] = None,
    min_quality: float = 0.7,
    min_steps: int = 2,
) -> Optional[dict]:
    """Extrai candidata a diretriz de uma SESSÃO de alta qualidade validada pelo judge.

    Critérios (TODOS obrigatórios — conservador: preferir abster a promover ruído):
    - >= min_steps passos COM veredito judge (score presente);
    - NENHUM passo com label='failure' (sessão limpa);
    - média dos scores (normalizada 0-1) >= min_quality.

    PURO (sem DB). O batch carrega judge_steps + user_meta e passa aqui; a âncora
    R9 (_tem_falha_odoo) e o gate A3 continuam em evaluate_and_promote.

    Args:
        session_id: UUID da sessão de origem.
        judge_steps: lista de dicts {score, label, evidencia, tools} — 1 por passo julgado.
        user_meta: 1ª mensagem do usuário (para o campo 'when'); opcional.
        min_quality: piso de qualidade média (0-1).
        min_steps: mínimo de passos julgados.

    Returns:
        candidata {titulo, when, prescricao, source_session_id, status='candidata'} ou None.
    """
    if not judge_steps or not isinstance(judge_steps, list):
        return None

    # Endurecimento (auditoria 2026-06-06): prompt trivial (saudacao/cortesia) NAO vira
    # diretriz-empresa — evita 'Abordagem validada pelo judge: BOM DIA' (reward-hacking:
    # judge premia sessao trivial, critica/A-flywheel.md C1). meta vazio segue p/ fallback.
    if user_meta and _meta_tarefa_trivial(user_meta):
        logger.info(
            f"[directive_promotion] propose(judge): meta trivial descartada "
            f"session={session_id!r} meta={user_meta!r}"
        )
        return None

    scores = []
    evidencias = []   # (score_norm, evidencia)
    tools_all = []
    tem_failure = False
    for st in judge_steps:
        if not isinstance(st, dict):
            continue
        raw = st.get('score')
        if raw is None:
            continue
        try:
            sc = float(raw)
        except (TypeError, ValueError):
            continue
        sc = sc / 100.0 if sc > 1.0 else sc
        scores.append(sc)
        if st.get('label') == 'failure':
            tem_failure = True
        ev = (st.get('evidencia') or '').strip()
        if ev:
            evidencias.append((sc, ev))
        for t in (st.get('tools') or []):
            if t:
                tools_all.append(t)

    if len(scores) < min_steps:
        return None
    if tem_failure:
        return None

    media = sum(scores) / len(scores)
    if media < min_quality:
        return None

    # Ferramentas dominantes (dedup preservando 1ª ocorrência)
    tools_dom = []
    for t in tools_all:
        if t not in tools_dom:
            tools_dom.append(t)
    tools_txt = ', '.join(tools_dom[:4]) or '(sem ferramenta)'

    # Evidência representativa = passo de MAIOR score
    evidencias.sort(key=lambda x: x[0], reverse=True)
    evid_rep = evidencias[0][1][:240] if evidencias else ''

    meta_snip = (user_meta or '').strip().replace('\n', ' ')[:80]
    titulo = (
        f"Abordagem validada pelo judge: {meta_snip}" if meta_snip
        else f"Abordagem validada pelo judge ({len(scores)} passos)"
    )[:80]
    when = (
        f"Em tarefas como: {meta_snip}" if meta_snip
        else "Em tarefas similares às desta sessão"
    )
    prescricao = (
        f"Abordagem que pontuou alto no judge (qualidade média {media:.2f} "
        f"em {len(scores)} passos, sem falhas). Ferramentas: {tools_txt}."
    )
    if evid_rep:
        prescricao += f" Ex.: {evid_rep}"

    candidata = {
        'titulo': titulo,
        'when': when,
        'prescricao': prescricao,
        'source_session_id': session_id,
        'status': 'candidata',
    }
    logger.info(
        f"[directive_promotion] propose(judge): candidata session={session_id!r} "
        f"media={media:.2f} passos={len(scores)} titulo={titulo!r}"
    )
    return candidata


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
# _slug_titulo + _persist_directive
# ---------------------------------------------------------------------------

def _slug_titulo(titulo: str) -> str:
    """Deriva slug URL-safe a partir do título da candidata (max 80 chars)."""
    base = (titulo or 'diretriz').lower().strip()
    base = _re.sub(r'[^a-z0-9]+', '-', base).strip('-')
    return (base or 'diretriz')[:80]


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

    # E2.7: derivar agente da sessão de origem para não contaminar corpus 'web'
    # com memórias de sessões 'lojas' e vice-versa.
    _agente = 'web'
    _src_session_id = candidata.get('source_session_id')
    if _src_session_id:
        try:
            from app.agente.models import AgentSession
            _src_sess = AgentSession.get_by_session_id(_src_session_id)
            if _src_sess:
                _agente = getattr(_src_sess, 'agente', None) or 'web'
        except Exception:
            pass  # fallback 'web'

    existente = AgentMemory.query.filter_by(user_id=0, path=path).first()
    if existente is not None:
        logger.info(
            f"[directive_promotion] _persist: já existe path={path!r} "
            f"id={existente.id} → no-op"
        )
        return existente.id

    # Formato canonico (2026-06-08): meta estruturado + content sentinela derivado
    # (mesmo formato que pattern_analyzer._save_conhecimentos_v3). Selecionavel pelo
    # builder via fallback WHEN:/DO:. Ver app/agente/services/memory_format.py.
    from app.agente.services.memory_format import build_meta, render_content
    meta = build_meta(
        tipo='heuristica', nivel=5,
        titulo=candidata.get('titulo', ''),
        when=candidata.get('when', ''),
        prescricao=candidata.get('prescricao', ''),
        origem=f"promovida automaticamente da sessao {candidata.get('source_session_id', '')}",
    )
    mem = AgentMemory(
        user_id=0,
        path=path,
        content=render_content(meta),
        meta=meta,
        is_directory=False,
        importance_score=0.7,
        escopo='empresa',
        directive_status='shadow',
        created_by=None,  # nullable — sem FK obrigatória; user_id=0 já estabelece autoria
        agente=_agente,  # E2.7: herdado da sessão de origem
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

    # ─── 2. Regression gate (report_only; função pura herdada do A3) ─────────
    from app.agente.services.regression_gate import eval_gate

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


# ---------------------------------------------------------------------------
# _buscar_sessoes_com_plano_concluido + _quality_score_da_sessao
# ---------------------------------------------------------------------------

def _buscar_sessoes_com_plano_concluido(lookback_hours: int, limit: int) -> list:
    """Sessões recentes (janela lookback) cujo data['plan'] existe. O filtro fino
    (todos steps completed) fica em propose_directive_from_plan."""
    from app.agente.models import AgentSession
    from app.utils.timezone import agora_utc_naive
    from datetime import timedelta
    corte = agora_utc_naive() - timedelta(hours=lookback_hours)
    rows = AgentSession.query.filter(
        AgentSession.updated_at >= corte,
        AgentSession.data.isnot(None),
    ).order_by(AgentSession.updated_at.desc()).limit(limit).all()
    return [s for s in rows if isinstance(s.data, dict) and s.data.get('plan')]


def _quality_score_da_sessao(session_id: str):
    """Média dos judge scores dos agent_step da sessão (normalizada 0-1).
    None se não houver judge signal (conservador → abstém)."""
    from app.agente.models import AgentStep
    steps = AgentStep.query.filter_by(session_id=session_id).all()
    scores = []
    for st in steps:
        sig = st.outcome_signal or {}
        judge = sig.get('judge') if isinstance(sig, dict) else None
        if isinstance(judge, dict) and judge.get('score') is not None:
            try:
                scores.append(float(judge['score']))
            except (TypeError, ValueError):
                pass
    if not scores:
        return None
    media = sum(scores) / len(scores)
    return media / 100.0 if media > 1.0 else media


# ---------------------------------------------------------------------------
# Fonte 2 (Opção B / A4 V2): sessões recentes + judge signal (sem PlanState)
# ---------------------------------------------------------------------------

def _buscar_sessoes_recentes(lookback_hours: int, limit: int) -> list:
    """Sessões recentes na janela (SEM filtro de plano). Fonte da candidata
    judge-driven: a sessão qualifica pela QUALIDADE do judge, não pelo plano."""
    from app.agente.models import AgentSession
    from app.utils.timezone import agora_utc_naive
    from datetime import timedelta
    corte = agora_utc_naive() - timedelta(hours=lookback_hours)
    return AgentSession.query.filter(
        AgentSession.updated_at >= corte,
    ).order_by(AgentSession.updated_at.desc()).limit(limit).all()


def _judge_steps_da_sessao(session_id: str) -> list:
    """Vereditos judge dos agent_step da sessão como lista
    {score, label, evidencia, tools} para propose_directive_from_judge_session."""
    from app.agente.models import AgentStep
    out = []
    steps = (
        AgentStep.query.filter_by(session_id=session_id)
        .order_by(AgentStep.created_at.asc()).all()
    )
    for st in steps:
        sig = st.outcome_signal or {}
        judge = sig.get('judge') if isinstance(sig, dict) else None
        if not isinstance(judge, dict) or judge.get('score') is None:
            continue
        out.append({
            'score': judge.get('score'),
            'label': judge.get('label'),
            'evidencia': judge.get('evidencia', ''),
            'tools': st.tools_used or [],
        })
    return out


def _primeira_msg_usuario(session) -> Optional[str]:
    """1ª mensagem do usuário da sessão (para o campo 'when' da candidata)."""
    try:
        messages = session.get_messages() if session else []
    except Exception:
        messages = []
    for m in (messages or []):
        if isinstance(m, dict) and m.get('role') == 'user' and m.get('content'):
            return m['content']
    return None


def _avaliar_e_contabilizar(candidata: dict, session_id: str, contadores: dict) -> None:
    """quality_score (abstém se None) → evaluate_and_promote (R9 + gate A3) →
    persist shadow. Atualiza contadores in-place. Compartilhado pelas 2 fontes."""
    contadores['candidatos'] += 1
    score = _quality_score_da_sessao(session_id)
    if score is None:
        contadores['abstencoes'] += 1
        logger.info(f"[directive_promotion] batch: abstém session={session_id!r} (sem judge)")
        return
    resultado = evaluate_and_promote(
        candidata, baseline_score=AGENT_DIRECTIVE_MIN_QUALITY, candidate_score=score,
    )
    if resultado.get('decision') == _DECISION_WOULD_PROMOTE:
        _persist_directive(candidata)
        contadores['promovidos'] += 1
    else:
        contadores['rejeitados'] += 1


# ---------------------------------------------------------------------------
# run_directive_promotion_batch
# ---------------------------------------------------------------------------

def _reframe_as_compiled_memory(content: str) -> str:
    """Fase 3.2B: reescreve a correcao em frame IMPERATIVO (Compiled Memory) na promocao.

    A Fase 0 mostrou que correcoes tipo-A (que competem com o pedido literal do usuario) so
    aderem com frame imperativo no topo (caso A: P3 0%->67% so com o frame). Formato de
    entrada gravado por _save_personal_insight: '[correcao] <descricao>\\nDO: <prescricao>'.
    Saida:
        SEMPRE|NUNCA: <prescricao>
        WHEN: <descricao>
        DO: <prescricao>
    IDEMPOTENTE (se ja comeca com SEMPRE/NUNCA, retorna inalterado — nao reprocessa).
    Heuristica NUNCA quando a prescricao tem negacao explicita (nao/nunca/evitar/ignorar/
    jamais), senao SEMPRE. Funcao PURA (sem DB/LLM) — testavel isoladamente.
    """
    if not content:
        return content
    stripped = content.strip()
    if _re.match(r'^(SEMPRE|NUNCA)\b', stripped, _re.IGNORECASE):
        return content  # ja em frame imperativo
    linhas = stripped.split('\n')
    descricao = _re.sub(r'^\[[^\]]*\]\s*', '', linhas[0]).strip() if linhas else stripped
    do_linha = next((l for l in linhas if l.strip().upper().startswith('DO:')), '')
    prescricao = do_linha.split(':', 1)[1].strip() if ':' in do_linha else descricao
    if not prescricao:
        return content
    low = prescricao.lower()
    verbo = 'NUNCA' if _re.search(r'\b(n[aã]o|nunca|evit\w*|jamais|ignor\w*)\b', low) else 'SEMPRE'
    return f"{verbo}: {prescricao}\nWHEN: {descricao}\nDO: {prescricao}"


def promover_correcoes_recorrentes(threshold: int = None, limit: int = 200, user_id: int = None) -> dict:
    """Fonte 3 do batch (CORRECTION-RECURRENCE): promove correcoes PESSOAIS reincidentes
    a priority='mandatory' para entrarem no canal duro <user_rules> (Fase 1 do loop).

    Correcao vem do USUARIO (feedback humano de alta confianca); por isso o filtro NAO e
    o gate Odoo (que protege a auto-promocao do agente), e sim a REINCIDENCIA: so promove
    correcao com correction_count >= threshold (default AGENT_CORRECTION_PROMOTION_THRESHOLD).
    Idempotente (correcao ja 'mandatory' e ignorada pelo filtro). Recorrente (modulo 32 D8):
    a licao reincidente do usuario e promovida automaticamente, sem script one-shot. Best-effort.

    Returns: {'avaliadas': N, 'promovidas': M}
    """
    out = {'avaliadas': 0, 'promovidas': 0}
    try:
        from app.agente.config.feature_flags import (
            AGENT_CORRECTION_PROMOTION,
            AGENT_CORRECTION_PROMOTION_THRESHOLD,
        )
    except Exception:
        return out
    if not AGENT_CORRECTION_PROMOTION:
        return out
    th = threshold if threshold is not None else AGENT_CORRECTION_PROMOTION_THRESHOLD
    try:
        from app.agente.models import AgentMemory
        from app import db
        q = AgentMemory.query.filter(
            AgentMemory.path.like('/memories/corrections/%'),
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.is_cold == False,  # noqa: E712
            AgentMemory.priority != 'mandatory',
            AgentMemory.correction_count >= th,
        )
        if user_id is not None:
            q = q.filter(AgentMemory.user_id == user_id)
        candidatas = q.order_by(AgentMemory.correction_count.desc()).limit(limit).all()
        out['avaliadas'] = len(candidatas)
        reembed = []  # (user_id, path, novo_conteudo) p/ re-embed apos reframe
        for mem in candidatas:
            # Fase 3.2B: reescreve em frame IMPERATIVO (Compiled Memory) ao virar regra dura.
            novo = _reframe_as_compiled_memory(mem.content or '')
            if novo != (mem.content or ''):
                mem.content = novo
                out['reescritas'] = out.get('reescritas', 0) + 1
                reembed.append((mem.user_id, mem.path, novo))
            mem.priority = 'mandatory'
            out['promovidas'] += 1
        if out['promovidas']:
            db.session.commit()
            logger.info(
                f"[CORRECTION_PROMOTION] {out['promovidas']} correcoes recorrentes "
                f"promovidas a 'mandatory' (threshold={th}, avaliadas={out['avaliadas']}, "
                f"reescritas={out.get('reescritas', 0)})"
            )
            # Re-embed best-effort: o reframe mudou o conteudo -> embedding ficaria stale.
            for _uid, _path, _cont in reembed:
                try:
                    from app.embeddings.config import MEMORY_SEMANTIC_SEARCH
                    if MEMORY_SEMANTIC_SEARCH:
                        from ..tools.memory_mcp_tool import _embed_memory_best_effort
                        _embed_memory_best_effort(_uid, _path, _cont)
                except Exception:
                    pass
    except Exception as exc:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        logger.warning(f"[CORRECTION_PROMOTION] falhou (ignorado): {exc}")
    return out


def demote_stale_rules(harmful_threshold: int = None, limit: int = 200, user_id: int = None) -> dict:
    """Fonte 3b do batch (DEMOTE): rebaixa regra dura que FALHOU repetidas vezes.

    Espelho de promover_correcoes_recorrentes. Criterio = OUTCOME (nao eco textual): uma
    correcao JA 'mandatory' (canal duro <user_rules>) com harmful_count >= threshold reincidiu
    mesmo sendo regra dura -> a regra, como esta escrita, NAO previne o erro. Acao: priority->
    'contextual' + is_cold=True (puxa de circulacao, pendente de reescrita humana).
    FLAP-FREE: a promocao (fonte 3) filtra is_cold==False, entao a regra rebaixada NAO e
    re-promovida no mesmo ciclo. Idempotente (regra ja contextual/cold sai do filtro).
    Flag AGENT_CORRECTION_DEMOTION (default OFF — demote remove regra explicita do usuario).

    Returns: {'avaliadas': N, 'rebaixadas': M}
    """
    out = {'avaliadas': 0, 'rebaixadas': 0}
    try:
        from app.agente.config.feature_flags import (
            AGENT_CORRECTION_DEMOTION,
            AGENT_OUTCOME_HARMFUL_THRESHOLD,
        )
    except Exception:
        return out
    if not AGENT_CORRECTION_DEMOTION:
        return out
    th = harmful_threshold if harmful_threshold is not None else AGENT_OUTCOME_HARMFUL_THRESHOLD
    try:
        from app.agente.models import AgentMemory
        from app import db
        q = AgentMemory.query.filter(
            AgentMemory.path.like('/memories/corrections/%'),
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.priority == 'mandatory',
            AgentMemory.harmful_count >= th,
        )
        if user_id is not None:
            q = q.filter(AgentMemory.user_id == user_id)
        candidatas = q.order_by(AgentMemory.harmful_count.desc()).limit(limit).all()
        out['avaliadas'] = len(candidatas)
        for mem in candidatas:
            mem.priority = 'contextual'
            mem.is_cold = True  # fora de circulacao ate reescrita humana (evita flap)
            out['rebaixadas'] += 1
        if out['rebaixadas']:
            db.session.commit()
            logger.info(
                f"[CORRECTION_DEMOTION] {out['rebaixadas']} regras duras rebaixadas "
                f"(harmful_count >= {th}, avaliadas={out['avaliadas']}) — pendentes de reescrita"
            )
    except Exception as exc:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        logger.warning(f"[CORRECTION_DEMOTION] falhou (ignorado): {exc}")
    return out


def run_directive_promotion_batch(lookback_hours: int = 24, limit: int = 50) -> dict:
    """Varredor A4-batch (D8 módulo 32). Flag-gated por AGENT_DIRECTIVE_PROMOTION.

    TRES fontes de candidata:
      1. PLANO: sessão com plano 100% concluído → propose_directive_from_plan.
      2. JUDGE: sessão de alta qualidade validada pelo judge (sem precisar de plano)
         → propose_directive_from_judge_session. DESLIGADA por default (estratégia R3,
         2026-06-12): gated por AGENT_DIRECTIVE_JUDGE_SOURCE (default OFF).
      3. CORRECTION-RECURRENCE: correcao PESSOAL reincidente (correction_count >= threshold)
         → promover_correcoes_recorrentes (priority='mandatory', canal duro <user_rules>).
         Filtro = reincidencia (feedback humano), NAO o gate Odoo das fontes 1/2.
    Ambas passam pelo MESMO gate (evaluate_and_promote: R9 anti-gaming DOMINA + A3
    report-only). Best-effort: nunca levanta. Sessão processada por uma fonte NÃO é
    re-proposta pela outra (dedup por session_id)."""
    contadores = {'candidatos': 0, 'promovidos': 0, 'abstencoes': 0, 'rejeitados': 0}
    if not AGENT_DIRECTIVE_PROMOTION:
        return contadores

    processadas = set()

    def _rollback_seguro():
        # Limpa sessão potencialmente poisoned para não derrubar as próximas iterações.
        # Promoções não-commitadas são re-propostas no próximo ciclo D8 (idempotente). Shadow.
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass

    # ── Fonte 1: PLANO concluído ─────────────────────────────────────────────
    try:
        sessoes_plano = _buscar_sessoes_com_plano_concluido(lookback_hours, limit)
    except Exception as exc:
        logger.error(f"[directive_promotion] batch: erro ao buscar sessões (plano): {exc}")
        sessoes_plano = []
    for s in sessoes_plano:
        try:
            candidata = propose_directive_from_plan(s.data.get('plan'), s.session_id)
            if candidata is None:
                continue
            processadas.add(s.session_id)
            _avaliar_e_contabilizar(candidata, s.session_id, contadores)
        except Exception as exc:
            logger.error(f"[directive_promotion] batch(plano): erro session={getattr(s, 'session_id', '?')!r}: {exc}")
            _rollback_seguro()

    # ── Fonte 2: JUDGE signal (alta qualidade, sem plano) — Opção B / A4 V2 ───
    # Estratégia R3 (2026-06-12): fonte DESLIGADA por default (flag
    # AGENT_DIRECTIVE_JUDGE_SOURCE, default false) — promover diretriz por nota
    # de turno do judge é frágil mesmo endurecido (_meta_tarefa_trivial fica no
    # código para quando religar). Religar exige judge ANCORADO EM OUTCOME (R9).
    if AGENT_DIRECTIVE_JUDGE_SOURCE:
        try:
            sessoes_recentes = _buscar_sessoes_recentes(lookback_hours, limit)
        except Exception as exc:
            logger.error(f"[directive_promotion] batch: erro ao buscar sessões (judge): {exc}")
            sessoes_recentes = []
    else:
        sessoes_recentes = []
        logger.debug(
            "[directive_promotion] batch: fonte JUDGE desligada "
            "(AGENT_DIRECTIVE_JUDGE_SOURCE=OFF — estratégia R3)"
        )
    for s in sessoes_recentes:
        sid = getattr(s, 'session_id', None)
        if not sid or sid in processadas:
            continue
        try:
            judge_steps = _judge_steps_da_sessao(sid)
            if len(judge_steps) < 2:
                continue
            candidata = propose_directive_from_judge_session(
                sid, judge_steps, user_meta=_primeira_msg_usuario(s),
            )
            if candidata is None:
                continue
            processadas.add(sid)
            _avaliar_e_contabilizar(candidata, sid, contadores)
        except Exception as exc:
            logger.error(f"[directive_promotion] batch(judge): erro session={sid!r}: {exc}")
            _rollback_seguro()

    # ── Fonte 3: CORRECTION-RECURRENCE — promove correcao PESSOAL recorrente a
    # 'mandatory' (canal duro <user_rules>, Fase 1). Filtro = reincidencia
    # (correction_count >= threshold), nao gate Odoo (correcao = feedback humano). ──
    try:
        _corr = promover_correcoes_recorrentes(limit=limit * 4)
        contadores['correcoes_promovidas'] = _corr.get('promovidas', 0)
        contadores['correcoes_reescritas'] = _corr.get('reescritas', 0)
    except Exception as exc:
        logger.error(f"[directive_promotion] batch(correcao): erro: {exc}")
        _rollback_seguro()

    # ── Fonte 3b: DEMOTE — regra dura que reincidiu repetidas vezes (harmful) sai de
    # circulacao pendente de reescrita. Commit isolado dentro da funcao (nao reverte a
    # promocao da fonte 3). Flag-gated (AGENT_CORRECTION_DEMOTION, default OFF). ──
    try:
        _dem = demote_stale_rules(limit=limit * 4)
        contadores['regras_rebaixadas'] = _dem.get('rebaixadas', 0)
    except Exception as exc:
        logger.error(f"[directive_promotion] batch(demote): erro: {exc}")
        _rollback_seguro()

    try:
        from app import db
        db.session.commit()
    except Exception:
        _rollback_seguro()
    logger.info(f"[directive_promotion] batch concluído: {contadores}")
    return contadores
