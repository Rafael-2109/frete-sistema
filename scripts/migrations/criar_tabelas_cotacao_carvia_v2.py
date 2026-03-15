"""
Migration: Criar tabelas para Cotacao CarVia v2
================================================
4 tabelas: grupos_cliente -> membros -> tabelas_frete -> cidades_atendidas

Ordem: rodar ANTES de adicionar_cnpj_demanda_cotacao.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        # ==================== BEFORE ====================
        tabelas = ['carvia_grupos_cliente', 'carvia_grupo_cliente_membros',
                    'carvia_tabelas_frete', 'carvia_cidades_atendidas']
        for t in tabelas:
            existe = conn.execute(db.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = :t)"
            ), {'t': t}).scalar()
            print(f"  [BEFORE] {t}: {'EXISTE' if existe else 'NAO EXISTE'}")

        # ==================== DDL ====================

        # 1. carvia_grupos_cliente
        conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS carvia_grupos_cliente (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL UNIQUE,
                descricao TEXT,
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL
            )
        """))
        print("  [OK] carvia_grupos_cliente")

        # 2. carvia_grupo_cliente_membros
        conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS carvia_grupo_cliente_membros (
                id SERIAL PRIMARY KEY,
                grupo_id INTEGER NOT NULL REFERENCES carvia_grupos_cliente(id) ON DELETE CASCADE,
                cnpj VARCHAR(20) NOT NULL,
                nome_empresa VARCHAR(255),
                criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL,
                CONSTRAINT uq_carvia_grupo_membro UNIQUE (grupo_id, cnpj)
            )
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_grupo_membro_grupo_id
            ON carvia_grupo_cliente_membros (grupo_id)
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_grupo_membro_cnpj
            ON carvia_grupo_cliente_membros (cnpj)
        """))
        print("  [OK] carvia_grupo_cliente_membros")

        # 3. carvia_tabelas_frete
        conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS carvia_tabelas_frete (
                id SERIAL PRIMARY KEY,
                uf_origem VARCHAR(2) NOT NULL,
                uf_destino VARCHAR(2) NOT NULL,
                nome_tabela VARCHAR(50) NOT NULL,
                tipo_carga VARCHAR(20) NOT NULL,
                modalidade VARCHAR(50) NOT NULL,
                grupo_cliente_id INTEGER REFERENCES carvia_grupos_cliente(id),
                valor_kg FLOAT,
                frete_minimo_peso FLOAT,
                percentual_valor FLOAT,
                frete_minimo_valor FLOAT,
                percentual_gris FLOAT,
                percentual_adv FLOAT,
                percentual_rca FLOAT,
                pedagio_por_100kg FLOAT,
                valor_despacho FLOAT,
                valor_cte FLOAT,
                valor_tas FLOAT,
                icms_incluso BOOLEAN NOT NULL DEFAULT FALSE,
                gris_minimo FLOAT DEFAULT 0,
                adv_minimo FLOAT DEFAULT 0,
                icms_proprio FLOAT,
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL,
                CONSTRAINT ck_carvia_tf_tipo_carga CHECK (tipo_carga IN ('DIRETA', 'FRACIONADA'))
            )
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_tf_uf
            ON carvia_tabelas_frete (uf_origem, uf_destino)
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_tf_grupo_cliente_id
            ON carvia_tabelas_frete (grupo_cliente_id)
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_tf_tipo_carga
            ON carvia_tabelas_frete (tipo_carga)
        """))
        print("  [OK] carvia_tabelas_frete")

        # 4. carvia_cidades_atendidas
        conn.execute(db.text("""
            CREATE TABLE IF NOT EXISTS carvia_cidades_atendidas (
                id SERIAL PRIMARY KEY,
                codigo_ibge VARCHAR(10) NOT NULL,
                nome_cidade VARCHAR(100) NOT NULL,
                uf VARCHAR(2) NOT NULL,
                nome_tabela VARCHAR(50) NOT NULL,
                lead_time INTEGER,
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL,
                CONSTRAINT uq_carvia_cidade_tabela UNIQUE (codigo_ibge, nome_tabela)
            )
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_cidade_ibge
            ON carvia_cidades_atendidas (codigo_ibge)
        """))
        conn.execute(db.text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_cidade_uf
            ON carvia_cidades_atendidas (uf)
        """))
        print("  [OK] carvia_cidades_atendidas")

        conn.execute(db.text("COMMIT"))
        conn.close()

        # ==================== AFTER ====================
        conn2 = db.engine.connect()
        for t in tabelas:
            existe = conn2.execute(db.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = :t)"
            ), {'t': t}).scalar()
            print(f"  [AFTER] {t}: {'EXISTE' if existe else 'FALHOU'}")
        conn2.close()

        print("\n=== Migration criar_tabelas_cotacao_carvia_v2 concluida ===")


if __name__ == '__main__':
    run()
