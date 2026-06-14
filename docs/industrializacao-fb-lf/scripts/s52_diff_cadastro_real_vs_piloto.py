#!/usr/bin/env python3
"""S52 — DIFF DE CADASTRO (READ-only): compara a NF REAL de retorno de industrializacao
709632 (AUTORIZADA na SEFAZ) vs as minhas NF-1 (791437) e NF-2 (791441) p/ achar TODOS os
gaps de header de uma vez (em vez de descobrir um a um pelo preview do XML).

O preview server-side ja' revelou 2 gaps em sequencia (incoterm -> meio de pagamento). Este
diff lista os campos de CADASTRO (selection/m2o/char/bool/date) onde a real tem valor e a
minha esta' vazia/diferente — foco em pagamento/fiscal/parcela.

READ-ONLY.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
REAL = 709632          # NF mista real de retorno (5124+16x5902), AUTORIZADA
NF1, NF2 = 791437, 791441
SIMPLE = ('selection', 'many2one', 'char', 'boolean', 'date', 'datetime', 'integer')
PAGKEYS = ['pag', 'forma', 'meio', 'parcela', 'fatura', 'cobranca', 'cobrança', 'financ',
           'duplicata', 'payment', 'term', 'fin_', 'tpag', 'fp_']


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rd(ids, fields):
        return o.execute_kw('account.move', 'read', [list(ids)], {'fields': fields, 'context': CTX})

    fg = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['string', 'type'], 'context': CTX})
    simples = [f for f in fg if fg[f].get('type') in SIMPLE]

    def norm(v):
        return v[0] if isinstance(v, list) and v else v

    r = rd([REAL], simples)[0]
    n1 = rd([NF1], simples)[0]
    n2 = rd([NF2], simples)[0]

    def diff(real, minha, label):
        out = []
        for f in simples:
            rv, mv = real.get(f), minha.get(f)
            if rv in (False, None, '', 0, 0.0):
                continue          # real vazio: nao e' um gap
            if norm(rv) != norm(mv):
                out.append((f, rv, mv))
        return out

    print("=" * 100)
    print(f"### DIFF NF-1 (servico {NF1}) vs REAL {REAL} — campos onde a real tem valor e a minha difere")
    print("=" * 100)
    d1 = diff(r, n1, 'NF-1')
    pag1 = [x for x in d1 if any(k in x[0].lower() or k in (fg[x[0]].get('string') or '').lower() for k in PAGKEYS)]
    print(f"  >> RELACIONADOS A PAGAMENTO/PARCELA ({len(pag1)}):")
    for f, rv, mv in pag1:
        print(f"     {f:34} {fg[f].get('string')!r:30} real={rv}  minha={mv}")
    print(f"\n  >> OUTROS gaps de cadastro (minha VAZIA, real tem) — l10n_br/fiscal:")
    for f, rv, mv in d1:
        if (f, rv, mv) in pag1:
            continue
        if mv in (False, None, '', 0, 0.0) and ('l10n_br' in f or 'fiscal' in f.lower() or 'incoterm' in f):
            print(f"     {f:34} {fg[f].get('string')!r:30} real={rv}  minha=VAZIO")

    print("\n" + "=" * 100)
    print(f"### NF-2 (insumos {NF2}) — pagamento/parcela vs REAL")
    print("=" * 100)
    d2 = diff(r, n2, 'NF-2')
    pag2 = [x for x in d2 if any(k in x[0].lower() or k in (fg[x[0]].get('string') or '').lower() for k in PAGKEYS)]
    for f, rv, mv in pag2:
        print(f"     {f:34} {fg[f].get('string')!r:30} real={rv}  minha={mv}")

    # parcelas/pagamento podem estar em one2many — listar os o2m candidatos
    print("\n" + "=" * 100)
    print("### one2many candidatos a PARCELA/PAGAMENTO (estrutura pode estar em linhas)")
    print("=" * 100)
    o2m = [f for f in fg if fg[f].get('type') == 'one2many'
           and any(k in f.lower() or k in (fg[f].get('string') or '').lower() for k in PAGKEYS)]
    for f in o2m:
        rv = rd([REAL], [f])[0].get(f)
        m1 = rd([NF1], [f])[0].get(f)
        m2 = rd([NF2], [f])[0].get(f)
        print(f"     {f:34} {fg[f].get('string')!r:28} real={len(rv or [])} NF1={len(m1 or [])} NF2={len(m2 or [])} (n linhas)")


if __name__ == '__main__':
    main()
