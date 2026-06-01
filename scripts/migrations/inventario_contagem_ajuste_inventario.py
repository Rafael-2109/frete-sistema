"""Migration: adiciona coluna `ajuste_inventario` em inventario_contagem_item.

Semântica (não confundir com `ajuste`):
  • ajuste            = contagem − qtd_esperada → delta a aplicar no Odoo (skills).
  • ajuste_inventario = valor literal da coluna AJUSTE da planilha (autoritativo) →
    delta somado ao último inventário na coluna INV/MOV do Confronto.

Backfill: ao CRIAR a coluna, popula ajuste_inventario = ajuste nos itens já
existentes (preserva no Confronto os ajustes cíclicos já contabilizados antes da
mudança). O backfill só roda quando a coluna é recém-criada (idempotente).

Spec: docs/superpowers/specs/2026-05-31-inventario-ciclico-contagem-ajustes-design.md
"""
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app, db  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402


TABELA = 'inventario_contagem_item'
COLUNA = 'ajuste_inventario'


def _tem_coluna(insp) -> bool:
    return COLUNA in {c['name'] for c in insp.get_columns(TABELA)}


def main():
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        existe_antes = _tem_coluna(insp)
        print(f'ANTES: {TABELA}.{COLUNA}: {"existe" if existe_antes else "AUSENTE"}')

        if not existe_antes:
            with db.engine.begin() as conn:
                conn.execute(text(
                    f'ALTER TABLE {TABELA} '
                    f'ADD COLUMN {COLUNA} NUMERIC(15,3) NOT NULL DEFAULT 0'
                ))
                # Backfill: preserva o que o Confronto somava (ajuste) p/ itens legados.
                res = conn.execute(text(
                    f'UPDATE {TABELA} SET {COLUNA} = ajuste WHERE ajuste IS NOT NULL'
                ))
                print(f'  Coluna criada. Backfill: {res.rowcount} linha(s) '
                      f'(ajuste_inventario = ajuste).')
        else:
            print('  Coluna já existe — nada a fazer (backfill ignorado).')

        insp = inspect(db.engine)
        print(f'DEPOIS: {TABELA}.{COLUNA}: '
              f'{"existe" if _tem_coluna(insp) else "AUSENTE"}')


if __name__ == '__main__':
    main()
