"""
Migration: Adicionar campo criacao_tardia em carvia_cotacoes
============================================================

Cotacoes criadas a partir de NFs que ja possuem CTe CarVia (criacao tardia)
recebem pricing pre-preenchido e permitem edicao restrita mesmo apos aprovacao.

Execucao:
    source .venv/bin/activate
    python scripts/migrations/add_criacao_tardia_cotacao.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def migrate():
    app = create_app()
    with app.app_context():
        # Verificar estado ANTES
        result = db.session.execute(db.text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'carvia_cotacoes'
              AND column_name = 'criacao_tardia'
        """))
        existe = result.fetchone()

        if existe:
            print("[OK] Campo 'criacao_tardia' ja existe em carvia_cotacoes. Nada a fazer.")
            return

        # Adicionar campo
        db.session.execute(db.text("""
            ALTER TABLE carvia_cotacoes
            ADD COLUMN criacao_tardia BOOLEAN NOT NULL DEFAULT FALSE
        """))
        db.session.commit()

        # Verificar estado APOS
        result = db.session.execute(db.text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'carvia_cotacoes'
              AND column_name = 'criacao_tardia'
        """))
        existe = result.fetchone()
        if existe:
            print("[OK] Campo 'criacao_tardia' adicionado com sucesso.")
        else:
            print("[ERRO] Campo 'criacao_tardia' NAO foi criado.")


if __name__ == '__main__':
    migrate()
