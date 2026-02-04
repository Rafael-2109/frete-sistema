"""
P1-3: Aprendizado de Padrões entre Sessões (RAG de Comportamento).

Analisa sessões históricas de um usuário para identificar padrões recorrentes:
- Clientes mais consultados
- Produtos mais buscados
- Queries mais frequentes
- Preferências de workflow

Salva padrões em /memories/learned/patterns.xml para uso proativo pelo agente.

Custo estimado: ~$0.002 por análise (~4K tokens input, ~800 output Haiku).
Trigger: a cada N sessões do usuário (configurável via PATTERN_LEARNING_THRESHOLD).

Uso:
    Chamado por _save_messages_to_db() em routes.py quando:
    - USE_PATTERN_LEARNING=true
    - total_sessions do usuário é múltiplo de PATTERN_LEARNING_THRESHOLD
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import anthropic

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Limite de caracteres totais das sessões para enviar ao Haiku
MAX_SESSIONS_CHARS = 12000

# Máximo de sessões recentes a analisar
MAX_SESSIONS_TO_ANALYZE = 15

PATTERN_PROMPT = """Voce eh um analista de padroes de uso para um sistema de logistica (Nacom Goya).
Analise o historico de sessoes abaixo e identifique PADROES RECORRENTES.

CONTEXTO DO SISTEMA:
- Gestao de pedidos de venda, estoque, separacoes e fretes
- Clientes: Atacadao, Assai, Carrefour, Sam's Club, outros
- Produtos: palmito, azeitona, conservas, molhos
- Operacoes: roteirizacao, expedicao, faturamento, NF-e, embarques

<sessoes>
{sessions}
</sessoes>

IDENTIFIQUE padroes e gere um JSON com esta estrutura:

{{
  "clientes_frequentes": [
    {{
      "nome": "Nome do cliente",
      "frequencia": "X de Y sessoes",
      "contexto": "O que o usuario geralmente consulta sobre este cliente"
    }}
  ],
  "produtos_frequentes": [
    {{
      "nome": "Nome do produto",
      "frequencia": "X de Y sessoes",
      "contexto": "Tipo de consulta mais comum"
    }}
  ],
  "queries_recorrentes": [
    {{
      "tipo": "estoque|pedido|separacao|embarque|faturamento|outro",
      "descricao": "O que o usuario costuma perguntar",
      "frequencia": "X de Y sessoes"
    }}
  ],
  "preferencias": [
    "Preferencia 1: descricao clara",
    "Preferencia 2: descricao clara"
  ],
  "workflow_tipico": "Descricao do workflow mais comum do usuario (ex: consulta estoque -> cria separacao -> verifica embarque)",
  "confianca": "alta|media|baixa"
}}

REGRAS:
- So inclua padroes que aparecem em 3+ sessoes (alta confianca) ou 2+ (media)
- Arrays vazios se nao houver padroes claros
- "confianca" = "alta" se 5+ sessoes analisadas com padroes claros, "media" se 3-4, "baixa" se < 3
- NAO invente padroes — so reporte o que esta nos dados
- "preferencias" so inclui se for padrao repetido (ex: "prefere parcial", "consulta primeiro Atacadao")

RESPONDA APENAS JSON VALIDO, sem markdown, sem comentarios."""


def _get_anthropic_client() -> anthropic.Anthropic:
    """Obtém cliente Anthropic para Haiku."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")
    return anthropic.Anthropic(api_key=api_key)


def _format_sessions_for_analysis(sessions_data: List[Dict[str, Any]]) -> str:
    """
    Formata sessões do usuário para enviar ao Haiku.

    Extrai resumo de cada sessão: mensagens do usuário e tools usadas.
    Trunca para MAX_SESSIONS_CHARS total.

    Args:
        sessions_data: Lista de dicts com {session_id, messages, created_at, summary}

    Returns:
        String formatada para o prompt
    """
    lines = []
    total_chars = 0

    for i, sess in enumerate(sessions_data):
        session_line = f"--- SESSÃO {i + 1} ({sess.get('created_at', 'data desconhecida')}) ---"

        # Se tem summary, usa ele (muito mais conciso)
        summary = sess.get('summary')
        if summary and isinstance(summary, dict):
            resumo = summary.get('resumo_geral', '')
            topicos = ', '.join(summary.get('topicos_abordados', []))
            tools = ', '.join(summary.get('ferramentas_usadas', []))
            session_line += f"\nResumo: {resumo}"
            if topicos:
                session_line += f"\nTópicos: {topicos}"
            if tools:
                session_line += f"\nFerramentas: {tools}"

            # Pedidos mencionados
            for p in summary.get('pedidos_mencionados', [])[:3]:
                session_line += f"\nPedido: {p.get('cliente', '')} - {p.get('pedido', '')} ({p.get('status', '')})"

        else:
            # Fallback: extrair mensagens do usuário
            messages = sess.get('messages', [])
            user_msgs = [m for m in messages if m.get('role') == 'user']
            tools_used = set()

            for msg in messages:
                for tool in msg.get('tools_used', []):
                    tools_used.add(tool)

            for msg in user_msgs[:5]:  # Máximo 5 mensagens por sessão
                content = msg.get('content', '')[:200]
                session_line += f"\n[USER]: {content}"

            if tools_used:
                session_line += f"\nFerramentas: {', '.join(tools_used)}"

        # Controle de tamanho total
        if total_chars + len(session_line) > MAX_SESSIONS_CHARS:
            lines.append("... [sessões anteriores omitidas por limite]")
            break

        lines.append(session_line)
        total_chars += len(session_line)

    return "\n\n".join(lines)


def analyze_patterns(
    sessions_data: List[Dict[str, Any]],
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Analisa sessões históricas e identifica padrões via Haiku.

    Args:
        sessions_data: Lista de sessões com messages e summaries
        user_id: ID do usuário (para logging)

    Returns:
        Dict com padrões identificados ou None em caso de erro
    """
    if not sessions_data or len(sessions_data) < 3:
        logger.debug(
            f"[PATTERNS] Usuário {user_id}: poucas sessões para análise "
            f"({len(sessions_data) if sessions_data else 0})"
        )
        return None

    try:
        client = _get_anthropic_client()
        formatted = _format_sessions_for_analysis(sessions_data)

        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": PATTERN_PROMPT.format(sessions=formatted),
            }],
        )

        result_text = response.content[0].text.strip()
        patterns = _parse_json_response(result_text, user_id)

        if not patterns:
            return None

        # Adiciona metadata
        patterns['_meta'] = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'model': HAIKU_MODEL,
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
            'sessions_analyzed': len(sessions_data),
        }

        logger.info(
            f"[PATTERNS] Padrões identificados para usuário {user_id}: "
            f"confiança={patterns.get('confianca', 'N/A')} "
            f"({response.usage.input_tokens}+{response.usage.output_tokens} tokens)"
        )

        return patterns

    except Exception as e:
        logger.warning(f"[PATTERNS] Erro ao analisar padrões para usuário {user_id}: {e}")
        return None


def _parse_json_response(
    result_text: str,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Parse seguro da resposta JSON do Haiku."""
    # Tentativa 1: parse direto
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        pass

    # Tentativa 2: extrair JSON com regex
    try:
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, AttributeError):
        pass

    logger.warning(
        f"[PATTERNS] Resposta inválida do Haiku para usuário {user_id}: "
        f"{result_text[:200]}"
    )
    return None


def analyze_and_save(
    app,
    user_id: int,
) -> bool:
    """
    Carrega sessões do usuário, analisa padrões e salva em memória.

    Função principal chamada por routes.py.

    Args:
        app: Flask app
        user_id: ID do usuário

    Returns:
        True se padrões foram salvos, False caso contrário
    """
    try:
        from ..models import AgentSession
        from app import db

        with app.app_context():
            # Carregar últimas N sessões do usuário (com mensagens)
            sessions = AgentSession.query.filter_by(
                user_id=user_id
            ).order_by(
                AgentSession.updated_at.desc()
            ).limit(MAX_SESSIONS_TO_ANALYZE).all()

            if len(sessions) < 3:
                logger.debug(
                    f"[PATTERNS] Usuário {user_id}: {len(sessions)} sessões, "
                    f"mínimo 3 para análise"
                )
                return False

            # Preparar dados das sessões
            sessions_data = []
            for sess in sessions:
                sessions_data.append({
                    'session_id': sess.session_id,
                    'created_at': sess.created_at.strftime('%d/%m/%Y') if sess.created_at else '',
                    'messages': sess.get_messages(),
                    'summary': sess.get_summary(),
                    'message_count': sess.message_count,
                })

            # Analisar padrões via Haiku
            patterns = analyze_patterns(sessions_data, user_id)
            if not patterns:
                return False

            # Salvar em /memories/learned/patterns.xml
            _save_patterns_to_memory(user_id, patterns)

            db.session.commit()
            logger.info(
                f"[PATTERNS] Padrões salvos para usuário {user_id} "
                f"({len(sessions)} sessões analisadas)"
            )
            return True

    except Exception as e:
        logger.warning(f"[PATTERNS] Erro ao salvar padrões: {e}")
        try:
            with app.app_context():
                db.session.rollback()
        except Exception:
            pass
        return False


def _save_patterns_to_memory(
    user_id: int,
    patterns: Dict[str, Any],
) -> None:
    """
    Salva padrões na memória persistente do usuário.

    Path: /memories/learned/patterns.xml
    Sobrescrito a cada análise com padrões mais recentes.

    Args:
        user_id: ID do usuário
        patterns: Padrões identificados pelo Haiku
    """
    from ..models import AgentMemory

    path = "/memories/learned/patterns.xml"
    timestamp = datetime.now(timezone.utc).isoformat()
    confianca = _xml_escape(patterns.get('confianca', 'baixa'))
    sessions_analyzed = patterns.get('_meta', {}).get('sessions_analyzed', 0)

    # Formatar clientes frequentes
    clientes_xml = ""
    for c in patterns.get('clientes_frequentes', []):
        nome = _xml_escape(c.get('nome', ''))
        freq = _xml_escape(c.get('frequencia', ''))
        ctx = _xml_escape(c.get('contexto', ''))
        clientes_xml += (
            f'\n    <cliente nome="{nome}" frequencia="{freq}">'
            f'\n      <contexto>{ctx}</contexto>'
            f'\n    </cliente>'
        )

    # Formatar produtos frequentes
    produtos_xml = ""
    for p in patterns.get('produtos_frequentes', []):
        nome = _xml_escape(p.get('nome', ''))
        freq = _xml_escape(p.get('frequencia', ''))
        ctx = _xml_escape(p.get('contexto', ''))
        produtos_xml += (
            f'\n    <produto nome="{nome}" frequencia="{freq}">'
            f'\n      <contexto>{ctx}</contexto>'
            f'\n    </produto>'
        )

    # Formatar queries recorrentes
    queries_xml = ""
    for q in patterns.get('queries_recorrentes', []):
        tipo = _xml_escape(q.get('tipo', 'outro'))
        desc = _xml_escape(q.get('descricao', ''))
        freq = _xml_escape(q.get('frequencia', ''))
        queries_xml += f'\n    <query tipo="{tipo}" frequencia="{freq}">{desc}</query>'

    # Formatar preferências
    prefs_xml = "\n".join(
        f"    <preferencia>{_xml_escape(p)}</preferencia>"
        for p in patterns.get('preferencias', [])
    )

    # Workflow típico
    workflow = _xml_escape(patterns.get('workflow_tipico', ''))

    content = f"""<user_patterns updated_at="{timestamp}" confianca="{confianca}" sessoes_analisadas="{sessions_analyzed}">
  <clientes_frequentes>{clientes_xml}
  </clientes_frequentes>
  <produtos_frequentes>{produtos_xml}
  </produtos_frequentes>
  <queries_recorrentes>{queries_xml}
  </queries_recorrentes>
  <preferencias>
{prefs_xml}
  </preferencias>
  <workflow_tipico>{workflow}</workflow_tipico>
</user_patterns>"""

    try:
        existing = AgentMemory.get_by_path(user_id, path)
        if existing:
            existing.content = content
        else:
            AgentMemory.create_file(user_id, path, content)

        logger.debug(f"[PATTERNS] Memory salva em {path}")
    except Exception as e:
        logger.warning(f"[PATTERNS] Erro ao salvar memory: {e}")


def _xml_escape(text: str) -> str:
    """Escapa caracteres especiais para XML."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def should_analyze_patterns(user_id: int, threshold: int = 10) -> bool:
    """
    Verifica se é hora de analisar padrões para o usuário.

    Critério: total de sessões do usuário é múltiplo de threshold.

    Args:
        user_id: ID do usuário
        threshold: A cada N sessões, analisa

    Returns:
        True se deve analisar
    """
    try:
        from ..models import AgentSession

        total = AgentSession.query.filter_by(user_id=user_id).count()
        return total > 0 and total % threshold == 0

    except Exception as e:
        logger.warning(f"[PATTERNS] Erro ao verificar threshold: {e}")
        return False
