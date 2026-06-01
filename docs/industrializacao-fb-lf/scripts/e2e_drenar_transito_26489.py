#!/usr/bin/env python3
"""
DRENO do transito 26489 -> 30720 (lado FB da remessa do piloto). DRY-RUN-FIRST.

Refaz o companheiro nativo "Transferir TERCEIROS" (322400, CANCELADO no Gate 1 do Model A)
como picking manual pt5 (FB: Transferencias Internas), movendo os 16 comps FB-lote
PILOTO-3105 de 26489 (Em Transito Industrializacao, transit) -> 30720 (Parceiros/Estoques
em poder de terceiros/LF, customer). Zera o lado fisico FB da remessa.

IMPACTO CONTABIL = ZERO (verificado ao vivo: 10 moves done 26489->30720 historicos geraram
0 SVL; 26489 transit cmp=False, 30720 customer cmp=False -> nenhuma e' valued p/ a FB; contas
1150200001/002 tem 0 linhas). Operacao puramente fisica.

METODO: picking manual pt5 (NAO re-disparar server action 1899) porque:
  - a remessa 322399 ja tem picking_terceiro_id=322400 (cancel) -> re-disparar e' nao-deterministico;
  - o companheiro nativo nasce 'assigned' e NUNCA e' validado no fluxo real (por isso 26489 nunca
    zera); o piloto PRECISA de 'done'. Picking manual + button_validate e' deterministico e
    replica a estrutura ja verificada do 322400 (16 moves 26489->30720, qtys exatas).

Padrao battle-tested herdado de e2e_remessa_criar.py (G-REM-4): move.line com lot_id PINADO
(sem action_assign/FIFO), grava quantity E qty_done juntos, button_validate com skip_backorder.

Uso:
  python e2e_drenar_transito_26489.py                 # plano (DRY-RUN, nada escrito)
  python e2e_drenar_transito_26489.py --execute       # cria picking pt5 + valida -> done (+ POS-CHECK)
"""
import argparse
import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')
from app.odoo.utils.connection import get_odoo_connection

CMP_FB = 1
PT_INT = 5                      # FB: Transferencias Internas (FB) — mesmo pt do companheiro nativo
LOC_T, LOC_3OS = 26489, 30720   # Em Transito (transit) -> Estoques em poder de terceiros/LF (customer)
LOTE = 'PILOTO-3105'
REMESSA = 322399                # FB/SAI/IND/01612 (done)
REF_COMP = 322400               # companheiro nativo CANCELADO (referencia de estrutura)
SOMA_ESPERADA = 42.28994948
TOL = 1e-6


def ctx_fb():
    return {'allowed_company_ids': [CMP_FB], 'company_id': CMP_FB}


def write_done(o, ml_id, qty):
    """grava qtd feita em quantity E qty_done juntos (CIEL IT v17). True se ok."""
    try:
        o.execute_kw('stock.move.line', 'write', [[ml_id], {'quantity': qty, 'qty_done': qty}], {'context': ctx_fb()})
        return True
    except Exception:
        for field in ('quantity', 'qty_done'):
            try:
                o.execute_kw('stock.move.line', 'write', [[ml_id], {field: qty}], {'context': ctx_fb()})
                return True
            except Exception:
                continue
    return False


def resolver_quants(o):
    """Os 16 quants do lote PILOTO-3105 (company FB=1) em 26489. lot company=1 (60496-60511)."""
    lots = o.search_read('stock.lot', [('name', 'ilike', LOTE), ('company_id', '=', CMP_FB)],
                         ['id', 'product_id'], limit=40)
    lot_ids = [l['id'] for l in lots]
    qs = o.search_read('stock.quant',
                       [('location_id', '=', LOC_T), ('lot_id', 'in', lot_ids)],
                       ['product_id', 'lot_id', 'quantity', 'reserved_quantity'], limit=60)
    out = []
    pcodes = {p['id']: p['default_code'] for p in o.search_read(
        'product.product', [('id', 'in', [q['product_id'][0] for q in qs])], ['default_code'])}
    for q in qs:
        out.append({'pid': q['product_id'][0], 'cod': pcodes.get(q['product_id'][0], '?'),
                    'nome': q['product_id'][1][:30], 'lot_id': q['lot_id'][0], 'lote_nm': q['lot_id'][1],
                    'qty': q['quantity'], 'reserved': q['reserved_quantity']})
    # uom por produto
    uoms = {p['id']: (p['uom_id'][0] if p['uom_id'] else 1) for p in o.search_read(
        'product.product', [('id', 'in', [x['pid'] for x in out])], ['uom_id'])}
    for x in out:
        x['uom'] = uoms.get(x['pid'], 1)
    return sorted(out, key=lambda x: x['cod'] or '')


def soma_lote_em(o, loc):
    lots = o.search_read('stock.lot', [('name', 'ilike', LOTE), ('company_id', '=', CMP_FB)], ['id'], limit=40)
    lot_ids = [l['id'] for l in lots]
    qs = o.search_read('stock.quant', [('location_id', '=', loc), ('lot_id', 'in', lot_ids)], ['quantity'], limit=60)
    return sum(q['quantity'] for q in qs), len(qs)


def achar_orfaos(o):
    """Pickings pt5 de dreno de execucoes anteriores NAO finalizados (orfaos a limpar).
    Identifica pelo origin 'DRENO-PILOTO%' + rota 26489->30720; exclui done/cancel."""
    return o.execute_kw('stock.picking', 'search_read',
        [[('picking_type_id', '=', PT_INT), ('location_id', '=', LOC_T),
          ('location_dest_id', '=', LOC_3OS), ('origin', 'like', 'DRENO-PILOTO%'),
          ('state', 'not in', ['done', 'cancel'])],
         ['id', 'name', 'state', 'origin']], {'context': ctx_fb(), 'limit': 20})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true')
    args = ap.parse_args()
    DRY = not args.execute
    o = get_odoo_connection(); o.authenticate()

    print("=" * 100)
    print(f"DRENO 26489 -> 30720 (lado FB) — lote {LOTE} — {'DRY-RUN' if DRY else 'EXECUTE'}")
    print("=" * 100)

    # -------- pre-checks de seguranca
    rem = o.execute_kw('stock.picking', 'read', [[REMESSA], ['name', 'state', 'picking_terceiro_id']], {'context': ctx_fb()})[0]
    comp = o.execute_kw('stock.picking', 'read', [[REF_COMP], ['name', 'state', 'partner_id', 'group_id']], {'context': ctx_fb()})[0]
    print(f"  remessa {REMESSA} {rem['name']} state={rem['state']} picking_terceiro_id={rem['picking_terceiro_id']}")
    print(f"  companheiro-ref {REF_COMP} {comp['name']} state={comp['state']} partner={comp['partner_id']} group={comp['group_id']}")
    if comp['state'] != 'cancel':
        print(f"  [ABORT] companheiro-ref {REF_COMP} NAO esta cancel (state={comp['state']}). "
              f"Pode haver companheiro ativo — investigar antes de duplicar."); return 1

    # orfaos de execucoes anteriores (ex.: 322852, abortado pre-validacao por duplicacao de move.lines)
    orfaos = achar_orfaos(o)
    if orfaos:
        print(f"\n  [ORFAOS] {len(orfaos)} picking(s) pt{PT_INT} de dreno anterior NAO finalizado(s):")
        for p in orfaos:
            print(f"    {p['id']} {p['name']} state={p['state']} origin={p['origin']}")
        print(f"    -> {'serao CANCELADOS no --execute (antes de recriar)' if DRY else 'CANCELANDO antes de recriar'}")

    # idempotencia: 26489 ja drenado?
    soma_t0, n_t0 = soma_lote_em(o, LOC_T)
    soma_3os0, n_3os0 = soma_lote_em(o, LOC_3OS)
    print(f"\n  ESTADO ATUAL (lote {LOTE} cmp FB):")
    print(f"    26489 (transito): {n_t0} quants, soma={soma_t0:.8f}")
    print(f"    30720 (terceiros): {n_3os0} quants, soma={soma_3os0:.8f}")
    if abs(soma_t0) < TOL:
        print(f"  [INFO] 26489 ja zerado p/ o lote {LOTE} -> nada a drenar (idempotente). Fim."); return 0

    quants = resolver_quants(o)
    print(f"\n  PLANO: picking pt{PT_INT} (FB Transf. Internas) {LOC_T} -> {LOC_3OS}; {len(quants)} moves:")
    print(f"  {'cod':>12} {'componente':<30} {'qty':>16} {'lote':<14} {'reserved':>10}")
    reservado = []
    soma_plano = 0.0
    for q in quants:
        soma_plano += q['qty']
        if q['reserved'] > TOL:
            reservado.append(q['cod'])
        print(f"  {q['cod']:>12} {q['nome']:<30} {q['qty']:>16.8f} {str(q['lote_nm'])[:14]:<14} {q['reserved']:>10.4f}"
              f"{'  *** RESERVADO' if q['reserved'] > TOL else ''}")
    print(f"\n  soma do plano = {soma_plano:.8f} (esperado {SOMA_ESPERADA})")

    # validacoes
    if len(quants) != 16:
        print(f"  [ABORT] esperado 16 quants, achei {len(quants)}. Investigar."); return 1
    if abs(soma_plano - SOMA_ESPERADA) > 1e-4:
        print(f"  [ABORT] soma {soma_plano} != esperado {SOMA_ESPERADA}. Investigar."); return 1
    if reservado:
        print(f"  [ABORT] {len(reservado)} quants RESERVADOS ({reservado}). Liberar reserva antes (Skill 2.4). Abortando."); return 1

    if DRY:
        print(f"\n  DRY-RUN: nada criado. Impacto contabil ESPERADO = ZERO (move transit->customer nao gera SVL).")
        print(f"  POS-CHECK (apos execute): 26489 lote {LOTE} -> 0 ; 30720 recebe {len(quants)} quants ({SOMA_ESPERADA}) ; picking done ; 0 SVL.")
        print(f"  Proximo (com go fresco): python {sys.argv[0].split('/')[-1]} --execute")
        return 0

    # ===================== EXECUTE — replica padrao e2e_remessa_criar (G-REM-4)
    # limpa orfaos (ex.: 322852) ANTES de recriar — evita acumular pickings inconsistentes
    if orfaos:
        oids = [p['id'] for p in orfaos]
        o.execute_kw('stock.picking', 'action_cancel', [oids], {'context': ctx_fb()})
        chk = o.execute_kw('stock.picking', 'read', [oids, ['name', 'state']], {'context': ctx_fb()})
        print(f"[orfaos cancelados] {[(c['name'], c['state']) for c in chk]}")
        bad_cancel = [c for c in chk if c['state'] != 'cancel']
        if bad_cancel:
            print(f"  [ABORT] orfao(s) nao cancelaram: {bad_cancel}. Investigar antes de recriar."); return 1

    move_vals = [(0, 0, {'name': f"DRENO-26489 {q['pid']}", 'product_id': q['pid'],
                         'product_uom_qty': q['qty'], 'product_uom': q['uom'],
                         'location_id': LOC_T, 'location_dest_id': LOC_3OS, 'company_id': CMP_FB})
                 for q in quants]
    pk_id = o.execute_kw('stock.picking', 'create',
                         [{'picking_type_id': PT_INT, 'location_id': LOC_T, 'location_dest_id': LOC_3OS,
                           'company_id': CMP_FB,
                           'partner_id': comp['partner_id'][0] if comp['partner_id'] else False,
                           'origin': f"DRENO-PILOTO remessa {rem['name']}",
                           'move_ids_without_package': move_vals}], {'context': ctx_fb()})
    print(f"\n[criado] picking id={pk_id}")
    smoves = o.search_read('stock.move', [('picking_id', '=', pk_id)], ['id', 'product_id', 'product_uom'], limit=40)
    o.execute_kw('stock.move', 'write', [[m['id'] for m in smoves], {'company_id': CMP_FB}], {'context': ctx_fb()})
    o.execute_kw('stock.picking', 'action_confirm', [[pk_id]], {'context': ctx_fb()})

    # CAUSA RAIZ do bug 322852: o pt5 reserva 'at confirm' -> action_confirm dispara action_assign
    # automatico que cria move.lines SEM-LOTE; somadas as manuais abaixo davam 32 mls (qty dobrada).
    # do_unreserve limpa as automaticas ANTES de criar as manuais pinadas (sem action_assign/FIFO).
    try:
        o.execute_kw('stock.picking', 'do_unreserve', [[pk_id]], {'context': ctx_fb()})
    except Exception as e:
        print(f"  [aviso do_unreserve] {e}")
    # garante zero move.lines residuais antes de criar as manuais (idempotente)
    residual = o.search_read('stock.move.line', [('picking_id', '=', pk_id)], ['id'], limit=80)
    if residual:
        o.execute_kw('stock.move.line', 'unlink', [[r['id'] for r in residual]], {'context': ctx_fb()})
        print(f"  [do_unreserve] removidas {len(residual)} move.lines automaticas (SEM-LOTE)")

    # move.line MANUAL com lote pinado (sem action_assign/FIFO)
    fails = []
    for sm in smoves:
        plan = next((q for q in quants if q['pid'] == (sm['product_id'][0] if sm['product_id'] else None)), None)
        if not plan:
            fails.append(('sem-plano', sm['id'])); continue
        ml_id = o.execute_kw('stock.move.line', 'create',
                             [{'move_id': sm['id'], 'picking_id': pk_id, 'product_id': plan['pid'],
                               'product_uom_id': sm['product_uom'][0] if sm['product_uom'] else plan['uom'],
                               'location_id': LOC_T, 'location_dest_id': LOC_3OS,
                               'lot_id': plan['lot_id'], 'company_id': CMP_FB}], {'context': ctx_fb()})
        if not write_done(o, ml_id, plan['qty']):
            fails.append((plan['pid'], ml_id))
    if fails:
        print(f"[ABORT] falha ao gravar qtd/lote em {fails}. Picking {pk_id} criado mas NAO validado — verificar."); return 1

    # conferir lote+qtd antes de validar
    mls = o.search_read('stock.move.line', [('picking_id', '=', pk_id)], ['product_id', 'lot_id', 'quantity'], limit=40)
    bad = [m for m in mls if not m['lot_id'] or LOTE.lower() not in str(m['lot_id'][1]).lower()]
    if bad:
        print(f"[ABORT] {len(bad)} move.line com lote != {LOTE}. NAO validando."); return 1
    print(f"  {len(mls)} move.lines com lote {LOTE} pinado e qtd gravada. Validando...")

    # button_validate (skip_backorder; sem stock.immediate.transfer no v17)
    try:
        o.execute_kw('stock.picking', 'button_validate', [[pk_id]],
                     {'context': dict(ctx_fb(), skip_backorder=True, picking_ids_not_to_backorder=[pk_id])})
    except Exception as e:
        if 'cannot marshal None' not in str(e):
            print(f"  [aviso button_validate] {e}")
    st = o.read('stock.picking', [pk_id], ['name', 'state'])[0]
    if st['state'] != 'done':
        print(f"\n[FALHA] picking {st['name']} state={st['state']} (NAO done). Investigar reservas/estoque."); return 1

    # ===================== POS-CHECK
    print(f"\n[OK] picking {st['name']} (id {pk_id}) done.")
    soma_t1, n_t1 = soma_lote_em(o, LOC_T)
    soma_3os1, n_3os1 = soma_lote_em(o, LOC_3OS)
    svls = o.search_read('stock.valuation.layer', [('stock_move_id', 'in', [m['id'] for m in smoves])], ['id', 'value'], limit=40)
    print(f"  POS-CHECK (lote {LOTE} cmp FB):")
    print(f"    26489 (transito): {n_t1} quants, soma={soma_t1:.8f}  (esperado 0)")
    print(f"    30720 (terceiros): {n_3os1} quants, soma={soma_3os1:.8f}  (esperado {SOMA_ESPERADA})")
    print(f"    SVL gerados pelos moves do dreno = {len(svls)} (esperado 0 — operacao fisica pura)")
    ok = abs(soma_t1) < TOL and abs(soma_3os1 - SOMA_ESPERADA) < 1e-4 and len(svls) == 0
    print(f"\n  {'[PASS] dreno completo: 26489 zerado, 30720 com o material, 0 contabil.' if ok else '[ALERTA] POS-CHECK divergente — investigar.'}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main() or 0)
