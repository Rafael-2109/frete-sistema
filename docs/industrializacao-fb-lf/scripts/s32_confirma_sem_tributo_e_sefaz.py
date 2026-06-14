#!/usr/bin/env python3
"""S32 — READ-only: fechar a duvida do 'imposto'. O -278,17 da NF 788504 e' a
CONTRAPARTIDA da baixa da PASSIVA 5101020001 (no_payment), NAO tributo (s31:
tax_line_id vazio, conta = a PASSIVA). Confirma em definitivo:

  1. product lines da 788504: TODOS os l10n_br_*_valor (ICMS/PIS/COFINS/IPI) = 0?
     -> se sim, NAO ha tributo; o XML SEFAZ sai com imposto 0 (so a baixa contabil).
  2. 5902 da NF REAL mista 709632: os mesmos valores (consistencia do alvo).
  3. SARET 725475 (NF separada real, total=0): foi AUTORIZADA na SEFAZ? (chave/protocolo/
     status) -> precedente de que total=0 / amount_tax negativo transmite.

READ-ONLY.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF_NOSSA = 788504
NF_REAL = 709632
SARET = 725475
VAL_FIELDS = ['l10n_br_icms_valor', 'l10n_br_icms_base', 'l10n_br_pis_valor', 'l10n_br_pis_base',
              'l10n_br_cofins_valor', 'l10n_br_cofins_base', 'l10n_br_ipi_valor', 'l10n_br_ipi_base']


def m2o(v):
    return f"{v[0]}|{str(v[1])[:28]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def soma_tributo(nf):
        lns = rr('account.move.line', [('move_id', '=', nf), ('display_type', '=', 'product'),
                                       ('l10n_br_cfop_codigo', '=', '5902')],
                 ['price_subtotal', 'price_total'] + VAL_FIELDS)
        tot = {f: round(sum(l.get(f) or 0 for l in lns), 2) for f in VAL_FIELDS}
        sub = round(sum(l.get('price_subtotal') or 0 for l in lns), 2)
        ptot = round(sum(l.get('price_total') or 0 for l in lns), 2)
        return lns, tot, sub, ptot

    for label, nf in [('NOSSA 788504 (s30)', NF_NOSSA), ('REAL mista 709632', NF_REAL)]:
        lns, tot, sub, ptot = soma_tributo(nf)
        print("=" * 92)
        print(f"### {label}: {len(lns)} linhas 5902 | price_subtotal={sub} price_total={ptot}")
        nz = {f: v for f, v in tot.items() if v}
        print(f"   tributo nas linhas: {'TUDO ZERO ✅' if not nz else nz}")
        print(f"   => subtotal==total? {'✅ sim (sem imposto por dentro)' if sub == ptot else '❌ NAO'}")

    # SARET — situacao SEFAZ
    print("\n" + "=" * 92)
    print(f"### SARET {SARET} — situacao SEFAZ (precedente de total=0)")
    hfg = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['string'], 'context': CTX})
    sefaz_f = sorted([f for f in hfg if any(k in f.lower() for k in
                     ['chave', 'protocolo', 'autoriz', 'sefaz', 'nfe', 'status', 'situacao', 'cstat'])])
    want = [f for f in sefaz_f if f in hfg][:30]
    h = rr('account.move', [('id', '=', SARET)], ['name', 'amount_total', 'state'] + want)
    if h:
        h = h[0]
        print(f"   {h.get('name')} state={h.get('state')} total={h.get('amount_total')}")
        for f in want:
            v = h.get(f)
            if v not in (False, None, '', 0, 0.0, []):
                print(f"   {f:34} = {m2o(v) if isinstance(v, list) else str(v)[:60]}")


if __name__ == '__main__':
    main()
