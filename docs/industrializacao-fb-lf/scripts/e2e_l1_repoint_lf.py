#!/usr/bin/env python3
"""
E2E passo L1 — repoint das 14 categorias do piloto na LF (Design A).
Valoração -> 1150200001 (terceiros, LF id 26140); input -> 1150100011 (26845); output -> 1150100012 (26855).
Salva SNAPSHOT (reversível) em /tmp/e2e_l1_snapshot.json.

--dry-run DEFAULT (não escreve). --execute aplica (contexto LF) + salva snapshot. --revert restaura do snapshot.
"""
import argparse
import json
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_LF = 5
CATS = [57, 64, 69, 73, 75, 76, 77, 78, 90, 193, 387, 388, 393, 395]
ALVO = {
    'property_stock_valuation_account_id': 26140,   # 1150200001 MATERIAL EM TERCEIROS (LF)
    'property_stock_account_input_categ_id': 26845,  # 1150100011 RECEB FISICO (LF) — fecha NF entrada
    'property_stock_account_output_categ_id': 26855,  # 1150100012 FATUR FISICO (LF) — fecha NF saida
}
FLDS = list(ALVO) + ['complete_name', 'property_valuation']
SNAP = '/tmp/e2e_l1_snapshot.json'


def ctx():
    return {'allowed_company_ids': [CMP_LF], 'company_id': CMP_LF}


def read_ctx(o, ids):
    return o.execute_kw('product.category', 'read', [ids, FLDS], {'context': ctx()})


def fmt(v):
    return f"{v[1].split(' ')[0]}" if isinstance(v, list) and v else str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--revert', action='store_true')
    args = ap.parse_args()
    o = get_odoo_connection(); o.authenticate()

    if args.revert:
        snap = json.load(open(SNAP))
        print(f"REVERT L1 — restaurando {len(snap)} categorias do snapshot")
        for cid, vals in snap.items():
            o.execute_kw('product.category', 'write', [[int(cid)], vals], {'context': ctx()})
            print(f"  categ {cid} restaurada: {vals}")
        return

    cur = {c['id']: c for c in read_ctx(o, CATS)}
    print("=" * 96)
    print(f"L1 REPOINT LF (Design A) — {'EXECUTE' if args.execute else 'DRY-RUN'} — {len(CATS)} categorias")
    print("=" * 96)
    print(f"ALVO: valoração->1150200001(26140) input->1150100011(26845) output->1150100012(26855)\n")
    snap = {}
    for cid in CATS:
        c = cur[cid]
        snap[str(cid)] = {k: (c[k][0] if isinstance(c.get(k), list) and c.get(k) else False) for k in ALVO}
        print(f"  categ {cid:<5} {c['complete_name'].split('/')[-1].strip()[:24]:24} val/in/out: "
              f"{fmt(c['property_stock_valuation_account_id'])}/{fmt(c['property_stock_account_input_categ_id'])}/"
              f"{fmt(c['property_stock_account_output_categ_id'])}  (valuation={c['property_valuation']})")

    if not args.execute:
        print(f"\nDRY-RUN: nada escrito. Snapshot seria salvo em {SNAP}. --execute aplica; --revert restaura.")
        return

    json.dump(snap, open(SNAP, 'w'), indent=2)
    print(f"\n[snapshot salvo: {SNAP}]")
    for cid in CATS:
        o.execute_kw('product.category', 'write', [[cid], ALVO], {'context': ctx()})
    chk = {c['id']: c for c in read_ctx(o, CATS)}
    ok = all(chk[cid]['property_stock_valuation_account_id'] and chk[cid]['property_stock_valuation_account_id'][0] == 26140 for cid in CATS)
    print(f"[OK] {len(CATS)} categorias repointadas. valoração=1150200001 confirmado: {ok}")


if __name__ == '__main__':
    main()
