"""
Migration: indice GIN em agent_sessions.data->subagent_costs (feature #3).

Permite queries agregadas de custo por subagente sem full scan. Zero
impacto em escritas (INSERT/UPDATE nao usam o indice — GIN sob JSONB
so e consultado em path queries).

Usage:
    python scripts/migrations/agent_session_subagent_costs_idx.py
"""
import sys

from sqlalchemy import text

from app import create_app, db


def verificar_indice() -> bool:
    """Retorna True se o indice ja existe."""
    result = db.session.execute(text("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'agent_sessions'
          AND indexname = 'idx_agent_sessions_subagent_costs'
    """)).scalar()
    return bool(result)


def main() -> int:
    app = create_app()
    with app.app_context():
        if verificar_indice():
            print('[SKIP] indice idx_agent_sessions_subagent_costs ja existe.')
            return 0

        print('[INFO] Criando indice GIN idx_agent_sessions_subagent_costs...')
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_agent_sessions_subagent_costs
            ON agent_sessions USING GIN ((data -> 'subagent_costs'))
        """))
        db.session.execute(text("""
            COMMENT ON INDEX idx_agent_sessions_subagent_costs IS
            'Suporta queries agregadas top subagentes por custo via jsonb_array_elements'
        """))
        db.session.commit()

        if verificar_indice():
            print('[OK] Indice criado com sucesso.')
            return 0
        print('[ERRO] Indice nao aparece em pg_indexes apos commit.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
