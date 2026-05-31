"""Migration: criar tabelas do Inventário Cíclico (contagem parcial por quant).

Tabelas: inventario_contagem, inventario_contagem_item
Spec: docs/superpowers/specs/2026-05-31-inventario-ciclico-contagem-ajustes-design.md
"""
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app, db  # noqa: E402
from app.inventario.models import (  # noqa: E402
    ContagemInventario, ContagemInventarioItem,
)
from sqlalchemy import inspect  # noqa: E402


TABELAS = ['inventario_contagem', 'inventario_contagem_item']


def main():
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        before = {t: t in insp.get_table_names() for t in TABELAS}
        print('ANTES:')
        for t, exists in before.items():
            print(f'  {t}: {"existe" if exists else "AUSENTE"}')

        # Ordem importa: pai antes do filho (FK)
        for model in [ContagemInventario, ContagemInventarioItem]:
            model.__table__.create(db.engine, checkfirst=True)

        insp = inspect(db.engine)
        after = {t: t in insp.get_table_names() for t in TABELAS}
        print('\nDEPOIS:')
        for t, exists in after.items():
            print(f'  {t}: {"existe" if exists else "AUSENTE"}')

        criadas = [t for t in TABELAS if not before[t] and after[t]]
        print(f'\nCriadas: {len(criadas)} ({", ".join(criadas) or "nenhuma"})')


if __name__ == '__main__':
    main()
