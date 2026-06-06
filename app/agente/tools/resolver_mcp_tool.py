"""MCP tool 'resolver' — expõe os resolvedores DETERMINÍSTICOS (app.resolvedores)
como fonte-que-prova de entidade/produto/transportadora/cliente. Consulta o dado
real; 'encontrado=false' é EXPLÍCITO para distinguir 'confirmei que não existe' de
'não procurei'. Item grounding (cobertura ampla).
"""
import logging

logger = logging.getLogger('sistema_fretes')


def _resolver_produto(termo, limit=10):
    from app.resolvedores.produto import resolver_produto
    return resolver_produto(termo, limit=limit) or []


def _resolver_transportadora(termo, limite=10):
    from app.resolvedores.transportadora import resolver_transportadora
    return resolver_transportadora(termo, limite=limite) or {}


def _resolver_cliente(termo):
    # B1: resolver_cliente_cli (chave 'clientes'), NAO resolver_cliente ('clientes_encontrados')
    from app.resolvedores.cliente import resolver_cliente_cli
    return resolver_cliente_cli(termo) or {}


def _resolver_entidade(tipo: str, termo: str) -> dict:
    t = (tipo or '').strip().lower()
    termo = (termo or '').strip()
    if not termo:
        return {'tipo': t, 'termo': termo, 'encontrado': False, 'erro': 'termo vazio'}
    if t == 'produto':
        rows = _resolver_produto(termo, limit=10)
        return {'tipo': 'produto', 'termo': termo, 'encontrado': bool(rows), 'candidatos': rows[:10]}
    if t == 'transportadora':
        r = _resolver_transportadora(termo, limite=10)
        cands = r.get('transportadoras', []) if isinstance(r, dict) else []
        return {'tipo': 'transportadora', 'termo': termo, 'encontrado': bool(cands), 'candidatos': cands[:10]}
    if t == 'cliente':
        r = _resolver_cliente(termo)
        cands = r.get('clientes', []) if isinstance(r, dict) else []
        return {'tipo': 'cliente', 'termo': termo, 'encontrado': bool(cands), 'candidatos': cands[:10]}
    return {'tipo': t, 'termo': termo, 'encontrado': False,
            'erro': f"tipo invalido: {tipo} (use produto|transportadora|cliente)"}


def _format_resultado(r: dict) -> str:
    if r.get('erro'):
        return f"resolver({r.get('tipo')},'{r.get('termo')}'): ERRO — {r['erro']}"
    if not r['encontrado']:
        return (f"resolver({r['tipo']},'{r['termo']}'): NÃO ENCONTRADO (busca no banco, inclui "
                f"correspondência aproximada). Indica inexistência PROVÁVEL — confirme em fonte "
                f"exata antes de afirmar 'não existe'. Mas já é diferente de 'não procurei'.")
    return f"resolver({r['tipo']},'{r['termo']}'): {len(r['candidatos'])} encontrado(s) — {r['candidatos'][:5]}"


try:
    from claude_agent_sdk import ToolAnnotations  # noqa: F401
    from app.agente.tools._mcp_enhanced import enhanced_tool, create_enhanced_mcp_server

    @enhanced_tool(
        "resolver_entidade",
        "Resolve (confirma na FONTE REAL do banco) uma entidade do sistema: tipo=produto|transportadora|cliente + termo. "
        "Use ANTES de afirmar que uma entidade existe/é de tal tipo. 'encontrado=false' = confirmado inexistente.",
        {"tipo": str, "termo": str},
    )
    async def resolver_entidade(args):
        try:
            r = _resolver_entidade(args.get("tipo", ""), args.get("termo", ""))
            return {"content": [{"type": "text", "text": _format_resultado(r)}], "structuredContent": r}
        except Exception as e:
            logger.error(f"[RESOLVER] erro: {e}")
            return {"content": [{"type": "text", "text": f"Erro ao resolver: {str(e)[:200]}"}], "is_error": True}

    resolver_server = create_enhanced_mcp_server(name="resolver", version="1.0.0", tools=[resolver_entidade])
    logger.info("[RESOLVER] Custom Tool MCP 'resolver' registrado (1 tool)")
except ImportError as e:
    resolver_server = None
    logger.debug(f"[RESOLVER] claude_agent_sdk nao disponivel: {e}")
