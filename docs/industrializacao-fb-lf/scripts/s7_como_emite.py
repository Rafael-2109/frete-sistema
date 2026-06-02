#!/usr/bin/env python3
"""S7 COMO A NF DE RETORNO E' MONTADA (READ-only) — responde: o operador digita os
insumos (5902) componente-a-componente, ou o sistema os compoe automaticamente?

Investiga:
  1. picking da VND real (322836): origin, group_id, sale_id, create_uid, moves (todos states)
     -> o picking traz so o PA (1 move) ou os insumos tambem?
  2. server action 1512 "CIEL IT: Robo Faturamento": le o `code` -> como compoe as linhas
     5902 (procura: 5902/insumo/retorno/industri/invoice_line/_prepare/_get_invoice).
  3. de onde vem o picking pt66 (operador cria? MO? remessa?).

NAO escreve nada. Salva o code do robo em /tmp/s7_robo_1512.txt p/ leitura.
"""
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5]}


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and v else ('-' if not v else str(v))


def main():
    o = get_odoo_connection()
    assert o.authenticate(), "FALHA AUTH"
    print(f"UID {o._uid}")

    def rr(model, domain, fields, **kw):
        return o.execute_kw(model, 'search_read', [domain], {'fields': fields, 'context': CTX, **kw})

    def rd(model, ids, fields):
        return o.execute_kw(model, 'read', [list(ids)], {'fields': fields, 'context': CTX}) if ids else []

    # ----------------------------------------------------------------
    # 1) PICKING da VND (322836) — origem e moves
    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("1) PICKING 322836 (origem da VND/2026/00359) — quem cria e com quantas linhas")
    print("=" * 88)
    pkflds = ['id', 'name', 'state', 'origin', 'group_id', 'sale_id', 'create_uid', 'create_date',
              'picking_type_id', 'location_id', 'location_dest_id', 'backorder_id']
    pk = rd('stock.picking', [322836], pkflds)
    if pk:
        for k in pkflds:
            v = pk[0].get(k)
            print(f"  {k:22} = {m2o(v) if isinstance(v, list) else v}")
    # TODOS os moves (qualquer state)
    sm = rr('stock.move', [('picking_id', '=', 322836)],
            ['id', 'product_id', 'quantity', 'product_uom_qty', 'state'], limit=200)
    print(f"\n  TODOS os stock.move do picking ({len(sm)}):")
    for s in sm:
        print(f"    move {s['id']} {m2o(s.get('product_id'))[:30]:30} qty={s.get('quantity')} "
              f"uom_qty={s.get('product_uom_qty')} state={s.get('state')}")

    # ----------------------------------------------------------------
    # 2) SERVER ACTION 1512 — o robo
    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("2) SERVER ACTION 1512 (CIEL IT: Robo Faturamento) — code")
    print("=" * 88)
    sa = rd('ir.actions.server', [1512], ['id', 'name', 'model_id', 'state', 'usage', 'code'])
    if sa:
        sa = sa[0]
        print(f"  name={sa.get('name')} model={m2o(sa.get('model_id'))} state={sa.get('state')} usage={sa.get('usage')}")
        code = sa.get('code') or ''
        with open('/tmp/s7_robo_1512.txt', 'w') as f:
            f.write(code)
        print(f"  code: {len(code)} chars -> salvo em /tmp/s7_robo_1512.txt")
        # grep das linhas-chave
        chaves = ['5902', '5124', 'insumo', 'retorno', 'industri', 'invoice_line', '_prepare',
                  '_get_invoice', 'move_line', 'remessa', 'devol', 'simbol', 'l10n_br_operacao',
                  'create', 'tipo_pedido', 'journal']
        print("\n  --- linhas do code contendo palavras-chave ---")
        for i, ln in enumerate(code.splitlines(), 1):
            low = ln.lower()
            if any(c in low for c in chaves):
                print(f"   L{i:4}: {ln.strip()[:120]}")

    # ----------------------------------------------------------------
    # 3) outras server actions / metodos de composicao de retorno
    # ----------------------------------------------------------------
    print("\n" + "=" * 88)
    print("3) server actions com '5902'/'retorno'/'industri' no code ou nome")
    print("=" * 88)
    sas = rr('ir.actions.server', [], ['id', 'name', 'model_id', 'state'], limit=400)
    achadas = [s for s in sas if any(k in (s.get('name') or '').lower()
               for k in ('retorno', 'industri', 'fatur', 'devol'))]
    for s in achadas[:25]:
        print(f"   id={s['id']:5} model={m2o(s.get('model_id'))[:28]:28} | {s.get('name')}")

    print("\n[FIM s7_como_emite — READ-only]")


if __name__ == '__main__':
    main()
