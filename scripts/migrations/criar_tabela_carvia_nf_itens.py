"""
Migration: Criar tabela carvia_nf_itens
========================================

Armazena itens de produto das NFs importadas (DANFE PDF ou XML NF-e).
Cada item tem codigo, descricao, NCM, CFOP, quantidade e valores.

Execucao:
    source .venv/bin/activate
    python scripts/migrations/criar_tabela_carvia_nf_itens.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def verificar_antes():
    """Verifica estado antes da migration"""
    result = db.session.execute(db.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'carvia_nf_itens'
        )
    """)).scalar()
    return result


def executar_migration():
    """Cria tabela carvia_nf_itens"""
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_nf_itens (
            id SERIAL PRIMARY KEY,
            nf_id INTEGER NOT NULL REFERENCES carvia_nfs(id),

            -- Produto
            codigo_produto VARCHAR(60),
            descricao VARCHAR(255),
            ncm VARCHAR(10),
            cfop VARCHAR(10),

            -- Quantidades e valores
            unidade VARCHAR(10),
            quantidade NUMERIC(15, 4),
            valor_unitario NUMERIC(15, 4),
            valor_total_item NUMERIC(15, 2),

            -- Auditoria (Brasil naive — sem timezone)
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # Indice na FK
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_nf_itens_nf_id
        ON carvia_nf_itens(nf_id)
    """))

    db.session.commit()


def verificar_depois():
    """Verifica estado depois da migration"""
    result = db.session.execute(db.text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'carvia_nf_itens'
        ORDER BY ordinal_position
    """)).fetchall()
    return result


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Before
        existe_antes = verificar_antes()
        if existe_antes:
            print('⚠️  Tabela carvia_nf_itens ja existe. Pulando migration.')
            sys.exit(0)

        print('📋 Tabela carvia_nf_itens NAO existe. Criando...')

        # Execute
        executar_migration()

        # After
        colunas = verificar_depois()
        print(f'✅ Tabela carvia_nf_itens criada com {len(colunas)} colunas:')
        for nome, tipo in colunas:
            print(f'   - {nome}: {tipo}')
