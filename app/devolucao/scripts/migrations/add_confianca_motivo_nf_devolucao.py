"""
Script de migracao para adicionar campo confianca_motivo na tabela nf_devolucao

Adiciona campo para armazenar a confianca da extracao de motivo por IA
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_campo_confianca_motivo():
    """Adiciona campo confianca_motivo na tabela nf_devolucao"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna ja existe
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'nf_devolucao' AND column_name = 'confianca_motivo'
            """))

            if result.fetchone():
                print("Coluna confianca_motivo ja existe na tabela nf_devolucao")
                return True

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE nf_devolucao
                ADD COLUMN confianca_motivo NUMERIC(5, 4)
            """))

            db.session.commit()
            print("Coluna confianca_motivo adicionada com sucesso!")
            return True

        except Exception as e:
            print(f"Erro ao adicionar coluna: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    adicionar_campo_confianca_motivo()
