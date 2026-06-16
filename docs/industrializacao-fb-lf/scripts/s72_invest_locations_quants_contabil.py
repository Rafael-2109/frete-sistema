"""s72 — INVESTIGA (READ-only) S2: locations-chave + contábil (valoração) + universo de migração + exceções.

Cobre itens do checklist S2 (MACRO_REESTRUTURACAO_DE_TERCEIROS_LF.md):
  - Locations-chave (42 + subárvore, 31092, 31093, 53, pós-produção, em-transito-ind, subcontratação)
  - Contábil: campos de conta/valoração na stock.location + property da product.category (company 5)
  - Mecanismo de migração: quants na subárvore de 42 (livre vs reservado, com/sem lote)
  - Exceções: lotes MIGRAÇÃO/P-15/05, açúcar, produtos sem PO

Zero escrita. Uso: python docs/industrializacao-fb-lf/scripts/s72_invest_locations_quants_contabil.py
"""
import sys, json, collections
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
# worktree NÃO tem .env -> carregar o da raiz (dotenv resolve por __file__, que aqui é o worktree)
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

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX})

    def fg(model, pat):
        f = o.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'relation'], 'context': CTX})
        return {k: v for k, v in f.items() if any(p in k.lower() for p in pat)}

    print(SEP); print('s72 — LOCATIONS + CONTÁBIL + MIGRAÇÃO + EXCEÇÕES (READ-only)'); print(SEP)

    # ---------- 1. Campos de conta/valoração existentes em stock.location ----------
    print('\n### 1. stock.location — campos de conta/valoração disponíveis')
    loc_acc_fields = fg('stock.location', ['account', 'valuation', 'valoracao'])
    for k, v in loc_acc_fields.items():
        print(f'  {k} ({v["type"]}{"->"+v["relation"] if v.get("relation") else ""}): {v["string"]}')
    OUT['stock_location_account_fields'] = list(loc_acc_fields.keys())

    # ---------- 2. Locations-chave ----------
    print('\n### 2. Locations-chave (LF)')
    # descobre por nome as que faltam id
    nomes = ['Pré-Produção', 'Pre-Produção', 'Pós-Produção', 'Pos-Produção',
             'Terceiros', 'Transito', 'Trânsito', 'Subcontrat', 'Industrializ']
    dom = ['|', ['id', 'in', [42, 31092, 31093]],
           '&', ['company_id', 'in', [5]], ['name', 'ilike', 'produção']]
    base_fields = ['id', 'complete_name', 'name', 'usage', 'company_id', 'location_id', 'scrap_location', 'return_location'] + list(loc_acc_fields.keys())
    # pega explicitamente as chaves + qualquer LF com nome relevante
    chave_ids = set([42, 31092, 31093])
    for n in ['produção', 'terceiros', 'transito', 'trânsito', 'subcontrat', 'industrializ', 'pós', 'pré', 'pre-', 'pos-']:
        for l in sr('stock.location', [['company_id', 'in', [5, 1]], ['complete_name', 'ilike', n]], ['id'], limit=50):
            chave_ids.add(l['id'])
    locs = rd('stock.location', sorted(chave_ids), base_fields)
    OUT['locations_chave'] = locs
    for l in sorted(locs, key=lambda x: x['id']):
        extra = {k: l[k] for k in loc_acc_fields if l.get(k)}
        print(f"  [{l['id']}] {l['usage']:10s} | {l['complete_name']}  (company={l['company_id']})"
              + (f"  ACC={extra}" if extra else ''))

    # ---------- 3. Subárvore de 42 (para entender onde mora o saldo) ----------
    print('\n### 3. Subárvore de 42 (LF/Estoque) — child locations internal')
    filhas = sr('stock.location', [['id', 'child_of', 42]], ['id', 'complete_name', 'usage'])
    OUT['subarvore_42_ids'] = [f['id'] for f in filhas]
    print(f"  total locations na subárvore de 42 (inclui 42): {len(filhas)}")

    # ---------- 4. Quants — universo de migração ----------
    print('\n### 4. stock.quant — universo de migração')
    sub_ids = [f['id'] for f in filhas]
    qdom = [['location_id', 'in', sub_ids]]
    qfields = ['id', 'location_id', 'product_id', 'lot_id', 'quantity', 'reserved_quantity', 'company_id']
    quants = sr('stock.quant', qdom, qfields, limit=5000)
    OUT['quants_total'] = len(quants)
    # só os com quantity != 0
    qn = [q for q in quants if abs(q['quantity']) > 1e-6]
    print(f"  quants na subárvore de 42: {len(quants)} (com qty!=0: {len(qn)})")
    # quebra por location
    by_loc = collections.Counter()
    by_loc_qty = collections.defaultdict(float)
    livres = reservados = 0
    com_lote = sem_lote = 0
    for q in qn:
        lname = q['location_id'][1] if q['location_id'] else '?'
        by_loc[lname] += 1
        by_loc_qty[lname] += q['quantity']
        if q['reserved_quantity'] and abs(q['reserved_quantity']) > 1e-6:
            reservados += 1
        else:
            livres += 1
        if q['lot_id']:
            com_lote += 1
        else:
            sem_lote += 1
    print(f"  quants(qty!=0): livres={livres} reservados={reservados} | com_lote={com_lote} sem_lote={sem_lote}")
    print('  --- por location (qty!=0) ---')
    for lname, cnt in by_loc.most_common():
        print(f"    {cnt:4d} quants | qty={by_loc_qty[lname]:>14.2f} | {lname}")
    OUT['quants_por_location'] = {k: {'n': by_loc[k], 'qty': round(by_loc_qty[k], 2)} for k in by_loc}

    # ---------- 5. Exceções: lotes MIGRAÇÃO / P-15/05 ----------
    print('\n### 5. Exceções — lotes especiais')
    lote_names = collections.Counter()
    for q in qn:
        if q['lot_id']:
            ln = q['lot_id'][1]
            up = ln.upper()
            if 'MIGRA' in up or 'P-15' in up or '15/05' in up:
                lote_names[ln] += 1
    if lote_names:
        for ln, c in lote_names.most_common():
            print(f"    {c}x lote especial: {ln}")
    else:
        print("    nenhum quant(qty!=0) em lote MIGRAÇÃO/P-15/05 na subárvore de 42")
    OUT['lotes_especiais'] = dict(lote_names)

    # açúcar (exceção saída FB pendente)
    print('\n  --- açúcar (exceção saída FB pendente) ---')
    acu = [q for q in qn if q['product_id'] and 'çúcar' in q['product_id'][1].lower() or (q['product_id'] and 'acucar' in q['product_id'][1].lower())]
    for q in acu:
        print(f"    quant {q['id']}: {q['product_id'][1]} | loc={q['location_id'][1]} | qty={q['quantity']} resv={q['reserved_quantity']} lote={q['lot_id']}")
    OUT['acucar_quants'] = [{'id': q['id'], 'product': q['product_id'][1], 'qty': q['quantity'], 'resv': q['reserved_quantity']} for q in acu]

    # ---------- 6. Contábil: categorias dos produtos em 42 + property accounts (company 5) ----------
    print('\n### 6. Contábil — product.category dos produtos no saldo + valoração (company 5)')
    prod_ids = list({q['product_id'][0] for q in qn if q['product_id']})
    print(f"  produtos distintos no saldo (qty!=0): {len(prod_ids)}")
    prods = rd('product.product', prod_ids, ['id', 'categ_id', 'type', 'default_code'])
    cat_counter = collections.Counter()
    for p in prods:
        if p.get('categ_id'):
            cat_counter[p['categ_id'][1]] += 1
    print('  --- categorias presentes (por nº de produtos) ---')
    for cat, c in cat_counter.most_common():
        print(f"    {c:4d} prod | categ: {cat}")
    OUT['categorias_produtos'] = dict(cat_counter)

    # property de valoração das categorias (company-specific)
    cat_ids = list({p['categ_id'][0] for p in prods if p.get('categ_id')})
    cat_fields = ['id', 'complete_name', 'property_valuation', 'property_cost_method',
                  'property_stock_valuation_account_id', 'property_stock_account_input_categ_id',
                  'property_stock_account_output_categ_id']
    # alguns campos são company-dependent (ir.property) -> read com company_id=5 no context
    cats = o.execute_kw('product.category', 'read', [cat_ids], {'fields': cat_fields, 'context': {**CTX, 'force_company': 5}})
    print('\n  --- valoração por categoria (context company=5 LF) ---')
    for c in cats:
        print(f"    [{c['id']}] {c['complete_name']}")
        print(f"        valuation={c.get('property_valuation')} cost={c.get('property_cost_method')}")
        print(f"        stock_val_acc={c.get('property_stock_valuation_account_id')}")
        print(f"        in={c.get('property_stock_account_input_categ_id')} out={c.get('property_stock_account_output_categ_id')}")
    OUT['categorias_valoracao'] = cats

    # ---------- dump ----------
    with open('/tmp/s2_s72.json', 'w') as f:
        json.dump(OUT, f, ensure_ascii=False, indent=2, default=str)
    print('\n[dump] /tmp/s2_s72.json')


if __name__ == '__main__':
    main()
