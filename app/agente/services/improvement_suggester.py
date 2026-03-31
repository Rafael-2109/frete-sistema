"""
Improvement Dialogue: Gerador batch de sugestoes de melhoria (Agent SDK -> Claude Code).

Analisa sessoes recentes em batch e gera sugestoes versionadas em 5 categorias:
- skill_suggestion: skills que ajudariam mas nao existem
- instruction_request: instrucoes/clarificacoes que o agente precisa
- prompt_feedback: feedback sobre system_prompt e memorias
- gotcha_report: armadilhas e informacoes uteis
- memory_feedback: memorias incorretas ou faltando

Tambem avalia respostas do Claude Code (verificacao contra sessoes recentes).

Custo: ~$0.005 por batch (~2K tokens input, ~500 output Sonnet).
Trigger: APScheduler no sincronizacao_incremental_definitiva.py (07:00 e 10:00).

Arquitetura batch vs pos-sessao:
- Captura TODAS as sessoes (inclusive abandonadas — as mais valiosas)
- Analise cross-sessao: detecta padroes que repetem entre sessoes
- 1 call Sonnet por batch (mais eficiente que 1/sessao)
- Desacoplado do lifecycle da sessao (nao depende de _save_messages_to_db completar)

Best-effort: falhas logadas, nunca propagadas (R1 services/CLAUDE.md).
"""

import json
import logging
import os
import re
from datetime import timedelta
from typing import Dict, Any, List

import anthropic

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

SONNET_MODEL = "claude-sonnet-4-6"

# Truncamento por mensagem (regra R3 services/CLAUDE.md)
MAX_CHARS_PER_MESSAGE = 3000
# Cap total por sessao no batch
MAX_CHARS_PER_SESSION = 8000
# Cap total do batch enviado ao Sonnet
MAX_BATCH_CHARS = 40000
# Maximo de sugestoes por batch
MAX_SUGGESTIONS = 5
# Minimo de mensagens para considerar sessao
MIN_MESSAGES = 3
# Janela de horas para buscar sessoes recentes
BATCH_WINDOW_HOURS = int(os.getenv('IMPROVEMENT_BATCH_WINDOW_HOURS', '8'))

# System prompt estatico — separado para prompt caching (cache_control ephemeral)
IMPROVEMENT_SYSTEM_PROMPT = """Voce eh um analista de auto-melhoria para um agente de IA logistica (Nacom Goya).
Analise as sessoes recentes entre usuarios e agente, e identifique oportunidades de melhoria.

CONTEXTO DO SISTEMA:
- Sistema de gestao de pedidos, estoque, separacoes e fretes
- Clientes: Atacadao, Assai, Carrefour, Sam's Club, outros
- Produtos: palmito, azeitona, conservas, molhos
- Operacoes: roteirizacao, expedicao, faturamento, NF-e, embarques, Odoo, SSW
- O agente usa: MCP tools (SQL, memoria, schema, browser), skills, subagentes

CATEGORIAS DE SUGESTAO:
A) skill_suggestion: skill que ajudaria mas nao existe
B) instruction_request: instrucao que o agente precisa mas nao tem
C) prompt_feedback: feedback sobre o system_prompt ou memorias
D) gotcha_report: armadilha ou informacao util descoberta nas sessoes
E) memory_feedback: memoria incorreta ou faltando

GERE um JSON array com 0-5 sugestoes. Cada sugestao:
{
  "category": "skill_suggestion|instruction_request|prompt_feedback|gotcha_report|memory_feedback",
  "severity": "critical|warning|info",
  "title": "titulo conciso (max 100 chars)",
  "description": "descricao prescritiva — O QUE deve mudar e POR QUE",
  "evidence": {"session_signal": "o que nas sessoes motivou", "occurrences": N, "session_ids": ["id1"]}
}

CRITERIOS DE QUALIDADE:
- PRESCRITIVAS (o que fazer), nao descritivas (o que aconteceu)
- Padroes cross-sessao (mesmo problema em 2+ sessoes) tem prioridade
- Sessoes abandonadas ou com sinais de frustacao merecem atencao especial
- Se nenhuma sessao revelar algo util, retorne [] (array vazio)
- severity=critical: causa erro/frustacao recorrente. warning: melhoria significativa. info: nice-to-have

RESPONDA APENAS o JSON array, sem markdown, sem comentarios."""


# Prompt para avaliacao de respostas do Claude Code
EVALUATION_SYSTEM_PROMPT = """Voce avalia se respostas do Claude Code a sugestoes de melhoria do agente foram eficazes.

Para cada resposta pendente de verificacao, compare com as sessoes recentes:
- Se o MESMO tipo de problema/friccao que motivou a sugestao aparece nas sessoes recentes: NAO resolveu
- Se o problema NAO aparece: PROVAVELMENTE resolveu (ou cenario nao ocorreu)

GERE um JSON array com avaliacoes:
{
  "suggestion_key": "IMP-YYYY-MM-DD-NNN",
  "verdict": "verified|needs_revision|inconclusive",
  "reason": "por que esta conclusao"
}

verified: problema resolvido. needs_revision: problema persiste. inconclusive: cenario nao ocorreu.
RESPONDA APENAS o JSON array."""


def _get_anthropic_client() -> anthropic.Anthropic:
    """Obtem cliente Anthropic."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY nao configurada")
    return anthropic.Anthropic(api_key=api_key)


def _truncate_session_messages(messages: List[Dict[str, Any]], max_chars: int) -> str:
    """
    Formata e trunca mensagens de UMA sessao.

    Segue regra R3 (services/CLAUDE.md): 3K chars/msg, cap por sessao.
    """
    parts = []
    total = 0

    for msg in messages:
        role = msg.get('role', '?')
        content = msg.get('content', '')

        if len(content) > MAX_CHARS_PER_MESSAGE:
            content = content[:MAX_CHARS_PER_MESSAGE] + '...[truncado]'

        entry = f"[{role}]: {content}"
        entry_len = len(entry)

        if total + entry_len > max_chars:
            parts.append('...[sessao truncada]')
            break

        parts.append(entry)
        total += entry_len

    return '\n'.join(parts)


def _format_batch(sessions_data: List[Dict[str, Any]]) -> str:
    """
    Formata batch de sessoes para envio ao Sonnet.

    Cada sessao e identificada por session_id e truncada individualmente.
    O batch total respeita MAX_BATCH_CHARS.
    """
    parts = []
    total = 0

    for sd in sessions_data:
        session_text = _truncate_session_messages(
            sd['messages'], MAX_CHARS_PER_SESSION
        )
        session_block = (
            f"<session id=\"{sd['session_id']}\" "
            f"msgs=\"{sd['message_count']}\" "
            f"user=\"{sd.get('user_id', '?')}\">\n"
            f"{session_text}\n"
            f"</session>"
        )

        block_len = len(session_block)
        if total + block_len > MAX_BATCH_CHARS:
            parts.append('...[batch truncado]')
            break

        parts.append(session_block)
        total += block_len

    return '\n\n'.join(parts)


def _parse_json_array(result_text: str) -> list:
    """Parse seguro de JSON array do Sonnet."""
    # Tentativa 1: parse direto
    try:
        parsed = json.loads(result_text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Tentativa 2: extrair JSON array com regex
    try:
        json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                return parsed
    except (json.JSONDecodeError, AttributeError):
        pass

    logger.warning(f"[IMPROVEMENT] Resposta invalida do Sonnet: {result_text[:200]}")
    return []


def _validate_suggestions(suggestions: list) -> List[Dict[str, Any]]:
    """Valida estrutura das sugestoes."""
    valid_categories = {
        'skill_suggestion', 'instruction_request', 'prompt_feedback',
        'gotcha_report', 'memory_feedback',
    }
    valid_severities = {'critical', 'warning', 'info'}

    valid = []
    for s in suggestions:
        if not isinstance(s, dict):
            continue
        if not all(k in s for k in ('category', 'title', 'description')):
            continue
        if s['category'] not in valid_categories:
            continue
        if s.get('severity') not in valid_severities:
            s['severity'] = 'info'
        if len(s['title']) > 200:
            s['title'] = s['title'][:197] + '...'
        valid.append(s)

    return valid[:MAX_SUGGESTIONS]


def _dedup_against_open(
    suggestions: List[Dict[str, Any]],
    open_items: list,
) -> List[Dict[str, Any]]:
    """Remove sugestoes duplicadas contra itens abertos."""
    if not open_items:
        return suggestions

    open_keys = {
        (item.category, item.title[:50].lower())
        for item in open_items
    }

    return [
        s for s in suggestions
        if (s['category'], s['title'][:50].lower()) not in open_keys
    ]


def _fetch_recent_sessions(hours: int) -> List[Dict[str, Any]]:
    """
    Busca sessoes recentes com 3+ mensagens.

    Returns:
        Lista de dicts com session_id, user_id, message_count, messages
    """
    from app.agente.models import AgentSession

    cutoff = agora_utc_naive() - timedelta(hours=hours)

    sessions = AgentSession.query.filter(
        AgentSession.updated_at >= cutoff,
        AgentSession.message_count >= MIN_MESSAGES,
    ).order_by(
        AgentSession.updated_at.desc()
    ).limit(20).all()

    result = []
    for s in sessions:
        messages = s.get_messages()
        if messages:
            result.append({
                'session_id': s.session_id,
                'user_id': s.user_id,
                'message_count': s.message_count or len(messages),
                'messages': messages,
            })

    return result


def _generate_batch_suggestions(
    sessions_data: List[Dict[str, Any]],
    open_items: list,
) -> List[Dict[str, Any]]:
    """
    Gera sugestoes de melhoria via Sonnet analisando batch de sessoes.

    Args:
        sessions_data: Lista de dicts com session_id, messages
        open_items: Itens abertos no dialogo (para dedup)

    Returns:
        Lista de sugestoes validadas (0-5 itens)
    """
    batch_text = _format_batch(sessions_data)

    # Informar sugestoes abertas para o LLM evitar duplicatas
    open_summary = ""
    if open_items:
        open_lines = [
            f"- [{item.category}] {item.title} (status={item.status})"
            for item in open_items[:10]
        ]
        open_summary = (
            "\n\n<sugestoes_abertas>\n"
            "Estas sugestoes ja estao em andamento — NAO duplique:\n"
            + '\n'.join(open_lines)
            + "\n</sugestoes_abertas>"
        )

    try:
        client = _get_anthropic_client()

        user_content = (
            f"<batch_sessoes count=\"{len(sessions_data)}\">\n"
            f"{batch_text}\n"
            f"</batch_sessoes>"
            f"{open_summary}"
        )

        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=1500,
            system=[{
                "type": "text",
                "text": IMPROVEMENT_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": user_content,
            }],
        )

        result_text = response.content[0].text.strip()
        suggestions = _validate_suggestions(_parse_json_array(result_text))
        suggestions = _dedup_against_open(suggestions, open_items)

        logger.info(
            f"[IMPROVEMENT] Batch: {len(suggestions)} sugestoes de {len(sessions_data)} sessoes "
            f"({response.usage.input_tokens}+{response.usage.output_tokens} tokens)"
        )

        return suggestions

    except Exception as e:
        logger.warning(f"[IMPROVEMENT] Erro ao gerar sugestoes batch: {e}")
        return []


def _evaluate_responses_batch(
    unverified: list,
    sessions_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Avalia respostas do Claude Code contra sessoes recentes (batch).

    Args:
        unverified: Itens AgentImprovementDialogue com status='responded'
        sessions_data: Sessoes recentes para comparacao

    Returns:
        Lista de avaliacoes [{suggestion_key, verdict, reason}]
    """
    if not unverified or not sessions_data:
        return []

    batch_text = _format_batch(sessions_data)

    response_lines = []
    for item in unverified:
        response_lines.append(
            f"- suggestion_key={item.suggestion_key} "
            f"category={item.category} "
            f"title=\"{item.title}\" "
            f"implementation_notes=\"{(item.implementation_notes or '')[:500]}\""
        )

    try:
        client = _get_anthropic_client()

        user_content = (
            f"<sessoes_recentes>\n{batch_text}\n</sessoes_recentes>\n\n"
            f"<respostas_pendentes>\n"
            + '\n'.join(response_lines)
            + "\n</respostas_pendentes>"
        )

        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=500,
            system=[{
                "type": "text",
                "text": EVALUATION_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": user_content,
            }],
        )

        result_text = response.content[0].text.strip()
        evaluations = _parse_json_array(result_text)

        if not isinstance(evaluations, list):
            return []

        logger.info(
            f"[IMPROVEMENT] Batch eval: {len(evaluations)} avaliacoes "
            f"({response.usage.input_tokens}+{response.usage.output_tokens} tokens)"
        )

        return evaluations

    except Exception as e:
        logger.warning(f"[IMPROVEMENT] Erro ao avaliar respostas batch: {e}")
        return []


def executar_batch_improvement(db_instance) -> Dict[str, Any]:
    """
    Entry point para APScheduler: gera sugestoes em batch e avalia respostas.

    Chamado pelo sincronizacao_incremental_definitiva.py (modulo 25, 07:00 e 10:00).
    Best-effort: falhas logadas, nunca propagadas.

    Args:
        db_instance: SQLAlchemy db instance (ja dentro de app_context)

    Returns:
        Dict com resultado: {suggestions_created, evaluations_done, sessions_analyzed}
    """
    result = {
        'suggestions_created': 0,
        'evaluations_done': 0,
        'sessions_analyzed': 0,
    }

    try:
        from app.agente.models import AgentImprovementDialogue

        # =========================================================
        # Passo 1: Buscar sessoes recentes
        # =========================================================
        sessions_data = _fetch_recent_sessions(BATCH_WINDOW_HOURS)
        result['sessions_analyzed'] = len(sessions_data)

        if not sessions_data:
            logger.info("[IMPROVEMENT] Nenhuma sessao recente com 3+ mensagens")
            return result

        # =========================================================
        # Passo 2: Avaliar respostas pendentes do Claude Code
        # =========================================================
        unverified = AgentImprovementDialogue.get_unverified_responses()
        if unverified:
            evaluations = _evaluate_responses_batch(unverified, sessions_data)
            for ev in evaluations:
                key = ev.get('suggestion_key')
                verdict = ev.get('verdict')
                reason = ev.get('reason', '')

                if not key or verdict not in ('verified', 'needs_revision', 'inconclusive'):
                    continue
                if verdict == 'inconclusive':
                    continue

                try:
                    v2 = AgentImprovementDialogue.query.filter_by(
                        suggestion_key=key, version=2,
                    ).first()

                    if not v2:
                        continue

                    new_status = 'verified' if verdict == 'verified' else 'needs_revision'
                    AgentImprovementDialogue.upsert_response(
                        suggestion_key=key,
                        version=3,
                        author='agent_sdk',
                        status=new_status,
                        description=reason,
                    )
                    result['evaluations_done'] += 1
                    logger.info(f"[IMPROVEMENT] Avaliacao v3: {key} -> {new_status}")
                except Exception as ev_err:
                    logger.warning(f"[IMPROVEMENT] Erro avaliacao {key}: {ev_err}")

        # =========================================================
        # Passo 3: Gerar novas sugestoes
        # =========================================================
        open_items = AgentImprovementDialogue.get_open_by_category()
        suggestions = _generate_batch_suggestions(sessions_data, open_items)

        # Extrair session_ids das sessoes analisadas
        all_session_ids = [sd['session_id'] for sd in sessions_data]

        for s in suggestions:
            try:
                # Usar session_ids da evidence se disponivel, senao usar todas
                evidence = s.get('evidence', {})
                source_ids = evidence.get('session_ids', all_session_ids[:3])

                AgentImprovementDialogue.create_suggestion(
                    category=s['category'],
                    severity=s['severity'],
                    title=s['title'],
                    description=s['description'],
                    evidence=evidence,
                    session_ids=source_ids,
                )
                result['suggestions_created'] += 1
            except Exception as save_err:
                logger.warning(
                    f"[IMPROVEMENT] Erro ao salvar sugestao '{s.get('title', '?')}': {save_err}"
                )

        # Commit tudo de uma vez
        if result['suggestions_created'] > 0 or result['evaluations_done'] > 0:
            try:
                db_instance.session.commit()
                logger.info(
                    f"[IMPROVEMENT] Batch concluido: {result['suggestions_created']} sugestoes, "
                    f"{result['evaluations_done']} avaliacoes, "
                    f"{result['sessions_analyzed']} sessoes analisadas"
                )
            except Exception as commit_err:
                db_instance.session.rollback()
                logger.warning(f"[IMPROVEMENT] Erro no commit: {commit_err}")
                result['suggestions_created'] = 0
                result['evaluations_done'] = 0

    except Exception as e:
        logger.warning(f"[IMPROVEMENT] Erro geral no batch: {e}")

    return result
