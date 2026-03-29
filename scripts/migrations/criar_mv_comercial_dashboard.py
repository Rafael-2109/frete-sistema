#!/usr/bin/env python3
"""
Migration: Materialized views para dashboard comercial
=======================================================

Cria duas materialized views que pre-computam os dados do dashboard:
- mv_comercial_equipes: agregacao por equipe de vendas
- mv_comercial_vendedores: agregacao por vendedor dentro de cada equipe

Elimina o FULL OUTER JOIN pesado (carteira × faturamento × entregas) a cada render.
Refresh via scheduler a cada 30 min.

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
        # Ler e executar o SQL
        sql_path = os.path.join(os.path.dirname(__file__), 'criar_mv_comercial_dashboard.sql')
        with open(sql_path, 'r') as f:
            sql_content = f.read()

        # Executar statements individuais (separados por ponto-e-virgula)
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
        for stmt in statements:
            if stmt:
                print(f"  Executando: {stmt[:80]}...")
                db.session.execute(text(stmt))

        db.session.commit()
        print("\nMaterialized views criadas com sucesso!")

        # Verificar
        for mv_name in ('mv_comercial_equipes', 'mv_comercial_vendedores'):
            result = db.session.execute(text(f"SELECT COUNT(*) FROM {mv_name}"))
            count = result.scalar()
            print(f"  {mv_name}: {count} registros")


if __name__ == "__main__":
    run()
