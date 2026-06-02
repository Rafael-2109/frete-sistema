#!/usr/bin/env python3
"""
Migration: split de NF por protocolo ST (Atacadão RJ).

Adiciona:
    regiao_tabela_rede.separar_protocolo_st       BOOLEAN NOT NULL DEFAULT FALSE
    portal_atacadao_produto_depara.protocolo_st   BOOLEAN NOT NULL DEFAULT FALSE

Execução:
    source .venv/bin/activate
    python scripts/migrations/2026_06_02_atacadao_protocolo_st.py

Data: 2026-06-02
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


COLUNAS_ESPERADAS = {
    "regiao_tabela_rede": ["separar_protocolo_st"],
    "portal_atacadao_produto_depara": ["protocolo_st"],
}


def verificar_colunas() -> dict:
    resultado: dict = {}
    for tabela, cols in COLUNAS_ESPERADAS.items():
        resultado[tabela] = {}
        for col in cols:
            existe = db.session.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=:t AND column_name=:c)"
                ),
                {"t": tabela, "c": col},
            ).scalar()
            resultado[tabela][col] = bool(existe)
    return resultado


def executar_migration():
    app = create_app()
    with app.app_context():
        print("=" * 78)
        print("MIGRATION: protocolo ST (regiao_tabela_rede + portal_atacadao_produto_depara)")
        print("=" * 78)

        print("\n[BEFORE]")
        antes = verificar_colunas()
        for tabela, cols in antes.items():
            for col, existe in cols.items():
                print(f"  [{'OK' if existe else '--'}] {tabela}.{col}")

        sql_path = Path(__file__).with_suffix(".sql")
        print(f"\n[EXEC] Executando {sql_path.name}...")
        sql_content = sql_path.read_text(encoding="utf-8")

        try:
            db.session.execute(text(sql_content))
            db.session.commit()
            print("[EXEC] OK — SQL executado com sucesso.")
        except Exception as exc:
            db.session.rollback()
            print(f"[ERRO] {exc}")
            raise

        print("\n[AFTER]")
        depois = verificar_colunas()
        todas_ok = True
        for tabela, cols in depois.items():
            for col, existe in cols.items():
                print(f"  [{'OK' if existe else '--'}] {tabela}.{col}")
                todas_ok = todas_ok and existe

        if not todas_ok:
            raise RuntimeError("Migration falhou: nem todas as colunas foram criadas.")
        print("\n[DONE] Migration concluída com sucesso.")


if __name__ == "__main__":
    executar_migration()
