#!/usr/bin/env python3
"""
Passo 0 — Classificar productive vs MRO (READ-ONLY).

Regra de negocio (Rafael, 2026-05-29): componentes PRODUTIVOS da LF sao TODOS da
FB (terceiros). Proprio da LF so' MRO/manutencao/uso da industria (nunca componente).
NOVACKI = remessa por conta e ordem (= FB/terceiros). CD->LF = PA p/ retrabalho (terceiros).

Verifica:
  A) produtos/categorias recebidos de fornecedores EXTERNOS (nao-NACOM) via pt19
     -> classificar se caem nas 66 categorias produtivas ou em categoria MRO.
  B) procura por categorias/produtos com cara de MRO (manutencao/peca/maquina/uso)
     dentro e fora das 66 -> saber se o repoint das 65 produtivas e' seguro.

Uso: source .venv/bin/activate
     python docs/industrializacao-fb-lf/scripts/passo0_classificar_mro.py
"""
import sys
import json
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_LF = 5
PT_LF_IN = 19
CUTOFF = '2025-05-01'
MRO_HINTS = ('MANUTEN', 'PECA', 'PEÇA', 'MAQUIN', 'MÁQUIN', 'FERRAMENT', 'SOLDA',
             'LUBRIFIC', 'GRAXA', 'ROLAMENT', 'CORREIA', 'MOTOR', 'USO', 'EPI',
             'LIMPEZA', 'HIGIEN', 'REPARO', 'INDUSTRIA')


def main():
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise SystemExit("Falha auth Odoo")

    # universo das 66 categorias produtivas (com quant LF)
    cats66 = set(json.load(open('/tmp/passo0_contas_lf.json'))['cat_ids']) \
        if _exists('/tmp/passo0_contas_lf.json') else set()

    print("=" * 90)
    print("A) Pickings pt19 de fornecedores EXTERNOS (nao-NACOM) — produtos/categorias")
    print("=" * 90)
    picks = odoo.search_read('stock.picking',
                             [('company_id', '=', CMP_LF),
                              ('picking_type_id', '=', PT_LF_IN),
                              ('state', '=', 'done'),
                              ('date_done', '>=', CUTOFF)],
                             ['id', 'partner_id', 'name'], limit=2000)
    ext = [p for p in picks if not (p['partner_id'] and 'NACOM' in p['partner_id'][1].upper())]
    print(f"  pickings nao-NACOM (inclui sem parceiro): {len(ext)}")
    pick_ids = [p['id'] for p in ext]
    moves = []
    for i in range(0, len(pick_ids), 200):
        moves += odoo.search_read('stock.move',
                                  [('picking_id', 'in', pick_ids[i:i + 200])],
                                  ['product_id', 'product_qty', 'picking_id'], limit=10000)
    prod_ids = sorted({m['product_id'][0] for m in moves if m['product_id']})
    pinfo = {}
    for i in range(0, len(prod_ids), 200):
        for p in odoo.read('product.product', prod_ids[i:i + 200],
                           ['default_code', 'name', 'categ_id', 'type']):
            pinfo[p['id']] = p
    cat_ext = {}
    for p in pinfo.values():
        c = p['categ_id']
        if c:
            cat_ext.setdefault(c[0], {'name': c[1], 'prods': [], 'type': p['type']})
            cat_ext[c[0]]['prods'].append(f"{p.get('default_code') or '?'} {p['name'][:30]}")
    print(f"  produtos distintos recebidos de externos: {len(prod_ids)}")
    for cid, info in sorted(cat_ext.items()):
        in66 = 'DENTRO das 66' if cid in cats66 else 'FORA das 66'
        print(f"\n  categ {cid} [{in66}] type={info['type']} | {info['name']}")
        for pr in info['prods'][:10]:
            print(f"      - {pr}")

    print()
    print("=" * 90)
    print("B) Categorias com cara de MRO (hints) em TODA a base")
    print("=" * 90)
    allcats = odoo.search_read('product.category', [], ['complete_name'], limit=2000)
    mro_cats = [c for c in allcats if any(h in c['complete_name'].upper() for h in MRO_HINTS)]
    print(f"  categorias MRO-like: {len(mro_cats)}")
    for c in mro_cats:
        in66 = 'DENTRO das 66' if c['id'] in cats66 else 'fora'
        print(f"    categ {c['id']:<5} [{in66}] {c['complete_name']}")

    print()
    print("  -> Conclusao automatica:")
    ext_fora = [cid for cid in cat_ext if cid not in cats66]
    print(f"     categorias de compras externas FORA das 66 (candidatas a MRO proprio): {ext_fora}")
    print(f"     categorias de compras externas DENTRO das 66 (produtivas/terceiros): "
          f"{[cid for cid in cat_ext if cid in cats66]}")


def _exists(p):
    import os
    return os.path.exists(p)


if __name__ == '__main__':
    main()
