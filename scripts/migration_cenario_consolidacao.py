"""
Migration: Adicionar campo cenario_consolidacao em validacao_nf_po_dfe
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """Adiciona campo cenario_consolidacao na tabela validacao_nf_po_dfe"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna ja existe
            result = db.session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'validacao_nf_po_dfe' AND column_name = 'cenario_consolidacao'
            """))
            if result.fetchone():
                print("Coluna cenario_consolidacao ja existe. Nada a fazer.")
                return

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE validacao_nf_po_dfe
                ADD COLUMN cenario_consolidacao VARCHAR(20)
            """))
            db.session.commit()
            print("Coluna cenario_consolidacao adicionada com sucesso!")

            # Preencher registros existentes baseado no acao_executada
            result = db.session.execute(text("""
                UPDATE validacao_nf_po_dfe
                SET cenario_consolidacao = 'n_pos'
                WHERE status = 'consolidado' AND cenario_consolidacao IS NULL
            """))
            db.session.commit()
            print(f"Registros existentes atualizados: {result.rowcount}")

        except Exception as e:
            db.session.rollback()
            print(f"Erro na migration: {e}")
            raise


if __name__ == '__main__':
    executar_migration()
