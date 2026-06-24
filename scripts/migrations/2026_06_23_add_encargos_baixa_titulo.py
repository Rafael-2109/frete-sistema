"""Migration idempotente: colunas de ENCARGOS em baixa_titulo_item.

Suporta a baixa de ANTECIPACAO (ex.: Sendas/Assai) no template de baixa de titulos:
o titulo entra liquido no banco (journal Sicoob) e a diferenca saldo-liquido e' o
encargo financeiro, lancado como write-off na conta ENCARGOS DE EMPRESTIMOS E
FINANCIAMENTOS (despesa), fechando o titulo.

Adiciona:
  - encargos_excel DOUBLE PRECISION DEFAULT 0
  - payment_encargos_odoo_id INTEGER
  - payment_encargos_odoo_name VARCHAR(100)

ORDEM DE DEPLOY:
  1. Rodar ESTA migration ANTES do deploy do codigo novo
     (o flush SQLAlchemy quebra com UndefinedColumn se a coluna nao existir).
  2. Conferir [OK] no output.
  3. Deploy do codigo.

Uso (local):
    source .venv/bin/activate
    python scripts/migrations/2026_06_23_add_encargos_baixa_titulo.py

Uso (prod, autorizado pelo usuario via DATABASE_URL_PROD):
    DATABASE_URL=<DATABASE_URL_PROD> python scripts/migrations/2026_06_23_add_encargos_baixa_titulo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import inspect, text
from app import create_app, db

SQL_PATH = os.path.join(
    os.path.dirname(__file__),
    '2026_06_23_add_encargos_baixa_titulo.sql',
)

TABELA = 'baixa_titulo_item'
COLUNAS = ['encargos_excel', 'payment_encargos_odoo_id', 'payment_encargos_odoo_name']


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table(TABELA):
            raise RuntimeError(f'Tabela {TABELA} nao existe.')

        cols_antes = {c['name'] for c in inspector.get_columns(TABELA)}
        for col in COLUNAS:
            print(f'[INFO] Coluna {col}: {"JA EXISTE" if col in cols_antes else "AUSENTE"}')

        with open(SQL_PATH) as f:
            sql_raw = f.read()

        sql_clean = '\n'.join(
            linha for linha in sql_raw.split('\n')
            if not linha.strip().startswith('--')
        )

        for stmt in sql_clean.split(';'):
            stmt_norm = stmt.strip()
            if not stmt_norm:
                continue
            db.session.execute(text(stmt_norm))
        db.session.commit()

        cols_depois = {c['name'] for c in inspect(db.engine).get_columns(TABELA)}
        faltando = [c for c in COLUNAS if c not in cols_depois]
        if faltando:
            raise RuntimeError(f'Colunas nao adicionadas: {faltando}')

        print(f'[OK] Colunas {COLUNAS} presentes em {TABELA}.')


if __name__ == '__main__':
    main()
