"""Migration HORA 38: campos `valor_frete` e `tipo_frete_calc` em hora_venda.

Mudancas:
  1. hora_venda -> +valor_frete NUMERIC(15,2) (nullable, default NULL)
  2. hora_venda -> +tipo_frete_calc VARCHAR(10) (nullable, default NULL)

Semantica:
  - valor_frete: valor monetario do frete CIF (R$). NULL quando nao aplicavel
    (FOB, sem ocorrencia ou pedido legado sem informacao de frete).
  - tipo_frete_calc:
      'INCLUSO'   -> o valor da moto JA inclui o frete; UI compara
                     (valor_moto - frete) com preco de tabela.
      'ADICIONAR' -> frete e somado ao valor da moto; UI rateia entre itens.
      NULL        -> nao informado / nao aplicavel.

Aplicavel apenas quando modalidade_frete == '0' (CIF). Service valida.

Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_38_frete_calc.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


SQL_ALTER_VENDA = [
    "ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS valor_frete NUMERIC(15,2);",
    "ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS tipo_frete_calc VARCHAR(10);",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        cols_antes = {c['name'] for c in inspector.get_columns('hora_venda')}
        print('Estado antes:')
        print(f'  hora_venda.valor_frete?      {"valor_frete" in cols_antes}')
        print(f'  hora_venda.tipo_frete_calc?  {"tipo_frete_calc" in cols_antes}')

        with db.engine.begin() as conn:
            for sql in SQL_ALTER_VENDA:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        cols_depois = {c['name'] for c in inspector.get_columns('hora_venda')}

        print('\nEstado depois:')
        print(f'  hora_venda.valor_frete?      {"valor_frete" in cols_depois}')
        print(f'  hora_venda.tipo_frete_calc?  {"tipo_frete_calc" in cols_depois}')

        faltantes = [
            c for c in ('valor_frete', 'tipo_frete_calc') if c not in cols_depois
        ]
        if faltantes:
            print(f'\nERRO: colunas nao criadas: {faltantes}')
            sys.exit(1)

        print('\nMigration HORA 38 concluida com sucesso.')


if __name__ == '__main__':
    main()
