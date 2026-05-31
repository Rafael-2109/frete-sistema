#!/usr/bin/env python3
"""
Passo 0 — Selecionar categoria-cobaia do teste controlado (READ-ONLY).

Criterios: categoria PRODUTIVA real_time com 1 unico produto com quant na LF,
saldo>0 e standard_price>0 (lancamento com valor), baixo giro (poucos moves 90d).

Uso: source .venv/bin/activate
     python docs/industrializacao-fb-lf/scripts/passo0_selecionar_cobaia.py
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_LF = 5
# categorias produtivas com n_prod=1 na LF (do probe inicial)
CAND = [82, 94, 100, 104, 110, 309, 316, 391, 392, 78, 77, 74, 72, 332, 180, 181, 324, 325]
CUTOFF90 = '2026-03-01'  # ~90d (giro)


def main():
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise SystemExit("Falha auth Odoo")

    print(f"{'categ':>6} {'cnt_q':>5} {'prod':>9} {'saldo_LF':>12} {'custo':>10} "
          f"{'val_LF':>12} {'moves90d':>9}  produto / categoria")
    print("-" * 130)
    melhores = []
    for cat in CAND:
        # produtos da categoria com quant na LF
        quants = odoo.search_read('stock.quant',
                                  [('company_id', '=', CMP_LF), ('product_id.categ_id', '=', cat),
                                   ('location_id.usage', '=', 'internal')],
                                  ['product_id', 'quantity'], limit=500)
        prods = {}
        for q in quants:
            if q['product_id']:
                prods.setdefault(q['product_id'][0], 0.0)
                prods[q['product_id'][0]] += q['quantity']
        if len(prods) != 1:
            print(f"{cat:>6} {len(prods):>5}  (pulado: {len(prods)} produtos com quant)")
            continue
        pid, saldo = next(iter(prods.items()))
        p = odoo.read('product.product', [pid],
                      ['default_code', 'name', 'standard_price', 'categ_id'])[0]
        custo = p.get('standard_price') or 0.0
        val = saldo * custo
        # giro: moves done 90d na LF
        nm = odoo.search_count('stock.move',
                               [('product_id', '=', pid), ('company_id', '=', CMP_LF),
                                ('state', '=', 'done'), ('date', '>=', CUTOFF90)])
        print(f"{cat:>6} {len(prods):>5} {pid:>9} {saldo:>12,.2f} {custo:>10,.4f} "
              f"{val:>12,.2f} {nm:>9}  {p.get('default_code')} {p['name'][:26]} | {p['categ_id'][1].split('/')[-1].strip()}")
        if saldo > 0 and custo > 0:
            melhores.append((nm, val, cat, pid, p, saldo, custo))

    print()
    print("=" * 90)
    print("RECOMENDACAO (saldo>0, custo>0, menor giro 90d):")
    print("=" * 90)
    for nm, val, cat, pid, p, saldo, custo in sorted(melhores, key=lambda x: (x[0], -x[1]))[:5]:
        print(f"  categ {cat} | produto {p.get('default_code')} {p['name'][:30]} "
              f"| saldo {saldo:,.2f} custo {custo:,.4f} val {val:,.2f} | moves90d={nm}")


if __name__ == '__main__':
    main()
