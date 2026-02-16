#!/usr/bin/env python3
"""
Indexador de produtos para busca semantica.

Le produtos de cadastro_palletizacao (ativo=True, produto_vendido=True),
gera embeddings via Voyage AI e armazena em product_embeddings.

Uso:
    source .venv/bin/activate
    python -m app.embeddings.indexers.product_indexer              # Indexar
    python -m app.embeddings.indexers.product_indexer --dry-run     # Preview
    python -m app.embeddings.indexers.product_indexer --reindex     # Re-indexar tudo
    python -m app.embeddings.indexers.product_indexer --stats       # Estatisticas

Custo estimado: ~$0.001 (546 produtos x ~100 tokens x $0.02/1M tokens)
"""

import argparse
import json
import sys
import os
import time
from typing import List, Dict, Tuple

# Setup path para imports do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


def build_embedding_text(produto: dict) -> str:
    """
    Constroi texto para embedding a partir dos campos do produto.

    Formato: "{nome_produto} | {tipo_materia_prima} | {tipo_embalagem} | {categoria_produto} | {subcategoria}"
    Campos None/vazios sao omitidos.

    Args:
        produto: Dict com campos do cadastro_palletizacao

    Returns:
        Texto concatenado para gerar embedding
    """
    parts = [produto.get('nome_produto', '')]

    for campo in ('tipo_materia_prima', 'tipo_embalagem', 'categoria_produto', 'subcategoria'):
        valor = produto.get(campo)
        if valor and str(valor).strip():
            parts.append(str(valor).strip())

    return ' | '.join(parts)


def collect_products() -> Tuple[List[Dict], int]:
    """
    Coleta todos os produtos vendidos ativos do cadastro_palletizacao.

    Returns:
        Tupla (lista_de_produtos, total)
    """
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        result = db.session.execute(text("""
            SELECT cod_produto, nome_produto, tipo_materia_prima,
                   tipo_embalagem, categoria_produto, subcategoria,
                   peso_bruto, palletizacao
            FROM cadastro_palletizacao
            WHERE ativo = true AND produto_vendido = true
            ORDER BY nome_produto
        """))

        rows = result.fetchall()
        produtos = []
        for row in rows:
            prod = {
                'cod_produto': row[0],
                'nome_produto': row[1],
                'tipo_materia_prima': row[2],
                'tipo_embalagem': row[3],
                'categoria_produto': row[4],
                'subcategoria': row[5],
                'peso_bruto': float(row[6]) if row[6] else 0,
                'palletizacao': float(row[7]) if row[7] else 0,
            }
            prod['texto_embedado'] = build_embedding_text(prod)
            produtos.append(prod)

        return produtos, len(produtos)


def index_products(produtos: List[Dict], reindex: bool = False) -> Dict:
    """
    Gera embeddings e salva no banco.

    Args:
        produtos: Lista de produtos do collect_products()
        reindex: Se True, apaga embeddings existentes primeiro

    Returns:
        Dict com estatisticas
    """
    from app import create_app, db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_DEFAULT_MODEL
    from sqlalchemy import text

    app = create_app()
    stats = {
        "total_produtos": len(produtos),
        "embedded": 0,
        "skipped": 0,
        "errors": 0,
        "total_tokens_est": 0,
    }

    with app.app_context():
        svc = EmbeddingService()

        if reindex:
            print("[INFO] Removendo embeddings existentes...")
            db.session.execute(text("DELETE FROM product_embeddings"))
            db.session.commit()

        # Verificar quais produtos ja existem
        existing = set()
        if not reindex:
            result = db.session.execute(text(
                "SELECT cod_produto FROM product_embeddings"
            ))
            existing = {row[0] for row in result.fetchall()}
            print(f"[INFO] {len(existing)} produtos ja existem no banco")

        # Filtrar produtos novos
        new_products = [p for p in produtos if p['cod_produto'] not in existing]

        if not new_products:
            print("[INFO] Nenhum produto novo para indexar")
            stats["skipped"] = len(produtos)
            return stats

        stats["skipped"] = len(produtos) - len(new_products)
        print(f"[INFO] {len(new_products)} produtos novos para indexar")

        # Gerar embeddings em batches
        batch_size = 128
        for i in range(0, len(new_products), batch_size):
            batch = new_products[i:i + batch_size]
            texts = [p['texto_embedado'] for p in batch]

            print(f"  Batch {i // batch_size + 1}/{(len(new_products) - 1) // batch_size + 1} "
                  f"({len(batch)} produtos)...", end=" ")

            try:
                embeddings = svc.embed_texts(texts, input_type="document")

                # Salvar no banco
                for prod, embedding in zip(batch, embeddings):
                    embedding_str = json.dumps(embedding)
                    char_count = len(prod['texto_embedado'])
                    token_est = max(1, char_count // 4)
                    stats["total_tokens_est"] += token_est

                    db.session.execute(text("""
                        INSERT INTO product_embeddings
                            (cod_produto, nome_produto, tipo_materia_prima,
                             texto_embedado, embedding, model_used)
                        VALUES
                            (:cod_produto, :nome_produto, :tipo_materia_prima,
                             :texto_embedado, :embedding, :model_used)
                        ON CONFLICT (cod_produto)
                        DO UPDATE SET
                            nome_produto = EXCLUDED.nome_produto,
                            tipo_materia_prima = EXCLUDED.tipo_materia_prima,
                            texto_embedado = EXCLUDED.texto_embedado,
                            embedding = EXCLUDED.embedding,
                            model_used = EXCLUDED.model_used,
                            updated_at = NOW()
                    """), {
                        "cod_produto": prod['cod_produto'],
                        "nome_produto": prod['nome_produto'],
                        "tipo_materia_prima": prod.get('tipo_materia_prima'),
                        "texto_embedado": prod['texto_embedado'],
                        "embedding": embedding_str,
                        "model_used": VOYAGE_DEFAULT_MODEL,
                    })

                db.session.commit()
                stats["embedded"] += len(batch)
                print(f"OK ({len(batch)} embeddings salvos)")

            except Exception as e:
                print(f"ERRO: {e}")
                db.session.rollback()
                stats["errors"] += len(batch)

            # Rate limiting gentil
            if i + batch_size < len(new_products):
                time.sleep(0.5)

    return stats


def show_stats():
    """Mostra estatisticas de product_embeddings."""
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("ESTATISTICAS DE EMBEDDINGS — PRODUTOS")
        print("=" * 60)

        with db.engine.connect() as conn:
            # Total de registros
            total = conn.execute(text(
                "SELECT COUNT(*) FROM product_embeddings"
            )).scalar()
            with_emb = conn.execute(text(
                "SELECT COUNT(*) FROM product_embeddings WHERE embedding IS NOT NULL"
            )).scalar()

            print(f"\nTotal de produtos: {total}")
            print(f"Com embedding: {with_emb}")
            print(f"Sem embedding: {total - with_emb}")

            # Por tipo materia prima
            print("\nPor tipo_materia_prima:")
            result = conn.execute(text("""
                SELECT
                    COALESCE(tipo_materia_prima, '(sem tipo)') as tipo,
                    COUNT(*) as total
                FROM product_embeddings
                GROUP BY tipo_materia_prima
                ORDER BY total DESC
            """))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} produtos")

            # Modelo
            print("\nModelos:")
            result = conn.execute(text("""
                SELECT model_used, COUNT(*)
                FROM product_embeddings
                WHERE model_used IS NOT NULL
                GROUP BY model_used
            """))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} produtos")


def main():
    parser = argparse.ArgumentParser(description='Indexar produtos para busca semantica')
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas mostra produtos sem gerar embeddings')
    parser.add_argument('--reindex', action='store_true',
                        help='Apaga embeddings existentes e reindexa tudo')
    parser.add_argument('--stats', action='store_true',
                        help='Mostra estatisticas')

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    print("=" * 60)
    print("INDEXADOR DE PRODUTOS — Busca Semantica via Voyage AI")
    print("=" * 60)

    # Coletar produtos
    print(f"\n[1/2] Coletando produtos vendidos ativos...")
    produtos, total = collect_products()

    total_chars = sum(len(p['texto_embedado']) for p in produtos)
    total_tokens_est = sum(max(1, len(p['texto_embedado']) // 4) for p in produtos)

    print(f"   Produtos: {total}")
    print(f"   Total chars: {total_chars:,}")
    print(f"   Total tokens (est): {total_tokens_est:,}")
    print(f"   Custo estimado: ${total_tokens_est * 0.02 / 1_000_000:.4f}")

    if args.dry_run:
        print("\n[DRY RUN] Top 10 maiores textos:")
        sorted_prods = sorted(produtos, key=lambda p: len(p['texto_embedado']), reverse=True)
        for i, p in enumerate(sorted_prods[:10]):
            print(f"   {i + 1}. [{p['cod_produto']}] {p['texto_embedado'][:80]} — {len(p['texto_embedado'])} chars")

        print(f"\nPor tipo_materia_prima:")
        from collections import Counter
        tipos = Counter(p.get('tipo_materia_prima', '(sem tipo)') for p in produtos)
        for tipo, count in tipos.most_common():
            print(f"   {tipo}: {count} produtos")
        return

    # Indexar
    print(f"\n[2/2] Gerando embeddings e salvando no banco...")
    start = time.time()
    stats = index_products(produtos, reindex=args.reindex)
    elapsed = time.time() - start

    print(f"\n" + "=" * 60)
    print("RESULTADO")
    print("=" * 60)
    print(f"Tempo: {elapsed:.1f}s")
    print(f"Embeddings gerados: {stats['embedded']}")
    print(f"Skipped (ja existiam): {stats['skipped']}")
    print(f"Erros: {stats['errors']}")
    print(f"Tokens estimados: {stats['total_tokens_est']:,}")
    print(f"Custo estimado: ${stats['total_tokens_est'] * 0.02 / 1_000_000:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
