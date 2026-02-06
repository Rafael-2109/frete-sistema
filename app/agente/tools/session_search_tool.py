"""
P2-1: Busca em Sessões Anteriores — Custom MCP Tool.

Permite ao agente buscar em sessões passadas do usuário quando contexto
histórico é necessário (ex: "lembra daquele problema com o Atacadão?").

A busca é feita via LIKE em SQL sobre o JSONB de mensagens,
limitada ao usuário atual. Retorna trechos com data e contexto.

Uso pelo agente:
    mcp__sessions__search_sessions(query="pedido Atacadão")
    mcp__sessions__list_recent_sessions()
"""

import logging
from typing import Any, Dict
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# User ID thread-safe (compartilhado com memory_mcp_tool via routes.py)
_current_user_id: ContextVar[int] = ContextVar('_session_search_user_id', default=0)


def set_current_user_id(user_id: int) -> None:
    """Define user_id para o contexto atual."""
    _current_user_id.set(user_id)


def get_current_user_id() -> int:
    """Obtém user_id do contexto atual."""
    uid = _current_user_id.get()
    if uid == 0:
        raise RuntimeError("user_id não definido para session search")
    return uid


def _execute_with_context(func):
    """Executa função garantindo Flask app context."""
    try:
        from flask import current_app
        _ = current_app.name
        return func()
    except RuntimeError:
        from app import create_app
        app = create_app()
        with app.app_context():
            return func()


# Máximo de resultados retornados
MAX_SEARCH_RESULTS = 10
MAX_RECENT_SESSIONS = 10

# ============================================================================
# MCP TOOL DEFINITIONS
# ============================================================================

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    @tool(
        "search_sessions",
        (
            "Busca em sessões anteriores do usuário por texto. "
            "Use quando o operador perguntar sobre conversas passadas, "
            "pedidos discutidos anteriormente, ou decisões tomadas em sessões anteriores. "
            "Retorna trechos relevantes com data e contexto."
        ),
        {"query": str},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def search_sessions(args: Dict[str, Any]) -> Dict[str, Any]:
        """Busca texto em sessões anteriores do usuário."""
        query = args.get("query", "").strip()

        if not query or len(query) < 2:
            return {
                "content": [{"type": "text", "text": "Erro: query deve ter pelo menos 2 caracteres."}],
                "is_error": True,
            }

        try:
            user_id = get_current_user_id()
        except RuntimeError as e:
            return {
                "content": [{"type": "text", "text": f"Erro: {e}"}],
                "is_error": True,
            }

        def _search():
            from app import db
            from sqlalchemy import text

            # Busca em JSONB messages via CAST + ILIKE (PostgreSQL)
            # Busca tanto nas mensagens brutas quanto no summary
            sql = text("""
                SELECT
                    session_id,
                    title,
                    message_count,
                    created_at,
                    updated_at,
                    CAST(data AS TEXT) as data_text,
                    CAST(summary AS TEXT) as summary_text
                FROM agent_sessions
                WHERE user_id = :user_id
                AND (
                    CAST(data AS TEXT) ILIKE :query_pattern
                    OR CAST(summary AS TEXT) ILIKE :query_pattern
                    OR title ILIKE :query_pattern
                )
                ORDER BY updated_at DESC
                LIMIT :max_results
            """)

            results = db.session.execute(sql, {
                'user_id': user_id,
                'query_pattern': f'%{query}%',
                'max_results': MAX_SEARCH_RESULTS,
            }).fetchall()

            if not results:
                return f"Nenhuma sessão encontrada com '{query}'."

            # Formatar resultados
            output_lines = [f"🔍 Encontrei {len(results)} sessão(ões) com '{query}':\n"]

            for row in results:
                session_id = row[0]
                title = row[1] or "Sem título"
                msg_count = row[2] or 0
                created = row[3].strftime('%d/%m/%Y %H:%M') if row[3] else 'data desconhecida'
                updated = row[4].strftime('%d/%m/%Y %H:%M') if row[4] else ''

                output_lines.append(f"📋 **{title}** ({created})")
                output_lines.append(f"   ID: {session_id[:8]}... | {msg_count} mensagens | Atualizada: {updated}")

                # Tentar extrair trecho relevante do data_text
                data_text = row[5] or ''
                excerpt = _extract_excerpt(data_text, query, max_chars=300)
                if excerpt:
                    output_lines.append(f"   Trecho: \"{excerpt}\"")

                # Se tem summary, mostrar resumo
                summary_text = row[6]
                if summary_text and query.lower() in summary_text.lower():
                    summary_excerpt = _extract_excerpt(summary_text, query, max_chars=200)
                    if summary_excerpt:
                        output_lines.append(f"   Resumo: \"{summary_excerpt}\"")

                output_lines.append("")  # Linha em branco

            return "\n".join(output_lines)

        try:
            result = _execute_with_context(_search)
            return {
                "content": [{"type": "text", "text": result}],
            }
        except Exception as e:
            logger.error(f"[SESSION_SEARCH] Erro na busca: {e}")
            return {
                "content": [{"type": "text", "text": f"Erro ao buscar sessões: {str(e)[:200]}"}],
                "is_error": True,
            }

    @tool(
        "list_recent_sessions",
        (
            "Lista as sessões recentes do usuário com título, data e quantidade de mensagens. "
            "Use quando o operador quiser ver o histórico de conversas ou "
            "quando precisar de contexto sobre interações anteriores."
        ),
        {"limit": int},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def list_recent_sessions(args: Dict[str, Any]) -> Dict[str, Any]:
        """Lista sessões recentes do usuário."""
        limit = min(args.get("limit", 10), MAX_RECENT_SESSIONS)

        try:
            user_id = get_current_user_id()
        except RuntimeError as e:
            return {
                "content": [{"type": "text", "text": f"Erro: {e}"}],
                "is_error": True,
            }

        def _list():
            from ..models import AgentSession

            sessions = AgentSession.query.filter_by(
                user_id=user_id
            ).order_by(
                AgentSession.updated_at.desc()
            ).limit(limit).all()

            if not sessions:
                return "Nenhuma sessão anterior encontrada."

            output_lines = [f"📚 Últimas {len(sessions)} sessões:\n"]

            for i, sess in enumerate(sessions, 1):
                title = sess.title or "Sem título"
                created = sess.created_at.strftime('%d/%m/%Y %H:%M') if sess.created_at else ''
                msg_count = sess.message_count or 0
                cost = float(sess.total_cost_usd or 0)

                output_lines.append(f"{i}. **{title}**")
                output_lines.append(f"   📅 {created} | 💬 {msg_count} msgs | 💰 ${cost:.4f}")

                # Se tem summary, mostrar resumo geral
                if sess.summary and isinstance(sess.summary, dict):
                    resumo = sess.summary.get('resumo_geral', '')
                    if resumo:
                        output_lines.append(f"   📝 {resumo}")

                    topicos = sess.summary.get('topicos_abordados', [])
                    if topicos:
                        output_lines.append(f"   🏷️ {', '.join(topicos)}")

                output_lines.append("")

            return "\n".join(output_lines)

        try:
            result = _execute_with_context(_list)
            return {
                "content": [{"type": "text", "text": result}],
            }
        except Exception as e:
            logger.error(f"[SESSION_SEARCH] Erro ao listar: {e}")
            return {
                "content": [{"type": "text", "text": f"Erro ao listar sessões: {str(e)[:200]}"}],
                "is_error": True,
            }

    # ========================================================================
    # MCP Server Registration
    # ========================================================================
    sessions_server = create_sdk_mcp_server(
        name="sessions",
        version="1.0.0",
        tools=[search_sessions, list_recent_sessions],
    )

    logger.info("[SESSION_SEARCH] Custom Tool MCP 'sessions' registrado com sucesso")

except ImportError as e:
    sessions_server = None
    logger.debug(f"[SESSION_SEARCH] claude_agent_sdk não disponível: {e}")


# ============================================================================
# HELPERS
# ============================================================================

def _extract_excerpt(text: str, query: str, max_chars: int = 300) -> str:
    """
    Extrai trecho de texto ao redor da query encontrada.

    Args:
        text: Texto completo
        query: Termo de busca
        max_chars: Máximo de caracteres no trecho

    Returns:
        Trecho com contexto ao redor do match, ou ''
    """
    if not text or not query:
        return ''

    lower_text = text.lower()
    lower_query = query.lower()
    pos = lower_text.find(lower_query)

    if pos == -1:
        return ''

    # Calcula janela ao redor do match
    half = max_chars // 2
    start = max(0, pos - half)
    end = min(len(text), pos + len(query) + half)

    excerpt = text[start:end].strip()

    # Limpa caracteres de controle e JSON artifacts
    excerpt = excerpt.replace('\\n', ' ').replace('\\"', '"')
    excerpt = ' '.join(excerpt.split())  # Normaliza espaços

    # Adiciona reticências se truncado
    if start > 0:
        excerpt = '...' + excerpt
    if end < len(text):
        excerpt = excerpt + '...'

    return excerpt
