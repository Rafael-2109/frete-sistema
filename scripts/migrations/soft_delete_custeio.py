"""
Migration: Soft delete em CustoFrete e ParametroCusteio
Sprint 3 - C17 (auditoria 2026-05-10)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db


DDL = [
    "ALTER TABLE custo_frete ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE NOT NULL",
    "ALTER TABLE custo_frete ADD COLUMN IF NOT EXISTS desativado_em TIMESTAMP NULL",
    "ALTER TABLE custo_frete ADD COLUMN IF NOT EXISTS desativado_por VARCHAR(100) NULL",
    "CREATE INDEX IF NOT EXISTS ix_custo_frete_ativo ON custo_frete(ativo)",
    "ALTER TABLE parametro_custeio ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE NOT NULL",
    "ALTER TABLE parametro_custeio ADD COLUMN IF NOT EXISTS desativado_em TIMESTAMP NULL",
    "ALTER TABLE parametro_custeio ADD COLUMN IF NOT EXISTS desativado_por VARCHAR(100) NULL",
    "CREATE INDEX IF NOT EXISTS ix_parametro_custeio_ativo ON parametro_custeio(ativo)",
]


def run():
    app = create_app()
    with app.app_context():
        for ddl in DDL:
            db.session.execute(db.text(ddl))
            print(f"OK {ddl[:70]}...")
        db.session.commit()
        print("\nMigration soft_delete_custeio aplicada.")


if __name__ == '__main__':
    run()
