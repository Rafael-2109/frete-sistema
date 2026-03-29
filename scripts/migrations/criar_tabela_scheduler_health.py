#!/usr/bin/env python3
"""
Migration: Tabela scheduler_health para monitoramento
=====================================================

Persiste resultado de cada step do scheduler.
Dashboard em /admin/scheduler-health.

Data: 2026-03-29
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text


def run():
    app = create_app()
    with app.app_context():
        # Verificar se tabela ja existe
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'scheduler_health'"
        ))
        if result.scalar() > 0:
            print("Tabela scheduler_health ja existe. Nada a fazer.")
            return

        sql_path = os.path.join(os.path.dirname(__file__), 'criar_tabela_scheduler_health.sql')
        with open(sql_path, 'r') as f:
            sql_content = f.read()

        for stmt in sql_content.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                db.session.execute(text(stmt))

        db.session.commit()
        print("Tabela scheduler_health criada com sucesso!")


if __name__ == "__main__":
    run()
