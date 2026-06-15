#!/usr/bin/env python3
"""G9 DESCOBERTA (READ-ONLY) — qual campo liga a NF de retorno LF a entrada FB?

Lista campos candidatos a chave NF-e em account.move e mostra amostras dos 2 lados
para identificar a chave de batimento (chave de acesso 44 dig / numero NF / ref).
NAO escreve nada.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}\n")

    fg = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['string', 'type'], 'context': CTX})
    keys = [t for t in ['nota', 'nfe', 'nf_e', 'chave', 'numero', 'document', 'fiscal', 'edoc', 'serie', 'l10n_br']]
    cands = sorted(k for k, v in fg.items() if any(t in k.lower() for t in keys) and v['type'] in ('char', 'integer', 'float', 'many2one'))
    print("CAMPOS CANDIDATOS a chave NF-e em account.move:")
    for k in cands:
        print(f"  {k:42s} [{fg[k]['type']}] {fg[k]['string']}")

    rf = ['name', 'ref', 'invoice_origin', 'date', 'amount_total', 'journal_id'] + \
         [k for k in cands if fg[k]['type'] in ('char', 'integer')]
    rf = list(dict.fromkeys(rf))

    def amostra(label, acc, partner, col):
        print("\n" + "=" * 78)
        print(f"AMOSTRA {label} — conta {acc} partner {partner} ({col}>0)")
        ml = o.execute_kw('account.move.line', 'search_read',
                          [[('account_id', '=', acc), ('partner_id', '=', partner),
                            ('parent_state', '=', 'posted'), (col, '>', 0)]],
                          {'fields': ['move_id'], 'limit': 5, 'order': 'date desc', 'context': CTX})
        mids = list({l['move_id'][0] for l in ml})
        moves = o.execute_kw('account.move', 'read', [mids], {'fields': rf, 'context': CTX})
        for m in moves:
            print(f"  --- move {m['id']} ---")
            for k in rf:
                v = m.get(k)
                if v:
                    print(f"     {k:34s}: {v}")

    amostra("LF retorno (CLIENTES)", 26085, 1, 'debit')
    amostra("FB entrada (FORNECEDORES)", 11038, 35, 'credit')


if __name__ == '__main__':
    main()
