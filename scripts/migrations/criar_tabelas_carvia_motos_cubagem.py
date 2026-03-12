"""
Migration: Criar tabelas carvia_modelos_moto e carvia_empresas_cubagem
========================================================================

Tabelas para calculo automatico de peso cubado de motos.

Executar: python scripts/migrations/criar_tabelas_carvia_motos_cubagem.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def run_migration():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        # ---- BEFORE ----
        result = conn.execute(db.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'carvia_modelos_moto')"
        ))
        moto_exists = result.scalar()

        result = conn.execute(db.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'carvia_empresas_cubagem')"
        ))
        cubagem_exists = result.scalar()

        print(f"[BEFORE] carvia_modelos_moto exists: {moto_exists}")
        print(f"[BEFORE] carvia_empresas_cubagem exists: {cubagem_exists}")

        # ---- CREATE carvia_modelos_moto ----
        if not moto_exists:
            conn.execute(db.text("""
                CREATE TABLE carvia_modelos_moto (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL,
                    regex_pattern VARCHAR(200),
                    comprimento NUMERIC(10,4) NOT NULL,
                    largura NUMERIC(10,4) NOT NULL,
                    altura NUMERIC(10,4) NOT NULL,
                    peso_medio NUMERIC(10,3),
                    cubagem_minima NUMERIC(10,2) NOT NULL DEFAULT 300,
                    ativo BOOLEAN DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    criado_por VARCHAR(100) NOT NULL
                )
            """))
            conn.execute(db.text(
                "CREATE UNIQUE INDEX uq_carvia_modelos_moto_nome "
                "ON carvia_modelos_moto (nome)"
            ))
            conn.commit()
            print("[OK] carvia_modelos_moto criada com indice UNIQUE(nome)")
        else:
            print("[SKIP] carvia_modelos_moto ja existe")

        # ---- CREATE carvia_empresas_cubagem ----
        if not cubagem_exists:
            conn.execute(db.text("""
                CREATE TABLE carvia_empresas_cubagem (
                    id SERIAL PRIMARY KEY,
                    cnpj_empresa VARCHAR(20) NOT NULL,
                    nome_empresa VARCHAR(255) NOT NULL,
                    considerar_cubagem BOOLEAN NOT NULL DEFAULT FALSE,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    criado_por VARCHAR(100) NOT NULL
                )
            """))
            conn.execute(db.text(
                "CREATE UNIQUE INDEX uq_carvia_empresas_cubagem_cnpj "
                "ON carvia_empresas_cubagem (cnpj_empresa)"
            ))
            conn.commit()
            print("[OK] carvia_empresas_cubagem criada com indice UNIQUE(cnpj_empresa)")
        else:
            print("[SKIP] carvia_empresas_cubagem ja existe")

        # ---- AFTER ----
        result = conn.execute(db.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'carvia_modelos_moto')"
        ))
        print(f"[AFTER] carvia_modelos_moto exists: {result.scalar()}")

        result = conn.execute(db.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'carvia_empresas_cubagem')"
        ))
        print(f"[AFTER] carvia_empresas_cubagem exists: {result.scalar()}")

        conn.close()
        print("\n[DONE] Migration concluida.")


if __name__ == '__main__':
    run_migration()
