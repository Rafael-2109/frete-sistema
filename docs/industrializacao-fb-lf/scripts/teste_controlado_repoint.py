#!/usr/bin/env python3
"""
BLOQUEADOR 1 — Teste controlado do repoint de contas de categoria na LF.

Valida EMPIRICAMENTE que repointar as contas da categoria (contexto LF) faz a
movimentacao lancar NET-ZERO em terceiros:
    entrada (+):  D 1150200001 MATERIAL EM TERCEIROS / C 1150200002 (-) MAT. TERCEIROS
    saida   (-):  D 1150200002 (-) MAT. TERCEIROS    / C 1150200001 MATERIAL EM TERCEIROS

Escopo do teste = ACCOUNTING WIRING do repoint (nao o fluxo fiscal das 5 etapas).
Proxy de movimento = ajuste de inventario +DELTA depois -DELTA (self-canceling,
restaura o saldo exato). Cobaia default: categ 104 / produto 4870110 (n_prod=1 LF).

SEGURANCA:
  - --dry-run e' o DEFAULT: NAO escreve nada (so' mostra snapshot + plano + esperado).
  - --execute faz o teste real e usa try/finally para SEMPRE restaurar a categoria
    (ir.property) e o saldo do quant, mesmo em erro.
  - Toda escrita de ir.property usa contexto allowed_company_ids=[5] (LF).

Uso:
    source .venv/bin/activate
    python docs/industrializacao-fb-lf/scripts/teste_controlado_repoint.py            # dry-run
    python docs/industrializacao-fb-lf/scripts/teste_controlado_repoint.py --execute  # real (com go)
"""
import argparse
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_LF = 5
COBAIA_CAT = 104          # PRODUTO ACABADO / MOLHOS / LIQUIDOS
COBAIA_PROD = 32299       # 4870110 MOLHO SHOYU - GL 3X5,02 L (product.product)
ACC_TERC_VAL = 26140      # 1150200001 MATERIAL EM TERCEIROS (LF)
ACC_TERC_CP = 26141       # 1150200002 (-) MATERIAL DE TERCEIROS (LF)

REPOINT_FIELDS = {
    'property_stock_valuation_account_id': ACC_TERC_VAL,
    'property_stock_account_input_categ_id': ACC_TERC_CP,
    'property_stock_account_output_categ_id': ACC_TERC_CP,
    # production_cost_id: NAO mexer no teste (decisao Contador) -> mantem 1150100004
}
SNAP_FIELDS = list(REPOINT_FIELDS) + ['property_stock_account_production_cost_id',
                                      'property_valuation', 'property_cost_method', 'complete_name']

DRY = True


def ctx():
    return {'allowed_company_ids': [CMP_LF], 'company_id': CMP_LF}


def read_ip(odoo, cat):
    return odoo.execute_kw('product.category', 'read', [[cat], SNAP_FIELDS], {'context': ctx()})[0]


def fmt_acc(v):
    return f"{v[1]} (id={v[0]})" if isinstance(v, list) and v else str(v)


def latest_svl(odoo, prod):
    rows = odoo.execute_kw('stock.valuation.layer', 'search_read',
                           [[('product_id', '=', prod), ('company_id', '=', CMP_LF)]],
                           {'fields': ['id', 'value', 'quantity', 'account_move_id', 'stock_move_id', 'create_date'],
                            'order': 'id desc', 'limit': 1})
    return rows[0] if rows else None


def read_move_lines(odoo, move_id):
    mls = odoo.execute_kw('account.move.line', 'search_read',
                          [[('move_id', '=', move_id)]],
                          {'fields': ['account_id', 'debit', 'credit', 'name']})
    out = []
    for ml in mls:
        acc = ml['account_id'][1] if ml['account_id'] else '?'
        out.append((ml['account_id'][0] if ml['account_id'] else None, acc, ml['debit'], ml['credit']))
    return out


def assert_pattern(lines, debit_acc, credit_acc):
    d = any(aid == debit_acc and deb > 0 for aid, _, deb, _ in lines)
    c = any(aid == credit_acc and cre > 0 for aid, _, _, cre in lines)
    return d and c


def pick_quant(odoo, prod):
    qs = odoo.execute_kw('stock.quant', 'search_read',
                         [[('product_id', '=', prod), ('company_id', '=', CMP_LF),
                           ('location_id.usage', '=', 'internal')]],
                         {'fields': ['id', 'location_id', 'quantity', 'inventory_quantity'],
                          'order': 'quantity desc', 'limit': 1})
    return qs[0] if qs else None


def apply_adjust(odoo, quant_id, new_qty):
    """Seta inventory_quantity e aplica. Retorna apos (gotcha None=sucesso)."""
    odoo.execute_kw('stock.quant', 'write', [[quant_id], {'inventory_quantity': new_qty}], {'context': ctx()})
    try:
        odoo.execute_kw('stock.quant', 'action_apply_inventory', [[quant_id]], {'context': ctx()})
    except Exception as e:
        if 'cannot marshal None' not in str(e):
            raise


def main():
    global DRY
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true', help='executa de verdade (default dry-run)')
    ap.add_argument('--delta', type=float, default=1.0, help='unidades do ajuste +/- (default 1)')
    ap.add_argument('--cat', type=int, default=COBAIA_CAT)
    ap.add_argument('--prod', type=int, default=COBAIA_PROD)
    args = ap.parse_args()
    DRY = not args.execute
    cat, prod, delta = args.cat, args.prod, args.delta

    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise SystemExit("Falha auth Odoo")

    print("=" * 96)
    print(f"TESTE CONTROLADO REPOINT — {'DRY-RUN (nada sera escrito)' if DRY else 'EXECUTE (real)'}")
    print(f"  cobaia categoria={cat}  produto={prod}  delta=+/-{delta}")
    print("=" * 96)

    # 1) SNAPSHOT
    snap = read_ip(odoo, cat)
    print(f"\n[1] SNAPSHOT categoria {cat} | {snap.get('complete_name')}")
    print(f"    valuation={snap.get('property_valuation')}/{snap.get('property_cost_method')}")
    for f in SNAP_FIELDS[:4]:
        print(f"    {f:46s} = {fmt_acc(snap.get(f))}")
    quant = pick_quant(odoo, prod)
    if not quant:
        raise SystemExit(f"Produto {prod} sem quant interno na LF — escolher outra cobaia.")
    saldo0 = quant['quantity']
    print(f"\n    quant alvo id={quant['id']} loc={quant['location_id'][1]} saldo_atual={saldo0}")

    print(f"\n[2] PLANO de repoint (contexto LF cmp=5):")
    for f, target in REPOINT_FIELDS.items():
        atual = fmt_acc(snap.get(f))
        print(f"    {f:46s}: {atual}  ->  id={target}")
    print(f"    production_cost_id: MANTIDO ({fmt_acc(snap.get('property_stock_account_production_cost_id'))}) [decisao Contador]")

    print(f"\n[3] MOVIMENTO esperado (ajuste +{delta} depois -{delta}):")
    print(f"    +{delta}: D 1150200001(id{ACC_TERC_VAL}) / C 1150200002(id{ACC_TERC_CP})")
    print(f"    -{delta}: D 1150200002(id{ACC_TERC_CP}) / C 1150200001(id{ACC_TERC_VAL})")
    print(f"    valor esperado ~ {delta} x custo do produto (SVL)")

    if DRY:
        print("\n" + "=" * 96)
        print("DRY-RUN: nenhuma escrita feita. Reveja o plano acima.")
        print("Para executar (com go): --execute   (restaura categoria e saldo via try/finally)")
        print("=" * 96)
        return

    # ---------- EXECUTE ----------
    resultado = {'entrada_ok': None, 'saida_ok': None, 'saldo_restaurado': None, 'categoria_restaurada': None}
    orig_vals = {f: (snap[f][0] if isinstance(snap.get(f), list) and snap.get(f) else False)
                 for f in REPOINT_FIELDS}
    try:
        print("\n[4] REPOINT (write LF)...")
        odoo.execute_kw('product.category', 'write', [[cat], REPOINT_FIELDS], {'context': ctx()})
        chk = read_ip(odoo, cat)
        for f, t in REPOINT_FIELDS.items():
            got = chk[f][0] if isinstance(chk.get(f), list) and chk.get(f) else None
            print(f"    {f}: -> {fmt_acc(chk.get(f))} {'OK' if got == t else 'FALHOU'}")

        print(f"\n[5] AJUSTE +{delta} (entrada)...")
        apply_adjust(odoo, quant['id'], saldo0 + delta)
        svl_in = latest_svl(odoo, prod)
        if svl_in and svl_in.get('account_move_id'):
            lines = read_move_lines(odoo, svl_in['account_move_id'][0])
            print(f"    SVL id={svl_in['id']} value={svl_in['value']} move={svl_in['account_move_id'][1]}")
            for _, acc, deb, cre in lines:
                print(f"      acc={acc[:40]:40s} D={deb:>10,.2f} C={cre:>10,.2f}")
            resultado['entrada_ok'] = assert_pattern(lines, ACC_TERC_VAL, ACC_TERC_CP)
        else:
            print("    (sem SVL/account_move — verificar; produto pode estar com custo 0)")

        print(f"\n[6] AJUSTE -{delta} (saida, restaura saldo)...")
        apply_adjust(odoo, quant['id'], saldo0)
        svl_out = latest_svl(odoo, prod)
        if svl_out and svl_out.get('account_move_id'):
            lines = read_move_lines(odoo, svl_out['account_move_id'][0])
            print(f"    SVL id={svl_out['id']} value={svl_out['value']} move={svl_out['account_move_id'][1]}")
            for _, acc, deb, cre in lines:
                print(f"      acc={acc[:40]:40s} D={deb:>10,.2f} C={cre:>10,.2f}")
            resultado['saida_ok'] = assert_pattern(lines, ACC_TERC_CP, ACC_TERC_VAL)
    finally:
        # SEMPRE restaurar categoria e conferir saldo
        print("\n[7] RESTAURAR categoria (try/finally)...")
        try:
            odoo.execute_kw('product.category', 'write', [[cat], orig_vals], {'context': ctx()})
            back = read_ip(odoo, cat)
            ok = all((back[f][0] if isinstance(back.get(f), list) and back.get(f) else None) == orig_vals[f]
                     for f in orig_vals)
            resultado['categoria_restaurada'] = ok
            print(f"    categoria restaurada: {'OK' if ok else 'CONFERIR MANUALMENTE'}")
        except Exception as e:
            print(f"    ERRO ao restaurar categoria: {e} — RESTAURAR MANUALMENTE: {orig_vals}")
        q2 = odoo.execute_kw('stock.quant', 'read', [[quant['id']], ['quantity']], {})
        saldo_fim = q2[0]['quantity'] if q2 else None
        resultado['saldo_restaurado'] = (saldo_fim == saldo0)
        print(f"    saldo: inicial={saldo0} final={saldo_fim} {'OK' if saldo_fim == saldo0 else 'CONFERIR'}")

    print("\n" + "=" * 96)
    print("RESULTADO:", resultado)
    print("entrada net-zero terceiros:", '✅' if resultado['entrada_ok'] else '❌/NA')
    print("saida net-zero terceiros  :", '✅' if resultado['saida_ok'] else '❌/NA')
    print("=" * 96)


if __name__ == '__main__':
    main()
