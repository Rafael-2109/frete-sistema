"""
Migration: Adiciona campos de empresa autorizada ao descarte de devolucao

Campos adicionados:
- empresa_autorizada_nome: Nome/Razao Social da empresa autorizada a descartar
- empresa_autorizada_documento: CNPJ ou CPF da empresa autorizada
- empresa_autorizada_tipo: TRANSPORTADOR ou CLIENTE

Executar: python scripts/migrations/add_empresa_autorizada_descarte.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            # Verificar se campos ja existem
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'descarte_devolucao'
                AND column_name = 'empresa_autorizada_nome'
            """))

            if resultado.fetchone():
                print("Campos ja existem. Migration ja foi executada.")
                return

            # Adicionar novos campos
            db.session.execute(text("""
                ALTER TABLE descarte_devolucao
                ADD COLUMN IF NOT EXISTS empresa_autorizada_nome VARCHAR(255),
                ADD COLUMN IF NOT EXISTS empresa_autorizada_documento VARCHAR(20),
                ADD COLUMN IF NOT EXISTS empresa_autorizada_tipo VARCHAR(20) DEFAULT 'TRANSPORTADOR'
            """))

            db.session.commit()
            print("Migration executada com sucesso!")
            print("Campos adicionados:")
            print("  - empresa_autorizada_nome VARCHAR(255)")
            print("  - empresa_autorizada_documento VARCHAR(20)")
            print("  - empresa_autorizada_tipo VARCHAR(20)")

        except Exception as e:
            print(f"Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
