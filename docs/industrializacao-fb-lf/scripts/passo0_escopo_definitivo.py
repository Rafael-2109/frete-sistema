#!/usr/bin/env python3
"""
Passo 0 — ESCOPO DEFINITIVO do repoint (READ-ONLY).

Regra (Rafael): componentes PRODUTIVOS da LF = FB (terceiros) -> repoint.
Proprio da LF = so' MRO/uso-consumo/servico/ativo-fixo -> NAO repoint.

Classifica TODAS as product.category pelo RAMO de 1o nivel (apos 'TODOS /') e
le property_valuation no contexto LF. Define:
  - PRODUTIVAS (EMBALAGEM / MATERIA PRIMA / PRODUTO ACABADO / SEMI ACABADOS)
  - OWN/MRO    (USO E CONSUMO / SERVICO / ATIVO FIXO / DESPESAS / outras)
Foco no que importa: categorias real_time (geram SVL) por ramo.
Saida: escopo de repoint (productive real_time) + JSON /tmp/passo0_escopo.json

Uso: source .venv/bin/activate
     python docs/industrializacao-fb-lf/scripts/passo0_escopo_definitivo.py
"""
import sys
import json
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_LF = 5
PRODUTIVAS = {'EMBALAGEM', 'MATERIA PRIMA', 'PRODUTO ACABADO', 'SEMI ACABADOS'}


def ramo(complete_name):
    parts = [p.strip() for p in complete_name.split('/')]
    # parts[0] == 'TODOS'; ramo de 1o nivel = parts[1]
    return parts[1] if len(parts) > 1 else parts[0]


def main():
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise SystemExit("Falha auth Odoo")

    cats = odoo.search_read('product.category', [], ['complete_name'], limit=5000)
    ids = [c['id'] for c in cats]
    name_by_id = {c['id']: c['complete_name'] for c in cats}

    # valuation/cost_method no contexto LF (company_dependent)
    val_lf = {}
    for i in range(0, len(ids), 300):
        chunk = ids[i:i + 300]
        rows = odoo.execute_kw('product.category', 'read',
                               [chunk, ['property_valuation', 'property_cost_method']],
                               {'context': {'allowed_company_ids': [CMP_LF], 'company_id': CMP_LF}})
        for r in rows:
            val_lf[r['id']] = (r.get('property_valuation'), r.get('property_cost_method'))

    from collections import defaultdict
    buckets = defaultdict(lambda: {'real_time': [], 'outros': []})
    for c in cats:
        r = ramo(c['complete_name'])
        grp = 'PRODUTIVA' if r in PRODUTIVAS else 'OWN/MRO'
        v = val_lf.get(c['id'], (None, None))[0]
        key = 'real_time' if v == 'real_time' else 'outros'
        buckets[(grp, r)][key].append(c['id'])

    print("=" * 96)
    print("CLASSIFICACAO por ramo (valuation no contexto LF)")
    print("=" * 96)
    prod_rt = []
    own_rt = []
    for (grp, r), d in sorted(buckets.items()):
        nrt, no = len(d['real_time']), len(d['outros'])
        print(f"  [{grp:9s}] {r:22s} real_time={nrt:<4} outros(consu/manual/std)={no}")
        if grp == 'PRODUTIVA':
            prod_rt += d['real_time']
        else:
            own_rt += d['real_time']

    print()
    print("=" * 96)
    print(f"ESCOPO DE REPOINT (PRODUTIVAS real_time) = {len(prod_rt)} categorias")
    print("=" * 96)
    for cid in sorted(prod_rt):
        print(f"  {cid:<6} {name_by_id[cid]}")

    print()
    print("=" * 96)
    print(f"⚠️  OWN/MRO com valuation real_time na LF = {len(own_rt)} (NAO repoint; LF proprio)")
    print("    (se >0, sao estoques proprios reais da LF que devem manter contas proprias)")
    print("=" * 96)
    for cid in sorted(own_rt):
        print(f"  {cid:<6} {name_by_id[cid]}")

    json.dump({'escopo_repoint_real_time': sorted(prod_rt),
               'own_mro_real_time': sorted(own_rt)},
              open('/tmp/passo0_escopo.json', 'w'), ensure_ascii=False, indent=2)
    print("\nJSON salvo em /tmp/passo0_escopo.json")


if __name__ == '__main__':
    main()
