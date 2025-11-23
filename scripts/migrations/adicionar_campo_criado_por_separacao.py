"""
Migration: Adicionar campo criado_por na tabela Separacao
=========================================================

OBJETIVO: Registrar o usuário que criou cada separação, especialmente
          para rastreabilidade de separações criadas via Claude AI.

CAMPO ADICIONADO:
    - criado_por: VARCHAR(100) - Nome do usuário que criou a separação

AUTOR: Claude AI
DATA: 22/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def adicionar_campo_criado_por():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 MIGRATION: Adicionar campo criado_por em separacao")
            print("=" * 80)

            # 1. Verificar se campo já existe
            print("\n1️⃣ Verificando se campo já existe...")

            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'separacao'
                AND column_name = 'criado_por'
            """))

            campos_existentes = [row[0] for row in resultado.fetchall()]

            if 'criado_por' in campos_existentes:
                print("   ✅ Campo 'criado_por' já existe. Nada a fazer.")
                return True

            # 2. Adicionar campo
            print("\n2️⃣ Adicionando campo criado_por...")

            db.session.execute(text("""
                ALTER TABLE separacao
                ADD COLUMN criado_por VARCHAR(100) NULL
            """))

            db.session.commit()
            print("   ✅ Campo 'criado_por' adicionado com sucesso!")

            # 3. Verificar criação
            print("\n3️⃣ Verificando criação do campo...")

            resultado = db.session.execute(text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'separacao'
                AND column_name = 'criado_por'
            """))

            campo = resultado.fetchone()
            if campo:
                print(f"   ✅ Campo criado: {campo[0]} ({campo[1]}({campo[2]}))")
            else:
                print("   ❌ Erro: Campo não foi criado")
                return False

            print("\n" + "=" * 80)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 80)

            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO na migration: {e}")
            return False


if __name__ == "__main__":
    adicionar_campo_criado_por()
