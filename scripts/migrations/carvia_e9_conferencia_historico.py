#!/usr/bin/env python3
"""Migration E9 (2026-04-19): CarviaConferenciaHistorico (append-only
log de transicoes de status_conferencia em CarviaFrete). GAP-31."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def tabela_existe():
    r = db.session.execute(text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'carvia_conferencia_historico'"
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
        if not tabela_existe():
            db.session.execute(text("""
                CREATE TABLE carvia_conferencia_historico (
                    id                       SERIAL PRIMARY KEY,
                    frete_id                 INTEGER NOT NULL
                                             REFERENCES carvia_fretes(id) ON DELETE CASCADE,
                    status_antes             VARCHAR(20),
                    status_depois            VARCHAR(20) NOT NULL,
                    valor_considerado_antes  NUMERIC(15, 2),
                    valor_considerado_depois NUMERIC(15, 2),
                    usuario                  VARCHAR(100) NOT NULL,
                    data                     TIMESTAMP NOT NULL
                                             DEFAULT (NOW() AT TIME ZONE 'UTC'),
                    detalhes_json            JSON
                )
            """))
            db.session.commit()
            print('+ tabela criada')
        else:
            print('= tabela ja existe')

        for nome, cols in [
            ('ix_carvia_conf_historico_frete_id', 'frete_id'),
            ('ix_carvia_conf_historico_data', 'data'),
            ('ix_carvia_conf_historico_frete_data', 'frete_id, data'),
        ]:
            if indice_existe(nome):
                continue
            db.session.execute(text(
                f'CREATE INDEX {nome} ON carvia_conferencia_historico ({cols})'
            ))
            db.session.commit()
            print(f'+ {nome} criado')


if __name__ == '__main__':
    main()
