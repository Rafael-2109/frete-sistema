"""Migration idempotente: ADD COLUMN meta JSONB + indice GIN em agent_memories.

Formato canonico de memorias (2026-06-08): da uma fonte de verdade estruturada e
queryavel (indice GIN jsonb_path_ops) aos campos discriminantes de cada memoria,
em vez de mante-los presos no texto livre da coluna `content`.

ADDITIVE: NAO altera a coluna `content`. O backfill (script separado
backfill_memoria_meta.py) popula `meta` parseando o content legado.

ORDEM DE DEPLOY (CRITICO — nao ha auto-migration Alembic p/ esta coluna):
  1. Rodar ESTA migration no Render Shell ANTES de fazer deploy do codigo novo.
     (O codigo grava `mem.meta`; sem a coluna, o flush quebra com UndefinedColumn —
      e nos paths background de extracao/promocao a falha e SILENCIOSA best-effort.)
  2. Conferir [OK] no output (coluna + indice).
  3. Deploy do codigo.
  4. (opcional) backfill_memoria_meta.py --apply no Render Shell.

Uso:
    python scripts/migrations/2026_06_08_agent_memories_meta_jsonb.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import inspect, text
from app import create_app, db

SQL_PATH = os.path.join(
    os.path.dirname(__file__),
    '2026_06_08_agent_memories_meta_jsonb.sql',
)

COLUNA_NOVA = 'meta'
INDICE_NOVO = 'ix_agent_memories_meta_gin'


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('agent_memories'):
            raise RuntimeError('Tabela agent_memories nao existe.')

        cols_antes = {c['name'] for c in inspector.get_columns('agent_memories')}
        indices_antes = {ix['name'] for ix in inspector.get_indexes('agent_memories')}

        print('[INFO] Estado ANTES:')
        print(f'  - coluna {COLUNA_NOVA:<8} -> {"JA EXISTE" if COLUNA_NOVA in cols_antes else "AUSENTE"}')
        print(f'  - indice {INDICE_NOVO:<28} -> {"JA EXISTE" if INDICE_NOVO in indices_antes else "AUSENTE"}')

        with open(SQL_PATH) as f:
            sql_raw = f.read()

        # Remove linhas de comentario ANTES do split (evita comentario colar no
        # statement seguinte). Atencao: COMMENT ON ... usa concatenacao de strings
        # SQL multi-linha — preservada porque nao comeca com '--'.
        sql_clean = '\n'.join(
            linha for linha in sql_raw.split('\n')
            if not linha.strip().startswith('--')
        )

        for stmt in sql_clean.split(';'):
            stmt_norm = stmt.strip()
            if not stmt_norm or stmt_norm.upper() in ('BEGIN', 'COMMIT'):
                continue
            db.session.execute(text(stmt_norm))
        db.session.commit()

        # Verificacao AFTER
        inspector = inspect(db.engine)
        cols_depois = {c['name'] for c in inspector.get_columns('agent_memories')}
        indices_depois = {ix['name'] for ix in inspector.get_indexes('agent_memories')}

        print('\n[INFO] Estado DEPOIS:')
        if COLUNA_NOVA not in cols_depois:
            raise RuntimeError(f'Coluna {COLUNA_NOVA} nao foi adicionada.')
        print(f'  + coluna {COLUNA_NOVA} ADICIONADA (JSONB)')
        if INDICE_NOVO not in indices_depois:
            raise RuntimeError(f'Indice {INDICE_NOVO} nao foi criado.')
        print(f'  + indice {INDICE_NOVO} CRIADO (GIN jsonb_path_ops)')

        print('\n[OK] Migration aplicada com sucesso.')


if __name__ == '__main__':
    main()
