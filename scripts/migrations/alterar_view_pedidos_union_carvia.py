"""
Migration: VIEW pedidos com UNION ALL para CarVia (3 partes)
Data: 2026-03-21 (v2)
Descricao:
  Parte 1: Pedidos Nacom (Separacao) — INALTERADO
  Parte 2A: Cotacoes CarVia APROVADAS SEM pedidos (provisorias, CARVIA-{id})
  Parte 2B: Pedidos CarVia individuais (quando cotacao tem pedidos, CARVIA-PED-{id})
  Efeito: cotacao com 0 pedidos = 1 linha. Com N pedidos = N linhas (cotacao some).
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes(conn):
    """Verifica estado antes da migration"""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.views "
        "  WHERE table_name = 'pedidos'"
        ")"
    ))
    print(f"[ANTES] VIEW pedidos existe: {result.scalar()}")

    # Contar registros atuais
    try:
        result = conn.execute(db.text("SELECT COUNT(*) FROM pedidos"))
        print(f"[ANTES] Registros na VIEW: {result.scalar()}")
    except Exception:
        print("[ANTES] VIEW nao acessivel")

    # Verificar se tabelas CarVia existem
    for tab in ['carvia_cotacoes', 'carvia_cliente_enderecos', 'carvia_pedidos']:
        result = conn.execute(db.text(
            f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{tab}')"
        ))
        print(f"[ANTES] {tab} existe: {result.scalar()}")


def executar_migration(conn):
    """Executa DDL — recria VIEW com UNION ALL"""
    # Ler SQL do arquivo .sql
    sql_path = os.path.join(os.path.dirname(__file__), 'alterar_view_pedidos_union_carvia.sql')
    with open(sql_path, 'r') as f:
        sql = f.read()

    # Remover comentarios SQL para execucao limpa
    conn.execute(db.text(sql))
    print("[OK] VIEW pedidos recriada com UNION ALL CarVia")


def verificar_depois(conn):
    """Verifica estado apos migration"""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.views "
        "  WHERE table_name = 'pedidos'"
        ")"
    ))
    print(f"[DEPOIS] VIEW pedidos existe: {result.scalar()}")

    try:
        result = conn.execute(db.text("SELECT COUNT(*) FROM pedidos"))
        print(f"[DEPOIS] Total registros: {result.scalar()}")

        result = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos WHERE rota = 'CARVIA'"
        ))
        print(f"[DEPOIS] Registros CarVia: {result.scalar()}")

        result = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos WHERE rota IS DISTINCT FROM 'CARVIA'"
        ))
        print(f"[DEPOIS] Registros Nacom: {result.scalar()}")
    except Exception as e:
        print(f"[DEPOIS] Erro ao verificar: {e}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: VIEW pedidos UNION ALL CarVia")
            print("=" * 60)

            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)

            print("=" * 60)
            print("Migration concluida com sucesso!")
