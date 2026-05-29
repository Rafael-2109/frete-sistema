"""Data-fix idempotente 2026-05-28: UoM de compra do VIDRO 200 G - CONSERVA (206200004).

CONTEXTO
--------
O De-Para fornecedor (NADIR FIGUEIREDO, CNPJ 61067161001835) foi sincronizado com
`odoo_product_uom_id = 181` (MI / milheiro). Como `product.supplierinfo.product_uom`
e' um campo `related` de `product_tmpl_id.uom_po_id` (store=True), a sincronizacao
alterou o `uom_po_id` do produto INTEIRO para MI.

A UoM MI(181) esta' cadastrada invertida (`uom_type='smaller'`, `factor=1000`), o que
faz o Odoo converter o preco na direcao errada e inflar o `price_unit` dos Pedidos de
Compra em ~10^6x (ex.: PO C2619539 / id 42349, linha do vidro: R$ 1.537.232,37/un ->
subtotal R$ 25,6 bilhoes). A NF/escrituracao real fica correta; o erro e' apenas no PO.
A medida agregada do fornecedor (2086 un/compra) permanece preservada em
`supplierinfo.fator_un` e no `fator_conversao` do De-Para (validacao NF x PO).

ACAO (pontual, escopo = produto 206200004)
------------------------------------------
1. BANCO : De-Para(s) do vidro com odoo_product_uom_id=181 -> 1 (Units), para que uma
           futura sincronizacao NAO re-propague MI ao Odoo. Preserva fator_conversao
           e um_fornecedor (nao quebra a validacao NF x PO do fornecedor).
2. ODOO  : garante `product.template.uom_po_id = Units(1)` no produto (best-effort;
           NAO quebra o deploy se o Odoo estiver indisponivel no build).

Idempotente: so' altera registros divergentes; seguro rodar a cada deploy.
Data-fix (sem DDL) -> apenas Python, conforme regra de migrations.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text

COD_INTERNO = '206200004'
UOM_MI = 181
UOM_UNITS = 1


def corrigir_banco():
    """De-Para(s) do vidro apontando para MI(181) -> Units(1). Idempotente."""
    rows = db.session.execute(text(
        "SELECT id, cnpj_fornecedor, odoo_product_uom_id "
        "FROM produto_fornecedor_depara "
        "WHERE cod_produto_interno = :cod AND odoo_product_uom_id = :mi"
    ), {"cod": COD_INTERNO, "mi": UOM_MI}).all()

    if not rows:
        print(f"[BANCO][SKIP] nenhum De-Para de {COD_INTERNO} com UoM MI({UOM_MI}).")
        return

    for r in rows:
        print(f"[BANCO] De-Para id={r[0]} ({r[1]}): odoo_product_uom_id {r[2]} -> {UOM_UNITS}")
    db.session.execute(text(
        "UPDATE produto_fornecedor_depara SET odoo_product_uom_id = :units "
        "WHERE cod_produto_interno = :cod AND odoo_product_uom_id = :mi"
    ), {"units": UOM_UNITS, "cod": COD_INTERNO, "mi": UOM_MI})
    db.session.commit()
    print(f"[BANCO][OK] {len(rows)} De-Para(s) corrigido(s).")


def corrigir_odoo():
    """Garante uom_po_id = Units(1) no product.template do vidro. Best-effort."""
    try:
        from app.odoo.utils.connection import get_odoo_connection
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            print("[ODOO][SKIP] falha de autenticacao — sera reavaliado no proximo deploy.")
            return
        tmpls = odoo.search_read(
            'product.template', [('default_code', '=', COD_INTERNO)], ['id', 'uom_po_id']
        )
        if not tmpls:
            print(f"[ODOO][SKIP] produto {COD_INTERNO} nao encontrado no Odoo.")
            return
        for t in tmpls:
            upo = t.get('uom_po_id')
            if upo and upo[0] != UOM_UNITS:
                odoo.write('product.template', [t['id']], {'uom_po_id': UOM_UNITS})
                print(f"[ODOO] template {t['id']}: uom_po_id {upo} -> Units({UOM_UNITS})")
            else:
                print(f"[ODOO][SKIP] template {t['id']}: uom_po_id ja = Units({UOM_UNITS}).")
    except Exception as e:
        print(f"[ODOO][WARN] nao foi possivel verificar/corrigir no Odoo: {e}")


def main():
    app = create_app()
    with app.app_context():
        print("=== Correcao UoM de compra VIDRO 200 G (206200004) ===")
        corrigir_banco()
        corrigir_odoo()
        print("=== Concluido ===")


if __name__ == '__main__':
    main()
