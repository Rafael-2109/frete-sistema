"""Migration idempotente: ADD session_id/tool_use_id/agent_type em operacao_odoo_auditoria.

Tambem aplica v21 (ampliar acao/status/pipeline_etapa) caso ainda nao tenha sido aplicada.

Suporta audit hook deterministico em OdooConnection.execute_kw (2026-05-28).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import inspect, text
from app import create_app, db

SQL_PATH = os.path.join(
    os.path.dirname(__file__),
    '2026_05_28_operacao_odoo_auditoria_session.sql',
)

COLUNAS_NOVAS = {'session_id', 'tool_use_id', 'agent_type'}
INDICES_NOVOS = {'idx_oaa_session_id', 'idx_oaa_tool_use_id', 'idx_oaa_agent_type'}


def _coletar_tamanhos(inspector) -> dict:
    """Retorna {coluna: tamanho_maximo} para validar ampliacao da v21."""
    tamanhos = {}
    for col in inspector.get_columns('operacao_odoo_auditoria'):
        if col['type'].__class__.__name__ == 'VARCHAR':
            tamanhos[col['name']] = col['type'].length
    return tamanhos


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('operacao_odoo_auditoria'):
            raise RuntimeError(
                'Tabela operacao_odoo_auditoria nao existe. Rode antes a migration '
                '2026_05_18_operacao_odoo_auditoria.py.'
            )

        cols_antes = {c['name'] for c in inspector.get_columns('operacao_odoo_auditoria')}
        tamanhos_antes = _coletar_tamanhos(inspector)
        indices_antes = {ix['name'] for ix in inspector.get_indexes('operacao_odoo_auditoria')}

        print('[INFO] Estado ANTES:')
        for col in sorted(COLUNAS_NOVAS):
            existe = col in cols_antes
            print(f'  - {col:<15} -> {"JA EXISTE" if existe else "AUSENTE"}')
        for col in ('acao', 'status', 'pipeline_etapa'):
            t = tamanhos_antes.get(col)
            print(f'  - {col:<15} -> VARCHAR({t})')
        for ix in sorted(INDICES_NOVOS):
            existe = ix in indices_antes
            print(f'  - {ix:<25} -> {"JA EXISTE" if existe else "AUSENTE"}')

        with open(SQL_PATH) as f:
            sql_raw = f.read()

        # Remover linhas de comentario ANTES de split — evita comentarios
        # colarem no statement seguinte e serem pulados pelo filtro.
        sql_clean = '\n'.join(
            linha for linha in sql_raw.split('\n')
            if not linha.strip().startswith('--')
        )

        for stmt in sql_clean.split(';'):
            stmt_norm = stmt.strip()
            if not stmt_norm:
                continue
            if stmt_norm.upper() in ('BEGIN', 'COMMIT'):
                continue
            db.session.execute(text(stmt_norm))
        db.session.commit()

        # Verificacao after
        inspector = inspect(db.engine)
        cols_depois = {c['name'] for c in inspector.get_columns('operacao_odoo_auditoria')}
        tamanhos_depois = _coletar_tamanhos(inspector)
        indices_depois = {ix['name'] for ix in inspector.get_indexes('operacao_odoo_auditoria')}

        print('\n[INFO] Estado DEPOIS:')
        faltando_cols = COLUNAS_NOVAS - cols_depois
        if faltando_cols:
            raise RuntimeError(f'Colunas nao adicionadas: {faltando_cols}')

        # Validar v21
        expected_sizes = {'acao': 60, 'status': 30, 'pipeline_etapa': 40}
        for col, esperado in expected_sizes.items():
            atual = tamanhos_depois.get(col)
            if atual is None or atual < esperado:
                raise RuntimeError(
                    f'Coluna {col} VARCHAR({atual}) < esperado VARCHAR({esperado}); '
                    'ALTER COLUMN TYPE falhou.'
                )
            print(f'  + {col:<15} VARCHAR({atual}) OK')

        for col in sorted(COLUNAS_NOVAS):
            print(f'  + {col:<15} ADICIONADO')

        faltando_idx = INDICES_NOVOS - indices_depois
        if faltando_idx:
            raise RuntimeError(f'Indices nao criados: {faltando_idx}')
        for ix in sorted(INDICES_NOVOS):
            print(f'  + {ix:<25} CRIADO')

        print('\n[OK] Migration aplicada com sucesso.')


if __name__ == '__main__':
    main()
