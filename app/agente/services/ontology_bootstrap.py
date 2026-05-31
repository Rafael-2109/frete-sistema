"""
Onda 3 / D2 — Bootstrap de ontologia canônica no Knowledge Graph.

Cria nós canônicos de negócio (cliente/produto/transportadora) com user_id=0
(escopo empresa) a partir das tabelas-mestre.

CUSTO: ZERO de API — _upsert_entity é INSERT idempotente, sem Voyage.
FLAG: USE_AGENT_ONTOLOGY (AGENT_ONTOLOGY=true) OU --force para escrita real.

Uso via CLI:
    source .venv/bin/activate
    # Dry-run (sempre permitido — não escreve):
    python scripts/agente/bootstrap_ontologia.py --dry-run
    # Escrita real (exige flag ou --force):
    AGENT_ONTOLOGY=true python scripts/agente/bootstrap_ontologia.py
    python scripts/agente/bootstrap_ontologia.py --force
    # Tipo específico:
    python scripts/agente/bootstrap_ontologia.py --entity-type produto --dry-run
    # Limite de rows (útil para smoke-test):
    python scripts/agente/bootstrap_ontologia.py --limit 10 --dry-run

NOTA de deploy:
    Confirmar COUNT(DISTINCT substring(cnpj_cpf FROM 1 FOR 8)) em PROD antes de
    rodar bootstrap de clientes — dados locais são teste.
    Rodar APÓS migrações de DB e ANTES de ativar flag USE_AGENT_ONTOLOGY.
"""
import logging
from typing import Iterable, Optional

from sqlalchemy import text

from app.agente.services.knowledge_graph_service import _upsert_entity  # noqa: F401

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapa de fontes canônicas por entity_type
# ---------------------------------------------------------------------------

_ENTITY_SOURCE_MAP: dict = {
    "produto": {
        "tabela": "cadastro_palletizacao",
        "key_field": "cod_produto",
        "name_field": "nome_produto",
    },
    "transportadora": {
        "tabela": "transportadoras",
        "key_field": "cnpj",
        "name_field": "razao_social",
    },
    "cliente": {
        "tabela": "carteira_principal",
        "key_field": "cnpj_cpf",
        "name_field": "raz_social",
    },
}

# ---------------------------------------------------------------------------
# Leitura das tabelas-mestre
# ---------------------------------------------------------------------------

def _read_tabela(entity_type: str, conn, limit: Optional[int] = None) -> list:
    """
    Lê linhas da tabela-mestre para um entity_type.

    Para 'produto': filtra ativo=True AND produto_vendido=True.
    Para 'cliente': DISTINCT por raiz CNPJ (primeiros 8 dígitos de cnpj_cpf).
    Para 'transportadora': razao_social IS NOT NULL AND razao_social != ''.

    Retorna lista de dicts {key_field: ..., name_field: ...}.
    """
    cfg = _ENTITY_SOURCE_MAP[entity_type]
    tabela = cfg["tabela"]
    key_field = cfg["key_field"]
    name_field = cfg["name_field"]
    limit_clause = f"LIMIT {int(limit)}" if limit else ""

    if entity_type == "produto":
        sql = f"""
            SELECT {key_field}, {name_field}
            FROM {tabela}
            WHERE ativo = TRUE AND produto_vendido = TRUE
            ORDER BY {key_field}
            {limit_clause}
        """
    elif entity_type == "transportadora":
        sql = f"""
            SELECT {key_field}, {name_field}
            FROM {tabela}
            WHERE {name_field} IS NOT NULL AND {name_field} != ''
            ORDER BY id
            {limit_clause}
        """
    elif entity_type == "cliente":
        # DISTINCT por raiz CNPJ (8 dígitos) — nome canônico = primeiro encontrado por CNPJ raiz
        sql = f"""
            SELECT DISTINCT ON (substring(regexp_replace({key_field}, '\\D', '', 'g') FROM 1 FOR 8))
                {key_field},
                {name_field}
            FROM {tabela}
            WHERE {key_field} IS NOT NULL
              AND {key_field} != ''
              AND {name_field} IS NOT NULL
              AND {name_field} != ''
            ORDER BY substring(regexp_replace({key_field}, '\\D', '', 'g') FROM 1 FOR 8),
                     {key_field}
            {limit_clause}
        """
    else:
        raise ValueError(f"entity_type desconhecido: {entity_type!r}")

    result = conn.execute(text(sql))
    rows = []
    for row in result.fetchall():
        rows.append({key_field: row[0], name_field: row[1]})
    return rows


# ---------------------------------------------------------------------------
# bootstrap_entities — núcleo de inserção
# ---------------------------------------------------------------------------

def bootstrap_entities(
    entity_type: str,
    rows: Iterable[dict],
    conn,
) -> int:
    """
    Insere/atualiza nós canônicos no KG para um entity_type.

    Para cada row em rows:
    - extrai entity_key = row[key_field], entity_name = row[name_field]
    - pula se nome ou chave vazios/None
    - chama _upsert_entity(conn, user_id=0, entity_type, entity_name, entity_key)
    - best-effort por row: exceções são logadas mas não abortam o loop

    Args:
        entity_type: Um dos tipos em _ENTITY_SOURCE_MAP.
        rows: Iterable de dicts com key_field e name_field.
        conn: Conexão SQLAlchemy (conn = db.engine.connect() ou similar).

    Returns:
        Número de entidades inseridas/atualizadas com sucesso.
    """
    cfg = _ENTITY_SOURCE_MAP.get(entity_type)
    if not cfg:
        raise ValueError(f"entity_type desconhecido: {entity_type!r}")

    key_field = cfg["key_field"]
    name_field = cfg["name_field"]
    count = 0

    for row in rows:
        entity_key = row.get(key_field)
        entity_name = row.get(name_field)

        # Pular se chave ou nome vazios
        if not entity_key or not entity_name:
            continue

        entity_key = str(entity_key).strip()
        entity_name = str(entity_name).strip()

        if not entity_key or not entity_name:
            continue

        try:
            _upsert_entity(conn, 0, entity_type, entity_name, entity_key)
            count += 1
        except Exception as exc:
            logger.warning(
                "[ONTOLOGY] Erro ao inserir %s key=%r name=%r: %s",
                entity_type, entity_key, entity_name, exc,
            )

    return count


# ---------------------------------------------------------------------------
# bootstrap_all — ponto de entrada para CLI
# ---------------------------------------------------------------------------

def bootstrap_all(
    conn,
    limit: Optional[int] = None,
) -> dict:
    """
    Lê as 3 tabelas-mestre e chama bootstrap_entities para cada tipo.

    Args:
        conn: Conexão SQLAlchemy aberta pelo caller (com transação ativa ou não).
        limit: Se fornecido, limita o número de rows por tabela (útil para smoke-test).

    Returns:
        Dict {entity_type: n_insertions} para os 3 tipos.
    """
    results = {}
    for entity_type in _ENTITY_SOURCE_MAP:
        try:
            rows = _read_tabela(entity_type, conn, limit=limit)
            n = bootstrap_entities(entity_type, rows, conn)
            results[entity_type] = n
            logger.info("[ONTOLOGY] bootstrap %s: %d entidades", entity_type, n)
        except Exception as exc:
            logger.error("[ONTOLOGY] Erro no bootstrap de %s: %s", entity_type, exc)
            results[entity_type] = 0

    return results
