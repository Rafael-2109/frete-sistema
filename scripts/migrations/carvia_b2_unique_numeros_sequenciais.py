#!/usr/bin/env python3
"""Migration B2 (2026-04-18): UniqueConstraints parciais em numeros
sequenciais CarVia.

Design pos-baseline: dupes legitimas existem em subcontratos (CANCELADO +
CONFIRMADO com mesmo cte_numero). Constraint simples quebraria. Usamos
parcial WHERE status != 'CANCELADO'.

Pre-check: o script aborta se encontrar dupes ATIVAS (nao-CANCELADO).

Idempotente. Uso local:
    source .venv/bin/activate
    python scripts/migrations/carvia_b2_unique_numeros_sequenciais.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


ALVOS = [
    ('carvia_operacoes', 'cte_numero', 'uq_carvia_operacoes_cte_numero_ativo'),
    ('carvia_subcontratos', 'cte_numero', 'uq_carvia_subcontratos_cte_numero_ativo'),
    ('carvia_cte_complementares', 'numero_comp', 'uq_carvia_cte_complementares_numero_comp_ativo'),
]


def indice_existe(nome):
    r = db.session.execute(text(
        f"SELECT 1 FROM pg_indexes WHERE indexname = '{nome}'"
    )).fetchone()
    return r is not None


def contar_dupes_ativas(tabela, coluna):
    r = db.session.execute(text(f"""
        SELECT COUNT(*) FROM (
            SELECT {coluna}
            FROM {tabela}
            WHERE {coluna} IS NOT NULL AND status != 'CANCELADO'
            GROUP BY {coluna} HAVING COUNT(*) > 1
        ) sub
    """)).scalar()
    return int(r or 0)


def main():
    app = create_app()
    with app.app_context():
        print('=== Pre-check: dupes ATIVAS (status != CANCELADO) ===')
        dupes_total = 0
        for tabela, coluna, _ in ALVOS:
            n = contar_dupes_ativas(tabela, coluna)
            dupes_total += n
            print(f'  {tabela}.{coluna}: {n} dupes')

        if dupes_total > 0:
            print(
                f'\n⛔ ABORTANDO: {dupes_total} dupes ATIVAS encontradas. '
                'Resolver antes de aplicar constraint.'
            )
            sys.exit(1)

        print('\n=== Before ===')
        for _, _, nome_idx in ALVOS:
            print(f'  {nome_idx}: ', 'exists' if indice_existe(nome_idx) else 'missing')

        for tabela, coluna, nome_idx in ALVOS:
            if indice_existe(nome_idx):
                print(f'= {nome_idx} ja existe')
                continue
            db.session.execute(text(f"""
                CREATE UNIQUE INDEX {nome_idx}
                    ON {tabela} ({coluna})
                    WHERE {coluna} IS NOT NULL AND status != 'CANCELADO'
            """))
            db.session.commit()
            print(f'+ {nome_idx} criado')

        print('=== After ===')
        for _, _, nome_idx in ALVOS:
            print(f'  {nome_idx}: ', 'exists' if indice_existe(nome_idx) else 'missing')


if __name__ == '__main__':
    main()
