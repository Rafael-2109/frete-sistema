"""s80 — INVESTIGA (READ-only) S2/A5: foto contábil terceiros vs próprio vs ciclo na LF.

Reconcilia a decisão D1 (repoint L1 -> 1150200001) com o ACHADOS (1150200001=R$0; sistema usa 51010xx).
  - saldo (balance posted) das contas LF: próprio (1150100001/002/007/010), transitórias (011/012),
    terceiros (1150200001/002), ciclo (5101010001/5101020001)
  - ir.property das categorias (há override p/ terceiros por company 5?)

Zero escrita. Uso: python .../s80_invest_contabil_terceiros.py
"""
import sys, json
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
from dotenv import load_dotenv
load_dotenv('/home/rafaelnascimento/projetos/frete_sistema/.env')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
OUT = {}


def main():
    o = get_odoo_connection()
    assert o.authenticate(), 'falha auth'

    def sr(model, dom, fields, **kw):
        kw.setdefault('context', CTX)
        return o.execute_kw(model, 'search_read', [dom], {'fields': fields, **kw})

    def rg(model, dom, gb, fields):
        return o.execute_kw(model, 'read_group', [dom, fields, gb], {'lazy': False, 'context': CTX})

    print('=' * 88); print('s80 — foto contábil terceiros vs próprio vs ciclo (LF, company 5)'); print('=' * 88)

    codes = ['1150100001', '1150100002', '1150100007', '1150100010', '1150100011', '1150100012',
             '1150200001', '1150200002', '5101010001', '5101020001', '3201000002', '3201000003']
    contas = sr('account.account', [['code', 'in', codes], ['company_id', '=', 5]],
                ['id', 'code', 'name', 'account_type'])
    by_id = {c['id']: c for c in contas}
    print('\n### 1. Contas LF (company 5) — saldo posted')
    for c in sorted(contas, key=lambda x: x['code']):
        g = rg('account.move.line',
               [['account_id', '=', c['id']], ['parent_state', '=', 'posted'], ['company_id', '=', 5]],
               [], ['debit:sum', 'credit:sum', 'balance:sum'])
        bal = g[0].get('balance', 0) if g else 0
        n = g[0].get('__count', 0) if g else 0
        print(f"  {c['code']} {c['name'][:36]:36s} type={c['account_type']:16s} saldo={bal:>16,.2f} ({n} lançs)")
        OUT[c['code']] = {'id': c['id'], 'name': c['name'], 'saldo': round(bal, 2), 'lancs': n}

    # contas terceiros podem não existir na company 5 — reportar
    faltando = [cd for cd in codes if cd not in {c['code'] for c in contas}]
    if faltando:
        print(f"\n  ⚠️ códigos NÃO encontrados como conta da company 5: {faltando}")
        # buscar em qualquer company
        any_c = sr('account.account', [['code', 'in', faltando]], ['id', 'code', 'name', 'company_id'])
        for c in any_c:
            print(f"      {c['code']} {c['name']} (company={c['company_id']})")
        OUT['faltando_c5'] = faltando

    # ---------- 2. ir.property override de valoração por categoria (company 5) ----------
    print('\n### 2. ir.property — property_stock_valuation_account_id por company (override terceiros?)')
    props = sr('ir.property',
               [['name', '=', 'property_stock_valuation_account_id'], ['company_id', '=', 5]],
               ['id', 'res_id', 'value_reference', 'company_id'], limit=80)
    print(f"  ir.property (valuation, company 5): {len(props)}")
    # resolver value_reference -> conta
    vals = {}
    for p in props[:80]:
        vr = p.get('value_reference')  # ex 'account.account,22288'
        vals[vr] = vals.get(vr, 0) + 1
    for vr, n in sorted(vals.items(), key=lambda x: -x[1]):
        # nome da conta
        acc_name = ''
        if vr and ',' in str(vr):
            aid = int(str(vr).split(',')[1])
            ac = o.execute_kw('account.account', 'read', [[aid]], {'fields': ['code', 'name'], 'context': CTX})
            if ac:
                acc_name = f"{ac[0]['code']} {ac[0]['name']}"
        print(f"    {n:4d} categorias -> {vr}  ({acc_name})")
    OUT['ir_property_valuation_c5'] = vals

    with open('/tmp/s2_s80.json', 'w') as f:
        json.dump(OUT, f, ensure_ascii=False, indent=2, default=str)
    print('\n[dump] /tmp/s2_s80.json')


if __name__ == '__main__':
    main()
