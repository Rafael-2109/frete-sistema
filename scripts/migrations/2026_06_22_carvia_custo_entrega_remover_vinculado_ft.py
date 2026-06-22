"""Migration de DADOS: status VINCULADO_FT -> PENDENTE em carvia_custos_entrega.

O status VINCULADO_FT foi removido (2026-06-22). O vinculo a uma Fatura
Transportadora passa a ser indicado pela FK fatura_transportadora_id; um CE
PENDENTE com FK preenchida = sera pago junto da FT.

Logica SQL em 2026_06_22_carvia_custo_entrega_remover_vinculado_ft.sql (SOT).
Idempotente. Uso:
    python scripts/migrations/2026_06_22_carvia_custo_entrega_remover_vinculado_ft.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402
from app import create_app, db  # noqa: E402

SQL_FILE = os.path.join(
    os.path.dirname(__file__),
    '2026_06_22_carvia_custo_entrega_remover_vinculado_ft.sql',
)


def _contar(status):
    return db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_custos_entrega WHERE status = :s"
    ), {'s': status}).scalar() or 0


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        antes = _contar('VINCULADO_FT')
        print(f'CEs em VINCULADO_FT ANTES: {antes}')

        with open(SQL_FILE, encoding='utf-8') as f:
            db.session.connection().exec_driver_sql(f.read())
        db.session.commit()

        depois = _contar('VINCULADO_FT')
        print(f'CEs em VINCULADO_FT DEPOIS: {depois} (esperado 0)')
        assert depois == 0, 'Ainda ha CEs em VINCULADO_FT apos a migration'
        print(f'OK — {antes} custo(s) migrado(s) para PENDENTE (FK FT preservada).')


if __name__ == '__main__':
    main()
