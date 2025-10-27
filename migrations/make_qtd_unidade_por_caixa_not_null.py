"""
Script de migração para tornar qtd_unidade_por_caixa NOT NULL em RecursosProducao
Campo necessário para conversão SKU→Unidade

Data: 2025-01-26
Autor: Sistema PCP
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def make_field_not_null():
    app = create_app()

    with app.app_context():
        try:
            print("🔍 Verificando dados existentes...")

            # Verificar se há registros com NULL
            result = db.session.execute(text("""
                SELECT COUNT(*)
                FROM recursos_producao
                WHERE qtd_unidade_por_caixa IS NULL
            """))

            count_null = result.scalar()

            if count_null > 0:
                print(f"⚠️  Encontrados {count_null} registros com qtd_unidade_por_caixa NULL")
                print("❌ Não é possível prosseguir. Corrija os dados primeiro.")
                print("💡 Sugestão: UPDATE recursos_producao SET qtd_unidade_por_caixa = 1 WHERE qtd_unidade_por_caixa IS NULL")
                return

            print("✅ Nenhum registro com NULL encontrado")

            # Alterar tipo para INTEGER e tornar NOT NULL
            print("📝 Alterando coluna para INTEGER NOT NULL...")
            db.session.execute(text("""
                ALTER TABLE recursos_producao
                ALTER COLUMN qtd_unidade_por_caixa TYPE INTEGER,
                ALTER COLUMN qtd_unidade_por_caixa SET NOT NULL
            """))

            db.session.commit()
            print("✅ Migração concluída com sucesso!")
            print("✅ qtd_unidade_por_caixa agora é INTEGER NOT NULL")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro durante migração: {str(e)}")
            raise

if __name__ == '__main__':
    make_field_not_null()
