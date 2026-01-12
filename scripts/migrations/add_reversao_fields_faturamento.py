"""
Migration: Adicionar campos de reversão em FaturamentoProduto

Campos adicionados:
- revertida: Boolean (indica se a NF foi revertida via Nota de Crédito)
- nota_credito_id: Integer (ID do out_refund no Odoo)
- data_reversao: DateTime (data/hora da reversão)

Executar: python scripts/migrations/add_reversao_fields_faturamento.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_campos_reversao():
    """Adiciona campos de reversão na tabela faturamento_produto"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se os campos já existem
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'faturamento_produto'
                AND column_name IN ('revertida', 'nota_credito_id', 'data_reversao')
            """))
            campos_existentes = [row[0] for row in resultado.fetchall()]

            campos_criados = []

            # 1. Campo revertida (Boolean)
            if 'revertida' not in campos_existentes:
                db.session.execute(text("""
                    ALTER TABLE faturamento_produto
                    ADD COLUMN revertida BOOLEAN DEFAULT FALSE NOT NULL
                """))
                campos_criados.append('revertida')
                print("✅ Campo 'revertida' adicionado")
            else:
                print("⏭️  Campo 'revertida' já existe")

            # 2. Campo nota_credito_id (Integer - ID do out_refund no Odoo)
            if 'nota_credito_id' not in campos_existentes:
                db.session.execute(text("""
                    ALTER TABLE faturamento_produto
                    ADD COLUMN nota_credito_id INTEGER NULL
                """))
                campos_criados.append('nota_credito_id')
                print("✅ Campo 'nota_credito_id' adicionado")
            else:
                print("⏭️  Campo 'nota_credito_id' já existe")

            # 3. Campo data_reversao (DateTime)
            if 'data_reversao' not in campos_existentes:
                db.session.execute(text("""
                    ALTER TABLE faturamento_produto
                    ADD COLUMN data_reversao TIMESTAMP NULL
                """))
                campos_criados.append('data_reversao')
                print("✅ Campo 'data_reversao' adicionado")
            else:
                print("⏭️  Campo 'data_reversao' já existe")

            # 4. Criar índice para revertida (performance em queries)
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_faturamento_revertida
                    ON faturamento_produto(revertida)
                """))
                print("✅ Índice 'idx_faturamento_revertida' criado")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    print("⏭️  Índice 'idx_faturamento_revertida' já existe")
                else:
                    print(f"⚠️  Erro ao criar índice: {e}")

            db.session.commit()

            if campos_criados:
                print(f"\n✅ Migration concluída! Campos criados: {', '.join(campos_criados)}")
            else:
                print("\n⏭️  Nenhum campo novo criado (todos já existiam)")

            # Mostrar estrutura atual
            print("\n📋 Estrutura atual dos campos de reversão:")
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'faturamento_produto'
                AND column_name IN ('revertida', 'nota_credito_id', 'data_reversao', 'status_nf')
                ORDER BY ordinal_position
            """))
            for row in resultado.fetchall():
                print(f"   - {row[0]}: {row[1]} (nullable={row[2]}, default={row[3]})")

            return True

        except Exception as e:
            print(f"❌ Erro na migration: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRATION: Adicionar campos de reversão em FaturamentoProduto")
    print("=" * 60)
    adicionar_campos_reversao()
