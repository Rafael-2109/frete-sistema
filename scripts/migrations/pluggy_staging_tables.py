#!/usr/bin/env python3
"""
Migration: Pluggy Staging Tables (Fase 1)
==========================================
Cria 4 tabelas staging para Pluggy Open Finance sem tocar em
pessoal_transacoes/pessoal_contas.

Tabelas criadas:
    1. pessoal_pluggy_items        — conexoes OAuth (1 item = 1 banco)
    2. pessoal_pluggy_accounts     — contas retornadas pelo item (BANK/CREDIT)
    3. pessoal_pluggy_transacoes_stg — transacoes fieis ao payload
    4. pessoal_pluggy_categorias_map — mapeamento categoryId Pluggy -> local

Execucao:
    # Local
    source .venv/bin/activate
    python scripts/migrations/pluggy_staging_tables.py

    # Render Shell (recomendado em producao)
    psql $DATABASE_URL -f scripts/migrations/pluggy_staging_tables.sql

Data: 2026-04-21
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db
from sqlalchemy import text


TABELAS_ALVO = [
    "pessoal_pluggy_items",
    "pessoal_pluggy_accounts",
    "pessoal_pluggy_transacoes_stg",
    "pessoal_pluggy_categorias_map",
]


def verificar_tabelas() -> dict[str, bool]:
    """Retorna dict {tabela: existe}."""
    resultado = {}
    for tabela in TABELAS_ALVO:
        existe = db.session.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=:t)"
            ),
            {"t": tabela},
        ).scalar()
        resultado[tabela] = bool(existe)
    return resultado


def executar_migration():
    app = create_app()
    with app.app_context():
        print("=" * 78)
        print("MIGRATION: Pluggy Staging Tables (Fase 1)")
        print("=" * 78)

        print("\n[BEFORE] Estado atual das tabelas:")
        antes = verificar_tabelas()
        for tab, existe in antes.items():
            simbolo = "OK" if existe else "--"
            print(f"  [{simbolo}] {tab}")

        sql_path = Path(__file__).parent / "pluggy_staging_tables.sql"
        if not sql_path.exists():
            raise FileNotFoundError(f"SQL nao encontrado: {sql_path}")

        print(f"\n[EXEC] Executando {sql_path.name} ...")
        sql_content = sql_path.read_text(encoding="utf-8")

        try:
            db.session.execute(text(sql_content))
            db.session.commit()
            print("[EXEC] OK — SQL executado com sucesso.")
        except Exception as exc:
            db.session.rollback()
            print(f"[ERRO] {exc}")
            raise

        print("\n[AFTER] Estado apos migration:")
        depois = verificar_tabelas()
        todas_ok = True
        for tab, existe in depois.items():
            simbolo = "OK" if existe else "FAIL"
            print(f"  [{simbolo}] {tab}")
            if not existe:
                todas_ok = False

        print("\n" + "=" * 78)
        if todas_ok:
            print("SUCESSO — 4 tabelas criadas (ou ja existentes).")
            print("Proximo passo: F2 (Ingestao) — pluggy_client, sync service, rotas.")
        else:
            print("FALHA — alguma tabela nao foi criada. Verificar erros acima.")
            sys.exit(1)
        print("=" * 78)


if __name__ == "__main__":
    executar_migration()
