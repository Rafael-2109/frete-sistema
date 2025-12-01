#!/usr/bin/env python3
"""
Script de migração: Adicionar campo criado_por na tabela separacao
Data: 2025-12-01
Autor: Agente Logístico

Este campo permite identificar a origem da criação da separação:
- 'Agente Logistico' - Criado via skill do agente
- 'Sistema' - Criado via interface web
- 'API' - Criado via API
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe():
    """Verifica se a coluna já existe"""
    resultado = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'separacao'
        AND column_name = 'criado_por'
    """)).fetchone()
    return resultado is not None


def adicionar_coluna():
    """Adiciona a coluna criado_por"""
    app = create_app()

    with app.app_context():
        if verificar_coluna_existe():
            print("✅ Coluna 'criado_por' já existe na tabela 'separacao'")
            return True

        try:
            print("Adicionando coluna 'criado_por' na tabela 'separacao'...")

            db.session.execute(text("""
                ALTER TABLE separacao
                ADD COLUMN criado_por VARCHAR(100) NULL
            """))

            db.session.commit()
            print("✅ Coluna 'criado_por' adicionada com sucesso!")

            # Verificar
            if verificar_coluna_existe():
                print("✅ Verificação: Coluna existe no banco")
                return True
            else:
                print("❌ Erro: Coluna não foi criada")
                return False

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar coluna: {e}")
            return False


if __name__ == '__main__':
    adicionar_coluna()
