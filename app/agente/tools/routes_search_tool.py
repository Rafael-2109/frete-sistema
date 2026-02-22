"""
Busca Semantica de Rotas e Templates — Custom MCP Tool.

Permite ao agente buscar rotas, telas e APIs do sistema por linguagem natural.
Usa embeddings via route_template_search.search_routes() (pgvector).

Uso pelo agente:
    mcp__routes__search_routes(query="contas a pagar")
    mcp__routes__search_routes(query="fretes", tipo="rota_api")
"""

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _execute_with_context(func):
    """Executa funcao garantindo Flask app context."""
    try:
        from flask import current_app
        _ = current_app.name
        return func()
    except RuntimeError:
        from app import create_app
        app = create_app()
        with app.app_context():
            return func()


def _format_results(results: list, query: str) -> str:
    """
    Formata resultados da busca para exibicao no agente.

    Args:
        results: Lista de dicts retornada por search_routes()
        query: Texto original da busca

    Returns:
        Texto formatado com URLs clicaveis e metadados
    """
    if not results:
        return (
            f"Nenhuma rota encontrada para '{query}'.\n\n"
            "Sugestoes:\n"
            "- Tente termos mais genericos (ex: 'financeiro' em vez de 'contas a pagar vencidas')\n"
            "- Use tipo='rota_template' para telas ou tipo='rota_api' para APIs\n"
            "- Verifique se os embeddings de rotas foram indexados"
        )

    base_url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")
    # Remove trailing slash do base_url se houver
    base_url = base_url.rstrip("/")

    lines = [f"Encontrei {len(results)} resultado(s) para '{query}':\n"]

    for i, r in enumerate(results, 1):
        tipo = r.get("tipo", "")
        tipo_label = "Tela" if tipo == "rota_template" else "API" if tipo == "rota_api" else tipo
        url_path = r.get("url_path", "")
        menu_path = r.get("menu_path")
        template_path = r.get("template_path")
        permission = r.get("permission_decorator")
        blueprint = r.get("blueprint_name", "")
        function = r.get("function_name", "")
        methods = r.get("http_methods", "")
        similarity = r.get("similarity", 0)
        docstring = r.get("docstring")
        source_file = r.get("source_file", "")
        ajax_endpoints = r.get("ajax_endpoints")

        # URL clicavel
        full_url = f"{base_url}{url_path}" if url_path else ""

        lines.append(f"**{i}. {function}** [{tipo_label}]")
        if full_url:
            lines.append(f"   URL: {full_url}")
        if methods:
            lines.append(f"   Metodos: {methods}")
        if menu_path:
            lines.append(f"   Menu: {menu_path}")
        else:
            lines.append("   Menu: Acesso direto (sem menu)")
        if template_path:
            lines.append(f"   Template: {template_path}")
        if permission:
            lines.append(f"   Permissao: {permission}")
        if docstring:
            # Truncar docstring longa
            doc_short = docstring[:120].replace("\n", " ").strip()
            if len(docstring) > 120:
                doc_short += "..."
            lines.append(f"   Descricao: {doc_short}")
        if ajax_endpoints:
            lines.append(f"   AJAX: {ajax_endpoints}")
        lines.append(f"   Blueprint: {blueprint} | Arquivo: {source_file}")
        lines.append(f"   Similaridade: {similarity:.1%}")
        lines.append("")

    return "\n".join(lines)


# ============================================================================
# MCP TOOL DEFINITIONS
# ============================================================================

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    @tool(
        "search_routes",
        (
            "Busca rotas, telas e APIs do sistema por linguagem natural. "
            "Use para responder 'onde fica a tela de X?', 'qual URL de Y?', "
            "'como acesso Z?', 'quais APIs existem para W?'. "
            "Retorna URL clicavel, menu, template e metadados. "
            "~300 rotas indexadas cobrindo todos os modulos do sistema."
        ),
        {"query": str, "tipo": str, "limit": int},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def search_routes(args: Dict[str, Any]) -> Dict[str, Any]:
        """Busca semantica em rotas e templates do sistema."""
        query = args.get("query", "").strip()
        tipo = args.get("tipo")  # 'rota_template' | 'rota_api' | None
        limit_raw = args.get("limit")

        if not query or len(query) < 2:
            return {
                "content": [{"type": "text", "text": "Erro: query deve ter pelo menos 2 caracteres."}],
                "is_error": True,
            }

        # Validar tipo se fornecido
        valid_tipos = ("rota_template", "rota_api")
        if tipo is not None and tipo not in valid_tipos:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Erro: tipo deve ser 'rota_template' ou 'rota_api'. Recebido: '{tipo}'",
                }],
                "is_error": True,
            }

        limit = min(int(limit_raw or 5), 20)

        def _search():
            from app.embeddings.route_template_search import search_routes as do_search
            return do_search(query=query, tipo=tipo, limit=limit)

        try:
            results = _execute_with_context(_search)
            text = _format_results(results, query)
            return {
                "content": [{"type": "text", "text": text}],
            }
        except Exception as e:
            logger.error(f"[ROUTES_SEARCH] Erro na busca: {e}")
            return {
                "content": [{"type": "text", "text": f"Erro ao buscar rotas: {str(e)[:200]}"}],
                "is_error": True,
            }

    # ========================================================================
    # MCP Server Registration
    # ========================================================================
    routes_server = create_sdk_mcp_server(
        name="routes",
        version="1.0.0",
        tools=[search_routes],
    )

    logger.info("[ROUTES_SEARCH] Custom Tool MCP 'routes' registrado com sucesso (1 tool)")

except ImportError as e:
    routes_server = None
    logger.debug(f"[ROUTES_SEARCH] claude_agent_sdk nao disponivel: {e}")
