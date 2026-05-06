"""Migration HORA 27: movimento + itens peca (NF entrada / venda) + ALTER pedido_item."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app import create_app, db


def main():
    app = create_app()
    with app.app_context():
        sql_path = os.path.join(os.path.dirname(__file__), 'hora_27_pecas_movimento_e_itens.sql')
        with open(sql_path, encoding='utf-8') as f:
            sql_full = f.read()

        with db.engine.connect() as conn:
            print('[before]')
            for tab in ('hora_peca_movimento', 'hora_nf_entrada_item_peca', 'hora_venda_item_peca'):
                exists = conn.execute(text(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = :n"
                ), {'n': tab}).fetchone() is not None
                print(f'  {tab:35s} exists: {exists}')
            col_peca = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='hora_pedido_item' AND column_name='peca_id'"
            )).fetchone() is not None
            print(f'  hora_pedido_item.peca_id col exists: {col_peca}')

            # Executa o SQL inteiro (DO $$ ... $$ exige execucao como bloco).
            conn.execute(text(sql_full))
            conn.commit()

            print('[after]')
            for tab in ('hora_peca_movimento', 'hora_nf_entrada_item_peca', 'hora_venda_item_peca'):
                exists = conn.execute(text(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = :n"
                ), {'n': tab}).fetchone() is not None
                print(f'  {tab:35s} exists: {exists}')
            col_peca = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='hora_pedido_item' AND column_name='peca_id'"
            )).fetchone() is not None
            print(f'  hora_pedido_item.peca_id col exists: {col_peca}')
            print('OK - hora_27 aplicada.')


if __name__ == '__main__':
    main()
