#!/usr/bin/env python3
"""S17 — Passo 2 grounding (READ-only): qual e' a FONTE REAL dos componentes 5902
do retorno, sem assumir subcontract. Resolve a divergencia apontada pelo Rafael:
"o 4870112 funciona quando o sistema abre os componentes" — entao a fonte do shoyu
NAO depende necessariamente de BoM type=subcontract (que o s15/GATE 1c explode).

READ-ONLY. Zero escrita. Mapeia:
  1. todas as mrp.bom dos 2 produtos (4870112 shoyu/piloto + 4739099 azeite): type, n linhas
  2. as bom_line de cada BoM (componentes diretos)
  3. as linhas-produto da REMESSA real RPI/2026/00245 (5901) — a fonte determinista
     (invariante retorno 5902 = remessa 5901), com qty/price/cfop/op
  4. se existir, uma VND mista real de RETORNO do 4870112 (linha 5124 = shoyu) e suas 5902

MODOS (sem args = roda 1-3; --retorno tambem):
  --bom           BoMs dos 2 produtos + componentes
  --remessa       linhas da remessa RPI/2026/00245
  --retorno       procura VND de retorno real do shoyu 4870112
"""
import sys
import argparse
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
CODS = ['4870112', '4739099']          # shoyu/piloto · azeite
REMESSA_NAME = 'RPI/2026/00245'        # NF 5901 do piloto (move 735679)
REMESSA_MOVE = 735679


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def dump_bom(o):
    print("=" * 84)
    print("=== 1) BoMs dos 2 produtos (type + componentes diretos) ===")
    prods = o.execute_kw('product.product', 'search_read',
                         [[('default_code', 'in', CODS)]],
                         {'fields': ['id', 'default_code', 'name', 'product_tmpl_id'], 'context': CTX})
    for p in prods:
        tmpl = p['product_tmpl_id'][0]
        print(f"\n### {p['default_code']} — {p['name'][:46]} (product={p['id']} tmpl={tmpl})")
        boms = o.execute_kw('mrp.bom', 'search_read',
                            [['|', ('product_id', '=', p['id']), ('product_tmpl_id', '=', tmpl)]],
                            {'fields': ['id', 'type', 'product_qty', 'code', 'company_id',
                                        'product_id', 'product_tmpl_id'], 'context': CTX})
        if not boms:
            print("   (nenhuma BoM)")
            continue
        for b in boms:
            lines = o.execute_kw('mrp.bom.line', 'search_read', [[('bom_id', '=', b['id'])]],
                                 {'fields': ['product_id', 'product_qty', 'product_uom_id'], 'context': CTX})
            print(f"   BoM {b['id']} type={b['type']:11} rende={b['product_qty']} code={b.get('code')} "
                  f"company={m2o(b.get('company_id'))} comps={len(lines)}")
            for ln in lines:
                pc = ln['product_id']
                # componente e' semi-acabado (tem BoM propria)?
                sub = o.execute_kw('mrp.bom', 'search_count',
                                   [['|', ('product_id', '=', pc[0]),
                                     ('product_tmpl_id.product_variant_ids', 'in', [pc[0]])]], {'context': CTX})
                tag = ' [SEMI=tem BoM]' if sub else ''
                print(f"       - {m2o(pc)[:52]:52} qty={ln['product_qty']}{tag}")


def dump_remessa(o):
    print("\n" + "=" * 84)
    print(f"=== 2) REMESSA real {REMESSA_NAME} (move {REMESSA_MOVE}) — linhas 5901 (fonte determinista) ===")
    mv = o.execute_kw('account.move', 'read', [[REMESSA_MOVE]],
                      {'fields': ['name', 'state', 'journal_id', 'partner_id', 'l10n_br_operacao_id',
                                  'l10n_br_tipo_pedido', 'amount_total', 'invoice_origin'], 'context': CTX})
    if not mv:
        print("   (move da remessa nao encontrado por id; tentando por name...)")
        ids = o.execute_kw('account.move', 'search', [[('name', '=', REMESSA_NAME)]], {'context': CTX})
        if not ids:
            print("   (nenhum)"); return
        mv = o.execute_kw('account.move', 'read', [ids],
                          {'fields': ['name', 'state', 'journal_id', 'partner_id', 'l10n_br_operacao_id',
                                      'l10n_br_tipo_pedido', 'amount_total'], 'context': CTX})
    h = mv[0]
    print(f"   HEADER: {h.get('name')} state={h.get('state')} journal={m2o(h.get('journal_id'))} "
          f"partner={m2o(h.get('partner_id'))} op={m2o(h.get('l10n_br_operacao_id'))} "
          f"tipo_ped={h.get('l10n_br_tipo_pedido')} total={h.get('amount_total')}")
    lines = o.execute_kw('account.move.line', 'search_read',
                         [[('move_id', '=', h['id']), ('display_type', '=', 'product')]],
                         {'fields': ['product_id', 'l10n_br_cfop_codigo', 'l10n_br_icms_cst',
                                     'l10n_br_operacao_id', 'quantity', 'price_unit', 'price_subtotal'],
                          'context': CTX, 'order': 'id'})
    for ln in lines:
        print(f"     {m2o(ln['product_id'])[:50]:50} cfop={ln.get('l10n_br_cfop_codigo')} "
              f"cst={ln.get('l10n_br_icms_cst')} op={m2o(ln.get('l10n_br_operacao_id'))[:18]:18} "
              f"qty={ln.get('quantity')} pu={ln.get('price_unit')} sub={ln.get('price_subtotal')}")
    print(f"   RESUMO remessa: {len(lines)} linhas | CFOPs="
          f"{dict(Counter(str(l.get('l10n_br_cfop_codigo')) for l in lines))}")


def dump_retorno(o):
    print("\n" + "=" * 84)
    print("=== 3) VND de retorno REAL do shoyu 4870112 (linha 5124 = shoyu) ? ===")
    prod = o.execute_kw('product.product', 'search_read', [[('default_code', '=', '4870112')]],
                        {'fields': ['id'], 'context': CTX})
    if not prod:
        print("   (produto 4870112 nao encontrado)"); return
    pid = prod[0]['id']
    # linhas 5124 desse produto em VND (saida LF)
    lns = o.execute_kw('account.move.line', 'search_read',
                       [[('product_id', '=', pid), ('l10n_br_cfop_codigo', '=', '5124'),
                         ('parent_state', '=', 'posted')]],
                       {'fields': ['move_id'], 'context': CTX, 'limit': 5, 'order': 'id desc'})
    moves = list({l['move_id'][0] for l in lns if l.get('move_id')})
    if not moves:
        print("   (nenhuma VND de retorno real do 4870112 com 5124 — piloto pode nunca ter retornado)")
        return
    for mid in moves[:3]:
        nl = o.execute_kw('account.move.line', 'search_read',
                          [[('move_id', '=', mid), ('display_type', '=', 'product')]],
                          {'fields': ['l10n_br_cfop_codigo', 'l10n_br_operacao_id', 'create_uid'],
                           'context': CTX})
        cf = Counter(str(x.get('l10n_br_cfop_codigo')) for x in nl)
        uids = Counter(m2o(x.get('create_uid')) for x in nl)
        print(f"   move {mid}: {len(nl)} linhas CFOPs={dict(cf)} create_uid={dict(uids)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bom', action='store_true')
    ap.add_argument('--remessa', action='store_true')
    ap.add_argument('--retorno', action='store_true')
    args = ap.parse_args()
    todos = not (args.bom or args.remessa or args.retorno)

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"

    if todos or args.bom:
        dump_bom(o)
    if todos or args.remessa:
        dump_remessa(o)
    if todos or args.retorno:
        dump_retorno(o)


if __name__ == '__main__':
    main()
