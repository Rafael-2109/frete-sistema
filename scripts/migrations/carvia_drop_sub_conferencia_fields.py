"""Migration: DROP campos de conferencia em carvia_subcontratos.

DEVE ser executada APOS todas as migrations do plano e deploy do codigo.
Idempotente via IF EXISTS.

Data: 2026-04-14
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


CAMPOS_SUB = [
    'valor_pago', 'valor_pago_em', 'valor_pago_por',
    'valor_considerado',
    'status_conferencia', 'conferido_por', 'conferido_em',
    'detalhes_conferencia', 'requer_aprovacao',
]

CAMPOS_CC = [
    'subcontrato_id',
    'compensacao_subcontrato_id',
]


def run_migration():
    print("=" * 70)
    print("MIGRATION: DROP campos obsoletos")
    print("=" * 70)

    print("1. Drop campos em carvia_subcontratos")
    for campo in CAMPOS_SUB:
        sql = f"ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS {campo}"
        print(f"  {sql}")
        db.session.execute(text(sql))

    print("2. Drop campos em carvia_conta_corrente_transportadoras")
    for campo in CAMPOS_CC:
        sql = f"ALTER TABLE carvia_conta_corrente_transportadoras DROP COLUMN IF EXISTS {campo}"
        print(f"  {sql}")
        db.session.execute(text(sql))

    db.session.commit()
    print()
    print("DROP concluido.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_migration()
