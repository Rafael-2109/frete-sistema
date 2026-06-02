#!/usr/bin/env python3
"""G4 — o CIEL IT SEPARA a NF automaticamente por journal/tipo_pedido?

Hipotese (pista Rafael, operacao carrega l10n_br_tipo_pedido → journal): se as
linhas de uma mesma ORIGEM (SO/picking) tiverem tipo_pedido → journals diferentes,
o sistema gera N account.move (1 por journal). Se SIM, basta dar a op 5902 um
tipo_pedido proprio (→ journal c/ no_payment=PASSIVA) p/ o retorno de insumos sair
em NF separada AUTOMATICAMENTE — sem mexer na Skill 8.

VERIFICA (READ-only):
  1. agrupa account.move (LF sale, recentes) por invoice_origin → conta journals distintos.
     origens com >1 journal = evidencia de separacao automatica.
  2. amostra os tipo_pedido das operacoes nas linhas de uma origem multi-journal.
NAO escreve nada.
"""
import sys
from collections import defaultdict
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    # 1) account.move LF sale recentes com origem
    moves = rr('account.move', [('company_id', '=', 5), ('move_type', '=', 'out_invoice'),
                                ('state', '=', 'posted'), ('date', '>=', '2026-01-01'),
                                ('invoice_origin', '!=', False)],
               ['id', 'name', 'invoice_origin', 'journal_id'], limit=3000)
    print(f"  {len(moves)} NFs LF(sale,posted,2026) com invoice_origin")
    by_origin = defaultdict(set)        # origin -> {journal_id}
    by_origin_moves = defaultdict(list)
    for mv in moves:
        j = mv['journal_id'][0] if isinstance(mv.get('journal_id'), list) else None
        by_origin[mv['invoice_origin']].add(j)
        by_origin_moves[mv['invoice_origin']].append(mv)
    multi = {o_: js for o_, js in by_origin.items() if len(js) > 1}
    print(f"  origens com >1 JOURNAL distinto (= separacao automatica por journal): {len(multi)}")
    for o_, js in list(multi.items())[:10]:
        jnames = rr('account.journal', [('id', 'in', list(js))], ['id', 'name', 'l10n_br_tipo_pedido'])
        print(f"\n  origin={o_}: journals={[ (j['id'], j['name'], j.get('l10n_br_tipo_pedido')) for j in jnames ]}")
        for mv in by_origin_moves[o_]:
            print(f"      move {mv['id']} {mv['name']} journal={m2o(mv['journal_id'])}")

    # 2) tambem checar: existe NF LF de retorno SO de insumos (5902) sem servico (5124)?
    print("\n" + "=" * 80)
    print("  Existe NF LF (out) com 5902 SEM 5124? (= retorno de insumos ja separado hoje)")
    print("=" * 80)
    OPS_5902 = [2864, 2710]
    OPS_5124 = [2702, 3039]
    # moves com 5902
    ml5902 = rr('account.move.line', [('company_id', '=', 5), ('l10n_br_operacao_id', 'in', OPS_5902),
                                      ('parent_state', '=', 'posted'), ('move_id.move_type', '=', 'out_invoice')],
               ['move_id'], limit=2000)
    mids_5902 = {l['move_id'][0] for l in ml5902 if isinstance(l.get('move_id'), list)}
    # desses, quais tem 5124?
    ml5124 = rr('account.move.line', [('move_id', 'in', list(mids_5902)), ('l10n_br_operacao_id', 'in', OPS_5124)],
               ['move_id'], limit=4000)
    mids_com5124 = {l['move_id'][0] for l in ml5124 if isinstance(l.get('move_id'), list)}
    so_5902 = mids_5902 - mids_com5124
    print(f"  NFs com 5902: {len(mids_5902)}; dessas, COM 5124(misto): {len(mids_com5124)}; SO 5902(separado): {len(so_5902)}")
    if so_5902:
        amostra = rr('account.move', [('id', 'in', list(so_5902))],
                     ['id', 'name', 'journal_id', 'amount_total'], limit=8)
        print("  amostra NFs SO-5902 (retorno de insumos ja separado):")
        for mv in amostra:
            print(f"    move {mv['id']} {mv['name']} journal={m2o(mv['journal_id'])} total={mv.get('amount_total')}")

    print("\n[FIM — READ-only, nada escrito]")


if __name__ == '__main__':
    main()
