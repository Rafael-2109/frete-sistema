"""Migration HORA 40: Origem do pedido (XLSX/IMAGEM/MANUAL) + XLSX gerado em background.

Adiciona 3 colunas em hora_pedido:
    origem                  VARCHAR(20) NOT NULL DEFAULT 'XLSX'
    xlsx_origem_s3_key      VARCHAR(500) NULL
    xlsx_origem_gerado_em   TIMESTAMP NULL

CHECK constraint em origem: ('XLSX', 'IMAGEM', 'MANUAL').

Backfill: distingue MANUAL de XLSX para pedidos legados a partir de
arquivo_origem_s3_key (NULL = MANUAL; preenchido = XLSX).

Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS + DO block para CHECK).

Uso:
    python scripts/migrations/hora_40_pedido_imagem_origem.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


SQL_ADD_COLUNAS = [
    "ALTER TABLE hora_pedido ADD COLUMN IF NOT EXISTS origem VARCHAR(20) NOT NULL DEFAULT 'XLSX';",
    "ALTER TABLE hora_pedido ADD COLUMN IF NOT EXISTS xlsx_origem_s3_key VARCHAR(500);",
    "ALTER TABLE hora_pedido ADD COLUMN IF NOT EXISTS xlsx_origem_gerado_em TIMESTAMP;",
]

SQL_CHECK_CONSTRAINT = """
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'hora_pedido_origem_check'
  ) THEN
    ALTER TABLE hora_pedido
      ADD CONSTRAINT hora_pedido_origem_check
      CHECK (origem IN ('XLSX', 'IMAGEM', 'MANUAL'));
  END IF;
END $$;
"""

SQL_BACKFILL = """
UPDATE hora_pedido
SET origem = 'MANUAL'
WHERE origem = 'XLSX' AND arquivo_origem_s3_key IS NULL;
"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        cols_antes = {c['name'] for c in inspector.get_columns('hora_pedido')}

        print('Estado antes:')
        print(f"  origem em hora_pedido?               {'origem' in cols_antes}")
        print(f"  xlsx_origem_s3_key em hora_pedido?   {'xlsx_origem_s3_key' in cols_antes}")
        print(f"  xlsx_origem_gerado_em em hora_pedido? {'xlsx_origem_gerado_em' in cols_antes}")

        # Conta registros antes para validacao posterior do backfill.
        with db.engine.begin() as conn:
            total_antes = conn.execute(text("SELECT COUNT(*) FROM hora_pedido")).scalar()
            print(f"  total pedidos: {total_antes}")

        with db.engine.begin() as conn:
            for sql in SQL_ADD_COLUNAS:
                conn.execute(text(sql))
            conn.execute(text(SQL_CHECK_CONSTRAINT))
            result = conn.execute(text(SQL_BACKFILL))
            backfill_rows = result.rowcount if hasattr(result, 'rowcount') else None

        inspector = inspect(db.engine)
        cols_depois = {c['name'] for c in inspector.get_columns('hora_pedido')}

        print('\nEstado depois:')
        print(f"  origem em hora_pedido?               {'origem' in cols_depois}")
        print(f"  xlsx_origem_s3_key em hora_pedido?   {'xlsx_origem_s3_key' in cols_depois}")
        print(f"  xlsx_origem_gerado_em em hora_pedido? {'xlsx_origem_gerado_em' in cols_depois}")

        faltantes = {'origem', 'xlsx_origem_s3_key', 'xlsx_origem_gerado_em'} - cols_depois
        if faltantes:
            print(f'\nERRO: colunas nao adicionadas: {faltantes}')
            sys.exit(1)

        # Confere distribuicao por origem apos backfill.
        with db.engine.begin() as conn:
            stats = conn.execute(text(
                "SELECT origem, COUNT(*) FROM hora_pedido GROUP BY origem ORDER BY origem"
            )).fetchall()
            total_depois = conn.execute(text("SELECT COUNT(*) FROM hora_pedido")).scalar()

        print('\nDistribuicao por origem apos backfill:')
        for origem, count in stats:
            print(f'  {origem}: {count}')
        print(f'  total: {total_depois}')

        if total_antes != total_depois:
            print(f'\nERRO: contagem de registros mudou ({total_antes} -> {total_depois})!')
            sys.exit(1)

        print(f'\nBackfill: {backfill_rows} pedidos marcados como MANUAL (sem arquivo_origem_s3_key).')
        print('\nMigration HORA 40 concluida com sucesso.')


if __name__ == '__main__':
    main()
