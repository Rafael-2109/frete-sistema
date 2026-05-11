"""
Backfill de KG links para memórias sem entidades vinculadas.

Roda extract_and_link_entities sobre memórias que ainda não têm entrada
em agent_memory_entity_links — alvo: subir KG coverage de ~43% para >70%.

Idempotente: re-execução pula memórias já linkadas (filtro `NOT EXISTS`).

Uso (local ou Render Shell):
    python scripts/maintenance/backfill_kg_links.py             # dry-run
    python scripts/maintenance/backfill_kg_links.py --apply     # processa
    python scripts/maintenance/backfill_kg_links.py --apply --limit 50  # batch

Custo estimado: ~$0.02-0.05 (Voyage $0.0001/memória, regex zero, Sonnet skipped em batch).
Tempo: ~5-10 minutos para 189 memórias (3s timeout Voyage por mem).
"""
import argparse
import logging
import sys
import time
from pathlib import Path

# sys.path setup obrigatorio para scripts em scripts/maintenance/
# Ver memory/feedback_migration_sys_path.md
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app, db
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger('backfill_kg')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--apply', action='store_true',
        help='Aplicar (sem esta flag, apenas mostra o que seria feito).'
    )
    parser.add_argument(
        '--limit', type=int, default=None,
        help='Limitar processamento a N memórias (útil para testar).'
    )
    parser.add_argument(
        '--min-content', type=int, default=100,
        help='Tamanho mínimo de content para tentar extração (default 100).'
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Identificar candidates: memórias sem link KG
        query = """
            SELECT m.id, m.user_id, LENGTH(m.content) as len
            FROM agent_memories m
            WHERE m.is_directory = false
              AND LENGTH(m.content) >= :min_content
              AND NOT EXISTS (
                  SELECT 1 FROM agent_memory_entity_links l
                  WHERE l.memory_id = m.id
              )
            ORDER BY LENGTH(m.content) DESC
        """
        if args.limit:
            query += f" LIMIT {int(args.limit)}"

        rows = db.session.execute(
            text(query), {'min_content': args.min_content}
        ).fetchall()

        total = len(rows)
        logger.info(f'Candidatos a backfill: {total} memórias')

        if not args.apply:
            logger.info('[DRY-RUN] Sem --apply, nada será modificado.')
            logger.info(f'Para processar: python {sys.argv[0]} --apply')
            return

        # Importação lazy (precisa do app context)
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
        )
        from app.agente.models import AgentMemory

        ok_count = 0
        empty_count = 0
        error_count = 0
        total_entities = 0
        total_links = 0
        total_relations = 0
        t_start = time.time()

        for i, row in enumerate(rows, start=1):
            memory_id = row.id
            user_id = row.user_id

            try:
                mem = AgentMemory.query.get(memory_id)
                if not mem or not mem.content:
                    empty_count += 1
                    continue

                stats = extract_and_link_entities(
                    user_id=user_id,
                    memory_id=memory_id,
                    content=mem.content,
                    haiku_entities=None,  # sem LLM em batch
                    haiku_relations=None,
                )

                ec = stats.get('entities_count', 0)
                lc = stats.get('links_count', 0)
                rc = stats.get('relations_count', 0)
                total_entities += ec
                total_links += lc
                total_relations += rc

                if lc > 0:
                    ok_count += 1
                else:
                    empty_count += 1

                if i % 10 == 0:
                    elapsed = time.time() - t_start
                    rate = i / elapsed
                    eta = (total - i) / rate if rate > 0 else 0
                    logger.info(
                        f'  [{i}/{total}] ok={ok_count} vazias={empty_count} '
                        f'erros={error_count} | ETA {eta:.0f}s'
                    )

            except Exception as e:
                error_count += 1
                logger.warning(f'  [mem_id={memory_id}] erro: {e}')

        elapsed = time.time() - t_start
        logger.info('=' * 60)
        logger.info(f'BACKFILL CONCLUIDO em {elapsed:.0f}s')
        logger.info(f'  Memórias processadas: {total}')
        logger.info(f'  Com novas entidades:  {ok_count}')
        logger.info(f'  Sem entidades novas:  {empty_count}')
        logger.info(f'  Erros:                {error_count}')
        logger.info(f'  Total entidades:      {total_entities}')
        logger.info(f'  Total links:          {total_links}')
        logger.info(f'  Total relations:      {total_relations}')

        # Snapshot pós-backfill
        coverage = db.session.execute(text("""
            SELECT
                COUNT(DISTINCT memory_id) as mems_linkadas,
                (SELECT COUNT(*) FROM agent_memories WHERE is_directory = false) as total
            FROM agent_memory_entity_links
        """)).fetchone()
        if coverage and coverage.total:
            pct = coverage.mems_linkadas * 100.0 / coverage.total
            logger.info(f'  COVERAGE POS-BACKFILL: {pct:.2f}% '
                        f'({coverage.mems_linkadas}/{coverage.total})')


if __name__ == '__main__':
    main()
