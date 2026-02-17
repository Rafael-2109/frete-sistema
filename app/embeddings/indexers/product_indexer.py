#!/usr/bin/env python3
"""
Indexador de produtos para busca semantica.

Le produtos de cadastro_palletizacao (ativo=True, produto_vendido=True),
enriquece com aliases das tabelas de_para (depara_produto_cliente,
portal_atacadao_produto_depara, portal_sendas_produto_depara),
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
import hashlib
import json
import sys
import os
import time
from typing import List, Dict, Tuple, Optional

# Setup path para imports do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


def _has_app_context() -> bool:
    """Verifica se ja estamos dentro de um Flask app context."""
    try:
        from flask import current_app
        _ = current_app.name
        return True
    except (RuntimeError, ImportError):
        return False


def build_embedding_text(produto: dict, aliases: Optional[List[str]] = None) -> str:
    """
    Constroi texto para embedding a partir dos campos do produto.

    Formato: "{nome_produto} | {tipo_materia_prima} | {tipo_embalagem} | {categoria_produto} | {subcategoria}"
    Se aliases disponiveis: " | Aliases: {alias1}, {alias2}, ..."

    Campos None/vazios sao omitidos. Aliases limitados a 5 para nao estourar tamanho.

    Args:
        produto: Dict com campos do cadastro_palletizacao
        aliases: Lista opcional de descricoes de clientes (de_para)

    Returns:
        Texto concatenado para gerar embedding
    """
    parts = [produto.get('nome_produto', '')]

    for campo in ('tipo_materia_prima', 'tipo_embalagem', 'categoria_produto', 'subcategoria'):
        valor = produto.get(campo)
        if valor and str(valor).strip():
            parts.append(str(valor).strip())

    texto = ' | '.join(parts)

    if aliases:
        aliases_text = ', '.join(aliases[:5])
        texto += f' | Aliases: {aliases_text}'

    return texto


def content_hash(text: str) -> str:
    """Gera MD5 hash do texto para stale detection."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def _collect_depara_aliases() -> Dict[str, List[str]]:
    """
    Coleta aliases de produtos das 3 tabelas de_para.

    REQUER app context ativo.

    Fontes:
    - depara_produto_cliente: nosso_codigo -> descricao_cliente
    - portal_atacadao_produto_depara: codigo_nosso -> descricao_atacadao
    - portal_sendas_produto_depara: codigo_nosso -> descricao_sendas

    Returns:
        Dict[cod_produto] -> [alias1, alias2, ...] (deduplicado case-insensitive)
    """
    from app import db
    from sqlalchemy import text

    aliases = {}  # cod_produto -> list[str]

    # 1. depara_produto_cliente (generico, por prefixo CNPJ)
    result = db.session.execute(text("""
        SELECT nosso_codigo, descricao_cliente
        FROM depara_produto_cliente
        WHERE ativo = true
          AND descricao_cliente IS NOT NULL
          AND descricao_cliente != ''
    """))
    for row in result.fetchall():
        cod = row[0]
        desc = row[1].strip()
        if desc:
            aliases.setdefault(cod, []).append(desc)

    # 2. portal_atacadao_produto_depara
    result = db.session.execute(text("""
        SELECT codigo_nosso, descricao_atacadao
        FROM portal_atacadao_produto_depara
        WHERE ativo = true
          AND descricao_atacadao IS NOT NULL
          AND descricao_atacadao != ''
    """))
    for row in result.fetchall():
        cod = row[0]
        desc = row[1].strip()
        if desc:
            aliases.setdefault(cod, []).append(desc)

    # 3. portal_sendas_produto_depara
    try:
        result = db.session.execute(text("""
            SELECT codigo_nosso, descricao_sendas
            FROM portal_sendas_produto_depara
            WHERE ativo = true
              AND descricao_sendas IS NOT NULL
              AND descricao_sendas != ''
        """))
        for row in result.fetchall():
            cod = row[0]
            desc = row[1].strip()
            if desc:
                aliases.setdefault(cod, []).append(desc)
    except Exception:
        pass  # Tabela pode nao existir ou estar vazia

    # Deduplicar (case-insensitive) por cod_produto
    for cod in aliases:
        seen = set()
        unique = []
        for a in aliases[cod]:
            key = a.lower()
            if key not in seen:
                seen.add(key)
                unique.append(a)
        aliases[cod] = unique

    return aliases


def _collect_products_impl() -> Tuple[List[Dict], int]:
    """
    Implementacao real da coleta de produtos. REQUER app context ativo.

    Coleta produtos vendidos ativos do cadastro_palletizacao e enriquece
    com aliases das tabelas de_para.
    """
    from app import db
    from sqlalchemy import text

    result = db.session.execute(text("""
        SELECT cod_produto, nome_produto, tipo_materia_prima,
               tipo_embalagem, categoria_produto, subcategoria,
               peso_bruto, palletizacao
        FROM cadastro_palletizacao
        WHERE ativo = true AND produto_vendido = true
        ORDER BY nome_produto
    """))

    rows = result.fetchall()

    # Coletar aliases de_para
    depara_aliases = _collect_depara_aliases()
    total_aliases = sum(len(v) for v in depara_aliases.values())
    print(f"[INFO] {len(depara_aliases)} produtos com aliases de_para ({total_aliases} aliases total)")

    produtos = []
    for row in rows:
        cod = row[0]
        prod = {
            'cod_produto': cod,
            'nome_produto': row[1],
            'tipo_materia_prima': row[2],
            'tipo_embalagem': row[3],
            'categoria_produto': row[4],
            'subcategoria': row[5],
            'peso_bruto': float(row[6]) if row[6] else 0,
            'palletizacao': float(row[7]) if row[7] else 0,
        }
        prod_aliases = depara_aliases.get(cod, [])
        prod['aliases'] = prod_aliases
        prod['texto_embedado'] = build_embedding_text(
            prod, aliases=prod_aliases if prod_aliases else None
        )
        prod['content_hash'] = content_hash(prod['texto_embedado'])
        produtos.append(prod)

    return produtos, len(produtos)


def collect_products() -> Tuple[List[Dict], int]:
    """
    Coleta todos os produtos vendidos ativos do cadastro_palletizacao,
    enriquecidos com aliases de tabelas de_para.

    Funciona tanto em app context existente (scheduler) quanto standalone (CLI).

    Returns:
        Tupla (lista_de_produtos, total)
    """
    if _has_app_context():
        return _collect_products_impl()

    from app import create_app
    app = create_app()
    with app.app_context():
        return _collect_products_impl()


def _index_products_impl(produtos: List[Dict], reindex: bool = False) -> Dict:
    """
    Implementacao real da indexacao. REQUER app context ativo.

    Detecta stale por comparacao de texto_embedado — aliases novos
    triggeram re-embed automaticamente.
    """
    from app import db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_DEFAULT_MODEL
    from sqlalchemy import text

    stats = {
        "total_produtos": len(produtos),
        "embedded": 0,
        "skipped": 0,
        "errors": 0,
        "total_tokens_est": 0,
    }

    svc = EmbeddingService()

    if reindex:
        print("[INFO] Removendo embeddings existentes...")
        db.session.execute(text("DELETE FROM product_embeddings"))
        db.session.commit()

    # Carregar existentes com texto para stale detection
    existing = {}  # cod_produto -> texto_embedado
    if not reindex:
        result = db.session.execute(text(
            "SELECT cod_produto, texto_embedado FROM product_embeddings"
        ))
        existing = {row[0]: row[1] for row in result.fetchall()}
        print(f"[INFO] {len(existing)} produtos ja existem no banco")

    # Filtrar: novos OU texto mudou (aliases adicionados/alterados)
    new_products = []
    for p in produtos:
        stored_text = existing.get(p['cod_produto'])
        if stored_text is None or stored_text != p['texto_embedado']:
            new_products.append(p)

    if not new_products:
        print("[INFO] Nenhum produto novo ou atualizado para indexar")
        stats["skipped"] = len(produtos)
        return stats

    stats["skipped"] = len(produtos) - len(new_products)
    new_count = sum(1 for p in new_products if p['cod_produto'] not in existing)
    updated_count = len(new_products) - new_count
    print(f"[INFO] {len(new_products)} produtos para indexar "
          f"({new_count} novos, {updated_count} atualizados)")

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


def index_products(produtos: List[Dict], reindex: bool = False) -> Dict:
    """
    Gera embeddings e salva no banco.

    Detecta stale por comparacao de texto (aliases novos triggeram re-embed).
    Funciona tanto em app context existente (scheduler) quanto standalone (CLI).

    Args:
        produtos: Lista de produtos do collect_products()
        reindex: Se True, apaga embeddings existentes primeiro

    Returns:
        Dict com estatisticas
    """
    if _has_app_context():
        return _index_products_impl(produtos, reindex=reindex)

    from app import create_app
    app = create_app()
    with app.app_context():
        return _index_products_impl(produtos, reindex=reindex)


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

            # Produtos com aliases
            with_aliases = conn.execute(text(
                "SELECT COUNT(*) FROM product_embeddings WHERE texto_embedado LIKE '%Aliases:%'"
            )).scalar()
            print(f"Com aliases de_para: {with_aliases}")

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
    com_aliases = sum(1 for p in produtos if p.get('aliases'))

    print(f"   Produtos: {total}")
    print(f"   Com aliases de_para: {com_aliases}")
    print(f"   Total chars: {total_chars:,}")
    print(f"   Total tokens (est): {total_tokens_est:,}")
    print(f"   Custo estimado: ${total_tokens_est * 0.02 / 1_000_000:.4f}")

    if args.dry_run:
        print("\n[DRY RUN] Top 10 maiores textos:")
        sorted_prods = sorted(produtos, key=lambda p: len(p['texto_embedado']), reverse=True)
        for i, p in enumerate(sorted_prods[:10]):
            print(f"   {i + 1}. [{p['cod_produto']}] {p['texto_embedado'][:100]} "
                  f"— {len(p['texto_embedado'])} chars")
            if p.get('aliases'):
                print(f"       Aliases ({len(p['aliases'])}): {', '.join(p['aliases'][:3])}")

        print(f"\nPor tipo_materia_prima:")
        from collections import Counter
        tipos = Counter(p.get('tipo_materia_prima', '(sem tipo)') for p in produtos)
        for tipo, count in tipos.most_common():
            print(f"   {tipo}: {count} produtos")

        print(f"\nTop 10 produtos com mais aliases:")
        sorted_by_aliases = sorted(produtos, key=lambda p: len(p.get('aliases', [])), reverse=True)
        for i, p in enumerate(sorted_by_aliases[:10]):
            if not p.get('aliases'):
                break
            print(f"   {i + 1}. [{p['cod_produto']}] {p['nome_produto']}: "
                  f"{len(p['aliases'])} aliases")
            for a in p['aliases'][:3]:
                print(f"       - {a}")
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
    print(f"Skipped (sem mudanca): {stats['skipped']}")
    print(f"Erros: {stats['errors']}")
    print(f"Tokens estimados: {stats['total_tokens_est']:,}")
    print(f"Custo estimado: ${stats['total_tokens_est'] * 0.02 / 1_000_000:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
