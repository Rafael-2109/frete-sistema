"""
Migration: Renomear lead_time_mto → lead_time + Adicionar lote_minimo_compra
===========================================================================

Tabela: cadastro_palletizacao
Mudancas:
  1. RENAME COLUMN lead_time_mto → lead_time
  2. ADD COLUMN lote_minimo_compra INTEGER (nullable)
  3. COMMENT nas colunas

Executar com: python scripts/migration_renomear_lead_time_add_lote_minimo.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration: lead_time_mto → lead_time + lote_minimo_compra")
        print("=" * 60)

        try:
            # Verificar estado atual
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'cadastro_palletizacao'
                AND column_name IN ('lead_time_mto', 'lead_time', 'lote_minimo_compra')
                ORDER BY column_name
            """))
            colunas_existentes = [row[0] for row in resultado]
            print(f"\nColunas encontradas: {colunas_existentes}")

            # 1. Renomear lead_time_mto → lead_time
            if 'lead_time_mto' in colunas_existentes and 'lead_time' not in colunas_existentes:
                print("\n[1/3] Renomeando lead_time_mto → lead_time...")
                db.session.execute(text(
                    "ALTER TABLE cadastro_palletizacao RENAME COLUMN lead_time_mto TO lead_time"
                ))
                print("  OK - Coluna renomeada")
            elif 'lead_time' in colunas_existentes:
                print("\n[1/3] Coluna 'lead_time' ja existe - SKIP")
            else:
                print("\n[1/3] AVISO: Coluna 'lead_time_mto' nao encontrada. Criando 'lead_time'...")
                db.session.execute(text(
                    "ALTER TABLE cadastro_palletizacao ADD COLUMN IF NOT EXISTS lead_time INTEGER"
                ))
                print("  OK - Coluna criada")

            # 2. Adicionar lote_minimo_compra
            if 'lote_minimo_compra' not in colunas_existentes:
                print("\n[2/3] Adicionando coluna lote_minimo_compra...")
                db.session.execute(text(
                    "ALTER TABLE cadastro_palletizacao ADD COLUMN IF NOT EXISTS lote_minimo_compra INTEGER"
                ))
                print("  OK - Coluna adicionada")
            else:
                print("\n[2/3] Coluna 'lote_minimo_compra' ja existe - SKIP")

            # 3. Comentarios
            print("\n[3/3] Adicionando comentarios nas colunas...")
            db.session.execute(text(
                "COMMENT ON COLUMN cadastro_palletizacao.lead_time IS 'Lead time de compra em dias'"
            ))
            db.session.execute(text(
                "COMMENT ON COLUMN cadastro_palletizacao.lote_minimo_compra IS 'Lote minimo de compra (unidades)'"
            ))
            print("  OK - Comentarios adicionados")

            db.session.commit()

            # Verificar resultado
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'cadastro_palletizacao'
                AND column_name IN ('lead_time', 'lote_minimo_compra')
                ORDER BY column_name
            """))
            print("\nVerificacao final:")
            for row in resultado:
                print(f"  {row[0]}: {row[1]} (nullable={row[2]})")

            print("\n" + "=" * 60)
            print("Migration concluida com sucesso!")
            print("=" * 60)

        except Exception as e:
            db.session.rollback()
            print(f"\nERRO na migration: {e}")
            raise


if __name__ == '__main__':
    executar_migration()
