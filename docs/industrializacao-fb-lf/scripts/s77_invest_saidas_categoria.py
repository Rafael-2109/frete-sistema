"""s77 — INVESTIGA (READ-only) S2: conteúdo (PA vs MP/EMB) das SAÍDAS de 42 por picking_type.

Decide se a origem de cada rule de saída vira 31093 (PA) ou 31092 (material).
pt de saída: 20 (Ordens Entrega), 66 (Exp Industrializ.), 94 (Exp Ñ Aplicado/perda),
             97 (Exp Industrializ. Retorno), 24 (Devoluções), 34 (Escolha Componentes->produção)

Zero escrita. Uso: python .../s77_invest_saidas_categoria.py
"""
import sys, json, collections
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

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX}) if ids else []

    PTS = {20: 'Ordens Entrega', 66: 'Exp Industrializ', 94: 'Exp Ñ Aplicado(perda)',
           97: 'Exp Ind Retorno', 24: 'Devoluções', 34: 'Escolha Componentes'}
    print('=' * 80); print('s77 — conteúdo PA vs MP das saídas (365d)'); print('=' * 80)

    for pt, nome in PTS.items():
        mv = sr('stock.move', [['picking_type_id', '=', pt], ['state', '=', 'done'], ['date', '>=', '2025-06-01']],
                ['id', 'product_id'], limit=4000)
        prod_ids = list({m['product_id'][0] for m in mv if m.get('product_id')})
        prods = rd('product.product', prod_ids, ['id', 'categ_id'])
        catof = {p['id']: (p['categ_id'][1] if p.get('categ_id') else '?') for p in prods}
        macro = collections.Counter()
        for m in mv:
            pid = m['product_id'][0] if m.get('product_id') else None
            cat = catof.get(pid, '?')
            top = cat.split('/')[1].strip() if '/' in cat else cat
            macro[top] += 1
        print(f"\n  pt{pt} ({nome}) — {len(mv)} moves:")
        for c, n in macro.most_common():
            print(f"      {n:5d} | {c}")
        OUT[f'pt{pt}'] = dict(macro)

    with open('/tmp/s2_s77.json', 'w') as f:
        json.dump(OUT, f, ensure_ascii=False, indent=2, default=str)
    print('\n[dump] /tmp/s2_s77.json')


if __name__ == '__main__':
    main()
