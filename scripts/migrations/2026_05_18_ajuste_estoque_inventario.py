"""Migration idempotente: cria ajuste_estoque_inventario."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import inspect, text
from app import create_app, db

SQL_PATH = os.path.join(os.path.dirname(__file__), '2026_05_18_ajuste_estoque_inventario.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH) as f:
            sql = f.read()
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--') and not stmt.upper() in ('BEGIN', 'COMMIT'):
                db.session.execute(text(stmt))
        db.session.commit()

        inspector = inspect(db.engine)
        assert inspector.has_table('ajuste_estoque_inventario')
        cols = {c['name'] for c in inspector.get_columns('ajuste_estoque_inventario')}
        expected = {
            'id', 'ciclo', 'cod_produto', 'tipo_produto', 'company_id',
            'lote_inventariado', 'lote_odoo', 'qtd_inventario', 'qtd_odoo',
            'qtd_ajuste', 'custo_medio', 'acao_decidida', 'external_id_operacao',
            'canary_passou', 'aprovado_em', 'aprovado_por', 'status', 'erro_msg',
            'criado_em', 'criado_por',
        }
        missing = expected - cols
        if missing:
            raise RuntimeError(f'Colunas faltando: {missing}')
        print(f'[OK] {len(cols)} colunas em ajuste_estoque_inventario')

        indexes = {ix['name'] for ix in inspector.get_indexes('ajuste_estoque_inventario')}
        for ix in ('idx_aei_ciclo_chave', 'idx_aei_status', 'idx_aei_acao'):
            assert ix in indexes, f'Index faltando: {ix} (encontrados: {sorted(indexes)})'
        print(f'[OK] Indexes confirmados: {sorted(indexes)}')


if __name__ == '__main__':
    main()
