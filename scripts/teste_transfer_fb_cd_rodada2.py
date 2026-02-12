"""
Teste Rodada 3 — Fluxo Completo Transfer FB → CD (Carrier corrigido)
=====================================================================

Produto: MOLHO SHOYU PET 12X150ML CAMPO BELO (ID=27832, cod=4870146)
Quantidade: 2 caixas (UOM=160)
Custo medio: R$ 20,96

Correcao vs Rodada 2:
  - CARRIER_ID: 997 → 996 (carrier 997 aponta para partner 97769 com CNPJ=False (bool),
    causando erro "argument should be bytes, buffer or ASCII string, not 'bool'"
    no gerador XML da NF-e. Carrier 996 = Partner ID=1, CNPJ=61.724.241/0001-78)
  - ORIGIN: TESTE-TRANSFER-SHOYU-003 → 004 (novo picking, evita idempotencia)
  - INVOICE_TO_CANCEL: 497711 → 497780 (invoice da rodada 2)

Passos:
  0. Cancelar invoice 497780 da rodada 2
  1. Criar picking saida FB
  2. Confirmar e reservar estoque
  3. Criar/buscar lote na company 1
  4. Preencher move lines com lote + quantidade
  5. Setar transportadora (carrier_id=996 — CORRETO)
  6. Aprovar quality checks + validar picking
  7. Liberar faturamento (action_liberar_faturamento)
  8. Pollar invoice criada pelo robo
  9. Transmitir NF-e (action_post + action_gerar_nfe)
 10. Verificar resultado (chave NF-e)

Uso:
    source .venv/bin/activate
    python scripts/teste_transfer_fb_cd_rodada2.py
"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==========================================
# Constantes do teste
# ==========================================
PRODUCT_ID = 27832           # MOLHO SHOYU PET 12X150ML CAMPO BELO
PRODUCT_NAME = 'MOLHO SHOYU - PET 12X150 ML - CAMPO BELO'
PRODUCT_UOM = 160            # CAIXAS
QTY = 2.0                    # 2 caixas
LOT_NAME = 'TESTE 2'

PICKING_TYPE_OUT_FB = 51     # FB/SAI/INT — Expedicao Entre Filiais
PARTNER_CD = 34              # NACOM GOYA - CD
COMPANY_FB = 1
LOCATION_FB_ESTOQUE = 8      # FB/Estoque
LOCATION_TRANSITO = 6        # Estoque Virtual/Em Transito (Filiais)
INCOTERM_CIF = 6             # CIF
CARRIER_ID = 996             # NACOM GOYA (Partner ID=1, CNPJ=61.724.241/0001-78)

ORIGIN = 'TESTE-TRANSFER-SHOYU-004'
INVOICE_TO_CANCEL = 497780

# Fire and Poll — parametros
FIRE_TIMEOUT = 60
POLL_INTERVAL = 10
MAX_POLL_TIME = 1800


def fire_and_poll(odoo, fire_fn, poll_fn, step_name,
                  poll_interval=POLL_INTERVAL, max_poll_time=MAX_POLL_TIME):
    """
    Padrao Fire and Poll simplificado para teste.
    1. fire_fn() com timeout curto — se timeout, OK
    2. poll_fn() a cada poll_interval ate retornar truthy
    """
    fire_result = None
    needs_polling = False

    try:
        fire_result = fire_fn()
        logger.info(f"  [{step_name}] Acao completou normalmente")
    except Exception as e:
        error_str = str(e)
        if 'Timeout' in error_str or 'timeout' in error_str or 'timed out' in error_str:
            logger.info(f"  [{step_name}] Timeout ao disparar — esperado, iniciando polling...")
            needs_polling = True
        elif 'cannot marshal None' in error_str:
            logger.info(f"  [{step_name}] Acao completou (retorno None)")
            fire_result = None
        elif any(kw in error_str for kw in ('Network is unreachable', 'Connection', 'SSL', 'socket', 'OSError')):
            logger.warning(f"  [{step_name}] Erro de rede ao disparar: {e} — tentando polling...")
            needs_polling = True
        else:
            raise

    # Se fire completou, verificar se resultado ja e valido
    if not needs_polling:
        try:
            poll_result = poll_fn()
            if poll_result:
                return poll_result
        except Exception:
            pass
        if fire_result:
            return fire_result

    # POLL — verificar resultado periodicamente
    elapsed = 0
    poll_count = 0
    while elapsed < max_poll_time:
        time.sleep(poll_interval)
        elapsed += poll_interval
        poll_count += 1

        try:
            poll_result = poll_fn()
            if poll_result:
                logger.info(f"  [{step_name}] Poll #{poll_count} ({elapsed}s): OK")
                return poll_result
            else:
                logger.info(f"  [{step_name}] Poll #{poll_count} ({elapsed}s): aguardando...")
        except Exception as e:
            error_str = str(e)
            if any(kw in error_str for kw in ('Timeout', 'timeout', 'Connection', 'SSL', 'socket')):
                logger.warning(f"  [{step_name}] Poll #{poll_count}: erro de conexao, tentando novamente...")
            else:
                raise

    raise TimeoutError(
        f"[{step_name}] Timeout apos {max_poll_time}s ({poll_count} polls)"
    )


def aprovar_quality_checks(odoo, picking_id):
    """Aprova TODOS quality checks do picking."""
    checks = odoo.execute_kw(
        'quality.check', 'search_read',
        [[
            ['picking_id', '=', picking_id],
            ['quality_state', '=', 'none'],
        ]],
        {'fields': ['id', 'test_type', 'quality_state']}
    )
    if not checks:
        logger.info(f"    Nenhum quality check pendente para picking {picking_id}")
        return

    logger.info(f"    Aprovando {len(checks)} quality checks...")
    for check in checks:
        check_id = check['id']
        test_type = check.get('test_type', 'passfail')
        try:
            if test_type == 'measure':
                odoo.write('quality.check', check_id, {'measure': 0})
                try:
                    odoo.execute_kw('quality.check', 'do_measure', [[check_id]])
                except Exception as e:
                    if 'cannot marshal None' not in str(e):
                        raise
            else:
                try:
                    odoo.execute_kw('quality.check', 'do_pass', [[check_id]])
                except Exception as e:
                    if 'cannot marshal None' not in str(e):
                        raise
            logger.info(f"    QC {check_id} ({test_type}): aprovado")
        except Exception as e:
            logger.error(f"    Erro no quality check {check_id}: {e}")
            raise


def main():
    app = create_app()

    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection

        odoo = get_odoo_connection()

        print("\n" + "=" * 70)
        print("TESTE RODADA 3 — Transfer FB → CD (Carrier corrigido: 996)")
        print(f"Produto: {PRODUCT_NAME} (ID={PRODUCT_ID})")
        print(f"Quantidade: {QTY} caixas (UOM={PRODUCT_UOM})")
        print(f"Carrier: {CARRIER_ID} (Partner ID=1, CNPJ=61.724.241/0001-78)")
        print("=" * 70)

        # ==================================================================
        # PASSO 0: Cancelar invoice do teste anterior
        # ==================================================================
        print(f"\n{'='*70}")
        print(f"PASSO 0: Cancelar invoice {INVOICE_TO_CANCEL}")
        print(f"{'='*70}")

        inv_data = odoo.execute_kw(
            'account.move', 'read',
            [[INVOICE_TO_CANCEL]],
            {'fields': ['id', 'name', 'state', 'l10n_br_situacao_nf']}
        )
        if not inv_data:
            print(f"  Invoice {INVOICE_TO_CANCEL} nao encontrada — pulando")
        else:
            inv = inv_data[0]
            print(f"  Invoice: {inv['name']} | state={inv['state']} | situacao_nf={inv.get('l10n_br_situacao_nf')}")

            if inv['state'] == 'cancel':
                print(f"  Ja cancelada — OK")
            else:
                if inv['state'] == 'posted':
                    print(f"  Revertendo para draft (button_draft)...")
                    try:
                        odoo.execute_kw('account.move', 'button_draft', [[INVOICE_TO_CANCEL]])
                    except Exception as e:
                        if 'cannot marshal None' not in str(e):
                            raise
                    print(f"  button_draft executado")

                print(f"  Cancelando (button_cancel)...")
                try:
                    odoo.execute_kw('account.move', 'button_cancel', [[INVOICE_TO_CANCEL]])
                except Exception as e:
                    if 'cannot marshal None' not in str(e):
                        raise

                # Verificar
                inv_check = odoo.execute_kw(
                    'account.move', 'read',
                    [[INVOICE_TO_CANCEL]],
                    {'fields': ['state']}
                )
                final_state = inv_check[0]['state'] if inv_check else '?'
                print(f"  Estado final: {final_state}")
                if final_state != 'cancel':
                    print(f"  AVISO: esperava 'cancel', obteve '{final_state}'")

        # ==================================================================
        # PASSO 1: Criar picking saida FB
        # ==================================================================
        print(f"\n{'='*70}")
        print(f"PASSO 1: Criar picking saida FB")
        print(f"{'='*70}")

        # Idempotencia: buscar picking existente
        existing = odoo.execute_kw(
            'stock.picking', 'search_read',
            [[
                ['origin', '=', ORIGIN],
                ['company_id', '=', COMPANY_FB],
                ['state', '!=', 'cancel'],
            ]],
            {'fields': ['id', 'name', 'state'], 'limit': 1}
        )

        if existing:
            picking_id = existing[0]['id']
            picking_name = existing[0]['name']
            picking_state = existing[0]['state']
            print(f"  Picking ja existe: {picking_name} (ID={picking_id}, state={picking_state})")
        else:
            picking_vals = {
                'picking_type_id': PICKING_TYPE_OUT_FB,
                'location_id': LOCATION_FB_ESTOQUE,
                'location_dest_id': LOCATION_TRANSITO,
                'partner_id': PARTNER_CD,
                'company_id': COMPANY_FB,
                'origin': ORIGIN,
                'incoterm': INCOTERM_CIF,
                'scheduled_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'move_ids': [(0, 0, {
                    'name': PRODUCT_NAME,
                    'product_id': PRODUCT_ID,
                    'product_uom_qty': QTY,
                    'product_uom': PRODUCT_UOM,
                    'location_id': LOCATION_FB_ESTOQUE,
                    'location_dest_id': LOCATION_TRANSITO,
                })],
            }
            picking_id = odoo.create('stock.picking', picking_vals)
            print(f"  Picking criado: ID={picking_id}")

            # Ler nome
            pk_data = odoo.execute_kw(
                'stock.picking', 'read',
                [[picking_id]],
                {'fields': ['name', 'state']}
            )
            picking_name = pk_data[0]['name'] if pk_data else f'ID={picking_id}'
            picking_state = pk_data[0]['state'] if pk_data else 'draft'
            print(f"  Nome: {picking_name} | state={picking_state}")

        # ==================================================================
        # PASSO 2: Confirmar e reservar estoque
        # ==================================================================
        print(f"\n{'='*70}")
        print(f"PASSO 2: Confirmar e reservar estoque")
        print(f"{'='*70}")

        # Re-ler estado
        pk_data = odoo.execute_kw(
            'stock.picking', 'read',
            [[picking_id]],
            {'fields': ['state']}
        )
        picking_state = pk_data[0]['state'] if pk_data else picking_state

        if picking_state == 'done':
            print(f"  Picking ja esta done — pulando confirm/assign")
        else:
            if picking_state == 'draft':
                print(f"  action_confirm...")
                try:
                    odoo.execute_kw('stock.picking', 'action_confirm', [[picking_id]], timeout_override=90)
                    print(f"  action_confirm OK")
                except Exception as e:
                    if 'cannot marshal None' not in str(e):
                        raise
                    print(f"  action_confirm OK (retorno None)")

            print(f"  action_assign...")
            try:
                odoo.execute_kw('stock.picking', 'action_assign', [[picking_id]], timeout_override=90)
                print(f"  action_assign OK")
            except Exception as e:
                if 'cannot marshal None' not in str(e):
                    raise
                print(f"  action_assign OK (retorno None)")

            # Verificar estado
            pk_data = odoo.execute_kw(
                'stock.picking', 'read',
                [[picking_id]],
                {'fields': ['state']}
            )
            picking_state = pk_data[0]['state'] if pk_data else '?'
            print(f"  Estado apos assign: {picking_state}")

        # ==================================================================
        # PASSO 3+4: Ler move lines e ajustar lote + quantidade
        # ==================================================================
        print(f"\n{'='*70}")
        print(f"PASSO 3+4: Ajustar move lines (lote + quantidade)")
        print(f"{'='*70}")

        lot_id = None  # Sera preenchido com o lote que action_assign reservou

        if picking_state == 'done':
            print(f"  Picking ja done — pulando preenchimento de move lines")
            # Ler lot_id para referencia
            move_lines = odoo.execute_kw(
                'stock.move.line', 'search_read',
                [[['picking_id', '=', picking_id]]],
                {'fields': ['id', 'lot_id']}
            )
            if move_lines and move_lines[0].get('lot_id'):
                lot_id = move_lines[0]['lot_id'][0] if isinstance(move_lines[0]['lot_id'], (list, tuple)) else move_lines[0]['lot_id']
        else:
            move_lines = odoo.execute_kw(
                'stock.move.line', 'search_read',
                [[['picking_id', '=', picking_id]]],
                {'fields': ['id', 'product_id', 'quantity', 'lot_id', 'lot_name']}
            )
            print(f"  Encontradas {len(move_lines)} move lines")

            for ml in move_lines:
                ml_id = ml['id']
                pid = ml['product_id'][0] if isinstance(ml.get('product_id'), (list, tuple)) else ml.get('product_id')
                existing_lot = ml.get('lot_id')
                lot_display = existing_lot[1] if isinstance(existing_lot, (list, tuple)) else existing_lot
                print(f"  Move line {ml_id}: product={pid}, qty={ml.get('quantity')}, lot={lot_display}")

                # Usar o lote que action_assign ja reservou (tem estoque real)
                if existing_lot:
                    lot_id = existing_lot[0] if isinstance(existing_lot, (list, tuple)) else existing_lot
                    print(f"    Mantendo lote reservado: ID={lot_id} ({lot_display})")
                    # Apenas garantir quantidade correta
                    odoo.write('stock.move.line', ml_id, {'quantity': QTY})
                    print(f"    Quantidade ajustada: {QTY}")
                else:
                    # Sem lote reservado — buscar/criar lote
                    lot_ids = odoo.execute_kw(
                        'stock.lot', 'search',
                        [[
                            ['name', '=', LOT_NAME],
                            ['product_id', '=', PRODUCT_ID],
                            ['company_id', '=', COMPANY_FB],
                        ]]
                    )
                    if lot_ids:
                        lot_id = lot_ids[0]
                        print(f"    Lote '{LOT_NAME}' encontrado: ID={lot_id}")
                    else:
                        lot_id = odoo.create('stock.lot', {
                            'name': LOT_NAME,
                            'product_id': PRODUCT_ID,
                            'company_id': COMPANY_FB,
                        })
                        print(f"    Lote '{LOT_NAME}' criado: ID={lot_id}")

                    odoo.write('stock.move.line', ml_id, {
                        'quantity': QTY,
                        'lot_id': lot_id,
                    })
                    print(f"    Atualizado: qty={QTY}, lot_id={lot_id}")

        # ==================================================================
        # PASSO 5: Setar transportadora
        # ==================================================================
        print(f"\n{'='*70}")
        print(f"PASSO 5: Setar transportadora (carrier_id={CARRIER_ID})")
        print(f"{'='*70}")

        if picking_state == 'done':
            print(f"  Picking ja done — pulando transportadora")
        else:
            odoo.write('stock.picking', [picking_id], {'carrier_id': CARRIER_ID})
            print(f"  carrier_id={CARRIER_ID} setado no picking {picking_id}")

        # ==================================================================
        # PASSO 6: Aprovar quality checks + validar picking
        # ==================================================================
        print(f"\n{'='*70}")
        print(f"PASSO 6: Aprovar quality checks + validar picking")
        print(f"{'='*70}")

        if picking_state == 'done':
            print(f"  Picking ja done — pulando validacao")
        else:
            # Quality checks
            aprovar_quality_checks(odoo, picking_id)

            # Validar picking [fire_and_poll]
            def fire_validar():
                return odoo.execute_kw(
                    'stock.picking', 'button_validate',
                    [[picking_id]],
                    {'context': {
                        'skip_backorder': True,
                        'picking_ids_not_to_backorder': [picking_id],
                    }},
                    timeout_override=FIRE_TIMEOUT
                )

            def poll_validar():
                p = odoo.execute_kw(
                    'stock.picking', 'read',
                    [[picking_id]],
                    {'fields': ['state', 'name']}
                )
                if p and p[0].get('state') == 'done':
                    return p[0]
                return None

            result = fire_and_poll(odoo, fire_validar, poll_validar, 'Validar Picking')
            if isinstance(result, dict):
                picking_name = result.get('name', picking_name)
            print(f"  Picking {picking_name} validado (state=done)")

        # ==================================================================
        # PASSO 7: Liberar faturamento
        # ==================================================================
        print(f"\n{'='*70}")
        print(f"PASSO 7: Liberar faturamento (action_liberar_faturamento)")
        print(f"{'='*70}")

        # Verificar se ja liberado
        pk_lib = odoo.execute_kw(
            'stock.picking', 'read',
            [[picking_id]],
            {'fields': ['liberado_faturamento']}
        )
        liberado = pk_lib[0].get('liberado_faturamento', False) if pk_lib else False

        if liberado:
            print(f"  Faturamento ja liberado — OK")
        else:
            def fire_liberar():
                return odoo.execute_kw(
                    'stock.picking', 'action_liberar_faturamento',
                    [[picking_id]],
                    timeout_override=FIRE_TIMEOUT
                )

            def poll_liberar():
                p = odoo.execute_kw(
                    'stock.picking', 'read',
                    [[picking_id]],
                    {'fields': ['liberado_faturamento']}
                )
                if p and p[0].get('liberado_faturamento'):
                    return True
                return None

            fire_and_poll(
                odoo, fire_liberar, poll_liberar,
                'Liberar Faturamento', poll_interval=10, max_poll_time=120
            )
            print(f"  Faturamento liberado no picking {picking_id}")

        # ==================================================================
        # PASSO 8: Pollar invoice criada pelo robo
        # ==================================================================
        print(f"\n{'='*70}")
        print(f"PASSO 8: Aguardando invoice do robo (poll via ref='{picking_name}')")
        print(f"{'='*70}")

        def fire_noop():
            return None

        def poll_invoice():
            # Metodo 1: campo invoice_ids no picking
            picking = odoo.execute_kw(
                'stock.picking', 'read',
                [[picking_id]],
                {'fields': ['invoice_ids']}
            )
            if picking and picking[0].get('invoice_ids'):
                inv_id = picking[0]['invoice_ids'][-1]
                logger.info(f"  Invoice encontrada via invoice_ids: {inv_id}")
                return inv_id

            # Metodo 2: buscar via campo 'ref' (robo CIEL IT popula ref com picking name)
            if picking_name:
                invoices = odoo.execute_kw(
                    'account.move', 'search_read',
                    [[
                        ['company_id', '=', COMPANY_FB],
                        ['ref', '=', picking_name],
                        ['state', '!=', 'cancel'],
                    ]],
                    {'fields': ['id', 'name', 'state'], 'limit': 1, 'order': 'id desc'}
                )
                if invoices:
                    logger.info(f"  Invoice encontrada via ref: {invoices[0]}")
                    return invoices[0]['id']

            # Metodo 3: buscar via invoice_origin (fallback)
            if picking_name:
                invoices = odoo.execute_kw(
                    'account.move', 'search_read',
                    [[
                        ['company_id', '=', COMPANY_FB],
                        ['invoice_origin', 'ilike', picking_name],
                        ['state', '!=', 'cancel'],
                    ]],
                    {'fields': ['id', 'name', 'state'], 'limit': 1, 'order': 'id desc'}
                )
                if invoices:
                    logger.info(f"  Invoice encontrada via invoice_origin: {invoices[0]}")
                    return invoices[0]['id']

            return None

        invoice_id = fire_and_poll(
            odoo, fire_noop, poll_invoice,
            'Aguardar Invoice Transfer',
            poll_interval=15, max_poll_time=900  # 15min
        )

        if isinstance(invoice_id, dict):
            invoice_id = invoice_id.get('id', invoice_id)

        print(f"  Invoice de transferencia encontrada: ID={invoice_id}")

        # ==================================================================
        # PASSO 9: Transmitir NF-e
        # ==================================================================
        print(f"\n{'='*70}")
        print(f"PASSO 9: Transmitir NF-e (invoice {invoice_id})")
        print(f"{'='*70}")

        inv_data = odoo.execute_kw(
            'account.move', 'read',
            [[invoice_id]],
            {'fields': ['name', 'state', 'l10n_br_situacao_nf']}
        )
        if not inv_data:
            raise ValueError(f"Invoice {invoice_id} nao encontrada")

        inv_name = inv_data[0].get('name', '')
        inv_state = inv_data[0].get('state')
        situacao_nf = inv_data[0].get('l10n_br_situacao_nf')
        print(f"  Invoice: {inv_name} | state={inv_state} | situacao_nf={situacao_nf}")

        if situacao_nf == 'autorizado':
            print(f"  Ja autorizada pela SEFAZ — OK")
        else:
            # Passo 9a: Se draft → postar
            if inv_state == 'draft':
                # Recalcular impostos
                print(f"  Recalculando impostos...")
                try:
                    odoo.execute_kw(
                        'account.move', 'onchange_l10n_br_calcular_imposto',
                        [[invoice_id]]
                    )
                    print(f"  onchange_l10n_br_calcular_imposto OK")
                except Exception as e:
                    print(f"  onchange_l10n_br_calcular_imposto falhou (nao critico): {e}")

                try:
                    odoo.execute_kw(
                        'account.move', 'onchange_l10n_br_calcular_imposto_btn',
                        [[invoice_id]],
                        timeout_override=FIRE_TIMEOUT
                    )
                    print(f"  onchange_l10n_br_calcular_imposto_btn OK")
                except Exception as e:
                    print(f"  onchange_l10n_br_calcular_imposto_btn falhou (nao critico): {e}")

                # action_post
                print(f"  Postando invoice (action_post)...")
                def fire_post():
                    return odoo.execute_kw(
                        'account.move', 'action_post',
                        [[invoice_id]],
                        {'context': {'validate_analytic': True}},
                        timeout_override=FIRE_TIMEOUT
                    )

                def poll_post():
                    inv = odoo.execute_kw(
                        'account.move', 'read',
                        [[invoice_id]],
                        {'fields': ['state', 'name']}
                    )
                    if inv and inv[0].get('state') == 'posted':
                        return inv[0]
                    return None

                result = fire_and_poll(odoo, fire_post, poll_post, 'Post Invoice')
                inv_name = result.get('name', inv_name) if isinstance(result, dict) else inv_name
                inv_state = 'posted'
                print(f"  Invoice {inv_name} postada (state=posted)")

                # Re-ler situacao_nf
                inv_refresh = odoo.execute_kw(
                    'account.move', 'read',
                    [[invoice_id]],
                    {'fields': ['l10n_br_situacao_nf']}
                )
                situacao_nf = inv_refresh[0].get('l10n_br_situacao_nf') if inv_refresh else situacao_nf

            # Passo 9b: Se posted + rascunho → transmitir NF-e
            if inv_state == 'posted' and situacao_nf in ('rascunho', 'excecao_autorizado', False, None):
                print(f"  Transmitindo NF-e (action_gerar_nfe)...")

                def fire_gerar_nfe():
                    return odoo.execute_kw(
                        'account.move', 'action_gerar_nfe',
                        [[invoice_id]],
                        timeout_override=FIRE_TIMEOUT
                    )

                def poll_nfe():
                    inv = odoo.execute_kw(
                        'account.move', 'read',
                        [[invoice_id]],
                        {'fields': ['l10n_br_situacao_nf', 'name']}
                    )
                    if not inv:
                        return None
                    sit = inv[0].get('l10n_br_situacao_nf')
                    if sit in ('autorizado', 'excecao_autorizado'):
                        return inv[0]
                    return None

                result = fire_and_poll(
                    odoo, fire_gerar_nfe, poll_nfe,
                    'Transmitir NF-e', poll_interval=15, max_poll_time=300
                )
                if isinstance(result, dict):
                    situacao_nf = result.get('l10n_br_situacao_nf')
                    inv_name = result.get('name', inv_name)

                print(f"  situacao_nf = {situacao_nf}")

        # ==================================================================
        # PASSO 10: Verificar resultado
        # ==================================================================
        print(f"\n{'='*70}")
        print(f"PASSO 10: Resultado final")
        print(f"{'='*70}")

        inv_final = odoo.execute_kw(
            'account.move', 'read',
            [[invoice_id]],
            {'fields': [
                'name', 'state', 'l10n_br_situacao_nf',
                'l10n_br_chave_nf', 'amount_total',
            ]}
        )

        if inv_final:
            inv = inv_final[0]
            print(f"\n  {'='*50}")
            print(f"  RESULTADO DO TESTE")
            print(f"  {'='*50}")
            print(f"  Invoice:       {inv.get('name')}")
            print(f"  State:         {inv.get('state')}")
            print(f"  Situacao NF:   {inv.get('l10n_br_situacao_nf')}")
            print(f"  Chave NF-e:    {inv.get('l10n_br_chave_nf')}")
            print(f"  Valor Total:   R$ {inv.get('amount_total', 0):.2f}")
            print(f"  Picking:       {picking_name} (ID={picking_id})")
            print(f"  Lote:          {LOT_NAME} (ID={lot_id})")
            print(f"  {'='*50}")

            if inv.get('l10n_br_situacao_nf') == 'autorizado':
                print(f"\n  ✓ SUCESSO — NF-e AUTORIZADA PELA SEFAZ!")
            elif inv.get('l10n_br_situacao_nf') == 'excecao_autorizado':
                print(f"\n  ⚠ NF-e autorizada com excecao — verificar manualmente")
            else:
                print(f"\n  ✗ NF-e NAO autorizada — situacao: {inv.get('l10n_br_situacao_nf')}")
        else:
            print(f"  ERRO: Nao foi possivel ler invoice {invoice_id}")


if __name__ == '__main__':
    main()
