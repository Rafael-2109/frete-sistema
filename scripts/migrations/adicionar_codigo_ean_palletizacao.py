#!/usr/bin/env python3
"""
Migration: Adicionar campo codigo_ean em cadastro_palletizacao.

Permite vincular produtos do portal Atacadao (que usam EAN/GTIN)
ao cadastro interno de palletizacao.

Fonte do EAN: Odoo product.template.barcode_nacom

Uso:
    source .venv/bin/activate
    python scripts/migrations/adicionar_codigo_ean_palletizacao.py
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


DDL = [
    "ALTER TABLE cadastro_palletizacao ADD COLUMN IF NOT EXISTS codigo_ean VARCHAR(50)",
    "CREATE INDEX IF NOT EXISTS idx_cadastro_palletizacao_ean ON cadastro_palletizacao(codigo_ean)",
    "COMMENT ON COLUMN cadastro_palletizacao.codigo_ean IS 'Codigo EAN/GTIN do produto. Fonte: Odoo product.template.barcode_nacom'",
]


def verificar_before(db):
    """Verifica estado ANTES da migration."""
    resultado = db.session.execute(
        db.text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'cadastro_palletizacao'
              AND column_name = 'codigo_ean'
        """)
    ).fetchall()

    if resultado:
        print("[BEFORE] Campo codigo_ean JA EXISTE. Migration sera idempotente.")
        return True
    else:
        print("[BEFORE] Campo codigo_ean NAO existe. Sera criado.")
        return False


def executar_migration(db):
    """Executa DDL statements."""
    for stmt in DDL:
        print(f"  Executando: {stmt[:80]}...")
        db.session.execute(db.text(stmt))
    db.session.commit()
    print("[OK] DDL executado com sucesso.")


def verificar_after(db):
    """Verifica estado APOS a migration."""
    # Verificar coluna
    resultado = db.session.execute(
        db.text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'cadastro_palletizacao'
              AND column_name = 'codigo_ean'
        """)
    ).fetchone()

    if not resultado:
        print("[ERRO] Campo codigo_ean NAO foi criado!")
        return False

    print(f"[AFTER] Campo codigo_ean: type={resultado.data_type}, max_length={resultado.character_maximum_length}")

    # Verificar indice
    idx = db.session.execute(
        db.text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'cadastro_palletizacao'
              AND indexname = 'idx_cadastro_palletizacao_ean'
        """)
    ).fetchone()

    if idx:
        print(f"[AFTER] Indice encontrado: {idx.indexname}")
    else:
        print("[AVISO] Indice idx_cadastro_palletizacao_ean NAO encontrado.")

    return True


def main():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration: adicionar_codigo_ean_palletizacao")
        print("=" * 60)

        ja_existe = verificar_before(db)
        executar_migration(db)
        ok = verificar_after(db)

        if ok:
            print("\n[SUCESSO] Migration concluida.")
        else:
            print("\n[FALHA] Verificacao pos-migration falhou.")
            sys.exit(1)


if __name__ == "__main__":
    main()
