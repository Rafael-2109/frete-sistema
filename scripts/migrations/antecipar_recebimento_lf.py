"""
Migration: Antecipar Recebimento LF
====================================
Adiciona campo odoo_lf_invoice_id e torna odoo_dfe_id nullable na tabela recebimento_lf.

Contexto: NFs emitidas pela LF passam a ser indice primario de "NFs a receber",
sem depender do DFe aparecer na FB (ate 2h de atraso SEFAZ).

Padrao: 3 blocos with separados (MEMORY.md: Padrao de Migrations Python)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        # =====================================================
        # BEFORE: Verificar estado atual
        # =====================================================
        with db.engine.connect() as conn:
            # Verificar se coluna odoo_lf_invoice_id ja existe
            result = conn.execute(db.text("""
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'recebimento_lf'
                  AND column_name IN ('odoo_dfe_id', 'odoo_lf_invoice_id')
                ORDER BY column_name
            """))
            columns = {row[0]: row[1] for row in result}

            has_lf_invoice_id = 'odoo_lf_invoice_id' in columns
            dfe_id_nullable = columns.get('odoo_dfe_id') == 'YES'

            print(f"BEFORE:")
            print(f"  odoo_lf_invoice_id existe: {has_lf_invoice_id}")
            print(f"  odoo_dfe_id nullable: {dfe_id_nullable}")

            if has_lf_invoice_id and dfe_id_nullable:
                print("\n  Migration ja aplicada. Nada a fazer.")
                return

        # =====================================================
        # EXECUTE: Aplicar DDL (auto-commit via engine.begin)
        # =====================================================
        with db.engine.begin() as conn:
            if not has_lf_invoice_id:
                print("\n  Adicionando coluna odoo_lf_invoice_id...")
                conn.execute(db.text(
                    "ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_lf_invoice_id INTEGER"
                ))
                conn.execute(db.text(
                    "CREATE INDEX IF NOT EXISTS ix_recebimento_lf_odoo_lf_invoice_id "
                    "ON recebimento_lf (odoo_lf_invoice_id)"
                ))
                print("  OK: odoo_lf_invoice_id adicionado com indice")

            if not dfe_id_nullable:
                print("\n  Tornando odoo_dfe_id nullable...")
                conn.execute(db.text(
                    "ALTER TABLE recebimento_lf ALTER COLUMN odoo_dfe_id DROP NOT NULL"
                ))
                print("  OK: odoo_dfe_id agora nullable")

        # =====================================================
        # AFTER: Verificar resultado
        # =====================================================
        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT column_name, is_nullable, data_type
                FROM information_schema.columns
                WHERE table_name = 'recebimento_lf'
                  AND column_name IN ('odoo_dfe_id', 'odoo_lf_invoice_id')
                ORDER BY column_name
            """))
            print("\nAFTER:")
            for row in result:
                print(f"  {row[0]}: nullable={row[1]}, type={row[2]}")

            # Verificar indice
            idx_result = conn.execute(db.text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'recebimento_lf'
                  AND indexname = 'ix_recebimento_lf_odoo_lf_invoice_id'
            """))
            idx_exists = idx_result.fetchone() is not None
            print(f"  indice ix_recebimento_lf_odoo_lf_invoice_id: {'OK' if idx_exists else 'FALTANDO'}")

        print("\nMigration concluida com sucesso!")


if __name__ == '__main__':
    main()
