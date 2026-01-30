# -*- coding: utf-8 -*-
"""
Migracao: Criar tabela lancamento_comprovante
==============================================

Armazena resultado de match entre ComprovantePagamentoBoleto e fatura Odoo.

Executar localmente:
    source .venv/bin/activate && python scripts/criar_tabela_lancamento_comprovante.py

SQL para Render Shell:
    CREATE TABLE IF NOT EXISTS lancamento_comprovante (
        id SERIAL PRIMARY KEY,
        comprovante_id INTEGER NOT NULL REFERENCES comprovante_pagamento_boleto(id),
        odoo_move_line_id INTEGER,
        odoo_move_id INTEGER,
        odoo_move_name VARCHAR(255),
        odoo_partner_id INTEGER,
        odoo_partner_name VARCHAR(255),
        odoo_partner_cnpj VARCHAR(20),
        odoo_company_id INTEGER,
        nf_numero VARCHAR(50),
        parcela INTEGER,
        odoo_valor_original NUMERIC(15,2),
        odoo_valor_residual NUMERIC(15,2),
        odoo_valor_recalculado NUMERIC(15,2),
        odoo_vencimento DATE,
        match_score INTEGER NOT NULL DEFAULT 0,
        match_criterios TEXT,
        diferenca_valor NUMERIC(15,2),
        beneficiario_e_financeira BOOLEAN DEFAULT FALSE,
        status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
        criado_em TIMESTAMP DEFAULT NOW(),
        confirmado_em TIMESTAMP,
        confirmado_por VARCHAR(100),
        rejeitado_em TIMESTAMP,
        rejeitado_por VARCHAR(100),
        motivo_rejeicao TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_lanc_comp_id ON lancamento_comprovante(comprovante_id);
    CREATE INDEX IF NOT EXISTS idx_lanc_comp_status ON lancamento_comprovante(comprovante_id, status);
    CREATE INDEX IF NOT EXISTS idx_lanc_odoo_move_line ON lancamento_comprovante(odoo_move_line_id);
    CREATE INDEX IF NOT EXISTS idx_lanc_nf_parcela ON lancamento_comprovante(nf_numero, parcela);
    CREATE INDEX IF NOT EXISTS idx_lanc_status ON lancamento_comprovante(status);
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela_lancamento_comprovante():
    """Cria a tabela lancamento_comprovante."""
    app = create_app()
    with app.app_context():
        try:
            # Criar tabela
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS lancamento_comprovante (
                    id SERIAL PRIMARY KEY,
                    comprovante_id INTEGER NOT NULL REFERENCES comprovante_pagamento_boleto(id),
                    odoo_move_line_id INTEGER,
                    odoo_move_id INTEGER,
                    odoo_move_name VARCHAR(255),
                    odoo_partner_id INTEGER,
                    odoo_partner_name VARCHAR(255),
                    odoo_partner_cnpj VARCHAR(20),
                    odoo_company_id INTEGER,
                    nf_numero VARCHAR(50),
                    parcela INTEGER,
                    odoo_valor_original NUMERIC(15,2),
                    odoo_valor_residual NUMERIC(15,2),
                    odoo_valor_recalculado NUMERIC(15,2),
                    odoo_vencimento DATE,
                    match_score INTEGER NOT NULL DEFAULT 0,
                    match_criterios TEXT,
                    diferenca_valor NUMERIC(15,2),
                    beneficiario_e_financeira BOOLEAN DEFAULT FALSE,
                    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
                    criado_em TIMESTAMP DEFAULT NOW(),
                    confirmado_em TIMESTAMP,
                    confirmado_por VARCHAR(100),
                    rejeitado_em TIMESTAMP,
                    rejeitado_por VARCHAR(100),
                    motivo_rejeicao TEXT
                );
            """))
            print("[OK] Tabela lancamento_comprovante criada")

            # Criar indices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_lanc_comp_id
                    ON lancamento_comprovante(comprovante_id);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_lanc_comp_status
                    ON lancamento_comprovante(comprovante_id, status);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_lanc_odoo_move_line
                    ON lancamento_comprovante(odoo_move_line_id);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_lanc_nf_parcela
                    ON lancamento_comprovante(nf_numero, parcela);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_lanc_status
                    ON lancamento_comprovante(status);
            """))
            print("[OK] Indices criados")

            db.session.commit()
            print("\n[SUCESSO] Migracao concluida!")

            # Verificar
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'lancamento_comprovante'
                ORDER BY ordinal_position;
            """))
            print("\nCampos da tabela:")
            for row in resultado:
                print(f"  - {row[0]}: {row[1]} (nullable={row[2]})")

        except Exception as e:
            print(f"[ERRO] {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    criar_tabela_lancamento_comprovante()
