"""Adiciona campos de geocoding (latitude, longitude, geocoding_provider, geocoded_at)
em assai_loja. Idempotente via SQL DO $$ guard."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run():
    app = create_app()
    with app.app_context():
        sql_path = os.path.join(
            os.path.dirname(__file__),
            'motos_assai_08_loja_geocoding.sql',
        )
        with open(sql_path) as f:
            db.session.execute(text(f.read()))
        db.session.commit()

        # Verificacao before/after
        result = db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'assai_loja'
              AND column_name IN ('latitude', 'longitude', 'geocoding_provider', 'geocoded_at')
            ORDER BY column_name;
        """)).fetchall()

        cols = [r[0] for r in result]
        expected = ['geocoded_at', 'geocoding_provider', 'latitude', 'longitude']
        if cols == expected:
            print(f'OK: 4 colunas de geocoding adicionadas em assai_loja: {cols}')
        else:
            print(f'AVISO: colunas encontradas = {cols}, esperadas = {expected}')


if __name__ == '__main__':
    run()
