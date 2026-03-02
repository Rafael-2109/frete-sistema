"""
Migration: Adicionar pago_em/pago_por em carvia_faturas_cliente e carvia_despesas
=================================================================================

carvia_faturas_transportadora JA tem esses campos (models.py:548-550).

Uso:
    source .venv/bin/activate
    python scripts/migrations/adicionar_pago_em_por_carvia.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


ALTERACOES = [
    {
        'tabela': 'carvia_faturas_cliente',
        'colunas': [
            ('pago_em', 'TIMESTAMP'),
            ('pago_por', 'VARCHAR(100)'),
        ],
    },
    {
        'tabela': 'carvia_despesas',
        'colunas': [
            ('pago_em', 'TIMESTAMP'),
            ('pago_por', 'VARCHAR(100)'),
        ],
    },
]


def coluna_existe(tabela, coluna):
    """Verifica se coluna ja existe na tabela."""
    return db.session.execute(db.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :coluna
        )
    """), {'tabela': tabela, 'coluna': coluna}).scalar()


def executar():
    """Adiciona colunas pago_em e pago_por."""
    alteracoes_feitas = 0

    for alt in ALTERACOES:
        tabela = alt['tabela']
        for col_nome, col_tipo in alt['colunas']:
            if coluna_existe(tabela, col_nome):
                print(f"[SKIP] {tabela}.{col_nome} ja existe.")
            else:
                db.session.execute(db.text(
                    f"ALTER TABLE {tabela} ADD COLUMN {col_nome} {col_tipo}"
                ))
                print(f"[ADD] {tabela}.{col_nome} ({col_tipo})")
                alteracoes_feitas += 1

    db.session.commit()
    print(f"\n[OK] {alteracoes_feitas} colunas adicionadas.")


def verificar():
    """Verifica estado apos a migration."""
    for alt in ALTERACOES:
        tabela = alt['tabela']
        for col_nome, _ in alt['colunas']:
            existe = coluna_existe(tabela, col_nome)
            status = 'OK' if existe else 'FALTANDO'
            print(f"[{status}] {tabela}.{col_nome}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=== Verificacao ANTES ===")
        verificar()
        print("\n=== Executando ===")
        executar()
        print("\n=== Verificacao DEPOIS ===")
        verificar()
        print("\n[DONE] Migration concluida.")
