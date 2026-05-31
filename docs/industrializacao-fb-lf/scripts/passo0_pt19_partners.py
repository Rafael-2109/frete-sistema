#!/usr/bin/env python3
"""
Passo 0 — Desambiguar pt19 LF/IN (READ-ONLY): as 800 entradas vem de fornecedor
EXTERNO (compra propria real -> premissa 'tudo terceiros' FALSA) ou da FB
(remessa de industrializacao roteada errado)?

Uso: source .venv/bin/activate
     python docs/industrializacao-fb-lf/scripts/passo0_pt19_partners.py
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_LF = 5
PT_LF_IN = 19
CUTOFF = '2025-05-01'
FB_PARTNERS = {1, 35}  # FB global / LF-em-FB; intercompany markers


def main():
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise SystemExit("Falha auth Odoo")

    print("=" * 90)
    print("pt19 LF/IN — top parceiros (state=done, desde", CUTOFF, ")")
    print("=" * 90)
    grp = odoo.execute_kw('stock.picking', 'read_group',
                          [[('company_id', '=', CMP_LF),
                            ('picking_type_id', '=', PT_LF_IN),
                            ('state', '=', 'done'),
                            ('date_done', '>=', CUTOFF)],
                           ['id'], ['partner_id']],
                          {'lazy': False})
    grp = sorted(grp, key=lambda x: -x['__count'])
    total = sum(g['__count'] for g in grp)
    print(f"  total pt19 done (12m): {total}")
    # caracterizar parceiros: commercial / supplier_rank / company vinculada
    pids = [g['partner_id'][0] for g in grp if g['partner_id']]
    pinfo = {}
    if pids:
        for p in odoo.read('res.partner', pids,
                           ['name', 'supplier_rank', 'customer_rank', 'vat', 'parent_id']):
            pinfo[p['id']] = p
    fb_count = 0
    print(f"\n  {'#pck':>6} {'partner':40s} {'sup_rank':>8} {'vat':>18}")
    for g in grp[:25]:
        pid = g['partner_id'][0] if g['partner_id'] else None
        nm = g['partner_id'][1] if g['partner_id'] else '(sem parceiro)'
        info = pinfo.get(pid, {})
        vat = info.get('vat') or ''
        sr = info.get('supplier_rank', '?')
        is_fb = (pid in FB_PARTNERS) or ('18467441' in (vat or '')) or \
                ('61724241' in (vat or '')) or ('FAMIGLIA' in nm.upper()) or \
                ('NACOM' in nm.upper())
        if is_fb:
            fb_count += g['__count']
        flag = '  <-- INTERCOMPANY FB/LF' if is_fb else ''
        print(f"  {g['__count']:>6} {nm[:40]:40s} {sr:>8} {vat[:18]:>18}{flag}")
    print(f"\n  >> pt19 de parceiros FB/LF (intercompany): {fb_count}")
    print(f"  >> pt19 de fornecedores EXTERNOS (compra propria real): {total - fb_count}")


if __name__ == '__main__':
    main()
