#!/usr/bin/env python3
"""Migration: VIEW pedidos v11 — v10 com local_cd da CarVia = default VICTORIO_MARCHEZINE (4B).

Faz o badge de CD aparecer tambem nas linhas CarVia da /pedidos/lista_pedidos (antes NULL).
Refinamento futuro: derivar TM da Coleta vinculada. Idempotente (DROP+CREATE). Local ou prod.
PRE-REQUISITO: alterar_view_pedidos_v10_local_cd. Data: 2026-06-17
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

SQL_FILE = os.path.join(os.path.dirname(__file__), 'alterar_view_pedidos_v11_carvia_local_cd.sql')


def run():
    app = create_app()
    with app.app_context():
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            script = f.read()
        script = script.replace('\nBEGIN;', '\n').replace('\nCOMMIT;', '\n')
        cur = db.session.connection().connection.cursor()
        cur.execute(script)
        cur.close()
        db.session.commit()
        print('  OK — VIEW pedidos + MV recriadas (v11).')

        # CarVia agora expoe VM (nao NULL)
        carvia_null = db.session.execute(text(
            "SELECT COUNT(*) FROM pedidos WHERE separacao_lote_id LIKE 'CARVIA-%' AND local_cd IS NULL"
        )).scalar()
        carvia_vm = db.session.execute(text(
            "SELECT COUNT(*) FROM pedidos WHERE separacao_lote_id LIKE 'CARVIA-%' AND local_cd = 'VICTORIO_MARCHEZINE'"
        )).scalar()
        print(f"  CarVia: NULL={carvia_null} (esperado 0) | VM={carvia_vm}")
        db.session.rollback()

        with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pedidos")
        print('  REFRESH CONCURRENTLY: OK')
        assert carvia_null == 0, 'CarVia ainda tem local_cd NULL'
        print('Migration v11 concluida.')


if __name__ == "__main__":
    run()
