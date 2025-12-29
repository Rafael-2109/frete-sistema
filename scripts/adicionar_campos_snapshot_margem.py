"""
Script para adicionar campos de snapshot de parametros de margem.

Novos campos:
- frete_percentual_snapshot
- custo_financeiro_pct_snapshot
- custo_operacao_pct_snapshot
- percentual_perda_snapshot

Uso:
    source .venv/bin/activate
    python scripts/adicionar_campos_snapshot_margem.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def adicionar_campos():
    """
    Adiciona campos de snapshot de parametros na CarteiraPrincipal.
    """
    app = create_app()
    with app.app_context():
        try:
            # Verificar quais campos ja existem
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'carteira_principal'
                AND column_name IN (
                    'frete_percentual_snapshot',
                    'custo_financeiro_pct_snapshot',
                    'custo_operacao_pct_snapshot',
                    'percentual_perda_snapshot'
                )
            """))
            campos_existentes = [row[0] for row in result]
            logger.info(f"Campos ja existentes: {campos_existentes}")

            campos_adicionar = []

            if 'frete_percentual_snapshot' not in campos_existentes:
                campos_adicionar.append(
                    "ADD COLUMN frete_percentual_snapshot NUMERIC(5, 2)"
                )

            if 'custo_financeiro_pct_snapshot' not in campos_existentes:
                campos_adicionar.append(
                    "ADD COLUMN custo_financeiro_pct_snapshot NUMERIC(5, 2)"
                )

            if 'custo_operacao_pct_snapshot' not in campos_existentes:
                campos_adicionar.append(
                    "ADD COLUMN custo_operacao_pct_snapshot NUMERIC(5, 2)"
                )

            if 'percentual_perda_snapshot' not in campos_existentes:
                campos_adicionar.append(
                    "ADD COLUMN percentual_perda_snapshot NUMERIC(5, 2)"
                )

            if not campos_adicionar:
                logger.info("Todos os campos ja existem. Nada a fazer.")
                return

            sql = f"ALTER TABLE carteira_principal {', '.join(campos_adicionar)}"
            logger.info(f"Executando: {sql}")

            db.session.execute(text(sql))
            db.session.commit()

            logger.info("=" * 60)
            logger.info("CAMPOS ADICIONADOS COM SUCESSO!")
            logger.info("=" * 60)
            for campo in campos_adicionar:
                logger.info(f"  - {campo}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao adicionar campos: {e}")
            raise


if __name__ == '__main__':
    adicionar_campos()
