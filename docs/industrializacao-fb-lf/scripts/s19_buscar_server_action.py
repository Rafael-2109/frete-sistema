#!/usr/bin/env python3
"""S19 — CACAR a server action (ou metodo/botao) que ABRE os componentes 5902 na NF.
Hipotese do Rafael: existe uma SA que explode a MO/BoM e cria as linhas 5902 — e o
padrao atual; a operadora (Josefa/Histaina) a dispara (9-16 linhas no MESMO timestamp).

READ-ONLY. Zero escrita. Mapeia:
  1. ir.actions.server com binding em account.move / stock.picking / mrp.production
     (= aparecem no menu "Acoes" do registro — o que a operadora clicaria)
  2. ir.actions.server cujo CODE toca bom/mrp/5902/2864/invoice_line/operacao
  3. le o CODE completo das candidatas mais provaveis
  4. botoes na view form do account.move que chamam metodos (object/action)

MODOS (sem args = 1-3; --views inclui 4):
  --bind          SAs com binding nos 3 modelos
  --code          SAs cujo code casa as keywords (+ dump do code das top)
  --dump ID       dump do code completo de UMA server action
  --views         botoes na view form do account.move
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 5, 'lang': 'pt_BR'}
KW = ['bom_line', 'mrp.production', 'mrp.bom', "5902", "2864", 'invoice_line_ids',
      'l10n_br_operacao', 'product_tmpl', 'component', 'bom_id', 'explode']
ALVO_MODELS = ['account.move', 'stock.picking', 'mrp.production']


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def model_ids(o):
    rows = o.execute_kw('ir.model', 'search_read', [[('model', 'in', ALVO_MODELS)]],
                        {'fields': ['id', 'model'], 'context': CTX})
    return {r['model']: r['id'] for r in rows}, [r['id'] for r in rows]


def dump_bind(o):
    print("=" * 88)
    print("=== 1) ir.actions.server com BINDING em account.move/stock.picking/mrp.production ===")
    _, mids = model_ids(o)
    rows = o.execute_kw('ir.actions.server', 'search_read',
                        [[('binding_model_id', 'in', mids)]],
                        {'fields': ['id', 'name', 'state', 'usage', 'model_id', 'binding_model_id'],
                         'context': CTX, 'order': 'binding_model_id,name'})
    if not rows:
        print("   (nenhuma SA com binding nesses modelos)")
    for r in rows:
        print(f"   SA {r['id']:5} [{r['state']:8}] bind={m2o(r['binding_model_id'])[:26]:26} "
              f"model={m2o(r['model_id'])[:20]:20} | {r['name'][:48]}")
    return rows


def dump_code(o, full_top=6):
    print("\n" + "=" * 88)
    print("=== 2) ir.actions.server cujo CODE casa keywords (bom/mrp/5902/2864/operacao/...) ===")
    seen = {}
    for kw in KW:
        rows = o.execute_kw('ir.actions.server', 'search_read',
                            [[('state', '=', 'code'), ('code', 'like', kw)]],
                            {'fields': ['id', 'name', 'model_id', 'binding_model_id'],
                             'context': CTX, 'limit': 60})
        for r in rows:
            seen.setdefault(r['id'], {'r': r, 'kw': set()})['kw'].add(kw)
    if not seen:
        print("   (nenhuma SA com code casando as keywords)")
        return []
    ranked = sorted(seen.values(), key=lambda x: (-len(x['kw']), x['r']['id']))
    for it in ranked:
        r = it['r']
        print(f"   SA {r['id']:5} model={m2o(r['model_id'])[:22]:22} kw={sorted(it['kw'])} | {r['name'][:46]}")
    print(f"\n   --- CODE das top {full_top} candidatas ---")
    for it in ranked[:full_top]:
        rid = it['r']['id']
        full = o.execute_kw('ir.actions.server', 'read', [[rid]],
                            {'fields': ['name', 'code', 'model_id', 'binding_model_id'], 'context': CTX})[0]
        print("\n" + "-" * 84)
        print(f"### SA {rid} — {full['name']}  (model={m2o(full['model_id'])} bind={m2o(full.get('binding_model_id'))})")
        print("-" * 84)
        print(full.get('code') or '(sem code)')
    return ranked


def dump_one(o, sid):
    full = o.execute_kw('ir.actions.server', 'read', [[sid]],
                        {'fields': ['name', 'code', 'model_id', 'binding_model_id', 'state', 'usage'],
                         'context': CTX})
    if not full:
        print(f"   SA {sid} nao encontrada"); return
    f = full[0]
    print("=" * 88)
    print(f"### SA {sid} — {f['name']}")
    print(f"   model={m2o(f['model_id'])} bind={m2o(f.get('binding_model_id'))} state={f['state']} usage={f.get('usage')}")
    print("=" * 88)
    print(f.get('code') or '(sem code)')


def dump_views(o):
    print("\n" + "=" * 88)
    print("=== 4) botoes <button> na view form do account.move (object/action) ===")
    views = o.execute_kw('ir.ui.view', 'search_read',
                         [[('model', '=', 'account.move'), ('type', '=', 'form')]],
                         {'fields': ['id', 'name', 'arch_db'], 'context': CTX, 'limit': 80})
    import re
    hit = 0
    for v in views:
        arch = v.get('arch_db') or ''
        for m in re.finditer(r'<button[^>]*name="([^"]+)"[^>]*>', arch):
            nm = m.group(1)
            seg = m.group(0)
            low = (nm + seg).lower()
            if any(k in low for k in ['bom', 'compon', 'insum', 'retorno', 'industr', 'explod', '5902', 'material']):
                hit += 1
                print(f"   view {v['id']} ({v['name'][:34]}): button name={nm} :: {seg[:90]}")
    if not hit:
        print("   (nenhum botao com nome relacionado a componente/bom/retorno)")
    # 4b: TODOS os metodos object/action chamados por botoes (label generico)
    print("\n   --- TODOS os botoes name= (type object/action) na view form account.move ---")
    metodos = set()
    for v in views:
        arch = v.get('arch_db') or ''
        for m in re.finditer(r'<button[^>]*\bname="([^"]+)"', arch):
            metodos.add(m.group(1))
    for nm in sorted(metodos):
        flag = ''
        low = nm.lower()
        if any(k in low for k in ['retor', 'compon', 'insum', 'industr', 'gera', 'add', 'criar',
                                  'explod', 'material', 'devol', 'linha', 'product', 'bom']):
            flag = '   <<< SUSPEITO'
        print(f"      {nm}{flag}")


def dump_nome(o):
    print("\n" + "=" * 88)
    print("=== 5) ir.actions.server por NOME (qualquer state) — termos de componente/retorno ===")
    termos = ['component', 'insumo', 'retorno', 'industr', 'kit', 'explod', 'material',
              'devolu', 'remessa', '5902', 'compoe', 'compõe', 'abrir', 'abre']
    seen = {}
    for t in termos:
        rows = o.execute_kw('ir.actions.server', 'search_read', [[('name', 'ilike', t)]],
                            {'fields': ['id', 'name', 'state', 'model_id', 'binding_model_id'],
                             'context': CTX, 'limit': 60})
        for r in rows:
            seen.setdefault(r['id'], r)
    if not seen:
        print("   (nenhuma SA com nome casando os termos)")
    for r in sorted(seen.values(), key=lambda x: x['id']):
        print(f"   SA {r['id']:5} [{r['state']:8}] model={m2o(r['model_id'])[:22]:22} "
              f"bind={m2o(r.get('binding_model_id'))[:18]:18} | {r['name'][:42]}")


def dump_auto(o):
    print("\n" + "=" * 88)
    print("=== 6) base.automation (automated actions) em account.move/picking/MO ===")
    _, mids = model_ids(o)
    af = o.execute_kw('base.automation', 'fields_get', [], {'attributes': ['type'], 'context': CTX})
    awant = [f for f in ['name', 'model_id', 'trigger', 'active', 'state', 'filter_domain',
                         'action_server_id', 'action_server_ids', 'trigger_field_ids'] if f in af]
    rows = o.execute_kw('base.automation', 'search_read',
                        [[('model_id', 'in', mids)]],
                        {'fields': awant, 'context': dict(CTX, active_test=False)})
    if not rows:
        print("   (nenhuma automated action nesses modelos)")
    for r in rows:
        sids = []
        if r.get('action_server_id'):
            sids = [r['action_server_id'][0]]
        sids += (r.get('action_server_ids') or [])
        print(f"   AUTO {r['id']} active={r.get('active')} model={m2o(r['model_id'])[:18]:18} "
              f"trigger={r.get('trigger')} SA={sids} | {r['name'][:40]}")
        for sid in sids:
            sa = o.execute_kw('ir.actions.server', 'read', [[sid]],
                              {'fields': ['name', 'code'], 'context': CTX})
            if sa:
                code = sa[0].get('code') or ''
                low = code.lower()
                if any(k in low for k in ['5902', '2864', 'bom', 'invoice_line', 'operacao', 'move_raw']):
                    print(f"       >>> SA {sid} ({sa[0]['name']}) CODE TOCA COMPONENTE/FATURA:")
                    print("       " + code.replace('\n', '\n       ')[:1200])


def dump_wizard(o):
    print("\n" + "=" * 88)
    print("=== 7) ACOES/WIZARDS (act_window) e modelos transient ligados a componente/industrializa ===")
    aw = o.execute_kw('ir.actions.act_window', 'search_read',
                      [['|', '|', '|', '|', '|',
                        ('name', 'ilike', 'component'), ('name', 'ilike', 'insumo'),
                        ('name', 'ilike', 'industr'), ('name', 'ilike', 'retorno'),
                        ('name', 'ilike', 'material'), ('name', 'ilike', 'explod')]],
                      {'fields': ['id', 'name', 'res_model', 'binding_model_id'], 'context': CTX, 'limit': 40})
    if not aw:
        print("   (nenhum act_window com nome relacionado)")
    for a in aw:
        print(f"   act_window {a['id']} res_model={a.get('res_model'):28} bind={m2o(a.get('binding_model_id'))[:16]:16} | {a['name'][:36]}")
    # modelos transient (wizards) que referenciam account.move/mrp e componente
    tm = o.execute_kw('ir.model', 'search_read',
                      [['|', '|', '|',
                        ('model', 'ilike', 'component'), ('model', 'ilike', 'industr'),
                        ('model', 'ilike', 'retorno'), ('model', 'ilike', 'insumo')]],
                      {'fields': ['id', 'model', 'name', 'transient'], 'context': CTX, 'limit': 40})
    print("   --- ir.model com nome de componente/industrializa ---")
    if not tm:
        print("   (nenhum)")
    for m in tm:
        print(f"   model {m['model']:42} transient={m.get('transient')} | {m['name'][:34]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bind', action='store_true')
    ap.add_argument('--code', action='store_true')
    ap.add_argument('--dump', type=int, metavar='SA_ID')
    ap.add_argument('--views', action='store_true')
    ap.add_argument('--nome', action='store_true')
    ap.add_argument('--auto', action='store_true')
    ap.add_argument('--wizard', action='store_true')
    args = ap.parse_args()

    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"

    if args.dump:
        dump_one(o, args.dump); return
    todos = not (args.bind or args.code or args.views or args.nome or args.auto)
    if todos or args.bind:
        dump_bind(o)
    if todos or args.code:
        dump_code(o)
    if todos or args.nome:
        dump_nome(o)
    if todos or args.auto:
        dump_auto(o)
    if args.views:
        dump_views(o)
    if args.wizard:
        dump_wizard(o)


if __name__ == '__main__':
    main()
