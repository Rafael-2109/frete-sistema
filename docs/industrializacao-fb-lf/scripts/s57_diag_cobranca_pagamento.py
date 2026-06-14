#!/usr/bin/env python3
"""S57 — DIAGNOSTICO (READ-only) do gap que rejeitou a NF-1: "Dados de cobranca nao devem
ser informados para pagamento a vista". A NF-1 (791437) saiu marcada a vista MAS com dados
de cobranca (duplicata). A NF real 709632 usa o MESMO payment_provider 31 e foi autorizada.
Acha a diferenca: condicao de pagamento / indicador / linhas de duplicata (display_type=payment_term).

Compara NF-1 (791437) vs REAL 709632 (autorizada) vs NF-2 (791441).
READ-ONLY.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1, NF2, REAL = 791437, 791441, 709632


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX})

    fg = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['string', 'type'], 'context': CTX})
    pagcands = sorted([f for f in fg if any(k in f.lower() for k in
                       ['indpag', 'ind_pag', 'forma_pag', 'forma_de_pag', 'meio_pag', 'fin_', 'cobr',
                        'duplicata', 'payment_term', 'pag_', 'a_vista', 'avista', 'prazo'])
                       and fg[f].get('type') not in ('one2many', 'many2many')])
    hdr = ['name', 'invoice_payment_term_id', 'invoice_date', 'invoice_date_due',
           'payment_provider_id', 'l10n_br_situacao_nf'] + pagcands
    hdr = [f for f in dict.fromkeys(hdr) if f in fg]

    print("=" * 100)
    print("### 1. CAMPOS de pagamento/cobranca — NF-1 vs REAL vs NF-2")
    print("=" * 100)
    rows = {r['id']: r for r in rd('account.move', [NF1, REAL, NF2], hdr)}
    for label, mid in [('NF-1 (rejeitada)', NF1), ('REAL (autorizada)', REAL), ('NF-2 (rascunho)', NF2)]:
        r = rows.get(mid, {})
        print(f"\n  {label} {mid} {r.get('name')}:")
        print(f"    invoice_payment_term_id = {r.get('invoice_payment_term_id')}")
        print(f"    invoice_date_due        = {r.get('invoice_date_due')}  (invoice_date={r.get('invoice_date')})")
        for f in pagcands:
            v = r.get(f)
            if v not in (False, None, '', 0, 0.0):
                print(f"    {f:32} = {v}")

    # ---- 2. linhas de duplicata/cobranca (display_type=payment_term) ----
    print("\n" + "=" * 100)
    print("### 2. LINHAS de duplicata/cobranca (display_type='payment_term') — o 'dados de cobranca' do XML")
    print("=" * 100)
    for label, mid in [('NF-1 (rejeitada)', NF1), ('REAL (autorizada)', REAL), ('NF-2 (rascunho)', NF2)]:
        lns = rr('account.move.line', [('move_id', '=', mid), ('display_type', '=', 'payment_term')],
                 ['name', 'date_maturity', 'debit', 'credit', 'account_id'])
        print(f"\n  {label} {mid}: {len(lns)} linha(s) payment_term")
        for l in lns:
            print(f"    venc={l.get('date_maturity')} D={l.get('debit')} C={l.get('credit')} conta={l.get('account_id')}")

    # ---- 3. condicao de pagamento: detalhe ----
    print("\n" + "=" * 100)
    print("### 3. CONDICAO DE PAGAMENTO (account.payment.term) usada por cada")
    print("=" * 100)
    terms = {}
    for mid in [NF1, REAL]:
        pt = rows.get(mid, {}).get('invoice_payment_term_id')
        if isinstance(pt, list):
            terms[mid] = pt
    ptids = list({pt[0] for pt in terms.values()})
    if ptids:
        ptdata = {p['id']: p for p in rd('account.payment.term', ptids, ['name', 'l10n_br_indpag', 'note'])
                  } if 'l10n_br_indpag' in o.execute_kw('account.payment.term', 'fields_get', [], {'attributes': [], 'context': CTX}) \
            else {p['id']: p for p in rd('account.payment.term', ptids, ['name'])}
        for mid, pt in terms.items():
            d = ptdata.get(pt[0], {})
            print(f"  {('NF-1' if mid == NF1 else 'REAL')} term {pt}: {d}")
    print(f"\n  >>> se a NF-1 tem term a-prazo / linha payment_term com vencimento != invoice_date enquanto a")
    print(f"      REAL e' a-vista (1 linha venc=invoice_date) -> ajustar a condicao de pagamento da NF-1.")


if __name__ == '__main__':
    main()
