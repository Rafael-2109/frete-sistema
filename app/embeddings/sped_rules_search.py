"""API de busca semantica em sped_ecd_rule_embeddings.

Usado pela skill auditando-sped-vs-manual (T3.3).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app import db
from app.embeddings.client import get_voyage_client
from app.embeddings.config import THRESHOLD_SPED_RULES


def buscar_regras_semantico(
    query: str,
    limit: int = 10,
    chunk_type: str | None = None,
    bloco: str | None = None,
    registro: str | None = None,
    min_similarity: float | None = None,
) -> list[dict[str, Any]]:
    """Busca regras normativas do Manual ECD por similaridade semantica.

    Args:
        query: pergunta natural (ex: "regra que valida CNPJ").
        limit: top-k.
        chunk_type: filtro 'registro' | 'regra' | 'campo' | 'plano_iteracao'.
        bloco: filtro 0|C|I|J|K|9.
        registro: filtro ex 'I050'.
        min_similarity: corte (default THRESHOLD_SPED_RULES).

    Returns:
        Lista de dicts com chunk + similarity.
    """
    threshold = min_similarity if min_similarity is not None else THRESHOLD_SPED_RULES

    client = get_voyage_client()
    response = client.embed([query], model="voyage-4-lite", input_type="query")
    embeddings = response.embeddings if hasattr(response, "embeddings") else response
    query_emb = embeddings[0]

    conds = []
    params: dict[str, Any] = {"qemb": str(query_emb), "limit": limit}
    if chunk_type:
        conds.append("chunk_type = :chunk_type")
        params["chunk_type"] = chunk_type
    if bloco:
        conds.append("bloco = :bloco")
        params["bloco"] = bloco
    if registro:
        conds.append("registro = :registro")
        params["registro"] = registro

    where_clause = "WHERE " + " AND ".join(conds) if conds else ""

    sql = f"""
        SELECT
            chunk_id, chunk_type, bloco, registro, regra_name, severidade,
            content, source_file, source_anchor,
            1 - (embedding <=> CAST(:qemb AS vector)) AS similarity
        FROM sped_ecd_rule_embeddings
        {where_clause}
        ORDER BY embedding <=> CAST(:qemb AS vector)
        LIMIT :limit
    """
    rows = db.session.execute(text(sql), params).all()

    results = []
    for row in rows:
        sim = float(row.similarity)
        if sim < threshold:
            continue
        results.append({
            "chunk_id": row.chunk_id,
            "chunk_type": row.chunk_type,
            "bloco": row.bloco,
            "registro": row.registro,
            "regra_name": row.regra_name,
            "severidade": row.severidade,
            "content": row.content,
            "source": f"{row.source_file}{row.source_anchor or ''}",
            "similarity": sim,
        })

    return results
