"""Migration idempotente: proveniencia + frescor em agent_memories (F5 PAD-CTX).

Adiciona source_session_id TEXT (+indice), last_confirmed TIMESTAMP e
confidence TEXT. ADDITIVE — nenhuma coluna existente e alterada.

ORDEM DE DEPLOY (CRITICO — nao ha auto-migration Alembic p/ estas colunas):
  1. Rodar ESTA migration no Render Shell ANTES do deploy do codigo novo.
     (save_memory passa a gravar mem.source_session_id; sem a coluna, o flush
      quebra com UndefinedColumn — e nos paths background a falha e SILENCIOSA.)
  2. Conferir [OK] no output (3 colunas + indice).
  3. Deploy do codigo.

Uso:
    python scripts/migrations/2026_06_09_agent_memories_proveniencia.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import inspect, text
from app import create_app, db

SQL_PATH = os.path.join(
    os.path.dirname(__file__),
    '2026_06_09_agent_memories_proveniencia.sql',
)

COLUNAS_NOVAS = ('source_session_id', 'last_confirmed', 'confidence')
INDICE_NOVO = 'ix_agent_memories_source_session_id'


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('agent_memories'):
            raise RuntimeError('Tabela agent_memories nao existe.')

        cols_antes = {c['name'] for c in inspector.get_columns('agent_memories')}
        indices_antes = {ix['name'] for ix in inspector.get_indexes('agent_memories')}

        print('[INFO] Estado ANTES:')
        for col in COLUNAS_NOVAS:
            print(f'  - coluna {col:<20} -> {"JA EXISTE" if col in cols_antes else "AUSENTE"}')
        print(f'  - indice {INDICE_NOVO:<36} -> {"JA EXISTE" if INDICE_NOVO in indices_antes else "AUSENTE"}')

        with open(SQL_PATH) as f:
            sql_raw = f.read()

        # Remove linhas de comentario ANTES do split (COMMENT ON multi-linha
        # preservado porque nao comeca com '--').
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
        for col in COLUNAS_NOVAS:
            if col not in cols_depois:
                raise RuntimeError(f'Coluna {col} nao foi adicionada.')
            print(f'  + coluna {col} ADICIONADA')
        if INDICE_NOVO not in indices_depois:
            raise RuntimeError(f'Indice {INDICE_NOVO} nao foi criado.')
        print(f'  + indice {INDICE_NOVO} CRIADO')

        print('\n[OK] Migration aplicada com sucesso.')


if __name__ == '__main__':
    main()
