"""
Migration: Adicionar Empresa Compradora em tabelas NF-PO
=======================================================
Bug Fix - Fase 1 Validacao Fiscal

Adiciona cnpj_empresa_compradora e razao_empresa_compradora nas tabelas:
1. validacao_nf_po_dfe
2. divergencia_nf_po

Data: 22/01/2026
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            print("Iniciando migration: adicionar_empresa_compradora_nf_po")
            print("=" * 60)

            # 1. Adicionar campos em validacao_nf_po_dfe
            print("\n1. Adicionando campos em validacao_nf_po_dfe...")
            db.session.execute(text("""
                ALTER TABLE validacao_nf_po_dfe
                ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
                ADD COLUMN IF NOT EXISTS razao_empresa_compradora VARCHAR(255);
            """))
            print("   OK: Campos adicionados em validacao_nf_po_dfe")

            # 2. Adicionar campos em divergencia_nf_po
            print("\n2. Adicionando campos em divergencia_nf_po...")
            db.session.execute(text("""
                ALTER TABLE divergencia_nf_po
                ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
                ADD COLUMN IF NOT EXISTS razao_empresa_compradora VARCHAR(255);
            """))
            print("   OK: Campos adicionados em divergencia_nf_po")

            # 3. Criar indices
            print("\n3. Criando indices...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_validacao_nf_po_dfe_cnpj_empresa
                ON validacao_nf_po_dfe(cnpj_empresa_compradora);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_divergencia_nf_po_cnpj_empresa
                ON divergencia_nf_po(cnpj_empresa_compradora);
            """))
            print("   OK: Indices criados")

            db.session.commit()

            # 4. Verificar campos criados
            print("\n4. Verificando campos criados...")
            result = db.session.execute(text("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_name IN ('validacao_nf_po_dfe', 'divergencia_nf_po')
                AND column_name IN ('cnpj_empresa_compradora', 'razao_empresa_compradora')
                ORDER BY table_name, column_name;
            """))
            rows = result.fetchall()
            for row in rows:
                print(f"   {row[0]}.{row[1]} ({row[2]})")

            print("\n" + "=" * 60)
            print("Migration executada com sucesso!")
            print("=" * 60)

        except Exception as e:
            print(f"\nERRO: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
