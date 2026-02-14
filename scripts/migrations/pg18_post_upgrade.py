"""
Post-Upgrade: PostgreSQL 16 → 18
=================================
Executa acoes obrigatorias APOS o upgrade do PostgreSQL.
- REINDEX DATABASE
- ANALYZE em todas as tabelas
- Verificacao de extensions
- Teste de triggers criticos

IMPORTANTE: Este script causa downtime durante o REINDEX.
Executar em janela de manutencao.

Uso:
    source .venv/bin/activate
    python scripts/migrations/pg18_post_upgrade.py [--force]

Flags:
    --force     Prosseguir mesmo se versao nao for PG18 (util para testes)
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def main():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("POST-UPGRADE: PostgreSQL 16 → 18")
        print("=" * 60)

        # --- Verificar versao ---
        print("\n[1/6] VERIFICANDO VERSAO")
        print("-" * 40)

        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT version()")).fetchone()
            version = result[0] if result else "desconhecida"
            print(f"  ℹ  Versao: {version}")

            if "PostgreSQL 18" not in version:
                print(f"\n  ⚠  ATENCAO: Versao nao e PostgreSQL 18!")
                print(f"     Este script e para execucao POS-UPGRADE.")
                if "--force" not in sys.argv:
                    print("     Use --force para continuar mesmo assim.")
                    return 1
                print("     --force detectado, continuando...")

        # --- REINDEX ---
        print("\n[2/6] REINDEX DATABASE")
        print("-" * 40)
        print("  ℹ  Isso pode demorar alguns minutos...")
        print("  ℹ  O banco ficara indisponivel durante o REINDEX.")

        start = time.time()
        try:
            # REINDEX DATABASE precisa de autocommit (nao pode rodar em transacao)
            with db.engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
            ) as conn:
                db_name = conn.execute(text("SELECT current_database()")).scalar()
                print(f"  ℹ  Database: {db_name}")
                conn.execute(text(f'REINDEX DATABASE "{db_name}"'))
            elapsed = time.time() - start
            print(f"  ✓  REINDEX concluido em {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ✗  REINDEX falhou apos {elapsed:.1f}s: {e}")
            print("  ℹ  Tentando REINDEX por schema...")

            try:
                with db.engine.connect().execution_options(
                    isolation_level="AUTOCOMMIT"
                ) as conn:
                    conn.execute(text("REINDEX SCHEMA public"))
                print(f"  ✓  REINDEX SCHEMA public concluido")
            except Exception as e2:
                print(f"  ✗  REINDEX SCHEMA tambem falhou: {e2}")
                print("  ℹ  Execute manualmente: REINDEX SCHEMA public;")

        # --- ANALYZE ---
        print("\n[3/6] ANALYZE (atualizando estatisticas)")
        print("-" * 40)

        start = time.time()
        try:
            with db.engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
            ) as conn:
                conn.execute(text("ANALYZE"))
            elapsed = time.time() - start
            print(f"  ✓  ANALYZE concluido em {elapsed:.1f}s")
        except Exception as e:
            print(f"  ✗  ANALYZE falhou: {e}")
            print("  ℹ  Execute manualmente: ANALYZE;")

        # --- Verificar Extensions ---
        print("\n[4/6] VERIFICANDO EXTENSIONS")
        print("-" * 40)

        with db.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT name, installed_version, default_version "
                "FROM pg_available_extensions "
                "WHERE installed_version IS NOT NULL ORDER BY name"
            )).fetchall()

            for row in rows:
                if row[1] != row[2]:
                    print(f"  ⚠  {row[0]}: v{row[1]} → v{row[2]} disponivel")
                    print(f"       Para atualizar: ALTER EXTENSION {row[0]} UPDATE;")
                else:
                    print(f"  ✓  {row[0]}: v{row[1]} (atual)")

        # --- Testes de Trigger ---
        print("\n[5/6] VERIFICANDO TRIGGERS")
        print("-" * 40)

        with db.engine.connect() as conn:
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
                ORDER BY c.relname
            """)).fetchall()

            for row in rows:
                marker = "✓" if row[3] == "BEFORE" else "ℹ"
                print(f"  {marker}  [{row[3]}] {row[0]} em {row[1]} → {row[2]}()")

            print(f"\n  ℹ  Total: {len(rows)} triggers ativos")

        # --- Verificar Collation / Ordering ---
        print("\n[6/6] VERIFICANDO COLLATION E ORDERING")
        print("-" * 40)

        with db.engine.connect() as conn:
            # Collation do banco
            result = conn.execute(text(
                "SELECT datcollate, datctype FROM pg_database "
                "WHERE datname = current_database()"
            )).fetchone()
            if result:
                print(f"  ℹ  Collation: {result[0]}  /  Ctype: {result[1]}")

            # Teste de ordering com dados reais (strings acentuadas)
            print("  ℹ  Teste de ordering com strings acentuadas...")
            try:
                rows = conn.execute(text(
                    "SELECT nome_cidade, cod_uf FROM carteira_principal "
                    "WHERE nome_cidade LIKE 'São%%' "
                    "ORDER BY nome_cidade LIMIT 5"
                )).fetchall()
                if rows:
                    for row in rows:
                        print(f"       {row[0]} / {row[1]}")
                    print("  ✓  Ordering OK — verificar visualmente se ordem e consistente")
                else:
                    print("  ℹ  Nenhuma cidade com 'São' encontrada para teste")
            except Exception as e:
                print(f"  ⚠  Teste de ordering falhou: {e}")
                print("     Verificar manualmente apos upgrade.")

        # --- Verificar MD5 ---
        print("\n[EXTRA] VERIFICANDO PASSWORD ENCRYPTION")
        print("-" * 40)

        with db.engine.connect() as conn:
            result = conn.execute(text("SHOW password_encryption")).fetchone()
            method = result[0] if result else "desconhecido"

            if method == "md5":
                print(f"  ⚠  password_encryption = md5")
                print("     PG 18 emite warnings para MD5.")
                print("     Recomendado: solicitar migracao SCRAM-SHA-256 ao Render.")
            else:
                print(f"  ✓  password_encryption = {method}")

        # --- Resultado ---
        print("\n" + "=" * 60)
        print("POST-UPGRADE CONCLUIDO")
        print("=" * 60)
        print("\nProximos passos:")
        print("  1. Testar fluxos criticos (separacao, faturamento)")
        print("  2. Testar triggers: criar embarque_item, atualizar ordem_producao")
        print("  3. Monitorar metricas de performance por 24h")
        print("  4. Verificar logs para MD5 warnings")
        if method == "md5":
            print("  5. Planejar migracao md5 → scram-sha-256")

        return 0


if __name__ == "__main__":
    sys.exit(main())
