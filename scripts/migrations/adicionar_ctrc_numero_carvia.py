"""
Migration: Adicionar ctrc_numero em carvia_operacoes e carvia_cte_complementares

O CTRC (Conhecimento de Transporte Rodoviario de Cargas) e o identificador oficial
do CTe no SSW/SEFAZ. Formato: CAR-{nCT}-{cDV} (ex: CAR-133-2).

Uso:
    source .venv/bin/activate
    python scripts/migrations/adicionar_ctrc_numero_carvia.py
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        try:
            # Verificar estado antes
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'carvia_operacoes' AND column_name = 'ctrc_numero'
            """)
            exists_op = cursor.fetchone()

            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'carvia_cte_complementares' AND column_name = 'ctrc_numero'
            """)
            exists_comp = cursor.fetchone()

            if exists_op and exists_comp:
                logger.info("Colunas ctrc_numero ja existem em ambas tabelas. Nada a fazer.")
                return

            # Aplicar DDL
            if not exists_op:
                cursor.execute("ALTER TABLE carvia_operacoes ADD COLUMN ctrc_numero VARCHAR(30)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS ix_carvia_operacoes_ctrc_numero "
                    "ON carvia_operacoes(ctrc_numero)"
                )
                logger.info("Coluna ctrc_numero adicionada em carvia_operacoes")

            if not exists_comp:
                cursor.execute("ALTER TABLE carvia_cte_complementares ADD COLUMN ctrc_numero VARCHAR(30)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS ix_carvia_cte_complementares_ctrc_numero "
                    "ON carvia_cte_complementares(ctrc_numero)"
                )
                logger.info("Coluna ctrc_numero adicionada em carvia_cte_complementares")

            conn.commit()

            # Verificar estado depois
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name IN ('carvia_operacoes', 'carvia_cte_complementares')
                AND column_name = 'ctrc_numero'
                ORDER BY table_name
            """)
            results = cursor.fetchall()
            logger.info("Verificacao pos-migration: %s", [r[0] for r in results])
            logger.info("Migration concluida com sucesso.")

        except Exception as e:
            conn.rollback()
            logger.error("Erro na migration: %s", e)
            raise
        finally:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    run()
