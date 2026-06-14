#!/usr/bin/env python3
"""S50 — DIAGNOSTICO READ-only: modalidade de frete (modFrete) ausente na NF-1/NF-2 do piloto.
O action_previsualizar_xml_nfe (preview) abortou: "Modalidade de frete nao configurada".
Descobre o CAMPO exato + o VALOR usado nas NFs REAIS de retorno de industrializacao (nao
inventar) p/ aplicar o mesmo nas 2 NFs do piloto antes de transmitir.

Le: (1) campos de account.move com frete/modalidade/freight/transp + opcoes do selection;
    (2) valor nas 3 NFs reais de retorno (709632/708286/574827) + VND recentes do j847;
    (3) valor atual nas minhas NF-1 (791437) / NF-2 (791441).
READ-ONLY.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
NF1, NF2 = 791437, 791441
REAIS = [709632, 708286, 574827]   # NFs reais de retorno de industrializacao (16x5902)
J847 = 847


def main():
    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, dom, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [dom], kw2)

    fg = o.execute_kw('account.move', 'fields_get', [],
                      {'attributes': ['string', 'type', 'selection', 'required'], 'context': CTX})

    def is_modfrete(f):
        meta = fg[f]
        lbl = (meta.get('string') or '').lower()
        nm = f.lower()
        # por label (PT) ou nome
        if any(k in lbl for k in ['modalidade', 'modalidad', 'mod. frete', 'frete por']):
            return True
        if any(k in nm for k in ['mod_frete', 'modfrete', 'ind_frete', 'modalidade', 'freight_mod']):
            return True
        # por opcoes do selection (chaves 0/1/2/3/4/9 do modFrete NFe)
        sel = meta.get('selection')
        if isinstance(sel, list) and sel:
            keys = {str(k) for k, _ in sel}
            if keys <= {'0', '1', '2', '3', '4', '9'} and ('9' in keys or '0' in keys) and len(keys) >= 2:
                return True
        return False

    cands = sorted([f for f in fg if any(k in f.lower() for k in
                    ['frete', 'modalidade', 'mod_frete', 'modfrete', 'freight', 'transp', 'incoterm'])
                    or is_modfrete(f)])

    print("=" * 92)
    print("### 1. CAMPOS candidatos (modalidade de frete / incoterm) em account.move")
    print("=" * 92)
    for f in cands:
        meta = fg[f]
        sel = meta.get('selection')
        print(f"  {f:34} type={meta.get('type'):10} req={meta.get('required')} string={meta.get('string')!r}")
        if sel:
            print(f"      opcoes: {sel}")
    frete_field = next((f for f in cands if is_modfrete(f)), None)
    print(f"\n  >>> campo modFrete provavel = {frete_field}")

    read_fields = list(cands) + ['name', 'l10n_br_tipo_pedido']
    read_fields = [f for f in read_fields if f in fg]

    # ---- 2. NFs reais de retorno + VND recentes do j847 ----
    print("\n" + "=" * 92)
    print("### 2. VALOR nas NFs REAIS de retorno de industrializacao + VND recentes (j847)")
    print("=" * 92)
    reais = rr('account.move', [('id', 'in', REAIS)], read_fields)
    for r in reais:
        vals = {f: r.get(f) for f in cands if r.get(f) not in (False, None, '')}
        print(f"  REAL {r['id']} {r.get('name')}: {vals}")
    vnd = rr('account.move', [('journal_id', '=', J847), ('state', '=', 'posted'),
                              ('l10n_br_situacao_nf', '=', 'autorizado')], read_fields, limit=5, order='id desc')
    print(f"\n  VND recentes autorizadas (j847):")
    for r in vnd:
        vals = {f: r.get(f) for f in cands if r.get(f) not in (False, None, '')}
        print(f"  VND {r['id']} {r.get('name')}: {vals}")

    # ---- 3. minhas NFs ----
    print("\n" + "=" * 92)
    print("### 3. VALOR atual nas minhas NF-1 / NF-2 (o gap)")
    print("=" * 92)
    minhas = rr('account.move', [('id', 'in', [NF1, NF2])], read_fields)
    for r in minhas:
        vals = {f: r.get(f) for f in cands}
        print(f"  NF {r['id']} {r.get('name')}: { {k: v for k, v in vals.items() if k == frete_field} }  (todos: {vals})")
    print(f"\n  >>> aplicar nas 2 NFs o MESMO valor das reais (campo {frete_field}).")


if __name__ == '__main__':
    main()
