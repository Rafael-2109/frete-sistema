"""
Script para adicionar colunas na tabela extrato_item.
=============================================================================

Colunas adicionadas:
- titulo_receber_id: FK para contas_a_receber (relação 1:1 legacy)
- titulo_pagar_id: FK para contas_a_pagar (relação 1:1 legacy)
- titulo_cnpj: CNPJ do título para facilitar busca por agrupamento

Data: 2025-12-15
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_colunas():
    """Adiciona colunas titulo_receber_id, titulo_pagar_id e titulo_cnpj à tabela extrato_item."""
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("ADICIONANDO COLUNAS À TABELA extrato_item")
        print("=" * 70)

        try:
            # Verificar se colunas já existem
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'extrato_item'
                AND column_name IN ('titulo_receber_id', 'titulo_pagar_id', 'titulo_cnpj')
            """))
            colunas_existentes = [row[0] for row in result.fetchall()]

            print(f"Colunas já existentes: {colunas_existentes}")

            # Adicionar titulo_receber_id se não existir
            if 'titulo_receber_id' not in colunas_existentes:
                print("\n📌 Adicionando coluna titulo_receber_id...")
                db.session.execute(text("""
                    ALTER TABLE extrato_item
                    ADD COLUMN titulo_receber_id INTEGER
                    REFERENCES contas_a_receber(id)
                """))
                print("   ✅ titulo_receber_id adicionada!")

                # Criar índice
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_extrato_item_titulo_receber
                    ON extrato_item(titulo_receber_id)
                """))
                print("   ✅ Índice criado!")
            else:
                print("\n⚠️  titulo_receber_id já existe")

            # Adicionar titulo_pagar_id se não existir
            if 'titulo_pagar_id' not in colunas_existentes:
                print("\n📌 Adicionando coluna titulo_pagar_id...")
                db.session.execute(text("""
                    ALTER TABLE extrato_item
                    ADD COLUMN titulo_pagar_id INTEGER
                    REFERENCES contas_a_pagar(id)
                """))
                print("   ✅ titulo_pagar_id adicionada!")

                # Criar índice
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_extrato_item_titulo_pagar
                    ON extrato_item(titulo_pagar_id)
                """))
                print("   ✅ Índice criado!")
            else:
                print("\n⚠️  titulo_pagar_id já existe")

            # Adicionar titulo_cnpj se não existir
            if 'titulo_cnpj' not in colunas_existentes:
                print("\n📌 Adicionando coluna titulo_cnpj...")
                db.session.execute(text("""
                    ALTER TABLE extrato_item
                    ADD COLUMN titulo_cnpj VARCHAR(20)
                """))
                print("   ✅ titulo_cnpj adicionada!")

                # Criar índice para busca por CNPJ
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_extrato_item_titulo_cnpj
                    ON extrato_item(titulo_cnpj)
                """))
                print("   ✅ Índice criado!")
            else:
                print("\n⚠️  titulo_cnpj já existe")

            db.session.commit()
            print("\n" + "=" * 70)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 70)

            # Verificar resultado
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'extrato_item'
                AND column_name IN ('titulo_receber_id', 'titulo_pagar_id', 'titulo_cnpj')
                ORDER BY column_name
            """))
            print("\nColunas na tabela extrato_item:")
            for row in result.fetchall():
                print(f"  - {row[0]}: {row[1]} (nullable: {row[2]})")

        except Exception as e:
            print(f"\n❌ Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    adicionar_colunas()
