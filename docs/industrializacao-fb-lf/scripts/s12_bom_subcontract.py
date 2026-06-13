#!/usr/bin/env python3
"""S12 — cria a BoM SUBCONTRACT do shoyu 4870112 (GATILHO da expansao 5902 no
faturamento — GATE 1 provou que falta). Espelha a BoM 14794 do azeite.

REVERSIVEL (--revert): cadastro de TESTE para o GATE 1; desfazer no final (pedido Rafael).
A decisao de torna-la permanente (piloto real / rollout) e separada.

Estrutura (= 14794): template 42282, type=subcontract, company FB=1, subcontractor=LF=35,
product_qty=1, uom=160 CAIXAS, consumption=warning. Linhas = os 16 componentes de
TERCEIROS da remessa RPI/2026/00245 (735679) com as qtys reais (= invariante 5902=5901).

MODOS:
  (sem flag)   dry-run: mostra a BoM que sera criada (16 linhas da remessa)
  --confirmar  cria a BoM subcontract (idempotente: pula se ja existe)
  --revert     deleta a BoM subcontract criada por nos (type=subcontract, tmpl 42282, FB)
  --validar    confere a BoM + nº de linhas
"""
import sys
import argparse
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CTX = {'allowed_company_ids': [1, 5], 'company_id': 1}  # BoM nasce na FB
SHOYU_TMPL = 42282        # [4870112] MOLHO SHOYU
FB, LF = 1, 35            # company FB=1 ; subcontractor partner LF=35
UOM_CAIXAS = 160
RPI_PILOTO = 735679       # remessa: fonte dos 16 componentes + qtys


def m2o(v):
    return f"{v[0]}|{v[1]}" if isinstance(v, list) and len(v) == 2 and isinstance(v[1], str) else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--validar', action='store_true')
    args = ap.parse_args()

    o = get_odoo_connection(); assert o.authenticate(), "FALHA AUTH"

    def rr(model, domain, fields, **kw):
        kw2 = {'fields': fields, 'context': CTX}; kw2.update(kw)
        return o.execute_kw(model, 'search_read', [domain], kw2)

    def find_bom():
        r = rr('mrp.bom', [('product_tmpl_id', '=', SHOYU_TMPL), ('type', '=', 'subcontract'),
                           ('company_id', '=', FB)], ['id', 'product_qty'])
        return r[0] if r else None

    # componentes da remessa (product_id, qty) — a fonte
    comps = rr('account.move.line', [('move_id', '=', RPI_PILOTO), ('display_type', '=', 'product')],
               ['product_id', 'quantity'])
    comp_pairs = [(c['product_id'][0], c['quantity']) for c in comps]

    # ---------- VALIDAR ----------
    if args.validar:
        b = find_bom()
        if not b:
            print("BoM subcontract do shoyu: NAO existe"); return
        nl = o.execute_kw('mrp.bom.line', 'search_count', [[('bom_id', '=', b['id'])]], {'context': CTX})
        print(f"BoM subcontract shoyu id={b['id']} product_qty={b['product_qty']} linhas={nl} "
              f"(esperado {len(comp_pairs)}) -> {'OK' if nl == len(comp_pairs) else 'DIVERGE'}")
        return

    # ---------- REVERT ----------
    if args.revert:
        b = find_bom()
        if not b:
            print("BoM subcontract do shoyu: nao existe (nada a reverter)"); return
        o.execute_kw('mrp.bom', 'unlink', [[b['id']]], {'context': CTX})
        print(f"BoM subcontract {b['id']} DELETADA")
        return

    # ---------- DRY-RUN / EXECUTAR ----------
    b = find_bom()
    print("=" * 80)
    print("S12 — BoM SUBCONTRACT do shoyu 4870112 (espelha azeite 14794)")
    print("=" * 80)
    if b:
        print(f"  JA EXISTE: id={b['id']} — pulando (idempotente)")
    print(f"  template={SHOYU_TMPL} type=subcontract company=FB({FB}) subcontractor=LF({LF}) "
          f"product_qty=1 uom={UOM_CAIXAS}")
    print(f"  {len(comp_pairs)} componentes (da remessa {RPI_PILOTO}):")
    for pid, qty in comp_pairs:
        print(f"    prod {pid:6} qty={qty}")

    if not args.confirmar:
        print("\n  [DRY-RUN] nada escrito. Com 'go': --confirmar  (desfaz com --revert)")
        return
    if b:
        print(f"\n  ja existe (id={b['id']}); nada a criar."); return

    vals = {
        'product_tmpl_id': SHOYU_TMPL, 'type': 'subcontract', 'company_id': FB,
        'subcontractor_ids': [(6, 0, [LF])], 'product_qty': 1.0, 'product_uom_id': UOM_CAIXAS,
        'consumption': 'warning',
        'bom_line_ids': [(0, 0, {'product_id': pid, 'product_qty': qty}) for pid, qty in comp_pairs],
    }
    bid = o.execute_kw('mrp.bom', 'create', [vals], {'context': CTX})
    print(f"\n  BoM subcontract CRIADA: id={bid}")
    print(f"  >>> valide com --validar ; desfaca com --revert")


if __name__ == '__main__':
    main()
