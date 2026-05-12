"""
Migration: tabela remessa_vortx_conversao.

Persiste auditoria de operacoes de conversao (BMP/274 → VORTX/310) e validacao
de arquivos CNAB 400 externos feitas via UI em /remessa-vortx/converter
e /remessa-vortx/validar.

Schema: ver scripts/migrations/2026_05_12_add_remessa_vortx_conversao.sql

Idempotente via IF NOT EXISTS.

Usage:
    python scripts/migrations/2026_05_12_add_remessa_vortx_conversao.py
"""
import os
import sys

# Adiciona raiz do projeto ao sys.path quando script eh executado direto
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


TABELA = 'remessa_vortx_conversao'


def verificar_tabela() -> bool:
    result = db.session.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = :nome
    """), {'nome': TABELA}).scalar()
    return bool(result)


def verificar_indices() -> list:
    rows = db.session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = :nome
        ORDER BY indexname
    """), {'nome': TABELA}).fetchall()
    return [r[0] for r in rows]


def main() -> int:
    app = create_app()
    with app.app_context():
        existed_before = verificar_tabela()
        print(f"[before] {TABELA} exists: {existed_before}")

        print(f"[info] Criando {TABELA} (auditoria de conversor/validador externo)...")

        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS remessa_vortx_conversao (
              id                     SERIAL PRIMARY KEY,
              tipo                   VARCHAR(20) NOT NULL,
              nome_arquivo_original  VARCHAR(255) NOT NULL,
              arquivo_original       BYTEA NULL,
              arquivo_convertido     BYTEA NULL,
              banco_origem           VARCHAR(3) NULL,
              qtd_titulos            INTEGER NOT NULL DEFAULT 0,
              qtd_alteracoes         INTEGER NOT NULL DEFAULT 0,
              qtd_avisos             INTEGER NOT NULL DEFAULT 0,
              qtd_checks_falha       INTEGER NOT NULL DEFAULT 0,
              multa_codigo           VARCHAR(1) NULL,
              resultado              JSONB NULL,
              sucesso                BOOLEAN NOT NULL DEFAULT TRUE,
              erro                   TEXT NULL,
              criado_em              TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
              criado_por_id          INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
              CONSTRAINT remessa_vortx_conversao_tipo_check
                CHECK (tipo IN ('CONVERSAO', 'VALIDACAO'))
            )
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS remessa_vortx_conversao_tipo_idx
              ON remessa_vortx_conversao (tipo)
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS remessa_vortx_conversao_banco_origem_idx
              ON remessa_vortx_conversao (banco_origem)
              WHERE banco_origem IS NOT NULL
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS remessa_vortx_conversao_sucesso_idx
              ON remessa_vortx_conversao (sucesso)
        """))

        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS remessa_vortx_conversao_criado_em_idx
              ON remessa_vortx_conversao (criado_em DESC)
        """))

        db.session.execute(text("""
            COMMENT ON TABLE remessa_vortx_conversao IS
              '2026-05-12: auditoria de operacoes de conversao (BMP/274 -> VORTX/310) e '
              'validacao de arquivos CNAB 400 externos. tipo IN (CONVERSAO, VALIDACAO). '
              'CONVERSAO grava arquivo_convertido para re-download; VALIDACAO grava apenas '
              'relatorio em resultado JSONB.'
        """))

        db.session.commit()

        if not verificar_tabela():
            print("[erro] Tabela nao aparece em information_schema apos commit.")
            return 1

        indices = verificar_indices()
        expected = {
            'remessa_vortx_conversao_pkey',
            'remessa_vortx_conversao_tipo_idx',
            'remessa_vortx_conversao_banco_origem_idx',
            'remessa_vortx_conversao_sucesso_idx',
            'remessa_vortx_conversao_criado_em_idx',
        }
        missing = expected - set(indices)
        if missing:
            print(f"[erro] Indices faltando: {missing}")
            return 1

        print(f"[after] {TABELA} indexes: {indices}")

        count = db.session.execute(text(
            f"SELECT COUNT(*) FROM {TABELA}"
        )).scalar()
        print(f"[after] {TABELA} rows: {count}")

        if existed_before:
            print("[ok] Migration idempotente — tabela ja existia, schema valido.")
        else:
            print("[ok] Tabela criada com sucesso.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
