"""Garante UNIQUE (recibo_id, chassi) em assai_recibo_item."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from app import create_app, db
from sqlalchemy import text


def run():
    app = create_app()
    with app.app_context():
        sql_path = os.path.join(os.path.dirname(__file__),
                                'motos_assai_07_unique_recibo_item.sql')
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()
        print('OK: UNIQUE (recibo_id, chassi) garantido.')


if __name__ == '__main__':
    run()
