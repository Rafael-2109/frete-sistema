#!/usr/bin/env python3
"""
Migration: Criar tabela grupo_transportadora e FK em transportadoras
Data: 2026-02-14
Descricao: Permite agrupar transportadoras que operam com multiplos CNPJs
           para matching correto de CTe -> Frete
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def verificar_antes(conn):
    """Verifica estado antes da migration"""
    # Verificar se tabela grupo_transportadora ja existe
    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'grupo_transportadora'
        )
    """))
    tabela_existe = result.scalar()

    # Verificar se coluna grupo_transportadora_id ja existe em transportadoras
    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'transportadoras'
            AND column_name = 'grupo_transportadora_id'
        )
    """))
    coluna_existe = result.scalar()

    print(f"[BEFORE] Tabela grupo_transportadora existe: {tabela_existe}")
    print(f"[BEFORE] Coluna grupo_transportadora_id em transportadoras: {coluna_existe}")

    return tabela_existe, coluna_existe


def executar_migration(tabela_existe, coluna_existe):
    """Executa a migration dentro de uma transacao"""
    with db.engine.begin() as conn:
        if not tabela_existe:
            print("[EXEC] Criando tabela grupo_transportadora...")
            conn.execute(db.text("""
                CREATE TABLE grupo_transportadora (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL UNIQUE,
                    descricao TEXT,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    criado_por VARCHAR(100)
                )
            """))
            print("[EXEC] Tabela grupo_transportadora criada.")
        else:
            print("[EXEC] Tabela grupo_transportadora ja existe, pulando.")

        if not coluna_existe:
            print("[EXEC] Adicionando coluna grupo_transportadora_id em transportadoras...")
            conn.execute(db.text("""
                ALTER TABLE transportadoras
                ADD COLUMN grupo_transportadora_id INTEGER
                REFERENCES grupo_transportadora(id)
            """))
            print("[EXEC] Coluna adicionada.")
        else:
            print("[EXEC] Coluna grupo_transportadora_id ja existe, pulando.")

        # Indice (idempotente)
        print("[EXEC] Criando indice idx_transportadoras_grupo...")
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS idx_transportadoras_grupo
            ON transportadoras(grupo_transportadora_id)
        """))
        print("[EXEC] Indice criado/verificado.")


def verificar_depois(conn):
    """Verifica estado apos a migration"""
    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'grupo_transportadora'
        )
    """))
    tabela_existe = result.scalar()

    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'transportadoras'
            AND column_name = 'grupo_transportadora_id'
        )
    """))
    coluna_existe = result.scalar()

    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'idx_transportadoras_grupo'
        )
    """))
    indice_existe = result.scalar()

    print(f"[AFTER] Tabela grupo_transportadora existe: {tabela_existe}")
    print(f"[AFTER] Coluna grupo_transportadora_id em transportadoras: {coluna_existe}")
    print(f"[AFTER] Indice idx_transportadoras_grupo existe: {indice_existe}")

    if tabela_existe and coluna_existe and indice_existe:
        print("\n[OK] Migration concluida com sucesso!")
    else:
        print("\n[ERRO] Migration incompleta!")
        sys.exit(1)


def main():
    app = create_app()
    with app.app_context():
        # BEFORE — conexao separada
        with db.engine.connect() as conn:
            tabela_existe, coluna_existe = verificar_antes(conn)

        # EXECUTE — transacao auto-commit
        executar_migration(tabela_existe, coluna_existe)

        # AFTER — conexao separada
        with db.engine.connect() as conn:
            verificar_depois(conn)


if __name__ == '__main__':
    main()
