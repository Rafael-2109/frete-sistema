"""
Migration: Alargar tipo_separacao em alertas_separacao_cotada
=============================================================

VARCHAR(30) → VARCHAR(50) para alinhar com modelo SQLAlchemy String(50).

Causa raiz: Sentry PYTHON-FLASK-1G — DataError: value too long for type character varying
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def migrar():
    app = create_app()
    with app.app_context():
        # Verificar estado atual
        result = db.session.execute(db.text("""
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'alertas_separacao_cotada'
              AND column_name = 'tipo_separacao'
        """))
        row = result.fetchone()

        if not row:
            print("ERRO: Coluna tipo_separacao nao encontrada em alertas_separacao_cotada")
            return False

        tamanho_atual = row[0]
        print(f"Tamanho atual: VARCHAR({tamanho_atual})")

        if tamanho_atual and tamanho_atual >= 50:
            print("Ja esta com tamanho >= 50. Nada a fazer.")
            return True

        # Verificar se existem valores que seriam truncados (improvavel mas seguro)
        result_max = db.session.execute(db.text("""
            SELECT MAX(LENGTH(tipo_separacao)) as max_len
            FROM alertas_separacao_cotada
            WHERE tipo_separacao IS NOT NULL
        """))
        max_len = result_max.fetchone()[0]
        if max_len:
            print(f"Maior valor existente: {max_len} chars")

        # Executar ALTER
        db.session.execute(db.text("""
            ALTER TABLE alertas_separacao_cotada
            ALTER COLUMN tipo_separacao TYPE VARCHAR(50)
        """))
        db.session.commit()

        # Verificar resultado
        result_depois = db.session.execute(db.text("""
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'alertas_separacao_cotada'
              AND column_name = 'tipo_separacao'
        """))
        tamanho_novo = result_depois.fetchone()[0]
        print(f"Tamanho apos migration: VARCHAR({tamanho_novo})")

        if tamanho_novo == 30:
            print("Migration concluida com sucesso!")
            return True
        else:
            print(f"ERRO: Esperava 30, obteve {tamanho_novo}")
            return False


if __name__ == '__main__':
    migrar()
