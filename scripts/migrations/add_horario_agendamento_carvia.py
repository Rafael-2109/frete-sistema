"""
Migration: campos de horario de agendamento (feature CarVia)
Data: 2026-05-21

Adiciona (o fluxo Nacom NAO usa horario):
  carvia_cotacoes.horario_agenda   (TIME) — FONTE (cotacao comercial CarVia)
  embarque_itens.hora_agendamento  (TIME) — RECEPTOR (propagado; Nacom = NULL)

O destino final (agendamentos_entrega.hora_agendada) ja existe.
Idempotente (ADD COLUMN IF NOT EXISTS). Executar no Render Shell.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


COLUNAS = [
    ('carvia_cotacoes', 'horario_agenda'),
    ('embarque_itens', 'hora_agendamento'),
]


def _coluna_existe(conn, tabela, coluna):
    return conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.columns "
        "  WHERE table_name = :t AND column_name = :c"
        ")"
    ), {"t": tabela, "c": coluna}).scalar()


def verificar_antes(conn):
    for tabela, coluna in COLUNAS:
        print(f"[ANTES] {tabela}.{coluna} existe: {_coluna_existe(conn, tabela, coluna)}")


def executar_migration(conn):
    sql_path = os.path.join(os.path.dirname(__file__), 'add_horario_agendamento_carvia.sql')
    with open(sql_path, 'r') as f:
        sql = f.read()
    conn.execute(db.text(sql))
    print("[OK] Colunas de horario adicionadas (idempotente)")


def verificar_depois(conn):
    for tabela, coluna in COLUNAS:
        existe = _coluna_existe(conn, tabela, coluna)
        print(f"[DEPOIS] {tabela}.{coluna} existe: {existe}")
        if not existe:
            raise RuntimeError(f"Coluna {tabela}.{coluna} nao foi criada!")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: horario de agendamento CarVia")
            print("=" * 60)
            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)
            print("=" * 60)
            print("Migration concluida com sucesso!")
