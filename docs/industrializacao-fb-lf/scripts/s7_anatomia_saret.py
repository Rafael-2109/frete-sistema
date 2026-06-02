#!/usr/bin/env python3
"""S7 ANATOMIA SARET (READ-only) — Frente 1: como uma NF de retorno de insumos
SO-5902 (separada do servico) NASCE e CONTABILIZA em PROD, nas 3 esferas.

Precedente vivo (ACHADOS R2b): SARET/2026/00007-11 (op 2710 dev-industrializacao,
j1002 RETRABALHO), move 725475. Baixa via no_payment (= o mecanismo que falta ao
retorno de insumos). POReM saiu com CFOP de LINHA 5949 (retrabalho), nao 5902.

DISSECA (READ-only, zero escrita) uma ou mais SARET reais:
  FISCAL   : account.move + linhas (CFOP 5949 vs 5902, CST, op, tipo_pedido, valores)
  CONTABIL : lancamentos D/C por conta -> contrapartida no_payment (esperado 5101010046)
             + transitoria (esperado 1150100012)
  FISICO   : picking/stock.move de origem (picking_type, locations, lote, SVL) -> simbolica?
  ORIGEM   : create_uid (robo 1512?), invoice_origin, picking_type.l10n_br_tipo_pedido -> journal
  JOURNAL  : j1002 (no_payment, tipo_pedido, type) vs j847 (a NF mista de servico)

NAO escreve nada. Uso: python s7_anatomia_saret.py [--move 725475] [--name SARET/2026/00007]
"""
import sys
import argparse
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def cf(v):
    """codigo CFOP a partir de l10n_br_cfop_id ([id, '5902 - ...'])."""
    return v[1].split(' - ')[0].strip() if isinstance(v, list) and v else '-'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--move', type=int, default=725475, help='account.move id da SARET (default 725475)')
    ap.add_argument('--name', default='SARET/2026/%', help='filtro name p/ buscar SARET (default SARET/2026/%)')
    ap.add_argument('--max', type=int, default=3, help='max SARET a dissecar')
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}  CTX={CTX}")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    def rd(model, ids, fields):
        if not ids:
            return []
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX})

    # ------------------------------------------------------------------
    # 0) localizar SARET-alvo: move explicito + busca por name
    # ------------------------------------------------------------------
    alvo = set()
    if args.move:
        alvo.add(args.move)
    saret = rr('account.move', [('name', 'like', args.name)],
               ['id', 'name', 'journal_id', 'amount_total', 'amount_untaxed', 'state', 'move_type'],
               limit=20, order='id asc')
    print(f"\n[BUSCA] name like {args.name!r}: {len(saret)} moves")
    for mv in saret:
        print(f"   move {mv['id']:>8} {mv['name']:<22} j={m2o(mv['journal_id'])[:28]:28} "
              f"type={mv.get('move_type'):11} state={mv.get('state'):7} "
              f"untax={mv.get('amount_untaxed')} total={mv.get('amount_total')}")
    for mv in saret[:args.max]:
        alvo.add(mv['id'])

    # ------------------------------------------------------------------
    # JOURNAL de referencia (j1002 SARET vs j847 NF mista)
    # ------------------------------------------------------------------
    print("\n" + "=" * 92)
    print("JOURNALS de referencia")
    print("=" * 92)
    jflds = ['id', 'name', 'code', 'type', 'l10n_br_tipo_pedido',
             'account_no_payment_id', 'default_account_id', 'restrict_mode_hash_table']
    for j in rd('account.journal', [1002, 847, 1003], jflds):
        print(f"  j{j['id']:<5} {j['name'][:36]:36} code={j.get('code'):8} type={j.get('type'):8}")
        print(f"        tipo_pedido={j.get('l10n_br_tipo_pedido')!r}  no_payment={m2o(j.get('account_no_payment_id'))}")
        print(f"        default_account={m2o(j.get('default_account_id'))}  hash_table={j.get('restrict_mode_hash_table')}")

    # ------------------------------------------------------------------
    # anatomia de cada SARET-alvo
    # ------------------------------------------------------------------
    for mid in sorted(alvo):
        print("\n" + "#" * 92)
        print(f"# ANATOMIA move {mid}")
        print("#" * 92)
        mvflds = ['id', 'name', 'state', 'move_type', 'journal_id', 'partner_id',
                  'invoice_origin', 'l10n_br_operacao_id', 'l10n_br_tipo_pedido',
                  'amount_total', 'amount_untaxed', 'create_uid', 'create_date',
                  'l10n_br_numero_nf', 'ref']
        try:
            mv = rd('account.move', [mid], mvflds)
        except Exception as e:
            print(f"  ERRO read move (tentando campos minimos): {e}")
            mv = rd('account.move', [mid], ['id', 'name', 'state', 'journal_id', 'invoice_origin', 'create_uid'])
        if not mv:
            print("  (move inexistente)")
            continue
        mv = mv[0]
        print("\n--- FISCAL/HEADER ---")
        for k in ['name', 'state', 'move_type', 'journal_id', 'partner_id', 'invoice_origin',
                  'l10n_br_operacao_id', 'l10n_br_tipo_pedido', 'amount_untaxed', 'amount_total',
                  'create_uid', 'create_date', 'l10n_br_numero_nf', 'ref']:
            if k in mv:
                val = m2o(mv[k]) if isinstance(mv.get(k), list) else mv.get(k)
                print(f"  {k:24} = {val}")

        # ---- linhas (fiscal + contabil) ----
        print("\n--- LINHAS (fiscal + contabil D/C) ---")
        lflds = ['account_id', 'name', 'product_id', 'quantity', 'price_unit', 'price_subtotal',
                 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'l10n_br_tipo_pedido',
                 'debit', 'credit', 'display_type', 'tax_line_id']
        lines = rr('account.move.line', [('move_id', '=', mid)], lflds, limit=300, order='id asc')
        by_acct = defaultdict(lambda: [0.0, 0.0])  # acct -> [D, C]
        cfops = defaultdict(lambda: [0.0, 0.0])
        for ln in lines:
            if ln.get('display_type') in ('line_section', 'line_note'):
                continue
            acc = m2o(ln.get('account_id'))
            d, c = ln.get('debit') or 0, ln.get('credit') or 0
            by_acct[acc][0] += d
            by_acct[acc][1] += c
            cc = cf(ln.get('l10n_br_cfop_id'))
            cfops[cc][0] += d
            cfops[cc][1] += c
            tag = ''
            if acc.startswith(('5101010046|', '5101010001|', '5101020001|', '26863|', '26667|', '26652|')):
                tag = '  <<< COMPENSACAO (no_payment?)'
            elif acc.startswith(('1150100012|', '1150100011|')):
                tag = '  <  transitoria'
            elif 'CLIENTE' in acc.upper() or acc.startswith(('1110', '1120')):
                tag = '  <<< CLIENTES (receivable)'
            print(f"  acc={acc[:40]:40} cfop={cc:6} op={m2o(ln.get('l10n_br_operacao_id'))[:16]:16} "
                  f"prod={m2o(ln.get('product_id'))[:18]:18} qty={ln.get('quantity')} pu={ln.get('price_unit')} "
                  f"D={d} C={c}{tag}")

        print("\n--- RESUMO CONTABIL (por conta) ---")
        for acc, (d, c) in sorted(by_acct.items()):
            net = round(c - d, 2)
            print(f"  {acc[:46]:46} D={round(d,2):>12} C={round(c,2):>12}  NET(C-D)={net}")
        print("\n--- por CFOP (D/C) ---")
        for cc, (d, c) in sorted(cfops.items()):
            print(f"  CFOP {cc:8} D={round(d,2):>12} C={round(c,2):>12}")

        # ---- FISICO: picking de origem ----
        print("\n--- FISICO (picking/stock.move de origem) ---")
        origin = mv.get('invoice_origin')
        pks = []
        if origin:
            for nm in str(origin).split(','):
                nm = nm.strip()
                if not nm:
                    continue
                pks += rr('stock.picking', [('name', '=', nm)],
                          ['id', 'name', 'picking_type_id', 'location_id', 'location_dest_id',
                           'state', 'origin', 'group_id'], limit=5)
        # fallback: SO de mesmo nome -> pickings
        if not pks and origin:
            so = rr('sale.order', [('name', '=', str(origin).strip())], ['id', 'name', 'picking_ids'], limit=3)
            for s in so:
                for pid in s.get('picking_ids') or []:
                    pks += rd('stock.picking', [pid],
                              ['id', 'name', 'picking_type_id', 'location_id', 'location_dest_id',
                               'state', 'origin', 'group_id'])
        if not pks:
            print(f"  (sem picking via invoice_origin={origin!r})")
        for pk in pks:
            print(f"  picking {pk['id']} {pk['name']} state={pk.get('state')} "
                  f"pt={m2o(pk.get('picking_type_id'))}")
            print(f"     {m2o(pk.get('location_id'))} -> {m2o(pk.get('location_dest_id'))}")
            pt = rd('stock.picking.type', [pk['picking_type_id'][0]] if isinstance(pk.get('picking_type_id'), list) else [],
                    ['id', 'name', 'code', 'l10n_br_tipo_pedido', 'default_location_src_id', 'default_location_dest_id'])
            for t in pt:
                print(f"     picking_type: tipo_pedido={t.get('l10n_br_tipo_pedido')!r} code={t.get('code')} "
                      f"src={m2o(t.get('default_location_src_id'))} dst={m2o(t.get('default_location_dest_id'))}")
            sm = rr('stock.move', [('picking_id', '=', pk['id'])],
                    ['id', 'product_id', 'quantity', 'location_id', 'location_dest_id', 'state'], limit=50)
            print(f"     stock.moves: {len(sm)}")
            for s in sm[:8]:
                print(f"        move {s['id']} {m2o(s.get('product_id'))[:24]:24} qty={s.get('quantity')} "
                      f"{m2o(s.get('location_id'))[:18]}->{m2o(s.get('location_dest_id'))[:18]} {s.get('state')}")
            # SVL desses moves (simbolica? value=0?)
            mids = [s['id'] for s in sm]
            if mids:
                svl = rr('stock.valuation.layer', [('stock_move_id', 'in', mids)],
                         ['id', 'stock_move_id', 'value', 'quantity'], limit=50)
                tot = round(sum(s.get('value') or 0 for s in svl), 2)
                print(f"     SVL: {len(svl)} layers, valor total = {tot}  "
                      f"({'SIMBOLICA (0 valoracao)' if abs(tot) < 0.01 else 'TEM valoracao'})")

    print("\n[FIM s7_anatomia_saret — READ-only, nada escrito]")


if __name__ == '__main__':
    main()
