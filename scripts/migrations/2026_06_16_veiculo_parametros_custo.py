"""Migration: amplia `veiculos` com parametros de custo e capacidade.

Adiciona custo_km, custo_motorista_dia, custo_fixo_dia, depreciacao_mensal,
capacidade_pallets, capacidade_m3, velocidade_media_kmh, ativo.
Idempotente (ADD COLUMN IF NOT EXISTS). Uso:
    python scripts/migrations/2026_06_16_veiculo_parametros_custo.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402
from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)
COLS = ['custo_km', 'custo_motorista_dia', 'custo_fixo_dia', 'depreciacao_mensal',
        'capacidade_pallets', 'capacidade_m3', 'velocidade_media_kmh', 'ativo']


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        antes = {c['name'] for c in inspect(db.engine).get_columns('veiculos')}
        print('Faltando antes:', [c for c in COLS if c not in antes])
        sql_path = os.path.join(os.path.dirname(__file__), '2026_06_16_veiculo_parametros_custo.sql')
        with open(sql_path, encoding='utf-8') as f:
            statements = [s.strip() for s in f.read().split(';') if s.strip()]
        for stmt in statements:
            db.session.execute(text(stmt))
        db.session.commit()
        depois = {c['name'] for c in inspect(db.engine).get_columns('veiculos')}
        print('Faltando depois:', [c for c in COLS if c not in depois])
        assert all(c in depois for c in COLS), 'Migration nao aplicou todas as colunas'
        print('OK — migration aplicada.')


if __name__ == '__main__':
    main()
