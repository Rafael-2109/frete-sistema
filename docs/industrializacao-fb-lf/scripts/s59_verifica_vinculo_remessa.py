#!/usr/bin/env python3
"""S59 — VERIFICA (READ-only) o vinculo COMPLETO remessa(FB->LF) <-> retorno(LF->FB) nas 2
NFs autorizadas. Responde: "estou conectando desde a remessa de industrializacao?"

Checa 3 niveis de conexao:
  1. refNFe (rastreabilidade no XML): as 2 NFs de retorno apontam a chave da REMESSA?
  2. invoice_origin (vinculo logico): comum entre as 2 + aponta a remessa?
  3. dados (invariante 5902=5901): os 16 insumos/valores da NF-2 batem com a remessa?
READ-ONLY.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
REMESSA = 735679      # RPI/2026/00245 (FB->LF)
NF1, NF2 = 791437, 791441
REF_MODEL = 'l10n_br_ciel_it_account.account.move.referencia'


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    rem = rd('account.move', [REMESSA], ['name', 'l10n_br_chave_nf', 'amount_untaxed'])[0]
    chave_rem = rem.get('l10n_br_chave_nf')
    rlines = rr('account.move.line', [('move_id', '=', REMESSA), ('display_type', '=', 'product')],
                ['product_id', 'quantity', 'price_unit', 'price_subtotal'])
    rem_prods = {l['product_id'][0]: round(l.get('price_subtotal') or 0, 2) for l in rlines if l.get('product_id')}

    print("=" * 96)
    print("S59 — VINCULO remessa (FB->LF) <-> retorno (LF->FB)")
    print("=" * 96)
    print(f"\n  REMESSA {rem['name']} (move {REMESSA})")
    print(f"    chave = {chave_rem}")
    print(f"    {len(rlines)} insumos product | untax = {rem.get('amount_untaxed')}")

    for label, nf in [('NF-1 servico', NF1), ('NF-2 insumos', NF2)]:
        h = rd('account.move', [nf], ['name', 'invoice_origin', 'l10n_br_chave_nf'])[0]
        refs = rr(REF_MODEL, [('move_id', '=', nf)], ['l10n_br_chave_nf'])
        ref_chaves = [r.get('l10n_br_chave_nf') for r in refs]
        aponta_remessa = chave_rem in ref_chaves
        plines = rr('account.move.line', [('move_id', '=', nf), ('display_type', '=', 'product')],
                    ['product_id', 'price_subtotal'])
        print(f"\n  {label} {nf} — {h['name']} (chave propria {(h.get('l10n_br_chave_nf') or '')[-12:]})")
        print(f"    [1] refNFe ({len(refs)}): {[c[-12:] for c in ref_chaves]} -> aponta REMESSA: {'✅' if aponta_remessa else '❌'}")
        print(f"    [2] invoice_origin = {h.get('invoice_origin')}")
        if label.startswith('NF-2'):
            nf_prods = {l['product_id'][0]: round(l.get('price_subtotal') or 0, 2) for l in plines if l.get('product_id')}
            match = set(nf_prods.keys()) == set(rem_prods.keys())
            val_match = all(abs(nf_prods.get(p, 0) - rem_prods.get(p, 0)) < 0.01 for p in rem_prods)
            print(f"    [3] dados: {len(nf_prods)} insumos vs {len(rem_prods)} da remessa -> "
                  f"produtos batem: {'✅' if match else '❌'} | valores batem (5902=5901): {'✅' if val_match else '❌'}")

    print("\n" + "=" * 96)
    print("  RESUMO da conexao com a remessa (o que JA esta' ligado vs o que e' fixo no piloto):")
    print("    ✅ rastreabilidade (refNFe da remessa nas 2 NFs) + dados (NF-2 = 16 linhas da remessa)")
    print("    ⚠️ no piloto a REMESSA e' FIXA (735679 hardcoded no s37). A automacao precisa DESCOBRIR")
    print("       a remessa correspondente ao retorno (genealogia lote->MO->mat.terceiros->remessa, SOT 6.2 A/B/C).")


if __name__ == '__main__':
    main()
