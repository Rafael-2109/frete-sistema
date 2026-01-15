"""
Migration: Adicionar campos de quantidade e valor em cadastro_primeira_compra
=============================================================================

Campos que faltavam na tela de validação:
- quantidade (det_prod_qcom)
- unidade_medida (det_prod_ucom)
- valor_unitario (det_prod_vuncom)
- valor_total (det_prod_vprod)
- valor_icms (det_imposto_icms_vicms)
- valor_icms_st (det_imposto_icms_vicmsst)
- valor_ipi (det_imposto_ipi_vipi)

Executar:
    source .venv/bin/activate && python scripts/migrations/adicionar_qtd_valor_primeira_compra.py
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
            print("=== MIGRATION: Adicionar campos QTD/VALOR em cadastro_primeira_compra ===\n")

            # Quantidade
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS quantidade NUMERIC(15,4)
                """))
                print("   ✓ quantidade")
            except Exception as e:
                print(f"   ⚠ quantidade: {e}")

            # Unidade de medida
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS unidade_medida VARCHAR(10)
                """))
                print("   ✓ unidade_medida")
            except Exception as e:
                print(f"   ⚠ unidade_medida: {e}")

            # Valor unitario
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS valor_unitario NUMERIC(15,4)
                """))
                print("   ✓ valor_unitario")
            except Exception as e:
                print(f"   ⚠ valor_unitario: {e}")

            # Valor total
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS valor_total NUMERIC(15,2)
                """))
                print("   ✓ valor_total")
            except Exception as e:
                print(f"   ⚠ valor_total: {e}")

            # Valor ICMS
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS valor_icms NUMERIC(15,2)
                """))
                print("   ✓ valor_icms")
            except Exception as e:
                print(f"   ⚠ valor_icms: {e}")

            # Valor ICMS ST
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS valor_icms_st NUMERIC(15,2)
                """))
                print("   ✓ valor_icms_st")
            except Exception as e:
                print(f"   ⚠ valor_icms_st: {e}")

            # Valor IPI
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS valor_ipi NUMERIC(15,2)
                """))
                print("   ✓ valor_ipi")
            except Exception as e:
                print(f"   ⚠ valor_ipi: {e}")

            # Valor tributos aproximados
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS valor_tributos_aprox NUMERIC(15,2)
                """))
                print("   ✓ valor_tributos_aprox")
            except Exception as e:
                print(f"   ⚠ valor_tributos_aprox: {e}")

            # Info complementar
            try:
                db.session.execute(text("""
                    ALTER TABLE cadastro_primeira_compra
                    ADD COLUMN IF NOT EXISTS info_complementar TEXT
                """))
                print("   ✓ info_complementar")
            except Exception as e:
                print(f"   ⚠ info_complementar: {e}")

            db.session.commit()
            print("\n✅ Migration concluida com sucesso!")

        except Exception as e:
            print(f"\n❌ Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()


""" 
                    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS quantidade NUMERIC(15,4);
                    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS unidade_medida VARCHAR(10);
                    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS valor_unitario NUMERIC(15,4);
                    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS valor_total NUMERIC(15,2);
                    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS valor_icms NUMERIC(15,2);
                    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS valor_icms_st NUMERIC(15,2);
                    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS valor_ipi NUMERIC(15,2);
                    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS valor_tributos_aprox NUMERIC(15,2);
                    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS info_complementar TEXT;
"""