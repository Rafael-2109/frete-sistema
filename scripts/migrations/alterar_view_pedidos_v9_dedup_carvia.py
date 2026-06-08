#!/usr/bin/env python3
"""
Migration: VIEW pedidos v9 + MV mv_pedidos — v8 + DEDUP CarVia (LATERAL LIMIT 1)
===============================================================================

Corrige o BUG que travava o `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pedidos`
desde ~13/04/2026 (warning "nao-critico" no scheduler) e mantinha a MV congelada.

CAUSA RAIZ
----------
Nas Partes 2A/2B (CarVia) da VIEW/MV, o `LEFT JOIN cadastro_sub_rota` casava por
substring (`LIKE '%nome_cidade%'`) e, SEM `GROUP BY`, multiplicava linhas com o
MESMO `separacao_lote_id` (ex.: 'Itu' casava 'TaquarITUba'; 'Uru' casava 'BaURU').
Isso viola a UNIQUE `idx_mv_pedidos_lote` (obrigatoria p/ REFRESH CONCURRENTLY),
abortando o refresh a cada ciclo do scheduler.

FIX
---
Cada `LEFT JOIN cadastro_rota`/`cadastro_sub_rota` vira `LEFT JOIN LATERAL (... LIMIT 1)`,
garantindo 1 linha por lote. O desempate da sub_rota prioriza match exato e depois
nome mais longo (escolhe 'Taquarituba', nao 'Itu') — tambem melhora a QUALIDADE.

Mantem as melhorias da v8 (Parte 1 usa `min(s.equipe_vendas)` em vez de JOIN
carteira_principal; equipe_vendas validado identico ao JOIN antigo — zero regressao).

A logica SQL vive em `alterar_view_pedidos_v9_dedup_carvia.sql` (fonte unica de
verdade). Este wrapper apenas executa o .sql com verificacao before/after.

Idempotente (DROP + CREATE). Pode rodar local (DATABASE_URL) ou no Render Shell.
Data: 2026-06-08
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

SQL_FILE = os.path.join(os.path.dirname(__file__), 'alterar_view_pedidos_v9_dedup_carvia.sql')


def _snapshot(label):
    """Imprime metricas de saude da MV e retorna (mv_rows, view_lotes, duplicatas, faltando)."""
    print(f"=== {label} ===")
    mv_exists = (db.session.execute(
        text("SELECT COUNT(*) FROM pg_matviews WHERE matviewname = 'mv_pedidos'")
    ).scalar() or 0) > 0
    if not mv_exists:
        print("  mv_pedidos: NAO EXISTE")
        view_lotes = db.session.execute(
            text("SELECT COUNT(DISTINCT separacao_lote_id) FROM pedidos")
        ).scalar()
        print(f"  VIEW pedidos (live): {view_lotes} lotes")
        db.session.rollback()
        return (None, view_lotes, None, None)

    mv_rows = db.session.execute(text("SELECT COUNT(*) FROM mv_pedidos")).scalar() or 0
    mv_lotes = db.session.execute(
        text("SELECT COUNT(DISTINCT separacao_lote_id) FROM mv_pedidos")
    ).scalar() or 0
    view_lotes = db.session.execute(
        text("SELECT COUNT(DISTINCT separacao_lote_id) FROM pedidos")
    ).scalar() or 0
    faltando = db.session.execute(text(
        "SELECT COUNT(*) FROM (SELECT separacao_lote_id FROM pedidos "
        "EXCEPT SELECT separacao_lote_id FROM mv_pedidos) z"
    )).scalar() or 0
    duplicatas = mv_rows - mv_lotes
    print(f"  mv_pedidos: {mv_rows} linhas / {mv_lotes} lotes distintos "
          f"(duplicatas={duplicatas})")
    print(f"  VIEW pedidos (live): {view_lotes} lotes")
    print(f"  lotes faltando na MV: {faltando}")
    db.session.rollback()
    return (mv_rows, view_lotes, duplicatas, faltando)


def run():
    app = create_app()
    with app.app_context():
        _snapshot("BEFORE")

        print("\n=== EXECUTANDO MIGRATION (v9) ===")
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            script = f.read()
        # O .sql ja tem BEGIN/COMMIT proprios; removemos para deixar o SQLAlchemy
        # gerenciar a transacao (evita BEGIN aninhado / COMMIT prematuro).
        script = script.replace('\nBEGIN;', '\n').replace('\nCOMMIT;', '\n')
        # psycopg2 aceita multiplos statements em uma chamada (simple query protocol).
        db.session.connection().exec_driver_sql(script)
        db.session.commit()
        print("  OK — VIEW pedidos + MV mv_pedidos recriadas (v9).")

        mv_rows, view_lotes, duplicatas, faltando = _snapshot("\nAFTER")

        # Listar indices
        indices = [r[0] for r in db.session.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename='mv_pedidos' ORDER BY indexname"
        ))]
        db.session.rollback()
        print(f"\n  Indices ({len(indices)}): {', '.join(indices)}")

        # Teste do bug: REFRESH CONCURRENTLY (precisa AUTOCOMMIT, fora de transacao)
        print("\n=== TESTE REFRESH CONCURRENTLY (o que falhava) ===")
        try:
            with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.exec_driver_sql("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pedidos")
            print("  REFRESH CONCURRENTLY: OK")
        except Exception as e:
            print(f"  REFRESH CONCURRENTLY: FALHOU -> {e}")
            raise

        # Veredito
        ok = (duplicatas == 0 and faltando == 0 and mv_rows == view_lotes)
        print("\n" + ("Migration v9 concluida com sucesso!" if ok
                      else "AVISO: validacao nao bateu — revisar metricas acima."))
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    run()
