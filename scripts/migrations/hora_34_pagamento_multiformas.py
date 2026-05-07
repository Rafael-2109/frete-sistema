"""Migration HORA 34: multiplas formas de pagamento por pedido + AUT/ID.

Mudancas:
  1. CREATE TABLE hora_venda_pagamento (1:N HoraVenda):
     - id, venda_id (FK), forma_pagamento_hora (string),
     - valor (NUMERIC 15,2 NOT NULL CHECK > 0), numero_parcelas (DEFAULT 1),
     - aut_id (string opcional), criado_em.
  2. ALTER hora_tagplus_forma_pagamento_map -> +exige_aut_id BOOLEAN
     (default FALSE).
  3. Backfill: para cada HoraVenda existente, cria 1 hora_venda_pagamento
     com valor=valor_total, forma_pagamento_hora=venda.forma_pagamento,
     numero_parcelas=venda.numero_parcelas. Pula vendas com
     forma_pagamento NULL/'NAO_INFORMADO' (registro sem forma definida).

Idempotente — pode rodar 2x sem efeito (CREATE TABLE IF NOT EXISTS,
ADD COLUMN IF NOT EXISTS, INSERT skipped por NOT EXISTS).

Uso:
    python scripts/migrations/hora_34_pagamento_multiformas.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


SQL_CREATE_PAGAMENTO = """
CREATE TABLE IF NOT EXISTS hora_venda_pagamento (
    id SERIAL PRIMARY KEY,
    venda_id INTEGER NOT NULL REFERENCES hora_venda(id) ON DELETE CASCADE,
    forma_pagamento_hora VARCHAR(20) NOT NULL,
    valor NUMERIC(15, 2) NOT NULL,
    numero_parcelas INTEGER NOT NULL DEFAULT 1,
    aut_id VARCHAR(50),
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_hora_venda_pag_valor_pos CHECK (valor > 0),
    CONSTRAINT ck_hora_venda_pag_parcelas_pos CHECK (numero_parcelas >= 1 AND numero_parcelas <= 60)
);
"""

SQL_INDEX_PAGAMENTO = """
CREATE INDEX IF NOT EXISTS ix_hora_venda_pag_venda
    ON hora_venda_pagamento (venda_id);
"""

SQL_ALTER_FORMA_PGTO_AUT = [
    "ALTER TABLE hora_tagplus_forma_pagamento_map "
    "ADD COLUMN IF NOT EXISTS exige_aut_id BOOLEAN NOT NULL DEFAULT FALSE;",
]

SQL_BACKFILL_PAGAMENTOS = """
INSERT INTO hora_venda_pagamento
    (venda_id, forma_pagamento_hora, valor, numero_parcelas, criado_em)
SELECT
    v.id,
    v.forma_pagamento,
    v.valor_total,
    COALESCE(v.numero_parcelas, 1),
    -- Preserva timestamp historico: criado_em > data_venda > NOW (fallback).
    -- Vendas legacy podem ter criado_em NULL (importadas antes do default
    -- server_default ser populado); nesse caso a data da venda e' a melhor
    -- aproximacao.
    COALESCE(
        v.criado_em,
        v.data_venda::timestamp,
        NOW()
    )
FROM hora_venda v
WHERE v.forma_pagamento IS NOT NULL
  AND v.forma_pagamento <> ''
  AND v.forma_pagamento <> 'NAO_INFORMADO'
  AND v.valor_total IS NOT NULL
  AND v.valor_total > 0
  AND NOT EXISTS (
      SELECT 1 FROM hora_venda_pagamento p
      WHERE p.venda_id = v.id
  );
"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        tabelas_antes = set(inspector.get_table_names())
        cols_forma_antes = {
            c['name'] for c in inspector.get_columns('hora_tagplus_forma_pagamento_map')
        }
        print('Estado antes:')
        print(f'  hora_venda_pagamento existe? {"hora_venda_pagamento" in tabelas_antes}')
        print(f'  hora_tagplus_forma_pagamento_map.exige_aut_id? '
              f'{"exige_aut_id" in cols_forma_antes}')

        with db.engine.begin() as conn:
            conn.execute(text(SQL_CREATE_PAGAMENTO))
            conn.execute(text(SQL_INDEX_PAGAMENTO))
            for sql in SQL_ALTER_FORMA_PGTO_AUT:
                conn.execute(text(sql))
            # Backfill so apos DDL.
            result = conn.execute(text(SQL_BACKFILL_PAGAMENTOS))
            n_backfill = result.rowcount

        inspector = inspect(db.engine)
        tabelas_depois = set(inspector.get_table_names())
        cols_forma_depois = {
            c['name'] for c in inspector.get_columns('hora_tagplus_forma_pagamento_map')
        }
        cols_pag_depois = {
            c['name'] for c in inspector.get_columns('hora_venda_pagamento')
        } if 'hora_venda_pagamento' in tabelas_depois else set()

        print('\nEstado depois:')
        print(f'  hora_venda_pagamento existe? {"hora_venda_pagamento" in tabelas_depois}')
        print(f'  hora_venda_pagamento cols: {sorted(cols_pag_depois)}')
        print(f'  hora_tagplus_forma_pagamento_map.exige_aut_id? '
              f'{"exige_aut_id" in cols_forma_depois}')
        print(f'  Backfill: {n_backfill} pagamento(s) criado(s) a partir de HoraVenda existentes.')

        ok = (
            'hora_venda_pagamento' in tabelas_depois
            and 'exige_aut_id' in cols_forma_depois
            and {'id', 'venda_id', 'forma_pagamento_hora', 'valor',
                 'numero_parcelas', 'aut_id', 'criado_em'} <= cols_pag_depois
        )
        if not ok:
            print('\nERRO: alguma estrutura nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 34 concluida com sucesso.')


if __name__ == '__main__':
    main()
