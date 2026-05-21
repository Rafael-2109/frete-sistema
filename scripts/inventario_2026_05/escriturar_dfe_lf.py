"""FLUXO A (inventario 2026-05) — Escriturar a in_invoice de ENTRADA na LF a partir do DFe
de industrializacao FB->LF (status 04). Reusa a SEQUENCIA do pipeline com a config da LF
(NAO reusar RecebimentoLfOdooService — direcao inversa). GENERALIZADO p/ multiplas linhas.

Por DFe (--tudo = 1 processo isolado, resiliencia anti-DetachedError/SSL):
  ESCRITURAR: set tipo='serv-industrializacao' -> action_gerar_po_dfe (company LF forcada) ->
    confirmar -> picking nativo (Fornecedores 4 -> LF/Estoque 42) -> preencher TODAS as
    move_lines (lote MIGRAÇÃO por produto, c/ validade) -> quality -> validar ->
    action_create_invoice -> calcular_imposto (1 por DFe) -> action_post = ENTIN (CFOP 1901).
  AJUSTAR: para cada move_line do picking nativo, remove a qty de LF/Estoque/MIGRAÇÃO
    (inventory adjustment) -> neutraliza a duplicacao (o manual ja alimentou).

IDEMPOTENCIA: pula DFe que ja tenha in_invoice posted (dfe_id). Cada DFe e' 1 execucao.
NUNCA rodar varios calcular_imposto juntos (memoria Odoo) — 1 DFe por processo.

Uso:
  .venv/bin/python scripts/inventario_2026_05/escriturar_dfe_lf.py --dfe 42882            # DRY
  .venv/bin/python scripts/inventario_2026_05/escriturar_dfe_lf.py --dfe 42882 --tudo --confirmar
  (--escriturar / --ajustar isolados; --limpar / --desfazer p/ cleanup)
DFes do bulk (13; 42865 ja escriturado=ENTIN/2026/05/0036): ver DFES_BULK.
"""
import argparse
import os
import sys
import time
import warnings

warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

# ---- Config LF (precedente real PO 41843) ----
COMPANY_LF = 5
PICKING_TYPE_LF = 19
LF_ESTOQUE = 42
LOTE_NATIVO = 'MIGRAÇÃO'  # lote do picking nativo; saldo correto do manual ja foi renomeado
VALIDADE_PADRAO = '2026-12-31 00:00:00'
CASAS = 6
TOL = 0.001

# FORCAR company LF (UID 42 default FB=1; action_gerar_po_dfe usa company do usuario, nao do DFe)
CTX_LF = {'allowed_company_ids': [COMPANY_LF], 'company_id': COMPANY_LF}

# DFes do Fluxo A (entrada industrializacao FB->LF). 42865 ja escriturado (idempotencia pula).
DFES_BULK = [42865, 42868, 42882, 42910, 42932, 42931, 42930, 42948, 42947, 42966, 43116, 43124, 43123]


def m2o_id(x):
    return x[0] if isinstance(x, list) and x else None


def m2o_name(x):
    return x[1] if isinstance(x, list) and len(x) >= 2 else ''


def chamar(o, modelo, metodo, ids, kw=None, ctx=None):
    """Chama metodo tolerando 'cannot marshal None' (=sucesso) e timeout (fire-and-poll)."""
    opts = {'context': ctx} if ctx else {}
    try:
        return o.execute_kw(modelo, metodo, [ids], {**opts, **(kw or {})})
    except Exception as e:
        s = str(e)
        if 'cannot marshal None' in s:
            return None
        if 'timeout' in s.lower() or 'timed out' in s.lower():
            return '__TIMEOUT__'
        raise


def resolver_lote(o, pid, nome=LOTE_NATIVO):
    """Busca/cria o lote `nome` do produto na LF, com validade se o produto exigir."""
    lot_ids = o.search('stock.lot', [['name', 'in', [nome]], ['product_id', '=', pid], ['company_id', '=', COMPANY_LF]])
    usa_val = o.read('product.product', [pid], ['use_expiration_date'])[0].get('use_expiration_date')
    if lot_ids:
        lid = lot_ids[0]
        if usa_val and not o.read('stock.lot', [lid], ['expiration_date'])[0].get('expiration_date'):
            o.write('stock.lot', [lid], {'expiration_date': VALIDADE_PADRAO})
        return lid
    vals = {'name': nome, 'product_id': pid, 'company_id': COMPANY_LF}
    if usa_val:
        vals['expiration_date'] = VALIDADE_PADRAO
    return o.create('stock.lot', vals)


def _ja_escriturado(o, dfe_id):
    """Idempotencia: in_invoice posted vinculada ao DFe."""
    return o.search('account.move', [['dfe_id', '=', dfe_id], ['move_type', '=', 'in_invoice'], ['state', '=', 'posted']])


def escriturar(o, dfe_id, dry):
    print(f"\n{'='*92}\n  ESCRITURAR DFe {dfe_id} | {'DRY' if dry else 'REAL'}\n{'='*92}")
    d = o.read('l10n_br_ciel_it_account.dfe', [dfe_id],
               ['l10n_br_status', 'l10n_br_tipo_pedido', 'company_id', 'nfe_infnfe_ide_nnf'])[0]
    print(f"  DFe: status={d['l10n_br_status']} tipo={d['l10n_br_tipo_pedido']} "
          f"company={m2o_name(d.get('company_id'))} nNF={d.get('nfe_infnfe_ide_nnf')}")
    ja = _ja_escriturado(o, dfe_id)
    if ja:
        inv = o.read('account.move', [ja[0]], ['name'])[0]
        print(f"  JA ESCRITURADO (in_invoice {inv['name']} id={ja[0]} posted) — PULANDO.")
        return {'invoice_id': ja[0], 'skipped': True}
    if m2o_id(d.get('company_id')) != COMPANY_LF:
        print("  ABORTAR: DFe nao e' company=5 (LF)."); return None
    if d['l10n_br_status'] != '04':
        print(f"  ABORTAR: DFe status={d['l10n_br_status']} != 04."); return None
    lns = o.search_read('l10n_br_ciel_it_account.dfe.line', [['dfe_id', '=', dfe_id]], ['product_id', 'det_prod_qcom'])
    print(f"  {len(lns)} linha(s)/produto(s) no DFe")
    if dry:
        print(f"  [DRY] set tipo=serv-industrializacao -> PO(LF) -> picking -> {len(lns)} move_lines "
              f"(lote {LOTE_NATIVO}) -> validar -> in_invoice ENTIN (CFOP 1901) -> ajustar depois.")
        return {'skipped': False, 'dry': True}

    # 1.5 — tipo serv-industrializacao (CHAVE p/ CFOP 1901)
    if d['l10n_br_tipo_pedido'] != 'serv-industrializacao':
        o.write('l10n_br_ciel_it_account.dfe', [dfe_id], {'l10n_br_tipo_pedido': 'serv-industrializacao'})
        print("  [1.5] tipo_pedido -> serv-industrializacao")

    # 2 — gerar PO (company LF forcada)
    print("  [2] action_gerar_po_dfe (company=LF) ...")
    chamar(o, 'l10n_br_ciel_it_account.dfe', 'action_gerar_po_dfe', [dfe_id], ctx={'validate_analytic': True, **CTX_LF})
    po_id = None
    for _ in range(15):
        time.sleep(8)
        dd = o.read('l10n_br_ciel_it_account.dfe', [dfe_id], ['purchase_id', 'purchase_fiscal_id'])[0]
        po_id = m2o_id(dd.get('purchase_id')) or m2o_id(dd.get('purchase_fiscal_id'))
        if not po_id:
            pos = o.search_read('purchase.order', [['dfe_id', '=', dfe_id], ['state', '!=', 'cancel']], ['id'], limit=1, order='id desc')
            po_id = pos[0]['id'] if pos else None
        if po_id:
            break
    if not po_id:
        print("  ABORTAR: PO nao gerada."); return None
    po = o.read('purchase.order', [po_id], ['name', 'company_id', 'state', 'picking_type_id'])[0]
    print(f"      PO {po['name']} (id {po_id}) company={m2o_name(po.get('company_id'))} type={m2o_name(po.get('picking_type_id'))} state={po['state']}")
    if m2o_id(po.get('company_id')) != COMPANY_LF or m2o_id(po.get('picking_type_id')) != PICKING_TYPE_LF:
        print("  ABORTAR: PO com company/type ERRADOS (esperado 5/19)."); return None

    # 4 — confirmar
    if po['state'] == 'draft':
        print("  [4] button_confirm ...")
        chamar(o, 'purchase.order', 'button_confirm', [po_id], ctx={'validate_analytic': True, **CTX_LF})
        for _ in range(12):
            time.sleep(6)
            st = o.read('purchase.order', [po_id], ['state'])[0]['state']
            if st in ('purchase', 'done', 'to approve'):
                break
        if o.read('purchase.order', [po_id], ['state'])[0]['state'] == 'to approve':
            chamar(o, 'purchase.order', 'button_approve', [po_id]); time.sleep(6)

    # 6 — buscar picking nativo
    picking_id = None
    for _ in range(8):
        pks = o.search_read('stock.picking', [['purchase_id', '=', po_id], ['picking_type_code', '=', 'incoming']],
                            ['id', 'name', 'state'], limit=1, order='id desc')
        if pks:
            picking_id, pk = pks[0]['id'], pks[0]; break
        time.sleep(8)
    if not picking_id:
        print("  ABORTAR: picking nativo nao encontrado."); return None
    print(f"      picking nativo {pk['name']} (id {picking_id}) state={pk['state']}")
    if pk['state'] not in ('assigned', 'done'):
        chamar(o, 'stock.picking', 'action_assign', [picking_id]); time.sleep(3)

    # 7 — preencher TODAS as move_lines (lote MIGRAÇÃO por produto, c/ validade)
    if o.read('stock.picking', [picking_id], ['state'])[0]['state'] != 'done':
        mls = o.search_read('stock.move.line', [['picking_id', '=', picking_id]], ['id', 'product_id', 'quantity', 'qty_done'])
        cache_lote = {}
        for ml in mls:
            mlpid = m2o_id(ml.get('product_id'))
            if mlpid not in cache_lote:
                cache_lote[mlpid] = resolver_lote(o, mlpid)
            q = float(ml.get('quantity') or 0) or float(ml.get('qty_done') or 0)
            o.write('stock.move.line', [ml['id']], {'qty_done': q, 'quantity': q, 'lot_id': cache_lote[mlpid]})
        print(f"      {len(mls)} move_lines preenchidas (lote {LOTE_NATIVO})")
        # 8 — quality ANTES
        for qc in o.search_read('quality.check', [['picking_id', '=', picking_id], ['quality_state', '=', 'none']], ['id']):
            chamar(o, 'quality.check', 'do_pass', [qc['id']])
        # 9 — validar
        print("  [9] button_validate ...")
        chamar(o, 'stock.picking', 'button_validate', [picking_id],
               ctx={'skip_backorder': True, 'picking_ids_not_to_backorder': [picking_id], **CTX_LF})
        for _ in range(10):
            time.sleep(5)
            if o.read('stock.picking', [picking_id], ['state'])[0]['state'] == 'done':
                break
    if o.read('stock.picking', [picking_id], ['state'])[0]['state'] != 'done':
        print("  ABORTAR: picking nao ficou done."); return None
    print(f"      picking nativo {picking_id} done")

    # 10 — criar invoice
    inv_ids = o.read('purchase.order', [po_id], ['invoice_ids'])[0].get('invoice_ids') or []
    if not inv_ids:
        print("  [10] action_create_invoice ...")
        chamar(o, 'purchase.order', 'action_create_invoice', [po_id], ctx=CTX_LF)
        for _ in range(10):
            time.sleep(6)
            inv_ids = o.read('purchase.order', [po_id], ['invoice_ids'])[0].get('invoice_ids') or []
            if inv_ids:
                break
    if not inv_ids:
        print("  ABORTAR: invoice nao criada."); return None
    invoice_id = inv_ids[-1]

    # 11 — situacao + impostos (1 por DFe)
    o.write('account.move', [invoice_id], {'l10n_br_situacao_nf': 'autorizado'})
    print("  [11] onchange_l10n_br_calcular_imposto_btn ...")
    chamar(o, 'account.move', 'onchange_l10n_br_calcular_imposto_btn', [invoice_id]); time.sleep(10)

    # 12 — postar
    if o.read('account.move', [invoice_id], ['state'])[0]['state'] != 'posted':
        print("  [12] action_post ...")
        chamar(o, 'account.move', 'action_post', [invoice_id], ctx={'validate_analytic': True, **CTX_LF})
        for _ in range(10):
            time.sleep(6)
            if o.read('account.move', [invoice_id], ['state'])[0]['state'] == 'posted':
                break
    inv = o.read('account.move', [invoice_id], ['name', 'state', 'move_type', 'amount_untaxed', 'amount_total'])[0]
    ils = o.read('account.move.line', o.read('account.move', [invoice_id], ['invoice_line_ids'])[0]['invoice_line_ids'], ['l10n_br_cfop_id'])
    cfops = sorted({m2o_name(il.get('l10n_br_cfop_id')) for il in ils if il.get('l10n_br_cfop_id')})
    print(f"  RESULTADO: {inv['name']} {inv['state']} {inv['move_type']} base={inv.get('amount_untaxed')} total={inv.get('amount_total')} CFOPs={cfops}")
    return {'po_id': po_id, 'picking_nativo': picking_id, 'invoice_id': invoice_id, 'skipped': False}


def _picking_nativo_do_dfe(o, dfe_id):
    d = o.read('l10n_br_ciel_it_account.dfe', [dfe_id], ['purchase_id', 'purchase_fiscal_id'])[0]
    po_id = m2o_id(d.get('purchase_fiscal_id')) or m2o_id(d.get('purchase_id'))
    if not po_id:
        return None
    pks = o.search_read('stock.picking', [['purchase_id', '=', po_id], ['picking_type_code', '=', 'incoming'], ['state', '=', 'done']],
                        ['id'], order='id desc', limit=1)
    return pks[0]['id'] if pks else None


def ajustar(o, dfe_id, dry, picking_id=None):
    print(f"\n{'='*92}\n  AJUSTAR DFe {dfe_id} (neutralizar duplicacao do picking nativo) | {'DRY' if dry else 'REAL'}\n{'='*92}")
    if picking_id is None:
        picking_id = _picking_nativo_do_dfe(o, dfe_id)
    if not picking_id:
        print("  picking nativo (done) nao encontrado — nada a ajustar."); return
    mls = o.search_read('stock.move.line', [['picking_id', '=', picking_id]], ['product_id', 'qty_done', 'lot_id'])
    print(f"  picking nativo {picking_id}: {len(mls)} move_lines")
    for ml in mls:
        pid = m2o_id(ml.get('product_id'))
        lot_id = m2o_id(ml.get('lot_id'))
        qty = round(float(ml.get('qty_done') or 0), CASAS)
        if qty <= 0 or not lot_id:
            continue
        qs = o.search_read('stock.quant', [['product_id', '=', pid], ['location_id', '=', LF_ESTOQUE], ['lot_id', '=', lot_id]],
                           ['id', 'quantity', 'reserved_quantity'])
        livre = sum(float(q['quantity']) - float(q.get('reserved_quantity') or 0) for q in qs)
        cod = o.read('product.product', [pid], ['default_code'])[0].get('default_code')
        if dry:
            print(f"      {cod:>10} remover {qty:>12,.3f} de LF/Estoque/{m2o_name(ml.get('lot_id'))} "
                  f"(livre {livre:,.3f}) {'[OK]' if livre + TOL >= qty else '[!! escriturar antes]'}")
            continue
        restante = qty
        for q in qs:
            if restante <= 0:
                break
            ql = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
            consumir = min(restante, ql)
            if consumir <= 0:
                continue
            o.write('stock.quant', [q['id']], {'inventory_quantity': float(q['quantity']) - consumir})
            o.execute_kw('stock.quant', 'action_apply_inventory', [[q['id']]])
            restante -= consumir
        print(f"      {cod:>10} removido {qty - restante:,.3f} de LF/Estoque/MIGRAÇÃO")


def limpar(o, dfe_id, dry):
    """Cancela PO vinculado (sem picking) + reverte DFe 06->04 (PO gerado em company errada)."""
    print(f"\n{'='*92}\n  LIMPAR DFe {dfe_id} | {'DRY' if dry else 'REAL'}\n{'='*92}")
    d = o.read('l10n_br_ciel_it_account.dfe', [dfe_id], ['l10n_br_status', 'purchase_id', 'purchase_fiscal_id'])[0]
    po_id = m2o_id(d.get('purchase_fiscal_id')) or m2o_id(d.get('purchase_id'))
    print(f"  DFe status={d['l10n_br_status']} PO={po_id}")
    if po_id and o.read('purchase.order', [po_id], ['picking_ids'])[0].get('picking_ids'):
        print("  ATENCAO: PO tem picking(s) — use --desfazer."); return
    if dry:
        print(f"  [DRY] cancelaria PO {po_id} + reverteria DFe->04."); return
    if po_id:
        try:
            o.execute_kw('purchase.order', 'button_cancel', [[po_id]])
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                raise
    o.write('l10n_br_ciel_it_account.dfe', [dfe_id], {'l10n_br_status': '04', 'purchase_fiscal_id': False, 'purchase_id': False})
    print(f"  DFe {dfe_id} revertido -> 04")


def desfazer(o, dfe_id, dry):
    """Cancela invoice(s) do PO + tenta cancelar PO + reverte DFe 06->04 (canary errado)."""
    print(f"\n{'='*92}\n  DESFAZER DFe {dfe_id} | {'DRY' if dry else 'REAL'}\n{'='*92}")
    d = o.read('l10n_br_ciel_it_account.dfe', [dfe_id], ['l10n_br_status', 'purchase_id', 'purchase_fiscal_id'])[0]
    po_id = m2o_id(d.get('purchase_fiscal_id')) or m2o_id(d.get('purchase_id'))
    invs = o.read('purchase.order', [po_id], ['invoice_ids'])[0].get('invoice_ids') if po_id else []
    print(f"  DFe status={d['l10n_br_status']} PO={po_id} invoices={invs}")
    if dry:
        print(f"  [DRY] cancelaria invoices {invs} + PO {po_id} + reverteria DFe->04."); return
    for inv_id in invs or []:
        if o.read('account.move', [inv_id], ['state'])[0]['state'] == 'cancel':
            continue
        for met in ('button_draft', 'button_cancel'):
            try:
                o.execute_kw('account.move', met, [[inv_id]])
            except Exception as e:
                if 'cannot marshal None' not in str(e):
                    raise
        print(f"  invoice {inv_id}: cancelada")
    if po_id:
        try:
            o.execute_kw('purchase.order', 'button_cancel', [[po_id]]); print(f"  PO {po_id}: cancelado")
        except Exception as e:
            print(f"  PO {po_id}: button_cancel falhou ({str(e)[:70]})")
    o.write('l10n_br_ciel_it_account.dfe', [dfe_id], {'l10n_br_status': '04', 'purchase_fiscal_id': False, 'purchase_id': False})
    print(f"  DFe {dfe_id} revertido -> 04")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dfe', type=int, required=True)
    ap.add_argument('--limpar', action='store_true')
    ap.add_argument('--desfazer', action='store_true')
    ap.add_argument('--escriturar', action='store_true')
    ap.add_argument('--ajustar', action='store_true')
    ap.add_argument('--tudo', action='store_true', help='escriturar + ajustar (1 DFe, processo isolado)')
    ap.add_argument('--confirmar', action='store_true')
    args = ap.parse_args()
    dry = not args.confirmar

    app = create_app()
    with app.app_context():
        o = get_odoo_connection()
        if args.limpar:
            limpar(o, args.dfe, dry)
        elif args.desfazer:
            desfazer(o, args.dfe, dry)
        elif args.tudo:
            res = escriturar(o, args.dfe, dry)
            if res and not res.get('skipped') and not res.get('dry'):
                ajustar(o, args.dfe, dry, picking_id=res.get('picking_nativo'))
            elif dry:
                ajustar(o, args.dfe, dry)
        elif args.escriturar:
            escriturar(o, args.dfe, dry)
        elif args.ajustar:
            ajustar(o, args.dfe, dry)
        else:
            escriturar(o, args.dfe, True)  # plano (dry)


if __name__ == '__main__':
    main()
