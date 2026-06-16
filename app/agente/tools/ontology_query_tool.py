"""
D4 (Onda 3) — Tool MCP `query_ontology`: read path da ontologia canônica.

Permite ao agente consultar diretamente a tabela `agent_memory_entities`
(nós canônicos de negócio: cliente, produto, transportadora, etc.) por
busca direta (entity_type / nome / chave), UNINDO o user_id do chamador
com user_id=0 (empresa/sistema).

DIFERENÇA de `query_graph_memories`:
  - `query_graph_memories` (HOP-1) navega via `agent_memory_entity_links`
    para encontrar memórias ligadas a entidades — exige link de memória.
  - `query_ontology_entities` (busca DIRETA) consulta `agent_memory_entities`
    sem depender de links — resolve nós canônicos bootstrapados pelo D2
    que ainda não têm link de memória.

FLAG: `USE_AGENT_ONTOLOGY` (= `AGENT_ONTOLOGY` env, default false).
  A tool `query_ontology` só é registrada no agente quando a flag está ON.
  A função núcleo `query_ontology_entities` está sempre disponível para
  uso programático (ex: outros services, testes).

IMPLEMENTAÇÃO: READ-ONLY. Sem escrita. Best-effort (sem raise em chamadas
  do agente; retorna lista vazia em caso de erro).
"""

import logging
import threading
from contextvars import ContextVar
from typing import Annotated, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# =====================================================================
# CONTEXTO DO USUÁRIO (espelho do padrão memory_mcp_tool.py)
# =====================================================================
# MCP tools são singleton (nível de módulo), user_id muda por request.
# ContextVar (mesma thread) + dict cross-thread como fallback seguro.

_current_user_id: ContextVar[int] = ContextVar('_ontology_query_user_id', default=0)
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
    """
    Obtém user_id: ContextVar primeiro, fallback dict cross-thread seguro.

    Raises:
        RuntimeError: Se user_id não pode ser determinado com segurança.
    """
    uid = _current_user_id.get()
    if uid == 0:
        with _uid_lock:
            unique_ids = set(_user_id_by_caller.values())
            if len(unique_ids) == 1:
                uid = next(iter(unique_ids))
            elif len(unique_ids) > 1:
                logger.warning(
                    "[ONTOLOGY_QUERY] Múltiplos user_ids ativos (%s) — "
                    "não é seguro resolver cross-thread",
                    unique_ids,
                )
    if uid == 0:
        raise RuntimeError(
            "[ONTOLOGY_QUERY] user_id não definido. "
            "Chame set_current_user_id() antes de usar a ontology tool."
        )
    return uid


# =====================================================================
# HELPERS DE CONTEXTO
# =====================================================================

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


# =====================================================================
# FUNÇÃO NÚCLEO — query_ontology_entities
# =====================================================================

def query_ontology_entities(
    user_id: int,
    entity_type: Optional[str] = None,
    name_like: Optional[str] = None,
    key: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Consulta ontologia canônica via busca DIRETA em `agent_memory_entities`.

    Une `user_id` do chamador + `user_id=0` (empresa/sistema) para incluir
    nós canônicos bootstrapados (D2: cliente/produto/transportadora).

    NÃO depende de `agent_memory_entity_links` — resolve nós sem link de
    memória, que seriam invisíveis ao HOP-1 de `query_graph_memories`.

    Args:
        user_id: ID do usuário chamador. Busca inclui user_id=0 automaticamente.
        entity_type: Filtro por tipo de entidade (ex: 'cliente', 'produto',
                     'transportadora'). None = todos os tipos.
        name_like: Filtro ILIKE parcial no nome da entidade (case-insensitive).
                   Ex: 'atacadao' → matches 'ATACADAO DISTRIBUIDORA'.
        key: Filtro por entity_key exato (CNPJ raiz, cod_produto, UF, etc.).
        limit: Máximo de resultados a retornar (default 20).

    Returns:
        Lista de dicts, cada um com:
            - entity_type (str): tipo da entidade
            - entity_name (str): nome normalizado (uppercase)
            - entity_key (str | None): ID canônico opcional
            - user_id (int): 0 = canônica empresa, N = pessoal do usuário

    Notes:
        - READ-ONLY: nunca escreve no banco.
        - Best-effort: retorna [] em caso de erro de DB (não propaga).
        - user_id=0 como chamador: ANY([0, 0]) = busca apenas sistema.
    """
    def _query():
        from app import db
        from sqlalchemy import text

        # user_id=0 como ANY([0, 0]) → busca apenas empresa (correto)
        user_ids = [user_id, 0] if user_id != 0 else [0]

        # Construir query dinamicamente (filtros opcionais)
        conditions = ["user_id = ANY(:user_ids)"]
        params: dict = {"user_ids": user_ids, "limit": max(1, min(limit, 200))}

        if entity_type:
            conditions.append("entity_type = :entity_type")
            params["entity_type"] = entity_type

        if name_like:
            conditions.append("entity_name ILIKE :name_like")
            params["name_like"] = f"%{name_like}%"

        if key:
            conditions.append("entity_key = :entity_key")
            params["entity_key"] = key

        where_clause = " AND ".join(conditions)

        sql = text(f"""
            SELECT entity_type, entity_name, entity_key, user_id
            FROM agent_memory_entities
            WHERE {where_clause}
            ORDER BY mention_count DESC, last_seen_at DESC
            LIMIT :limit
        """)

        rows = db.session.execute(sql, params).fetchall()

        return [
            {
                "entity_type": row[0],
                "entity_name": row[1],
                "entity_key": row[2],
                "user_id": row[3],
            }
            for row in rows
        ]

    try:
        return _execute_with_context(_query)
    except Exception as e:
        # Quando o erro vem de uma sessao herdada ja' poluida por um statement
        # ANTERIOR (a tool e' VITIMA, nao causa), ela se auto-recupera abaixo
        # (rollback + []), entao WARNING evita falso-positivo no Sentry
        # (PYTHON-FLASK-XA). Erro genuino desta tool continua ERROR.
        _msg_low = str(e).lower()
        _sessao_herdada = (
            "invalid transaction is rolled back" in _msg_low
            or "can't reconnect" in _msg_low
            or "rolled back due to a previous exception" in _msg_low
        )
        (logger.warning if _sessao_herdada else logger.error)(
            "[ONTOLOGY_QUERY] %s ao consultar ontologia (user_id=%s, "
            "entity_type=%s, name_like=%s, key=%s): %s",
            "Sessao herdada abortada" if _sessao_herdada else "Erro",
            user_id, entity_type, name_like, key, e,
        )
        # Best-effort rollback: se a sessao chegou aqui com uma transacao
        # invalida (ex: PendingRollbackError vindo de um statement anterior
        # que falhou), o erro re-aparece em TODA operacao subsequente na
        # mesma sessao ("Can't reconnect until invalid transaction is rolled
        # back"). Esta tool e READ-ONLY, entao limpar o estado da sessao e'
        # seguro e permite que o resto do request se recupere. PYTHON-FLASK-XA.
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        return []


# =====================================================================
# MCP TOOL DEFINITION — query_ontology
# =====================================================================
# Registra a tool sob flag USE_AGENT_ONTOLOGY.
# Quando flag OFF (default): ontology_server = None → não é registrado
# em client.py → tool invisível ao agente.
# Quando flag ON: tool mcp__ontology__query_ontology exposta ao agente.

ONTOLOGY_QUERY_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string"},
                    "entity_name": {"type": "string"},
                    "entity_key": {"type": ["string", "null"]},
                    "user_id": {"type": "integer"},
                },
                "required": ["entity_type", "entity_name", "entity_key", "user_id"],
            },
        },
    },
    "required": ["count", "entities"],
}

try:
    from app.agente.config.feature_flags import USE_AGENT_ONTOLOGY

    if not USE_AGENT_ONTOLOGY:
        # Flag OFF — tool não é exposta ao agente.
        # ontology_server = None sinalizará ao _register_mcp para pular.
        ontology_server = None
        logger.debug(
            "[ONTOLOGY_QUERY] USE_AGENT_ONTOLOGY=false — "
            "MCP 'ontology' não registrada (flag-gated)."
        )

    else:
        # Flag ON — define e registra a tool MCP.
        from claude_agent_sdk import ToolAnnotations
        from app.agente.tools._mcp_enhanced import enhanced_tool, create_enhanced_mcp_server

        @enhanced_tool(
            "query_ontology",
            (
                "Consulta a ontologia canônica de entidades de negócio (clientes, "
                "produtos, transportadoras, etc.) diretamente na base de nós. "
                "Use quando precisar encontrar um cliente/produto pelo nome ou chave "
                "sem depender de memórias vinculadas. "
                "Inclui automaticamente entidades canônicas da empresa (user_id=0) "
                "além das suas entidades pessoais. "
                "Filtros disponíveis: entity_type, name_like (parcial, ILIKE), key (exato)."
            ),
            {
                "entity_type": Annotated[
                    Optional[str],
                    "Tipo de entidade a filtrar: 'cliente', 'produto', 'transportadora', "
                    "'fornecedor', 'uf', 'cnpj', 'valor', 'conceito', 'processo', etc. "
                    "Omitir para retornar todos os tipos.",
                ],
                "name_like": Annotated[
                    Optional[str],
                    "Filtro parcial (ILIKE) no nome da entidade, case-insensitive. "
                    "Ex: 'atacadao' matches 'ATACADAO DISTRIBUIDORA'.",
                ],
                "key": Annotated[
                    Optional[str],
                    "Filtro por entity_key exato: CNPJ raiz (8 dígitos), cod_produto, UF, etc.",
                ],
                "limit": Annotated[
                    Optional[int],
                    "Máximo de entidades a retornar (default 20, máximo 200).",
                ],
            },
            annotations=ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=False,
            ),
            output_schema=ONTOLOGY_QUERY_OUTPUT_SCHEMA,
        )
        async def query_ontology(args: Dict[str, Any]) -> Dict[str, Any]:
            """Consulta ontologia canônica — busca direta em agent_memory_entities."""
            entity_type_arg = args.get("entity_type")
            name_like_arg = args.get("name_like")
            key_arg = args.get("key")
            limit_arg = int(args.get("limit") or 20)

            try:
                uid = get_current_user_id()
            except RuntimeError as e:
                return {
                    "content": [{"type": "text", "text": f"Erro: {e}"}],
                    "is_error": True,
                }

            results = query_ontology_entities(
                user_id=uid,
                entity_type=entity_type_arg,
                name_like=name_like_arg,
                key=key_arg,
                limit=limit_arg,
            )

            if not results:
                filter_desc = []
                if entity_type_arg:
                    filter_desc.append(f"tipo={entity_type_arg}")
                if name_like_arg:
                    filter_desc.append(f"nome~{name_like_arg}")
                if key_arg:
                    filter_desc.append(f"key={key_arg}")
                filter_str = ", ".join(filter_desc) if filter_desc else "sem filtros"
                text_out = f"Nenhuma entidade encontrada na ontologia ({filter_str})."
            else:
                lines = [f"Ontologia: {len(results)} entidade(s) encontrada(s).\n"]
                for r in results:
                    scope = "(empresa)" if r["user_id"] == 0 else "(pessoal)"
                    key_str = f" [{r['entity_key']}]" if r["entity_key"] else ""
                    lines.append(
                        f"- [{r['entity_type']}] {r['entity_name']}{key_str} {scope}"
                    )
                text_out = "\n".join(lines)

            structured = {"count": len(results), "entities": results}

            return {
                "content": [{"type": "text", "text": text_out}],
                "structuredContent": structured,
            }

        ontology_server = create_enhanced_mcp_server(
            name="ontology",
            version="1.0.0",
            tools=[query_ontology],
        )

        logger.info(
            "[ONTOLOGY_QUERY] Enhanced MCP 'ontology' v1.0.0 registrado "
            "(1 tool: query_ontology, flag AGENT_ONTOLOGY=true)"
        )

except ImportError as e:
    ontology_server = None
    logger.debug(f"[ONTOLOGY_QUERY] Dependência não disponível: {e}")
