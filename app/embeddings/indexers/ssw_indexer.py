#!/usr/bin/env python3
"""
Indexador de documentos SSW para busca semantica.

Le todos os .md em .claude/references/ssw/, chunka por secoes (headers),
gera embeddings via Voyage AI e armazena no PostgreSQL.

Uso:
    source .venv/bin/activate
    python -m app.embeddings.indexers.ssw_indexer
    python -m app.embeddings.indexers.ssw_indexer --dry-run
    python -m app.embeddings.indexers.ssw_indexer --reindex
    python -m app.embeddings.indexers.ssw_indexer --stats

Custo estimado: ~$0.006 (1500 chunks x ~200 tokens x $0.02/1M tokens)
"""

import argparse
import json
import re
import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Tuple

# Setup path para imports do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


# Diretorio base da documentacao SSW
SSW_BASE = Path(__file__).resolve().parent.parent.parent.parent / ".claude" / "references" / "ssw"

# Tamanho minimo de chunk para valer a pena embeddar (em caracteres)
MIN_CHUNK_SIZE = 50

# Tamanho maximo de chunk (evitar tokens excessivos por chunk)
MAX_CHUNK_SIZE = 4000


def chunk_document(filepath: Path) -> List[Dict]:
    """
    Divide um arquivo .md em chunks por secoes (headers).

    Estrategia:
    1. Cada header (# ou ##) inicia um novo chunk
    2. Se nao houver headers, o documento inteiro e um chunk
    3. Chunks muito pequenos (<50 chars) sao descartados
    4. Chunks muito grandes (>4000 chars) sao divididos em paragrafos

    Args:
        filepath: Caminho do arquivo .md

    Returns:
        Lista de dicts com {heading, text, chunk_index}
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return []

    lines = content.split("\n")

    # Extrair titulo do documento (primeiro # H1)
    doc_title = ""
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            doc_title = line.lstrip("# ").strip()
            break

    # Dividir por headers
    chunks = []
    current_heading = doc_title or filepath.stem
    current_lines = []

    for line in lines:
        # Detectar headers (# ou ##, nao ### ou mais profundo)
        if re.match(r'^#{1,2}\s+', line):
            # Salvar chunk anterior
            if current_lines:
                chunk_text = "\n".join(current_lines).strip()
                if len(chunk_text) >= MIN_CHUNK_SIZE:
                    chunks.append({
                        "heading": current_heading,
                        "text": chunk_text,
                    })

            current_heading = line.lstrip("# ").strip()
            current_lines = [line]  # Inclui o header no chunk
        else:
            current_lines.append(line)

    # Salvar ultimo chunk
    if current_lines:
        chunk_text = "\n".join(current_lines).strip()
        if len(chunk_text) >= MIN_CHUNK_SIZE:
            chunks.append({
                "heading": current_heading,
                "text": chunk_text,
            })

    # Se nao gerou chunks (sem headers), usa documento inteiro
    if not chunks and content.strip():
        text = content.strip()
        if len(text) >= MIN_CHUNK_SIZE:
            chunks.append({
                "heading": doc_title or filepath.stem,
                "text": text,
            })

    # Dividir chunks muito grandes em paragrafos
    final_chunks = []
    for chunk in chunks:
        if len(chunk["text"]) > MAX_CHUNK_SIZE:
            # Dividir por paragrafos (linhas em branco duplas)
            paragraphs = re.split(r'\n\n+', chunk["text"])
            sub_text = ""
            for para in paragraphs:
                if len(sub_text) + len(para) > MAX_CHUNK_SIZE and sub_text:
                    final_chunks.append({
                        "heading": chunk["heading"],
                        "text": sub_text.strip(),
                    })
                    sub_text = para
                else:
                    sub_text += "\n\n" + para if sub_text else para

            if sub_text.strip() and len(sub_text.strip()) >= MIN_CHUNK_SIZE:
                final_chunks.append({
                    "heading": chunk["heading"],
                    "text": sub_text.strip(),
                })
        else:
            final_chunks.append(chunk)

    # Atribuir indices
    for i, chunk in enumerate(final_chunks):
        chunk["chunk_index"] = i
        chunk["doc_title"] = doc_title

    return final_chunks


def collect_all_chunks() -> Tuple[List[Dict], int]:
    """
    Coleta todos os chunks de todos os docs SSW.

    Returns:
        Tupla (lista_de_chunks, total_de_arquivos)
    """
    if not SSW_BASE.exists():
        print(f"[ERRO] Diretorio SSW nao encontrado: {SSW_BASE}")
        return [], 0

    all_chunks = []
    file_count = 0

    for md_file in sorted(SSW_BASE.rglob("*.md")):
        # Pular INDEX.md e MAPA_MENU.md (meta-documentos)
        if md_file.name in ("INDEX.md", "MAPA_MENU.md"):
            continue

        file_count += 1
        rel_path = str(md_file.relative_to(SSW_BASE))
        chunks = chunk_document(md_file)

        for chunk in chunks:
            chunk["doc_path"] = rel_path

        all_chunks.extend(chunks)

    return all_chunks, file_count


def index_chunks(chunks: List[Dict], reindex: bool = False) -> Dict:
    """
    Gera embeddings e salva no banco.

    Args:
        chunks: Lista de chunks do collect_all_chunks()
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
        "total_chunks": len(chunks),
        "embedded": 0,
        "skipped": 0,
        "errors": 0,
        "total_tokens_est": 0,
    }

    with app.app_context():
        svc = EmbeddingService()

        if reindex:
            print("[INFO] Removendo embeddings existentes...")
            db.session.execute(text("DELETE FROM ssw_document_embeddings"))
            db.session.commit()

        # Verificar quais chunks ja existem
        existing = set()
        if not reindex:
            result = db.session.execute(text(
                "SELECT doc_path, chunk_index FROM ssw_document_embeddings"
            ))
            existing = {(row[0], row[1]) for row in result.fetchall()}
            print(f"[INFO] {len(existing)} chunks ja existem no banco")

        # Filtrar chunks novos
        new_chunks = [
            c for c in chunks
            if (c["doc_path"], c["chunk_index"]) not in existing
        ]

        if not new_chunks:
            print("[INFO] Nenhum chunk novo para indexar")
            stats["skipped"] = len(chunks)
            return stats

        stats["skipped"] = len(chunks) - len(new_chunks)
        print(f"[INFO] {len(new_chunks)} chunks novos para indexar")

        # Gerar embeddings em batches
        batch_size = 128
        for i in range(0, len(new_chunks), batch_size):
            batch = new_chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]

            print(f"  Batch {i//batch_size + 1}/{(len(new_chunks)-1)//batch_size + 1} "
                  f"({len(batch)} chunks)...", end=" ")

            try:
                embeddings = svc.embed_texts(texts, input_type="document")

                # Salvar no banco
                for chunk, embedding in zip(batch, embeddings):
                    embedding_str = json.dumps(embedding)
                    char_count = len(chunk["text"])
                    token_est = max(1, char_count // 4)
                    stats["total_tokens_est"] += token_est

                    db.session.execute(text("""
                        INSERT INTO ssw_document_embeddings
                            (doc_path, chunk_index, chunk_text, heading, doc_title,
                             embedding, char_count, token_count, model_used)
                        VALUES
                            (:doc_path, :chunk_index, :chunk_text, :heading, :doc_title,
                             :embedding, :char_count, :token_count, :model_used)
                        ON CONFLICT (doc_path, chunk_index)
                        DO UPDATE SET
                            chunk_text = EXCLUDED.chunk_text,
                            heading = EXCLUDED.heading,
                            doc_title = EXCLUDED.doc_title,
                            embedding = EXCLUDED.embedding,
                            char_count = EXCLUDED.char_count,
                            token_count = EXCLUDED.token_count,
                            model_used = EXCLUDED.model_used,
                            updated_at = NOW()
                    """), {
                        "doc_path": chunk["doc_path"],
                        "chunk_index": chunk["chunk_index"],
                        "chunk_text": chunk["text"],
                        "heading": chunk["heading"],
                        "doc_title": chunk.get("doc_title", ""),
                        "embedding": embedding_str,
                        "char_count": char_count,
                        "token_count": token_est,
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
            if i + batch_size < len(new_chunks):
                time.sleep(0.5)

    return stats


def show_stats():
    """Mostra estatisticas das tabelas de embeddings."""
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("ESTATISTICAS DE EMBEDDINGS SSW")
        print("=" * 60)

        with db.engine.connect() as conn:
            # Total de registros
            total = conn.execute(text(
                "SELECT COUNT(*) FROM ssw_document_embeddings"
            )).scalar()
            with_emb = conn.execute(text(
                "SELECT COUNT(*) FROM ssw_document_embeddings WHERE embedding IS NOT NULL"
            )).scalar()

            print(f"\nTotal de chunks: {total}")
            print(f"Com embedding: {with_emb}")
            print(f"Sem embedding: {total - with_emb}")

            # Por subdiretorio
            print("\nPor subdiretorio:")
            result = conn.execute(text("""
                SELECT
                    SPLIT_PART(doc_path, '/', 1) as subdir,
                    COUNT(*) as total,
                    SUM(char_count) as total_chars,
                    SUM(token_count) as total_tokens
                FROM ssw_document_embeddings
                GROUP BY SPLIT_PART(doc_path, '/', 1)
                ORDER BY total DESC
            """))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} chunks, "
                      f"~{row[2]:,} chars, ~{row[3]:,} tokens")

            # Modelo usado
            print("\nModelos:")
            result = conn.execute(text("""
                SELECT model_used, COUNT(*)
                FROM ssw_document_embeddings
                WHERE model_used IS NOT NULL
                GROUP BY model_used
            """))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} chunks")


def main():
    parser = argparse.ArgumentParser(description='Indexar documentos SSW para busca semantica')
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas mostra chunks sem gerar embeddings')
    parser.add_argument('--reindex', action='store_true',
                        help='Apaga embeddings existentes e reindexa tudo')
    parser.add_argument('--stats', action='store_true',
                        help='Mostra estatisticas')

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    print("=" * 60)
    print("INDEXADOR SSW — Busca Semantica via Voyage AI")
    print("=" * 60)

    # Coletar chunks
    print(f"\n[1/2] Coletando chunks de {SSW_BASE}...")
    chunks, file_count = collect_all_chunks()

    total_chars = sum(len(c["text"]) for c in chunks)
    total_tokens_est = sum(max(1, len(c["text"]) // 4) for c in chunks)

    print(f"   Arquivos: {file_count}")
    print(f"   Chunks: {len(chunks)}")
    print(f"   Total chars: {total_chars:,}")
    print(f"   Total tokens (est): {total_tokens_est:,}")
    print(f"   Custo estimado: ${total_tokens_est * 0.02 / 1_000_000:.4f}")

    if args.dry_run:
        print("\n[DRY RUN] Top 10 maiores chunks:")
        sorted_chunks = sorted(chunks, key=lambda c: len(c["text"]), reverse=True)
        for i, c in enumerate(sorted_chunks[:10]):
            print(f"   {i+1}. [{c['doc_path']}] {c['heading'][:50]} — {len(c['text']):,} chars")

        print(f"\nPor subdiretorio:")
        from collections import Counter
        subdirs = Counter(c["doc_path"].split("/")[0] for c in chunks)
        for subdir, count in subdirs.most_common():
            print(f"   {subdir}: {count} chunks")
        return

    # Indexar
    print(f"\n[2/2] Gerando embeddings e salvando no banco...")
    start = time.time()
    stats = index_chunks(chunks, reindex=args.reindex)
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
