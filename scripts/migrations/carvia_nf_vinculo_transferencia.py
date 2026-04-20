#!/usr/bin/env python3
"""Migration (2026-04-20): CarviaNfVinculoTransferencia.

Vinculo NF Transferencia (intercompany, raiz CNPJ emit==dest) -> NF Venda
ao cliente final, para operacoes triangulares (1:N).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def tabela_existe(conn):
    r = conn.execute(text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'carvia_nf_vinculos_transferencia'"
    )).fetchone()
    return r is not None


def indice_existe(conn, nome):
    r = conn.execute(text(
        f"SELECT 1 FROM pg_indexes WHERE indexname = '{nome}'"
    )).fetchone()
    return r is not None


def contar_registros(conn):
    try:
        r = conn.execute(text(
            "SELECT COUNT(*) FROM carvia_nf_vinculos_transferencia"
        )).fetchone()
        return int(r[0]) if r else 0
    except Exception:
        return None


def main():
    app = create_app()
    with app.app_context():
        # Usa conexao direta (nao db.session) para evitar estado abortado
        # vindo do create_app (warnings de FK cycles no PostgreSQL).
        with db.engine.connect() as conn:
            antes = contar_registros(conn)
            print(f'= antes: tabela existe? {tabela_existe(conn)}; count={antes}')

            if not tabela_existe(conn):
                conn.execute(text("""
                    CREATE TABLE carvia_nf_vinculos_transferencia (
                        id                          SERIAL PRIMARY KEY,
                        nf_transferencia_id         INTEGER NOT NULL
                                                    REFERENCES carvia_nfs(id) ON DELETE RESTRICT,
                        nf_venda_id                 INTEGER NOT NULL
                                                    REFERENCES carvia_nfs(id) ON DELETE CASCADE,
                        peso_bruto_venda_snapshot   NUMERIC(15, 3),
                        peso_bruto_transf_snapshot  NUMERIC(15, 3),
                        vinculado_retroativamente   BOOLEAN NOT NULL DEFAULT FALSE,
                        contexto_retroativo         TEXT,
                        criado_em                   TIMESTAMP NOT NULL
                                                    DEFAULT (NOW() AT TIME ZONE 'UTC'),
                        criado_por                  VARCHAR(100) NOT NULL,
                        CONSTRAINT uq_nfvt_venda_unico     UNIQUE (nf_venda_id),
                        CONSTRAINT ck_nfvt_nf_distintas
                            CHECK (nf_transferencia_id != nf_venda_id)
                    )
                """))
                conn.commit()
                print('+ tabela carvia_nf_vinculos_transferencia criada')
            else:
                print('= tabela ja existe (skip CREATE)')

            for nome, cols in [
                ('ix_nfvt_transf',    'nf_transferencia_id'),
                ('ix_nfvt_venda',     'nf_venda_id'),
                ('ix_nfvt_criado_em', 'criado_em'),
            ]:
                if indice_existe(conn, nome):
                    print(f'= {nome} ja existe')
                    continue
                conn.execute(text(
                    f'CREATE INDEX {nome} ON '
                    f'carvia_nf_vinculos_transferencia ({cols})'
                ))
                conn.commit()
                print(f'+ {nome} criado')

            depois = contar_registros(conn)
            print(f'= depois: tabela existe? {tabela_existe(conn)}; count={depois}')


if __name__ == '__main__':
    main()
