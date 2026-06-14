#!/usr/bin/env python3
"""G9 DETALHE p/ desenhar a correcao (READ-ONLY) do caso VND/2026/00234.

Mede o que falta p/ desenhar a reversao pura per-documento com seguranca:
  1) recebivel (CLIENTES) da NF LF 562158: conciliado? amount_residual? (mexer quebra concil.)
  2) stock.move + SVL da entrada FB 564486 (double-count fisico): contas, valor, ainda existe?
  3) quants atuais dos insumos (o estoque double-counted ainda esta la?)
NAO escreve nada.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}
LF_MOVE = 562158   # VND/2026/00234
FB_MOVE = 564486   # ENTSI/2026/04/0025


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v in (False, None) else str(v)


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    # ===== 1) recebivel da NF LF =====
    print("=" * 70)
    print("1) RECEBIVEL (CLIENTES) da NF LF 562158")
    print("=" * 70)
    recv = rr('account.move.line',
              [('move_id', '=', LF_MOVE), ('account_id', '=', 26085)],
              ['name', 'debit', 'credit', 'amount_residual', 'reconciled',
               'full_reconcile_id', 'matched_credit_ids', 'date_maturity'])
    for ln in recv:
        print(f"  {ln.get('name')}: D {ln.get('debit'):,.2f}  residual {ln.get('amount_residual'):,.2f}")
        print(f"     reconciled={ln.get('reconciled')}  full_reconcile={m2o(ln.get('full_reconcile_id'))}")
        print(f"     matched_credit_ids={ln.get('matched_credit_ids')}  venc={ln.get('date_maturity')}")
    # estado de pagamento do move
    mv = rr('account.move', [('id', '=', LF_MOVE)],
            ['payment_state', 'amount_residual', 'amount_total'])
    if mv:
        print(f"  >> move payment_state={mv[0].get('payment_state')} residual={mv[0].get('amount_residual'):,.2f} total={mv[0].get('amount_total'):,.2f}")

    # ===== 2) product_ids das linhas 1902 da entrada FB =====
    print("\n" + "=" * 70)
    print("2) LINHAS 1902 (op 2027) da entrada FB 564486 — produtos")
    print("=" * 70)
    fb1902 = rr('account.move.line',
                [('move_id', '=', FB_MOVE), ('l10n_br_operacao_id', '=', 2027)],
                ['name', 'product_id', 'debit', 'quantity'])
    prod_ids = []
    for ln in fb1902:
        pid = ln.get('product_id')
        if isinstance(pid, list):
            prod_ids.append(pid[0])
        print(f"  prod={m2o(pid)[:40]:40} qty={ln.get('quantity')} D {ln.get('debit'):,.2f}")
    prod_ids = list(set(prod_ids))
    print(f"  total produtos distintos: {len(prod_ids)}")

    # ===== 2b) stock.move da entrada FB (double-count fisico) =====
    print("\n" + "=" * 70)
    print("2b) STOCK.MOVE da entrada FB (company 1) p/ esses produtos em 2026-04 (double-count?)")
    print("=" * 70)
    if prod_ids:
        sm = rr('stock.move',
                [('company_id', '=', 1), ('product_id', 'in', prod_ids),
                 ('date', '>=', '2026-04-08'), ('date', '<=', '2026-04-12'),
                 ('state', '=', 'done')],
                ['product_id', 'product_uom_qty', 'location_id', 'location_dest_id',
                 'reference', 'origin', 'picking_id'], limit=60)
        print(f"  {len(sm)} stock.move done")
        for s in sm[:25]:
            print(f"    {m2o(s['product_id'])[:26]:26} qty={s['product_uom_qty']:>7} "
                  f"{m2o(s['location_id'])[:14]:14}->{m2o(s['location_dest_id'])[:14]:14} "
                  f"ref={str(s.get('reference'))[:18]} pick={m2o(s.get('picking_id'))[:18]}")

    # ===== 2c) SVL (valoracao) =====
    print("\n" + "=" * 70)
    print("2c) SVL (stock.valuation.layer) company 1, esses produtos, 2026-04")
    print("=" * 70)
    if prod_ids:
        svl = rr('stock.valuation.layer',
                 [('company_id', '=', 1), ('product_id', 'in', prod_ids),
                  ('create_date', '>=', '2026-04-08'), ('create_date', '<=', '2026-04-12')],
                 ['product_id', 'quantity', 'value', 'unit_cost', 'description', 'stock_move_id'], limit=60)
        tot = 0.0
        for s in svl[:25]:
            tot += s.get('value') or 0
            print(f"    {m2o(s['product_id'])[:24]:24} qty={s['quantity']:>7} value R$ {s.get('value'):>9,.2f} | {str(s.get('description'))[:24]}")
        print(f"  => SVL value total (entrada estoque FB pelos insumos): R$ {tot:,.2f}  [double-count se >0]")

    print("\n[FIM G9 DETALHE — nada foi escrito]")


if __name__ == '__main__':
    main()
