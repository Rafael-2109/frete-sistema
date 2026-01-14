"""
Migration: Adicionar campos PIS e COFINS nas tabelas de validacao fiscal
=========================================================================

Adiciona campos para PIS e COFINS em:
- perfil_fiscal_produto_fornecedor (baseline)
- cadastro_primeira_compra (validacao manual)

Campos Odoo disponiveis:
- det_imposto_pis_cst (CST PIS)
- det_imposto_pis_ppis (% PIS)
- det_imposto_pis_vbc (BC PIS)
- det_imposto_cofins_cst (CST COFINS)
- det_imposto_cofins_pcofins (% COFINS)
- det_imposto_cofins_vbc (BC COFINS)

Executar:
    source .venv/bin/activate && python scripts/migrations/adicionar_pis_cofins_validacao_fiscal.py
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
            print("=== MIGRATION: Adicionar campos PIS/COFINS ===\n")

            # ===================================================================
            # 1. perfil_fiscal_produto_fornecedor
            # ===================================================================
            print("1. Adicionando campos em perfil_fiscal_produto_fornecedor...")

            # CST PIS
            try:
                db.session.execute(text("""
                    ALTER TABLE perfil_fiscal_produto_fornecedor
                    ADD COLUMN IF NOT EXISTS cst_pis_esperado VARCHAR(5)
                """))
                print("   ✓ cst_pis_esperado")
            except Exception as e:
                print(f"   ⚠ cst_pis_esperado: {e}")

            # Aliquota PIS
            try:
                db.session.execute(text("""
                    ALTER TABLE perfil_fiscal_produto_fornecedor
                    ADD COLUMN IF NOT EXISTS aliquota_pis_esperada NUMERIC(5,2)
                """))
                print("   ✓ aliquota_pis_esperada")
            except Exception as e:
                print(f"   ⚠ aliquota_pis_esperada: {e}")

            # CST COFINS
            try:
                db.session.execute(text("""
                    ALTER TABLE perfil_fiscal_produto_fornecedor
                    ADD COLUMN IF NOT EXISTS cst_cofins_esperado VARCHAR(5)
                """))
                print("   ✓ cst_cofins_esperado")
            except Exception as e:
                print(f"   ⚠ cst_cofins_esperado: {e}")

            # Aliquota COFINS
            try:
                db.session.execute(text("""
                    ALTER TABLE perfil_fiscal_produto_fornecedor
                    ADD COLUMN IF NOT EXISTS aliquota_cofins_esperada NUMERIC(5,2)
                """))
                print("   ✓ aliquota_cofins_esperada")
            except Exception as e:
                print(f"   ⚠ aliquota_cofins_esperada: {e}")

            # ===================================================================
            # 2. cadastro_primeira_compra
            # ===================================================================
            print("\n2. Adicionando campos em cadastro_primeira_compra...")

            # CST PIS
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS cst_pis VARCHAR(5)
                """))
                print("   ✓ cst_pis")
            except Exception as e:
                print(f"   ⚠ cst_pis: {e}")

            # Aliquota PIS
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS aliquota_pis NUMERIC(5,2)
                """))
                print("   ✓ aliquota_pis")
            except Exception as e:
                print(f"   ⚠ aliquota_pis: {e}")

            # BC PIS
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS bc_pis NUMERIC(15,2)
                """))
                print("   ✓ bc_pis")
            except Exception as e:
                print(f"   ⚠ bc_pis: {e}")

            # CST COFINS
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS cst_cofins VARCHAR(5)
                """))
                print("   ✓ cst_cofins")
            except Exception as e:
                print(f"   ⚠ cst_cofins: {e}")

            # Aliquota COFINS
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS aliquota_cofins NUMERIC(5,2)
                """))
                print("   ✓ aliquota_cofins")
            except Exception as e:
                print(f"   ⚠ aliquota_cofins: {e}")

            # BC COFINS
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS bc_cofins NUMERIC(15,2)
                """))
                print("   ✓ bc_cofins")
            except Exception as e:
                print(f"   ⚠ bc_cofins: {e}")

            db.session.commit()
            print("\n✅ Migration concluida com sucesso!")

        except Exception as e:
            print(f"\n❌ Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
