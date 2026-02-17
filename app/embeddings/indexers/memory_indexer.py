#!/usr/bin/env python3
"""
Indexador de memorias do agente para busca semantica.

Le memorias persistentes (agent_memories), gera embeddings via Voyage AI
e armazena em agent_memory_embeddings.

Uso:
    source .venv/bin/activate
    python -m app.embeddings.indexers.memory_indexer              # Indexar tudo
    python -m app.embeddings.indexers.memory_indexer --dry-run     # Preview
    python -m app.embeddings.indexers.memory_indexer --reindex     # Re-indexar
    python -m app.embeddings.indexers.memory_indexer --stats       # Estatisticas
    python -m app.embeddings.indexers.memory_indexer --user-id 5   # So usuario 5

Custo estimado: ~$0.0004 (200 memorias, ~200 chars cada)
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


# Tamanho minimo do conteudo para ser indexado
MIN_CONTENT_CHARS = 10


def _has_app_context() -> bool:
    """Verifica se ja estamos dentro de um Flask app context."""
    try:
        from flask import current_app
        _ = current_app.name
        return True
    except (RuntimeError, ImportError):
        return False


def build_memory_text(path: str, content: str) -> str:
    """
    Constroi texto para embedding a partir de path e conteudo.

    Args:
        path: Path da memoria (ex: /memories/user.xml)
        content: Conteudo da memoria

    Returns:
        Texto combinado para gerar embedding
    """
    return f"[{path}]: {content}"


def content_hash(text: str) -> str:
    """Gera MD5 hash do texto para stale detection."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def _collect_memories_impl(user_id: Optional[int] = None) -> Tuple[List[Dict], Dict]:
    """Implementacao real da coleta de memorias. REQUER app context ativo."""
    from app.agente.models import AgentMemory

    memories_data = []

    query = AgentMemory.query.filter_by(is_directory=False)
    if user_id:
        query = query.filter_by(user_id=user_id)

    memories = query.filter(
        AgentMemory.content.isnot(None),
    ).order_by(AgentMemory.user_id, AgentMemory.path).all()

    print(f"[INFO] {len(memories)} memorias encontradas (arquivos com conteudo)")

    for mem in memories:
        content = (mem.content or '').strip()
        if len(content) < MIN_CONTENT_CHARS:
            continue

        texto = build_memory_text(mem.path, content)
        memories_data.append({
            'memory_id': mem.id,
            'user_id': mem.user_id,
            'path': mem.path,
            'texto_embedado': texto,
            'content_hash': content_hash(content),
        })

    stats = {
        'total_in_db': len(memories),
        'indexable': len(memories_data),
        'users': len(set(m['user_id'] for m in memories_data)),
    }

    return memories_data, stats


def collect_memories(user_id: Optional[int] = None) -> Tuple[List[Dict], Dict]:
    """
    Coleta memorias de todos os usuarios (ou de um especifico).

    Funciona tanto em app context existente (scheduler) quanto standalone (CLI).

    Args:
        user_id: Filtrar por usuario especifico (None = todos)

    Returns:
        Tupla (lista_memorias, stats)
    """
    if _has_app_context():
        return _collect_memories_impl(user_id=user_id)

    from app import create_app
    app = create_app()
    with app.app_context():
        return _collect_memories_impl(user_id=user_id)


def _index_memories_impl(memories: List[Dict], reindex: bool = False) -> Dict:
    """Implementacao real da indexacao de memorias. REQUER app context ativo."""
    from app import db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_DEFAULT_MODEL
    from sqlalchemy import text

    stats = {
        "total": len(memories),
        "embedded": 0,
        "skipped": 0,
        "errors": 0,
        "total_tokens_est": 0,
    }

    svc = EmbeddingService()

    if reindex:
        print("[INFO] Removendo embeddings existentes...")
        db.session.execute(text("DELETE FROM agent_memory_embeddings"))
        db.session.commit()

    # Verificar quais memorias ja existem (por content_hash + memory_id)
    existing = {}
    if not reindex:
        result = db.session.execute(text(
            "SELECT memory_id, content_hash FROM agent_memory_embeddings"
        ))
        existing = {row[0]: row[1] for row in result.fetchall()}
        print(f"[INFO] {len(existing)} memorias ja existem no banco")

    # Filtrar: novas OU conteudo mudou (hash diferente)
    new_memories = []
    for m in memories:
        existing_hash = existing.get(m['memory_id'])
        if existing_hash is None or existing_hash != m['content_hash']:
            new_memories.append(m)

    if not new_memories:
        print("[INFO] Nenhuma memoria nova ou atualizada para indexar")
        stats["skipped"] = len(memories)
        return stats

    stats["skipped"] = len(memories) - len(new_memories)
    print(f"[INFO] {len(new_memories)} memorias novas/atualizadas para indexar")

    # Gerar embeddings em batches
    batch_size = 128
    for i in range(0, len(new_memories), batch_size):
        batch = new_memories[i:i + batch_size]
        texts = [m['texto_embedado'] for m in batch]

        num_batch = i // batch_size + 1
        total_batches = (len(new_memories) - 1) // batch_size + 1
        print(f"  Batch {num_batch}/{total_batches} ({len(batch)} memorias)...", end=" ")

        try:
            embeddings = svc.embed_texts(texts, input_type="document")

            for mem, embedding in zip(batch, embeddings):
                embedding_str = json.dumps(embedding)

                char_count = len(mem['texto_embedado'])
                token_est = max(1, char_count // 4)
                stats["total_tokens_est"] += token_est

                db.session.execute(text("""
                    INSERT INTO agent_memory_embeddings
                        (memory_id, user_id, path,
                         texto_embedado, embedding, model_used, content_hash)
                    VALUES
                        (:memory_id, :user_id, :path,
                         :texto_embedado, :embedding, :model_used, :content_hash)
                    ON CONFLICT ON CONSTRAINT uq_memory_embedding
                    DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        path = EXCLUDED.path,
                        texto_embedado = EXCLUDED.texto_embedado,
                        embedding = EXCLUDED.embedding,
                        model_used = EXCLUDED.model_used,
                        content_hash = EXCLUDED.content_hash,
                        updated_at = NOW()
                """), {
                    "memory_id": mem['memory_id'],
                    "user_id": mem['user_id'],
                    "path": mem['path'],
                    "texto_embedado": mem['texto_embedado'],
                    "embedding": embedding_str,
                    "model_used": VOYAGE_DEFAULT_MODEL,
                    "content_hash": mem['content_hash'],
                })

            db.session.commit()
            stats["embedded"] += len(batch)
            print(f"OK ({len(batch)} embeddings salvos)")

        except Exception as e:
            print(f"ERRO: {e}")
            db.session.rollback()
            stats["errors"] += len(batch)

        # Rate limiting gentil
        if i + batch_size < len(new_memories):
            time.sleep(0.5)

    # Nota: Indices HNSW sao criados pela migration criar_indices_hnsw_embeddings.py
    # IVFFlat removido (HNSW tem melhor recall e funciona em tabelas vazias)

    return stats


def index_memories(memories: List[Dict], reindex: bool = False) -> Dict:
    """
    Gera embeddings e salva no banco via upsert.

    Funciona tanto em app context existente (scheduler) quanto standalone (CLI).

    Args:
        memories: Lista de memorias do collect_memories()
        reindex: Se True, apaga embeddings existentes primeiro

    Returns:
        Dict com estatisticas
    """
    if _has_app_context():
        return _index_memories_impl(memories, reindex=reindex)

    from app import create_app
    app = create_app()
    with app.app_context():
        return _index_memories_impl(memories, reindex=reindex)


def show_stats():
    """Mostra estatisticas de agent_memory_embeddings."""
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("ESTATISTICAS DE EMBEDDINGS — MEMORIAS DO AGENTE")
        print("=" * 60)

        with db.engine.connect() as conn:
            total = conn.execute(text(
                "SELECT COUNT(*) FROM agent_memory_embeddings"
            )).scalar()
            with_emb = conn.execute(text(
                "SELECT COUNT(*) FROM agent_memory_embeddings WHERE embedding IS NOT NULL"
            )).scalar()

            print(f"\nTotal de memorias: {total}")
            print(f"Com embedding: {with_emb}")
            print(f"Sem embedding: {total - with_emb}")

            # Por usuario
            print("\nPor usuario:")
            result = conn.execute(text("""
                SELECT user_id, COUNT(*) as total
                FROM agent_memory_embeddings
                GROUP BY user_id
                ORDER BY total DESC
            """))
            for row in result.fetchall():
                print(f"  user_id={row[0]}: {row[1]} memorias")

            # Paths mais comuns
            print("\nTop 10 paths:")
            result = conn.execute(text("""
                SELECT path, COUNT(*) as total
                FROM agent_memory_embeddings
                GROUP BY path
                ORDER BY total DESC
                LIMIT 10
            """))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]}")

            # Modelo
            print("\nModelos:")
            result = conn.execute(text("""
                SELECT model_used, COUNT(*)
                FROM agent_memory_embeddings
                WHERE model_used IS NOT NULL
                GROUP BY model_used
            """))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} memorias")


def main():
    parser = argparse.ArgumentParser(
        description='Indexar memorias do agente para busca semantica'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas mostra memorias sem gerar embeddings')
    parser.add_argument('--reindex', action='store_true',
                        help='Apaga embeddings existentes e reindexa tudo')
    parser.add_argument('--stats', action='store_true',
                        help='Mostra estatisticas')
    parser.add_argument('--user-id', type=int, default=None,
                        help='Indexar apenas memorias de um usuario')

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    print("=" * 60)
    print("INDEXADOR DE MEMORIAS DO AGENTE — Busca Semantica via Voyage AI")
    print("=" * 60)

    # Coletar memorias
    print(f"\n[1/2] Coletando memorias...")
    memories, collect_stats = collect_memories(user_id=args.user_id)

    total_chars = sum(len(m['texto_embedado']) for m in memories)
    total_tokens_est = sum(max(1, len(m['texto_embedado']) // 4) for m in memories)

    print(f"\n   Resumo:")
    print(f"   Memorias no DB: {collect_stats['total_in_db']}")
    print(f"   Indexaveis (>= {MIN_CONTENT_CHARS} chars): {collect_stats['indexable']}")
    print(f"   Usuarios: {collect_stats['users']}")
    print(f"   Total chars: {total_chars:,}")
    print(f"   Total tokens (est): {total_tokens_est:,}")
    print(f"   Custo estimado: ${total_tokens_est * 0.02 / 1_000_000:.6f}")

    if args.dry_run:
        print("\n[DRY RUN] Primeiras 10 memorias:")
        for i, m in enumerate(memories[:10]):
            content_preview = m['texto_embedado'][:80]
            print(f"   {i + 1}. [user={m['user_id']}] {m['path']}: "
                  f"\"{content_preview}...\" ({len(m['texto_embedado'])} chars)")
        return

    # Indexar
    print(f"\n[2/2] Gerando embeddings e salvando no banco...")
    start = time.time()
    stats = index_memories(memories, reindex=args.reindex)
    elapsed = time.time() - start

    print(f"\n" + "=" * 60)
    print("RESULTADO")
    print("=" * 60)
    print(f"Tempo: {elapsed:.1f}s")
    print(f"Embeddings gerados: {stats['embedded']}")
    print(f"Skipped (ja existiam): {stats['skipped']}")
    print(f"Erros: {stats['errors']}")
    print(f"Tokens estimados: {stats['total_tokens_est']:,}")
    print(f"Custo estimado: ${stats['total_tokens_est'] * 0.02 / 1_000_000:.6f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
