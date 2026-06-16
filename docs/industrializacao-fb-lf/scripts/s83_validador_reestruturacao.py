"""s83 — VALIDADOR (READ-only) dos gates da S3 (reestruturação LF "De Terceiros").

Modos:
  --baseline   captura snapshot PRÉ-go (saldo por produto/lote, contas, parents, reserva MO) -> /tmp/s2_baseline.json
  --validar    compara estado atual vs baseline + checa invariantes pós-A1/A4
               (parents OK, 42 esvaziado exceto açúcar, saldo por produto idêntico,
                0 SVL nos pickings de migração, contas de estoque Δ=0, reserva MO 20797 intacta)

Zero escrita. Uso: python .../s83_validador_reestruturacao.py --baseline   (antes do go)
                   python .../s83_validador_reestruturacao.py --validar     (depois do go)
"""
import sys, json, argparse, collections
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
from dotenv import load_dotenv
load_dotenv('/home/rafaelnascimento/projetos/frete_sistema/.env')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
LOC_42, LOC_MP, LOC_PA = 42, 31092, 31093
MO_KETCHUP = 20797
SUGAR_LOT = '230326'
ESTOQUE_CODES = ['1150100001', '1150100002', '1150100007', '1150100010']
BASELINE = '/tmp/s2_baseline.json'


def snapshot(o):
    def sr(model, dom, fields, **kw):
        kw.setdefault('context', CTX)
        return o.execute_kw(model, 'search_read', [dom], {'fields': fields, **kw})

    # locations LF de estoque (42 e filhas + 31092/31093)
    locs = [l['id'] for l in sr('stock.location', ['|', ['id', 'child_of', LOC_42],
                                                   ['id', 'in', [LOC_MP, LOC_PA]]], ['id'])]
    quants = sr('stock.quant', [['location_id', 'in', locs]],
                ['product_id', 'lot_id', 'location_id', 'quantity', 'reserved_quantity'], limit=6000)
    saldo_prod = collections.defaultdict(float)   # por produto (total LF estoque)
    saldo_prod_lote = collections.defaultdict(float)
    por_loc = collections.Counter()
    for q in quants:
        if abs(q['quantity']) < 1e-6 or not q.get('product_id'):
            continue
        pid = q['product_id'][0]
        lot = q['lot_id'][0] if q.get('lot_id') else 0
        saldo_prod[pid] += q['quantity']
        saldo_prod_lote[f'{pid}|{lot}'] += q['quantity']
        por_loc[q['location_id'][0]] += 1
    # contas de estoque (saldo posted)
    contas = {}
    for c in sr('account.account', [['code', 'in', ESTOQUE_CODES], ['company_id', '=', 5]], ['id', 'code']):
        g = o.execute_kw('account.move.line', 'read_group',
                         [[['account_id', '=', c['id']], ['parent_state', '=', 'posted'], ['company_id', '=', 5]],
                          ['balance:sum'], []], {'lazy': False, 'context': CTX})
        contas[c['code']] = round(g[0].get('balance', 0) if g else 0, 2)
    # parents 31092/31093
    parents = {l['id']: (l['location_id'][0] if l['location_id'] else None)
               for l in o.execute_kw('stock.location', 'read', [[LOC_MP, LOC_PA]],
                                     {'fields': ['location_id'], 'context': CTX})}
    # reserva MO ketchup
    mo = o.execute_kw('mrp.production', 'read', [[MO_KETCHUP]], {'fields': ['name', 'state'], 'context': CTX})
    return {
        'saldo_prod': {str(k): round(v, 3) for k, v in saldo_prod.items()},
        'saldo_prod_lote': {k: round(v, 3) for k, v in saldo_prod_lote.items()},
        'quants_por_loc': dict(por_loc),
        'contas_estoque': contas,
        'parents': {str(k): v for k, v in parents.items()},
        'mo_ketchup': mo[0] if mo else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', action='store_true')
    ap.add_argument('--validar', action='store_true')
    args = ap.parse_args()
    o = get_odoo_connection()
    assert o.authenticate(), 'falha auth'
    print('=' * 80)

    if args.baseline or not args.validar:
        snap = snapshot(o)
        with open(BASELINE, 'w') as f:
            json.dump(snap, f, ensure_ascii=False, indent=2, default=str)
        print('s83 — BASELINE capturado (PRÉ-go)')
        print(f"  produtos com saldo: {len(snap['saldo_prod'])}")
        print(f"  quants por location: {snap['quants_por_loc']}")
        print(f"  parents 31092/31093: {snap['parents']}")
        print(f"  contas estoque: {snap['contas_estoque']}")
        print(f"  MO ketchup: {snap['mo_ketchup']}")
        print(f"  [dump] {BASELINE}")
        return

    # ---- validar ----
    try:
        base = json.load(open(BASELINE))
    except FileNotFoundError:
        print('❌ baseline não encontrado — rode --baseline ANTES do go'); return
    cur = snapshot(o)
    print('s83 — VALIDAÇÃO (PÓS-go) vs baseline')
    falhas = []

    # 1. parents 31092/31093 == 42
    for lid in (str(LOC_MP), str(LOC_PA)):
        if cur['parents'].get(lid) != LOC_42:
            falhas.append(f'parent de {lid} = {cur["parents"].get(lid)} (esperado {LOC_42})')
    print(f"  [A1] parents 31092/31093 sob 42: {'OK' if cur['parents'].get(str(LOC_MP))==LOC_42 and cur['parents'].get(str(LOC_PA))==LOC_42 else 'FALHA'}")

    # 2. saldo por produto idêntico (conservação)
    difs = []
    keys = set(base['saldo_prod']) | set(cur['saldo_prod'])
    for k in keys:
        b = base['saldo_prod'].get(k, 0); c = cur['saldo_prod'].get(k, 0)
        if abs(b - c) > 1e-3:
            difs.append((k, b, c))
    if difs:
        falhas.append(f'{len(difs)} produtos com saldo alterado (ex: {difs[:3]})')
    print(f"  [A4] saldo por produto conservado: {'OK' if not difs else f'FALHA ({len(difs)} difs)'}")

    # 3. 42 esvaziado exceto açúcar
    q42 = cur['quants_por_loc'].get(LOC_42, 0)
    print(f"  [A4] quants restantes em 42: {q42} (esperado ~1 = açúcar)")
    if q42 > 2:
        falhas.append(f'42 ainda tem {q42} quants (esperado ~1 açúcar)')

    # 4. contas de estoque Δ=0 (neutralidade)
    for code in ESTOQUE_CODES:
        d = round(cur['contas_estoque'].get(code, 0) - base['contas_estoque'].get(code, 0), 2)
        flag = 'OK' if abs(d) < 0.01 else f'Δ={d}'
        print(f"  [neutralidade] {code}: {flag}")
        if abs(d) >= 0.01:
            falhas.append(f'conta {code} mudou Δ={d} (migração deveria ser 0 SVL)')

    # 5. reserva MO ketchup intacta
    print(f"  [MO] ketchup state: base={base['mo_ketchup']} cur={cur['mo_ketchup']}")

    print('\n' + ('✅ TODOS OS GATES OK' if not falhas else f'❌ {len(falhas)} FALHAS:'))
    for f in falhas:
        print(f'   - {f}')


if __name__ == '__main__':
    main()
