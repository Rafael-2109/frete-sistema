"""Migration HORA 46: origem do lead no pedido de venda (roadmap #6).

Mudancas:
  1. hora_venda -> +origem_lead VARCHAR(20)      (canal: GOOGLE/INSTAGRAM/FACEBOOK/OUTROS)
  2. hora_venda -> +origem_lead_obs VARCHAR(255) (texto livre, so quando OUTROS)

Ambas nullable: vendas legadas / import DANFE / backfill ficam com NULL.
A obrigatoriedade do canal e do formulario manual (frontend + rota), nao do
schema. NAO confundir com hora_venda.origem_criacao (fonte tecnica DANFE/MANUAL).

Idempotente — pode rodar 2x (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_46_venda_origem_lead.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_venda "
    "ADD COLUMN IF NOT EXISTS origem_lead VARCHAR(20);",
    "ALTER TABLE hora_venda "
    "ADD COLUMN IF NOT EXISTS origem_lead_obs VARCHAR(255);",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        cols_venda = {c['name'] for c in inspector.get_columns('hora_venda')}
        print('Estado antes:')
        print(f'  hora_venda.origem_lead? {"origem_lead" in cols_venda}')
        print(f'  hora_venda.origem_lead_obs? {"origem_lead_obs" in cols_venda}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        cols_venda = {c['name'] for c in inspector.get_columns('hora_venda')}
        print('\nEstado depois:')
        print(f'  hora_venda.origem_lead? {"origem_lead" in cols_venda}')
        print(f'  hora_venda.origem_lead_obs? {"origem_lead_obs" in cols_venda}')

        if 'origem_lead' not in cols_venda or 'origem_lead_obs' not in cols_venda:
            print('\nERRO: colunas nao criadas.')
            sys.exit(1)

        print('\nMigration HORA 46 concluida com sucesso.')


if __name__ == '__main__':
    main()
