"""Migration HORA 21: modalidade_frete + parcelamento em hora_venda.

Adiciona 3 colunas em `hora_venda`:
  - modalidade_frete VARCHAR(1) NOT NULL DEFAULT '9'
      (TagPlus enum 0/1/2/3/4/9; default '9' = sem ocorrencia, equivale ao
       comportamento anterior hardcoded no PayloadBuilder).
  - numero_parcelas INTEGER NOT NULL DEFAULT 1
      (BETWEEN 1 AND 60; default 1 = a vista).
  - intervalo_parcelas_dias INTEGER NOT NULL DEFAULT 30
      (BETWEEN 1 AND 90; mensal=30, semanal=7, diario=1).

Reporta estado antes/depois (existencia, default, constraint).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


COLUNAS_NOVAS = (
    'modalidade_frete',
    'numero_parcelas',
    'intervalo_parcelas_dias',
)

CONSTRAINTS = (
    'ck_hora_venda_modalidade_frete',
    'ck_hora_venda_numero_parcelas',
    'ck_hora_venda_intervalo_parcelas_dias',
)


def coluna_existe(tabela: str, coluna: str) -> bool:
    return bool(db.session.execute(
        db.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {'t': tabela, 'c': coluna},
    ).scalar())


def coluna_default(tabela: str, coluna: str):
    return db.session.execute(
        db.text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {'t': tabela, 'c': coluna},
    ).scalar()


def constraint_existe(nome: str) -> bool:
    return bool(db.session.execute(
        db.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = :n"
        ),
        {'n': nome},
    ).scalar())


def estado_atual() -> dict:
    return {
        'colunas': {
            c: {
                'existe': coluna_existe('hora_venda', c),
                'default': coluna_default('hora_venda', c),
            } for c in COLUNAS_NOVAS
        },
        'constraints': {c: constraint_existe(c) for c in CONSTRAINTS},
    }


def imprimir(rotulo: str, estado: dict) -> None:
    print(f'\n=== {rotulo} ===')
    print('Colunas:')
    for col, info in estado['colunas'].items():
        marca = '[OK]' if info['existe'] else '[!!]'
        default = info['default'] if info['existe'] else '-'
        print(f'  {marca} hora_venda.{col}  default={default}')
    print('Constraints:')
    for con, ok in estado['constraints'].items():
        marca = '[OK]' if ok else '[!!]'
        print(f'  {marca} {con}')


SQL_PATH = os.path.join(os.path.dirname(__file__), 'hora_21_venda_modalidade_frete_parcelas.sql')


def main() -> None:
    app = create_app()
    with app.app_context():
        antes = estado_atual()
        imprimir('ANTES', antes)

        with open(SQL_PATH, 'r', encoding='utf-8') as f:
            sql = f.read()

        # Executa em statements separados (DO $$ ... $$ e ALTER TABLE).
        # PostgreSQL aceita o SQL inteiro em uma transacao via psycopg2.
        db.session.execute(db.text(sql))
        db.session.commit()

        depois = estado_atual()
        imprimir('DEPOIS', depois)

        ok_colunas = all(v['existe'] for v in depois['colunas'].values())
        ok_constraints = all(depois['constraints'].values())
        if ok_colunas and ok_constraints:
            print('\nMigration aplicada com sucesso.')
        else:
            print('\n[ERRO] Estado pos-migration incompleto — investigar.')
            sys.exit(1)


if __name__ == '__main__':
    main()
