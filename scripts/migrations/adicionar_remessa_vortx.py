"""
Migration: Adicionar flag sistema_remessa_vortx + tabela remessa_vortx_cache + sequence
========================================================================================

Executar: python scripts/migrations/adicionar_remessa_vortx.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(table_name, column_name):
    """Verifica se coluna ja existe na tabela."""
    result = db.session.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns "
            "  WHERE table_name = :t AND column_name = :c"
            ")"
        ),
        {'t': table_name, 'c': column_name},
    )
    return result.scalar()


def verificar_tabela_existe(table_name):
    """Verifica se tabela ja existe."""
    result = db.session.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables "
            "  WHERE table_name = :t"
            ")"
        ),
        {'t': table_name},
    )
    return result.scalar()


def verificar_sequence_existe(seq_name):
    """Verifica se sequence ja existe."""
    result = db.session.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM pg_sequences "
            "  WHERE sequencename = :s"
            ")"
        ),
        {'s': seq_name},
    )
    return result.scalar()


def executar():
    app = create_app()
    with app.app_context():
        # ---------------------------------------------------------------
        # 1. ALTER TABLE usuarios ADD COLUMN sistema_remessa_vortx
        # ---------------------------------------------------------------
        if verificar_coluna_existe('usuarios', 'sistema_remessa_vortx'):
            print("\u2192 usuarios.sistema_remessa_vortx ja existe, pulando.")
        else:
            db.session.execute(text(
                "ALTER TABLE usuarios "
                "ADD COLUMN sistema_remessa_vortx BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            db.session.commit()
            print("\u2713 usuarios.sistema_remessa_vortx adicionada.")

        # ---------------------------------------------------------------
        # 2. CREATE TABLE remessa_vortx_cache
        # ---------------------------------------------------------------
        if verificar_tabela_existe('remessa_vortx_cache'):
            print("\u2192 tabela remessa_vortx_cache ja existe, pulando.")
        else:
            db.session.execute(text("""
                CREATE TABLE remessa_vortx_cache (
                    id SERIAL PRIMARY KEY,
                    etapa VARCHAR(30) NOT NULL DEFAULT 'CNAB_GERADO',
                    tentativas INTEGER NOT NULL DEFAULT 0,
                    ultimo_erro TEXT,

                    odoo_escritural_id INTEGER,
                    odoo_remessa_id INTEGER,

                    move_line_ids_marcados TEXT,
                    move_line_ids_pendentes TEXT,
                    mapa_nn_move_line TEXT,

                    company_id_odoo INTEGER NOT NULL,
                    tipo_cobranca_id_odoo INTEGER,
                    nome_arquivo VARCHAR(200) NOT NULL,
                    qtd_boletos INTEGER NOT NULL DEFAULT 0,
                    valor_total NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    nosso_numero_inicial BIGINT,
                    nosso_numero_final BIGINT,
                    arquivo_cnab BYTEA,

                    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                    criado_por_id INTEGER REFERENCES usuarios(id),
                    concluido_em TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT NOW()
                )
            """))
            db.session.commit()
            print("\u2713 tabela remessa_vortx_cache criada.")

        # Indexes
        # idx_remessa_vortx_etapa
        result = db.session.execute(text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM pg_indexes "
            "  WHERE indexname = 'idx_remessa_vortx_etapa'"
            ")"
        ))
        if result.scalar():
            print("\u2192 idx_remessa_vortx_etapa ja existe, pulando.")
        else:
            db.session.execute(text(
                "CREATE INDEX idx_remessa_vortx_etapa "
                "ON remessa_vortx_cache (etapa)"
            ))
            db.session.commit()
            print("\u2713 idx_remessa_vortx_etapa criado.")

        # idx_remessa_vortx_company
        result = db.session.execute(text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM pg_indexes "
            "  WHERE indexname = 'idx_remessa_vortx_company'"
            ")"
        ))
        if result.scalar():
            print("\u2192 idx_remessa_vortx_company ja existe, pulando.")
        else:
            db.session.execute(text(
                "CREATE INDEX idx_remessa_vortx_company "
                "ON remessa_vortx_cache (company_id_odoo)"
            ))
            db.session.commit()
            print("\u2713 idx_remessa_vortx_company criado.")

        # ---------------------------------------------------------------
        # 3. CREATE SEQUENCE nosso_numero_vortx_seq
        # ---------------------------------------------------------------
        if verificar_sequence_existe('nosso_numero_vortx_seq'):
            print("\u2192 sequence nosso_numero_vortx_seq ja existe, pulando.")
        else:
            db.session.execute(text(
                "CREATE SEQUENCE nosso_numero_vortx_seq START 1"
            ))
            db.session.commit()
            print("\u2713 sequence nosso_numero_vortx_seq criada.")

        print("\n[DONE] Migration adicionar_remessa_vortx concluida.")


if __name__ == '__main__':
    executar()
