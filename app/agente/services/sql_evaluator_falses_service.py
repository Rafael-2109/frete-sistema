"""
T7 — Service para gerenciamento de falsos positivos do Haiku evaluator.

Quando o agente identifica falso positivo (via register_improvement com
category=skill_bug + area evaluator), este service:
1. Gera embedding do par (sql, reason) via Voyage AI
2. INSERT em sql_evaluator_false_positives com status='pending_review'
3. Aguarda promocao manual para 'active' (via D8 dialogue ou admin)

Quando o SQLEvaluator vai rodar Haiku, busca via cosine_similarity > threshold
casos similares com status='active' e injeta como contra-exemplo no prompt.

Best-effort: Voyage indisponivel = no-op (degrada para comportamento atual).

Public API:
    record_false_positive(sql, reason, ...) -> int | None
    search_similar_false_positives(sql, threshold, limit) -> list[dict]
    promote_to_active(id, reviewer_user_id) -> bool
    reject_false_positive(id, reviewer_user_id, motivo) -> bool
    increment_reference(id) -> bool
"""
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =====================================================================
# CONFIG
# =====================================================================

THRESHOLD_DEFAULT = float(os.getenv("TEXT_TO_SQL_FEWSHOT_THRESHOLD", "0.80"))
LIMIT_DEFAULT = int(os.getenv("TEXT_TO_SQL_FEWSHOT_LIMIT", "2"))
ENABLE_FEWSHOT = os.getenv("TEXT_TO_SQL_AUTO_FEWSHOT", "true").lower() == "true"


def _is_enabled() -> bool:
    return ENABLE_FEWSHOT


def _content_hash(sql: str, reason: str) -> str:
    """sha256(sql + '|' + reason) — evita duplicacao do mesmo par."""
    payload = f"{(sql or '').strip()}|{(reason or '').strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _embed_sql_for_record(sql: str) -> Optional[List[float]]:
    """Gera embedding da SQL para record (input_type=document).

    NOTA: embedamos apenas a SQL (sem rejection_reason) porque na busca
    futura teremos apenas a SQL nova. Embedar par causa drift de similaridade
    (sim cai de ~0.89 para ~0.77 entre record e query).

    O rejection_reason fica armazenado em coluna separada para uso humano.
    """
    return _embed_sql(sql, input_type="document")


def _embed_sql_for_query(sql: str) -> Optional[List[float]]:
    """Gera embedding da SQL para busca (input_type=query)."""
    return _embed_sql(sql, input_type="query")


def _embed_sql(sql: str, input_type: str) -> Optional[List[float]]:
    """Helper compartilhado: embed da SQL com input_type especifico."""
    try:
        from app.embeddings.client import embed_with_retry, EmbeddingUnavailableError
        from app.embeddings.config import VOYAGE_DEFAULT_MODEL, VOYAGE_EMBEDDING_DIMENSIONS

        # Truncar SQL para evitar token explosion (raro mas possivel com CTEs grandes)
        texto = f"SQL: {(sql or '').strip()[:2000]}"
        embeddings = embed_with_retry(
            texts=[texto],
            model=VOYAGE_DEFAULT_MODEL,
            input_type=input_type,
            output_dimension=VOYAGE_EMBEDDING_DIMENSIONS,
        )
        return embeddings[0] if embeddings else None
    except EmbeddingUnavailableError as e:  # pyright: ignore[reportUnboundVariable]
        logger.warning(f"[SQL_EVAL_FALSES] Voyage bloqueada: {e}")
        return None
    except Exception as e:
        logger.debug(f"[SQL_EVAL_FALSES] Embed falhou ({input_type}): {e}")
        return None


# =====================================================================
# RECORD (chamado de register_improvement)
# =====================================================================

def record_false_positive(
    sql: str,
    reason: str,
    rejection_category: Optional[str] = None,
    improvement_key: Optional[str] = None,
    confirmed_by_user_id: Optional[int] = None,
) -> Optional[int]:
    """Registra um falso positivo confirmado pelo agente.

    Args:
        sql: SQL que foi rejeitada pelo Haiku.
        reason: Motivo da rejeicao reportado pelo Haiku.
        rejection_category: Categoria do _classify_evaluator_rejection (T6).
        improvement_key: agent_improvement_dialogue.suggestion_key (link D8).
        confirmed_by_user_id: usuario que rodou register_improvement.

    Returns:
        id do registro criado, ou None se falhou.
    """
    if not _is_enabled():
        return None
    if not sql or not reason:
        return None

    try:
        from app import db
        from sqlalchemy import text
        from app.embeddings.config import VOYAGE_DEFAULT_MODEL

        ch = _content_hash(sql, reason)

        # Dedup por content_hash
        existing = db.session.execute(
            text(
                "SELECT id, status FROM sql_evaluator_false_positives "
                "WHERE content_hash = :ch"
            ),
            {"ch": ch},
        ).fetchone()
        if existing:
            logger.info(
                f"[SQL_EVAL_FALSES] Par ja existe id={existing[0]} "
                f"status={existing[1]} — pulando insert"
            )
            return existing[0]

        # Gerar embedding APENAS da SQL (rejection_reason fica em coluna separada)
        # Razao: na busca futura so teremos a SQL nova — embedar par causa drift.
        embedding = _embed_sql_for_record(sql)
        embedding_json = json.dumps(embedding) if embedding else None

        # Texto auditavel armazenado em texto_embedado (NAO usado como chave de busca)
        texto = f"SQL: {sql.strip()[:2000]}"
        result = db.session.execute(
            text(
                """
                INSERT INTO sql_evaluator_false_positives
                    (sql_text, rejection_reason, rejection_category,
                     texto_embedado, embedding, model_used, content_hash,
                     improvement_key, status, confirmed_by_user_id,
                     confirmed_at, created_at, updated_at)
                VALUES
                    (:sql_text, :rejection_reason, :rejection_category,
                     :texto_embedado, :embedding, :model_used, :content_hash,
                     :improvement_key, 'pending_review', :confirmed_by_user_id,
                     NOW(), NOW(), NOW())
                RETURNING id
                """
            ),
            {
                "sql_text": sql.strip(),
                "rejection_reason": reason.strip(),
                "rejection_category": rejection_category,
                "texto_embedado": texto,
                "embedding": embedding_json,
                "model_used": VOYAGE_DEFAULT_MODEL,
                "content_hash": ch,
                "improvement_key": improvement_key,
                "confirmed_by_user_id": confirmed_by_user_id,
            },
        )
        row = result.fetchone()
        db.session.commit()

        new_id = row[0] if row else None
        logger.info(
            f"[SQL_EVAL_FALSES] Registrado id={new_id} status=pending_review "
            f"category={rejection_category} key={improvement_key}"
        )
        return new_id

    except Exception as e:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"[SQL_EVAL_FALSES] Falha ao registrar: {e}", exc_info=True)
        return None


# =====================================================================
# SEARCH (chamado do SQLEvaluator antes de Haiku)
# =====================================================================

def search_similar_false_positives(
    sql: str,
    threshold: float = None,
    limit: int = None,
) -> List[Dict[str, Any]]:
    """Busca falsos positivos similares a SQL atual.

    Args:
        sql: SQL gerada pelo Generator (antes do Haiku evaluator).
        threshold: cosine_similarity minima (default 0.85).
        limit: max resultados (default 2).

    Returns:
        Lista de dicts {id, sql_text, rejection_reason, rejection_category, similarity}.
        Lista vazia se feature flag off, sem matches, ou Voyage indisponivel.
    """
    if not _is_enabled() or not sql:
        return []

    threshold = threshold if threshold is not None else THRESHOLD_DEFAULT
    limit = limit if limit is not None else LIMIT_DEFAULT

    # Embed da SQL nova (input_type=query)
    query_emb = _embed_sql_for_query(sql)
    if query_emb is None:
        return []

    try:
        from app import db
        from sqlalchemy import text

        emb_str = "[" + ",".join(str(x) for x in query_emb) + "]"
        result = db.session.execute(
            text(
                """
                SELECT
                    id, sql_text, rejection_reason, rejection_category,
                    improvement_key,
                    1 - (embedding <=> CAST(:q AS vector)) AS similarity
                FROM sql_evaluator_false_positives
                WHERE status = 'active' AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:q AS vector)
                LIMIT :lim
                """
            ),
            {"q": emb_str, "lim": limit * 2},  # buscar 2x para filtrar por threshold
        )

        results = []
        for row in result.fetchall():
            sim = float(row.similarity)
            if sim >= threshold:
                results.append(
                    {
                        "id": row.id,
                        "sql_text": row.sql_text,
                        "rejection_reason": row.rejection_reason,
                        "rejection_category": row.rejection_category,
                        "improvement_key": row.improvement_key,
                        "similarity": round(sim, 4),
                    }
                )

        return results[:limit]

    except Exception as e:
        logger.debug(f"[SQL_EVAL_FALSES] Busca falhou: {e}")
        return []


def increment_reference(false_positive_id: int) -> bool:
    """Incrementa times_referenced + last_referenced_at quando injetado."""
    if not false_positive_id:
        return False
    try:
        from app import db
        from sqlalchemy import text

        db.session.execute(
            text(
                """
                UPDATE sql_evaluator_false_positives
                SET times_referenced = times_referenced + 1,
                    last_referenced_at = NOW(),
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": false_positive_id},
        )
        db.session.commit()
        return True
    except Exception as e:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        logger.debug(f"[SQL_EVAL_FALSES] Increment falhou: {e}")
        return False


# =====================================================================
# REVIEW (admin / D8 dialogue)
# =====================================================================

def promote_to_active(false_positive_id: int, reviewer_user_id: Optional[int]) -> bool:
    """Promove falso positivo de pending_review para active."""
    return _update_status(false_positive_id, "active", reviewer_user_id)


def reject_false_positive(
    false_positive_id: int, reviewer_user_id: Optional[int]
) -> bool:
    """Marca como rejected (revisor descartou — nao injeta mais)."""
    return _update_status(false_positive_id, "rejected", reviewer_user_id)


def _update_status(
    false_positive_id: int, new_status: str, reviewer_user_id: Optional[int]
) -> bool:
    if new_status not in ("active", "rejected", "pending_review"):
        return False
    try:
        from app import db
        from sqlalchemy import text

        result = db.session.execute(
            text(
                """
                UPDATE sql_evaluator_false_positives
                SET status = :status,
                    reviewed_by_user_id = :reviewer,
                    reviewed_at = NOW(),
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {
                "status": new_status,
                "reviewer": reviewer_user_id,
                "id": false_positive_id,
            },
        )
        db.session.commit()
        affected = result.rowcount or 0
        if affected > 0:
            logger.info(
                f"[SQL_EVAL_FALSES] id={false_positive_id} → {new_status} "
                f"by user_id={reviewer_user_id}"
            )
            return True
        return False
    except Exception as e:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"[SQL_EVAL_FALSES] update_status falhou: {e}")
        return False


# =====================================================================
# STATS (observabilidade)
# =====================================================================

def get_stats() -> Dict[str, Any]:
    """Retorna metricas da tabela para dashboards admin."""
    try:
        from app import db
        from sqlalchemy import text

        rows = db.session.execute(
            text(
                """
                SELECT status, COUNT(*) AS cnt, SUM(times_referenced) AS refs
                FROM sql_evaluator_false_positives
                GROUP BY status
                """
            )
        ).fetchall()
        return {
            row.status: {"count": row.cnt, "references_total": int(row.refs or 0)}
            for row in rows
        }
    except Exception as e:
        logger.debug(f"[SQL_EVAL_FALSES] stats falhou: {e}")
        return {}
