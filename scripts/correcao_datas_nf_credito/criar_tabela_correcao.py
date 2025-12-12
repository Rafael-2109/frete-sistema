#!/usr/bin/env python3
"""
Script para criar a tabela de correção de datas de NF de Crédito.

Uso:
    python scripts/correcao_datas_nf_credito/criar_tabela_correcao.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela():
    app = create_app()
    with app.app_context():
        try:
            # Verificar se tabela já existe
            resultado = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'correcao_data_nf_credito'
                )
            """))
            existe = resultado.scalar()

            if existe:
                print("Tabela 'correcao_data_nf_credito' já existe.")
                return

            # Criar tabela
            db.session.execute(text("""
                CREATE TABLE correcao_data_nf_credito (
                    id SERIAL PRIMARY KEY,

                    -- Identificação do documento no Odoo
                    odoo_move_id INTEGER NOT NULL,
                    nome_documento VARCHAR(50) NOT NULL,
                    numero_nf VARCHAR(20),

                    -- Parceiro
                    odoo_partner_id INTEGER,
                    nome_parceiro VARCHAR(255),

                    -- Datas do documento
                    data_emissao DATE NOT NULL,
                    data_lancamento_antes DATE NOT NULL,
                    data_lancamento_linhas_antes DATE,
                    data_correta DATE NOT NULL,

                    -- Resultado da correção
                    data_lancamento_depois DATE,
                    data_lancamento_linhas_depois DATE,

                    -- Status
                    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
                    erro_mensagem TEXT,

                    -- Auditoria
                    diagnosticado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    corrigido_em TIMESTAMP,
                    corrigido_por VARCHAR(100),

                    -- Controle de exportação
                    exportado_em TIMESTAMP
                )
            """))

            # Criar índices
            db.session.execute(text("""
                CREATE INDEX idx_correcao_odoo_move_id ON correcao_data_nf_credito(odoo_move_id)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_correcao_status ON correcao_data_nf_credito(status)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_correcao_data_emissao ON correcao_data_nf_credito(data_emissao)
            """))
            db.session.execute(text("""
                CREATE UNIQUE INDEX uq_correcao_odoo_move_id ON correcao_data_nf_credito(odoo_move_id)
            """))

            db.session.commit()
            print("Tabela 'correcao_data_nf_credito' criada com sucesso!")

        except Exception as e:
            print(f"Erro ao criar tabela: {e}")
            db.session.rollback()


# SQL para Render Shell:
SQL_RENDER = """
-- Criar tabela de correção de datas NF Crédito
CREATE TABLE IF NOT EXISTS correcao_data_nf_credito (
    id SERIAL PRIMARY KEY,
    odoo_move_id INTEGER NOT NULL,
    nome_documento VARCHAR(50) NOT NULL,
    numero_nf VARCHAR(20),
    odoo_partner_id INTEGER,
    nome_parceiro VARCHAR(255),
    data_emissao DATE NOT NULL,
    data_lancamento_antes DATE NOT NULL,
    data_lancamento_linhas_antes DATE,
    data_correta DATE NOT NULL,
    data_lancamento_depois DATE,
    data_lancamento_linhas_depois DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    erro_mensagem TEXT,
    diagnosticado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    corrigido_em TIMESTAMP,
    corrigido_por VARCHAR(100),
    exportado_em TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_correcao_odoo_move_id ON correcao_data_nf_credito(odoo_move_id);
CREATE INDEX IF NOT EXISTS idx_correcao_status ON correcao_data_nf_credito(status);
CREATE INDEX IF NOT EXISTS idx_correcao_data_emissao ON correcao_data_nf_credito(data_emissao);
CREATE UNIQUE INDEX IF NOT EXISTS uq_correcao_odoo_move_id ON correcao_data_nf_credito(odoo_move_id);
"""

if __name__ == '__main__':
    print("=" * 60)
    print("Criando tabela correcao_data_nf_credito")
    print("=" * 60)
    criar_tabela()

    print("\n" + "=" * 60)
    print("SQL para Render Shell:")
    print("=" * 60)
    print(SQL_RENDER)
