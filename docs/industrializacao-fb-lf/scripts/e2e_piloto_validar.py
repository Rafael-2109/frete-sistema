#!/usr/bin/env python3
"""
PILOTO 4870112 — VALIDADOR read-only do teste controlado (1 caixa). NAO escreve nada.

Mede o Delta DO CICLO (cadeia documental + lote do piloto), nao saldo absoluto
(5101010001=R$60,8M, 26489 com ruido historico). Metricas-chave sao COMPUTADAS (PASS/FAIL).

Modos:
  --modo baseline      A0: snapshot contabil (saldos posted FB+LF) + fisico por lote. Salva
                       JSON (--out) p/ diff.
  --modo diff --base   Delta vs um baseline salvo (contabil + fisico).
  --modo preflight-lf  pre-C: checa default_location_dest_id de pt64/pt19 (deve ser 31092).
  --modo remessa       D(B): NET D 5101010001 +I / C 1150100002 -I (cadeia); 1150100012=0;
                       16 comps em 26489 (lote).
  --modo entrada-lf    D(C): dst==31092; COMPUTA Delta 1150100011(LF)=0 (Design A) na cadeia
                       NF+SVL; COMPUTA 26489(lote)=0.
  --modo mo            F(E): consumo de 31092; PA (finished move) em 31093; loc 42 inalterado
                       (vs --base).
  --modo entrada-fb    I(H): linhas 1902 com op 3252 E sem stock.move/SVL de componentes
                       (G5b). RESSALVA: 5101010001(FB) NAO zera (G5a/Contador).

Uso:
  python e2e_piloto_validar.py --modo baseline --lote PILOTO-3105 --out /tmp/base.json
  python e2e_piloto_validar.py --modo entrada-lf --picking <pt64> --nf <entin> --lote PILOTO-3105
  python e2e_piloto_validar.py --modo diff --base /tmp/base.json --lote PILOTO-3105
"""
import argparse
import json
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_FB, CMP_LF = 1, 5
PA_CODE = '4870112'
COMPS = ['207210014', '208000008', '208000010', '210030010', '210030110', '210030203',
         '210030322', '104000004', '104000007', '104000015', '104000018', '104000002',
         '105000023', '105000024', '105000039', '105000022']
AGUA = '104000017'
LOCS = {8: 'FB/Estoque', 26489: 'Em Transito', 31092: 'LF/Mat.Terceiros',
        31093: 'LF/PA Terceiros', 42: 'LF/Estoque', 53: 'LF/Pre-Producao'}
ACC_SNAP = [
    ('5101010001', CMP_FB), ('5101020001', CMP_FB), ('5101010002', CMP_FB), ('5101020002', CMP_FB),
    ('1150100002', CMP_FB), ('1150100007', CMP_FB), ('1150100011', CMP_FB),
    ('1150100012', CMP_FB), ('1150200001', CMP_FB),
    ('5101010001', CMP_LF), ('5101020001', CMP_LF), ('1150100011', CMP_LF),
    ('1150100012', CMP_LF), ('1150200001', CMP_LF), ('1150100007', CMP_LF), ('1150100004', CMP_LF),
]
PASS = lambda b: 'PASS' if b else '*** FAIL'


def sec(t): print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def resolve_acc(o, code, cmp):
    r = o.search_read('account.account', [('code', '=', code), ('company_id', '=', cmp)], ['id'], limit=1)
    return r[0]['id'] if r else None


def saldo_posted(o, acc_id):
    if not acc_id:
        return {'balance': 0.0, 'debit': 0.0, 'credit': 0.0}
    g = o.execute_kw('account.move.line', 'read_group',
                     [[('account_id', '=', acc_id), ('parent_state', '=', 'posted')],
                      ['balance:sum', 'debit:sum', 'credit:sum'], []], {'lazy': False})
    if not g:
        return {'balance': 0.0, 'debit': 0.0, 'credit': 0.0}
    return {'balance': g[0].get('balance') or 0.0, 'debit': g[0].get('debit') or 0.0, 'credit': g[0].get('credit') or 0.0}


def prod_ids(o, codes):
    out = {}
    for c in codes:
        r = o.search_read('product.product', [('default_code', '=', c)], ['id'], limit=1)
        if r:
            out[c] = r[0]['id']
    return out


def loc_ids_all(o):
    ids = set()
    for base in LOCS:
        for s in o.search_read('stock.location', [('id', 'child_of', base)], ['id'], limit=500):
            ids.add(s['id'])
    return list(ids)


def quants_fisico(o, pids, lote=None, loc_filter=None):
    dom = [('product_id', 'in', list(pids.values())), ('location_id', 'in', loc_ids_all(o)), ('quantity', '!=', 0)]
    qs = o.search_read('stock.quant', dom, ['product_id', 'location_id', 'lot_id', 'quantity', 'reserved_quantity'], limit=800)
    out = []
    for q in qs:
        ln = q['lot_id'][1] if q['lot_id'] else '-'
        lid = q['location_id'][0] if q['location_id'] else None
        if lote and lote.lower() not in str(ln).lower():
            continue
        if loc_filter and lid not in loc_filter:
            continue
        out.append({'prod': q['product_id'][1], 'loc_id': lid, 'loc': q['location_id'][1] if q['location_id'] else '?',
                    'lote': ln, 'qty': q['quantity'], 'free': q['quantity'] - q['reserved_quantity']})
    return out


def move_accounts(o, move_id):
    mls = o.search_read('account.move.line', [('move_id', '=', move_id)], ['account_id', 'debit', 'credit', 'product_id'], limit=80)
    return [(m['account_id'][1].split(' ')[0] if m['account_id'] else '?', m['account_id'][0] if m['account_id'] else None,
             m['debit'], m['credit'], m['product_id'][1] if m['product_id'] else '') for m in mls]


def show_move(o, move_id, label):
    mv = o.read('account.move', [move_id], ['name', 'state', 'move_type', 'journal_id'])
    if not mv:
        print(f"  {label}: move {move_id} nao encontrado"); return
    mv = mv[0]
    print(f"  {label}: {mv['name']} state={mv['state']} journal={mv['journal_id'][1] if mv['journal_id'] else '?'}")
    for code, _aid, d, c, prod in move_accounts(o, move_id):
        flag = '  <ATIVA' if code.startswith('51010') else ('  <PASSIVA' if code.startswith('51020') else
               ('  <terceiros' if code == '1150200001' else ('  <transitoria' if code in ('1150100011', '1150100012') else '')))
        print(f"      {code:12} D={d:>12,.2f} C={c:>12,.2f} {prod[:28]}{flag}")


def delta_on_account_chain(o, move_ids, acc_id):
    """soma (debit-credit) das account.move.line dos moves dados, na conta dada."""
    if not move_ids or not acc_id:
        return None
    mls = o.search_read('account.move.line', [('move_id', 'in', list(move_ids)), ('account_id', '=', acc_id)],
                        ['debit', 'credit'], limit=200)
    return sum((m['debit'] or 0) - (m['credit'] or 0) for m in mls)


def svl_account_moves(o, picking_id):
    mvs = [m['id'] for m in o.search_read('stock.move', [('picking_id', '=', picking_id)], ['id'], limit=80)]
    if not mvs:
        return [], []
    svls = o.search_read('stock.valuation.layer', [('stock_move_id', 'in', mvs)],
                         ['value', 'account_move_id', 'product_id', 'quantity'], limit=300)
    am_ids = list({s['account_move_id'][0] for s in svls if s['account_move_id']})
    return svls, am_ids


# --------------------------------------------------------------------------- modos
def modo_baseline(o, args):
    sec("A0 — SNAPSHOT BASELINE (contabil posted + fisico por lote)")
    snap = {'lote': args.lote, 'contabil': {}, 'fisico': []}
    print("  CONTABIL (saldo posted):")
    for code, cmp in ACC_SNAP:
        s = saldo_posted(o, resolve_acc(o, code, cmp))
        snap['contabil'][f"{code}@{cmp}"] = s
        emp = 'FB' if cmp == CMP_FB else 'LF'
        print(f"    {code}@{emp:2}: balance={s['balance']:>18,.2f}")
    fis = quants_fisico(o, prod_ids(o, COMPS + [PA_CODE, AGUA]), args.lote)
    snap['fisico'] = fis
    print(f"\n  FISICO ({'lote '+args.lote if args.lote else 'todos'}): {len(fis)} quants")
    for f in fis:
        print(f"    {f['prod'][:32]:32} loc{f['loc_id']}={f['loc'][:22]:22} lote={f['lote'][:14]:14} qty={f['qty']:>10}")
    if args.out:
        json.dump(snap, open(args.out, 'w'), indent=2, default=str)
        print(f"\n  [salvo: {args.out}] — rode '--modo diff --base {args.out}' apos o ciclo.")


def modo_diff(o, args):
    sec("DIFF — Delta vs baseline (contabil + fisico)")
    if not args.base:
        print("  passe --base <snapshot.json>"); return
    base = json.load(open(args.base))
    print("  CONTABIL Delta (atual - base):")
    for code, cmp in ACC_SNAP:
        atual = saldo_posted(o, resolve_acc(o, code, cmp))['balance']
        b = (base['contabil'].get(f"{code}@{cmp}") or {}).get('balance', 0.0)
        d = atual - b
        emp = 'FB' if cmp == CMP_FB else 'LF'
        mark = '' if abs(d) < 0.005 else '  <-- mudou'
        print(f"    {code}@{emp:2}: Delta={d:>16,.2f}{mark}")
    print("\n  FISICO Delta (por prod+loc+lote):")
    cur = {(f['prod'], f['loc_id'], f['lote']): f['qty'] for f in quants_fisico(o, prod_ids(o, COMPS + [PA_CODE, AGUA]), args.lote)}
    bas = {(f['prod'], f['loc_id'], f['lote']): f['qty'] for f in base.get('fisico', [])}
    for k in sorted(set(cur) | set(bas)):
        d = cur.get(k, 0) - bas.get(k, 0)
        if abs(d) > 1e-6:
            print(f"    {str(k[0])[:30]:30} loc{k[1]} lote={str(k[2])[:12]:12} Delta={d:>10}")


def modo_preflight_lf(o, args):
    sec("PRE-FLIGHT C — picking type da entrada LF (dst deve ser 31092 Materiais de Terceiros)")
    for pt in (64, 19):
        r = o.read('stock.picking.type', [pt], ['name', 'default_location_dest_id', 'default_location_src_id'])
        if not r:
            print(f"  pt{pt}: nao encontrado"); continue
        r = r[0]
        dst = r['default_location_dest_id'][0] if r['default_location_dest_id'] else None
        print(f"  pt{pt} {r['name'][:30]:30} src={r['default_location_src_id']} dst={r['default_location_dest_id']} "
              f"{PASS(dst == 31092)} (esperado dst=31092)")
    print("  -> se != 31092: override no picking da entrada (location_dest_id=31092) OU ajustar o default do pt.")
    print("  NOTA: producao real usa pt19 (96%) vs pt64 (ocioso). Para o piloto, garantir dst=31092 seja qual for o pt.")


def modo_remessa(o, args):
    sec("D(B) — VALIDACAO DA REMESSA (NF 5901 + picking pt53)")
    chain = set()
    if args.picking:
        pk = o.read('stock.picking', [args.picking], ['name', 'state'])[0]
        print(f"  picking {pk['name']} state={pk['state']}")
        for m in o.search_read('stock.move', [('picking_id', '=', args.picking)],
                               ['product_id', 'product_qty', 'location_id', 'location_dest_id', 'state'], limit=60):
            print(f"    {m['product_id'][1][:28]:28} qty={m['product_qty']:>8} {m['location_id'][0]}->{m['location_dest_id'][0]} ({m['state']})")
        svls, am_ids = svl_account_moves(o, args.picking)
        chain.update(am_ids)
        print(f"  SVL: {len(svls)} (valor {sum(s['value'] for s in svls):,.2f}); account.moves: {am_ids}")
        for amid in am_ids:
            show_move(o, amid, 'SVL')
    if args.nf:
        chain.add(args.nf)
        show_move(o, args.nf, 'NF 5901')
    # COMPUTA: NET na cadeia
    acc_ativa = resolve_acc(o, '5101010001', CMP_FB)
    acc_emb = resolve_acc(o, '1150100002', CMP_FB)
    acc_trans = resolve_acc(o, '1150100012', CMP_FB)
    d_ativa = delta_on_account_chain(o, chain, acc_ativa)
    d_emb = delta_on_account_chain(o, chain, acc_emb)
    d_trans = delta_on_account_chain(o, chain, acc_trans)
    print(f"\n  COMPUTADO na cadeia {sorted(chain)}:")
    print(f"    5101010001 (ATIVA) Delta = {d_ativa:>12,.2f}  {PASS(d_ativa and d_ativa > 0)} (esperado +I, debito)")
    print(f"    1150100002 (EMB)   Delta = {d_emb:>12,.2f}  {PASS(d_emb and d_emb < 0)} (esperado -I, credito)")
    print(f"    1150100012 (trans) Delta = {d_trans:>12,.2f}  {PASS(abs(d_trans or 0) < 0.01)} (esperado 0)")
    print("\n  FISICO: 16 comps em 26489 (lote)?")
    q26489 = quants_fisico(o, prod_ids(o, COMPS), args.lote, loc_filter={26489})
    print(f"    {len(q26489)} quants em 26489 (lote {args.lote}): {PASS(len(q26489) > 0)}")
    for f in q26489:
        print(f"      {f['prod'][:30]:30} qty={f['qty']}")


def modo_entrada_lf(o, args):
    sec("D(C) — VALIDACAO ENTRADA LF (dst=31092 + Delta 1150100011(LF)=0 COMPUTADO)")
    chain = set()
    if args.picking:
        pk = o.read('stock.picking', [args.picking], ['name', 'state', 'location_dest_id'])[0]
        dst = pk['location_dest_id'][0] if pk['location_dest_id'] else None
        print(f"  picking {pk['name']} dst={pk['location_dest_id']} {PASS(dst == 31092)} (esperado 31092)")
        _, am_ids = svl_account_moves(o, args.picking)
        chain.update(am_ids)
        for amid in am_ids:
            show_move(o, amid, 'SVL entrada LF (esperado D 1150200001 / C 1150100011)')
    if args.nf:
        chain.add(args.nf)
        show_move(o, args.nf, 'NF ENTIN (esperado D 1150100011 / C 5101020001 PASSIVA)')
    acc_trans_lf = resolve_acc(o, '1150100011', CMP_LF)
    acc_ter_lf = resolve_acc(o, '1150200001', CMP_LF)
    d_trans = delta_on_account_chain(o, chain, acc_trans_lf)
    d_ter = delta_on_account_chain(o, chain, acc_ter_lf)
    print(f"\n  COMPUTADO na cadeia {sorted(chain)} (Design A):")
    print(f"    1150100011 (LF, transitoria) Delta = {d_trans if d_trans is not None else 'N/A':>12}  {PASS(d_trans is not None and abs(d_trans) < 0.01)} (esperado 0 — fecha)")
    print(f"    1150200001 (LF, terceiros)   Delta = {d_ter if d_ter is not None else 'N/A':>12}  (esperado +valor, material sob custodia)")
    q26489 = quants_fisico(o, prod_ids(o, COMPS), args.lote, loc_filter={26489})
    tot = sum(f['qty'] for f in q26489)
    print(f"\n  FISICO: 26489 do lote zerou? soma={tot:.4f} ({len(q26489)} quants) {PASS(abs(tot) < 1e-6)}")
    q31092 = quants_fisico(o, prod_ids(o, COMPS), args.lote, loc_filter={31092})
    print(f"  material em 31092 (Mat.Terceiros)? {len(q31092)} quants {PASS(len(q31092) > 0)}")


def modo_mo(o, args):
    sec("F(E) — VALIDACAO MOs (consumo de 31092; PA em 31093; loc 42 inalterado)")
    for tag, mid in (('BATELADA', args.mo), ('PA', args.mo2)):
        if not mid:
            continue
        mo = o.read('mrp.production', [mid], ['name', 'state', 'product_id', 'product_qty'])
        if not mo:
            print(f"  MO {tag} {mid} nao encontrada"); continue
        mo = mo[0]
        print(f"\n  MO {tag}: {mo['name']} state={mo['state']} produz {mo['product_id'][1][:24]} qty={mo['product_qty']}")
        raws = o.search_read('stock.move', [('raw_material_production_id', '=', mid)],
                             ['product_id', 'product_qty', 'location_id', 'state'], limit=40)
        for r in raws:
            src = r['location_id'][0] if r['location_id'] else None
            print(f"    consome {r['product_id'][1][:24]:24} qty={r['product_qty']:>8} de loc{src} {PASS(src == 31092)}")
        fins = o.search_read('stock.move', [('production_id', '=', mid), ('raw_material_production_id', '=', False)],
                             ['product_id', 'product_qty', 'location_dest_id', 'state'], limit=10)
        for f in fins:
            dst = f['location_dest_id'][0] if f['location_dest_id'] else None
            esperado = 31093 if tag == 'PA' else None
            print(f"    PRODUZ  {f['product_id'][1][:24]:24} qty={f['product_qty']:>8} -> loc{dst} "
                  f"{PASS(dst == esperado) if esperado else '(semi)'}")
    if args.base:
        base = json.load(open(args.base))
        bas42 = {(f['prod'], f['lote']): f['qty'] for f in base.get('fisico', []) if f['loc_id'] == 42}
        cur42 = {(f['prod'], f['lote']): f['qty'] for f in quants_fisico(o, prod_ids(o, COMPS + [PA_CODE]), args.lote, loc_filter={42})}
        diffs = [(k, cur42.get(k, 0) - bas42.get(k, 0)) for k in set(bas42) | set(cur42) if abs(cur42.get(k, 0) - bas42.get(k, 0)) > 1e-6]
        print(f"\n  loc 42 (LF/Estoque proprio) inalterado vs base? {PASS(not diffs)} {diffs if diffs else ''}")
    else:
        print("\n  (passe --base p/ checar loc 42 inalterado)")


def modo_entrada_fb(o, args):
    sec("I(H) — VALIDACAO ENTRADA FB (G5b: 1902 op 3252 + 0 stock.move/SVL de componentes)")
    if not args.nf:
        print("  passe --nf <account.move da entrada FB>"); return
    mv = o.read('account.move', [args.nf], ['name', 'state'])[0]
    print(f"  NF entrada FB: {mv['name']} state={mv['state']}")
    lines = o.search_read('account.move.line', [('move_id', '=', args.nf), ('product_id', '!=', False)],
                          ['product_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id'], limit=80)
    n_1902, n_3252, prods_1902 = 0, 0, set()
    for l in lines:
        cfop = l['l10n_br_cfop_id'][1].split(' ')[0] if l['l10n_br_cfop_id'] else '-'
        is3252 = l['l10n_br_operacao_id'] and l['l10n_br_operacao_id'][0] == 3252
        if cfop.startswith('1902'):
            n_1902 += 1
            prods_1902.add(l['product_id'][0])
            if is3252:
                n_3252 += 1
        op = l['l10n_br_operacao_id'][1][:22] if l['l10n_br_operacao_id'] else '-'
        print(f"    {l['product_id'][1][:28]:28} CFOP={cfop:6} op={op} {'<op3252' if is3252 else ''}")
    print(f"\n  linhas 1902: {n_1902} | com op 3252: {n_3252}  {PASS(n_1902 and n_1902 == n_3252)}")
    # COMPUTA G5b: as linhas 1902 NAO podem ter SVL (movimento_estoque=False)
    svl_1902 = o.search_read('stock.valuation.layer', [('account_move_id', '=', args.nf), ('product_id', 'in', list(prods_1902))],
                             ['product_id', 'value'], limit=100) if prods_1902 else []
    print(f"  G5b: SVL de componentes (linhas 1902) nesta NF = {len(svl_1902)} {PASS(len(svl_1902) == 0)} (esperado 0; sem double-count)")
    for s in svl_1902:
        print(f"      *** SVL indevido: {s['product_id'][1]} valor={s['value']}")
    print("  RESSALVA G5a: 5101010001(FB) NAO zera neste piloto (depende do journal novo -> Contador). Fora do escopo G5b.")
    print("\n  PA 4870112 entrou em FB/Estoque(8)?")
    for f in quants_fisico(o, prod_ids(o, [PA_CODE]), args.lote, loc_filter={8}):
        print(f"    {f['prod'][:30]:30} lote={f['lote'][:12]:12} qty={f['qty']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--modo', required=True,
                    choices=['baseline', 'diff', 'preflight-lf', 'remessa', 'entrada-lf', 'mo', 'entrada-fb'])
    ap.add_argument('--lote', default=None)
    ap.add_argument('--picking', type=int)
    ap.add_argument('--nf', type=int)
    ap.add_argument('--mo', type=int)
    ap.add_argument('--mo2', type=int)
    ap.add_argument('--out')
    ap.add_argument('--base')
    args = ap.parse_args()
    o = get_odoo_connection(); o.authenticate()
    {'baseline': modo_baseline, 'diff': modo_diff, 'preflight-lf': modo_preflight_lf,
     'remessa': modo_remessa, 'entrada-lf': modo_entrada_lf, 'mo': modo_mo,
     'entrada-fb': modo_entrada_fb}[args.modo](o, args)
    print("\n" + "=" * 100 + "\nFIM (read-only)\n" + "=" * 100)


if __name__ == '__main__':
    main()
