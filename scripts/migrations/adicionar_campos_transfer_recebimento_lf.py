"""
Migration: Adicionar campos de transferencia FB -> CD no Recebimento LF
Data: 2026-02-11
Contexto: Apos receber NF da LF na FB, transferir produtos acabados para o CD

Novos campos:
- recebimento_lf: 8 campos (picking out, invoice, picking in, transfer_status, erro)
- recebimento_lf_lote: 1 campo (odoo_lot_id_cd)
- total_etapas: default alterado de 18 para 26

Uso: python scripts/migrations/adicionar_campos_transfer_recebimento_lf.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    app = create_app()
    with app.app_context():
        # =============================================
        # BEFORE: verificar estado atual (conexao read-only)
        # =============================================
        print("=== BEFORE ===")

        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'recebimento_lf'
                ORDER BY ordinal_position
            """))
            cols_lf = [row[0] for row in result]
            print(f"recebimento_lf: {len(cols_lf)} colunas")
            print(f"  transfer_status existe: {'transfer_status' in cols_lf}")

            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'recebimento_lf_lote'
                ORDER BY ordinal_position
            """))
            cols_lote = [row[0] for row in result]
            print(f"recebimento_lf_lote: {len(cols_lote)} colunas")
            print(f"  odoo_lot_id_cd existe: {'odoo_lot_id_cd' in cols_lote}")

            result = conn.execute(text("""
                SELECT column_default FROM information_schema.columns
                WHERE table_name = 'recebimento_lf' AND column_name = 'total_etapas'
            """))
            row = result.fetchone()
            print(f"  total_etapas default: {row[0] if row else 'N/A'}")

            result = conn.execute(text("""
                SELECT COUNT(*) FROM recebimento_lf
                WHERE status = 'pendente' AND total_etapas = 18
            """))
            count_pendentes = result.scalar()
            print(f"  Pendentes com total_etapas=18: {count_pendentes}")

        # =============================================
        # EXECUTE: aplicar alteracoes (conexao com commit)
        # =============================================
        print("\n=== EXECUTANDO MIGRATION ===")

        with db.engine.begin() as conn:
            # recebimento_lf: campos de transferencia
            campos_lf = [
                ("odoo_transfer_out_picking_id", "INTEGER"),
                ("odoo_transfer_out_picking_name", "VARCHAR(50)"),
                ("odoo_transfer_invoice_id", "INTEGER"),
                ("odoo_transfer_invoice_name", "VARCHAR(50)"),
                ("odoo_transfer_in_picking_id", "INTEGER"),
                ("odoo_transfer_in_picking_name", "VARCHAR(50)"),
                ("transfer_status", "VARCHAR(20)"),
                ("transfer_erro_mensagem", "TEXT"),
            ]

            for col_name, col_type in campos_lf:
                if col_name not in cols_lf:
                    conn.execute(text(
                        f"ALTER TABLE recebimento_lf ADD COLUMN {col_name} {col_type}"
                    ))
                    print(f"  + recebimento_lf.{col_name} ({col_type})")
                else:
                    print(f"  = recebimento_lf.{col_name} (ja existe)")

            # recebimento_lf_lote: lot ID no CD
            if 'odoo_lot_id_cd' not in cols_lote:
                conn.execute(text(
                    "ALTER TABLE recebimento_lf_lote ADD COLUMN odoo_lot_id_cd INTEGER"
                ))
                print("  + recebimento_lf_lote.odoo_lot_id_cd (INTEGER)")
            else:
                print("  = recebimento_lf_lote.odoo_lot_id_cd (ja existe)")

            # Atualizar default total_etapas
            conn.execute(text(
                "ALTER TABLE recebimento_lf ALTER COLUMN total_etapas SET DEFAULT 26"
            ))
            print("  ~ total_etapas DEFAULT -> 26")

            # Atualizar registros pendentes
            result = conn.execute(text(
                "UPDATE recebimento_lf SET total_etapas = 26 "
                "WHERE status = 'pendente' AND total_etapas = 18"
            ))
            print(f"  ~ {result.rowcount} registros pendentes atualizados para total_etapas=26")

        # engine.begin() faz auto-commit ao sair do with
        print("\n  COMMIT OK")

        # =============================================
        # AFTER: verificar resultado (conexao NOVA)
        # =============================================
        print("\n=== AFTER ===")

        with db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'recebimento_lf'
                ORDER BY ordinal_position
            """))
            cols_lf_after = [row[0] for row in result]
            print(f"recebimento_lf: {len(cols_lf_after)} colunas ({len(cols_lf_after) - len(cols_lf)} novas)")

            novos = [c for c in cols_lf_after if c.startswith('transfer_') or c.startswith('odoo_transfer_')]
            print(f"  Campos transfer: {novos}")

            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'recebimento_lf_lote'
                ORDER BY ordinal_position
            """))
            cols_lote_after = [row[0] for row in result]
            print(f"recebimento_lf_lote: {len(cols_lote_after)} colunas ({len(cols_lote_after) - len(cols_lote)} novas)")

            result = conn.execute(text("""
                SELECT column_default FROM information_schema.columns
                WHERE table_name = 'recebimento_lf' AND column_name = 'total_etapas'
            """))
            row = result.fetchone()
            print(f"  total_etapas default: {row[0] if row else 'N/A'}")

        print("\n=== MIGRATION CONCLUIDA ===")


if __name__ == '__main__':
    run_migration()
