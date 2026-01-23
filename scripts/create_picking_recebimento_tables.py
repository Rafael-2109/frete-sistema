#!/usr/bin/env python3
"""
Migration: Tabelas de cache para Pickings de Recebimento (Fase 4)
=================================================================

Cria 4 tabelas normalizadas para armazenar dados de pickings
sincronizados do Odoo via APScheduler (a cada 30 min).

Tabelas:
1. picking_recebimento - 1 linha por picking (stock.picking)
2. picking_recebimento_produto - 1 linha por produto (stock.move)
3. picking_recebimento_move_line - 1 linha por move_line (stock.move.line)
4. picking_recebimento_quality_check - 1 linha por quality check

Padrao: Mesmo do PedidoCompras, FaturamentoProduto, etc.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas():
    app = create_app()
    with app.app_context():
        try:
            # =====================================================
            # TABELA 1: picking_recebimento (1 linha por picking)
            # =====================================================
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS picking_recebimento (
                    id SERIAL PRIMARY KEY,
                    odoo_picking_id INTEGER NOT NULL UNIQUE,
                    odoo_picking_name VARCHAR(50) NOT NULL,
                    state VARCHAR(20) NOT NULL,
                    picking_type_code VARCHAR(20),
                    odoo_partner_id INTEGER,
                    odoo_partner_name VARCHAR(255),
                    origin VARCHAR(100),
                    odoo_purchase_order_id INTEGER,
                    odoo_purchase_order_name VARCHAR(50),
                    company_id INTEGER NOT NULL,
                    scheduled_date TIMESTAMP,
                    create_date TIMESTAMP,
                    write_date TIMESTAMP,
                    location_id INTEGER,
                    location_dest_id INTEGER,
                    sincronizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                    atualizado_em TIMESTAMP
                );
            """))
            print("✅ Tabela picking_recebimento criada")

            # Indices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_picking_rec_company
                ON picking_recebimento(company_id, state);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_picking_rec_partner
                ON picking_recebimento(odoo_partner_name);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_picking_rec_origin
                ON picking_recebimento(origin);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_picking_rec_po
                ON picking_recebimento(odoo_purchase_order_id);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_picking_rec_write
                ON picking_recebimento(write_date);
            """))
            print("  ✅ Indices criados para picking_recebimento")

            # =====================================================
            # TABELA 2: picking_recebimento_produto (1 linha por stock.move)
            # =====================================================
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS picking_recebimento_produto (
                    id SERIAL PRIMARY KEY,
                    picking_recebimento_id INTEGER NOT NULL
                        REFERENCES picking_recebimento(id) ON DELETE CASCADE,
                    odoo_move_id INTEGER NOT NULL,
                    odoo_product_id INTEGER NOT NULL,
                    odoo_product_name VARCHAR(255),
                    product_uom_qty NUMERIC(15,3),
                    product_uom VARCHAR(20),
                    tracking VARCHAR(20) DEFAULT 'none',
                    use_expiration_date BOOLEAN DEFAULT FALSE,
                    UNIQUE(picking_recebimento_id, odoo_move_id)
                );
            """))
            print("✅ Tabela picking_recebimento_produto criada")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_picking_rec_prod_picking
                ON picking_recebimento_produto(picking_recebimento_id);
            """))
            print("  ✅ Indice criado para picking_recebimento_produto")

            # =====================================================
            # TABELA 3: picking_recebimento_move_line (1 linha por stock.move.line)
            # =====================================================
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS picking_recebimento_move_line (
                    id SERIAL PRIMARY KEY,
                    picking_recebimento_id INTEGER NOT NULL
                        REFERENCES picking_recebimento(id) ON DELETE CASCADE,
                    produto_id INTEGER NOT NULL
                        REFERENCES picking_recebimento_produto(id) ON DELETE CASCADE,
                    odoo_move_line_id INTEGER NOT NULL,
                    odoo_move_id INTEGER,
                    lot_id INTEGER,
                    lot_name VARCHAR(100),
                    quantity NUMERIC(15,3) DEFAULT 0,
                    reserved_uom_qty NUMERIC(15,3) DEFAULT 0,
                    location_id INTEGER,
                    location_dest_id INTEGER,
                    UNIQUE(picking_recebimento_id, odoo_move_line_id)
                );
            """))
            print("✅ Tabela picking_recebimento_move_line criada")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_picking_rec_ml_picking
                ON picking_recebimento_move_line(picking_recebimento_id);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_picking_rec_ml_produto
                ON picking_recebimento_move_line(produto_id);
            """))
            print("  ✅ Indices criados para picking_recebimento_move_line")

            # =====================================================
            # TABELA 4: picking_recebimento_quality_check (1 linha por quality.check)
            # =====================================================
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS picking_recebimento_quality_check (
                    id SERIAL PRIMARY KEY,
                    picking_recebimento_id INTEGER NOT NULL
                        REFERENCES picking_recebimento(id) ON DELETE CASCADE,
                    odoo_check_id INTEGER NOT NULL,
                    odoo_point_id INTEGER,
                    odoo_product_id INTEGER,
                    odoo_product_name VARCHAR(255),
                    quality_state VARCHAR(20),
                    test_type VARCHAR(20),
                    title VARCHAR(255),
                    norm_unit VARCHAR(20),
                    tolerance_min NUMERIC(15,4),
                    tolerance_max NUMERIC(15,4),
                    UNIQUE(picking_recebimento_id, odoo_check_id)
                );
            """))
            print("✅ Tabela picking_recebimento_quality_check criada")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_picking_rec_qc_picking
                ON picking_recebimento_quality_check(picking_recebimento_id);
            """))
            print("  ✅ Indice criado para picking_recebimento_quality_check")

            db.session.commit()
            print("\n✅ TODAS as 4 tabelas criadas com sucesso!")
            print("\nSQL para rodar no Render Shell:")
            print("=" * 60)
            print(gerar_sql_render())

        except Exception as e:
            print(f"\n❌ Erro: {e}")
            db.session.rollback()
            raise


def gerar_sql_render():
    """Gera SQL simples para rodar no Shell do Render."""
    return """
CREATE TABLE IF NOT EXISTS picking_recebimento (
    id SERIAL PRIMARY KEY,
    odoo_picking_id INTEGER NOT NULL UNIQUE,
    odoo_picking_name VARCHAR(50) NOT NULL,
    state VARCHAR(20) NOT NULL,
    picking_type_code VARCHAR(20),
    odoo_partner_id INTEGER,
    odoo_partner_name VARCHAR(255),
    origin VARCHAR(100),
    odoo_purchase_order_id INTEGER,
    odoo_purchase_order_name VARCHAR(50),
    company_id INTEGER NOT NULL,
    scheduled_date TIMESTAMP,
    create_date TIMESTAMP,
    write_date TIMESTAMP,
    location_id INTEGER,
    location_dest_id INTEGER,
    sincronizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_picking_rec_company ON picking_recebimento(company_id, state);
CREATE INDEX IF NOT EXISTS idx_picking_rec_partner ON picking_recebimento(odoo_partner_name);
CREATE INDEX IF NOT EXISTS idx_picking_rec_origin ON picking_recebimento(origin);
CREATE INDEX IF NOT EXISTS idx_picking_rec_po ON picking_recebimento(odoo_purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_picking_rec_write ON picking_recebimento(write_date);

CREATE TABLE IF NOT EXISTS picking_recebimento_produto (
    id SERIAL PRIMARY KEY,
    picking_recebimento_id INTEGER NOT NULL REFERENCES picking_recebimento(id) ON DELETE CASCADE,
    odoo_move_id INTEGER NOT NULL,
    odoo_product_id INTEGER NOT NULL,
    odoo_product_name VARCHAR(255),
    product_uom_qty NUMERIC(15,3),
    product_uom VARCHAR(20),
    tracking VARCHAR(20) DEFAULT 'none',
    use_expiration_date BOOLEAN DEFAULT FALSE,
    UNIQUE(picking_recebimento_id, odoo_move_id)
);

CREATE INDEX IF NOT EXISTS idx_picking_rec_prod_picking ON picking_recebimento_produto(picking_recebimento_id);

CREATE TABLE IF NOT EXISTS picking_recebimento_move_line (
    id SERIAL PRIMARY KEY,
    picking_recebimento_id INTEGER NOT NULL REFERENCES picking_recebimento(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL REFERENCES picking_recebimento_produto(id) ON DELETE CASCADE,
    odoo_move_line_id INTEGER NOT NULL,
    odoo_move_id INTEGER,
    lot_id INTEGER,
    lot_name VARCHAR(100),
    quantity NUMERIC(15,3) DEFAULT 0,
    reserved_uom_qty NUMERIC(15,3) DEFAULT 0,
    location_id INTEGER,
    location_dest_id INTEGER,
    UNIQUE(picking_recebimento_id, odoo_move_line_id)
);

CREATE INDEX IF NOT EXISTS idx_picking_rec_ml_picking ON picking_recebimento_move_line(picking_recebimento_id);
CREATE INDEX IF NOT EXISTS idx_picking_rec_ml_produto ON picking_recebimento_move_line(produto_id);

CREATE TABLE IF NOT EXISTS picking_recebimento_quality_check (
    id SERIAL PRIMARY KEY,
    picking_recebimento_id INTEGER NOT NULL REFERENCES picking_recebimento(id) ON DELETE CASCADE,
    odoo_check_id INTEGER NOT NULL,
    odoo_point_id INTEGER,
    odoo_product_id INTEGER,
    odoo_product_name VARCHAR(255),
    quality_state VARCHAR(20),
    test_type VARCHAR(20),
    title VARCHAR(255),
    norm_unit VARCHAR(20),
    tolerance_min NUMERIC(15,4),
    tolerance_max NUMERIC(15,4),
    UNIQUE(picking_recebimento_id, odoo_check_id)
);

CREATE INDEX IF NOT EXISTS idx_picking_rec_qc_picking ON picking_recebimento_quality_check(picking_recebimento_id);
"""


if __name__ == '__main__':
    criar_tabelas()
