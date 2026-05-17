"""API de busca semantica em sped_ecd_rule_embeddings.

Usado pela skill auditando-sped-vs-manual (T3.3).

Busca HIBRIDA (P1-3):
- Lookup EXATO por nome de regra (REGRA_X) quando query contem o codigo —
  cosine perde precisao para nomes unicos.
- Cosine vector search para resto da query (descricao em linguagem natural).
- Resultados exatos vem primeiro com similarity=1.0.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text

from app import db
from app.embeddings.client import get_voyage_client
from app.embeddings.config import (
    RERANK_SPED_RULES,
    SPED_RULES_RERANK_CANDIDATES,
    THRESHOLD_SPED_RULES,
    VOYAGE_RERANK_MODEL,
)

import logging
logger = logging.getLogger(__name__)


REGRA_NAME_RE = re.compile(r"\bREGRA_[A-Z_0-9]+\b")
REGISTRO_CODE_RE = re.compile(r"\b([0CIJK9]\d{3})\b")


def buscar_regras_semantico(
    query: str,
    limit: int = 10,
    chunk_type: str | None = None,
    bloco: str | None = None,
    registro: str | None = None,
    min_similarity: float | None = None,
) -> list[dict[str, Any]]:
    """Busca hibrida de regras normativas do Manual ECD.

    Estrategia em 2 camadas:
    1. **Exato** — se query contem `REGRA_X`, busca por `regra_name = X`
       direto (cosine ranqueia mal nomes proprios unicos). Tambem detecta
       codigo de registro (`I050`, `J930` etc) e injeta filtro `registro=`.
    2. **Semantico** — vector cosine para o restante da query (descricao
       em linguagem natural). Exclui chunks ja retornados pelo exato.

    Args:
        query: pergunta natural ou contendo REGRA_X / codigo de registro.
        limit: top-k total (exato + semantico).
        chunk_type: filtro 'registro' | 'regra' | 'campo' | 'plano_iteracao'.
        bloco: filtro 0|C|I|J|K|9.
        registro: filtro ex 'I050' (sobrepoe deteccao automatica).
        min_similarity: corte (default THRESHOLD_SPED_RULES).

    Returns:
        Lista de dicts com chunk + similarity + match_type (`exact`|`semantic`).
    """
    threshold = min_similarity if min_similarity is not None else THRESHOLD_SPED_RULES

    # Auto-detecta codigo de registro se nao foi passado explicitamente.
    # Ex: query "I050 codigo de conta duplicado" -> registro='I050'.
    # Autodetect e LASSO (permite chunks sem registro como categorias/gotchas);
    # passar `registro` explicitamente eh RESTRITIVO (filtra so esse registro).
    registro_autodetected = False
    if registro is None:
        m = REGISTRO_CODE_RE.search(query)
        if m:
            registro = m.group(1)
            registro_autodetected = True

    def _registro_clause() -> str:
        # Autodetect: inclui tambem chunks com registro NULL (categoria/gotcha/capitulo).
        # Explicit: estrito.
        return (
            "(registro = :registro OR registro IS NULL)"
            if registro_autodetected
            else "registro = :registro"
        )

    # CAMADA 1 — Exato por nome de regra
    exact_results: list[dict[str, Any]] = []
    exact_chunk_ids: set[str] = set()
    regras_in_query = REGRA_NAME_RE.findall(query)
    if regras_in_query:
        conds_exact = ["regra_name = ANY(:names)"]
        params_exact: dict[str, Any] = {"names": regras_in_query}
        if chunk_type:
            conds_exact.append("chunk_type = :chunk_type")
            params_exact["chunk_type"] = chunk_type
        if bloco:
            conds_exact.append("bloco = :bloco")
            params_exact["bloco"] = bloco
        if registro:
            conds_exact.append(_registro_clause())
            params_exact["registro"] = registro

        sql_exact = f"""
            SELECT chunk_id, chunk_type, bloco, registro, regra_name, severidade,
                   content, source_file, source_anchor
            FROM sped_ecd_rule_embeddings
            WHERE {" AND ".join(conds_exact)}
        """
        rows_exact = db.session.execute(text(sql_exact), params_exact).all()
        for row in rows_exact:
            exact_chunk_ids.add(row.chunk_id)
            exact_results.append({
                "chunk_id": row.chunk_id,
                "chunk_type": row.chunk_type,
                "bloco": row.bloco,
                "registro": row.registro,
                "regra_name": row.regra_name,
                "severidade": row.severidade,
                "content": row.content,
                "source": f"{row.source_file}{row.source_anchor or ''}",
                "similarity": 1.0,
                "match_type": "exact",
            })

    # CAMADA 2 — Semantico (cosine) com reranking opcional
    semantic_results: list[dict[str, Any]] = []
    remaining = limit - len(exact_results)
    if remaining > 0:
        # Rerank ativo SO quando: flag global ligada E sem REGRA_X na query
        # (P1-3 ja cobriu exato) E vai pedir top-K nao-trivial (>=5).
        use_rerank = (
            RERANK_SPED_RULES
            and not regras_in_query
            and remaining >= 5
        )
        # Quando rerank ativo, busca MAIS candidatos no cosine para o rerank
        # ter espaco para reordenar (default 50 vs `remaining`).
        k_cosine = SPED_RULES_RERANK_CANDIDATES if use_rerank else remaining

        client = get_voyage_client()
        response = client.embed([query], model="voyage-4-lite", input_type="query")
        if hasattr(response, "embeddings"):
            embeddings_list: list = response.embeddings
        else:
            embeddings_list = list(response)  # type: ignore[arg-type]
        query_emb = embeddings_list[0]

        conds = []
        params: dict[str, Any] = {"qemb": str(query_emb), "limit": k_cosine}
        if exact_chunk_ids:
            conds.append("chunk_id <> ALL(:exclude_ids)")
            params["exclude_ids"] = list(exact_chunk_ids)
        if chunk_type:
            conds.append("chunk_type = :chunk_type")
            params["chunk_type"] = chunk_type
        if bloco:
            conds.append("bloco = :bloco")
            params["bloco"] = bloco
        if registro:
            conds.append(_registro_clause())
            params["registro"] = registro

        where_clause = "WHERE " + " AND ".join(conds) if conds else ""

        sql_sem = f"""
            SELECT
                chunk_id, chunk_type, bloco, registro, regra_name, severidade,
                content, source_file, source_anchor,
                1 - (embedding <=> CAST(:qemb AS vector)) AS similarity
            FROM sped_ecd_rule_embeddings
            {where_clause}
            ORDER BY embedding <=> CAST(:qemb AS vector)
            LIMIT :limit
        """
        rows = db.session.execute(text(sql_sem), params).all()

        # Filtra cosine por threshold + monta candidates para rerank/return
        candidates: list[dict[str, Any]] = []
        for row in rows:
            sim = float(row.similarity)
            if sim < threshold:
                continue
            candidates.append({
                "chunk_id": row.chunk_id,
                "chunk_type": row.chunk_type,
                "bloco": row.bloco,
                "registro": row.registro,
                "regra_name": row.regra_name,
                "severidade": row.severidade,
                "content": row.content,
                "source": f"{row.source_file}{row.source_anchor or ''}",
                "similarity": sim,
                "match_type": "semantic",
            })

        # Re-rank cross-encoder se ativo e tiver candidatos suficientes
        if use_rerank and len(candidates) >= 5:
            try:
                documents = [c["content"] for c in candidates]
                rerank_resp = client.rerank(
                    query=query,
                    documents=documents,
                    model=VOYAGE_RERANK_MODEL,
                    top_k=min(remaining, len(documents)),
                )
                for r in rerank_resp.results:
                    c = candidates[r.index].copy()
                    c["similarity"] = round(float(r.relevance_score), 4)
                    c["match_type"] = "rerank"
                    semantic_results.append(c)
            except Exception as e:
                # Fallback graceful — devolve cosine puro top-`remaining`
                logger.warning(
                    f"[sped_rules_search] Rerank falhou ({type(e).__name__}: {e}); "
                    f"retornando cosine puro"
                )
                semantic_results = candidates[:remaining]
        else:
            # Cosine puro
            semantic_results = candidates[:remaining]

    return exact_results + semantic_results
