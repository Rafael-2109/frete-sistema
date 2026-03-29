#!/usr/bin/env python3
"""
Migration: Indexes de performance para embarques e embarque_itens
=================================================================

Tabelas sem indexes customizados, usadas em joins frequentes em todo o sistema.

embarques: status, data_embarque, transportadora_id+status, tipo_carga
embarque_itens: embarque_id+status, nota_fiscal, cnpj_cliente, uf_destino

Data: 2026-03-29
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text


INDEXES = [
    # embarques
    ("embarques", "idx_emb_status", "CREATE INDEX IF NOT EXISTS idx_emb_status ON embarques (status)"),
    ("embarques", "idx_emb_data_embarque", "CREATE INDEX IF NOT EXISTS idx_emb_data_embarque ON embarques (data_embarque)"),
    ("embarques", "idx_emb_transportadora_status", "CREATE INDEX IF NOT EXISTS idx_emb_transportadora_status ON embarques (transportadora_id, status)"),
    ("embarques", "idx_emb_tipo_carga", "CREATE INDEX IF NOT EXISTS idx_emb_tipo_carga ON embarques (tipo_carga)"),
    # embarque_itens
    ("embarque_itens", "idx_ei_embarque_status", "CREATE INDEX IF NOT EXISTS idx_ei_embarque_status ON embarque_itens (embarque_id, status)"),
    ("embarque_itens", "idx_ei_nota_fiscal", "CREATE INDEX IF NOT EXISTS idx_ei_nota_fiscal ON embarque_itens (nota_fiscal)"),
    ("embarque_itens", "idx_ei_cnpj_cliente", "CREATE INDEX IF NOT EXISTS idx_ei_cnpj_cliente ON embarque_itens (cnpj_cliente)"),
    ("embarque_itens", "idx_ei_uf_destino", "CREATE INDEX IF NOT EXISTS idx_ei_uf_destino ON embarque_itens (uf_destino)"),
]


def run():
    app = create_app()
    with app.app_context():
        for table_name in ("embarques", "embarque_itens"):
            result = db.session.execute(text(
                "SELECT indexname FROM pg_indexes WHERE tablename = :t"
            ), {"t": table_name})
            existing = {row[0] for row in result}
            print(f"\n{table_name}: {len(existing)} indexes existentes")

        created = 0
        for table, idx_name, ddl in INDEXES:
            print(f"  [CREATE] {idx_name} on {table}...")
            db.session.execute(text(ddl))
            created += 1

        db.session.execute(text("ANALYZE embarques"))
        db.session.execute(text("ANALYZE embarque_itens"))
        db.session.commit()

        print(f"\n{created} indexes criados/verificados. ANALYZE executado.")


if __name__ == "__main__":
    run()
