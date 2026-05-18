"""Migration: audit log append-only de ajuste_estoque_inventario.

Cria tabela ajuste_estoque_inventario_audit + trigger AFTER INSERT/UPDATE/DELETE
em ajuste_estoque_inventario. Captura todas as mudancas independente da origem
(ORM SQLAlchemy, SQL direto, MCP, psql, scripts).

CONTEXTO (decisao 2026-05-18):
    Rafael solicitou camada de audit log SEM bloqueios para o ciclo inventario
    2026-05 que esta em andamento. Foco: forense de cancelamentos/reset de
    EXECUTADO->PROPOSTO sem rastreio (caso real: NF 626032 SEFAZ).

USO LOCAL (autorizado por feedback_migrations_local_autorizadas):
    python scripts/migrations/2026_05_18_audit_ajuste_estoque_inventario.py

USO RENDER (apos aprovacao):
    Adicionar SQL ao build.sh item 22 OU rodar manualmente no Render Shell:
        psql $DATABASE_URL -f .../2026_05_18_audit_ajuste_estoque_inventario.sql

CONSULTA POS-IMPLANTACAO:
    -- Timeline de 1 ajuste:
    SELECT registrado_em, tipo_evento, registrado_por, aplicacao,
           campos_alterados,
           dados_antes->>'status' AS status_antes,
           dados_depois->>'status' AS status_depois
    FROM ajuste_estoque_inventario_audit
    WHERE ajuste_id = 162931
    ORDER BY registrado_em;

    -- Quem alterou EXECUTADO -> PROPOSTO (reset):
    SELECT registrado_em, registrado_por, aplicacao,
           ajuste_id, dados_antes->>'invoice_id_odoo' AS invoice
    FROM ajuste_estoque_inventario_audit
    WHERE tipo_evento = 'UPDATE'
      AND 'status' = ANY(campos_alterados)
      AND dados_antes->>'status' = 'EXECUTADO'
      AND dados_depois->>'status' = 'PROPOSTO'
    ORDER BY registrado_em DESC;
"""
import os
import sys
import subprocess
from pathlib import Path
from urllib.parse import urlparse

# sys.path setup obrigatorio (feedback_migration_sys_path)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text

from app import create_app, db


SQL_FILE = Path(__file__).with_suffix('.sql')


def _print_state(prefix: str) -> None:
    """Imprime estado atual: existencia da tabela, trigger e contagem."""
    tabela_existe = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'ajuste_estoque_inventario_audit'
        )
    """)).scalar()

    trigger_existe = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'audit_ajuste_estoque_inventario_trg'
              AND NOT tgisinternal
        )
    """)).scalar()

    funcao_existe = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_proc
            WHERE proname = 'audit_ajuste_estoque_inventario_fn'
        )
    """)).scalar()

    qtd_audit = 0
    if tabela_existe:
        qtd_audit = db.session.execute(text(
            'SELECT COUNT(*) FROM ajuste_estoque_inventario_audit'
        )).scalar()

    print(f'\n[{prefix}]')
    print(f'  tabela audit existe:  {tabela_existe}')
    print(f'  funcao trigger existe: {funcao_existe}')
    print(f'  trigger ativo:        {trigger_existe}')
    print(f'  linhas em audit:       {qtd_audit}')


def main():
    app = create_app()
    with app.app_context():
        print('=== Migration: audit log ajuste_estoque_inventario ===')
        _print_state('BEFORE')

        print(f'\nExecutando SQL ({SQL_FILE.name}) via psql...')
        _run_psql(SQL_FILE)
        print('SQL executado com sucesso.')

        _print_state('AFTER')

        # Validacao final
        ok = db.session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'audit_ajuste_estoque_inventario_trg'
                  AND NOT tgisinternal
            )
        """)).scalar()
        if not ok:
            print('\nERRO: trigger nao foi criado.', file=sys.stderr)
            sys.exit(1)

        print('\nMigration aplicada com sucesso.')
        print('Proximo passo: rodar teste de validacao.')


def _run_psql(sql_path: Path) -> None:
    """Executa SQL via psql usando DATABASE_URL da app config.

    Motivo: SQL contem funcao plpgsql com $$...$$ + BEGIN/COMMIT.
    Splitter manual gera bugs sutis. psql parseia nativamente.
    """
    from flask import current_app

    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')
    if not db_url:
        raise RuntimeError('SQLALCHEMY_DATABASE_URI nao configurada')

    parsed = urlparse(db_url)
    env = os.environ.copy()
    if parsed.password:
        env['PGPASSWORD'] = parsed.password

    cmd = [
        'psql',
        '-h', parsed.hostname or 'localhost',
        '-p', str(parsed.port or 5432),
        '-U', parsed.username or 'postgres',
        '-d', parsed.path.lstrip('/'),
        '-v', 'ON_ERROR_STOP=1',
        '-f', str(sql_path),
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print('--- psql stdout ---')
        print(result.stdout)
        print('--- psql stderr ---')
        print(result.stderr)
        raise RuntimeError(f'psql falhou (exit={result.returncode})')
    if result.stdout.strip():
        print(result.stdout.strip())


if __name__ == '__main__':
    main()
