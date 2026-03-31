"""
P2-1: Busca em Sessões Anteriores — Custom MCP Tool.

Permite ao agente buscar em sessões passadas do usuário quando contexto
histórico é necessário (ex: "lembra daquele problema com o Atacadão?").

A busca é feita via LIKE em SQL sobre o JSONB de mensagens,
limitada ao usuário atual. Em debug mode, admin pode buscar cross-user
via target_user_id e filtrar por channel (teams/web).

Uso pelo agente:
    mcp__sessions__search_sessions(query="pedido Atacadão")
    mcp__sessions__list_recent_sessions()
    mcp__sessions__semantic_search_sessions(query="problema frete")
    mcp__sessions__list_session_users()  # admin-only, debug mode
"""

import logging
import threading
from typing import Annotated, Any, Dict, Optional, Tuple
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# User ID: ContextVar (mesma thread) + dict cross-thread SEGURO.
# MCP tools executam em sdk-pool-daemon thread — ContextVar não propaga.
# Dict só resolve se TODOS os callers ativos têm o MESMO user_id.
_current_user_id: ContextVar[int] = ContextVar('_session_search_user_id', default=0)
_user_id_by_caller: dict[int, int] = {}
_uid_lock = threading.Lock()


def set_current_user_id(user_id: int) -> None:
    """Define user_id para o contexto atual (ContextVar + dict cross-thread)."""
    _current_user_id.set(user_id)
    tid = threading.current_thread().ident
    with _uid_lock:
        _user_id_by_caller[tid] = user_id


def clear_current_user_id() -> None:
    """Remove user_id do caller atual no dict cross-thread."""
    tid = threading.current_thread().ident
    with _uid_lock:
        _user_id_by_caller.pop(tid, None)


def get_current_user_id() -> int:
    """Obtém user_id: ContextVar primeiro, fallback dict cross-thread seguro."""
    uid = _current_user_id.get()
    if uid == 0:
        with _uid_lock:
            unique_ids = set(_user_id_by_caller.values())
            if len(unique_ids) == 1:
                uid = next(iter(unique_ids))
    if uid == 0:
        raise RuntimeError("user_id não definido para session search")
    return uid


def _resolve_user_id(args: dict) -> int:
    """
    Resolve user_id efetivo: proprio usuario ou target em debug mode.

    Espelha o padrao de memory_mcp_tool.py:_resolve_user_id.

    Args:
        args: Dict dos argumentos da tool (pode conter target_user_id)

    Returns:
        user_id efetivo para a operacao

    Raises:
        PermissionError: target_user_id sem debug mode ativo
    """
    target = args.get('target_user_id')
    current = get_current_user_id()

    if target is None or target == current:
        return current

    # Cross-user requer debug mode (validacao deterministica)
    from ..config.permissions import get_debug_mode
    if not get_debug_mode():
        raise PermissionError(
            f"Acesso a sessoes de outro usuario (ID={target}) requer Modo Debug ativo. "
            f"Peca ao administrador ativar o toggle de debug."
        )

    logger.warning(
        f"[SESSION_SEARCH] DEBUG: acesso cross-user user={current} -> target={target}"
    )
    return target


def _build_channel_filter(channel: Optional[str]) -> Tuple[str, dict]:
    """
    Constroi fragmento SQL e params para filtro de canal.

    Args:
        channel: 'teams', 'web', ou None (sem filtro)

    Returns:
        Tupla (sql_fragment, params_dict)
    """
    if channel == 'teams':
        return "AND session_id LIKE :channel_pattern", {'channel_pattern': 'teams_%'}
    elif channel == 'web':
        return "AND session_id NOT LIKE :channel_pattern", {'channel_pattern': 'teams_%'}
    return "", {}


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
# OUTPUT SCHEMAS (Enhanced MCP — structuredContent)
# ============================================================================

SESSION_SEARCH_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "sessions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "title": {"type": "string"},
                    "created_at": {"type": ["string", "null"]},
                    "updated_at": {"type": ["string", "null"]},
                    "message_count": {"type": "integer"},
                    "channel": {"type": "string"},
                    "excerpt": {"type": ["string", "null"]},
                },
            },
        },
    },
    "required": ["count", "sessions"],
}

SESSION_LIST_RECENT_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "sessions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "title": {"type": "string"},
                    "created_at": {"type": ["string", "null"]},
                    "message_count": {"type": "integer"},
                    "cost_usd": {"type": "number"},
                    "summary": {"type": ["string", "null"]},
                    "topics": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
    "required": ["count", "sessions"],
}

SESSION_SEMANTIC_SEARCH_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "fallback_used": {"type": "boolean"},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "title": {"type": "string"},
                    "created_at": {"type": ["string", "null"]},
                    "similarity": {"type": "number"},
                    "user_content": {"type": "string"},
                    "assistant_summary": {"type": ["string", "null"]},
                },
            },
        },
    },
    "required": ["count", "fallback_used", "results"],
}

SESSION_LIST_USERS_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "users": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "nome": {"type": "string"},
                    "email": {"type": "string"},
                    "total_sessions": {"type": "integer"},
                    "web_sessions": {"type": "integer"},
                    "teams_sessions": {"type": "integer"},
                    "last_activity": {"type": ["string", "null"]},
                },
            },
        },
    },
    "required": ["count", "users"],
}

# ============================================================================
# MCP TOOL DEFINITIONS (Enhanced v4.0.0)
# ============================================================================

try:
    from claude_agent_sdk import ToolAnnotations
    from app.agente.tools._mcp_enhanced import enhanced_tool, create_enhanced_mcp_server

    @enhanced_tool(
        "search_sessions",
        (
            "Busca em sessões anteriores do usuário por texto. "
            "Use quando o operador perguntar sobre conversas passadas, "
            "pedidos discutidos anteriormente, ou decisões tomadas em sessões anteriores. "
            "Retorna trechos relevantes com data e contexto. "
            "Em debug mode: use target_user_id para buscar sessões de outro usuário, "
            "e channel='teams' ou 'web' para filtrar por canal."
        ),
        {"query": Annotated[str, "Texto a buscar em sessoes anteriores (minimo 2 caracteres). Busca em titulos e conteudo de mensagens"]},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=SESSION_SEARCH_OUTPUT_SCHEMA,
    )
    async def search_sessions(args: Dict[str, Any]) -> Dict[str, Any]:
        """Busca texto em sessões anteriores do usuário."""
        query = args.get("query", "").strip()
        channel = args.get("channel")  # 'teams', 'web', ou None

        if not query or len(query) < 2:
            return {
                "content": [{"type": "text", "text": "Erro: query deve ter pelo menos 2 caracteres."}],
                "is_error": True,
            }

        try:
            user_id = _resolve_user_id(args)
        except (RuntimeError, PermissionError) as e:
            return {
                "content": [{"type": "text", "text": f"Erro: {e}"}],
                "is_error": True,
            }

        def _search():
            from app import db
            from sqlalchemy import text

            # Filtro de canal (teams/web)
            channel_sql, channel_params = _build_channel_filter(channel)

            # Busca em JSONB messages via CAST + ILIKE (PostgreSQL)
            # Busca tanto nas mensagens brutas quanto no summary
            sql = text(f"""
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
                {channel_sql}
                AND (
                    CAST(data AS TEXT) ILIKE :query_pattern
                    OR CAST(summary AS TEXT) ILIKE :query_pattern
                    OR title ILIKE :query_pattern
                )
                ORDER BY updated_at DESC
                LIMIT :max_results
            """)

            params = {
                'user_id': user_id,
                'query_pattern': f'%{query}%',
                'max_results': MAX_SEARCH_RESULTS,
                **channel_params,
            }

            results = db.session.execute(sql, params).fetchall()

            if not results:
                structured = {"count": 0, "sessions": []}
                return f"Nenhuma sessão encontrada com '{query}'.", structured

            # Construir structured data + texto formatado
            structured_sessions = []
            is_cross_user = args.get('target_user_id') is not None
            header = f"🔍 Encontrei {len(results)} sessão(ões) com '{query}'"
            if is_cross_user:
                header += f" (user_id={user_id})"
            if channel:
                header += f" [canal: {channel}]"
            output_lines = [header + ":\n"]

            for row in results:
                session_id = row[0]
                title = row[1] or "Sem título"
                msg_count = row[2] or 0
                created_dt = row[3]
                updated_dt = row[4]
                created = created_dt.strftime('%d/%m/%Y %H:%M') if created_dt else 'data desconhecida'
                updated = updated_dt.strftime('%d/%m/%Y %H:%M') if updated_dt else ''

                # Indicar canal no output
                ch = "teams" if session_id.startswith('teams_') else "web"
                canal_tag = " [Teams]" if ch == "teams" else ""
                output_lines.append(f"📋 **{title}**{canal_tag} ({created})")
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

                structured_sessions.append({
                    "session_id": session_id,
                    "title": title,
                    "created_at": created_dt.isoformat() if created_dt else None,
                    "updated_at": updated_dt.isoformat() if updated_dt else None,
                    "message_count": msg_count,
                    "channel": ch,
                    "excerpt": excerpt or None,
                })

            structured = {"count": len(results), "sessions": structured_sessions}
            return "\n".join(output_lines), structured

        try:
            result_text, structured = _execute_with_context(_search)
            return {
                "content": [{"type": "text", "text": result_text}],
                "structuredContent": structured,
            }
        except Exception as e:
            logger.error(f"[SESSION_SEARCH] Erro na busca: {e}")
            return {
                "content": [{"type": "text", "text": f"Erro ao buscar sessões: {str(e)[:200]}"}],
                "is_error": True,
            }

    @enhanced_tool(
        "list_recent_sessions",
        (
            "Lista as sessões recentes do usuário com título, data e quantidade de mensagens. "
            "Use quando o operador quiser ver o histórico de conversas ou "
            "quando precisar de contexto sobre interações anteriores. "
            "Em debug mode: use target_user_id para listar sessões de outro usuário, "
            "e channel='teams' ou 'web' para filtrar por canal."
        ),
        {"limit": Annotated[int, "Numero maximo de sessoes recentes a retornar (default 10)"]},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=SESSION_LIST_RECENT_OUTPUT_SCHEMA,
    )
    async def list_recent_sessions(args: Dict[str, Any]) -> Dict[str, Any]:
        """Lista sessões recentes do usuário."""
        limit = min(args.get("limit", 10), MAX_RECENT_SESSIONS)
        channel = args.get("channel")  # 'teams', 'web', ou None

        try:
            user_id = _resolve_user_id(args)
        except (RuntimeError, PermissionError) as e:
            return {
                "content": [{"type": "text", "text": f"Erro: {e}"}],
                "is_error": True,
            }

        def _list():
            from ..models import AgentSession

            query = AgentSession.query.filter_by(user_id=user_id)

            # Filtro de canal via session_id pattern
            if channel == 'teams':
                query = query.filter(AgentSession.session_id.like('teams_%'))
            elif channel == 'web':
                query = query.filter(~AgentSession.session_id.like('teams_%'))

            sessions = query.order_by(
                AgentSession.updated_at.desc()
            ).limit(limit).all()

            if not sessions:
                structured = {"count": 0, "sessions": []}
                return "Nenhuma sessão anterior encontrada.", structured

            structured_sessions = []
            is_cross_user = args.get('target_user_id') is not None
            header = f"📚 Últimas {len(sessions)} sessões"
            if is_cross_user:
                header += f" (user_id={user_id})"
            if channel:
                header += f" [canal: {channel}]"
            output_lines = [header + ":\n"]

            for i, sess in enumerate(sessions, 1):
                title = sess.title or "Sem título"
                created = sess.created_at.strftime('%d/%m/%Y %H:%M') if sess.created_at else ''
                msg_count = sess.message_count or 0
                cost = float(sess.total_cost_usd or 0)

                canal_tag = " [Teams]" if sess.session_id.startswith('teams_') else ""
                output_lines.append(f"{i}. **{title}**{canal_tag}")
                output_lines.append(f"   📅 {created} | 💬 {msg_count} msgs | 💰 ${cost:.4f}")

                summary_text = None
                topics_list = []
                if sess.summary and isinstance(sess.summary, dict):
                    resumo = sess.summary.get('resumo_geral', '')
                    if resumo:
                        output_lines.append(f"   📝 {resumo}")
                        summary_text = resumo

                    topicos = sess.summary.get('topicos_abordados', [])
                    if topicos:
                        output_lines.append(f"   🏷️ {', '.join(topicos)}")
                        topics_list = topicos

                output_lines.append("")

                structured_sessions.append({
                    "session_id": sess.session_id,
                    "title": title,
                    "created_at": sess.created_at.isoformat() if sess.created_at else None,
                    "message_count": msg_count,
                    "cost_usd": cost,
                    "summary": summary_text,
                    "topics": topics_list,
                })

            structured = {"count": len(sessions), "sessions": structured_sessions}
            return "\n".join(output_lines), structured

        try:
            result_text, structured = _execute_with_context(_list)
            return {
                "content": [{"type": "text", "text": result_text}],
                "structuredContent": structured,
            }
        except Exception as e:
            logger.error(f"[SESSION_SEARCH] Erro ao listar: {e}")
            return {
                "content": [{"type": "text", "text": f"Erro ao listar sessões: {str(e)[:200]}"}],
                "is_error": True,
            }

    @enhanced_tool(
        "semantic_search_sessions",
        (
            "Busca semântica em sessões anteriores do usuário. "
            "Mais precisa que search_sessions para perguntas conceituais, "
            "temas ou situações passadas. Use quando o operador perguntar "
            "'lembra que...', 'já conversamos sobre...', ou temas abstratos. "
            "Encontra conversas por similaridade de significado, não apenas texto exato. "
            "Em debug mode: use target_user_id para buscar sessões de outro usuário."
        ),
        {"query": Annotated[str, "Texto ou tema para busca semantica por similaridade em sessoes anteriores (minimo 2 caracteres)"], "limit": Annotated[int, "Numero maximo de resultados a retornar (default 10)"]},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=SESSION_SEMANTIC_SEARCH_OUTPUT_SCHEMA,
    )
    async def semantic_search_sessions(args: Dict[str, Any]) -> Dict[str, Any]:
        """Busca semântica em sessões anteriores do usuário via embeddings."""
        query = args.get("query", "").strip()
        limit = min(args.get("limit", 10), MAX_SEARCH_RESULTS)

        if not query or len(query) < 2:
            return {
                "content": [{"type": "text", "text": "Erro: query deve ter pelo menos 2 caracteres."}],
                "is_error": True,
            }

        try:
            user_id = _resolve_user_id(args)
        except (RuntimeError, PermissionError) as e:
            return {
                "content": [{"type": "text", "text": f"Erro: {e}"}],
                "is_error": True,
            }

        def _semantic_search():
            try:
                from app.embeddings.session_search import buscar_sessoes_semantica
                results = buscar_sessoes_semantica(
                    query=query,
                    user_id=user_id,
                    limite=limit,
                    min_similarity=0.35,
                )
            except Exception as emb_err:
                logger.warning(f"[SESSION_SEARCH] Semantic search falhou, fallback ILIKE: {emb_err}")
                results = []

            if not results:
                return None  # Sinal para fallback

            # Formatar resultados + structured data
            structured_results = []
            is_cross_user = args.get('target_user_id') is not None
            header = f"🔍 Busca semântica encontrou {len(results)} resultado(s) para '{query}'"
            if is_cross_user:
                header += f" (user_id={user_id})"
            output_lines = [header + ":\n"]

            for r in results:
                title = r.get('session_title') or 'Sem título'
                created_iso = r.get('session_created_at', '')
                created_display = created_iso
                if created_iso:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(created_iso)
                        created_display = dt.strftime('%d/%m/%Y %H:%M')
                    except (ValueError, TypeError):
                        pass

                similarity = r.get('similarity', 0)
                similarity_pct = round(similarity * 100, 1)
                user_content = (r.get('user_content') or '')[:200]
                assistant_summary = (r.get('assistant_summary') or '')[:150]

                output_lines.append(f"📋 **{title}** ({created_display}) — {similarity_pct}% relevância")
                output_lines.append(f"   Pergunta: \"{user_content}\"")
                if assistant_summary:
                    output_lines.append(f"   Resposta: \"{assistant_summary}...\"")
                output_lines.append("")

                structured_results.append({
                    "session_id": r.get('session_id', ''),
                    "title": title,
                    "created_at": created_iso or None,
                    "similarity": round(similarity, 4),
                    "user_content": user_content,
                    "assistant_summary": assistant_summary or None,
                })

            structured = {
                "count": len(results),
                "fallback_used": False,
                "results": structured_results,
            }
            return "\n".join(output_lines), structured

        try:
            result = _execute_with_context(_semantic_search)

            # Se semantic search nao retornou nada, fallback para ILIKE
            if result is None:
                fallback_args = {"query": query}
                if args.get('target_user_id') is not None:
                    fallback_args['target_user_id'] = args['target_user_id']
                fallback_result = await search_sessions.handler(fallback_args)

                if not fallback_result.get("is_error"):
                    text_content = fallback_result["content"][0]["text"]
                    text_content = "⚠️ Busca semântica indisponível, usando busca textual:\n\n" + text_content
                    fallback_result["content"][0]["text"] = text_content

                    # Mapear structuredContent do search_sessions para schema semantic
                    fb_structured = fallback_result.get("structuredContent") or {}
                    fb_sessions = fb_structured.get("sessions", [])
                    fallback_result["structuredContent"] = {
                        "count": fb_structured.get("count", 0),
                        "fallback_used": True,
                        "results": [
                            {
                                "session_id": s.get("session_id", ""),
                                "title": s.get("title", ""),
                                "created_at": s.get("created_at"),
                                "similarity": 0.0,
                                "user_content": s.get("excerpt") or "",
                                "assistant_summary": None,
                            }
                            for s in fb_sessions
                        ],
                    }
                return fallback_result

            result_text, structured = result
            return {
                "content": [{"type": "text", "text": result_text}],
                "structuredContent": structured,
            }
        except Exception as e:
            logger.error(f"[SESSION_SEARCH] Erro na busca semântica: {e}")
            return {
                "content": [{"type": "text", "text": f"Erro ao buscar sessões: {str(e)[:200]}"}],
                "is_error": True,
            }

    @enhanced_tool(
        "list_session_users",
        (
            "Lista usuários que possuem sessões no sistema. "
            "Admin-only: requer Modo Debug ativo. "
            "Retorna user_id, nome, total de sessões, breakdown web/teams e última atividade. "
            "Use para descobrir target_user_id antes de buscar sessões de outro usuário."
        ),
        {"limit": Annotated[int, "Numero maximo de usuarios a retornar (default 20, max 50). Requer debug mode"]},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        output_schema=SESSION_LIST_USERS_OUTPUT_SCHEMA,
    )
    async def list_session_users(args: Dict[str, Any]) -> Dict[str, Any]:
        """Lista usuários com sessões (admin-only, requer debug mode)."""
        from ..config.permissions import get_debug_mode

        if not get_debug_mode():
            return {
                "content": [{"type": "text", "text":
                    "Erro: list_session_users requer Modo Debug ativo. "
                    "Peça ao administrador ativar o toggle de debug."
                }],
                "is_error": True,
            }

        limit = min(args.get("limit", 20), 50)

        def _list_users():
            from app import db
            from sqlalchemy import text

            sql = text("""
                SELECT
                    u.id AS user_id,
                    u.nome,
                    u.email,
                    COUNT(s.id) AS total_sessoes,
                    COUNT(CASE WHEN s.session_id LIKE 'teams_%%' THEN 1 END) AS sessoes_teams,
                    COUNT(CASE WHEN s.session_id NOT LIKE 'teams_%%' THEN 1 END) AS sessoes_web,
                    MAX(s.updated_at) AS ultima_atividade
                FROM usuarios u
                INNER JOIN agent_sessions s ON s.user_id = u.id
                WHERE u.id > 0
                GROUP BY u.id, u.nome, u.email
                ORDER BY ultima_atividade DESC
                LIMIT :limit
            """)

            results = db.session.execute(sql, {'limit': limit}).fetchall()

            if not results:
                structured = {"count": 0, "users": []}
                return "Nenhum usuário com sessões encontrado.", structured

            structured_users = []
            output_lines = [f"👥 {len(results)} usuários com sessões:\n"]

            for row in results:
                uid = row[0]
                nome = row[1] or "Sem nome"
                email = row[2] or ""
                total = row[3]
                teams = row[4]
                web = row[5]
                ultima_dt = row[6]
                ultima = ultima_dt.strftime('%d/%m/%Y %H:%M') if ultima_dt else ''

                output_lines.append(f"**{nome}** (ID={uid})")
                output_lines.append(f"   📧 {email}")
                output_lines.append(f"   📊 {total} sessões (web: {web}, teams: {teams})")
                output_lines.append(f"   🕐 Última atividade: {ultima}")
                output_lines.append("")

                structured_users.append({
                    "user_id": uid,
                    "nome": nome,
                    "email": email,
                    "total_sessions": total,
                    "web_sessions": web,
                    "teams_sessions": teams,
                    "last_activity": ultima_dt.isoformat() if ultima_dt else None,
                })

            output_lines.append(
                "💡 Use target_user_id=N em search_sessions, list_recent_sessions "
                "ou semantic_search_sessions para acessar sessões desse usuário."
            )
            structured = {"count": len(results), "users": structured_users}
            return "\n".join(output_lines), structured

        try:
            result_text, structured = _execute_with_context(_list_users)
            return {
                "content": [{"type": "text", "text": result_text}],
                "structuredContent": structured,
            }
        except Exception as e:
            logger.error(f"[SESSION_SEARCH] Erro ao listar usuários: {e}")
            return {
                "content": [{"type": "text", "text": f"Erro ao listar usuários: {str(e)[:200]}"}],
                "is_error": True,
            }

    # ========================================================================
    # MCP Server Registration (Enhanced v4.0.0)
    # ========================================================================
    sessions_server = create_enhanced_mcp_server(
        name="sessions",
        version="4.0.0",
        tools=[search_sessions, list_recent_sessions, semantic_search_sessions, list_session_users],
    )

    logger.info("[SESSION_SEARCH] Enhanced MCP 'sessions' v4.0.0 registrado (4 tools, structuredContent)")

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
