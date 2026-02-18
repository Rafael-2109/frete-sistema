"""
Indexer de transportadoras para matching semantico.

Coleta transportadoras da tabela `transportadoras` (fonte canonica)
e gera embeddings dos nomes + aliases para resolucao semantica.

Aliases sao coletados de:
- entregas_monitoradas.transportadora (nomes informais)

Executar:
    source .venv/bin/activate
    python -m app.embeddings.indexers.carrier_indexer [--dry-run] [--reindex] [--stats]
"""

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


def _normalize_name(name: str) -> str:
    """Normaliza nome de transportadora para comparacao."""
    import unicodedata
    name = name.upper().strip()
    # Remover acentos
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    # Remover sufixos legais
    for suffix in ['LTDA', 'EIRELI', 'S.A.', 'S/A', 'ME', 'EPP', 'SA']:
        name = name.replace(suffix, '')
    return name.strip()


# =====================================================================
# COLETA
# =====================================================================

def collect_carriers() -> List[Dict[str, Any]]:
    """
    Coleta transportadoras do banco com aliases.

    Fonte canonica: tabela `transportadoras`
    Aliases: nomes distintos em `entregas_monitoradas`

    Returns:
        Lista de dicts com carrier_name, cnpj, aliases, texto_embedado
    """
    from app import db as _db

    # 1. Transportadoras canonicas
    result = _db.session.execute(text("""
        SELECT id, cnpj, razao_social, ativo
        FROM transportadoras
        WHERE razao_social IS NOT NULL AND razao_social != ''
        ORDER BY id
    """))

    carriers = {}
    for row in result.fetchall():
        t_id, cnpj, razao_social, ativo = row
        name = razao_social.strip().upper()
        normalized = _normalize_name(name)

        if normalized in carriers:
            # Merge — mesma transportadora com nome diferente
            existing = carriers[normalized]
            if name not in existing["aliases_set"]:
                existing["aliases_set"].add(name)
        else:
            carriers[normalized] = {
                "carrier_name": name,
                "cnpj": cnpj,
                "aliases_set": {name},
                "t_id": t_id,
            }

    # 2. Coletar aliases de entregas_monitoradas
    aliases_result2 = _db.session.execute(text("""
        SELECT DISTINCT transportadora
        FROM entregas_monitoradas
        WHERE transportadora IS NOT NULL AND transportadora != ''
        LIMIT 2000
    """))

    for row in aliases_result2.fetchall():
        alias = row[0].strip().upper()
        if not alias or len(alias) < 3:
            continue

        normalized = _normalize_name(alias)

        for key, carrier in carriers.items():
            if key in normalized or normalized in key:
                carrier["aliases_set"].add(alias)
                break

    # 3. Montar resultado final
    results = []
    for key, carrier in carriers.items():
        aliases = sorted(carrier["aliases_set"])
        aliases_json = json.dumps(aliases, ensure_ascii=False)

        texto = f"Transportadora: {carrier['carrier_name']}"
        if carrier["cnpj"]:
            texto += f"\nCNPJ: {carrier['cnpj']}"
        if len(aliases) > 1:
            texto += f"\nNomes conhecidos: {', '.join(aliases)}"

        results.append({
            "carrier_name": carrier["carrier_name"],
            "cnpj": carrier["cnpj"],
            "aliases": aliases_json,
            "texto_embedado": texto,
        })

    return results


# =====================================================================
# INDEXACAO
# =====================================================================

def index_carriers(
    carriers: List[Dict[str, Any]],
    reindex: bool = False,
) -> Dict[str, Any]:
    """
    Gera embeddings e salva transportadoras.

    Args:
        carriers: Lista de transportadoras para indexar
        reindex: Se True, re-embeda todas

    Returns:
        Estatisticas
    """
    from app import db as _db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_DEFAULT_MODEL

    svc = EmbeddingService()
    stats = {"embedded": 0, "skipped": 0, "errors": 0, "total_tokens_est": 0}

    if not carriers:
        return stats

    # Verificar existentes
    existing_names = set()
    if not reindex:
        result = _db.session.execute(
            text("SELECT carrier_name FROM carrier_embeddings WHERE embedding IS NOT NULL")
        )
        existing_names = {row[0] for row in result.fetchall()}

    # Filtrar
    to_embed = []
    for c in carriers:
        if not reindex and c["carrier_name"] in existing_names:
            stats["skipped"] += 1
            continue
        to_embed.append(c)

    if not to_embed:
        logger.info(f"[CARRIER_INDEXER] Nada novo (skipped={stats['skipped']})")
        return stats

    # Batch embedding
    batch_size = 128
    for i in range(0, len(to_embed), batch_size):
        batch = to_embed[i:i + batch_size]
        texts = [c["texto_embedado"] for c in batch]

        try:
            embeddings = svc.embed_texts(texts, input_type="document")
        except Exception as e:
            logger.error(f"[CARRIER_INDEXER] Erro batch {i}: {e}")
            stats["errors"] += len(batch)
            continue

        for carrier, embedding in zip(batch, embeddings):
            try:
                embedding_json = json.dumps(embedding)
                tokens_est = max(1, len(carrier["texto_embedado"]) // 4)
                stats["total_tokens_est"] += tokens_est

                _db.session.execute(
                    text("""
                        INSERT INTO carrier_embeddings
                            (carrier_name, cnpj, aliases,
                             texto_embedado, embedding, model_used,
                             created_at, updated_at)
                        VALUES
                            (:carrier_name, :cnpj, :aliases,
                             :texto_embedado, :embedding, :model_used,
                             NOW(), NOW())
                        ON CONFLICT ON CONSTRAINT uq_carrier_name
                        DO UPDATE SET
                            cnpj = EXCLUDED.cnpj,
                            aliases = EXCLUDED.aliases,
                            texto_embedado = EXCLUDED.texto_embedado,
                            embedding = EXCLUDED.embedding,
                            model_used = EXCLUDED.model_used,
                            updated_at = NOW()
                    """),
                    {
                        "carrier_name": carrier["carrier_name"],
                        "cnpj": carrier["cnpj"],
                        "aliases": carrier["aliases"],
                        "texto_embedado": carrier["texto_embedado"],
                        "embedding": embedding_json,
                        "model_used": VOYAGE_DEFAULT_MODEL,
                    }
                )
                stats["embedded"] += 1

            except Exception as e:
                logger.error(f"[CARRIER_INDEXER] Erro salvando {carrier['carrier_name']}: {e}")
                stats["errors"] += 1

        _db.session.commit()
        if i + batch_size < len(to_embed):
            time.sleep(0.5)

    logger.info(f"[CARRIER_INDEXER] Concluido: {stats}")
    return stats


# =====================================================================
# CLI
# =====================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Indexer de transportadoras')
    parser.add_argument('--dry-run', action='store_true', help='Simula sem salvar')
    parser.add_argument('--reindex', action='store_true', help='Re-embeda todas')
    parser.add_argument('--stats', action='store_true', help='Mostra estatisticas')

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    from app import create_app, db as _db
    app = create_app()

    with app.app_context():
        if args.stats:
            result = _db.session.execute(text("""
                SELECT COUNT(*), COUNT(embedding), COUNT(cnpj)
                FROM carrier_embeddings
            """)).fetchone()
            print(f"\n=== Carrier Embeddings ===")
            print(f"Total: {result[0]}")
            print(f"Com embedding: {result[1]}")
            print(f"Com CNPJ: {result[2]}")
            return

        carriers = collect_carriers()
        print(f"Transportadoras: {len(carriers)}")

        if args.dry_run:
            total_chars = sum(len(c["texto_embedado"]) for c in carriers)
            tokens_est = total_chars // 4
            cost_est = tokens_est * 0.02 / 1_000_000
            print(f"\n[DRY-RUN]")
            print(f"Transportadoras a indexar: {len(carriers)}")
            print(f"Tokens estimados: {tokens_est:,}")
            print(f"Custo estimado: ${cost_est:.6f}")
            for c in carriers[:10]:
                aliases = json.loads(c["aliases"])
                print(f"  - {c['carrier_name']} (aliases: {len(aliases)})")
            if len(carriers) > 10:
                print(f"  ... +{len(carriers) - 10} transportadoras")
            return

        stats = index_carriers(carriers, reindex=args.reindex)
        print(f"\nEmbedded: {stats['embedded']} | Skipped: {stats['skipped']} | Errors: {stats['errors']}")


if __name__ == '__main__':
    main()
