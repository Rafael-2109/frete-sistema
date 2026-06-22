"""Migration de DADOS: numero_custo 'CE-###' -> numero direto em
carvia_custos_entrega (2026-06-22).

O prefixo 'CE-' so atrapalhava; passa a ser o numero sequencial puro.
Logica SQL em 2026_06_22_carvia_custo_entrega_numero_direto.sql (SOT).
Idempotente. Uso:
    python scripts/migrations/2026_06_22_carvia_custo_entrega_numero_direto.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402
from app import create_app, db  # noqa: E402

SQL_FILE = os.path.join(
    os.path.dirname(__file__),
    '2026_06_22_carvia_custo_entrega_numero_direto.sql',
)


def _contar_prefixados():
    return db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_custos_entrega WHERE numero_custo LIKE 'CE-%'"
    )).scalar() or 0


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        antes = _contar_prefixados()
        print(f"numero_custo com prefixo 'CE-' ANTES: {antes}")

        with open(SQL_FILE, encoding='utf-8') as f:
            db.session.connection().exec_driver_sql(f.read())
        db.session.commit()

        depois = _contar_prefixados()
        print(f"numero_custo com prefixo 'CE-' DEPOIS: {depois}")
        print(f'OK — {antes - depois} custo(s) convertido(s) para numero direto.')


if __name__ == '__main__':
    main()
