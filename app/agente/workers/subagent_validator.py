"""
Validador anti-alucinacao assincrono (feature #4).

Job RQ executado na queue 'agent_validation' pelos workers existentes
(worker_render.py em producao, worker_atacadao.py em dev). Compara a
resposta final do subagente com o resultado de suas tools usando Haiku
4.5, retorna score 0-100. Se score < threshold, emite SSE event
'subagent_validation' para UI mostrar icone amarelo ⚠.

Pipeline:
  SubagentStop hook -> enqueue job -> worker processa -> Haiku analisa
  -> persiste AgentSession.data['subagent_validations'] -> se score < N,
  publica Redis pubsub agent_sse:<session_id>

Flag: USE_SUBAGENT_VALIDATION (default true).
Threshold: SUBAGENT_VALIDATION_THRESHOLD env var (default 70).
"""
import json
import logging
from typing import Optional

from app import create_app
from app.agente.sdk.subagent_reader import get_subagent_summary
from app.utils.timezone import agora_brasil_naive

logger = logging.getLogger('sistema_fretes')

HAIKU_MODEL = 'claude-haiku-4-5-20251001'

VALIDATION_SYSTEM_PROMPT = """Voce compara o que um especialista fez \
(tool_calls + tool_results) vs o que ele reportou (resposta final).
Retorne EXCLUSIVAMENTE JSON valido no formato:

{"score": int 0-100, "reason": str curta, "flagged_claims": [str]}

Criterios:
- Score >= 80: resposta consistente com tool_results.
- Score 50-79: pequenas inconsistencias ou omissoes.
- Score < 50: resposta contradiz ou inventa informacoes.

flagged_claims = afirmacoes especificas do subagente que NAO estao \
suportadas pelos tool_results. Maximo 3 items."""


def _call_haiku(user_prompt: str) -> str:
    """Chama Haiku 4.5 e retorna texto da resposta. Testavel via mock."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=500,
        system=VALIDATION_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_prompt}],
    )
    for block in resp.content:
        if getattr(block, 'type', None) == 'text':
            return block.text
    return ''


def _build_user_prompt(summary) -> str:
    """Monta o prompt do usuario para o Haiku."""
    tools_section = []
    for t in summary.tools_used:
        name = t.get('name', 'unknown')
        args = (t.get('args_summary') or '')[:300]
        result = (t.get('result_summary') or '')[:500]
        tools_section.append(
            f"Tool: {name}\n  Args: {args}\n  Result: {result}\n"
        )

    return (
        f"## Tools chamadas ({len(summary.tools_used)} total):\n\n"
        + '\n'.join(tools_section)
        + f"\n\n## Resposta final do subagent:\n{summary.findings_text[:3000]}"
    )


def _push_validation_event(session_id: str, event_data: dict) -> None:
    """
    Publica 'subagent_validation' no canal Redis agent_sse:<session_id>.

    Worker RQ roda em processo separado — sem acesso direto a event_queue
    do SSE. Usa Redis publish; routes/chat.py assina esse canal.
    """
    try:
        import os
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        channel = f'agent_sse:{session_id}'
        r.publish(channel, json.dumps({
            'type': 'subagent_validation',
            'data': event_data,
        }))
    except Exception as e:
        logger.error(f"[validator] redis publish falhou: {e}")


def _parse_haiku_json(raw: str) -> Optional[dict]:
    """Parseia JSON tolerante a prefixos/sufixos. Retorna None se invalido."""
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


def validate_subagent_output(
    session_id: str,
    agent_id: str,
    threshold: int = 70,
) -> None:
    """Job RQ: valida output do subagent, persiste e notifica se score baixo."""
    logger.info(
        f"[validator] iniciando: session={session_id} "
        f"agent_id={agent_id[:12] if agent_id else 'N/A'}"
    )

    summary = get_subagent_summary(
        session_id, agent_id, include_pii=True, max_tool_chars=1000
    )
    if summary.status == 'error':
        logger.warning(
            f"[validator] summary error (agent_id={agent_id}), abortando"
        )
        return

    user_prompt = _build_user_prompt(summary)
    try:
        raw = _call_haiku(user_prompt)
    except Exception as e:
        logger.error(f"[validator] Haiku falhou: {e}")
        return

    payload = _parse_haiku_json(raw)
    if payload is None:
        logger.warning(
            f"[validator] Haiku retornou JSON invalido: {raw[:200]}"
        )
        return

    score = int(payload.get('score', 100))
    reason = str(payload.get('reason', ''))[:500]
    flagged = list(payload.get('flagged_claims', []))[:5]

    try:
        from app import db
        from sqlalchemy.orm.attributes import flag_modified
        from app.agente.models import AgentSession

        app = create_app()
        with app.app_context():
            sess = AgentSession.query.filter_by(
                session_id=session_id
            ).first()
            if sess is None:
                logger.warning(
                    f"[validator] session {session_id} nao encontrada"
                )
                return

            data = sess.data or {}
            bucket = data.setdefault(
                'subagent_validations',
                {'version': 1, 'entries': []},
            )
            entry = {
                'agent_id': agent_id,
                'agent_type': summary.agent_type,
                'score': score,
                'reason': reason,
                'flagged_claims': flagged,
                'validated_at': agora_brasil_naive().isoformat(),
            }
            bucket['entries'].append(entry)
            sess.data = data
            flag_modified(sess, 'data')
            db.session.commit()
    except Exception as e:
        logger.error(f"[validator] persistencia falhou: {e}")
        return

    logger.info(
        f"[validator] concluido: score={score} threshold={threshold} "
        f"agent_type={summary.agent_type}"
    )

    if score < threshold:
        _push_validation_event(session_id, entry)
