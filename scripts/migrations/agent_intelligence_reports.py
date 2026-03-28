"""
Migracao: Criar tabela agent_intelligence_reports

Tabela para persistir relatorios de inteligencia do agente (D7 do cron semanal).
Bridge Agent SDK <-> Claude Code: metricas, recomendacoes e backlog acumulado.

Executar:
    source .venv/bin/activate
    python scripts/migrations/agent_intelligence_reports.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela():
    """Cria tabela agent_intelligence_reports no PostgreSQL."""
    app = create_app()

    with app.app_context():
        try:
            # Verifica se tabela ja existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'agent_intelligence_reports'
                )
            """))

            if result.scalar():
                print("Tabela agent_intelligence_reports ja existe")
                return True

            # Cria tabela
            print("Criando tabela agent_intelligence_reports...")

            db.session.execute(text("""
                CREATE TABLE agent_intelligence_reports (
                    id SERIAL PRIMARY KEY,
                    report_date DATE NOT NULL UNIQUE,
                    health_score NUMERIC(5,1) DEFAULT 0,
                    friction_score NUMERIC(5,1) DEFAULT 0,
                    recommendation_count INTEGER DEFAULT 0,
                    sessions_analyzed INTEGER DEFAULT 0,
                    report_json JSONB NOT NULL,
                    report_markdown TEXT NOT NULL,
                    backlog_json JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))

            # Cria indice
            print("Criando indice...")

            db.session.execute(text("""
                CREATE INDEX idx_intelligence_reports_date
                ON agent_intelligence_reports(report_date DESC)
            """))

            db.session.commit()
            print("Tabela agent_intelligence_reports criada com sucesso")

            # Verificacao pos-criacao
            result = db.session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'agent_intelligence_reports'
                ORDER BY ordinal_position
            """))

            print("\nColunas criadas:")
            for row in result:
                print(f"  {row[0]}: {row[1]}")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"ERRO ao criar tabela: {e}")
            return False


if __name__ == '__main__':
    success = criar_tabela()
    sys.exit(0 if success else 1)
