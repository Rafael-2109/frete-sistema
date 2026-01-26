"""
Script para adicionar campo e_pallet_devolucao na tabela nf_devolucao.

Este campo indica se uma NFD é de devolução de pallet/vasilhame (CFOP 1920/2920/5920/6920)
e deve ser tratada no módulo de pallet, não no módulo de devoluções de produto.

Autor: Sistema de Fretes
Data: 25/01/2026
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_campo_pallet():
    """Adiciona campo e_pallet_devolucao na tabela nf_devolucao"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se a coluna já existe
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'nf_devolucao'
                AND column_name = 'e_pallet_devolucao'
            """))

            if result.fetchone():
                print("✅ Coluna e_pallet_devolucao já existe na tabela nf_devolucao")
                return True

            print("🔄 Adicionando coluna e_pallet_devolucao...")

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE nf_devolucao
                ADD COLUMN e_pallet_devolucao BOOLEAN NOT NULL DEFAULT FALSE
            """))

            # Criar índice
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_nf_devolucao_pallet
                ON nf_devolucao (e_pallet_devolucao)
            """))

            db.session.commit()
            print("✅ Coluna e_pallet_devolucao adicionada com sucesso!")
            print("✅ Índice idx_nf_devolucao_pallet criado!")

            # Mostrar estatísticas
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM nf_devolucao
            """))
            row = result.fetchone()
            total = row[0] if row else 0
            print(f"📊 Total de NFDs na tabela: {total}")
            print("")
            print("🔄 Para detectar NFDs de pallet existentes, execute:")
            print("   python scripts/devolucao/002_detectar_nfds_pallet_existentes.py")

            return True

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    adicionar_campo_pallet()
