"""Reindex de agent_memory_embeddings para VOYAGE_MEMORY_MODEL (voyage-4-large).

Migracao do retrieval de memorias lite -> large (decisao Rafael 2026-06-10;
base: relatorios/estudo_contexto_boot_2026-06-09/precision_at_k_baseline_2026-06-10.md
— precision@4 0.842 vs 0.558 @0.45 no mesmo corpus).

O que faz (idempotente — WHERE model_used != alvo):
- Re-embeda o texto_embedado EXISTENTE (NAO regenera contexto Sonnet) com
  VOYAGE_MEMORY_MODEL em batches e atualiza SOMENTE `embedding` + `model_used`.
- `dedup_embedding` e `content_hash` ficam INTACTOS (dedup permanece no lite).
- Inclui memorias cold (barato; evita inconsistencia se reaquecerem).

ORDEM DE DEPLOY:
  1. Deploy do codigo (busca passa a filtrar model_used=voyage-4-large —
     semantic temporariamente vazio, fallback com caps F4 cobre).
  2. Rodar ESTE script no Render Shell: --confirmar (dry-run e o default).
  3. Cobertura volta a 100% ao final (~549 linhas, poucos minutos).

Uso:
    python scripts/migrations/2026_06_10_reindex_memorias_voyage4large.py            # dry-run
    python scripts/migrations/2026_06_10_reindex_memorias_voyage4large.py --confirmar
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BATCH = 64


def main():
    confirmar = '--confirmar' in sys.argv

    from sqlalchemy import text
    from app import create_app, db
    from app.embeddings.config import VOYAGE_MEMORY_MODEL
    from app.embeddings.service import EmbeddingService

    app = create_app()
    with app.app_context():
        rows = db.session.execute(text("""
            SELECT id, texto_embedado, model_used
            FROM agent_memory_embeddings
            WHERE model_used IS DISTINCT FROM :alvo
            ORDER BY id
        """), {"alvo": VOYAGE_MEMORY_MODEL}).fetchall()

        print(f'[INFO] alvo={VOYAGE_MEMORY_MODEL} | linhas a reindexar: {len(rows)}')
        if not rows:
            print('[OK] nada a fazer (idempotente).')
            return
        if not confirmar:
            por_modelo = {}
            for r in rows:
                por_modelo[r.model_used] = por_modelo.get(r.model_used, 0) + 1
            print(f'[DRY-RUN] por modelo atual: {por_modelo}')
            print('[DRY-RUN] re-rode com --confirmar para aplicar.')
            return

        svc = EmbeddingService()
        feitas = 0
        for i in range(0, len(rows), BATCH):
            batch = rows[i:i + BATCH]
            embeddings = svc.embed_texts(
                [r.texto_embedado for r in batch],
                input_type="document",
                model=VOYAGE_MEMORY_MODEL,
            )
            for r, emb in zip(batch, embeddings):
                db.session.execute(text("""
                    UPDATE agent_memory_embeddings
                    SET embedding = CAST(:emb AS vector),
                        model_used = :alvo,
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "emb": json.dumps(emb),
                    "alvo": VOYAGE_MEMORY_MODEL,
                    "id": r.id,
                })
            db.session.commit()
            feitas += len(batch)
            print(f'  [{feitas}/{len(rows)}] commit batch')

        restantes = db.session.execute(text("""
            SELECT COUNT(*) FROM agent_memory_embeddings
            WHERE model_used IS DISTINCT FROM :alvo
        """), {"alvo": VOYAGE_MEMORY_MODEL}).scalar()
        if restantes:
            raise RuntimeError(f'{restantes} linhas nao migradas.')
        print(f'\n[OK] {feitas} embeddings reindexados para {VOYAGE_MEMORY_MODEL}.')


if __name__ == '__main__':
    main()
