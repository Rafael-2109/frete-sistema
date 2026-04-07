#!/usr/bin/env python3
"""
Migration: Materialized view mv_pedidos
========================================

Cria mv_pedidos — copia pre-computada da VIEW pedidos.
Elimina custo de ~500ms/scan (subqueries correlacionadas CarVia).
Refresh via scheduler (CONCURRENTLY, ~30 min).

A VIEW regular `pedidos` permanece intacta (rollback: reverter __tablename__).

Data: 2026-04-07
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text


def run():
    app = create_app()
    with app.app_context():
        # Verificar estado ANTES
        print("=== BEFORE ===")
        try:
            result = db.session.execute(
                text("SELECT COUNT(*) FROM pg_matviews WHERE matviewname = 'mv_pedidos'")
            )
            mv_exists = (result.scalar() or 0) > 0
            print(f"  mv_pedidos existe: {mv_exists}")
        except Exception as e:
            print(f"  Erro ao verificar: {e}")
            mv_exists = False

        try:
            result = db.session.execute(text("SELECT COUNT(*) FROM pedidos"))
            view_count = result.scalar()
            print(f"  VIEW pedidos: {view_count} registros")
        except Exception as e:
            print(f"  Erro ao contar VIEW: {e}")
            view_count = 0

        # Executar SQL
        print("\n=== EXECUTANDO MIGRATION ===")
        sql_path = os.path.join(os.path.dirname(__file__), 'criar_mv_pedidos.sql')
        with open(sql_path, 'r') as f:
            sql_content = f.read()

        # Executar statements individuais
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
        for stmt in statements:
            if stmt:
                preview = stmt[:80].replace('\n', ' ')
                print(f"  Executando: {preview}...")
                db.session.execute(text(stmt))

        db.session.commit()

        # Verificar estado DEPOIS
        print("\n=== AFTER ===")
        result = db.session.execute(text("SELECT COUNT(*) FROM mv_pedidos"))
        mv_count = result.scalar()
        print(f"  mv_pedidos: {mv_count} registros")
        print(f"  VIEW pedidos: {view_count} registros")

        if mv_count == view_count:
            print(f"\n  Paridade OK: {mv_count} == {view_count}")
        else:
            print(f"\n  AVISO: contagens diferem! MV={mv_count}, VIEW={view_count}")

        # Listar indices
        result = db.session.execute(text("""
            SELECT indexname FROM pg_indexes WHERE tablename = 'mv_pedidos'
            ORDER BY indexname
        """))
        indices = [r[0] for r in result]
        print(f"\n  Indices criados ({len(indices)}):")
        for idx in indices:
            print(f"    - {idx}")

        print("\nMigration concluida com sucesso!")


if __name__ == "__main__":
    run()
