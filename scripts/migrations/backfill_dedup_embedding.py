#!/usr/bin/env python3
"""
Backfill: Popular dedup_embedding para registros existentes.

Gera embedding do texto limpo (strip_xml_tags do conteúdo original)
e salva na coluna dedup_embedding de agent_memory_embeddings.

Uso:
    source .venv/bin/activate
    python scripts/migrations/backfill_dedup_embedding.py [--dry-run]

Custo estimado: ~$0.001 por 100 memórias (Voyage voyage-4-lite).
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def run_backfill(dry_run: bool = False):
    from app import create_app
    app = create_app()

    with app.app_context():
        from app import db
        from sqlalchemy import text
        from app.embeddings.service import EmbeddingService
        from app.agente.services.knowledge_graph_service import strip_xml_tags
        from app.agente.models import AgentMemory

        # Buscar registros sem dedup_embedding
        rows = db.session.execute(text("""
            SELECT ame.id, ame.memory_id, ame.path
            FROM agent_memory_embeddings ame
            WHERE ame.dedup_embedding IS NULL
            ORDER BY ame.id
        """)).fetchall()

        total = len(rows)
        print(f"Registros sem dedup_embedding: {total}")

        if total == 0:
            print("✓ Nada para fazer — todos já têm dedup_embedding.")
            return

        if dry_run:
            print(f"[DRY-RUN] Seria gerado dedup_embedding para {total} registros.")
            return

        svc = EmbeddingService()
        sucesso = 0
        erros = 0

        # Processar em batches de 32
        batch_size = 32
        for batch_start in range(0, total, batch_size):
            batch = rows[batch_start:batch_start + batch_size]

            # Carregar conteúdo das memórias
            memory_ids = [r.memory_id for r in batch]
            memories = {
                m.id: m for m in
                AgentMemory.query.filter(AgentMemory.id.in_(memory_ids)).all()
            }

            texts_to_embed = []
            embed_rows = []

            for row in batch:
                mem = memories.get(row.memory_id)
                if not mem or not mem.content:
                    erros += 1
                    continue

                # Texto limpo: strip XML (mesmo que _check_memory_duplicate faz)
                clean_text = strip_xml_tags(mem.content)
                if not clean_text.strip():
                    erros += 1
                    continue

                texts_to_embed.append(clean_text)
                embed_rows.append(row)

            if not texts_to_embed:
                continue

            # Gerar embeddings em batch
            try:
                embeddings = svc.embed_texts(texts_to_embed, input_type="document")
            except Exception as e:
                print(f"  ✗ Erro ao gerar embeddings batch {batch_start}: {e}")
                erros += len(texts_to_embed)
                continue

            # Salvar no banco
            for row, embedding in zip(embed_rows, embeddings):
                try:
                    embedding_str = json.dumps(embedding)
                    db.session.execute(text("""
                        UPDATE agent_memory_embeddings
                        SET dedup_embedding = CAST(:embedding AS vector)
                        WHERE id = :id
                    """), {"embedding": embedding_str, "id": row.id})
                    sucesso += 1
                except Exception as e:
                    print(f"  ✗ Erro ao salvar id={row.id}: {e}")
                    erros += 1

            db.session.commit()
            print(f"  Batch {batch_start + 1}-{batch_start + len(batch)}/{total}: "
                  f"{sucesso} OK, {erros} erros")

        print(f"\n✓ Backfill concluído: {sucesso}/{total} sucesso, {erros} erros")


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run_backfill(dry_run=dry_run)
