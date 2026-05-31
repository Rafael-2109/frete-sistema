"""
JUDGE de passo — Process Reward Model (E2/A1, Onda 1).

Avalia a QUALIDADE de um passo (turno) do agente e grava o veredito
em agent_step.outcome_signal['judge'].

PRINCÍPIO CENTRAL (Process Reward Model):
    O SINAL AMBIENTAL (operacoes reais no ERP Odoo — auditoria determinística)
    DOMINA o texto da resposta. Se houve FALHA_ODOO no passo, o score e' baixo
    (<= 35) independente de quao confiante a resposta soe. Se as operacoes
    foram EXECUTADO com sucesso, isso eleva o score.

Heurística ambiental inviolável (nao-gameável pelo Haiku):
    Se QUALQUER op em odoo_ops tem status == 'FALHA_ODOO':
        score = min(score_haiku, 35)
        componente_culpado = 'odoo'

ENQUEUE (shadow, Onda 3 / A3):
    Esta funcao existe para shadow/teste. O enqueue automatico sera' feito
    por um varredor RQ batch, controlado pela flag USE_AGENT_STEP_JUDGE
    (ja' criada, OFF por default). Nenhum hook/SSE/path chama judge_step
    diretamente nesta versao.

Padrao clonado de: app/agente/workers/subagent_validator.py
"""
import json
import logging
from datetime import timedelta
from typing import Optional

from app import create_app

logger = logging.getLogger('sistema_fretes')

HAIKU_MODEL = 'claude-haiku-4-5-20251001'

# Fila RQ (LEVE) onde o varredor batch enfileira jobs judge_step.
# Classificada como leve — NAO entra em FILAS_PESADAS (worker_render.py).
JUDGE_QUEUE_NAME = 'agent_judge'

JUDGE_SYSTEM_PROMPT = """Voce avalia a QUALIDADE de UM passo (turno) de um agente \
logistico — se ele atingiu o objetivo do usuario.

REGRA DOMINANTE (Process Reward Model): o SINAL AMBIENTAL (operacoes reais no ERP \
Odoo) DOMINA o texto. Se houve FALHA_ODOO no passo, o score e' baixo (<40) \
independente de quao confiante a resposta soe. Se as operacoes Odoo foram \
EXECUTADO com sucesso e coerentes com o pedido, isso eleva o score.

Retorne EXCLUSIVAMENTE JSON valido:
{"score": int 0-100, "label": "success"|"partial"|"failure",
 "componente_culpado": "tool"|"skill"|"reasoning"|"odoo"|null,
 "evidencia": str curta}"""


def _call_haiku_judge(user_prompt: str) -> str:
    """Chama Haiku com JUDGE_SYSTEM_PROMPT e retorna texto da resposta. Testavel via mock."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=500,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_prompt}],
    )
    for block in resp.content:
        if getattr(block, 'type', None) == 'text':
            return block.text
    return ''


def _parse_judge_json(raw: str) -> Optional[dict]:
    """Parseia JSON tolerante a prefixos/sufixos. Retorna None se invalido ou sem chaves obrigatorias."""
    if not raw:
        return None
    try:
        start = raw.find('{')
        end = raw.rfind('}')
        if start < 0 or end < 0 or end <= start:
            return None
        parsed = json.loads(raw[start:end + 1])
        # Validar chaves obrigatórias
        if 'score' not in parsed or 'label' not in parsed:
            return None
        return parsed
    except (ValueError, json.JSONDecodeError):
        return None


def _build_judge_prompt(step, odoo_ops: list) -> str:
    """Monta o prompt do usuário para o Haiku judge.

    Inclui:
    - tools_used do step
    - resumo das operacoes Odoo (quantas EXECUTADO, quantas FALHA_ODOO, modelos/metodos)
    - mensagem explicita quando sem auditoria ambiental disponivel
    """
    tools_section = ', '.join(step.tools_used or []) or '(nenhuma)'

    if not odoo_ops:
        odoo_section = (
            "AUDITORIA AMBIENTAL: sem auditoria ambiental disponivel "
            "(flag USE_ODOO_AUDIT_HOOK off ou tabela vazia para esta sessao). "
            "Avaliar apenas pelo contexto das ferramentas usadas."
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

    return (
        f"## Tools usadas no passo:\n{tools_section}\n\n"
        f"## {odoo_section}\n\n"
        f"Avalie a qualidade deste passo do agente logistico. "
        f"Retorne JSON com score (0-100), label, componente_culpado e evidencia."
    )


def _judge_core(step, odoo_ops: list) -> Optional[dict]:
    """Nucleo testavel do judge: recebe step + odoo_ops, retorna veredito dict ou None.

    Separado do boilerplate app_context para facilitar testes unitarios
    sem necessidade de mockar create_app ou sessao de banco.

    Aplica a heuristica ambiental ANTES de retornar:
        Se QUALQUER op tem status == 'FALHA_ODOO':
            score = min(score_haiku, 35)
            componente_culpado = 'odoo'
    """
    prompt = _build_judge_prompt(step, odoo_ops)

    try:
        raw = _call_haiku_judge(prompt)
    except Exception as e:
        logger.error(f"[step_judge] Haiku falhou: {e}")
        return None

    veredito = _parse_judge_json(raw)
    if veredito is None:
        logger.warning(f"[step_judge] Haiku retornou JSON invalido: {raw[:200]}")
        return None

    # Normalizar campos
    score = int(veredito.get('score', 50))
    label = str(veredito.get('label', 'partial'))
    componente_culpado = veredito.get('componente_culpado')
    evidencia = str(veredito.get('evidencia', ''))[:500]

    # ─── HEURÍSTICA AMBIENTAL (inviolável, nao-gameável pelo Haiku) ───────────
    # Se QUALQUER operacao Odoo falhou, o passo falhou por mais confiante
    # que a resposta soe. O ambiental domina.
    tem_falha_odoo = any(
        getattr(op, 'status', '') == 'FALHA_ODOO'
        for op in odoo_ops
    )
    if tem_falha_odoo:
        score = min(score, 35)
        componente_culpado = 'odoo'
        if label == 'success':
            label = 'failure'

    return {
        'score': score,
        'label': label,
        'componente_culpado': componente_culpado,
        'evidencia': evidencia,
    }


def judge_step(step_uid: str) -> None:
    """Job RQ: avalia qualidade do passo e persiste veredito em outcome_signal['judge'].

    Estrutura:
    1. Inicializa app context (via create_app())
    2. Carrega AgentStep pelo step_uid
    3. Carrega odoo_ops (best-effort, degrada para [] se tabela vazia/ausente)
    4. Delega para _judge_core (testavel sem app_context)
    5. Persiste via AgentStep.update_outcome({'judge': veredito})

    Best-effort total: qualquer excecao e logada e o job retorna silenciosamente.

    SHADOW (Onda 1): nenhum hook/SSE/path chama esta funcao automaticamente.
    O enqueue sera' feito por varredor RQ batch na Onda 3 / A3 sob a flag
    USE_AGENT_STEP_JUDGE (em app/agente/config/feature_flags.py, OFF por default).
    """
    logger.info(f"[step_judge] iniciando: step_uid={step_uid[:40] if step_uid else 'N/A'}")

    try:
        app = create_app()
        with app.app_context():
            _judge_step_in_context(step_uid)
    except Exception as e:
        logger.error(f"[step_judge] falha inesperada: {e}")


def _judge_step_in_context(step_uid: str) -> None:
    """Executa judge dentro de app_context ativo. Separado para evitar aninhamento em testes."""
    from app.agente.models import AgentStep

    step = AgentStep.query.filter_by(step_uid=step_uid).first()
    if step is None:
        logger.warning(f"[step_judge] step_uid={step_uid} nao encontrado, abortando")
        return

    # Carregar operacoes Odoo de auditoria (best-effort — tabela pode estar vazia)
    odoo_ops = []
    try:
        from app.odoo.models.operacao_odoo_auditoria import OperacaoOdooAuditoria
        odoo_ops = OperacaoOdooAuditoria.query.filter_by(
            session_id=step.session_id,
            contexto_origem='execute_kw_hook',
        ).all()
    except Exception as e:
        logger.debug(f"[step_judge] nao foi possivel carregar odoo_ops: {e}")

    veredito = _judge_core(step, odoo_ops)
    if veredito is None:
        logger.warning(f"[step_judge] veredito None para step_uid={step_uid}, abortando persistencia")
        return

    AgentStep.update_outcome(step_uid, {'judge': veredito})

    # CRITICAL-1 (code-review Onda 1): commit explicito obrigatorio.
    # update_outcome usa begin_nested()+flush() (SAVEPOINT) — desenhado para
    # rodar DENTRO de transacao pai que alguem commita. No job RQ, judge_step
    # abre create_app()+app_context() SEM transacao pai, entao o flush nunca
    # commita e o veredito e descartado quando o app_context morre. O esqueleto
    # clonado (subagent_validator.py) commita explicito — aqui replicamos.
    from app import db
    try:
        db.session.commit()
    except Exception as commit_err:
        logger.error(f"[step_judge] commit falhou: {commit_err}")
        db.session.rollback()
        return

    logger.info(
        f"[step_judge] concluido: step_uid={step_uid[:40]} "
        f"score={veredito['score']} label={veredito['label']}"
    )


def enqueue_pending_judges(queue=None, now=None, lookback_hours=6, limit=50) -> dict:
    """Varredor RQ batch (E2/A3): enfileira judge_step para steps recentes sem veredito.

    WIRING da Onda 3 / A3 — torna funcional o job judge_step que vive em shadow.
    Chamado por ciclo (cada tick de 30min do orquestrador de sincronizacao),
    sob a flag USE_AGENT_STEP_JUDGE (OFF por default).

    Comportamento:
    1. Gate pela flag (import LAZY p/ patch de teste funcionar): se OFF, retorna
       sem tocar em Redis/Queue.
    2. Janela: candidatos sao steps com created_at no intervalo [now-lookback, now].
    3. Filtro Python: candidato = step SEM 'judge' em outcome_signal.
    4. Para cada candidato, enfileira judge_step com job_id deterministico
       ('judge-step:{step_uid}') — evita pilha de duplicatas do mesmo step na fila.
    5. Best-effort total (INV-6): falha de Redis NAO levanta excecao.

    Args:
        queue: rq.Queue ja construida (injecao p/ teste). Se None, constroi a real.
        now: datetime de referencia da janela. Default = agora_utc_naive().
        lookback_hours: tamanho da janela retroativa (horas).
        limit: cap de steps lidos do banco por execucao.

    Returns:
        dict com {'enfileirados': int, 'candidatos': int} (+ 'skipped' quando aplicavel).
    """
    # 1. Gate — import LAZY (permite patch de USE_AGENT_STEP_JUDGE em teste)
    from app.agente.config.feature_flags import USE_AGENT_STEP_JUDGE
    if not USE_AGENT_STEP_JUDGE:
        return {'enfileirados': 0, 'candidatos': 0, 'skipped': 'flag_off'}

    from app.utils.timezone import agora_utc_naive
    from app.agente.models import AgentStep

    if now is None:
        now = agora_utc_naive()
    corte = now - timedelta(hours=lookback_hours)

    # 2. Query — usa o indice de created_at; janela superior fecha em `now`
    #    para que `now` passado deterministicamente (teste fora-da-janela) funcione.
    steps = (
        AgentStep.query
        .filter(AgentStep.created_at >= corte)
        .filter(AgentStep.created_at <= now)
        .order_by(AgentStep.created_at.asc())
        .limit(limit)
        .all()
    )

    # 3. Filtro Python — candidato = sem veredito 'judge'
    candidatos = [s for s in steps if 'judge' not in (s.outcome_signal or {})]

    if not candidatos:
        logger.info("[judge_enqueuer] enfileirados=0 candidatos=0")
        return {'enfileirados': 0, 'candidatos': 0}

    # 4. Construir fila real inline se nao injetada (best-effort — INV-6)
    if queue is None:
        try:
            import os
            from rq import Queue
            import redis

            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            queue = Queue(JUDGE_QUEUE_NAME, connection=r)
        except Exception as e:
            logger.error(f"[judge_enqueuer] Redis indisponivel, abortando best-effort: {e}")
            return {
                'enfileirados': 0,
                'candidatos': len(candidatos),
                'skipped': 'redis_error',
            }

    # 5. Enfileirar
    enfileirados = 0
    for step in candidatos:
        try:
            queue.enqueue(
                'app.agente.workers.step_judge.judge_step',
                step.step_uid,
                job_id=f'judge-step:{step.step_uid}',
                job_timeout=120,
            )
            enfileirados += 1
        except Exception as e:
            logger.warning(
                f"[judge_enqueuer] enqueue falhou para step_uid={step.step_uid}: {e}"
            )

    logger.info(
        f"[judge_enqueuer] enfileirados={enfileirados} candidatos={len(candidatos)}"
    )
    return {'enfileirados': enfileirados, 'candidatos': len(candidatos)}
