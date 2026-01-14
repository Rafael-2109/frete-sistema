"""
Migration: Adicionar campos de identificacao da NF e localizacao do fornecedor
===============================================================================

Campos adicionados:
- numero_nf: Numero da NF (nfe_infnfe_ide_nnf)
- serie_nf: Serie da NF (nfe_infnfe_ide_serie)
- chave_nfe: Chave de acesso NF-e (protnfe_infnfe_chnfe)
- uf_fornecedor: UF do fornecedor (nfe_infnfe_emit_uf)
- cidade_fornecedor: Cidade do fornecedor (res.partner.city)

Tabelas afetadas:
- cadastro_primeira_compra
- divergencia_fiscal

Executar:
    source .venv/bin/activate && python scripts/migrations/adicionar_dados_nf_validacao.py
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
            print("=== MIGRATION: Adicionar campos de identificacao da NF ===\n")

            # =====================================================================
            # TABELA: cadastro_primeira_compra
            # =====================================================================
            print(">>> cadastro_primeira_compra:")

            # numero_nf
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS numero_nf VARCHAR(20)
                """))
                print("   ✓ numero_nf")
            except Exception as e:
                print(f"   ⚠ numero_nf: {e}")

            # serie_nf
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS serie_nf VARCHAR(5)
                """))
                print("   ✓ serie_nf")
            except Exception as e:
                print(f"   ⚠ serie_nf: {e}")

            # chave_nfe
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS chave_nfe VARCHAR(44)
                """))
                print("   ✓ chave_nfe")
            except Exception as e:
                print(f"   ⚠ chave_nfe: {e}")

            # uf_fornecedor
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS uf_fornecedor VARCHAR(2)
                """))
                print("   ✓ uf_fornecedor")
            except Exception as e:
                print(f"   ⚠ uf_fornecedor: {e}")

            # cidade_fornecedor
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS cidade_fornecedor VARCHAR(100)
                """))
                print("   ✓ cidade_fornecedor")
            except Exception as e:
                print(f"   ⚠ cidade_fornecedor: {e}")

            # =====================================================================
            # TABELA: divergencia_fiscal
            # =====================================================================
            print("\n>>> divergencia_fiscal:")

            # numero_nf
            try:
                db.session.execute(text("""
                    ALTER TABLE divergencia_fiscal
                    ADD COLUMN IF NOT EXISTS numero_nf VARCHAR(20)
                """))
                print("   ✓ numero_nf")
            except Exception as e:
                print(f"   ⚠ numero_nf: {e}")

            # serie_nf
            try:
                db.session.execute(text("""
                    ALTER TABLE divergencia_fiscal
                    ADD COLUMN IF NOT EXISTS serie_nf VARCHAR(5)
                """))
                print("   ✓ serie_nf")
            except Exception as e:
                print(f"   ⚠ serie_nf: {e}")

            # chave_nfe
            try:
                db.session.execute(text("""
                    ALTER TABLE divergencia_fiscal
                    ADD COLUMN IF NOT EXISTS chave_nfe VARCHAR(44)
                """))
                print("   ✓ chave_nfe")
            except Exception as e:
                print(f"   ⚠ chave_nfe: {e}")

            # uf_fornecedor
            try:
                db.session.execute(text("""
                    ALTER TABLE divergencia_fiscal
                    ADD COLUMN IF NOT EXISTS uf_fornecedor VARCHAR(2)
                """))
                print("   ✓ uf_fornecedor")
            except Exception as e:
                print(f"   ⚠ uf_fornecedor: {e}")

            # cidade_fornecedor
            try:
                db.session.execute(text("""
                    ALTER TABLE divergencia_fiscal
                    ADD COLUMN IF NOT EXISTS cidade_fornecedor VARCHAR(100)
                """))
                print("   ✓ cidade_fornecedor")
            except Exception as e:
                print(f"   ⚠ cidade_fornecedor: {e}")

            db.session.commit()
            print("\n✅ Migration concluida com sucesso!")

            # Mostrar SQL para executar no Render
            print("\n" + "="*60)
            print("SQL PARA EXECUTAR NO RENDER (Shell PostgreSQL):")
            print("="*60)
            print("""
-- cadastro_primeira_compra
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS numero_nf VARCHAR(20);
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS serie_nf VARCHAR(5);
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS chave_nfe VARCHAR(44);
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS uf_fornecedor VARCHAR(2);
ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS cidade_fornecedor VARCHAR(100);

-- divergencia_fiscal
ALTER TABLE divergencia_fiscal ADD COLUMN IF NOT EXISTS numero_nf VARCHAR(20);
ALTER TABLE divergencia_fiscal ADD COLUMN IF NOT EXISTS serie_nf VARCHAR(5);
ALTER TABLE divergencia_fiscal ADD COLUMN IF NOT EXISTS chave_nfe VARCHAR(44);
ALTER TABLE divergencia_fiscal ADD COLUMN IF NOT EXISTS uf_fornecedor VARCHAR(2);
ALTER TABLE divergencia_fiscal ADD COLUMN IF NOT EXISTS cidade_fornecedor VARCHAR(100);
            """)

        except Exception as e:
            print(f"\n❌ Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
