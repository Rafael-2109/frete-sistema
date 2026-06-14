#!/usr/bin/env python3
"""S16 — GATE 1c APROFUNDAMENTO (Passo 1 do plano de 13/06): entender o MECANISMO
da montagem das 5902 — como `l10n_br_operacao_id=2864` governa cfop/CST/conta, e se
isso depende (ou nao) do HEADER do account.move (journal/tipo_pedido).

READ-ONLY. Zero escrita no Odoo. Liga o Passo 1 -> Passo 2: se a linha 5902 herdar
o comportamento fiscal do HEADER (ACHADOS R2d), montar a NF-insumos SEPARADA no
RETIND 1083 (tipo_pedido vazio) pode computar DIFERENTE da NF mista do GATE 1c (j847).

MODOS (sem args = roda todos):
  --op            op 2864 (5902 retorno) vs 2702 (5124 PA): campos non-falsy + diff
  --nf NF_ID      linhas 5124/5902 de NF real (default 738097): campos fiscais resultantes
  --header        compara o HEADER da NF mista real (738097) vs o journal RETIND 1083
"""
import sys
import argparse
from collections import Counter
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
OP_5902 = 2864   # Retorno de Industrializacao (a da NF mista) — CFOP 5902
OP_5124 = 2702   # operacao do PA (linha de servico 5124)
NF_REAL = 738097  # VND mista real (Josefa montou as 9x5902 a mao)
J_RETIND = 1083   # journal de destino da NF-insumos separada (config 13/06)
J847 = 847        # journal da NF mista (venda-producao)


def _non_falsy(d):
    return {k: v for k, v in sorted(d.items()) if v not in (False, None, '', 0, 0.0, [], ())}


def dump_op(o):
    print("=" * 78)
    print("=== OPERACOES FISCAIS — 2864 (5902 retorno) vs 2702 (5124 PA) ===")
    rows = o.execute_kw('l10n_br_ciel_it_account.operacao', 'read',
                        [[OP_5902, OP_5124]], {'context': CTX})
    by_id = {r['id']: r for r in rows}
    a, b = by_id.get(OP_5902, {}), by_id.get(OP_5124, {})
    na, nb = _non_falsy(a), _non_falsy(b)
    print(f"\n--- op {OP_5902} (5902) non-falsy ({len(na)} campos) ---")
    for k, v in na.items():
        print(f"  {k} = {v}")
    print(f"\n--- DIFF op {OP_5902} (5902) vs op {OP_5124} (5124/PA) ---")
    keys = sorted(set(na) | set(nb))
    for k in keys:
        va, vb = a.get(k, '∅'), b.get(k, '∅')
        if va != vb:
            print(f"  {k}: [5902]={va!r}  |  [5124]={vb!r}")


def dump_nf(o, nf):
    print("\n" + "=" * 78)
    print(f"=== NF REAL {nf} — linhas fiscais resultantes (o que a op preencheu) ===")
    pf = o.execute_kw('account.move.line', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
    want = ['product_id', 'l10n_br_operacao_id', 'l10n_br_cfop_codigo', 'l10n_br_cfop_id',
            'l10n_br_icms_cst', 'l10n_br_tipo_pedido', 'account_id', 'quantity', 'price_unit',
            'price_subtotal', 'display_type', 'l10n_br_calcular_imposto']
    fields = [f for f in want if f in pf]
    lines = o.execute_kw('account.move.line', 'search_read',
                         [[('move_id', '=', nf), ('display_type', '=', 'product')]],
                         {'fields': fields, 'context': CTX, 'order': 'id'})
    for ln in lines:
        cfop = ln.get('l10n_br_cfop_codigo')
        op = ln.get('l10n_br_operacao_id')
        acc = ln.get('account_id')
        tp = ln.get('l10n_br_tipo_pedido')
        print(f"  prod={str(ln.get('product_id'))[:42]:42} cfop={cfop} cst={ln.get('l10n_br_icms_cst')} "
              f"op={op[0] if op else None} conta={acc[1][:20] if acc else None} tipo_ped={tp} "
              f"qty={ln.get('quantity')} pu={ln.get('price_unit')}")
    cfops = Counter(str(l.get('l10n_br_cfop_codigo')) for l in lines)
    csts = Counter(str(l.get('l10n_br_icms_cst')) for l in lines)
    tps = Counter(str(l.get('l10n_br_tipo_pedido')) for l in lines)
    print(f"\n  RESUMO: {len(lines)} linhas | CFOPs={dict(cfops)} CST={dict(csts)} tipo_pedido(linha)={dict(tps)}")


def dump_header(o):
    print("\n" + "=" * 78)
    print("=== HEADER: NF mista real 738097 vs journals j847 (mista) e RETIND 1083 ===")
    mf = o.execute_kw('account.move', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
    mwant = ['name', 'journal_id', 'l10n_br_tipo_pedido', 'l10n_br_operacao_id',
             'move_type', 'company_id', 'invoice_origin', 'partner_id',
             'l10n_br_fiscal_position_id', 'fiscal_position_id', 'l10n_br_cfop_id',
             'amount_total', 'amount_untaxed', 'l10n_br_referencia_ids', 'invoice_line_ids']
    mfields = [f for f in mwant if f in mf]
    mv = o.execute_kw('account.move', 'read', [[NF_REAL]], {'fields': mfields, 'context': CTX})
    print(f"\n--- account.move {NF_REAL} (HEADER) ---")
    for k, v in _non_falsy(mv[0]).items():
        print(f"  {k} = {v}")

    jf = o.execute_kw('account.journal', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
    jwant = ['name', 'code', 'type', 'l10n_br_tipo_pedido', 'l10n_br_no_payment',
             'account_no_payment_id', 'l10n_br_operacao_id']
    jfields = [f for f in jwant if f in jf]
    js = o.execute_kw('account.journal', 'read', [[J847, J_RETIND]], {'fields': jfields, 'context': CTX})
    for j in js:
        print(f"\n--- journal {j['id']} ({j.get('code')}) ---")
        for k, v in _non_falsy(j).items():
            print(f"  {k} = {v}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--op', action='store_true')
    ap.add_argument('--nf', type=int, nargs='?', const=NF_REAL, metavar='NF_ID')
    ap.add_argument('--header', action='store_true')
    args = ap.parse_args()
    todos = not (args.op or args.nf or args.header)

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"

    if todos or args.op:
        dump_op(o)
    if todos or args.nf:
        dump_nf(o, args.nf if args.nf else NF_REAL)
    if todos or args.header:
        dump_header(o)


if __name__ == '__main__':
    main()
