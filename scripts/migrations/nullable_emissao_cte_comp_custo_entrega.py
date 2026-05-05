"""
Migration: torna `carvia_emissao_cte_complementar.custo_entrega_id` NULLABLE.

Data: 2026-05-05
Fonte de verdade: app/carvia/models/cte_custos.py::CarviaEmissaoCteComplementar

Motivo:
    Unificacao do fluxo de criacao de CTe Complementar (PR CarVia) — emissao
    SSW 222 deixa de exigir `CarviaCustoEntrega` previo. CE passa a ser
    vinculo OPCIONAL (pode ser anexado depois pelo botao "Vincular CE" no
    detalhe do CTe Comp).

    Antes: usuario obrigado a criar Custo Entrega antes de gerar CTe Comp.
    Depois: pode emitir CTe Comp diretamente da operacao, vincular CE depois
            (ou nem vincular).
"""

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402

TABLE = 'carvia_emissao_cte_complementar'
COLUMN = 'custo_entrega_id'


def coluna_eh_nullable(conn) -> bool:
    """Verifica se a coluna ja esta nullable (idempotencia)."""
    row = conn.execute(
        text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c "
            "  AND table_schema = 'public'"
        ),
        {'t': TABLE, 'c': COLUMN},
    ).fetchone()
    if row is None:
        raise RuntimeError(
            f'Coluna {TABLE}.{COLUMN} nao encontrada — migration anterior incompleta.'
        )
    return row[0] == 'YES'


def main() -> int:
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            print(f'=== ANTES ===')
            antes = coluna_eh_nullable(conn)
            print(f'  {TABLE}.{COLUMN} is_nullable = {antes}')

            if antes:
                print('Coluna ja eh nullable — nada a fazer (idempotente).')
                return 0

            print(f'\n=== APLICANDO ALTER ===')
            conn.execute(
                text(
                    f'ALTER TABLE {TABLE} ALTER COLUMN {COLUMN} DROP NOT NULL'
                )
            )
            conn.commit()
            print(f'  ALTER TABLE {TABLE} ALTER COLUMN {COLUMN} DROP NOT NULL  -> OK')

            print(f'\n=== DEPOIS ===')
            depois = coluna_eh_nullable(conn)
            print(f'  {TABLE}.{COLUMN} is_nullable = {depois}')

            if not depois:
                print('FALHA: coluna ainda nao eh nullable apos ALTER.')
                return 1

            print('\nMigration aplicada com sucesso.')
            return 0


if __name__ == '__main__':
    sys.exit(main())
