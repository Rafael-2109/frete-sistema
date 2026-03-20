"""
Migration: Criar tabela carvia_receitas
========================================

Receitas operacionais diversas (comissoes, reembolsos, bonificacoes)
do modulo CarVia. Espelho de carvia_despesas com semantica CREDITO.

Uso:
    source .venv/bin/activate
    python scripts/migrations/criar_tabela_carvia_receitas.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def verificar_antes():
    """Verifica estado antes da migration."""
    insp = inspect(db.engine)
    tabelas = insp.get_table_names()
    if 'carvia_receitas' in tabelas:
        print('[!] Tabela carvia_receitas ja existe. Migration nao necessaria.')
        return False
    print('[OK] Tabela carvia_receitas nao existe. Pode criar.')
    return True


def executar():
    """Cria tabela carvia_receitas com indices."""
    sql = text("""
        CREATE TABLE IF NOT EXISTS carvia_receitas (
            id SERIAL PRIMARY KEY,
            tipo_receita VARCHAR(50) NOT NULL,
            descricao VARCHAR(500),
            valor NUMERIC(15, 2) NOT NULL,
            data_receita DATE NOT NULL,
            data_vencimento DATE,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
            recebido_por VARCHAR(100),
            recebido_em TIMESTAMP,
            total_conciliado NUMERIC(15, 2) NOT NULL DEFAULT 0,
            conciliado BOOLEAN NOT NULL DEFAULT FALSE,
            observacoes TEXT,
            criado_por VARCHAR(150),
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_carvia_receitas_tipo_receita
            ON carvia_receitas (tipo_receita);

        CREATE INDEX IF NOT EXISTS ix_carvia_receitas_status
            ON carvia_receitas (status);
    """)
    db.session.execute(sql)
    db.session.commit()
    print('[OK] Tabela carvia_receitas criada com 2 indices.')


def verificar_depois():
    """Verifica estado apos a migration."""
    insp = inspect(db.engine)
    tabelas = insp.get_table_names()
    if 'carvia_receitas' not in tabelas:
        print('[ERRO] Tabela carvia_receitas NAO encontrada apos migration!')
        return False

    colunas = [col['name'] for col in insp.get_columns('carvia_receitas')]
    esperadas = [
        'id', 'tipo_receita', 'descricao', 'valor', 'data_receita',
        'data_vencimento', 'status', 'recebido_por', 'recebido_em',
        'total_conciliado', 'conciliado', 'observacoes',
        'criado_por', 'criado_em', 'atualizado_em',
    ]
    faltando = [c for c in esperadas if c not in colunas]
    if faltando:
        print(f'[ERRO] Colunas faltando: {faltando}')
        return False

    indices = insp.get_indexes('carvia_receitas')
    nomes_idx = [idx['name'] for idx in indices]
    if 'ix_carvia_receitas_tipo_receita' not in nomes_idx:
        print('[AVISO] Indice ix_carvia_receitas_tipo_receita nao encontrado.')
    if 'ix_carvia_receitas_status' not in nomes_idx:
        print('[AVISO] Indice ix_carvia_receitas_status nao encontrado.')

    print(f'[OK] Tabela carvia_receitas: {len(colunas)} colunas, {len(indices)} indices.')
    return True


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print('=== Migration: Criar tabela carvia_receitas ===')
        print()

        if not verificar_antes():
            sys.exit(0)

        print()
        executar()

        print()
        if verificar_depois():
            print()
            print('Migration concluida com sucesso!')
        else:
            print()
            print('Migration FALHOU na verificacao pos-execucao.')
            sys.exit(1)
