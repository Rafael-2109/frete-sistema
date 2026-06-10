"""Migration idempotente: coluna agente_fable5 em usuarios (opt-in Fable 5).

Adiciona `agente_fable5 BOOLEAN NOT NULL DEFAULT FALSE`.
Controlada pela UI em /auth/usuarios/<id>/editar (toggle "Agente — Fable 5").

ORDEM DE DEPLOY:
  1. Rodar ESTA migration no Render Shell ANTES do deploy do codigo novo.
     (o flush SQLAlchemy quebra com UndefinedColumn se a coluna nao existir.)
  2. Conferir [OK] no output.
  3. Deploy do codigo.

Uso:
    source .venv/bin/activate
    python scripts/migrations/2026_06_10_add_agente_fable5_usuarios.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import inspect, text
from app import create_app, db

SQL_PATH = os.path.join(
    os.path.dirname(__file__),
    '2026_06_10_add_agente_fable5_usuarios.sql',
)

COLUNA = 'agente_fable5'


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('usuarios'):
            raise RuntimeError('Tabela usuarios nao existe.')

        cols_antes = {c['name'] for c in inspector.get_columns('usuarios')}
        print(f'[INFO] Coluna {COLUNA}: {"JA EXISTE" if COLUNA in cols_antes else "AUSENTE"}')

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

        cols_depois = {c['name'] for c in inspect(db.engine).get_columns('usuarios')}
        if COLUNA not in cols_depois:
            raise RuntimeError(f'Coluna {COLUNA} nao foi adicionada.')

        print(f'[OK] Coluna {COLUNA} presente em usuarios.')


if __name__ == '__main__':
    main()
