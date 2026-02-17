#!/usr/bin/env python3
"""
Indexador de turns de sessao do agente para busca semantica.

Le sessoes do agente (agent_sessions), extrai pares user+assistant,
gera embeddings via Voyage AI e armazena em session_turn_embeddings.

Uso:
    source .venv/bin/activate
    python -m app.embeddings.indexers.session_turn_indexer              # Indexar tudo
    python -m app.embeddings.indexers.session_turn_indexer --dry-run     # Preview
    python -m app.embeddings.indexers.session_turn_indexer --reindex     # Re-indexar
    python -m app.embeddings.indexers.session_turn_indexer --stats       # Estatisticas
    python -m app.embeddings.indexers.session_turn_indexer --user-id 5   # So usuario 5

Custo estimado: ~$0.02 (5K turns, ~500 chars cada)
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


# Tamanho maximo da resposta do assistant incluida no embedding
ASSISTANT_SUMMARY_MAX_CHARS = 500

# Tamanho minimo da mensagem do usuario para ser indexada
MIN_USER_CONTENT_CHARS = 10


def _has_app_context() -> bool:
    """Verifica se ja estamos dentro de um Flask app context."""
    try:
        from flask import current_app
        _ = current_app.name
        return True
    except (RuntimeError, ImportError):
        return False


def build_turn_text(user_content: str, assistant_content: str) -> str:
    """
    Constroi texto para embedding a partir de um par user+assistant.

    Args:
        user_content: Mensagem do usuario
        assistant_content: Resposta do assistente

    Returns:
        Texto combinado para gerar embedding
    """
    assistant_summary = (assistant_content or '')[:ASSISTANT_SUMMARY_MAX_CHARS]
    return f"[USER]: {user_content}\n[ASSISTANT]: {assistant_summary}"


def content_hash(text: str) -> str:
    """Gera MD5 hash do texto para stale detection."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def _collect_turns_impl(user_id: Optional[int] = None) -> Tuple[List[Dict], Dict]:
    """Implementacao real da coleta de turns. REQUER app context ativo."""
    from app.agente.models import AgentSession
    from sqlalchemy.orm import defer

    turns = []

    # defer() evita SELECT de colunas pesadas/inexistentes no banco
    query = AgentSession.query.options(
        defer(AgentSession.sdk_session_transcript),
    )
    if user_id:
        query = query.filter_by(user_id=user_id)

    sessions = query.order_by(AgentSession.created_at.desc()).all()
    print(f"[INFO] {len(sessions)} sessoes encontradas")

    for session in sessions:
        messages = session.get_messages()
        if not messages:
            continue

        # Extrair pares user -> assistant
        turn_index = 0
        i = 0
        while i < len(messages):
            msg = messages[i]

            if msg.get('role') == 'user':
                user_content = msg.get('content', '')

                # Buscar resposta do assistant (proximo message)
                assistant_content = ''
                if i + 1 < len(messages) and messages[i + 1].get('role') == 'assistant':
                    assistant_content = messages[i + 1].get('content', '')
                    i += 1  # Pular assistant no proximo loop

                # Filtrar mensagens muito curtas
                if len(user_content) >= MIN_USER_CONTENT_CHARS:
                    texto = build_turn_text(user_content, assistant_content)
                    turns.append({
                        'session_id': session.session_id,
                        'user_id': session.user_id,
                        'turn_index': turn_index,
                        'user_content': user_content,
                        'assistant_summary': assistant_content[:ASSISTANT_SUMMARY_MAX_CHARS] if assistant_content else None,
                        'texto_embedado': texto,
                        'content_hash': content_hash(texto),
                        'session_title': session.title,
                        'session_created_at': session.created_at,
                    })

                turn_index += 1

            i += 1

    stats = {
        'sessions': len(sessions),
        'turns': len(turns),
        'users': len(set(t['user_id'] for t in turns)),
    }

    return turns, stats


def collect_turns(user_id: Optional[int] = None) -> Tuple[List[Dict], Dict]:
    """
    Coleta pares user+assistant de todas as sessoes.

    Funciona tanto em app context existente (scheduler) quanto standalone (CLI).

    Args:
        user_id: Filtrar por usuario especifico (None = todos)

    Returns:
        Tupla (lista_turns, stats)
    """
    if _has_app_context():
        return _collect_turns_impl(user_id=user_id)

    from app import create_app
    app = create_app()
    with app.app_context():
        return _collect_turns_impl(user_id=user_id)


def _index_turns_impl(turns: List[Dict], reindex: bool = False) -> Dict:
    """Implementacao real da indexacao de turns. REQUER app context ativo."""
    from app import db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_DEFAULT_MODEL
    from sqlalchemy import text

    stats = {
        "total": len(turns),
        "embedded": 0,
        "skipped": 0,
        "errors": 0,
        "total_tokens_est": 0,
    }

    svc = EmbeddingService()

    if reindex:
        print("[INFO] Removendo embeddings existentes...")
        db.session.execute(text("DELETE FROM session_turn_embeddings"))
        db.session.commit()

    # Verificar quais turns ja existem (por content_hash)
    existing_hashes = set()
    if not reindex:
        result = db.session.execute(text(
            "SELECT content_hash FROM session_turn_embeddings WHERE content_hash IS NOT NULL"
        ))
        existing_hashes = {row[0] for row in result.fetchall()}
        print(f"[INFO] {len(existing_hashes)} turns ja existem no banco")

    # Filtrar novos
    new_turns = [t for t in turns if t['content_hash'] not in existing_hashes]

    if not new_turns:
        print("[INFO] Nenhum turn novo para indexar")
        stats["skipped"] = len(turns)
        return stats

    stats["skipped"] = len(turns) - len(new_turns)
    print(f"[INFO] {len(new_turns)} turns novos para indexar")

    # Gerar embeddings em batches
    batch_size = 128
    for i in range(0, len(new_turns), batch_size):
        batch = new_turns[i:i + batch_size]
        texts = [t['texto_embedado'] for t in batch]

        num_batch = i // batch_size + 1
        total_batches = (len(new_turns) - 1) // batch_size + 1
        print(f"  Batch {num_batch}/{total_batches} ({len(batch)} turns)...", end=" ")

        try:
            embeddings = svc.embed_texts(texts, input_type="document")

            for turn, embedding in zip(batch, embeddings):
                embedding_str = json.dumps(embedding)

                char_count = len(turn['texto_embedado'])
                token_est = max(1, char_count // 4)
                stats["total_tokens_est"] += token_est

                db.session.execute(text("""
                    INSERT INTO session_turn_embeddings
                        (session_id, user_id, turn_index,
                         user_content, assistant_summary, texto_embedado,
                         embedding, model_used, content_hash,
                         session_title, session_created_at)
                    VALUES
                        (:session_id, :user_id, :turn_index,
                         :user_content, :assistant_summary, :texto_embedado,
                         :embedding, :model_used, :content_hash,
                         :session_title, :session_created_at)
                    ON CONFLICT ON CONSTRAINT uq_session_turn
                    DO UPDATE SET
                        user_content = EXCLUDED.user_content,
                        assistant_summary = EXCLUDED.assistant_summary,
                        texto_embedado = EXCLUDED.texto_embedado,
                        embedding = EXCLUDED.embedding,
                        model_used = EXCLUDED.model_used,
                        content_hash = EXCLUDED.content_hash,
                        session_title = EXCLUDED.session_title,
                        session_created_at = EXCLUDED.session_created_at,
                        updated_at = NOW()
                """), {
                    "session_id": turn['session_id'],
                    "user_id": turn['user_id'],
                    "turn_index": turn['turn_index'],
                    "user_content": turn['user_content'],
                    "assistant_summary": turn['assistant_summary'],
                    "texto_embedado": turn['texto_embedado'],
                    "embedding": embedding_str,
                    "model_used": VOYAGE_DEFAULT_MODEL,
                    "content_hash": turn['content_hash'],
                    "session_title": turn['session_title'],
                    "session_created_at": turn['session_created_at'],
                })

            db.session.commit()
            stats["embedded"] += len(batch)
            print(f"OK ({len(batch)} embeddings salvos)")

        except Exception as e:
            print(f"ERRO: {e}")
            db.session.rollback()
            stats["errors"] += len(batch)

        # Rate limiting gentil
        if i + batch_size < len(new_turns):
            time.sleep(0.5)

    # Criar indice IVFFlat se pgvector disponivel e tabela nao vazia
    try:
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM session_turn_embeddings WHERE embedding IS NOT NULL"
        ))
        count = result.scalar()
        if count > 0:
            result = db.session.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ))
            if result.fetchone():
                lists = max(1, min(count // 10, 100))
                print(f"\n[INFO] Criando indice IVFFlat (lists={lists})...")
                try:
                    db.session.execute(text(
                        "DROP INDEX IF EXISTS idx_ste_emb_cosine"
                    ))
                    db.session.execute(text(f"""
                        CREATE INDEX idx_ste_emb_cosine
                            ON session_turn_embeddings
                            USING ivfflat (CAST(embedding AS vector) vector_cosine_ops)
                            WITH (lists = {lists})
                    """))
                    db.session.commit()
                    print("   IVFFlat index criado com sucesso")
                except Exception as idx_err:
                    print(f"   IVFFlat index falhou (ignorado): {idx_err}")
                    db.session.rollback()
    except Exception:
        pass

    return stats


def index_turns(turns: List[Dict], reindex: bool = False) -> Dict:
    """
    Gera embeddings e salva no banco via upsert.

    Funciona tanto em app context existente (scheduler) quanto standalone (CLI).

    Args:
        turns: Lista de turns do collect_turns()
        reindex: Se True, apaga embeddings existentes primeiro

    Returns:
        Dict com estatisticas
    """
    if _has_app_context():
        return _index_turns_impl(turns, reindex=reindex)

    from app import create_app
    app = create_app()
    with app.app_context():
        return _index_turns_impl(turns, reindex=reindex)


def show_stats():
    """Mostra estatisticas de session_turn_embeddings."""
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("ESTATISTICAS DE EMBEDDINGS — SESSION TURNS")
        print("=" * 60)

        with db.engine.connect() as conn:
            total = conn.execute(text(
                "SELECT COUNT(*) FROM session_turn_embeddings"
            )).scalar()
            with_emb = conn.execute(text(
                "SELECT COUNT(*) FROM session_turn_embeddings WHERE embedding IS NOT NULL"
            )).scalar()

            print(f"\nTotal de turns: {total}")
            print(f"Com embedding: {with_emb}")
            print(f"Sem embedding: {total - with_emb}")

            # Por usuario
            print("\nPor usuario:")
            result = conn.execute(text("""
                SELECT user_id, COUNT(*) as total,
                       COUNT(DISTINCT session_id) as sessions
                FROM session_turn_embeddings
                GROUP BY user_id
                ORDER BY total DESC
            """))
            for row in result.fetchall():
                print(f"  user_id={row[0]}: {row[1]} turns em {row[2]} sessoes")

            # Sessoes com mais turns
            print("\nTop 10 sessoes com mais turns:")
            result = conn.execute(text("""
                SELECT session_id, session_title, COUNT(*) as turns
                FROM session_turn_embeddings
                GROUP BY session_id, session_title
                ORDER BY turns DESC
                LIMIT 10
            """))
            for row in result.fetchall():
                title = row[1] or 'Sem titulo'
                print(f"  {row[0][:8]}... ({title[:40]}): {row[2]} turns")

            # Modelo
            print("\nModelos:")
            result = conn.execute(text("""
                SELECT model_used, COUNT(*)
                FROM session_turn_embeddings
                WHERE model_used IS NOT NULL
                GROUP BY model_used
            """))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} turns")


def main():
    parser = argparse.ArgumentParser(
        description='Indexar turns de sessao do agente para busca semantica'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas mostra turns sem gerar embeddings')
    parser.add_argument('--reindex', action='store_true',
                        help='Apaga embeddings existentes e reindexa tudo')
    parser.add_argument('--stats', action='store_true',
                        help='Mostra estatisticas')
    parser.add_argument('--user-id', type=int, default=None,
                        help='Indexar apenas turns de um usuario')

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    print("=" * 60)
    print("INDEXADOR DE SESSION TURNS — Busca Semantica via Voyage AI")
    print("=" * 60)

    # Coletar turns
    print(f"\n[1/2] Coletando turns de sessoes...")
    turns, collect_stats = collect_turns(user_id=args.user_id)

    total_chars = sum(len(t['texto_embedado']) for t in turns)
    total_tokens_est = sum(max(1, len(t['texto_embedado']) // 4) for t in turns)

    print(f"\n   Resumo:")
    print(f"   Sessoes: {collect_stats['sessions']}")
    print(f"   Turns: {collect_stats['turns']}")
    print(f"   Usuarios: {collect_stats['users']}")
    print(f"   Total chars: {total_chars:,}")
    print(f"   Total tokens (est): {total_tokens_est:,}")
    print(f"   Custo estimado: ${total_tokens_est * 0.02 / 1_000_000:.4f}")

    if args.dry_run:
        print("\n[DRY RUN] Primeiros 10 turns:")
        for i, t in enumerate(turns[:10]):
            user_preview = t['user_content'][:60]
            print(f"   {i + 1}. [{t['session_id'][:8]}] turn={t['turn_index']}: "
                  f"\"{user_preview}...\" ({len(t['texto_embedado'])} chars)")
        return

    # Indexar
    print(f"\n[2/2] Gerando embeddings e salvando no banco...")
    start = time.time()
    stats = index_turns(turns, reindex=args.reindex)
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
