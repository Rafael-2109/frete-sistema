"""s82 — BUILDER da S3 (reestruturação LF "De Terceiros") — DRY-RUN-FIRST.

Modos (dry-run é o DEFAULT; escrita só com --confirmar + go fresco do Rafael):
  --plano       (default) roda TODOS os blocos em DRY/READ + valida invariantes + gera mapa A5
  --reparent    A1: 31092/31093 location_id -> 42
  --putaway     A2/A3: cria 2 stock.putaway.rule (cat 6 PA->31093 ; cat 1 TODOS->31092)
  --migrar      A4: cria picking(s) interno(s) pt23 movendo os 442 quants livres por categoria
  --mapa-a5     A5(READ): categorias próprias com material no saldo -> candidatas a repoint (Contador)
  --confirmar   efetiva a escrita do(s) bloco(s) selecionado(s) (NUNCA no --plano)

Uso: python .../s82_exec_reestruturacao.py            # plano dry completo
     python .../s82_exec_reestruturacao.py --migrar   # dry da migração
     python .../s82_exec_reestruturacao.py --reparent --confirmar   # (só com go)
"""
import sys, json, argparse, collections
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema_wire_r2')
from dotenv import load_dotenv
load_dotenv('/home/rafaelnascimento/projetos/frete_sistema/.env')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
SEP = '=' * 92
LOC_42, LOC_MP, LOC_PA = 42, 31092, 31093
CAT_PA_ROOT, CAT_ROOT = 6, 1
PT_INTERNO = 23           # Transferências Internas (LF)
TERCEIROS_ACC_ID = 26140  # 1150200001 (LF)
SUGAR_LOT = '230326'      # lote do açúcar reservado (excluir — D3)


def main():
    ap = argparse.ArgumentParser()
    for m in ['plano', 'reparent', 'putaway', 'migrar', 'mapa-a5', 'confirmar']:
        ap.add_argument(f'--{m}', action='store_true')
    args = ap.parse_args()
    blocos = any([args.reparent, args.putaway, args.migrar, getattr(args, 'mapa_a5')])
    plano = args.plano or not blocos
    confirmar = args.confirmar and not plano

    o = get_odoo_connection()
    assert o.authenticate(), 'falha auth'

    def sr(model, dom, fields, **kw):
        kw.setdefault('context', CTX)
        return o.execute_kw(model, 'search_read', [dom], {'fields': fields, **kw})

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [ids], {'fields': fields, 'context': CTX}) if ids else []

    def m2(v):
        return f"{v[0]}:{v[1]}" if v else "—"

    print(SEP); print(f"s82 — BUILDER S3  (modo={'PLANO/DRY' if plano else 'BLOCO'} confirmar={confirmar})"); print(SEP)
    R = {'mode': 'plano' if plano else 'bloco', 'confirmar': confirmar}

    # ---------- pré-condições comuns ----------
    locs = {l['id']: l for l in rd('stock.location', [LOC_42, LOC_MP, LOC_PA], ['complete_name', 'usage', 'location_id'])}
    pa_cats = {c['id'] for c in sr('product.category', [['id', 'child_of', CAT_PA_ROOT]], ['id'])}
    print(f"\n[pré] 42={m2([LOC_42, locs[LOC_42]['complete_name']])} usage={locs[LOC_42]['usage']}")
    print(f"[pré] 31092 parent={m2(locs[LOC_MP]['location_id'])} | 31093 parent={m2(locs[LOC_PA]['location_id'])}")
    print(f"[pré] categorias descendentes de PA(6): {len(pa_cats)}")

    # ================= A1 reparent =================
    if plano or args.reparent:
        print('\n' + '-' * 60 + '\n### A1 — REPARENT 31092/31093 sob 42')
        need = []
        for lid in (LOC_MP, LOC_PA):
            cur = locs[lid]['location_id'][0] if locs[lid]['location_id'] else None
            if cur != LOC_42:
                need.append(lid)
            print(f"  [{lid}] {locs[lid]['complete_name']}: parent atual={cur} -> alvo={LOC_42} {'(MUDA)' if cur != LOC_42 else '(ok)'}")
        R['A1'] = {'precisa_reparent': need}
        if (args.reparent and confirmar) and need:
            for lid in need:
                o.execute_kw('stock.location', 'write', [[lid], {'location_id': LOC_42}], {'context': CTX})
            print(f"  ✅ ESCRITO: reparent {need} -> 42")
        else:
            print("  [DRY] write stock.location.location_id=42 (não executado)")

    # ================= A2/A3 put-away =================
    if plano or args.putaway:
        print('\n' + '-' * 60 + '\n### A2/A3 — PUT-AWAY (cat 6 PA->31093 ; cat 1 TODOS->31092)')
        existing = sr('stock.putaway.rule', [['location_in_id', 'child_of', LOC_42]],
                      ['id', 'category_id', 'location_out_id'])
        print(f"  put-away existentes em 42/filhas: {len(existing)} (esperado 0)")
        regras = [
            {'location_in_id': LOC_42, 'category_id': CAT_PA_ROOT, 'location_out_id': LOC_PA, 'company_id': 5},
            {'location_in_id': LOC_42, 'category_id': CAT_ROOT, 'location_out_id': LOC_MP, 'company_id': 5},
        ]
        for r in regras:
            print(f"  [DRY] putaway.rule: in={r['location_in_id']} categ={r['category_id']} -> out={r['location_out_id']}")
        R['A2A3'] = {'existentes': len(existing), 'criar': regras}
        if args.putaway and confirmar and not existing:
            ids = [o.execute_kw('stock.putaway.rule', 'create', [r], {'context': CTX}) for r in regras]
            print(f"  ✅ ESCRITO: putaway rules {ids}")
        else:
            print("  [DRY] create stock.putaway.rule x2 (não executado)")

    # ================= A4 migração (classificação) =================
    if plano or args.migrar:
        print('\n' + '-' * 60 + '\n### A4 — MIGRAÇÃO dos quants livres (classificada por categoria)')
        sub42 = [f['id'] for f in sr('stock.location', [['id', 'child_of', LOC_42]], ['id'])]
        quants = sr('stock.quant', [['location_id', 'in', sub42]],
                    ['id', 'location_id', 'product_id', 'lot_id', 'quantity', 'reserved_quantity'], limit=6000)
        qn = [q for q in quants if abs(q['quantity']) > 1e-6 and q.get('product_id')]
        livres = [q for q in qn if not (q['reserved_quantity'] and q['reserved_quantity'] > 1e-6)]
        reservados = [q for q in qn if q not in livres]
        acucar = [q for q in livres if q.get('lot_id') and SUGAR_LOT in str(q['lot_id'][1])]
        migrar = [q for q in livres if q not in acucar]
        prod_ids = list({q['product_id'][0] for q in migrar})
        pcat = {p['id']: (p['categ_id'][0] if p.get('categ_id') else None)
                for p in rd('product.product', prod_ids, ['categ_id'])}
        destino = collections.Counter(); dqty = collections.defaultdict(float); plan_lines = []
        for q in migrar:
            cat = pcat.get(q['product_id'][0])
            dst = LOC_PA if cat in pa_cats else LOC_MP
            destino[dst] += 1; dqty[dst] += q['quantity']
            plan_lines.append({'quant': q['id'], 'product': q['product_id'][1], 'lot': m2(q.get('lot_id')),
                               'qty': q['quantity'], 'src': q['location_id'][0], 'dst': dst})
        soma_mig = sum(q['quantity'] for q in migrar)
        soma_tot = sum(q['quantity'] for q in qn)
        # o açúcar reservado (lote 230326) já sai via 'reservados'; 'acucar' é rede de segurança caso esteja livre
        sugar_resv = [q for q in reservados if q.get('lot_id') and SUGAR_LOT in str(q['lot_id'][1])]
        print(f"  quants(qty!=0)={len(qn)} | livres={len(livres)} | EXCLUÍDOS: reservados={len(reservados)} "
              f"(açúcar lote {SUGAR_LOT}={len(sugar_resv)}) + açúcar-livre-no-filtro={len(acucar)}")
        print(f"  A MIGRAR={len(migrar)}  ->  31092(MP/EMB)={destino[LOC_MP]} ({dqty[LOC_MP]:,.1f})  "
              f"31093(PA)={destino[LOC_PA]} ({dqty[LOC_PA]:,.1f})")
        inv_ok = abs((dqty[LOC_MP] + dqty[LOC_PA]) - soma_mig) < 1e-3
        print(f"  INVARIANTE Σdst == Σmigrar: {dqty[LOC_MP]+dqty[LOC_PA]:,.3f} == {soma_mig:,.3f} -> {'OK' if inv_ok else 'FALHA'}")
        print(f"  (saldo total {soma_tot:,.1f} = migrar {soma_mig:,.1f} + reservado/açúcar {soma_tot-soma_mig:,.1f})")
        R['A4'] = {'qn': len(qn), 'migrar': len(migrar), 'dst_31092': destino[LOC_MP], 'dst_31093': destino[LOC_PA],
                   'qty_31092': round(dqty[LOC_MP], 2), 'qty_31093': round(dqty[LOC_PA], 2),
                   'acucar_excluido': [q['id'] for q in acucar], 'invariante_ok': inv_ok}
        with open('/tmp/s2_s82_migracao_plan.json', 'w') as f:
            json.dump(plan_lines, f, ensure_ascii=False, indent=2, default=str)
        print("  [dump] /tmp/s2_s82_migracao_plan.json (442 linhas planejadas)")
        if args.migrar and confirmar:
            print("  ⚠️ ESCRITA da migração exige go explícito — implementar criação de picking pt23 aqui (gated).")
        else:
            print("  [DRY] criação de picking interno pt23 (não executado)")

    # ================= A5 mapa (READ) =================
    if plano or getattr(args, 'mapa_a5'):
        print('\n' + '-' * 60 + '\n### A5 — MAPA categorias próprias no saldo (candidatas a repoint p/ Contador)')
        props = sr('ir.property', [['name', '=', 'property_stock_valuation_account_id'], ['company_id', '=', 5]],
                   ['res_id', 'value_reference'])
        cat2acc = {}
        for p in props:
            rid = p.get('res_id')
            if rid and ',' in str(rid):
                vr = p.get('value_reference')
                cat2acc[int(str(rid).split(',')[1])] = int(str(vr).split(',')[1]) if vr and ',' in str(vr) else None
        sub42 = [f['id'] for f in sr('stock.location', [['id', 'child_of', LOC_42]], ['id'])]
        quants = sr('stock.quant', [['location_id', 'in', sub42]], ['product_id', 'quantity'], limit=6000)
        qn = [q for q in quants if abs(q['quantity']) > 1e-6 and q.get('product_id')]
        prod_ids = list({q['product_id'][0] for q in qn})
        pcat = {p['id']: (p['categ_id'][0] if p.get('categ_id') else None)
                for p in rd('product.product', prod_ids, ['categ_id'])}
        catname = {c['id']: c['complete_name'] for c in rd('product.category', list({v for v in pcat.values() if v}), ['complete_name'])}
        proprio = collections.Counter(); pqty = collections.defaultdict(float); acc_of = {}
        for q in qn:
            cat = pcat.get(q['product_id'][0])
            acc = cat2acc.get(cat)
            if acc != TERCEIROS_ACC_ID:  # próprio ou sem property
                proprio[cat] += 1; pqty[cat] += q['quantity']; acc_of[cat] = acc
        print(f"  categorias PRÓPRIO com material no saldo: {len(proprio)} ({sum(proprio.values())} quants)")
        linhas_a5 = []
        for cat, n in proprio.most_common():
            linhas_a5.append({'categ_id': cat, 'categoria': catname.get(cat, cat),
                              'quants': n, 'qty': round(pqty[cat], 1), 'conta_atual': acc_of.get(cat)})
            print(f"    [{cat}] {n:4d}q qty={pqty[cat]:>12,.1f} acc={acc_of.get(cat)} | {catname.get(cat)}")
        R['A5'] = {'categorias_proprio': len(proprio), 'quants': sum(proprio.values())}
        # entregável CSV p/ Contador
        with open('/tmp/s2_mapa_a5_categorias_repoint.csv', 'w', encoding='utf-8') as f:
            f.write('categ_id;categoria;quants;qty;conta_valoracao_atual;conta_alvo\n')
            for l in linhas_a5:
                f.write(f"{l['categ_id']};{l['categoria']};{l['quants']};{l['qty']};{l['conta_atual']};1150200001\n")
        print("  [entregável] /tmp/s2_mapa_a5_categorias_repoint.csv")

    print('\n' + SEP); print('RESUMO:', json.dumps({k: v for k, v in R.items()
          if k in ('A1', 'A4', 'A5', 'mode', 'confirmar')}, ensure_ascii=False, default=str)[:600])
    with open('/tmp/s2_s82.json', 'w') as f:
        json.dump(R, f, ensure_ascii=False, indent=2, default=str)


if __name__ == '__main__':
    main()
