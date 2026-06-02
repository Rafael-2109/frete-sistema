#!/usr/bin/env python3
"""G4/G5a GROUNDING 3 (READ-ONLY) — header tipo_pedido (decide o journal da NF).

Decide a ambiguidade central: o journal e' do CABECALHO (1 por NF). Qual
l10n_br_tipo_pedido(_entrada) o header da NF de retorno tera? Isso decide se a
NF cai no journal novo (G4) e se precisa criar tipo.pedido.diario(FB, serv-ind).

1) header da ENTSI/2026/05/0126 (move 727672): tipo_pedido_entrada real.
2) account.journal: campos l10n_br (journal carrega tipo_pedido?).
3) NF de SAIDA LF MISTA de retorno real (5124+5902 juntas) -> header + journal.
NAO escreve nada.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    if isinstance(v, list) and v:
        return f"{v[0]}|{v[1]}"
    return '-' if v is False or v is None else str(v)


def cf(v):
    return v[1].split(' - ')[0] if isinstance(v, list) and v else '-'


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        kwargs = {'fields': fields, 'context': CTX}
        kwargs.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kwargs)

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX})

    # ========================================================================
    print("\n" + "=" * 90)
    print("1 — HEADER da ENTSI/2026/05/0126 (move 727672) — quais campos l10n_br_tipo_*")
    print("=" * 90)
    mvfields = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['string', 'type'], 'context': CTX})
    tipo_fields = [k for k in mvfields if 'tipo_pedido' in k.lower() or k in ('l10n_br_operacao_id',)]
    hdr = rd('account.move', [727672], ['id', 'name', 'journal_id', 'move_type', 'l10n_br_operacao_id'] + tipo_fields)
    if hdr:
        h = hdr[0]
        print(f"  move {h['id']} {h['name']} journal={m2o(h.get('journal_id'))} type={h.get('move_type')}")
        for f in ['l10n_br_operacao_id'] + tipo_fields:
            print(f"    {f} = {m2o(h.get(f)) if isinstance(h.get(f), list) else h.get(f)}")

    # ========================================================================
    print("\n" + "=" * 90)
    print("2 — account.journal: campos l10n_br (journal carrega tipo_pedido proprio?)")
    print("=" * 90)
    jfields = o.execute_kw('account.journal', 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
    jl10n = {k: v for k, v in jfields.items() if k.startswith('l10n_br') or 'tipo' in k.lower()}
    print(f"  {len(jl10n)} campos l10n_br/tipo em account.journal:")
    j1001 = rd('account.journal', [1001], list(jl10n.keys()) + ['id'])
    for k in sorted(jl10n.keys()):
        val = j1001[0].get(k) if j1001 else None
        print(f"    {k:42} {jl10n[k].get('type'):10} j1001={m2o(val) if isinstance(val, list) else val}")

    # ========================================================================
    print("\n" + "=" * 90)
    print("3 — NF de SAIDA LF MISTA de retorno (linhas 5124 + 5902 na mesma NF)")
    print("=" * 90)
    # operacoes LF de retorno: 2702/3039 (5124), 2710/2864 (5902), 2711 (5903)
    ops_ret = [2702, 3039, 2710, 2864, 2711]
    # buscar linhas dessas operacoes em moves company 5 (out), agrupar por move
    lines = rr('account.move.line',
               [('l10n_br_operacao_id', 'in', ops_ret), ('company_id', '=', 5),
                ('parent_state', '=', 'posted'), ('move_id.move_type', '=', 'out_invoice')],
               ['id', 'move_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id'], limit=400)
    from collections import defaultdict
    by_move = defaultdict(set)
    for ln in lines:
        by_move[ln['move_id'][0]].add(cf(ln.get('l10n_br_cfop_id')))
    # mistas = move com >=2 CFOPs distintos entre {5124,5902,5903}
    mistas = {mid: cfs for mid, cfs in by_move.items() if len(cfs & {'5124', '5902', '5903'}) >= 2}
    print(f"  moves LF(out,posted) com op de retorno: {len(by_move)}; MISTAS (>=2 CFOPs): {len(mistas)}")
    alvo_ids = sorted(mistas.keys(), reverse=True)[:4] or sorted(by_move.keys(), reverse=True)[:4]
    hdr_tipo_fields = [k for k in mvfields if 'tipo_pedido' in k.lower()]
    moves = rd('account.move', alvo_ids,
               ['id', 'name', 'state', 'journal_id', 'amount_total', 'l10n_br_operacao_id'] + hdr_tipo_fields) if alvo_ids else []
    for mv in sorted(moves, key=lambda x: -x['id']):
        cfs = by_move.get(mv['id'], set())
        print(f"\n  move {mv['id']} {mv['name']} journal={m2o(mv['journal_id'])} total={mv.get('amount_total')} CFOPs={sorted(cfs)}")
        print(f"    header_operacao={m2o(mv.get('l10n_br_operacao_id'))}")
        for f in hdr_tipo_fields:
            v = mv.get(f)
            if v:
                print(f"    header_{f} = {v}")
        mls = rr('account.move.line', [('move_id', '=', mv['id'])],
                 ['id', 'account_id', 'l10n_br_operacao_id', 'l10n_br_cfop_id', 'debit', 'credit', 'display_type'], limit=30)
        for ln in mls:
            if ln.get('display_type') in ('line_section', 'line_note'):
                continue
            print(f"      L{ln['id']} acc={m2o(ln.get('account_id'))[:40]:40} op={m2o(ln.get('l10n_br_operacao_id'))[:24]:24} "
                  f"cfop={cf(ln.get('l10n_br_cfop_id')):6} D={ln.get('debit')} C={ln.get('credit')}")

    print("\n[FIM GROUNDING 3 READ-ONLY — nada foi escrito]")


if __name__ == '__main__':
    main()
