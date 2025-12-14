# -*- coding: utf-8 -*-
"""
Script para criar a tabela contas_a_pagar
=========================================

Execução local:
    source venv/bin/activate && python scripts/migrations/criar_tabela_contas_pagar.py

Execução no Render (Shell):
    Copie e execute o SQL gerado abaixo.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

SQL_CREATE_TABLE = """
-- Criar tabela contas_a_pagar
CREATE TABLE IF NOT EXISTS contas_a_pagar (
    id SERIAL PRIMARY KEY,

    -- Identificação única
    empresa INTEGER NOT NULL,
    titulo_nf VARCHAR(50) NOT NULL,
    parcela VARCHAR(10) NOT NULL,

    -- IDs do Odoo
    odoo_line_id INTEGER UNIQUE,
    odoo_move_id INTEGER,
    odoo_move_name VARCHAR(255),

    -- Fornecedor
    partner_id INTEGER,
    cnpj VARCHAR(20),
    raz_social VARCHAR(255),
    raz_social_red VARCHAR(100),

    -- Datas
    emissao DATE,
    vencimento DATE,

    -- Valores
    valor_original FLOAT,
    valor_residual FLOAT,

    -- Status Odoo
    parcela_paga BOOLEAN DEFAULT FALSE,
    reconciliado BOOLEAN DEFAULT FALSE,

    -- Campos do sistema
    observacao TEXT,
    alerta BOOLEAN DEFAULT FALSE NOT NULL,
    status_sistema VARCHAR(30) DEFAULT 'PENDENTE' NOT NULL,
    data_programada DATE,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),

    -- Controle de sincronização
    odoo_write_date TIMESTAMP,
    ultima_sincronizacao TIMESTAMP,

    -- Constraint única
    CONSTRAINT uq_conta_pagar_empresa_nf_parcela UNIQUE (empresa, titulo_nf, parcela)
);

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_conta_pagar_empresa ON contas_a_pagar (empresa);
CREATE INDEX IF NOT EXISTS idx_conta_pagar_vencimento ON contas_a_pagar (vencimento);
CREATE INDEX IF NOT EXISTS idx_conta_pagar_cnpj ON contas_a_pagar (cnpj);
CREATE INDEX IF NOT EXISTS idx_conta_pagar_nf ON contas_a_pagar (titulo_nf);
CREATE INDEX IF NOT EXISTS idx_conta_pagar_odoo_line ON contas_a_pagar (odoo_line_id);
CREATE INDEX IF NOT EXISTS idx_conta_pagar_status_sistema ON contas_a_pagar (status_sistema);
CREATE INDEX IF NOT EXISTS idx_conta_pagar_partner ON contas_a_pagar (partner_id);
"""


def criar_tabela():
    """Cria a tabela contas_a_pagar"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("CRIANDO TABELA contas_a_pagar")
            print("=" * 60)

            # Executar SQL
            for statement in SQL_CREATE_TABLE.split(';'):
                statement = statement.strip()
                if statement:
                    db.session.execute(text(statement))

            db.session.commit()
            print("✅ Tabela contas_a_pagar criada com sucesso!")

            # Verificar
            result = db.session.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'contas_a_pagar'"
            ))
            count = result.scalar()
            if count > 0:
                print("✅ Verificação: Tabela existe no banco")
            else:
                print("❌ Erro: Tabela não foi criada")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("SQL PARA EXECUÇÃO MANUAL NO RENDER:")
    print("=" * 60)
    print(SQL_CREATE_TABLE)
    print("=" * 60 + "\n")

    criar_tabela()
