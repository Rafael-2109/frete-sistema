"""Migration: tabela `geocode_cache` (cache persistente de geocoding — L2).

Idempotente (CREATE TABLE IF NOT EXISTS). O boot tambem cria via create_all;
este script garante a tabela em PROD quando create_all e pulado. Uso:
    python scripts/migrations/2026_06_16_geocode_cache.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402
from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        existe_antes = 'geocode_cache' in inspect(db.engine).get_table_names()
        print('Tabela existia antes?', existe_antes)
        sql_path = os.path.join(os.path.dirname(__file__), '2026_06_16_geocode_cache.sql')
        with open(sql_path, encoding='utf-8') as f:
            statements = [s.strip() for s in f.read().split(';') if s.strip()]
        for stmt in statements:
            db.session.execute(text(stmt))
        db.session.commit()
        existe_depois = 'geocode_cache' in inspect(db.engine).get_table_names()
        assert existe_depois, 'Tabela geocode_cache nao foi criada'
        print('OK — geocode_cache disponivel.')


if __name__ == '__main__':
    main()
