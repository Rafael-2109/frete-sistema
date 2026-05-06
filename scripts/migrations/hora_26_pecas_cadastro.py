"""Migration HORA 26: cadastro de pecas.

Cria hora_peca e hora_tagplus_peca_map.

Uso:
    python scripts/migrations/hora_26_pecas_cadastro.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app import create_app, db


def existe_tabela(conn, nome: str) -> bool:
    r = conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = :n"
    ), {'n': nome}).fetchone()
    return r is not None


def main():
    app = create_app()
    with app.app_context():
        sql_path = os.path.join(os.path.dirname(__file__), 'hora_26_pecas_cadastro.sql')
        with open(sql_path, encoding='utf-8') as f:
            sql_full = f.read()

        with db.engine.connect() as conn:
            print('[before]')
            print(f'  hora_peca exists:              {existe_tabela(conn, "hora_peca")}')
            print(f'  hora_tagplus_peca_map exists:  {existe_tabela(conn, "hora_tagplus_peca_map")}')
            for stmt in [s for s in sql_full.split(';') if s.strip()]:
                conn.execute(text(stmt))
            conn.commit()
            print('[after]')
            print(f'  hora_peca exists:              {existe_tabela(conn, "hora_peca")}')
            print(f'  hora_tagplus_peca_map exists:  {existe_tabela(conn, "hora_tagplus_peca_map")}')
            print('OK - hora_26 aplicada.')


if __name__ == '__main__':
    main()
