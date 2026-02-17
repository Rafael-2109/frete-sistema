#!/usr/bin/env python3
"""
Indexador de entidades financeiras para busca semantica.

Le fornecedores (contas_a_pagar) e clientes (contas_a_receber),
agrupa por CNPJ raiz (8 digitos), gera embeddings via Voyage AI
e armazena em financial_entity_embeddings.

Uso:
    source .venv/bin/activate
    python -m app.embeddings.indexers.entity_indexer              # Indexar tudo
    python -m app.embeddings.indexers.entity_indexer --dry-run     # Preview
    python -m app.embeddings.indexers.entity_indexer --reindex     # Re-indexar tudo
    python -m app.embeddings.indexers.entity_indexer --stats       # Estatisticas
    python -m app.embeddings.indexers.entity_indexer --type supplier  # So fornecedores
    python -m app.embeddings.indexers.entity_indexer --type customer  # So clientes

Custo estimado: ~$0.02 (5K-15K fornecedores + 2K-8K clientes)
"""

import argparse
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


def build_embedding_text(nome_canonico: str, nomes_alternativos: List[str]) -> str:
    """
    Constroi texto para embedding a partir do nome canonico e variacoes.

    Formato: "{nome_canonico} | {variacao_1} | {variacao_2}"
    Variacoes duplicatas ou substring do canonico sao omitidas.

    Args:
        nome_canonico: Nome mais completo (longest raz_social)
        nomes_alternativos: Variacoes conhecidas para mesmo CNPJ raiz

    Returns:
        Texto concatenado para gerar embedding
    """
    parts = [nome_canonico]

    canonico_upper = nome_canonico.upper()
    for nome in nomes_alternativos:
        nome_upper = nome.upper()
        # Omitir variacoes que sao substring do canonico
        if nome_upper != canonico_upper and nome_upper not in canonico_upper:
            parts.append(nome)

    return ' | '.join(parts)


def _collect_suppliers_impl() -> List[Dict]:
    """Implementacao real da coleta de fornecedores. REQUER app context ativo."""
    from app import db
    from sqlalchemy import text

    result = db.session.execute(text("""
        WITH cnpj_limpo AS (
            SELECT
                cnpj,
                raz_social,
                substring(regexp_replace(cnpj, '\\D', '', 'g') FROM 1 FOR 8) AS raiz,
                length(raz_social) AS len_nome
            FROM contas_a_pagar
            WHERE cnpj IS NOT NULL
              AND cnpj != ''
              AND raz_social IS NOT NULL
              AND raz_social != ''
        ),
        agrupado AS (
            SELECT
                raiz,
                -- CNPJ mais completo (primeiro por raiz)
                (array_agg(cnpj ORDER BY len_nome DESC))[1] AS cnpj_representativo,
                -- Nome mais longo = canonico
                (array_agg(raz_social ORDER BY len_nome DESC))[1] AS nome_canonico,
                -- Todas as variacoes
                array_agg(DISTINCT raz_social ORDER BY raz_social) AS nomes
            FROM cnpj_limpo
            WHERE raiz != ''
              AND length(raiz) = 8
            GROUP BY raiz
        )
        SELECT raiz, cnpj_representativo, nome_canonico, nomes
        FROM agrupado
        ORDER BY nome_canonico
    """))

    entidades = []
    for row in result.fetchall():
        raiz = row[0]
        cnpj = row[1]
        nome_canonico = row[2]
        nomes = list(row[3]) if row[3] else []

        # Filtrar nomes alternativos (remover canonico da lista)
        nomes_alt = [n for n in nomes if n.upper() != nome_canonico.upper()]

        entidades.append({
            'entity_type': 'supplier',
            'cnpj_raiz': raiz,
            'cnpj_completo': cnpj,
            'nome': nome_canonico,
            'nomes_alternativos': nomes_alt,
            'texto_embedado': build_embedding_text(nome_canonico, nomes_alt),
        })

    return entidades


def collect_suppliers() -> List[Dict]:
    """
    Coleta fornecedores unicos de contas_a_pagar, agrupados por CNPJ raiz.

    Funciona tanto em app context existente (scheduler) quanto standalone (CLI).

    Returns:
        Lista de dicts com cnpj_raiz, cnpj_completo, nome, nomes_alternativos
    """
    if _has_app_context():
        return _collect_suppliers_impl()

    from app import create_app
    app = create_app()
    with app.app_context():
        return _collect_suppliers_impl()


def _collect_customers_impl() -> List[Dict]:
    """Implementacao real da coleta de clientes. REQUER app context ativo."""
    from app import db
    from sqlalchemy import text

    result = db.session.execute(text("""
        WITH cnpj_limpo AS (
            SELECT
                cnpj,
                raz_social,
                raz_social_red,
                substring(regexp_replace(cnpj, '\\D', '', 'g') FROM 1 FOR 8) AS raiz,
                length(raz_social) AS len_nome
            FROM contas_a_receber
            WHERE cnpj IS NOT NULL
              AND cnpj != ''
              AND raz_social IS NOT NULL
              AND raz_social != ''
        ),
        agrupado AS (
            SELECT
                raiz,
                (array_agg(cnpj ORDER BY len_nome DESC))[1] AS cnpj_representativo,
                (array_agg(raz_social ORDER BY len_nome DESC))[1] AS nome_canonico,
                array_agg(DISTINCT raz_social ORDER BY raz_social) AS nomes_razao,
                array_agg(DISTINCT raz_social_red ORDER BY raz_social_red)
                    FILTER (WHERE raz_social_red IS NOT NULL AND raz_social_red != '')
                    AS nomes_red
            FROM cnpj_limpo
            WHERE raiz != ''
              AND length(raiz) = 8
            GROUP BY raiz
        )
        SELECT raiz, cnpj_representativo, nome_canonico, nomes_razao, nomes_red
        FROM agrupado
        ORDER BY nome_canonico
    """))

    entidades = []
    for row in result.fetchall():
        raiz = row[0]
        cnpj = row[1]
        nome_canonico = row[2]
        nomes_razao = list(row[3]) if row[3] else []
        nomes_red = list(row[4]) if row[4] else []

        # Combinar variacoes de raz_social + raz_social_red
        todos_nomes = set()
        for n in nomes_razao + nomes_red:
            if n and n.upper() != nome_canonico.upper():
                todos_nomes.add(n)

        nomes_alt = sorted(todos_nomes)

        entidades.append({
            'entity_type': 'customer',
            'cnpj_raiz': raiz,
            'cnpj_completo': cnpj,
            'nome': nome_canonico,
            'nomes_alternativos': nomes_alt,
            'texto_embedado': build_embedding_text(nome_canonico, nomes_alt),
        })

    return entidades


def collect_customers() -> List[Dict]:
    """
    Coleta clientes unicos de contas_a_receber, agrupados por CNPJ raiz.

    Funciona tanto em app context existente (scheduler) quanto standalone (CLI).

    Returns:
        Lista de dicts com cnpj_raiz, cnpj_completo, nome, nomes_alternativos
    """
    if _has_app_context():
        return _collect_customers_impl()

    from app import create_app
    app = create_app()
    with app.app_context():
        return _collect_customers_impl()


def collect_entities(entity_type: Optional[str] = None) -> Tuple[List[Dict], Dict]:
    """
    Coleta entidades conforme tipo solicitado.

    Args:
        entity_type: 'supplier', 'customer', ou None para ambos

    Returns:
        Tupla (lista_entidades, stats)
    """
    entidades = []

    if entity_type in (None, 'supplier'):
        print("[INFO] Coletando fornecedores de contas_a_pagar...")
        suppliers = collect_suppliers()
        print(f"   {len(suppliers)} fornecedores unicos (por CNPJ raiz)")
        entidades.extend(suppliers)

    if entity_type in (None, 'customer'):
        print("[INFO] Coletando clientes de contas_a_receber...")
        customers = collect_customers()
        print(f"   {len(customers)} clientes unicos (por CNPJ raiz)")
        entidades.extend(customers)

    stats = {
        'suppliers': sum(1 for e in entidades if e['entity_type'] == 'supplier'),
        'customers': sum(1 for e in entidades if e['entity_type'] == 'customer'),
        'total': len(entidades),
    }

    return entidades, stats


def _index_entities_impl(entidades: List[Dict], reindex: bool = False) -> Dict:
    """Implementacao real da indexacao. REQUER app context ativo."""
    from app import db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_DEFAULT_MODEL
    from sqlalchemy import text

    stats = {
        "total": len(entidades),
        "embedded": 0,
        "skipped": 0,
        "errors": 0,
        "total_tokens_est": 0,
    }

    svc = EmbeddingService()

    if reindex:
        print("[INFO] Removendo embeddings existentes...")
        db.session.execute(text("DELETE FROM financial_entity_embeddings"))
        db.session.commit()

    # Verificar quais entidades ja existem
    existing = set()
    if not reindex:
        result = db.session.execute(text(
            "SELECT entity_type || ':' || cnpj_raiz FROM financial_entity_embeddings"
        ))
        existing = {row[0] for row in result.fetchall()}
        print(f"[INFO] {len(existing)} entidades ja existem no banco")

    # Filtrar novas
    new_entities = [
        e for e in entidades
        if f"{e['entity_type']}:{e['cnpj_raiz']}" not in existing
    ]

    if not new_entities:
        print("[INFO] Nenhuma entidade nova para indexar")
        stats["skipped"] = len(entidades)
        return stats

    stats["skipped"] = len(entidades) - len(new_entities)
    print(f"[INFO] {len(new_entities)} entidades novas para indexar")

    # Gerar embeddings em batches
    batch_size = 128
    for i in range(0, len(new_entities), batch_size):
        batch = new_entities[i:i + batch_size]
        texts = [e['texto_embedado'] for e in batch]

        num_batch = i // batch_size + 1
        total_batches = (len(new_entities) - 1) // batch_size + 1
        print(f"  Batch {num_batch}/{total_batches} ({len(batch)} entidades)...", end=" ")

        try:
            embeddings = svc.embed_texts(texts, input_type="document")

            # Salvar no banco via upsert
            for ent, embedding in zip(batch, embeddings):
                embedding_str = json.dumps(embedding)
                nomes_alt_json = json.dumps(
                    ent['nomes_alternativos'], ensure_ascii=False
                ) if ent['nomes_alternativos'] else None

                char_count = len(ent['texto_embedado'])
                token_est = max(1, char_count // 4)
                stats["total_tokens_est"] += token_est

                db.session.execute(text("""
                    INSERT INTO financial_entity_embeddings
                        (entity_type, cnpj_raiz, cnpj_completo, nome,
                         nomes_alternativos, texto_embedado, embedding, model_used)
                    VALUES
                        (:entity_type, :cnpj_raiz, :cnpj_completo, :nome,
                         :nomes_alternativos, :texto_embedado, :embedding, :model_used)
                    ON CONFLICT ON CONSTRAINT uq_fin_entity_type_cnpj
                    DO UPDATE SET
                        cnpj_completo = EXCLUDED.cnpj_completo,
                        nome = EXCLUDED.nome,
                        nomes_alternativos = EXCLUDED.nomes_alternativos,
                        texto_embedado = EXCLUDED.texto_embedado,
                        embedding = EXCLUDED.embedding,
                        model_used = EXCLUDED.model_used,
                        updated_at = NOW()
                """), {
                    "entity_type": ent['entity_type'],
                    "cnpj_raiz": ent['cnpj_raiz'],
                    "cnpj_completo": ent['cnpj_completo'],
                    "nome": ent['nome'],
                    "nomes_alternativos": nomes_alt_json,
                    "texto_embedado": ent['texto_embedado'],
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
        if i + batch_size < len(new_entities):
            time.sleep(0.5)

    return stats


def index_entities(entidades: List[Dict], reindex: bool = False) -> Dict:
    """
    Gera embeddings e salva no banco via upsert.

    Funciona tanto em app context existente (scheduler) quanto standalone (CLI).

    Args:
        entidades: Lista de entidades do collect_entities()
        reindex: Se True, apaga embeddings existentes primeiro

    Returns:
        Dict com estatisticas
    """
    if _has_app_context():
        return _index_entities_impl(entidades, reindex=reindex)

    from app import create_app
    app = create_app()
    with app.app_context():
        return _index_entities_impl(entidades, reindex=reindex)


def show_stats():
    """Mostra estatisticas de financial_entity_embeddings."""
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("ESTATISTICAS DE EMBEDDINGS — ENTIDADES FINANCEIRAS")
        print("=" * 60)

        with db.engine.connect() as conn:
            # Total de registros
            total = conn.execute(text(
                "SELECT COUNT(*) FROM financial_entity_embeddings"
            )).scalar()
            with_emb = conn.execute(text(
                "SELECT COUNT(*) FROM financial_entity_embeddings WHERE embedding IS NOT NULL"
            )).scalar()

            print(f"\nTotal de entidades: {total}")
            print(f"Com embedding: {with_emb}")
            print(f"Sem embedding: {total - with_emb}")

            # Por tipo
            print("\nPor entity_type:")
            result = conn.execute(text("""
                SELECT entity_type, COUNT(*) as total,
                       COUNT(*) FILTER (WHERE embedding IS NOT NULL) as com_emb
                FROM financial_entity_embeddings
                GROUP BY entity_type
                ORDER BY entity_type
            """))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} total ({row[2]} com embedding)")

            # Top 10 com mais variacoes
            print("\nTop 10 entidades com mais variacoes:")
            result = conn.execute(text("""
                SELECT entity_type, nome, cnpj_raiz,
                       jsonb_array_length(nomes_alternativos::jsonb) as num_alt
                FROM financial_entity_embeddings
                WHERE nomes_alternativos IS NOT NULL
                  AND nomes_alternativos != 'null'
                ORDER BY jsonb_array_length(nomes_alternativos::jsonb) DESC
                LIMIT 10
            """))
            for row in result.fetchall():
                print(f"  [{row[0]}] {row[1]} (raiz={row[2]}, {row[3]} variacoes)")

            # Modelo
            print("\nModelos:")
            result = conn.execute(text("""
                SELECT model_used, COUNT(*)
                FROM financial_entity_embeddings
                WHERE model_used IS NOT NULL
                GROUP BY model_used
            """))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} entidades")


def main():
    parser = argparse.ArgumentParser(
        description='Indexar entidades financeiras para busca semantica'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas mostra entidades sem gerar embeddings')
    parser.add_argument('--reindex', action='store_true',
                        help='Apaga embeddings existentes e reindexa tudo')
    parser.add_argument('--stats', action='store_true',
                        help='Mostra estatisticas')
    parser.add_argument('--type', choices=['supplier', 'customer'],
                        help='Indexar apenas fornecedores ou clientes')

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    print("=" * 60)
    print("INDEXADOR DE ENTIDADES FINANCEIRAS — Busca Semantica via Voyage AI")
    print("=" * 60)

    # Coletar entidades
    print(f"\n[1/2] Coletando entidades...")
    entidades, collect_stats = collect_entities(entity_type=args.type)

    total_chars = sum(len(e['texto_embedado']) for e in entidades)
    total_tokens_est = sum(max(1, len(e['texto_embedado']) // 4) for e in entidades)

    print(f"\n   Resumo:")
    print(f"   Fornecedores: {collect_stats['suppliers']}")
    print(f"   Clientes: {collect_stats['customers']}")
    print(f"   Total: {collect_stats['total']}")
    print(f"   Total chars: {total_chars:,}")
    print(f"   Total tokens (est): {total_tokens_est:,}")
    print(f"   Custo estimado: ${total_tokens_est * 0.02 / 1_000_000:.4f}")

    if args.dry_run:
        print("\n[DRY RUN] Top 10 maiores textos embedados:")
        sorted_ents = sorted(entidades, key=lambda e: len(e['texto_embedado']), reverse=True)
        for i, e in enumerate(sorted_ents[:10]):
            texto_preview = e['texto_embedado'][:80]
            n_alt = len(e['nomes_alternativos'])
            print(f"   {i + 1}. [{e['entity_type']}] {e['cnpj_raiz']} — {texto_preview}... "
                  f"({len(e['texto_embedado'])} chars, {n_alt} variacoes)")

        print(f"\nTop 10 com mais variacoes de nome:")
        sorted_by_alt = sorted(entidades, key=lambda e: len(e['nomes_alternativos']), reverse=True)
        for i, e in enumerate(sorted_by_alt[:10]):
            print(f"   {i + 1}. [{e['entity_type']}] {e['nome'][:50]} — "
                  f"{len(e['nomes_alternativos'])} variacoes")
            for alt in e['nomes_alternativos'][:3]:
                print(f"       - {alt}")
        return

    # Indexar
    print(f"\n[2/2] Gerando embeddings e salvando no banco...")
    start = time.time()
    stats = index_entities(entidades, reindex=args.reindex)
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
