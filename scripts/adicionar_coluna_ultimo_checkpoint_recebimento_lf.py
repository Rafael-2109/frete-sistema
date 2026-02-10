"""
Migration: Adiciona coluna ultimo_checkpoint_em na tabela recebimento_lf.

Campo usado para monitoramento de checkpoints durante processamento resiliente.

Uso local:
    source .venv/bin/activate
    python scripts/adicionar_coluna_ultimo_checkpoint_recebimento_lf.py

Uso no Render Shell:
    python scripts/adicionar_coluna_ultimo_checkpoint_recebimento_lf.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


SQL_ALTER = """
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS ultimo_checkpoint_em TIMESTAMP;
"""


def executar():
    app = create_app()
    with app.app_context():
        try:
            db.session.execute(text(SQL_ALTER))
            db.session.commit()
            print("[OK] Coluna ultimo_checkpoint_em adicionada em recebimento_lf")
            print("\n[SUCESSO] Migration completa!")

        except Exception as e:
            print(f"\n[ERRO] {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar()
