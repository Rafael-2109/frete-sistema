"""
Script de migração para adicionar campos de impostos e desconto contratual
na tabela carteira_principal

Campos adicionados:
- icms_valor (NUMERIC 15,2) - Valor do ICMS da linha
- icmsst_valor (NUMERIC 15,2) - Valor do ICMS ST da linha
- pis_valor (NUMERIC 15,2) - Valor do PIS da linha
- cofins_valor (NUMERIC 15,2) - Valor do COFINS da linha
- desconto_contratual (BOOLEAN) - Se cliente tem desconto contratual
- desconto_percentual (NUMERIC 5,2) - Percentual de desconto contratual

Data: 2025-12-26
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(nome_coluna):
    """Verifica se a coluna já existe na tabela"""
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'carteira_principal'
        AND column_name = :nome_coluna
    """), {'nome_coluna': nome_coluna})
    return result.fetchone() is not None


def adicionar_colunas():
    """Adiciona as novas colunas na tabela carteira_principal"""

    colunas = [
        ('icms_valor', 'NUMERIC(15, 2)', 'NULL'),
        ('icmsst_valor', 'NUMERIC(15, 2)', 'NULL'),
        ('pis_valor', 'NUMERIC(15, 2)', 'NULL'),
        ('cofins_valor', 'NUMERIC(15, 2)', 'NULL'),
        ('desconto_contratual', 'BOOLEAN', 'DEFAULT FALSE'),
        ('desconto_percentual', 'NUMERIC(5, 2)', 'NULL'),
    ]

    for nome, tipo, default in colunas:
        if verificar_coluna_existe(nome):
            print(f"✅ Coluna '{nome}' já existe - pulando")
            continue

        try:
            sql = f"ALTER TABLE carteira_principal ADD COLUMN {nome} {tipo} {default}"
            db.session.execute(text(sql))
            db.session.commit()
            print(f"✅ Coluna '{nome}' adicionada com sucesso")
        except Exception as e:
            print(f"❌ Erro ao adicionar coluna '{nome}': {e}")
            db.session.rollback()


def main():
    print("=" * 60)
    print("MIGRAÇÃO: Campos de Impostos e Desconto Contratual")
    print("=" * 60)

    app = create_app()
    with app.app_context():
        adicionar_colunas()

    print("\n" + "=" * 60)
    print("Migração concluída!")
    print("=" * 60)


if __name__ == '__main__':
    main()
