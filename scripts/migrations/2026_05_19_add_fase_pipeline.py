"""Migration idempotente: adiciona campos de pipeline em ajuste_estoque_inventario
e operacao_odoo_auditoria. Decisao D003 pos-G004.

NOTA: Executa statements EXPLICITAMENTE (sem split por `;`) porque ALTER TABLE
com multiplos ADD COLUMN tem virgulas que confundem split ingenuo.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import inspect, text
from app import create_app, db


STATEMENTS = [
    """
    ALTER TABLE ajuste_estoque_inventario
        ADD COLUMN IF NOT EXISTS fase_pipeline VARCHAR(20),
        ADD COLUMN IF NOT EXISTS picking_id_odoo INTEGER,
        ADD COLUMN IF NOT EXISTS invoice_id_odoo INTEGER,
        ADD COLUMN IF NOT EXISTS chave_nfe VARCHAR(44)
    """,
    "CREATE INDEX IF NOT EXISTS idx_aei_fase_pipeline ON ajuste_estoque_inventario (fase_pipeline)",
    "ALTER TABLE operacao_odoo_auditoria ADD COLUMN IF NOT EXISTS pipeline_etapa VARCHAR(20)",
]


def main():
    app = create_app()
    with app.app_context():
        for stmt in STATEMENTS:
            db.session.execute(text(stmt))
            db.session.commit()

        inspector = inspect(db.engine)
        cols_aei = {c['name'] for c in inspector.get_columns('ajuste_estoque_inventario')}
        for c in ('fase_pipeline', 'picking_id_odoo', 'invoice_id_odoo', 'chave_nfe'):
            assert c in cols_aei, f'{c} faltando em ajuste_estoque_inventario'
        cols_oa = {c['name'] for c in inspector.get_columns('operacao_odoo_auditoria')}
        assert 'pipeline_etapa' in cols_oa, 'pipeline_etapa faltando em operacao_odoo_auditoria'
        print('[OK] 4 colunas adicionadas em ajuste_estoque_inventario + pipeline_etapa em operacao_odoo_auditoria')


if __name__ == '__main__':
    main()
