"""
Migration: Adicionar campos de controle de pallets no Embarque

Novos campos:
- qtd_pallets_separados: Total pallets expedidos
- qtd_pallets_trazidos: Pallets trazidos pela transportadora

O saldo pendente e calculado dinamicamente:
Saldo = Separados - Trazidos - Faturados (NF pallet preenchida)

Criado em: 2026-01-04
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def migrar():
    app = create_app()
    with app.app_context():
        try:
            # Adicionar qtd_pallets_separados
            print("Adicionando coluna qtd_pallets_separados...")
            db.session.execute(text("""
                ALTER TABLE embarques
                ADD COLUMN IF NOT EXISTS qtd_pallets_separados INTEGER DEFAULT 0;
            """))

            # Adicionar qtd_pallets_trazidos
            print("Adicionando coluna qtd_pallets_trazidos...")
            db.session.execute(text("""
                ALTER TABLE embarques
                ADD COLUMN IF NOT EXISTS qtd_pallets_trazidos INTEGER DEFAULT 0;
            """))

            db.session.commit()
            print("Migration concluida com sucesso!")
            print("")
            print("Novos campos adicionados a tabela embarques:")
            print("  - qtd_pallets_separados: Total pallets expedidos")
            print("  - qtd_pallets_trazidos: Pallets trazidos pela transportadora")
            print("")
            print("O saldo pendente e calculado dinamicamente pela property:")
            print("  saldo_pallets_pendentes = separados - trazidos - faturados")

        except Exception as e:
            print(f"Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    migrar()
