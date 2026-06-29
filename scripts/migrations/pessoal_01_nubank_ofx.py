"""Migration Pessoal 01: suporte a Nubank (OFX) — contas + casamento de transferencias.

Mudancas:
1. pessoal_contas.numero_conta: VARCHAR(30) -> VARCHAR(50)
   (comporta o ACCTID UUID do cartao Nubank, ex.: "5f00ffaf-...-6ef2b15baa39", 36 chars).
2. pessoal_transacoes.transferencia_par_id: nova coluna self-FK (ON DELETE SET NULL)
   que casa as duas pontas de um deposito entre contas proprias (Bradesco <-> Nubank).
3. Indice parcial em transferencia_par_id.

Idempotente — pode rodar 2x (IF NOT EXISTS / ALTER TYPE re-aplicavel).

Uso:
    python scripts/migrations/pessoal_01_nubank_ofx.py            # banco local (DATABASE_URL)
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/pessoal_01_nubank_ofx.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE pessoal_contas ALTER COLUMN numero_conta TYPE VARCHAR(50)",
    "ALTER TABLE pessoal_transacoes ADD COLUMN IF NOT EXISTS transferencia_par_id INTEGER",
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_pessoal_transacoes_transferencia_par'
        ) THEN
            ALTER TABLE pessoal_transacoes
                ADD CONSTRAINT fk_pessoal_transacoes_transferencia_par
                FOREIGN KEY (transferencia_par_id)
                REFERENCES pessoal_transacoes (id) ON DELETE SET NULL;
        END IF;
    END$$;
    """,
    "CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_transf_par "
    "ON pessoal_transacoes (transferencia_par_id) "
    "WHERE transferencia_par_id IS NOT NULL",
]


def _colunas(tabela: str) -> dict:
    return {c['name']: c for c in inspect(db.engine).get_columns(tabela)}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        cols_contas = _colunas('pessoal_contas')
        cols_tx = _colunas('pessoal_transacoes')
        numero_len = getattr(cols_contas.get('numero_conta', {}).get('type'), 'length', None)
        print('Estado antes:')
        print(f"  pessoal_contas.numero_conta length = {numero_len}")
        print(f"  pessoal_transacoes.transferencia_par_id existe? {'transferencia_par_id' in cols_tx}")

        for ddl in SQL_DDL:
            db.session.execute(text(ddl))
        db.session.commit()

        cols_contas = _colunas('pessoal_contas')
        cols_tx = _colunas('pessoal_transacoes')
        numero_len = getattr(cols_contas.get('numero_conta', {}).get('type'), 'length', None)
        print('Estado depois:')
        print(f"  pessoal_contas.numero_conta length = {numero_len}")
        print(f"  pessoal_transacoes.transferencia_par_id existe? {'transferencia_par_id' in cols_tx}")
        print('OK.')


if __name__ == '__main__':
    main()
