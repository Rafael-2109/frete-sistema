#!/usr/bin/env python3
"""Migration: VIEW pedidos v10 + MV mv_pedidos — v9 + coluna local_cd.

Acrescenta `local_cd` (CD de expedicao) em TODAS as ramificacoes UNION da VIEW e da MV:
  - Parte 1 (Nacom): min(s.local_cd) — de separacao (backfill VM ja aplicado).
  - Partes 2A/2B (CarVia): NULL ate a Coleta atribuir o CD (stream Coletas).

A logica SQL vive em `alterar_view_pedidos_v10_local_cd.sql` (fonte de verdade).
Este wrapper executa o .sql com verificacao before/after + testa o REFRESH CONCURRENTLY
(o invariante que a v9 corrigiu — nao pode regredir).

PRE-REQUISITO: 2026_06_17_local_cd_e_chegada_filial.py (cria separacao.local_cd).
Idempotente (DROP + CREATE). Local (DATABASE_URL) ou Render Shell.
Data: 2026-06-17
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

SQL_FILE = os.path.join(os.path.dirname(__file__), 'alterar_view_pedidos_v10_local_cd.sql')


def _metricas(label):
    print(f"=== {label} ===")
    mv_exists = (db.session.execute(
        text("SELECT COUNT(*) FROM pg_matviews WHERE matviewname = 'mv_pedidos'")
    ).scalar() or 0) > 0
    view_lotes = db.session.execute(
        text("SELECT COUNT(DISTINCT separacao_lote_id) FROM pedidos")
    ).scalar()
    if not mv_exists:
        print(f"  mv_pedidos: NAO EXISTE | VIEW pedidos: {view_lotes} lotes")
        db.session.rollback()
        return (None, view_lotes, None, None)
    mv_rows = db.session.execute(text("SELECT COUNT(*) FROM mv_pedidos")).scalar() or 0
    mv_lotes = db.session.execute(
        text("SELECT COUNT(DISTINCT separacao_lote_id) FROM mv_pedidos")
    ).scalar() or 0
    faltando = db.session.execute(text(
        "SELECT COUNT(*) FROM (SELECT separacao_lote_id FROM pedidos "
        "EXCEPT SELECT separacao_lote_id FROM mv_pedidos) z"
    )).scalar() or 0
    duplicatas = mv_rows - mv_lotes
    print(f"  mv_pedidos: {mv_rows} linhas / {mv_lotes} lotes (dup={duplicatas}) | "
          f"VIEW: {view_lotes} lotes | faltando MV: {faltando}")
    db.session.rollback()
    return (mv_rows, view_lotes, duplicatas, faltando)


def run():
    app = create_app()
    with app.app_context():
        _metricas("BEFORE")

        print("\n=== EXECUTANDO MIGRATION (v10) ===")
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            script = f.read()
        # O .sql ja tem BEGIN/COMMIT proprios; removemos p/ o SQLAlchemy gerenciar a transacao.
        script = script.replace('\nBEGIN;', '\n').replace('\nCOMMIT;', '\n')
        # cursor DBAPI cru SEM params: psycopg2 nao interpola o `%` literal de `LIKE '%'`
        # (exec_driver_sql passaria um dict vazio e o `%` quebraria com "not a sequence").
        raw_conn = db.session.connection().connection
        cur = raw_conn.cursor()
        cur.execute(script)
        cur.close()
        db.session.commit()
        print("  OK — VIEW pedidos + MV recriadas (v10).")

        # local_cd existe na VIEW e na MV? (pg_attribute cobre matview, que NAO
        # aparece em information_schema.columns no PostgreSQL).
        for rel in ('pedidos', 'mv_pedidos'):
            tem = db.session.execute(text(
                "SELECT COUNT(*) FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid "
                "WHERE c.relname = :t AND a.attname = 'local_cd' "
                "AND a.attnum > 0 AND NOT a.attisdropped"
            ), {'t': rel}).scalar()
            assert tem == 1, f"coluna local_cd ausente em {rel}"
            print(f"  coluna local_cd presente em {rel}: OK")
        db.session.rollback()

        mv_rows, view_lotes, duplicatas, faltando = _metricas("\nAFTER")

        # Invariante v9: REFRESH CONCURRENTLY nao pode regredir
        print("\n=== TESTE REFRESH CONCURRENTLY ===")
        with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pedidos")
        print("  REFRESH CONCURRENTLY: OK")

        ok = (duplicatas == 0 and faltando == 0 and mv_rows == view_lotes)
        print("\n" + ("Migration v10 concluida com sucesso!" if ok
                      else "AVISO: validacao nao bateu — revisar metricas acima."))
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    run()
