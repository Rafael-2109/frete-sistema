"""
Script de Migração: Adicionar campo observacao na tabela moto
Data: 2025-01-10
Executar: python migrations/scripts/20250110_adicionar_observacao_moto.py
"""
import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db

def aplicar_migracao():
    """Aplica a migração SQL"""
    app = create_app()

    with app.app_context():
        # Ler arquivo SQL
        sql_path = os.path.join(
            os.path.dirname(__file__),
            '../sql/20250110_adicionar_observacao_moto.sql'
        )

        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_commands = f.read()

        # Executar SQL
        try:
            db.session.execute(db.text(sql_commands))
            db.session.commit()
            print("✅ Migração aplicada com sucesso!")
            print("   - Campo 'observacao' adicionado na tabela 'moto'")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao aplicar migração: {e}")
            sys.exit(1)

if __name__ == '__main__':
    print("🔄 Aplicando migração: Adicionar campo observacao na tabela moto")
    aplicar_migracao()
