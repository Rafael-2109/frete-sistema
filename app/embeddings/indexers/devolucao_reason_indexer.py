"""
Indexer de motivos de devolucao para classificacao por similaridade.

Coleta devolucoes ja classificadas (motivo != NULL, descricao_motivo != NULL)
e gera embeddings para busca semantica posterior.

Fonte: nf_devolucao (motivo + descricao_motivo + observacoes_logistica)

Executar:
    source .venv/bin/activate
    python -m app.embeddings.indexers.devolucao_reason_indexer [--dry-run] [--reindex] [--stats]
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List

from sqlalchemy import text

logger = logging.getLogger(__name__)


def _has_app_context() -> bool:
    """Verifica se esta dentro de um Flask app_context."""
    try:
        from flask import current_app
        _ = current_app.name
        return True
    except (RuntimeError, ImportError):
        return False


def _content_hash(text_str: str) -> str:
    """Gera MD5 do texto para dedup."""
    return hashlib.md5(text_str.strip().lower().encode('utf-8')).hexdigest()


# =====================================================================
# COLETA
# =====================================================================

def collect_devolucao_reasons() -> List[Dict[str, Any]]:
    """
    Coleta devolucoes ja classificadas do banco.

    Busca nf_devolucao com motivo classificado e descricao nao vazia.
    Combina descricao_motivo + observacoes_logistica para texto rico.

    Returns:
        Lista de dicts com nf_devolucao_id, descricao_text, motivo_classificado,
        texto_embedado, content_hash
    """
    from app import db as _db

    result = _db.session.execute(text("""
        SELECT
            nd.id,
            nd.motivo,
            nd.descricao_motivo,
            nd.observacoes_logistica
        FROM nf_devolucao nd
        WHERE nd.motivo IS NOT NULL
            AND nd.motivo != ''
            AND (nd.descricao_motivo IS NOT NULL AND nd.descricao_motivo != ''
                 OR nd.observacoes_logistica IS NOT NULL AND nd.observacoes_logistica != '')
        ORDER BY nd.id
    """))

    reasons = []
    for row in result.fetchall():
        nf_id, motivo, descricao, observacoes = row

        # Combinar textos disponiveis
        parts = []
        if descricao and descricao.strip():
            parts.append(descricao.strip())
        if observacoes and observacoes.strip():
            parts.append(observacoes.strip())

        descricao_text = " | ".join(parts)
        if not descricao_text or len(descricao_text) < 5:
            continue

        texto = f"Motivo: {motivo}\nDescricao: {descricao_text}"

        reasons.append({
            "nf_devolucao_id": nf_id,
            "descricao_text": descricao_text,
            "motivo_classificado": motivo,
            "texto_embedado": texto,
            "content_hash": _content_hash(texto),
        })

    return reasons


# =====================================================================
# INDEXACAO
# =====================================================================

def index_devolucao_reasons(
    reasons: List[Dict[str, Any]],
    reindex: bool = False,
) -> Dict[str, Any]:
    """
    Gera embeddings e salva motivos de devolucao.

    Args:
        reasons: Lista de motivos para indexar
        reindex: Se True, re-embeda todos

    Returns:
        Estatisticas
    """
    from app import db as _db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_DEFAULT_MODEL

    svc = EmbeddingService()
    stats = {"embedded": 0, "skipped": 0, "errors": 0, "total_tokens_est": 0}

    if not reasons:
        return stats

    # Verificar existentes
    existing_hashes = set()
    if not reindex:
        result = _db.session.execute(
            text("SELECT content_hash FROM devolucao_reason_embeddings WHERE embedding IS NOT NULL")
        )
        existing_hashes = {row[0] for row in result.fetchall()}

    # Filtrar novos
    to_embed = []
    for r in reasons:
        if not reindex and r.get("content_hash") in existing_hashes:
            stats["skipped"] += 1
            continue
        to_embed.append(r)

    if not to_embed:
        logger.info(f"[DEVOLUCAO_INDEXER] Nada novo (skipped={stats['skipped']})")
        return stats

    # Batch embedding
    batch_size = 128
    for i in range(0, len(to_embed), batch_size):
        batch = to_embed[i:i + batch_size]
        texts = [r["texto_embedado"] for r in batch]

        try:
            embeddings = svc.embed_texts(texts, input_type="document")
        except Exception as e:
            logger.error(f"[DEVOLUCAO_INDEXER] Erro batch {i}: {e}")
            stats["errors"] += len(batch)
            continue

        for reason, embedding in zip(batch, embeddings):
            try:
                embedding_json = json.dumps(embedding)
                tokens_est = max(1, len(reason["texto_embedado"]) // 4)
                stats["total_tokens_est"] += tokens_est

                # Upsert por content_hash — se motivo reclassificado, atualiza embedding
                _db.session.execute(
                    text("""
                        INSERT INTO devolucao_reason_embeddings
                            (nf_devolucao_linha_id, descricao_text, motivo_classificado,
                             texto_embedado, embedding, model_used, content_hash,
                             created_at, updated_at)
                        VALUES
                            (:nf_devolucao_id, :descricao_text, :motivo_classificado,
                             :texto_embedado, :embedding, :model_used, :content_hash,
                             NOW(), NOW())
                        ON CONFLICT (content_hash) WHERE content_hash IS NOT NULL
                        DO UPDATE SET
                            motivo_classificado = EXCLUDED.motivo_classificado,
                            descricao_text = EXCLUDED.descricao_text,
                            texto_embedado = EXCLUDED.texto_embedado,
                            embedding = EXCLUDED.embedding,
                            model_used = EXCLUDED.model_used,
                            updated_at = NOW()
                    """),
                    {
                        "nf_devolucao_id": reason.get("nf_devolucao_id"),
                        "descricao_text": reason["descricao_text"],
                        "motivo_classificado": reason["motivo_classificado"],
                        "texto_embedado": reason["texto_embedado"],
                        "embedding": embedding_json,
                        "model_used": VOYAGE_DEFAULT_MODEL,
                        "content_hash": reason["content_hash"],
                    }
                )
                stats["embedded"] += 1

            except Exception as e:
                logger.error(f"[DEVOLUCAO_INDEXER] Erro salvando: {e}")
                stats["errors"] += 1

        _db.session.commit()
        if i + batch_size < len(to_embed):
            time.sleep(0.5)

    logger.info(f"[DEVOLUCAO_INDEXER] Concluido: {stats}")
    return stats


# =====================================================================
# CLI
# =====================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Indexer de motivos de devolucao')
    parser.add_argument('--dry-run', action='store_true', help='Simula sem salvar')
    parser.add_argument('--reindex', action='store_true', help='Re-embeda todos')
    parser.add_argument('--stats', action='store_true', help='Mostra estatisticas')

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    from app import create_app, db as _db
    app = create_app()

    with app.app_context():
        if args.stats:
            result = _db.session.execute(text("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(embedding) AS com_embedding,
                    COUNT(DISTINCT motivo_classificado) AS categorias
                FROM devolucao_reason_embeddings
            """)).fetchone()
            print(f"\n=== Devolucao Reason Embeddings ===")
            print(f"Total: {result[0]}")
            print(f"Com embedding: {result[1]}")
            print(f"Categorias distintas: {result[2]}")

            # Distribuicao por motivo
            dist = _db.session.execute(text("""
                SELECT motivo_classificado, COUNT(*)
                FROM devolucao_reason_embeddings
                GROUP BY motivo_classificado
                ORDER BY COUNT(*) DESC
            """)).fetchall()
            if dist:
                print("\nDistribuicao:")
                for motivo, count in dist:
                    print(f"  {motivo}: {count}")
            return

        reasons = collect_devolucao_reasons()
        print(f"Devolucoes com motivo classificado: {len(reasons)}")

        if args.dry_run:
            total_chars = sum(len(r["texto_embedado"]) for r in reasons)
            tokens_est = total_chars // 4
            cost_est = tokens_est * 0.02 / 1_000_000
            print(f"\n[DRY-RUN]")
            print(f"Motivos a indexar: {len(reasons)}")
            print(f"Tokens estimados: {tokens_est:,}")
            print(f"Custo estimado: ${cost_est:.6f}")

            # Preview por categoria
            from collections import Counter
            dist = Counter(r["motivo_classificado"] for r in reasons)
            print("\nDistribuicao:")
            for motivo, count in dist.most_common():
                print(f"  {motivo}: {count}")
            return

        stats = index_devolucao_reasons(reasons, reindex=args.reindex)
        print(f"\nEmbedded: {stats['embedded']} | Skipped: {stats['skipped']} | Errors: {stats['errors']}")


if __name__ == '__main__':
    main()
