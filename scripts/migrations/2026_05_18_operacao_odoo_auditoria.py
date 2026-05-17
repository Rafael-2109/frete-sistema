"""Migration idempotente: cria operacao_odoo_auditoria (polimorfica)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import inspect, text
from app import create_app, db

SQL_PATH = os.path.join(os.path.dirname(__file__), '2026_05_18_operacao_odoo_auditoria.sql')


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table('operacao_odoo_auditoria'):
            print('[INFO] Tabela operacao_odoo_auditoria ja existe — re-rodando para garantir indices')
        else:
            print('[INFO] Criando operacao_odoo_auditoria...')

        with open(SQL_PATH) as f:
            sql = f.read()
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--') and not stmt.upper() in ('BEGIN', 'COMMIT'):
                db.session.execute(text(stmt))
        db.session.commit()

        inspector = inspect(db.engine)
        assert inspector.has_table('operacao_odoo_auditoria')
        cols = {c['name'] for c in inspector.get_columns('operacao_odoo_auditoria')}
        expected = {
            'id', 'external_id', 'tabela_origem', 'registro_id', 'acao',
            'modelo_odoo', 'metodo_odoo', 'odoo_id', 'etapa', 'etapa_descricao',
            'status', 'payload_json', 'resposta_json', 'dados_antes_json',
            'dados_depois_json', 'erro_msg', 'tempo_execucao_ms',
            'contexto_origem', 'contexto_ref', 'screenshot_s3_key',
            'executado_em', 'executado_por',
        }
        missing = expected - cols
        if missing:
            raise RuntimeError(f'Colunas faltando: {missing}')
        print(f'[OK] Tabela com {len(cols)} colunas')

        indexes = {ix['name'] for ix in inspector.get_indexes('operacao_odoo_auditoria')}
        for ix in ('idx_oaa_tabela_odoo', 'idx_oaa_contexto', 'idx_oaa_status'):
            assert ix in indexes, f'Index faltando: {ix} (encontrados: {sorted(indexes)})'
        print(f'[OK] Indexes confirmados: {sorted(indexes)}')


if __name__ == '__main__':
    main()
