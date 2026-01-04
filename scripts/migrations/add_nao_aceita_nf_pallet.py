"""
Migração: Adicionar campo nao_aceita_nf_pallet
==============================================

Adiciona o campo 'nao_aceita_nf_pallet' nas tabelas:
- contatos_agendamento (clientes)
- transportadoras

Data: 02/01/2026
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
            # 1. Adicionar campo na tabela contatos_agendamento
            print("Adicionando campo nao_aceita_nf_pallet em contatos_agendamento...")
            db.session.execute(text("""
                ALTER TABLE contatos_agendamento
                ADD COLUMN IF NOT EXISTS nao_aceita_nf_pallet BOOLEAN NOT NULL DEFAULT FALSE;
            """))
            print("  ✓ Campo adicionado em contatos_agendamento")

            # 2. Adicionar campo na tabela transportadoras
            print("Adicionando campo nao_aceita_nf_pallet em transportadoras...")
            db.session.execute(text("""
                ALTER TABLE transportadoras
                ADD COLUMN IF NOT EXISTS nao_aceita_nf_pallet BOOLEAN NOT NULL DEFAULT FALSE;
            """))
            print("  ✓ Campo adicionado em transportadoras")

            db.session.commit()
            print("\n✓ Migração concluída com sucesso!")

        except Exception as e:
            print(f"\n✗ Erro na migração: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    migrar()
