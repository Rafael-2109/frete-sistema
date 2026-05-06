"""Migration HORA 33: preço A vista/A prazo + tipo de pagamento + desconto %.

Mudanças:
  1. hora_modelo  -> +preco_a_vista, +preco_a_prazo (NUMERIC(15,2), opcional)
  2. hora_tagplus_forma_pagamento_map -> +tipo_pagamento VARCHAR(10)
     (valores esperados: 'A_VISTA', 'A_PRAZO'; NULL = nao classificada)
  3. hora_venda_item -> +desconto_percentual NUMERIC(5,2) NOT NULL DEFAULT 0

Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS + CHECK guard).

Uso:
    python scripts/migrations/hora_33_preco_avp_desconto.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


SQL_ALTER_MODELO = [
    "ALTER TABLE hora_modelo ADD COLUMN IF NOT EXISTS preco_a_vista NUMERIC(15, 2);",
    "ALTER TABLE hora_modelo ADD COLUMN IF NOT EXISTS preco_a_prazo NUMERIC(15, 2);",
]

SQL_ALTER_FORMA_PGTO = [
    "ALTER TABLE hora_tagplus_forma_pagamento_map "
    "ADD COLUMN IF NOT EXISTS tipo_pagamento VARCHAR(10);",
]

SQL_CHECK_TIPO_PGTO = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'ck_hora_tagplus_forma_pgto_tipo'
          AND table_name = 'hora_tagplus_forma_pagamento_map'
    ) THEN
        ALTER TABLE hora_tagplus_forma_pagamento_map
            ADD CONSTRAINT ck_hora_tagplus_forma_pgto_tipo
            CHECK (tipo_pagamento IS NULL OR tipo_pagamento IN ('A_VISTA', 'A_PRAZO'));
    END IF;
END $$;
"""

SQL_ALTER_VENDA_ITEM = [
    "ALTER TABLE hora_venda_item "
    "ADD COLUMN IF NOT EXISTS desconto_percentual NUMERIC(5, 2) NOT NULL DEFAULT 0;",
]


def _has_check_constraint(inspector, table: str, name: str) -> bool:
    for ck in inspector.get_check_constraints(table):
        if ck.get('name') == name:
            return True
    return False


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        cols_modelo_antes = {c['name'] for c in inspector.get_columns('hora_modelo')}
        cols_forma_antes = {c['name'] for c in inspector.get_columns('hora_tagplus_forma_pagamento_map')}
        cols_item_antes = {c['name'] for c in inspector.get_columns('hora_venda_item')}
        check_antes = _has_check_constraint(
            inspector, 'hora_tagplus_forma_pagamento_map',
            'ck_hora_tagplus_forma_pgto_tipo',
        )

        print('Estado antes:')
        print(f'  hora_modelo.preco_a_vista? {"preco_a_vista" in cols_modelo_antes}')
        print(f'  hora_modelo.preco_a_prazo? {"preco_a_prazo" in cols_modelo_antes}')
        print(f'  hora_tagplus_forma_pagamento_map.tipo_pagamento? {"tipo_pagamento" in cols_forma_antes}')
        print(f'  CHECK ck_hora_tagplus_forma_pgto_tipo? {check_antes}')
        print(f'  hora_venda_item.desconto_percentual? {"desconto_percentual" in cols_item_antes}')

        with db.engine.begin() as conn:
            for sql in SQL_ALTER_MODELO:
                conn.execute(text(sql))
            for sql in SQL_ALTER_FORMA_PGTO:
                conn.execute(text(sql))
            conn.execute(text(SQL_CHECK_TIPO_PGTO))
            for sql in SQL_ALTER_VENDA_ITEM:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        cols_modelo_depois = {c['name'] for c in inspector.get_columns('hora_modelo')}
        cols_forma_depois = {c['name'] for c in inspector.get_columns('hora_tagplus_forma_pagamento_map')}
        cols_item_depois = {c['name'] for c in inspector.get_columns('hora_venda_item')}
        check_depois = _has_check_constraint(
            inspector, 'hora_tagplus_forma_pagamento_map',
            'ck_hora_tagplus_forma_pgto_tipo',
        )

        print('\nEstado depois:')
        print(f'  hora_modelo.preco_a_vista? {"preco_a_vista" in cols_modelo_depois}')
        print(f'  hora_modelo.preco_a_prazo? {"preco_a_prazo" in cols_modelo_depois}')
        print(f'  hora_tagplus_forma_pagamento_map.tipo_pagamento? {"tipo_pagamento" in cols_forma_depois}')
        print(f'  CHECK ck_hora_tagplus_forma_pgto_tipo? {check_depois}')
        print(f'  hora_venda_item.desconto_percentual? {"desconto_percentual" in cols_item_depois}')

        ok = (
            'preco_a_vista' in cols_modelo_depois
            and 'preco_a_prazo' in cols_modelo_depois
            and 'tipo_pagamento' in cols_forma_depois
            and check_depois
            and 'desconto_percentual' in cols_item_depois
        )
        if not ok:
            print('\nERRO: alguma estrutura nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 33 concluida com sucesso.')


if __name__ == '__main__':
    main()
