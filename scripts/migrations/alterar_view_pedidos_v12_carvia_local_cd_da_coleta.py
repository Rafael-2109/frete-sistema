#!/usr/bin/env python3
"""Migration: VIEW pedidos v12 — local_cd da CarVia DERIVADO da Coleta (Frente A).

As Partes 2A/2B passam de literal 'VICTORIO_MARCHEZINE' para COALESCE(cot/ped.local_cd, ...).
DEADLOCK-RESILIENTE: o .sql recria a VIEW e a MV (independentes) em TRANSACOES SEPARADAS
+ lock_timeout. Este runner executa em AUTOCOMMIT no driver, deixando os BEGIN/COMMIT do
proprio .sql controlarem as transacoes (NAO envolve tudo numa transacao unica — era o que
causava o deadlock no PROD quando view+MV eram recriadas juntas com o app lendo ambas).

Idempotente (DROP+CREATE). Rodar LOCAL ou PROD:
  SKIP_DB_CREATE=true DATABASE_URL=$DATABASE_URL_PROD python <este arquivo>
Alternativa equivalente no PROD: psql "$DATABASE_URL_PROD" -f <este .sql>
PRE-REQUISITO: 2026_06_18_carvia_pedido_cotacao_local_cd (colunas) + v11. Data: 2026-06-18
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

SQL_FILE = os.path.join(os.path.dirname(__file__), 'alterar_view_pedidos_v12_carvia_local_cd_da_coleta.sql')


def run():
    app = create_app()
    with app.app_context():
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            script = f.read()

        # AUTOCOMMIT na conexao psycopg2: os BEGIN/COMMIT do proprio .sql controlam as
        # 2 transacoes (view; depois MV). cursor.execute(script) sem params preserva o
        # '%' literal do LIKE (exec_driver_sql o trataria como placeholder e quebraria).
        raw = db.engine.raw_connection()
        try:
            dbapi = raw.driver_connection
            old_autocommit = dbapi.autocommit
            dbapi.autocommit = True
            try:
                cur = dbapi.cursor()
                cur.execute(script)
                cur.close()
            finally:
                dbapi.autocommit = old_autocommit
        finally:
            raw.close()
        print('  OK — VIEW pedidos + MV recriadas (v12, 2 transacoes).')

        carvia_null = db.session.execute(text(
            "SELECT COUNT(*) FROM pedidos WHERE separacao_lote_id LIKE 'CARVIA-%' AND local_cd IS NULL"
        )).scalar()
        carvia_tm = db.session.execute(text(
            "SELECT COUNT(*) FROM pedidos WHERE separacao_lote_id LIKE 'CARVIA-%' AND local_cd = 'TENENTE_MARQUES'"
        )).scalar()
        print(f"  CarVia: NULL={carvia_null} (esperado 0) | TM={carvia_tm}")
        db.session.rollback()

        with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pedidos")
        print('  REFRESH CONCURRENTLY: OK')
        assert carvia_null == 0, 'CarVia ainda tem local_cd NULL'
        print('Migration v12 concluida.')


if __name__ == "__main__":
    run()
