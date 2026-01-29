"""
Migration: Adicionar campo motorista_proprio na tabela transportadoras
========================================================================

Campo Boolean para indicar se a transportadora utiliza motorista próprio da empresa.

SQL para Render Shell:
----------------------
ALTER TABLE transportadoras ADD COLUMN IF NOT EXISTS motorista_proprio BOOLEAN DEFAULT FALSE;

Autor: Sistema de Fretes
Data: 2026-01-29
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """Adiciona campo motorista_proprio na tabela transportadoras"""
    app = create_app()
    with app.app_context():
        try:
            # Verifica se o campo já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'transportadoras'
                AND column_name = 'motorista_proprio'
            """))

            if resultado.fetchone():
                print("[INFO] Campo 'motorista_proprio' já existe na tabela transportadoras.")
                return True

            # Adiciona o campo
            print("[INFO] Adicionando campo 'motorista_proprio' na tabela transportadoras...")
            db.session.execute(text("""
                ALTER TABLE transportadoras
                ADD COLUMN motorista_proprio BOOLEAN DEFAULT FALSE
            """))
            db.session.commit()

            print("[SUCESSO] Campo 'motorista_proprio' adicionado com sucesso!")
            print("[INFO] Valor padrão: FALSE")
            return True

        except Exception as e:
            print(f"[ERRO] Falha ao executar migration: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("Migration: Adicionar motorista_proprio em transportadoras")
    print("=" * 60)

    sucesso = executar_migration()

    if sucesso:
        print("\n[OK] Migration concluída com sucesso!")
    else:
        print("\n[FALHA] Migration falhou. Verifique os erros acima.")
        sys.exit(1)
