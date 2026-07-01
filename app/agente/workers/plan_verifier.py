"""
Verifier adversarial de plano — B2, Onda 2 (Job RQ).

Tenta REFUTAR a conclusão do passo do agente usando Sonnet com a MESMA
matéria que o judge vê (pergunta + resposta + tools + auditoria Odoo).
Veredito: {'refuted': bool, 'reason': str} (+ 'skipped': True quando não
há matéria — chave ADITIVA, contrato preservado).

Doutrina (2026-06-12): refutar SOMENTE com razão concreta ancorada na
matéria apresentada. Sem matéria suficiente → refuted=false (não punir o
agente por cegueira do verifier). Modelo Sonnet (e não Haiku): modelo
fraco não audita forte; volume ~263 calls/semana → custo desprezível.

Enqueue ativo via enqueue_pending_verifies sob a flag USE_AGENT_VERIFY
(app/agente/config/feature_flags.py — ON em PROD via env).

Padrão clonado de: app/agente/workers/step_judge.py
CRITICAL-1 replicado: db.session.commit() explícito após update_outcome —
sem ele, o SAVEPOINT do begin_nested()+flush() nunca é consolidado quando
o app_context do job RQ morre, e o veredito é descartado silenciosamente.
"""
import json
import logging
from datetime import timedelta
from typing import Optional

from app import create_app

logger = logging.getLogger('sistema_fretes')

# Sonnet (não Haiku): o adversarial audita respostas produzidas por modelos
# fortes (Opus/Fable) — modelo fraco não audita forte. ~263 calls/semana.
ADVERSARIAL_MODEL = 'claude-sonnet-5'

# Fila RQ (LEVE) onde o varredor batch enfileira verify_step_shadow.
# REUSA a mesma fila do step_judge ('agent_judge') — ambos são jobs leves de
# avaliação pós-turno, classificados fora de FILAS_PESADAS (worker_render.py).
VERIFY_QUEUE_NAME = 'agent_judge'

ADVERSARIAL_SYSTEM_PROMPT = (
    "Você é um revisor adversarial de um agente logístico. Sua tarefa é "
    "tentar REFUTAR a conclusão do passo, mas SOMENTE com razão concreta "
    "ancorada na matéria apresentada (pergunta do usuário, resposta do "
    "agente, ferramentas usadas e auditoria Odoo).\n\n"
    "Regras:\n"
    "  - Refute (refuted=true) APENAS se você apontar uma falha concreta e "
    "verificável na matéria: conclusão contradita pela auditoria, premissa "
    "falsa, pedido do usuário ignorado, número inconsistente.\n"
    "  - Se a matéria for insuficiente para julgar, retorne refuted=false "
    'com reason "matéria insuficiente". NÃO refute por falta de acesso a '
    "dados que não foram apresentados.\n"
    "  - Proporcionalidade: não exija prova além do escopo da tarefa. "
    "Ex.: um export de arquivo não exige confirmação no Odoo; uma resposta "
    "informativa não exige operação executiva.\n\n"
    "Retorne EXCLUSIVAMENTE JSON válido:\n"
    '{"refuted": bool, "reason": str curta}'
)


def _call_adversarial_verifier(user_prompt: str) -> str:
    """Chama o modelo adversarial (Sonnet) com ADVERSARIAL_SYSTEM_PROMPT.

    Helper independente para mock nos testes
    (mesmo padrão de step_judge._call_haiku_judge).
    """
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=ADVERSARIAL_MODEL,
        max_tokens=500,
        system=ADVERSARIAL_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_prompt}],
    )
    for block in resp.content:
        if getattr(block, 'type', None) == 'text':
            return block.text
    return ''


def _parse_adversarial_json(raw: str) -> Optional[dict]:
    """Parseia JSON tolerante a prefixos/sufixos. Retorna None se inválido."""
    if not raw:
        return None
    try:
        start = raw.find('{')
        end = raw.rfind('}')
        if start < 0 or end < 0 or end <= start:
            return None
        return json.loads(raw[start:end + 1])
    except (ValueError, json.JSONDecodeError):
        return None


def _build_adversarial_prompt(step, odoo_ops: Optional[list] = None,
                              meta: Optional[str] = None,
                              response: Optional[str] = None) -> str:
    """Monta o prompt do adversarial com PARIDADE DE MATÉRIA com o judge.

    Inclui (espelha step_judge._build_judge_prompt):
    - PERGUNTA do usuário (meta, 1500c) e RESPOSTA do agente (response, 3000c)
    - tools_used do step
    - resumo das operações Odoo (EXECUTADO/FALHA_ODOO, modelos/métodos)
    - resumo do judge anterior (quando presente em outcome_signal)

    Sem isto o adversarial refutava cego ("sem acesso ao resultado das
    ferramentas...") — refutações vazias que poluíam a calibração.
    """
    odoo_ops = odoo_ops or []
    tools_section = ', '.join(step.tools_used or []) or '(nenhuma)'

    pergunta_section = (meta or '').strip()[:1500] if meta else '(pergunta do usuario nao disponivel)'
    resposta_section = (response or '').strip()[:3000] if response else '(resposta do agente nao disponivel)'

    if not odoo_ops:
        odoo_section = (
            "AUDITORIA AMBIENTAL: sem auditoria ambiental disponivel "
            "(flag USE_ODOO_AUDIT_HOOK off ou tabela vazia para esta sessao). "
            "Julgue apenas pela materia apresentada acima."
        )
    else:
        executado = sum(1 for op in odoo_ops if getattr(op, 'status', '') == 'EXECUTADO')
        falhas = sum(1 for op in odoo_ops if getattr(op, 'status', '') == 'FALHA_ODOO')
        modelos = list({getattr(op, 'modelo_odoo', '?') for op in odoo_ops})
        metodos = list({getattr(op, 'metodo_odoo', '?') for op in odoo_ops if getattr(op, 'metodo_odoo', None)})

        odoo_section = (
            f"AUDITORIA AMBIENTAL Odoo ({len(odoo_ops)} ops registradas):\n"
            f"  - EXECUTADO: {executado}\n"
            f"  - FALHA_ODOO: {falhas}\n"
            f"  - Modelos: {', '.join(modelos[:5])}\n"
            f"  - Metodos: {', '.join(metodos[:5])}"
        )

    outcome = step.outcome_signal or {}
    conclusao_resumo = ''
    if 'judge' in outcome:
        j = outcome['judge']
        conclusao_resumo = (
            f"Judge anterior: score={j.get('score', '?')}, "
            f"label={j.get('label', '?')}, "
            f"evidencia={j.get('evidencia', '?')}"
        )

    return (
        f"## PERGUNTA do usuario:\n{pergunta_section}\n\n"
        f"## RESPOSTA do agente:\n{resposta_section}\n\n"
        f"## Ferramentas usadas no passo:\n{tools_section}\n\n"
        f"## {odoo_section}\n\n"
        + (f"## {conclusao_resumo}\n\n" if conclusao_resumo else '')
        + "Tente REFUTAR a conclusão deste passo — somente com razão concreta "
        "ancorada na matéria acima. Retorne JSON com refuted (bool) e reason "
        "(str curta)."
    )


def _load_turn_materia(step) -> dict:
    """Carrega a MATÉRIA do turno (mesmo caminho do worker do step_judge).

    Replica step_judge._judge_step_in_context: odoo_ops via
    OperacaoOdooAuditoria (session_id + contexto_origem='execute_kw_hook'),
    pergunta via triage_shadow._extract_user_message_text e resposta via
    _extract_assistant_response_text — correlação turn_seq = sufixo do
    step_uid após ':'.

    Best-effort total: cada bloco degrada isolado.

    Returns:
        {'odoo_ops': list, 'meta': str|None, 'response': str|None,
         'session': AgentSession|None, 'turn_seq': int|None}
    """
    out: dict = {'odoo_ops': [], 'meta': None, 'response': None,
                 'session': None, 'turn_seq': None}

    try:
        from app.odoo.models.operacao_odoo_auditoria import OperacaoOdooAuditoria
        out['odoo_ops'] = OperacaoOdooAuditoria.query.filter_by(
            session_id=step.session_id,
            contexto_origem='execute_kw_hook',
        ).all()
    except Exception as exc:
        logger.debug(f'[plan_verifier] odoo_ops nao carregadas (best-effort): {exc}')

    try:
        from app.agente.models import AgentSession
        from app.agente.workers.triage_shadow import _extract_user_message_text

        session = AgentSession.query.filter_by(session_id=step.session_id).first()
        out['session'] = session
        try:
            out['turn_seq'] = int(str(step.step_uid).rsplit(':', 1)[-1])
        except (ValueError, IndexError):
            out['turn_seq'] = None
        out['meta'] = _extract_user_message_text(session, out['turn_seq'])
        out['response'] = _extract_assistant_response_text(session, out['turn_seq'])
    except Exception as exc:
        logger.debug(f'[plan_verifier] conteudo do turno nao carregado (best-effort): {exc}')

    return out


def _verify_core(step, odoo_ops: Optional[list] = None,
                 meta: Optional[str] = None,
                 response: Optional[str] = None) -> Optional[dict]:
    """Núcleo testável do verifier adversarial: recebe step + matéria do
    turno (pergunta/resposta/auditoria), retorna veredito.

    Separado do boilerplate app_context para facilitar testes unitários
    sem necessidade de mockar create_app ou sessão de banco.

    SKIP-SEM-MATÉRIA: se pergunta E resposta indisponíveis, NÃO chama o LLM
    — refutar sem matéria produz refutações vazias ("sem acesso ao resultado
    das ferramentas..."). Grava {'refuted': False, 'skipped': True,
    'reason': 'sem_materia'} ('skipped' é chave ADITIVA — contrato do
    outcome_signal.verify preservado).

    Sem viés cego: se 'refuted' ausente no JSON do modelo, padrão é False
    (refutar exige razão concreta explícita).

    Returns:
        {'refuted': bool, 'reason': str} ou None se LLM falhar/JSON inválido.
    """
    if not (meta or '').strip() and not (response or '').strip():
        return {'refuted': False, 'skipped': True, 'reason': 'sem_materia'}

    prompt = _build_adversarial_prompt(step, odoo_ops=odoo_ops, meta=meta,
                                       response=response)

    try:
        raw = _call_adversarial_verifier(prompt)
    except Exception as exc:
        logger.error(f'[plan_verifier] LLM adversarial falhou: {exc}')
        return None

    parsed = _parse_adversarial_json(raw)
    if parsed is None:
        logger.warning(f'[plan_verifier] LLM retornou JSON inválido: {raw[:200]}')
        return None

    # Refutar exige razão concreta explícita — sem campo 'refuted', NÃO refuta.
    refuted = bool(parsed.get('refuted', False))
    reason = str(parsed.get('reason', ''))[:500]

    return {'refuted': refuted, 'reason': reason}


def verify_plan_adversarial(step_uid: str) -> None:
    """Job RQ: verifier adversarial — tenta refutar conclusão do passo.

    Persiste veredito em agent_step.outcome_signal['verify'] via
    AgentStep.update_outcome.

    Estrutura:
    1. Inicializa app context (via create_app())
    2. Carrega AgentStep pelo step_uid
    3. Delega para _verify_core (testável sem app_context)
    4. Persiste via AgentStep.update_outcome({'verify': veredito})
    5. db.session.commit() EXPLÍCITO (CRITICAL-1: sem isso o SAVEPOINT do
       begin_nested()+flush() nunca consolida no job RQ sem transação pai)

    Best-effort total: qualquer exceção é logada, job retorna silenciosamente.

    SHADOW (Onda 2): nenhum hook/SSE/loop chama esta função automaticamente.
    O enqueue virá na Onda 3 sob USE_AGENT_VERIFY
    (app/agente/config/feature_flags.py, OFF por default).
    """
    logger.info(
        f'[plan_verifier] iniciando: step_uid={step_uid[:40] if step_uid else "N/A"}'
    )

    try:
        app = create_app()
        with app.app_context():
            _verify_adversarial_in_context(step_uid)
    except Exception as exc:
        logger.error(f'[plan_verifier] falha inesperada: {exc}')


def _verify_adversarial_in_context(step_uid: str) -> None:
    """Executa o verifier dentro de app_context ativo.

    Separado para evitar aninhamento em testes (espelha step_judge._judge_step_in_context).
    """
    from app.agente.models import AgentStep

    step = AgentStep.query.filter_by(step_uid=step_uid).first()
    if step is None:
        logger.warning(f'[plan_verifier] step_uid={step_uid} não encontrado, abortando')
        return

    # Paridade de matéria com o judge: pergunta + resposta + auditoria Odoo
    materia = _load_turn_materia(step)
    veredito = _verify_core(
        step,
        odoo_ops=materia['odoo_ops'],
        meta=materia['meta'],
        response=materia['response'],
    )
    if veredito is None:
        logger.warning(
            f'[plan_verifier] veredito None para step_uid={step_uid}, abortando persistência'
        )
        return

    AgentStep.update_outcome(step_uid, {'verify': veredito})

    # CRITICAL-1 (espelha step_judge CRITICAL-1): commit explícito obrigatório.
    # update_outcome usa begin_nested()+flush() (SAVEPOINT) — desenhado para
    # rodar DENTRO de transação pai que alguém commita. No job RQ,
    # verify_plan_adversarial abre create_app()+app_context() SEM transação pai,
    # então o flush nunca commita e o veredito é descartado quando o app_context
    # morre. O esqueleto clonado (step_judge.py) commita explicitamente — aqui
    # replicamos a mesma lição.
    from app import db
    try:
        db.session.commit()
    except Exception as commit_err:
        logger.error(f'[plan_verifier] commit falhou: {commit_err}')
        db.session.rollback()
        return

    logger.info(
        f'[plan_verifier] concluído: step_uid={step_uid[:40]} '
        f'refuted={veredito["refuted"]}'
    )


# ═══════════════════════════════════════════════════════════════════════════════
# T2b — verify_step_shadow: orquestrador shadow dos 3 verifiers
# ═══════════════════════════════════════════════════════════════════════════════
# Roda os 3 verifiers (adversarial/arithmetic/domain) em best-effort para UM
# step e grava o veredito combinado em outcome_signal['verify'] com 3 sub-chaves.
# SHADOW: nenhum caller ativo; o enqueue vem de enqueue_pending_verifies sob a
# flag USE_AGENT_VERIFY (OFF por default). Não altera SSE nem o loop do agente.

def _extract_assistant_response_text(session, turn_seq: Optional[int]) -> Optional[str]:
    """Extrai o texto da resposta do assistente correspondente ao turno.

    Mapeia turn_seq (sufixo do step_uid após ':') → a N-ésima mensagem do
    assistente em session.data['messages'].

    Correlação (ver app/agente/routes/chat.py:1836): turn_seq é a CONTAGEM de
    mensagens role=='user' APÓS add_user_message. Para o N-ésimo turno,
    turn_seq=N corresponde à N-ésima mensagem do assistente (ordem de inserção:
    user/assistant alternados). Indexamos as mensagens role=='assistant' (1-based)
    e pegamos a N-ésima.

    Degrade (best-effort): se turn_seq não mapear com segurança (None, fora de
    range, ou sem assistant na posição), retorna a ÚLTIMA resposta do assistente
    da sessão. Se não houver nenhuma → None.
    """
    try:
        messages = session.get_messages() if session else []
    except Exception:
        messages = []

    assistant_msgs = [
        m for m in (messages or [])
        if isinstance(m, dict) and m.get('role') == 'assistant'
    ]
    if not assistant_msgs:
        return None

    # Mapeamento direto: turn_seq=N → N-ésima (1-based) mensagem do assistente
    if turn_seq is not None and 1 <= turn_seq <= len(assistant_msgs):
        content = assistant_msgs[turn_seq - 1].get('content')
        if content:
            return content

    # Degrade: última resposta do assistente
    last_content = assistant_msgs[-1].get('content')
    return last_content or None


def verify_step_shadow(step_uid: str) -> None:
    """Job RQ orquestrador: roda os 3 verifiers shadow e persiste veredito.

    Estrutura (mesmo esqueleto de verify_plan_adversarial):
    1. create_app() + app_context()
    2. Carrega AgentStep pelo step_uid; se None → log + return
    3. Roda os 3 verifiers em best-effort (cada um em try/except isolado):
       - adversarial: _verify_core(step) (reusa existente)
       - arithmetic : verify_arithmetic(response_text do turno)
       - domain     : verify_domain(plan_step) para cada step do plano c/ entities
    4. Grava AgentStep.update_outcome({'verify': {...}}) + commit EXPLÍCITO
       (CRITICAL-1 — SAVEPOINT não commita sozinho no job RQ)

    Best-effort total (INV-6): qualquer exceção é logada e o job retorna silencioso.

    SHADOW: enqueue via enqueue_pending_verifies sob USE_AGENT_VERIFY (OFF default).
    """
    logger.info(
        f'[verify_shadow] iniciando: step_uid={step_uid[:40] if step_uid else "N/A"}'
    )

    try:
        app = create_app()
        with app.app_context():
            _verify_step_shadow_in_context(step_uid)
    except Exception as exc:
        logger.error(f'[verify_shadow] falha inesperada: {exc}')


def _verify_step_shadow_in_context(step_uid: str) -> None:
    """Executa os 3 verifiers dentro de app_context ativo.

    Separado para evitar aninhamento em testes (espelha
    _verify_adversarial_in_context / _judge_step_in_context).
    """
    from app.agente.models import AgentStep

    step = AgentStep.query.filter_by(step_uid=step_uid).first()
    if step is None:
        logger.warning(f'[verify_shadow] step_uid={step_uid} não encontrado, abortando')
        return

    verify: dict = {}

    # Matéria do turno carregada UMA vez (compartilhada pelos 3 verifiers):
    # sessão + turn_seq + pergunta + resposta + auditoria Odoo — mesmo caminho
    # de resolução do worker do step_judge (paridade de matéria).
    materia = _load_turn_materia(step)
    session = materia['session']
    turn_seq = materia['turn_seq']

    # ── (1) adversarial — _verify_core (Sonnet, com matéria do turno) ────────
    try:
        adversarial = _verify_core(
            step,
            odoo_ops=materia['odoo_ops'],
            meta=materia['meta'],
            response=materia['response'],
        )
        if adversarial is not None:
            verify['adversarial'] = adversarial
        else:
            verify['adversarial'] = {'ok': True, 'issues': [], 'skipped': 'no_verdict'}
    except Exception as exc:
        logger.debug(f'[verify_shadow] adversarial falhou (best-effort): {exc}')

    # ── (2) arithmetic — verifica inconsistências aritméticas na resposta ────
    try:
        from app.agente.sdk.verifiers import verify_arithmetic
        response_text = materia['response']
        if not response_text:
            verify['arithmetic'] = {'ok': True, 'issues': [], 'skipped': 'no_response_text'}
        else:
            verify['arithmetic'] = verify_arithmetic(response_text, contexto=step_uid)
    except Exception as exc:
        logger.debug(f'[verify_shadow] arithmetic falhou (best-effort): {exc}')

    # ── (3) domain — valida entidades de cada step do plano contra ontologia ─
    try:
        from app.agente.sdk.verifiers import verify_domain
        plan = (session.data or {}).get('plan') if (session and session.data) else None
        plan_steps = (plan or {}).get('steps') if isinstance(plan, dict) else None

        if not plan_steps or not isinstance(plan_steps, dict):
            verify['domain'] = {'ok': True, 'issues': [], 'skipped': 'no_plan'}
        else:
            uid_for_domain = step.user_id or 0
            agg_issues: list = []
            verificou_algum = False
            for plan_step in plan_steps.values():
                if not isinstance(plan_step, dict):
                    continue
                if not plan_step.get('entities'):
                    continue
                verificou_algum = True
                res = verify_domain(plan_step, user_id=uid_for_domain)
                if res and res.get('issues'):
                    agg_issues.extend(res['issues'])
            if not verificou_algum:
                verify['domain'] = {'ok': True, 'issues': [], 'skipped': 'no_entities'}
            else:
                verify['domain'] = {'ok': len(agg_issues) == 0, 'issues': agg_issues}
    except Exception as exc:
        logger.debug(f'[verify_shadow] domain falhou (best-effort): {exc}')

    # ── Persiste veredito combinado + commit EXPLÍCITO (CRITICAL-1) ──────────
    # Guard de consistência com judge_step (code-review T2b MINOR): se TODOS os 3
    # verifiers falharem no nível de try (verify vazio — caso ~teórico, exigiria
    # falha de import), NÃO grava. Deixa o step sem 'verify' → re-enfileirado no
    # próximo ciclo (retry), em vez de marcá-lo "feito" com veredito vazio que
    # nunca mais seria reavaliado.
    if not verify:
        logger.warning(
            f'[verify_shadow] veredito vazio para step_uid={step_uid}, '
            f'abortando persistencia (permite retry no proximo ciclo)'
        )
        return

    AgentStep.update_outcome(step_uid, {'verify': verify})

    from app import db
    try:
        db.session.commit()
    except Exception as commit_err:
        logger.error(f'[verify_shadow] commit falhou: {commit_err}')
        db.session.rollback()
        return

    logger.info(
        f'[verify_shadow] concluído: step_uid={step_uid[:40]} '
        f'subchaves={sorted(verify.keys())}'
    )


def enqueue_pending_verifies(queue=None, now=None, lookback_hours=6, limit=50) -> dict:
    """Varredor RQ batch (B2/Onda 3): enfileira verify_step_shadow para steps
    recentes sem veredito 'verify'.

    WIRING shadow sob a flag USE_AGENT_VERIFY (OFF por default). Espelha
    enqueue_pending_judges (step_judge.py).

    Comportamento:
    1. Gate pela flag (import LAZY p/ patch de teste): se OFF, retorna sem
       tocar em Redis/Queue.
    2. Janela: candidatos = steps com created_at em [now-lookback, now].
    3. Filtro Python: candidato = step SEM 'verify' em outcome_signal.
    4. Enfileira verify_step_shadow com job_id determinístico RQ-safe
       (':' → '-', pois RQ 2.6.1 Job.set_id rejeita ':').
    5. Best-effort total (INV-6): falha de Redis NÃO levanta exceção.

    Returns:
        {'enfileirados': int, 'candidatos': int} (+ 'skipped' quando aplicável).
    """
    # 1. Gate — import LAZY (permite patch de USE_AGENT_VERIFY em teste)
    from app.agente.config.feature_flags import USE_AGENT_VERIFY
    if not USE_AGENT_VERIFY:
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

    # 3. Filtro Python — candidato = sem veredito 'verify'
    candidatos = [s for s in steps if 'verify' not in (s.outcome_signal or {})]

    if not candidatos:
        logger.info("[verify_enqueuer] enfileirados=0 candidatos=0")
        return {'enfileirados': 0, 'candidatos': 0}

    # 4. Construir fila real inline se não injetada (best-effort — INV-6)
    if queue is None:
        try:
            import os
            from rq import Queue
            import redis

            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            queue = Queue(VERIFY_QUEUE_NAME, connection=r)
        except Exception as e:
            logger.error(f"[verify_enqueuer] Redis indisponivel, abortando best-effort: {e}")
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
            job_id = f"verify-step-{step.step_uid.replace(':', '-')}"
            queue.enqueue(
                'app.agente.workers.plan_verifier.verify_step_shadow',
                step.step_uid,
                job_id=job_id,
                job_timeout=180,
            )
            enfileirados += 1
        except Exception as e:
            logger.warning(
                f"[verify_enqueuer] enqueue falhou para step_uid={step.step_uid}: {e}"
            )

    logger.info(
        f"[verify_enqueuer] enfileirados={enfileirados} candidatos={len(candidatos)}"
    )
    return {'enfileirados': enfileirados, 'candidatos': len(candidatos)}
