"""CarVia — Comprovantes de Pagamento + flag "Cotacao Paga".

Aplica carvia_comprovante_pagamento.sql:
 (1) tabela carvia_comprovantes_pagamento
 (2) tabela carvia_comprovante_vinculos (N:N polimorfico)
 (3) colunas pago/pago_em/pago_por em carvia_cotacoes

Idempotente; safe para re-execucao.
Executar: python scripts/migrations/carvia_comprovante_pagamento.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def _tabela_existe(nome):
    return db.session.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :t)"
    ), {'t': nome}).scalar()


def _cols_cotacao():
    rows = db.session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'carvia_cotacoes' "
        "  AND column_name IN ('pago','pago_em','pago_por') "
        "ORDER BY column_name"
    )).fetchall()
    return [r[0] for r in rows]


def run():
    app = create_app()
    with app.app_context():
        print(f'BEFORE: comprovantes={_tabela_existe("carvia_comprovantes_pagamento")} '
              f'vinculos={_tabela_existe("carvia_comprovante_vinculos")} '
              f'cols_cotacao={_cols_cotacao()}')

        sql_path = os.path.join(
            os.path.dirname(__file__), 'carvia_comprovante_pagamento.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        comp = _tabela_existe('carvia_comprovantes_pagamento')
        vinc = _tabela_existe('carvia_comprovante_vinculos')
        cols = _cols_cotacao()
        print(f'AFTER: comprovantes={comp} vinculos={vinc} cols_cotacao={cols}')

        expected = ['pago', 'pago_em', 'pago_por']
        if comp and vinc and cols == expected:
            print('OK: migration concluida.')
        else:
            print(f'ERRO: esperado tabelas + cols {expected}; '
                  f'obtido comp={comp} vinc={vinc} cols={cols}')
            sys.exit(1)


if __name__ == '__main__':
    run()
