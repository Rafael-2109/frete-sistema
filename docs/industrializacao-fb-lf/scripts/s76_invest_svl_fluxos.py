"""s76 — INVESTIGA (READ-only) S2: prova SVL limpa internal->internal + SVL dos fluxos a redirecionar.

  - prova: moves done 365d com src.usage=internal E dst.usage=internal (company 5) geram SVL? (esperado 0)
  - SVL dos moves pt64 (26489->42 entrada industrializ.) — muda algo redirecionar p/ 31092?
  - SVL dos moves pt35 (54->42 armazenar PA) — muda algo redirecionar p/ 31093?

Zero escrita. Uso: python .../s76_invest_svl_fluxos.py
"""
import sys, json
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
from dotenv import load_dotenv
load_dotenv('/home/rafaelnascimento/projetos/frete_sistema/.env')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
SEP = '=' * 90
OUT = {}


def main():
    o = get_odoo_connection()
    assert o.authenticate(), 'falha auth'

    def sr(model, dom, fields, **kw):
        kw.setdefault('context', CTX)
        return o.execute_kw(model, 'search_read', [dom], {'fields': fields, **kw})

    def count(model, dom):
        return o.execute_kw(model, 'search_count', [dom], {'context': CTX})

    def m2(v):
        return f"{v[0]}:{v[1]}" if v else "—"

    print(SEP); print('s76 — SVL internal->internal + fluxos pt64/pt35 (READ-only)'); print(SEP)

    # ---------- 1. Prova limpa: internal->internal company 5 = 0 SVL ----------
    print('\n### 1. Moves done 365d internal(c5)->internal(c5) — geram SVL?')
    dom = [['state', '=', 'done'], ['date', '>=', '2025-06-01'],
           ['company_id', '=', 5],
           ['location_id.usage', '=', 'internal'], ['location_dest_id.usage', '=', 'internal']]
    mv = sr('stock.move', dom, ['id', 'location_id', 'location_dest_id', 'product_id'], limit=2000)
    print(f"  moves internal->internal (c5, 365d): {len(mv)}")
    ids = [m['id'] for m in mv]
    # contar SVL ligadas (em lotes p/ não estourar domain)
    total_svl = 0
    for i in range(0, len(ids), 300):
        total_svl += count('stock.valuation.layer', [['stock_move_id', 'in', ids[i:i+300]]])
    print(f"  SVL ligadas a esses moves: {total_svl}  (esperado 0 se internal->internal é neutro)")
    OUT['internal_moves'] = len(mv)
    OUT['internal_svl'] = total_svl
    if total_svl:
        sample = sr('stock.valuation.layer', [['stock_move_id', 'in', ids]],
                    ['id', 'stock_move_id', 'value', 'quantity'], limit=10)
        for s in sample:
            print(f"    SVL {s['id']} move={m2(s.get('stock_move_id'))} value={s.get('value')}")

    # ---------- 2. pt64 (26489->42 entrada industrializ.) gera SVL? ----------
    print('\n### 2. pt64 (Recebimentos Industrialização, 26489->42) — SVL?')
    mv64 = sr('stock.move', [['picking_type_id', '=', 64], ['state', '=', 'done'], ['date', '>=', '2025-06-01']],
              ['id', 'location_id', 'location_dest_id', 'product_id'], limit=500)
    ids64 = [m['id'] for m in mv64]
    svl64 = 0
    for i in range(0, len(ids64), 300):
        svl64 += count('stock.valuation.layer', [['stock_move_id', 'in', ids64[i:i+300]]])
    print(f"  moves pt64 done(365d)={len(mv64)} | SVL ligadas={svl64}")
    # amostra de src/dst reais
    srcset = {}
    for m in mv64:
        k = f"{m2(m['location_id'])} -> {m2(m['location_dest_id'])}"
        srcset[k] = srcset.get(k, 0) + 1
    for k, c in sorted(srcset.items(), key=lambda x: -x[1]):
        print(f"    {c:4d}x {k}")
    OUT['pt64_moves'] = len(mv64); OUT['pt64_svl'] = svl64

    # ---------- 3. pt35 (54->42 armazenar PA) gera SVL? ----------
    print('\n### 3. pt35 (Armazenar PA, 54->42) — SVL?')
    mv35 = sr('stock.move', [['picking_type_id', '=', 35], ['state', '=', 'done'], ['date', '>=', '2025-06-01']],
              ['id', 'location_id', 'location_dest_id'], limit=2000)
    ids35 = [m['id'] for m in mv35]
    svl35 = 0
    for i in range(0, len(ids35), 300):
        svl35 += count('stock.valuation.layer', [['stock_move_id', 'in', ids35[i:i+300]]])
    print(f"  moves pt35 done(365d)={len(mv35)} | SVL ligadas={svl35}")
    OUT['pt35_moves'] = len(mv35); OUT['pt35_svl'] = svl35

    with open('/tmp/s2_s76.json', 'w') as f:
        json.dump(OUT, f, ensure_ascii=False, indent=2, default=str)
    print('\n[dump] /tmp/s2_s76.json')


if __name__ == '__main__':
    main()
