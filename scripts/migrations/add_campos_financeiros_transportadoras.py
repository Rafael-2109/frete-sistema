"""
Migration: Adicionar campos financeiros na tabela transportadoras

Campos adicionados:
- banco: Nome do banco
- agencia: Número da agência
- conta: Número da conta
- tipo_conta: 'corrente' ou 'poupanca'
- pix: Chave PIX
- cpf_cnpj_favorecido: CPF/CNPJ do favorecido
- obs_financ: Observações financeiras

Data: 2025-01-11
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_campos_financeiros():
    """Adiciona campos financeiros na tabela transportadoras"""
    app = create_app()
    with app.app_context():
        try:
            # Lista de campos a adicionar
            campos = [
                ("banco", "VARCHAR(100)"),
                ("agencia", "VARCHAR(20)"),
                ("conta", "VARCHAR(30)"),
                ("tipo_conta", "VARCHAR(20)"),
                ("pix", "VARCHAR(100)"),
                ("cpf_cnpj_favorecido", "VARCHAR(20)"),
                ("obs_financ", "TEXT"),
            ]

            for campo, tipo in campos:
                try:
                    sql = f"ALTER TABLE transportadoras ADD COLUMN IF NOT EXISTS {campo} {tipo};"
                    db.session.execute(text(sql))
                    print(f"✓ Campo '{campo}' adicionado com sucesso")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                        print(f"⚠ Campo '{campo}' já existe, ignorando...")
                    else:
                        print(f"✗ Erro ao adicionar campo '{campo}': {e}")

            db.session.commit()
            print("\n✓ Migration concluída com sucesso!")

        except Exception as e:
            print(f"✗ Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    adicionar_campos_financeiros()
