"""Migration 2026-05-27: snapshot freeze MOV/SIST em inventario_snapshot_odoo.

Adiciona 5 colunas Numeric(15,3) NULL DEFAULT 0:
  - mov_compras, mov_vendas, mov_consumo, mov_producao  (filtrado >= data_snapshot)
  - mov_sist_total                                       (sum total ATIVO sem filtro data)

Motivacao: ate hoje ConfrontoService lia MovimentacaoEstoque LIVE a cada GET,
gerando ODOO-MOV inconsistente (ODOO snapshot T0 vs MOV agora T1). Freeze grava
MOV no mesmo T0 do snapshot Odoo. AJ continua live (justificativa em models.py).

Idempotente: detecta colunas existentes via information_schema antes de adicionar.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


COLUNAS = [
    'mov_compras',
    'mov_vendas',
    'mov_consumo',
    'mov_producao',
    'mov_sist_total',
]


def colunas_existentes():
    rows = db.session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='inventario_snapshot_odoo'"
    )).all()
    return {r[0] for r in rows}


def main():
    app = create_app()
    with app.app_context():
        existing = colunas_existentes()
        print(f"[BEFORE] colunas inventario_snapshot_odoo: {len(existing)}")
        faltando = [c for c in COLUNAS if c not in existing]
        if not faltando:
            print("[SKIP] todas as 5 colunas mov_* ja existem — nada a fazer")
            return 0

        print(f"[ADD] colunas a adicionar: {faltando}")
        for col in faltando:
            db.session.execute(text(
                f"ALTER TABLE inventario_snapshot_odoo "
                f"ADD COLUMN IF NOT EXISTS {col} NUMERIC(15,3) DEFAULT 0"
            ))
        db.session.commit()

        after = colunas_existentes()
        print(f"[AFTER] colunas inventario_snapshot_odoo: {len(after)}")
        for col in COLUNAS:
            status = "OK" if col in after else "FAIL"
            print(f"  - {col}: {status}")

        ok = all(c in after for c in COLUNAS)
        return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
