#!/usr/bin/env python3
"""S7 FLUXO DO PA (READ-only) — Frente 3 (contabil decisivo): em que LINHA/NF viaja o
PA fisico no retorno de industrializacao, com que price_unit, e como o AVCO=Ic+S se forma.

Disseca VNDs reais (retorno LF->FB, mista 5124+5902, j847) + a saida fisica:
  - cada linha: produto, CFOP, operacao + movimento_estoque(op), price_unit, qty, D/C
  - identifica a linha que carrega o PA (mov_estoque=True -> gera stock.move) vs simbolica
  - picking de saida + SVL por produto (qual e' o PA, valor fisico)
  - standard_price atual dos produtos (AVCO)

NAO escreve nada. Uso: python s7_fluxo_pa.py [--move 738097] [--max 2]
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def cf(v):
    return v[1].split(' - ')[0].strip() if isinstance(v, list) and v else '-'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--move', type=int, default=738097, help='VND de retorno LF (default 738097)')
    ap.add_argument('--max', type=int, default=2, help='quantas VND extras dissecar')
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
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    # descobrir o campo movimento_estoque na operacao
    fg = o.execute_kw('l10n_br_ciel_it_account.operacao', 'fields_get', [],
                      {'attributes': ['string'], 'context': CTX})
    mov_field = 'movimento_estoque' if 'movimento_estoque' in fg else (
        'l10n_br_movimento_estoque' if 'l10n_br_movimento_estoque' in fg else None)
    print(f"  campo movimento_estoque na operacao = {mov_field!r}")

    # alvos: 738097 + outras VND de retorno (j847) recentes
    alvo = [args.move] if args.move else []
    extra = rr('account.move', [('journal_id', '=', 847), ('company_id', '=', 5),
                                ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
                                ('date', '>=', '2026-05-01')],
               ['id', 'name', 'amount_total', 'amount_untaxed'], limit=args.max, order='id desc')
    for mv in extra:
        if mv['id'] not in alvo:
            alvo.append(mv['id'])

    for mid in alvo:
        print("\n" + "#" * 96)
        mvflds = ['id', 'name', 'state', 'move_type', 'journal_id', 'partner_id', 'invoice_origin',
                  'ref', 'l10n_br_operacao_id', 'l10n_br_tipo_pedido', 'amount_untaxed', 'amount_total',
                  'l10n_br_numero_nf']
        mv = rd('account.move', [mid], mvflds)
        if not mv:
            print(f"# move {mid}: inexistente"); continue
        mv = mv[0]
        print(f"# VND {mv['name']} (move {mid}) — {m2o(mv.get('journal_id'))}")
        print("#" * 96)
        print(f"  partner={m2o(mv.get('partner_id'))} origin={mv.get('invoice_origin')} ref={mv.get('ref')}")
        print(f"  chave_nfe={mv.get('l10n_br_chave_nfe')} num_nf={mv.get('l10n_br_numero_nf')} "
              f"untax={mv.get('amount_untaxed')} total={mv.get('amount_total')}")

        lflds = ['account_id', 'name', 'product_id', 'quantity', 'price_unit', 'price_subtotal',
                 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'debit', 'credit', 'display_type']
        lines = rr('account.move.line', [('move_id', '=', mid)], lflds, limit=400, order='id asc')
        # ler movimento_estoque das ops presentes
        op_ids = {ln['l10n_br_operacao_id'][0] for ln in lines if isinstance(ln.get('l10n_br_operacao_id'), list)}
        opmov = {}
        if mov_field and op_ids:
            for op in rd('l10n_br_ciel_it_account.operacao', op_ids, ['id', 'name', mov_field]):
                opmov[op['id']] = op.get(mov_field)
        print("\n  --- LINHAS (produto / CFOP / op[mov_estoque] / price_unit / qty / D-C) ---")
        for ln in lines:
            if ln.get('display_type') in ('line_section', 'line_note'):
                continue
            opid = ln['l10n_br_operacao_id'][0] if isinstance(ln.get('l10n_br_operacao_id'), list) else None
            mov = opmov.get(opid, '?')
            prod = m2o(ln.get('product_id'))
            tag = ''
            if mov is True:
                tag = '  <<< mov_estoque=True (GERA stock.move -> valora AVCO)'
            print(f"   prod={prod[:30]:30} cfop={cf(ln.get('l10n_br_cfop_id')):6} "
                  f"op={str(opid):6}[mov={mov}] pu={ln.get('price_unit')} qty={ln.get('quantity')} "
                  f"D={ln.get('debit')} C={ln.get('credit')}{tag}")

        # picking de saida -> SVL por produto
        cand = []
        for src in (mv.get('invoice_origin'), mv.get('ref')):
            if src:
                cand += [x.strip() for x in str(src).split(',') if x.strip()]
        pks = []
        for nm in cand:
            pks += rr('stock.picking', [('name', '=', nm)],
                      ['id', 'name', 'picking_type_id', 'location_id', 'location_dest_id', 'state'], limit=5)
        print(f"\n  --- FISICO (picking saida): candidatos={cand} achados={len(pks)} ---")
        for pk in pks:
            print(f"   picking {pk['id']} {pk['name']} pt={m2o(pk.get('picking_type_id'))} "
                  f"{m2o(pk.get('location_id'))}->{m2o(pk.get('location_dest_id'))} {pk.get('state')}")
            sm = rr('stock.move', [('picking_id', '=', pk['id'])],
                    ['id', 'product_id', 'quantity', 'price_unit'], limit=80)
            mids = [s['id'] for s in sm]
            svl = rr('stock.valuation.layer', [('stock_move_id', 'in', mids)],
                     ['stock_move_id', 'value', 'quantity', 'unit_cost'], limit=120) if mids else []
            svl_by = {s['stock_move_id'][0]: s for s in svl if isinstance(s.get('stock_move_id'), list)}
            for s in sm[:12]:
                v = svl_by.get(s['id'], {})
                print(f"      move {s['id']} {m2o(s.get('product_id'))[:28]:28} qty={s.get('quantity')} "
                      f"pu={s.get('price_unit')} | SVL value={v.get('value')} unit_cost={v.get('unit_cost')} qty={v.get('quantity')}")

        # standard_price (AVCO) dos produtos da NF (FB=1 e LF=5)
        prods = {ln['product_id'][0] for ln in lines if isinstance(ln.get('product_id'), list)}
        print(f"\n  --- AVCO (standard_price) dos {len(prods)} produtos — FB(1) e LF(5) ---")
        for emp in (1, 5):
            ctx_emp = dict(CTX, force_company=emp, company_id=emp, allowed_company_ids=[emp])
            pr = o.execute_kw('product.product', 'read', [list(prods)],
                              {'fields': ['id', 'default_code', 'standard_price', 'categ_id'], 'context': ctx_emp})
            for p in pr[:14]:
                print(f"   [emp{emp}] {str(p.get('default_code')):12} std_price={p.get('standard_price')} "
                      f"categ={m2o(p.get('categ_id'))[:30]}")

    print("\n[FIM s7_fluxo_pa — READ-only, nada escrito]")


if __name__ == '__main__':
    main()
