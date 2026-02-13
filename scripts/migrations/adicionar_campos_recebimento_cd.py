"""
Migration: Adicionar campos de Recebimento CD via DFe (Fase 7)

Tabela: recebimento_lf
Campos novos: odoo_cd_dfe_id, odoo_cd_po_id, odoo_cd_po_name,
              odoo_cd_invoice_id, odoo_cd_invoice_name

Executar:
    source .venv/bin/activate && python scripts/migrations/adicionar_campos_recebimento_cd.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def main():
    app = create_app()
    with app.app_context():
        # ============================
        # BEFORE: Verificar estado atual
        # ============================
        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'recebimento_lf'
                AND column_name IN (
                    'odoo_cd_dfe_id', 'odoo_cd_po_id', 'odoo_cd_po_name',
                    'odoo_cd_invoice_id', 'odoo_cd_invoice_name'
                )
                ORDER BY column_name
            """))
            existing = [row[0] for row in result]
            print(f"[BEFORE] Campos CD existentes: {existing or 'NENHUM'}")

            result2 = conn.execute(db.text("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = 'recebimento_lf'
                AND column_name = 'total_etapas'
            """))
            row = result2.fetchone()
            default_val = row[0] if row else 'N/A'
            print(f"[BEFORE] total_etapas default: {default_val}")

        # ============================
        # EXECUTE: Aplicar DDL
        # ============================
        with db.engine.begin() as conn:
            # Novos campos
            campos = [
                ("odoo_cd_dfe_id", "INTEGER"),
                ("odoo_cd_po_id", "INTEGER"),
                ("odoo_cd_po_name", "VARCHAR(50)"),
                ("odoo_cd_invoice_id", "INTEGER"),
                ("odoo_cd_invoice_name", "VARCHAR(50)"),
            ]
            for campo, tipo in campos:
                conn.execute(db.text(f"""
                    ALTER TABLE recebimento_lf
                    ADD COLUMN IF NOT EXISTS {campo} {tipo}
                """))
                print(f"  + Campo {campo} ({tipo}) adicionado/verificado")

            # Atualizar total_etapas para registros pendentes
            result = conn.execute(db.text("""
                UPDATE recebimento_lf
                SET total_etapas = 37
                WHERE transfer_status IS NULL
                   OR transfer_status IN ('pendente', 'erro')
                   OR (transfer_status = 'processando' AND etapa_atual < 24)
            """))
            print(f"  ~ total_etapas atualizado para 37 em {result.rowcount} registros pendentes")

            # Resetar etapa_atual para registros nas etapas antigas 24-25
            result2 = conn.execute(db.text("""
                UPDATE recebimento_lf
                SET etapa_atual = 23
                WHERE etapa_atual IN (24, 25)
                  AND (transfer_status IS NULL
                       OR transfer_status NOT IN ('concluido', 'sem_transferencia'))
            """))
            print(f"  ~ etapa_atual resetada para 23 em {result2.rowcount} registros (antigo fluxo)")

            # Default para novos registros
            conn.execute(db.text("""
                ALTER TABLE recebimento_lf
                ALTER COLUMN total_etapas SET DEFAULT 37
            """))
            print("  ~ total_etapas default alterado para 37")

        # ============================
        # AFTER: Verificar resultado
        # ============================
        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'recebimento_lf'
                AND column_name IN (
                    'odoo_cd_dfe_id', 'odoo_cd_po_id', 'odoo_cd_po_name',
                    'odoo_cd_invoice_id', 'odoo_cd_invoice_name'
                )
                ORDER BY column_name
            """))
            campos_novos = [(row[0], row[1]) for row in result]
            print(f"\n[AFTER] Campos CD: {campos_novos}")

            result2 = conn.execute(db.text("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = 'recebimento_lf'
                AND column_name = 'total_etapas'
            """))
            row = result2.fetchone()
            default_val = row[0] if row else 'N/A'
            print(f"[AFTER] total_etapas default: {default_val}")

            # Contar registros por total_etapas
            result3 = conn.execute(db.text("""
                SELECT total_etapas, COUNT(*) as cnt
                FROM recebimento_lf
                GROUP BY total_etapas
                ORDER BY total_etapas
            """))
            print("\n[AFTER] Distribuicao total_etapas:")
            for row in result3:
                print(f"  total_etapas={row[0]}: {row[1]} registros")

        print("\n[OK] Migration concluida com sucesso!")


if __name__ == '__main__':
    main()
