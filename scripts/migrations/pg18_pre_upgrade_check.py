"""
Pre-Upgrade Check: PostgreSQL 16 → 18
======================================
Executa verificacoes de compatibilidade ANTES do upgrade.
Deve ser executado com o banco PG 16 ainda ativo.

Uso:
    source .venv/bin/activate
    python scripts/migrations/pg18_pre_upgrade_check.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def run_check(conn, label, sql, expected=None, warn_if=None):
    """Executa uma verificacao e reporta resultado."""
    try:
        result = conn.execute(text(sql)).fetchone()
        value = result[0] if result else None

        if warn_if and warn_if(value):
            print(f"  ⚠  {label}: {value}")
            return False
        elif expected is not None and value != expected:
            print(f"  ✗  {label}: {value} (esperado: {expected})")
            return False
        else:
            print(f"  ✓  {label}: {value}")
            return True
    except Exception as e:
        print(f"  ✗  {label}: ERRO - {e}")
        return False


def main():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("PRE-UPGRADE CHECK: PostgreSQL 16 → 18")
        print("=" * 60)

        all_ok = True

        with db.engine.connect() as conn:
            # --- SECAO 1: Versao e Configuracao ---
            print("\n[1/6] VERSAO E CONFIGURACAO")
            print("-" * 40)

            result = conn.execute(text("SELECT version()")).fetchone()
            version = result[0] if result else "desconhecida"
            print(f"  ℹ  Versao atual: {version}")

            result = conn.execute(text(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )).fetchone()
            db_size = result[0] if result else "desconhecido"
            print(f"  ℹ  Tamanho do banco: {db_size}")

            # --- SECAO 2: Data Checksums ---
            print("\n[2/6] DATA CHECKSUMS")
            print("-" * 40)

            ok = run_check(
                conn,
                "data_checksums",
                "SHOW data_checksums",
                expected="on"
            )
            if ok:
                print("       PG 18 tambem usa checksums ON por default. Compativel.")
            else:
                print("       ⚠ ATENCAO: PG 18 habilita checksums por default.")
                print("       pg_upgrade pode falhar com mismatch de checksums.")
                print("       Verificar com Render suporte antes do upgrade.")
                all_ok = False

            # --- SECAO 3: Autenticacao ---
            print("\n[3/6] METODO DE AUTENTICACAO")
            print("-" * 40)

            ok = run_check(
                conn,
                "password_encryption",
                "SHOW password_encryption",
                warn_if=lambda v: v == "md5"
            )
            if not ok:
                print("       PG 18 emite warnings para senhas MD5.")
                print("       Recomendado: migrar para scram-sha-256 apos upgrade.")
                # Nao e bloqueante
                all_ok = True  # warning apenas

            # --- SECAO 4: Extensions ---
            print("\n[4/6] EXTENSIONS INSTALADAS")
            print("-" * 40)

            rows = conn.execute(text(
                "SELECT name, installed_version FROM pg_available_extensions "
                "WHERE installed_version IS NOT NULL ORDER BY name"
            )).fetchall()

            for row in rows:
                print(f"  ✓  {row[0]} v{row[1]}")

            if not rows:
                print("  ℹ  Nenhuma extension customizada instalada.")

            # --- SECAO 5: Triggers ---
            print("\n[5/6] TRIGGERS (foco em AFTER)")
            print("-" * 40)

            rows = conn.execute(text("""
                SELECT tgname, c.relname, p.proname,
                       CASE tgtype & 66
                         WHEN 2 THEN 'BEFORE'
                         WHEN 64 THEN 'INSTEAD OF'
                         ELSE 'AFTER'
                       END AS timing
                FROM pg_trigger t
                JOIN pg_class c ON t.tgrelid = c.oid
                JOIN pg_proc p ON t.tgfoid = p.oid
                WHERE NOT t.tgisinternal
                ORDER BY timing DESC, c.relname
            """)).fetchall()

            after_count = 0
            for row in rows:
                marker = "⚠" if row[3] == "AFTER" else "✓"
                print(f"  {marker}  [{row[3]}] {row[0]} em {row[1]} → {row[2]}()")
                if row[3] == "AFTER":
                    after_count += 1

            if after_count > 0:
                print(f"\n       {after_count} AFTER trigger(s) encontrado(s).")
                print("       PG 18 muda contexto de role em AFTER triggers.")
                print("       Verificar se ha SET ROLE/SET SESSION AUTHORIZATION.")

                # Verificar se funcoes dos AFTER triggers usam SET ROLE
                for row in rows:
                    if row[3] == "AFTER":
                        func_check = conn.execute(text(
                            "SELECT prosrc FROM pg_proc WHERE proname = :name"
                        ), {"name": row[2]}).fetchone()
                        if func_check:
                            src = func_check[0].lower()
                            if "set role" in src or "set session" in src:
                                print(f"  ✗  ALERTA: {row[2]}() usa SET ROLE!")
                                all_ok = False
                            else:
                                print(f"  ✓  {row[2]}(): sem SET ROLE (seguro)")
            else:
                print("  ✓  Nenhum AFTER trigger encontrado.")

            # --- SECAO 6: Indexes ---
            print("\n[6/6] INDEXES (estimativa de REINDEX)")
            print("-" * 40)

            result = conn.execute(text(
                "SELECT count(*) FROM pg_indexes WHERE schemaname = 'public'"
            )).fetchone()
            total_idx = result[0] if result else 0
            print(f"  ℹ  Total de indexes: {total_idx}")

            result = conn.execute(text("""
                SELECT count(*) FROM pg_indexes
                WHERE schemaname = 'public' AND indexdef LIKE '%WHERE%'
            """)).fetchone()
            partial_idx = result[0] if result else 0
            print(f"  ℹ  Partial indexes: {partial_idx}")

            result = conn.execute(text("""
                SELECT count(*) FROM pg_indexes
                WHERE schemaname = 'public' AND indexdef LIKE '%USING gin%'
            """)).fetchone()
            gin_idx = result[0] if result else 0
            print(f"  ℹ  GIN indexes: {gin_idx}")

            # Collation
            result = conn.execute(text(
                "SELECT datcollate, datctype FROM pg_database "
                "WHERE datname = current_database()"
            )).fetchone()
            if result:
                print(f"  ℹ  Collation: {result[0]} / CType: {result[1]}")

            print(f"\n       REINDEX sera necessario apos upgrade.")
            print(f"       Estimativa: {total_idx} indexes em {db_size}")

        # --- RESULTADO FINAL ---
        print("\n" + "=" * 60)
        if all_ok:
            print("RESULTADO: ✓ APROVADO PARA UPGRADE")
            print("Nenhum bloqueador encontrado.")
        else:
            print("RESULTADO: ✗ BLOQUEADORES ENCONTRADOS")
            print("Resolver itens marcados com ✗ antes do upgrade.")
        print("=" * 60)

        return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
