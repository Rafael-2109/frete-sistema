"""
Aplicar mapa nCT→CTRC no banco de producao (Render).

Le o mapa JSON gerado pelo backfill_ctrc_ssw.py e atualiza
carvia_operacoes.ctrc_numero no banco Render.

Uso (incluir no hook de deploy ou rodar manualmente):
    source .venv/bin/activate
    python scripts/migrations/apply_ctrc_map_render.py [--dry-run]
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Mapa hardcoded — gerado por backfill_ctrc_ssw.py via varredura SSW
# Formato: nCT (SEFAZ) → CTRC formatado (SSW)
NCT_CTRC_MAP = {}

# Carregar mapa do arquivo JSON se existir
MAP_FILE = os.path.join(os.path.dirname(__file__), 'nct_ctrc_map.json')


def run(dry_run=False):
    from app import create_app, db

    # Carregar mapa
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE) as f:
            nct_map = {int(k): v for k, v in json.load(f).items()}
        logger.info("Mapa carregado de %s: %d entradas", MAP_FILE, len(nct_map))
    elif NCT_CTRC_MAP:
        nct_map = NCT_CTRC_MAP
        logger.info("Usando mapa hardcoded: %d entradas", len(nct_map))
    else:
        logger.error("Nenhum mapa disponivel! Rode backfill_ctrc_ssw.py primeiro.")
        return

    app = create_app()
    with app.app_context():
        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, cte_numero, ctrc_numero
                FROM carvia_operacoes
                WHERE cte_numero IS NOT NULL
                  AND cte_numero ~ '^\\d+$'
                ORDER BY id
            """)
            rows = cursor.fetchall()
            logger.info("Operacoes com cte_numero numerico: %d", len(rows))

            atualizados = 0
            sem_mapa = 0
            ja_corretos = 0

            for op_id, cte_numero, ctrc_atual in rows:
                nct = int(cte_numero)
                ctrc_correto = nct_map.get(nct)

                if not ctrc_correto:
                    sem_mapa += 1
                    continue

                if ctrc_atual == ctrc_correto:
                    ja_corretos += 1
                    continue

                if dry_run:
                    logger.info("  [DRY] op=%d: %s → %s", op_id, ctrc_atual, ctrc_correto)
                else:
                    cursor.execute(
                        "UPDATE carvia_operacoes SET ctrc_numero = %s WHERE id = %s",
                        (ctrc_correto, op_id)
                    )
                atualizados += 1

            if not dry_run:
                conn.commit()

            logger.info(
                "Resultado (%s): %d atualizados, %d ja corretos, %d sem mapa",
                "DRY RUN" if dry_run else "APLICADO",
                atualizados, ja_corretos, sem_mapa
            )

        finally:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run(dry_run=args.dry_run)
