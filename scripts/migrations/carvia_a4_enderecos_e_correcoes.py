#!/usr/bin/env python3
"""Migration A4.1 (2026-04-18): Enderecos textuais + CarviaEnderecoCorrecao.

1. Adiciona 8 colunas em carvia_operacoes (remetente/destinatario
   logradouro/numero/bairro/cep)
2. Cria tabela carvia_endereco_correcoes (audit trail CC-e / manual)

Idempotente. Uso local:
    source .venv/bin/activate
    python scripts/migrations/carvia_a4_enderecos_e_correcoes.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


COLUNAS_OP = [
    ('remetente_logradouro', 'VARCHAR(150)'),
    ('remetente_numero', 'VARCHAR(20)'),
    ('remetente_bairro', 'VARCHAR(150)'),
    ('remetente_cep', 'VARCHAR(10)'),
    ('destinatario_logradouro', 'VARCHAR(150)'),
    ('destinatario_numero', 'VARCHAR(20)'),
    ('destinatario_bairro', 'VARCHAR(150)'),
    ('destinatario_cep', 'VARCHAR(10)'),
]

INDEXES_CORRECOES = [
    ('ix_carvia_endereco_correcoes_operacao_id', 'operacao_id'),
    ('ix_carvia_endereco_correcoes_operacao_criado', 'operacao_id, criado_em'),
    ('ix_carvia_endereco_correcoes_motivo_criado', 'motivo, criado_em'),
]


def coluna_existe(tabela, coluna):
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        f"WHERE table_name = '{tabela}' AND column_name = '{coluna}'"
    )).fetchone()
    return r is not None


def tabela_existe(tabela):
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.tables "
        f"WHERE table_name = '{tabela}'"
    )).fetchone()
    return r is not None


def indice_existe(nome):
    r = db.session.execute(text(
        f"SELECT 1 FROM pg_indexes WHERE indexname = '{nome}'"
    )).fetchone()
    return r is not None


def main():
    app = create_app()
    with app.app_context():
        print('=== Before ===')
        for nome, _ in COLUNAS_OP:
            print(f'  carvia_operacoes.{nome}:', 'exists' if coluna_existe('carvia_operacoes', nome) else 'missing')
        print(f'  carvia_endereco_correcoes:',
              'exists' if tabela_existe('carvia_endereco_correcoes') else 'missing')

        # 1. Colunas em carvia_operacoes
        for nome, tipo in COLUNAS_OP:
            if coluna_existe('carvia_operacoes', nome):
                print(f'= carvia_operacoes.{nome} ja existe')
                continue
            db.session.execute(text(
                f'ALTER TABLE carvia_operacoes ADD COLUMN {nome} {tipo}'
            ))
            db.session.commit()
            print(f'+ Coluna carvia_operacoes.{nome} criada')

        # 2. Tabela carvia_endereco_correcoes
        if not tabela_existe('carvia_endereco_correcoes'):
            db.session.execute(text("""
                CREATE TABLE carvia_endereco_correcoes (
                    id              SERIAL PRIMARY KEY,
                    operacao_id     INTEGER NOT NULL
                                    REFERENCES carvia_operacoes(id) ON DELETE CASCADE,
                    campo           VARCHAR(40) NOT NULL,
                    valor_anterior  VARCHAR(150),
                    valor_novo      VARCHAR(150),
                    motivo          VARCHAR(20) NOT NULL DEFAULT 'CORRECAO_MANUAL',
                    numero_cce      VARCHAR(30),
                    criado_em       TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
                    criado_por      VARCHAR(100)
                )
            """))
            db.session.commit()
            print('+ Tabela carvia_endereco_correcoes criada')
        else:
            print('= Tabela carvia_endereco_correcoes ja existe')

        # 3. Indices
        for nome_idx, colunas in INDEXES_CORRECOES:
            if indice_existe(nome_idx):
                print(f'= Index {nome_idx} ja existe')
                continue
            db.session.execute(text(
                f'CREATE INDEX {nome_idx} '
                f'ON carvia_endereco_correcoes ({colunas})'
            ))
            db.session.commit()
            print(f'+ Index {nome_idx} criado')

        print('=== After ===')
        for nome, _ in COLUNAS_OP:
            print(f'  carvia_operacoes.{nome}:',
                  'exists' if coluna_existe('carvia_operacoes', nome) else 'missing')
        print(f'  carvia_endereco_correcoes:',
              'exists' if tabela_existe('carvia_endereco_correcoes') else 'missing')


if __name__ == '__main__':
    main()
