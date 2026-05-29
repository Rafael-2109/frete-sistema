"""Data-fix idempotente 2026-05-29: deprecar odoo_product_uom_id no De-Para.

Apos o fix de codigo (DeparaService nao grava mais product_uom no supplierinfo —
ver app/recebimento/services/depara_service.py), o campo odoo_product_uom_id
deixou de ter funcao. A conversao da unidade do fornecedor e' feita por
fator_un (Odoo, por produto) + fator_conversao (validacao NF x PO).

CONTEXTO: product.supplierinfo.product_uom e' related de product_tmpl_id.uom_po_id
(store=True). Gravar esse campo (o que a feature fazia a partir de odoo_product_uom_id)
ALTERAVA a UoM de compra do produto INTEIRO e inflava o price_unit dos POs (~10^6x
no caso do VIDRO 200 G / MI). O De-Para NUNCA deve tocar o uom_po_id.

Este script ZERA (NULL) o odoo_product_uom_id de TODOS os De-Paras, removendo o
dado obsoleto que poderia, em fluxos legados, reescrever uom_po_id no produto.

Idempotente: WHERE odoo_product_uom_id IS NOT NULL. Seguro rodar a cada deploy.
A coluna e' mantida (deprecada em models.py); remocao via migration futura.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


def main():
    app = create_app()
    with app.app_context():
        n = db.session.execute(text(
            "SELECT COUNT(*) FROM produto_fornecedor_depara "
            "WHERE odoo_product_uom_id IS NOT NULL"
        )).scalar()
        print(f"[DEPRECAR] De-Paras com odoo_product_uom_id != NULL: {n}")
        if not n:
            print("[SKIP] nada a limpar.")
            return
        db.session.execute(text(
            "UPDATE produto_fornecedor_depara SET odoo_product_uom_id = NULL "
            "WHERE odoo_product_uom_id IS NOT NULL"
        ))
        db.session.commit()
        print(f"[OK] {n} De-Para(s) com odoo_product_uom_id zerado (deprecado).")


if __name__ == '__main__':
    main()
