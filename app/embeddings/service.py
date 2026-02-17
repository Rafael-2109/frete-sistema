"""
Servico de alto nivel para embeddings.

Fornece API unificada para:
- Gerar embeddings de texto (documents, queries)
- Buscar por similaridade semantica (pgvector ou fallback Python)
- Reranking de resultados

Uso:
    from app.embeddings.service import EmbeddingService

    svc = EmbeddingService()
    embeddings = svc.embed_texts(["texto1", "texto2"], input_type="document")
    results = svc.search_ssw_docs("como fazer MDF-e", limit=5)
"""

import json
import math
from typing import List, Dict, Any

from sqlalchemy import text

from app import db
from app.embeddings.config import (
    VOYAGE_DEFAULT_MODEL,
    VOYAGE_RERANK_MODEL,
    VOYAGE_EMBEDDING_DIMENSIONS,
    EMBEDDING_BATCH_SIZE,
    SEARCH_DEFAULT_LIMIT,
    SEARCH_MIN_SIMILARITY,
    RERANK_TOP_K,
    EMBEDDINGS_ENABLED,
    RERANKING_ENABLED,
)


class EmbeddingService:
    """
    Servico principal de embeddings.

    Abstrai Voyage AI client e pgvector, fornecendo interface simples
    para os consumidores (skills, services, etc.).
    """

    def __init__(self, model: str = None, dimensions: int = None):
        self.model = model or VOYAGE_DEFAULT_MODEL
        self.dimensions = dimensions or VOYAGE_EMBEDDING_DIMENSIONS
        self._pgvector_available = None  # Cache de deteccao

    # ================================================================
    # EMBEDDING
    # ================================================================

    def embed_texts(
        self,
        texts: List[str],
        input_type: str = "document",
        model: str = None,
    ) -> List[List[float]]:
        """
        Gera embeddings para uma lista de textos.

        Args:
            texts: Lista de textos para embeddar
            input_type: "document" para indexacao, "query" para busca
            model: Modelo Voyage AI (default: config)

        Returns:
            Lista de embeddings (cada um e uma lista de floats)

        Raises:
            ValueError: Se texts estiver vazio
            RuntimeError: Se Voyage AI falhar
        """
        if not texts:
            return []

        from app.embeddings.client import get_voyage_client
        vo = get_voyage_client()

        model = model or self.model
        all_embeddings = []

        # Processar em batches de 128 (limite Voyage AI)
        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i:i + EMBEDDING_BATCH_SIZE]
            try:
                result = vo.embed(
                    batch,
                    model=model,
                    input_type=input_type,
                    output_dimension=self.dimensions,
                )
                all_embeddings.extend(result.embeddings)
            except Exception as e:
                raise RuntimeError(
                    f"Erro ao gerar embeddings com Voyage AI (modelo={model}, "
                    f"batch={i}-{i+len(batch)} de {len(texts)}): {e}"
                ) from e

        return all_embeddings

    def embed_query(self, query: str, model: str = None) -> List[float]:
        """
        Gera embedding para uma query de busca.

        Args:
            query: Texto da query
            model: Modelo (default: config)

        Returns:
            Embedding como lista de floats
        """
        embeddings = self.embed_texts([query], input_type="query", model=model)
        return embeddings[0]

    # ================================================================
    # BUSCA SEMANTICA — SSW DOCS
    # ================================================================

    def search_ssw_docs(
        self,
        query: str,
        limit: int = None,
        min_similarity: float = None,
        subdir_filter: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca semantica nos documentos SSW via pgvector.

        Args:
            query: Texto da busca
            limit: Maximo de resultados
            min_similarity: Score minimo (0-1)
            subdir_filter: Filtrar por subdiretorio (ex: "comercial", "fiscal")

        Returns:
            Lista de dicts com doc_path, chunk_text, heading, similarity
        """
        if not EMBEDDINGS_ENABLED:
            return []

        limit = limit or SEARCH_DEFAULT_LIMIT
        min_similarity = min_similarity or SEARCH_MIN_SIMILARITY

        # Gerar embedding da query
        query_embedding = self.embed_query(query)

        # Buscar por similaridade
        if self._is_pgvector_available():
            results = self._search_pgvector_ssw(
                query_embedding, limit, min_similarity, subdir_filter
            )
        else:
            results = self._search_fallback_ssw(
                query_embedding, limit, min_similarity, subdir_filter
            )

        # Reranking opcional
        if RERANKING_ENABLED and results:
            results = self._rerank_results(query, results)

        return results

    def _search_pgvector_ssw(
        self,
        query_embedding: List[float],
        limit: int,
        min_similarity: float,
        subdir_filter: str = None,
    ) -> List[Dict[str, Any]]:
        """Busca via pgvector usando operador de cosine distance."""
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # Query com operador <=> (cosine distance) do pgvector
        # similarity = 1 - distance
        where_clause = ""
        if subdir_filter:
            where_clause = "AND doc_path LIKE :subdir_pattern"

        sql = text(f"""
            SELECT
                id,
                doc_path,
                chunk_index,
                chunk_text,
                heading,
                doc_title,
                char_count,
                1 - (CAST(embedding AS vector) <=> CAST(:query_embedding AS vector)) AS similarity
            FROM ssw_document_embeddings
            WHERE embedding IS NOT NULL
            {where_clause}
            ORDER BY CAST(embedding AS vector) <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """)

        params = {
            "query_embedding": embedding_str,
            "limit": limit * 2,  # Pegar mais para filtrar por min_similarity
        }
        if subdir_filter:
            params["subdir_pattern"] = f"{subdir_filter}/%"

        result = db.session.execute(sql, params)
        rows = result.fetchall()

        results = []
        for row in rows:
            similarity = float(row.similarity)
            if similarity >= min_similarity:
                results.append({
                    "id": row.id,
                    "doc_path": row.doc_path,
                    "chunk_index": row.chunk_index,
                    "chunk_text": row.chunk_text,
                    "heading": row.heading,
                    "doc_title": row.doc_title,
                    "char_count": row.char_count,
                    "similarity": round(similarity, 4),
                })

        return results[:limit]

    def _search_fallback_ssw(
        self,
        query_embedding: List[float],
        limit: int,
        min_similarity: float,
        subdir_filter: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca fallback sem pgvector — carrega embeddings do banco e calcula
        cosine similarity em Python.

        ATENCAO: Menos eficiente que pgvector. Adequado para <10K registros.
        """
        from app.embeddings.models import SswDocumentEmbedding

        query = SswDocumentEmbedding.query.filter(
            SswDocumentEmbedding.embedding.isnot(None)
        )

        if subdir_filter:
            query = query.filter(
                SswDocumentEmbedding.doc_path.like(f"{subdir_filter}/%")
            )

        docs = query.all()

        if not docs:
            return []

        # Calcular similaridade em Python
        scored = []
        for doc in docs:
            try:
                doc_embedding = json.loads(doc.embedding)
            except (json.JSONDecodeError, TypeError):
                continue

            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            if similarity >= min_similarity:
                scored.append((doc, similarity))

        # Ordenar por similaridade (desc)
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, similarity in scored[:limit]:
            results.append({
                "id": doc.id,
                "doc_path": doc.doc_path,
                "chunk_index": doc.chunk_index,
                "chunk_text": doc.chunk_text,
                "heading": doc.heading,
                "doc_title": doc.doc_title,
                "char_count": doc.char_count,
                "similarity": round(similarity, 4),
            })

        return results

    # ================================================================
    # BUSCA SEMANTICA — PRODUTOS
    # ================================================================

    def search_products(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca semantica em produtos.

        Args:
            query: Texto de busca (nome, descricao, sinonimos)
            limit: Maximo de resultados
            min_similarity: Score minimo

        Returns:
            Lista de dicts com cod_produto, nome_produto, similarity
        """
        if not EMBEDDINGS_ENABLED:
            return []

        min_similarity = min_similarity or SEARCH_MIN_SIMILARITY

        query_embedding = self.embed_query(query)

        if self._is_pgvector_available():
            return self._search_pgvector_products(query_embedding, limit, min_similarity)
        else:
            return self._search_fallback_products(query_embedding, limit, min_similarity)

    def _search_pgvector_products(
        self,
        query_embedding: List[float],
        limit: int,
        min_similarity: float,
    ) -> List[Dict[str, Any]]:
        """Busca produtos via pgvector."""
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = text("""
            SELECT
                id,
                cod_produto,
                nome_produto,
                tipo_materia_prima,
                1 - (CAST(embedding AS vector) <=> CAST(:query_embedding AS vector)) AS similarity
            FROM product_embeddings
            WHERE embedding IS NOT NULL
            ORDER BY CAST(embedding AS vector) <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """)

        result = db.session.execute(sql, {
            "query_embedding": embedding_str,
            "limit": limit * 2,
        })

        results = []
        for row in result.fetchall():
            similarity = float(row.similarity)
            if similarity >= min_similarity:
                results.append({
                    "cod_produto": row.cod_produto,
                    "nome_produto": row.nome_produto,
                    "tipo_materia_prima": row.tipo_materia_prima,
                    "similarity": round(similarity, 4),
                })

        return results[:limit]

    def _search_fallback_products(
        self,
        query_embedding: List[float],
        limit: int,
        min_similarity: float,
    ) -> List[Dict[str, Any]]:
        """Busca produtos fallback sem pgvector."""
        from app.embeddings.models import ProductEmbedding

        docs = ProductEmbedding.query.filter(
            ProductEmbedding.embedding.isnot(None)
        ).all()

        scored = []
        for doc in docs:
            try:
                doc_embedding = json.loads(doc.embedding)
            except (json.JSONDecodeError, TypeError):
                continue

            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            if similarity >= min_similarity:
                scored.append((doc, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, similarity in scored[:limit]:
            results.append({
                "cod_produto": doc.cod_produto,
                "nome_produto": doc.nome_produto,
                "tipo_materia_prima": doc.tipo_materia_prima,
                "similarity": round(similarity, 4),
            })

        return results

    # ================================================================
    # BUSCA SEMANTICA — ENTIDADES FINANCEIRAS
    # ================================================================

    def search_entities(
        self,
        query: str,
        entity_type: str = 'supplier',
        limit: int = 5,
        min_similarity: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca semantica em entidades financeiras (fornecedores/clientes).

        Args:
            query: Nome do fornecedor/cliente (pode ser truncado/abreviado)
            entity_type: 'supplier', 'customer', ou 'all'
            limit: Maximo de resultados
            min_similarity: Score minimo (0-1)

        Returns:
            Lista de dicts com cnpj_raiz, cnpj_completo, nome, similarity, entity_type
        """
        if not EMBEDDINGS_ENABLED:
            return []

        min_similarity = min_similarity or SEARCH_MIN_SIMILARITY

        query_embedding = self.embed_query(query)

        if self._is_pgvector_available():
            return self._search_pgvector_entities(
                query_embedding, entity_type, limit, min_similarity
            )
        else:
            return self._search_fallback_entities(
                query_embedding, entity_type, limit, min_similarity
            )

    def _search_pgvector_entities(
        self,
        query_embedding: List[float],
        entity_type: str,
        limit: int,
        min_similarity: float,
    ) -> List[Dict[str, Any]]:
        """Busca entidades financeiras via pgvector."""
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        where_clause = ""
        if entity_type != 'all':
            where_clause = "AND entity_type = :entity_type"

        sql = text(f"""
            SELECT
                id,
                entity_type,
                cnpj_raiz,
                cnpj_completo,
                nome,
                1 - (CAST(embedding AS vector) <=> CAST(:query_embedding AS vector)) AS similarity
            FROM financial_entity_embeddings
            WHERE embedding IS NOT NULL
            {where_clause}
            ORDER BY CAST(embedding AS vector) <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """)

        params = {
            "query_embedding": embedding_str,
            "limit": limit * 2,
        }
        if entity_type != 'all':
            params["entity_type"] = entity_type

        result = db.session.execute(sql, params)

        results = []
        for row in result.fetchall():
            similarity = float(row.similarity)
            if similarity >= min_similarity:
                results.append({
                    "cnpj_raiz": row.cnpj_raiz,
                    "cnpj_completo": row.cnpj_completo,
                    "nome": row.nome,
                    "similarity": round(similarity, 4),
                    "entity_type": row.entity_type,
                })

        return results[:limit]

    def _search_fallback_entities(
        self,
        query_embedding: List[float],
        entity_type: str,
        limit: int,
        min_similarity: float,
    ) -> List[Dict[str, Any]]:
        """Busca entidades financeiras fallback sem pgvector."""
        from app.embeddings.models import FinancialEntityEmbedding

        query = FinancialEntityEmbedding.query.filter(
            FinancialEntityEmbedding.embedding.isnot(None)
        )

        if entity_type != 'all':
            query = query.filter(
                FinancialEntityEmbedding.entity_type == entity_type
            )

        docs = query.all()

        scored = []
        for doc in docs:
            try:
                doc_embedding = json.loads(doc.embedding)
            except (json.JSONDecodeError, TypeError):
                continue

            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            if similarity >= min_similarity:
                scored.append((doc, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, similarity in scored[:limit]:
            results.append({
                "cnpj_raiz": doc.cnpj_raiz,
                "cnpj_completo": doc.cnpj_completo,
                "nome": doc.nome,
                "similarity": round(similarity, 4),
                "entity_type": doc.entity_type,
            })

        return results

    # ================================================================
    # BUSCA SEMANTICA — SESSION TURNS
    # ================================================================

    def search_session_turns(
        self,
        query: str,
        user_id: int,
        limit: int = 10,
        min_similarity: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca semantica em turns de sessoes passadas do usuario.

        Args:
            query: Texto de busca
            user_id: ID do usuario (filtro obrigatorio)
            limit: Maximo de resultados
            min_similarity: Score minimo (0-1)

        Returns:
            Lista de dicts com session_id, turn_index, user_content,
            assistant_summary, session_title, session_created_at, similarity
        """
        if not EMBEDDINGS_ENABLED:
            return []

        min_similarity = min_similarity or SEARCH_MIN_SIMILARITY

        query_embedding = self.embed_query(query)

        if self._is_pgvector_available():
            return self._search_pgvector_session_turns(
                query_embedding, user_id, limit, min_similarity
            )
        else:
            return self._search_fallback_session_turns(
                query_embedding, user_id, limit, min_similarity
            )

    def _search_pgvector_session_turns(
        self,
        query_embedding: List[float],
        user_id: int,
        limit: int,
        min_similarity: float,
    ) -> List[Dict[str, Any]]:
        """Busca session turns via pgvector."""
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = text("""
            SELECT
                id,
                session_id,
                turn_index,
                user_content,
                assistant_summary,
                session_title,
                session_created_at,
                1 - (CAST(embedding AS vector) <=> CAST(:query_embedding AS vector)) AS similarity
            FROM session_turn_embeddings
            WHERE user_id = :user_id
              AND embedding IS NOT NULL
            ORDER BY CAST(embedding AS vector) <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """)

        result = db.session.execute(sql, {
            "query_embedding": embedding_str,
            "user_id": user_id,
            "limit": limit * 2,
        })

        results = []
        for row in result.fetchall():
            similarity = float(row.similarity)
            if similarity >= min_similarity:
                results.append({
                    "session_id": row.session_id,
                    "turn_index": row.turn_index,
                    "user_content": row.user_content,
                    "assistant_summary": row.assistant_summary,
                    "session_title": row.session_title,
                    "session_created_at": row.session_created_at.isoformat() if row.session_created_at else None,
                    "similarity": round(similarity, 4),
                })

        return results[:limit]

    def _search_fallback_session_turns(
        self,
        query_embedding: List[float],
        user_id: int,
        limit: int,
        min_similarity: float,
    ) -> List[Dict[str, Any]]:
        """Busca session turns fallback sem pgvector."""
        from app.embeddings.models import SessionTurnEmbedding

        docs = SessionTurnEmbedding.query.filter(
            SessionTurnEmbedding.user_id == user_id,
            SessionTurnEmbedding.embedding.isnot(None),
        ).all()

        scored = []
        for doc in docs:
            try:
                doc_embedding = json.loads(doc.embedding)
            except (json.JSONDecodeError, TypeError):
                continue

            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            if similarity >= min_similarity:
                scored.append((doc, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, similarity in scored[:limit]:
            results.append({
                "session_id": doc.session_id,
                "turn_index": doc.turn_index,
                "user_content": doc.user_content,
                "assistant_summary": doc.assistant_summary,
                "session_title": doc.session_title,
                "session_created_at": doc.session_created_at.isoformat() if doc.session_created_at else None,
                "similarity": round(similarity, 4),
            })

        return results

    # ================================================================
    # BUSCA SEMANTICA — MEMORIAS DO AGENTE
    # ================================================================

    def search_memories(
        self,
        query: str,
        user_id: int,
        limit: int = 10,
        min_similarity: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca semantica em memorias persistentes do usuario.

        Args:
            query: Texto de busca
            user_id: ID do usuario (filtro obrigatorio)
            limit: Maximo de resultados
            min_similarity: Score minimo (0-1)

        Returns:
            Lista de dicts com memory_id, path, texto_embedado, similarity
        """
        if not EMBEDDINGS_ENABLED:
            return []

        min_similarity = min_similarity or SEARCH_MIN_SIMILARITY

        query_embedding = self.embed_query(query)

        if self._is_pgvector_available():
            return self._search_pgvector_memories(
                query_embedding, user_id, limit, min_similarity
            )
        else:
            return self._search_fallback_memories(
                query_embedding, user_id, limit, min_similarity
            )

    def _search_pgvector_memories(
        self,
        query_embedding: List[float],
        user_id: int,
        limit: int,
        min_similarity: float,
    ) -> List[Dict[str, Any]]:
        """Busca memorias via pgvector."""
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = text("""
            SELECT
                id,
                memory_id,
                path,
                texto_embedado,
                1 - (CAST(embedding AS vector) <=> CAST(:query_embedding AS vector)) AS similarity
            FROM agent_memory_embeddings
            WHERE user_id = :user_id
              AND embedding IS NOT NULL
            ORDER BY CAST(embedding AS vector) <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """)

        result = db.session.execute(sql, {
            "query_embedding": embedding_str,
            "user_id": user_id,
            "limit": limit * 2,
        })

        results = []
        for row in result.fetchall():
            similarity = float(row.similarity)
            if similarity >= min_similarity:
                results.append({
                    "memory_id": row.memory_id,
                    "path": row.path,
                    "texto_embedado": row.texto_embedado,
                    "similarity": round(similarity, 4),
                })

        return results[:limit]

    def _search_fallback_memories(
        self,
        query_embedding: List[float],
        user_id: int,
        limit: int,
        min_similarity: float,
    ) -> List[Dict[str, Any]]:
        """Busca memorias fallback sem pgvector."""
        from app.embeddings.models import AgentMemoryEmbedding

        docs = AgentMemoryEmbedding.query.filter(
            AgentMemoryEmbedding.user_id == user_id,
            AgentMemoryEmbedding.embedding.isnot(None),
        ).all()

        scored = []
        for doc in docs:
            try:
                doc_embedding = json.loads(doc.embedding)
            except (json.JSONDecodeError, TypeError):
                continue

            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            if similarity >= min_similarity:
                scored.append((doc, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, similarity in scored[:limit]:
            results.append({
                "memory_id": doc.memory_id,
                "path": doc.path,
                "texto_embedado": doc.texto_embedado,
                "similarity": round(similarity, 4),
            })

        return results

    # ================================================================
    # RERANKING
    # ================================================================

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = None,
        model: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Rerankeia documentos usando Voyage AI reranker.

        Args:
            query: Texto da query
            documents: Lista de textos candidatos
            top_k: Numero de resultados apos rerank
            model: Modelo de reranking

        Returns:
            Lista de dicts com index, document, relevance_score
        """
        if not documents:
            return []

        from app.embeddings.client import get_voyage_client
        vo = get_voyage_client()

        model = model or VOYAGE_RERANK_MODEL
        top_k = top_k or RERANK_TOP_K

        try:
            result = vo.rerank(
                query=query,
                documents=documents,
                model=model,
                top_k=min(top_k, len(documents)),
            )
            return [
                {
                    "index": r.index,
                    "document": r.document,
                    "relevance_score": round(r.relevance_score, 4),
                }
                for r in result.results
            ]
        except Exception as e:
            # Fallback: retornar documentos na ordem original
            print(f"[EmbeddingService] Rerank falhou, retornando ordem original: {e}")
            return [
                {"index": i, "document": d, "relevance_score": 0.0}
                for i, d in enumerate(documents[:top_k])
            ]

    def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Aplica reranking a resultados de busca semantica."""
        if len(results) <= 1:
            return results

        documents = [r["chunk_text"] for r in results]
        reranked = self.rerank(query, documents, top_k=RERANK_TOP_K)

        # Reconstroi resultados na nova ordem
        reranked_results = []
        for item in reranked:
            idx = item["index"]
            if idx < len(results):
                result = results[idx].copy()
                result["rerank_score"] = item["relevance_score"]
                reranked_results.append(result)

        return reranked_results

    # ================================================================
    # HELPERS
    # ================================================================

    def _is_pgvector_available(self) -> bool:
        """Verifica se a extensao pgvector esta disponivel no banco."""
        if self._pgvector_available is not None:
            return self._pgvector_available

        try:
            result = db.session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )
            self._pgvector_available = result.fetchone() is not None
        except Exception:
            self._pgvector_available = False

        return self._pgvector_available

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """
        Calcula cosine similarity entre dois vetores.

        Voyage AI retorna embeddings normalizados L2, entao dot product = cosine.
        Mas implementamos cosine completo por seguranca.
        """
        if len(vec_a) != len(vec_b):
            return 0.0

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estima numero de tokens (regra geral: ~4 chars/token)."""
        return max(1, len(text) // 4)
