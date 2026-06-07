"""
Migration: VIEW pedidos v8 + MV mv_pedidos — remove o LEFT JOIN carteira_principal

Data: 2026-06-07
Descricao:
    Recria a VIEW pedidos (v8) e a MV mv_pedidos eliminando o LEFT JOIN com
    carteira_principal da Parte 1 (Nacom). equipe_vendas passa a vir de
    min(s.equipe_vendas) — coluna desnormalizada em separacao.

    GANHO MEDIDO (EXPLAIN ANALYZE producao): Parte 1 de ~710ms -> ~26ms/scan.
    Equivalencia v7 vs v8 validada no banco local: 0 divergencias de equipe
    por lote.

    O SQL canonico vive em alterar_view_pedidos_v8.sql (mesmo diretorio) — este
    .py o executa via conn.execute(db.text(...)) (mesmo mecanismo da v7.py, que
    suporta multi-statement + '%' literais das clausulas LIKE da CarVia).

PRE-REQUISITO: add_equipe_vendas_separacao (coluna + backfill) DEVE ter rodado.

Executar: python scripts/migrations/alterar_view_pedidos_v8.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes(conn):
    """Guard: a coluna desnormalizada precisa existir (pre-requisito)."""
    col_existe = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.columns "
        "  WHERE table_name = 'separacao' AND column_name = 'equipe_vendas'"
        ")"
    )).scalar()
    print(f"[ANTES] separacao.equipe_vendas existe: {col_existe}")
    if not col_existe:
        raise RuntimeError(
            "separacao.equipe_vendas nao existe. Execute "
            "add_equipe_vendas_separacao.py ANTES desta migration."
        )

    existe_view = conn.execute(db.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'pedidos')"
    )).scalar()
    print(f"[ANTES] VIEW pedidos existe: {existe_view}")


def executar_migration(conn):
    """Executa DDL — recria VIEW v8 + MV mv_pedidos sem o JOIN."""
    sql_path = os.path.join(os.path.dirname(__file__), 'alterar_view_pedidos_v8.sql')
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    conn.execute(db.text(sql))
    print("[OK] VIEW pedidos (v8) e MV mv_pedidos recriadas sem JOIN carteira_principal")


def verificar_depois(conn):
    """Verifica VIEW/MV pos-migration."""
    total = conn.execute(db.text("SELECT COUNT(*) FROM pedidos")).scalar()
    com_equipe = conn.execute(db.text(
        "SELECT COUNT(*) FROM pedidos WHERE equipe_vendas IS NOT NULL"
    )).scalar()
    print(f"[DEPOIS] VIEW pedidos: {total} linhas | {com_equipe} com equipe_vendas")

    # A VIEW v8 NAO pode mais depender de carteira_principal
    depende_carteira = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.view_table_usage "
        "  WHERE view_name = 'pedidos' AND table_name = 'carteira_principal'"
        ")"
    )).scalar()
    print(f"[DEPOIS] VIEW pedidos ainda depende de carteira_principal: {depende_carteira} (esperado False)")
    if depende_carteira:
        raise RuntimeError("VIEW v8 ainda referencia carteira_principal — JOIN nao removido!")

    mv_pop = conn.execute(db.text(
        "SELECT ispopulated FROM pg_matviews WHERE matviewname = 'mv_pedidos'"
    )).scalar()
    print(f"[DEPOIS] MV mv_pedidos ispopulated: {mv_pop}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: VIEW pedidos v8 + MV (remove JOIN carteira_principal)")
            print("=" * 60)
            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)
            print("=" * 60)
            print("Migration concluida com sucesso!")
