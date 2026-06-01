#!/usr/bin/env python3
"""
PASSO E — MO de industrializacao na LF (consome 31092 terceiros -> produz 31093). DRY-RUN-FIRST.

2 MOs em cascata (BoM 3695 PA -> 3646 BATELADA semi):
  BATELADA: BoM 3646 -> 12,818 kg de 3800018; consome 8 quimicos+shoyu (31092) + AGUA (consu); produz em 31092.
  PA:       BoM 3695 -> 1 cx de 4870112; consome 7 embalagens + 12,818 semi (31092); produz em 31093.

Invariante (SOT Etapa 3): LF so' agrega AGUA(consu)+servico; nunca product proprio. PA em 31093.

Modos (gated; cada --execute = 1 comando):
  (default DRY-RUN)         plano das 2 MOs + locations. NAO escreve.
  --modo batelada --execute cria+confirma+reserva+produz MO BATELADA (semi 3800018 -> 31092).
  --modo pa --mo-semi <id> --execute  idem MO PA (4870112 -> 31093).

Validar: e2e_piloto_validar.py --modo mo --mo <batelada> --mo2 <pa> --base /tmp/piloto_base.json
"""
import argparse
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

COMPANY_FB, COMPANY_LF = 1, 5
LOTE = 'PILOTO-3105'
LOC_TERCEIROS, LOC_PA_TERCEIROS = 31092, 31093
PT_PRODUCAO = 36            # LF: Produção
BOM_PA, BOM_BAT = 3695, 3646
PROD_PA, PROD_SEMI = 27834, 29986   # 4870112 / 3800018
SEMI_CODE = '3800018'
QTD_CAIXA = 1.0


def ctx_lf():
    return {'allowed_company_ids': [COMPANY_FB, COMPANY_LF], 'company_id': COMPANY_LF}


def sec(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def qtd_semi_por_caixa(o):
    """12,818 — qty de 3800018 que a BoM 3695 consome por caixa."""
    bl = o.execute_kw('mrp.bom.line', 'search_read', [[('bom_id', '=', BOM_PA), ('product_id', '=', PROD_SEMI)], ['product_qty']], {'context': ctx_lf()})
    rende = float(o.execute_kw('mrp.bom', 'read', [[BOM_PA], ['product_qty']], {'context': ctx_lf()})[0]['product_qty'] or 1.0)
    return (bl[0]['product_qty'] if bl else 0.0) * (QTD_CAIXA / rende)


def show_mo(o, mo_id, label='MO'):
    mo = o.execute_kw('mrp.production', 'read', [[mo_id], ['name', 'state', 'product_id', 'product_qty', 'location_src_id', 'location_dest_id']], {'context': ctx_lf()})[0]
    print(f"  {label} {mo_id}: {mo['name']} state={mo['state']} produz {mo['product_id'][1][:24]} qty={mo['product_qty']} src={mo['location_src_id']} dst={mo['location_dest_id']}")
    for r in o.execute_kw('stock.move', 'search_read', [[('raw_material_production_id', '=', mo_id)], ['product_id', 'product_qty', 'location_id', 'state']], {'context': ctx_lf(), 'limit': 30}):
        print(f"      consome {r['product_id'][1][:24]:24} qty={r['product_qty']:>10} de loc{r['location_id'][0] if r['location_id'] else '?'} ({r['state']})")
    for f in o.execute_kw('stock.move', 'search_read', [[('production_id', '=', mo_id), ('raw_material_production_id', '=', False)], ['product_id', 'product_qty', 'location_dest_id', 'state']], {'context': ctx_lf(), 'limit': 10}):
        print(f"      PRODUZ  {f['product_id'][1][:24]:24} qty={f['product_qty']:>10} -> loc{f['location_dest_id'][0] if f['location_dest_id'] else '?'} ({f['state']})")
    return mo


def resolver_lot_producing(o, product_id):
    ex = o.execute_kw('stock.lot', 'search_read', [[('name', '=', LOTE), ('product_id', '=', product_id), ('company_id', '=', COMPANY_LF)], ['id']], {'context': ctx_lf()})
    return ex[0]['id'] if ex else o.execute_kw('stock.lot', 'create', [{'name': LOTE, 'product_id': product_id, 'company_id': COMPANY_LF}], {'context': ctx_lf()})


def criar_e_produzir(o, *, product_id, bom_id, qty, loc_src, loc_dst, label):
    """Cria MO + confirma + reserva + seta lote produzido + mark_done. Retorna mo_id."""
    mo_id = o.execute_kw('mrp.production', 'create', [{
        'product_id': product_id, 'product_qty': qty, 'bom_id': bom_id,
        'location_src_id': loc_src, 'location_dest_id': loc_dst,
        'picking_type_id': PT_PRODUCAO, 'company_id': COMPANY_LF,
    }], {'context': ctx_lf()})
    print(f"  [criada] MO {label} id={mo_id}")
    o.execute_kw('mrp.production', 'action_confirm', [[mo_id]], {'context': ctx_lf()})
    # forcar location_src/dst nos raw moves + finished move (override pt36)
    raws = o.execute_kw('stock.move', 'search', [[('raw_material_production_id', '=', mo_id)]], {'context': ctx_lf()})
    if raws:
        o.execute_kw('stock.move', 'write', [raws, {'location_id': loc_src}], {'context': ctx_lf()})
    fins = o.execute_kw('stock.move', 'search', [[('production_id', '=', mo_id), ('raw_material_production_id', '=', False)]], {'context': ctx_lf()})
    if fins:
        o.execute_kw('stock.move', 'write', [fins, {'location_dest_id': loc_dst}], {'context': ctx_lf()})
    o.execute_kw('mrp.production', 'action_assign', [[mo_id]], {'context': ctx_lf()})
    # alinhar demanda dos raws ao RESERVADO (rounding: demanda BoM 6dp > estoque 4dp -> evita wizard de consumo)
    for rm in o.execute_kw('stock.move', 'search_read', [[('raw_material_production_id', '=', mo_id)], ['id', 'product_uom_qty']], {'context': ctx_lf()}):
        mls = o.execute_kw('stock.move.line', 'search_read', [[('move_id', '=', rm['id'])], ['quantity']], {'context': ctx_lf()})
        reservado = sum(m['quantity'] for m in mls)
        # consu (AGUA) reserva infinito; so alinhar quando reservado < demanda (partial real)
        if 0 < reservado < rm['product_uom_qty'] - 1e-9:
            o.execute_kw('stock.move', 'write', [[rm['id']], {'product_uom_qty': reservado}], {'context': ctx_lf()})
    # seta lote produzido + qty_producing
    lot_prod = resolver_lot_producing(o, product_id)
    o.execute_kw('mrp.production', 'write', [[mo_id], {'lot_producing_id': lot_prod, 'qty_producing': qty}], {'context': ctx_lf()})

    # ===== FIX G-ENT-10 (2026-06-01): APONTAR consumo ANTES do mark_done =====
    # Causa raiz (investigada ao vivo): action_assign cria stock.move.line com quantity=reservado
    # mas picked=False. O wizard mrp.consumption.warning.action_confirm dispara
    # button_mark_done(skip_consumption=True) que, com picked=False, interpreta "nada apontado"
    # e CANCELA os raws (qty_done=0) -> producao fantasma (MOs 20235/36/38/39).
    # Ground-truth: MO boa LF/MO/03510 (20216) tem todas as raws move.line com picked=True +
    # quantity>0 + lote. Fix = setar picked=True nas move.lines dos raws (e no move) ANTES do done.
    # [ASSUNCAO - CONFIRMAR no piloto via POS-CHECK abaixo; rodar 1 MO BATELADA primeiro.]
    raws_apontados, raws_sem_ml = [], []
    for rm in o.execute_kw('stock.move', 'search_read',
                           [[('raw_material_production_id', '=', mo_id), ('state', 'not in', ['done', 'cancel'])],
                            ['id', 'product_id', 'product_uom_qty']], {'context': ctx_lf()}):
        mls = o.execute_kw('stock.move.line', 'search', [[('move_id', '=', rm['id'])]], {'context': ctx_lf()})
        if mls:
            o.execute_kw('stock.move.line', 'write', [mls, {'picked': True}], {'context': ctx_lf()})
            o.execute_kw('stock.move', 'write', [[rm['id']], {'picked': True}], {'context': ctx_lf()})
            raws_apontados.append(rm['id'])
        else:
            raws_sem_ml.append((rm['id'], rm['product_id'][1] if rm['product_id'] else '?'))
    print(f"  [FIX G-ENT-10] picked=True em {len(raws_apontados)} raws; SEM move.line (verificar): {raws_sem_ml}")
    show_mo(o, mo_id, label + ' (pre-done, picked aplicado)')

    # mark done — com picked=True, o wizard de consumo (rounding) deve CONSUMIR, nao cancelar
    try:
        res = o.execute_kw('mrp.production', 'button_mark_done', [[mo_id]], {'context': dict(ctx_lf(), skip_backorder=True)})
        if isinstance(res, dict) and res.get('res_model') == 'mrp.consumption.warning':
            # confirmar wizard de consumo (com picked=True ja apontado, consome o reservado)
            wiz = o.execute_kw('mrp.consumption.warning', 'create', [{'mrp_production_ids': [(6, 0, [mo_id])]}], {'context': ctx_lf()})
            o.execute_kw('mrp.consumption.warning', 'action_confirm', [[wiz]], {'context': ctx_lf()})
            print("  [wizard consumo confirmado]")
    except Exception as e:
        if 'cannot marshal None' not in str(e):
            print(f"  [aviso button_mark_done] {str(e)[:300]}")
    st = o.execute_kw('mrp.production', 'read', [[mo_id], ['state']], {'context': ctx_lf()})[0]['state']
    print(f"  MO {label} state={st}")

    # ===== POS-CHECK anti-falso-sucesso (G-ENT-10): os raws CONSUMIRAM de verdade? =====
    raws_pos = o.execute_kw('stock.move', 'search_read',
                            [[('raw_material_production_id', '=', mo_id)],
                             ['product_id', 'state', 'quantity']], {'context': ctx_lf()})
    n_cancel = sum(1 for r in raws_pos if r['state'] == 'cancel')
    n_consumido = sum(1 for r in raws_pos if r['state'] == 'done' and r['quantity'] > 1e-9)
    if n_cancel:
        print(f"  *** POS-CHECK FALHA G-ENT-10: {n_cancel} raws CANCELADOS (produziu sem consumir). "
              f"NAO prosseguir; investigar mecanismo de apontamento.")
        for r in raws_pos:
            if r['state'] == 'cancel':
                print(f"        CANCELADO: {r['product_id'][1][:30]} qty={r['quantity']}")
    else:
        print(f"  POS-CHECK OK: {n_consumido} raws consumidos (state=done, qty>0); 0 cancelados.")
    return mo_id, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--modo', default='dry-run', choices=['dry-run', 'batelada', 'pa'])
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--mo-semi', type=int, help='id da MO BATELADA (p/ --modo pa)')
    args = ap.parse_args()
    o = get_odoo_connection(); o.authenticate()

    q_semi = qtd_semi_por_caixa(o)

    if args.modo == 'dry-run':
        sec("PASSO E — MO LF (31092 -> 31093) — DRY-RUN")
        print(f"  MO BATELADA: BoM {BOM_BAT} -> {q_semi:.4f} kg de {SEMI_CODE}; src=31092 dst=31092 (consu AGUA incl.)")
        print(f"  MO PA:       BoM {BOM_PA} -> {QTD_CAIXA} cx de 4870112; src=31092 dst=31093 (consome semi {q_semi:.4f})")
        print(f"  Invariante: LF so' agrega AGUA(consu)+servico; PA -> 31093.")
        print(f"  Proximo: --modo batelada --execute")
        return 0

    if args.modo == 'batelada':
        sec(f"MO BATELADA — {SEMI_CODE} {q_semi:.4f} kg (src=31092 dst=31092)")
        if not args.execute:
            print("  DRY: rode com --execute."); return 0
        mo_id, st = criar_e_produzir(o, product_id=PROD_SEMI, bom_id=BOM_BAT, qty=round(q_semi, 6),
                                     loc_src=LOC_TERCEIROS, loc_dst=LOC_TERCEIROS, label='BATELADA')
        print(f"  Proximo: --modo pa --mo-semi {mo_id} --execute")
        return 0

    if args.modo == 'pa':
        sec("MO PA — 4870112 1 cx (src=31092 dst=31093)")
        if not args.execute:
            print("  DRY: rode com --execute."); return 0
        mo_id, st = criar_e_produzir(o, product_id=PROD_PA, bom_id=BOM_PA, qty=QTD_CAIXA,
                                     loc_src=LOC_TERCEIROS, loc_dst=LOC_PA_TERCEIROS, label='PA')
        print(f"  VALIDAR: e2e_piloto_validar.py --modo mo --mo {args.mo_semi or '<bat>'} --mo2 {mo_id} --base /tmp/piloto_base.json")
        return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
