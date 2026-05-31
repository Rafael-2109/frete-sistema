"""
Verifier adversarial de plano — B2, Onda 2 (Job RQ).

Tenta REFUTAR a conclusão do passo do agente usando Haiku em modo cético.
Veredito: {'refuted': bool, 'reason': str}.

Padrão SHADOW: nenhum caller ativo. O enqueue automático virá na Onda 3
sob a flag USE_AGENT_VERIFY (app/agente/config/feature_flags.py, OFF por
default). Esta função existe exclusivamente para shadow/teste.

Padrão clonado de: app/agente/workers/step_judge.py
CRITICAL-1 replicado: db.session.commit() explícito após update_outcome —
sem ele, o SAVEPOINT do begin_nested()+flush() nunca é consolidado quando
o app_context do job RQ morre, e o veredito é descartado silenciosamente.
"""
import json
import logging
from typing import Optional

from app import create_app

logger = logging.getLogger('sistema_fretes')

HAIKU_MODEL = 'claude-haiku-4-5-20251001'

ADVERSARIAL_SYSTEM_PROMPT = (
    "Você é um revisor cético. Sua tarefa é tentar REFUTAR a conclusão "
    "apresentada por um agente logístico.\n\n"
    "Analise criticamente:\n"
    "  - A conclusão é suportada pelas ferramentas usadas?\n"
    "  - Há premissas não verificadas?\n"
    "  - Há alternativas mais plausíveis ignoradas?\n\n"
    "Padrão cético: na dúvida, REFUTE (refuted=true).\n\n"
    "Retorne EXCLUSIVAMENTE JSON válido:\n"
    '{"refuted": bool, "reason": str curta}'
)


def _call_haiku_verifier(user_prompt: str) -> str:
    """Chama Haiku com ADVERSARIAL_SYSTEM_PROMPT e retorna texto da resposta.

    Helper independente para mock nos testes
    (mesmo padrão de step_judge._call_haiku_judge).
    """
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=300,
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


def _build_adversarial_prompt(step) -> str:
    """Monta prompt para o Haiku adversarial."""
    tools_section = ', '.join(step.tools_used or []) or '(nenhuma)'

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
        f"## Ferramentas usadas no passo:\n{tools_section}\n\n"
        + (f"## {conclusao_resumo}\n\n" if conclusao_resumo else '')
        + "Tente REFUTAR a conclusão deste passo do agente logístico. "
        "Retorne JSON com refuted (bool) e reason (str curta)."
    )


def _verify_core(step) -> Optional[dict]:
    """Núcleo testável do verifier adversarial: recebe step, retorna veredito.

    Separado do boilerplate app_context para facilitar testes unitários
    sem necessidade de mockar create_app ou sessão de banco.

    Padrão cético: se 'refuted' ausente no JSON do Haiku, padrão é True.

    Returns:
        {'refuted': bool, 'reason': str} ou None se Haiku falhar/JSON inválido.
    """
    prompt = _build_adversarial_prompt(step)

    try:
        raw = _call_haiku_verifier(prompt)
    except Exception as exc:
        logger.error(f'[plan_verifier] Haiku falhou: {exc}')
        return None

    parsed = _parse_adversarial_json(raw)
    if parsed is None:
        logger.warning(f'[plan_verifier] Haiku retornou JSON inválido: {raw[:200]}')
        return None

    # Padrão cético: na dúvida, refuta
    refuted = bool(parsed.get('refuted', True))
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

    veredito = _verify_core(step)
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
