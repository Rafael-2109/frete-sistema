"""Indexer do CATALOGO DE TABELAS para busca semantica por intencao (S1).

Le o catalog.json (gerado por generate_schemas.py) e gera 1 embedding por
tabela (nome + dominio + descricao + campos-chave). Alimenta a tool
buscar_tabelas (camada semantica), FUNDIDA com a busca textual deterministica.

Freshness (decisao 1a do plano S1): reindexado no scheduler diario
(reindexacao_embeddings.py, 11o modulo). content_hash detecta mudanca de
descricao/key_fields/dominio -> so re-embeda o que mudou. A busca TEXTUAL ja
cobre tabelas novas na hora (le o catalog.json fresco), entao a janela de
staleness do indice semantico (<=24h) nao deixa tabela invisivel.

Chave de upsert: table_name (1 linha por tabela). Ver MASTER text-to-sql S1.

Executar standalone:
    source .venv/bin/activate
    python -m app.embeddings.indexers.table_catalog_indexer [--dry-run] [--reindex] [--stats]
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List

from sqlalchemy import text

logger = logging.getLogger(__name__)

# catalog.json fica em .claude/skills/consultando-sql/schemas/ (committed, vai no deploy).
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..')
)
_CATALOG_PATH = os.path.join(
    _PROJECT_ROOT, '.claude', 'skills', 'consultando-sql', 'schemas', 'catalog.json'
)


def _content_hash(text_str: str) -> str:
    """MD5 do texto embedado para detectar mudanca (descricao/key_fields/dominio)."""
    return hashlib.md5(text_str.strip().lower().encode('utf-8')).hexdigest()


def _build_texto_embedado(name: str, dominio: str, descricao: str, key_fields_csv: str) -> str:
    """Texto canonico que vai para o embedding de uma tabela.

    Inclui dominio e campos-chave porque melhoram MUITO o recall de intencao
    vaga (pre-mortem 1 do plano S1). Determinístico (mesma tabela -> mesmo texto
    -> mesmo hash)."""
    return (
        f"Tabela: {name}\n"
        f"Dominio: {dominio}\n"
        f"Descricao: {descricao}\n"
        f"Campos-chave: {key_fields_csv}"
    )


def collect_table_catalog(catalog_path: str = None) -> List[Dict[str, Any]]:
    """Le o catalog.json e monta os registros a indexar (tabelas + admin).

    Indexa tanto `tabelas` (consultaveis por todos) quanto `tabelas_admin`
    (visiveis so para admin) — a VISIBILIDADE por usuario e aplicada na busca
    (tool buscar_tabelas), nao aqui.
    """
    path = catalog_path or _CATALOG_PATH
    with open(path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    entries = list(catalog.get('tabelas', [])) + list(catalog.get('tabelas_admin', []))
    results = []
    for e in entries:
        name = e.get('name', '')
        if not name:
            continue
        dominio = e.get('dominio', '') or ''
        descricao = e.get('description', '') or ''
        kf_csv = ', '.join(e.get('key_fields', []) or [])
        texto = _build_texto_embedado(name, dominio, descricao, kf_csv)
        results.append({
            'table_name': name,
            'dominio': dominio,
            'descricao': descricao,
            'key_fields': kf_csv,
            'texto_embedado': texto,
            'content_hash': _content_hash(texto),
        })
    return results


def index_table_catalog(
    entries: List[Dict[str, Any]],
    reindex: bool = False,
) -> Dict[str, Any]:
    """Gera embeddings e faz upsert por table_name.

    Idempotente: pula tabelas cujo content_hash nao mudou (a menos de reindex).

    Returns:
        Estatisticas: {embedded, skipped, errors, total_tokens_est}
    """
    from app import db as _db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_TABLE_CATALOG_MODEL

    modelo = VOYAGE_TABLE_CATALOG_MODEL
    svc = EmbeddingService()
    stats = {"embedded": 0, "skipped": 0, "errors": 0, "total_tokens_est": 0}

    if not entries:
        return stats

    # Hashes existentes (so re-embeda o que mudou) — chave = table_name.
    # Filtra por model_used = modelo atual: ao TROCAR de modelo, as linhas com o
    # modelo antigo nao contam como existentes -> sao re-embedadas (espacos
    # vetoriais de modelos diferentes sao incompativeis).
    existing = {}
    if not reindex:
        result = _db.session.execute(
            text(
                "SELECT table_name, content_hash FROM table_catalog_embeddings "
                "WHERE embedding IS NOT NULL AND model_used = :modelo"
            ),
            {"modelo": modelo}
        )
        existing = {row[0]: row[1] for row in result.fetchall()}

    to_embed = []
    for e in entries:
        if not reindex and existing.get(e["table_name"]) == e["content_hash"]:
            stats["skipped"] += 1
            continue
        to_embed.append(e)

    if not to_embed:
        logger.info(f"[TABLE_CATALOG_INDEXER] Nada novo (skipped={stats['skipped']})")
        return stats

    batch_size = 128
    for i in range(0, len(to_embed), batch_size):
        batch = to_embed[i:i + batch_size]
        texts = [e["texto_embedado"] for e in batch]

        try:
            embeddings = svc.embed_texts(texts, input_type="document", model=modelo)
        except Exception as e:
            logger.error(f"[TABLE_CATALOG_INDEXER] Erro batch {i}: {e}")
            stats["errors"] += len(batch)
            continue

        for entry, embedding in zip(batch, embeddings):
            try:
                embedding_json = json.dumps(embedding)
                stats["total_tokens_est"] += max(1, len(entry["texto_embedado"]) // 4)

                _db.session.execute(
                    text("""
                        INSERT INTO table_catalog_embeddings
                            (table_name, dominio, descricao, key_fields,
                             texto_embedado, embedding, model_used, content_hash,
                             created_at, updated_at)
                        VALUES
                            (:table_name, :dominio, :descricao, :key_fields,
                             :texto_embedado, :embedding, :model_used, :content_hash,
                             NOW(), NOW())
                        ON CONFLICT (table_name)
                        DO UPDATE SET
                            dominio = EXCLUDED.dominio,
                            descricao = EXCLUDED.descricao,
                            key_fields = EXCLUDED.key_fields,
                            texto_embedado = EXCLUDED.texto_embedado,
                            embedding = EXCLUDED.embedding,
                            model_used = EXCLUDED.model_used,
                            content_hash = EXCLUDED.content_hash,
                            updated_at = NOW()
                    """),
                    {
                        "table_name": entry["table_name"],
                        "dominio": entry["dominio"],
                        "descricao": entry["descricao"],
                        "key_fields": entry["key_fields"],
                        "texto_embedado": entry["texto_embedado"],
                        "embedding": embedding_json,
                        "model_used": modelo,
                        "content_hash": entry["content_hash"],
                    }
                )
                stats["embedded"] += 1
            except Exception as e:
                logger.error(f"[TABLE_CATALOG_INDEXER] Erro salvando {entry.get('table_name')}: {e}")
                stats["errors"] += 1

        _db.session.commit()
        if i + batch_size < len(to_embed):
            time.sleep(0.5)

    logger.info(f"[TABLE_CATALOG_INDEXER] Concluido: {stats}")
    return stats


# =====================================================================
# CLI
# =====================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description='Indexer do catalogo de tabelas (S1)')
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
                SELECT COUNT(*) AS total, COUNT(embedding) AS com_embedding,
                       MAX(updated_at) AS ultima
                FROM table_catalog_embeddings
            """)).fetchone()
            print("\n=== Table Catalog Embeddings ===")
            if result:
                print(f"Total: {result[0]} | Com embedding: {result[1]} | Ultima: {result[2]}")
            else:
                print("Tabela vazia ou nao encontrada")
            return

        entries = collect_table_catalog()
        print(f"Tabelas no catalogo: {len(entries)}")

        if args.dry_run:
            total_chars = sum(len(e["texto_embedado"]) for e in entries)
            tokens_est = total_chars // 4
            cost_est = tokens_est * 0.02 / 1_000_000
            print("\n[DRY-RUN]")
            print(f"Tabelas a indexar: {len(entries)}")
            print(f"Tokens estimados: {tokens_est:,} | Custo est: ${cost_est:.6f}")
            for e in entries[:5]:
                print(f"  - {e['table_name']} [{e['dominio']}]")
            if len(entries) > 5:
                print(f"  ... +{len(entries) - 5} tabelas")
            return

        stats = index_table_catalog(entries, reindex=args.reindex)
        print(f"\n=== Resultado ===")
        print(f"Embedded: {stats['embedded']} | Skipped: {stats['skipped']} | "
              f"Errors: {stats['errors']} | Tokens est: {stats['total_tokens_est']:,}")


if __name__ == '__main__':
    main()
