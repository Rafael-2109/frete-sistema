#!/usr/bin/env python3
"""Migration: local_cd em carvia_pedidos + carvia_cotacoes (Frente A do redesign CarVia).

Adiciona a coluna `local_cd` nas 2 tabelas (default VM = backfill historico), indices
parciais (TM) e propaga TM retroativo a partir das CarviaNf ja marcadas (via numero_nf).
A VIEW pedidos passa a ler essas colunas na migration alterar_view_pedidos_v12_*.

Idempotente. Rodar LOCAL ou PROD:
  SKIP_DB_CREATE=true DATABASE_URL=$DATABASE_URL_PROD python <este arquivo>
Data: 2026-06-18
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402

SQL_FILE = os.path.join(os.path.dirname(__file__), '2026_06_18_carvia_pedido_cotacao_local_cd.sql')


def run():
    app = create_app()
    with app.app_context():
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            script = f.read()
        cur = db.session.connection().connection.cursor()
        cur.execute(script)
        cur.close()
        db.session.commit()
        print('  OK — colunas local_cd + indices + backfill aplicados.')

        for tabela in ('carvia_cotacoes', 'carvia_pedidos'):
            tm = db.session.execute(text(
                f"SELECT COUNT(*) FROM {tabela} WHERE local_cd = 'TENENTE_MARQUES'"
            )).scalar()
            nulos = db.session.execute(text(
                f"SELECT COUNT(*) FROM {tabela} WHERE local_cd IS NULL"
            )).scalar()
            print(f"  {tabela}: TM={tm} | NULL={nulos} (esperado 0)")
            assert nulos == 0, f'{tabela} tem local_cd NULL'
        db.session.rollback()
        print('Migration concluida.')


if __name__ == "__main__":
    run()
