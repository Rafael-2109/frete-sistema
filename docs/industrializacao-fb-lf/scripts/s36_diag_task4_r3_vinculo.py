#!/usr/bin/env python3
"""S36 — READ-only: preparar a Task #4 (unir NF-1 servico 5124 + NF-2 insumos 5902 numa
SA + vinculo R3). Investiga o que falta (as 2 NFs ja estao provadas: NF-1=GATE 1c/s15,
NF-2=s35):

  1. ESTADO do PA shoyu 4870112 em 31093 (lote PILOTO-3105) — pre-condicao do picking pt66.
  2. R3 — campos de VINCULO em account.move: referencia_ids (refNFe) + invoice_origin
     (tipo/relacao/modelo) — como apontar uma NF a outra / a remessa.
  3. Como as NFs REAIS preenchem o vinculo: a mista 709632 e a SARET 725475 tem
     referencia_ids? invoice_origin? apontam p/ a remessa (RPI) ou p/ a industrializacao?
  4. A remessa RPI 735679: tem chave NFe (l10n_br_chave_nf)? (refNFe so referencia chave
     ja autorizada — em draft a NF nao tem chave, entao o cross-link NF1<->NF2 so pos-SEFAZ).

READ-ONLY.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
PA_PROD = 27834       # 4870112
PA_LOT = 60542        # PILOTO-3105
LOC_SRC = 31093       # LF/PA de Terceiros
RPI_PILOTO = 735679   # remessa RPI/2026/00245
NF_MISTA = 709632
SARET = 725475


def m2o(v):
    return f"{v[0]}|{str(v[1])[:30]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    # ---- 1. estado do PA ----
    print("=" * 94)
    print("### 1. PA shoyu 4870112 em 31093 (pre-condicao do picking pt66 da NF-1)")
    q = rr('stock.quant', [('product_id', '=', PA_PROD), ('location_id', '=', LOC_SRC)],
           ['lot_id', 'quantity', 'reserved_quantity'])
    for x in q:
        livre = (x.get('quantity') or 0) - (x.get('reserved_quantity') or 0)
        print(f"   lote={m2o(x.get('lot_id'))} qty={x.get('quantity')} resv={x.get('reserved_quantity')} livre={livre}")
    ok_pa = any(isinstance(x.get('lot_id'), list) and x['lot_id'][0] == PA_LOT
                and (x.get('quantity', 0) - x.get('reserved_quantity', 0)) >= 1 for x in q)
    print(f"   >>> PA livre lote PILOTO-3105 (>=1): {'✅ OK' if ok_pa else '❌ FALTA'}")
    # pickings de retorno existentes do PA (pt66 ou saidas 31093->5)
    pk = rr('stock.picking', [('picking_type_id', '=', 66), ('origin', 'like', 'GATE')],
            ['id', 'name', 'state', 'origin'], limit=5, order='id desc')
    print(f"   pickings pt66 GATE existentes: {[(p['id'], p['state'], p['origin']) for p in pk] or 'nenhum'}")

    # ---- 2. campos de vinculo R3 ----
    print("\n" + "=" * 94)
    print("### 2. R3 — campos de vinculo em account.move (referencia_ids / invoice_origin / refNFe)")
    fg = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
    cand = sorted([f for f in fg if any(k in f.lower() for k in
                  ['referencia', 'refnfe', 'ref_nfe', 'invoice_origin', 'origin', 'reversed', 'chave'])])
    for f in cand:
        m = fg[f]
        print(f"   {f:34} {m.get('type'):10} rel={m.get('relation') or '-':32} {m.get('string','')[:26]}")
    ref_rel = fg.get('referencia_ids', {}).get('relation')
    if ref_rel:
        print(f"\n   -> modelo de referencia_ids = {ref_rel}; campos:")
        rfg = o.execute_kw(ref_rel, 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
        for f in sorted(rfg):
            if any(k in f.lower() for k in ['chave', 'nfe', 'documento', 'move', 'data', 'modelo', 'serie', 'numero']):
                print(f"        {f:30} {rfg[f].get('type'):10} rel={rfg[f].get('relation') or '-'}")

    # ---- 3. como as NFs reais preenchem o vinculo ----
    print("\n" + "=" * 94)
    print("### 3. vinculo nas NFs REAIS (mista 709632 / SARET 725475)")
    for label, nf in [('MISTA 709632', NF_MISTA), ('SARET 725475', SARET)]:
        h = rr('account.move', [('id', '=', nf)],
               ['name', 'invoice_origin', 'referencia_ids'] + ([c for c in ['l10n_br_chave_nf'] if c in fg]))
        if not h:
            print(f"   {label}: inexistente"); continue
        h = h[0]
        print(f"   {label} = {h.get('name')} | invoice_origin={h.get('invoice_origin')!r} | "
              f"referencia_ids={h.get('referencia_ids')}")
        if h.get('referencia_ids') and ref_rel:
            refs = rr(ref_rel, [('id', 'in', h['referencia_ids'])],
                      [f for f in ['l10n_br_chave_nf', 'chave', 'documento_id', 'name', 'display_name'] if f in (o.execute_kw(ref_rel,'fields_get',[],{'attributes':['type'],'context':CTX}))])
            for r in refs[:6]:
                print(f"        ref: {r}")

    # ---- 4. remessa tem chave NFe? (p/ refNFe) ----
    print("\n" + "=" * 94)
    print("### 4. remessa RPI 735679 — chave NFe (p/ refNFe das 2 NFs apontarem a remessa)")
    rem = rr('account.move', [('id', '=', RPI_PILOTO)],
             ['name', 'state'] + ([c for c in ['l10n_br_chave_nf', 'l10n_br_cstat_nf'] if c in fg]))
    if rem:
        print(f"   {rem[0].get('name')} state={rem[0].get('state')} "
              f"chave={rem[0].get('l10n_br_chave_nf')} cstat={rem[0].get('l10n_br_cstat_nf')}")


if __name__ == '__main__':
    main()
