"""
SCRIPT 1: Adicionar FK fatura_frete_id em DespesaExtra
Objetivo: Adiciona a coluna sem quebrar o sistema existente
Executar: LOCALMENTE primeiro, depois criar SQL para Render
Data: 2025-01-23
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_fk_fatura():
    """Adiciona FK fatura_frete_id na tabela despesas_extras"""

    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("ADICIONANDO FK fatura_frete_id EM despesas_extras")
            print("=" * 80)
            print()

            # Verifica se a coluna já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='despesas_extras'
                AND column_name='fatura_frete_id';
            """))

            if resultado.fetchone():
                print("⚠️  Coluna 'fatura_frete_id' já existe!")
                print("   Pulando criação da coluna.")
                return

            print("📝 Adicionando coluna fatura_frete_id...")

            # Adiciona a coluna (nullable=True para não quebrar registros existentes)
            db.session.execute(text("""
                ALTER TABLE despesas_extras
                ADD COLUMN fatura_frete_id INTEGER;
            """))

            print("✅ Coluna adicionada com sucesso!")
            print()

            # Adiciona a FK (constraint)
            print("📝 Adicionando FOREIGN KEY constraint...")

            db.session.execute(text("""
                ALTER TABLE despesas_extras
                ADD CONSTRAINT fk_despesa_extra_fatura_frete
                FOREIGN KEY (fatura_frete_id)
                REFERENCES faturas_frete(id)
                ON DELETE SET NULL;
            """))

            print("✅ Foreign Key constraint adicionada com sucesso!")
            print()

            # Adiciona índice para performance
            print("📝 Adicionando índice para performance...")

            db.session.execute(text("""
                CREATE INDEX idx_despesas_extras_fatura_frete_id
                ON despesas_extras(fatura_frete_id);
            """))

            print("✅ Índice criado com sucesso!")
            print()

            # Commit
            db.session.commit()

            print("=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print()
            print("PRÓXIMOS PASSOS:")
            print("1. Executar script 03_migrar_dados_despesas.sql no Render")
            print("2. Validar migração com 04_validar_migracao.sql")
            print("3. Atualizar código (models.py e routes.py)")
            print()

        except Exception as e:
            db.session.rollback()
            print()
            print("❌ ERRO durante migração:")
            print(f"   {str(e)}")
            print()
            raise

if __name__ == '__main__':
    adicionar_fk_fatura()
