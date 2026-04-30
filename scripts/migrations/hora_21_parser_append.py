"""Migration HORA #21 — Append-prompt versionado para o parser de DANFE.

Cria tabela `hora_danfe_parser_append`. Idempotente.

Como rodar localmente:
    source .venv/bin/activate
    python scripts/migrations/hora_21_parser_append.py

Como rodar no Render Shell:
    psql $DATABASE_URL -f scripts/migrations/hora_21_parser_append.sql
"""
from __future__ import annotations

import sys
from pathlib import Path

# Permite executar via `python scripts/migrations/hora_21_parser_append.py`
# de qualquer cwd — adiciona raiz do projeto ao sys.path.
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402


def _existe_tabela(inspector, nome: str) -> bool:
    return nome in inspector.get_table_names()


def _existe_indice(inspector, tabela: str, indice: str) -> bool:
    try:
        existing = {ix['name'] for ix in inspector.get_indexes(tabela)}
    except Exception:
        return False
    return indice in existing


def main() -> int:
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # Before
        antes = _existe_tabela(inspector, 'hora_danfe_parser_append')
        print(f'[before] tabela hora_danfe_parser_append existe? {antes}')

        ddl = """
        CREATE TABLE IF NOT EXISTS hora_danfe_parser_append (
            id SERIAL PRIMARY KEY,
            versao INTEGER NOT NULL UNIQUE,
            texto_append TEXT NOT NULL,
            acrescimo_aplicado TEXT,
            motivo VARCHAR(500),
            criado_por VARCHAR(100),
            criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
            ativo BOOLEAN NOT NULL DEFAULT TRUE
        );

        CREATE INDEX IF NOT EXISTS ix_hora_danfe_parser_append_ativo
            ON hora_danfe_parser_append (ativo);

        CREATE INDEX IF NOT EXISTS ix_hora_danfe_parser_append_criado_em
            ON hora_danfe_parser_append (criado_em);

        CREATE UNIQUE INDEX IF NOT EXISTS uq_hora_danfe_parser_append_unico_ativo
            ON hora_danfe_parser_append (ativo) WHERE ativo = TRUE;
        """
        with db.engine.begin() as conn:
            for stmt in [s.strip() for s in ddl.split(';') if s.strip()]:
                conn.execute(text(stmt))

        # After
        inspector = inspect(db.engine)
        depois = _existe_tabela(inspector, 'hora_danfe_parser_append')
        idx_ativo = _existe_indice(
            inspector, 'hora_danfe_parser_append',
            'uq_hora_danfe_parser_append_unico_ativo',
        )
        print(f'[after] tabela existe? {depois}; indice unico ativo? {idx_ativo}')

        if not depois:
            print('[ERRO] tabela nao foi criada')
            return 1
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
