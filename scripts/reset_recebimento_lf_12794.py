"""
Reset E2E: Reverter NF 12794 (RecebimentoLf id=1) e reprocessar.

Contexto:
    NF 12794 foi a primeira NF processada pelo fluxo automatizado de Recebimento LF.
    Apos a migration de precisao de precos (Numeric(15,4) -> Numeric(18,8)),
    precisamos reprocessar para validar que o fluxo E2E preserva precos completos.

IDs fixos:
    - RecebimentoLf: id=1
    - PO Odoo: 35782 (C2614995)
    - Picking Odoo: 302074 (FB/IN/11525)
    - Invoice Odoo: 495837
    - DFe Odoo: 37390
    - Lotes locais: 17 registros (move_line IDs 217488624-217488640)

Fases:
    1. Ler estado Odoo (read-only)
    2. Cancelar Invoice
    3. Reverter Picking
    4. Cancelar PO
    5. Desvincular DFe
    6. Reset local DB
    7. Re-enfileirar job RQ

Uso:
    source .venv/bin/activate
    python scripts/reset_recebimento_lf_12794.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.odoo.utils.connection import get_odoo_connection
from app.recebimento.models import RecebimentoLf
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# IDs fixos da NF 12794
RECEBIMENTO_LF_ID = 1
ODOO_PO_ID = 35782
ODOO_PICKING_ID = 302074
ODOO_INVOICE_ID = 495837
ODOO_DFE_ID = 37390
MOVE_LINE_IDS = list(range(217488624, 217488641))  # 217488624 a 217488640 (17 lotes)


def fase_1_ler_estado_odoo(conn):
    """FASE 1: Ler estado atual no Odoo (read-only)."""
    print("\n" + "=" * 60)
    print("FASE 1: Leitura do estado atual no Odoo")
    print("=" * 60)

    # Invoice
    try:
        invoice = conn.execute_kw(
            'account.move', 'read', [[ODOO_INVOICE_ID]],
            {'fields': ['name', 'state', 'payment_state', 'move_type']}
        )
        if invoice:
            inv = invoice[0]
            print(f"\n  Invoice {ODOO_INVOICE_ID}:")
            print(f"    name: {inv.get('name')}")
            print(f"    state: {inv.get('state')}")
            print(f"    payment_state: {inv.get('payment_state')}")
            print(f"    move_type: {inv.get('move_type')}")
        else:
            print(f"\n  Invoice {ODOO_INVOICE_ID}: NAO ENCONTRADA")
    except Exception as e:
        print(f"\n  Invoice {ODOO_INVOICE_ID}: ERRO ao ler - {e}")

    # Picking
    try:
        picking = conn.execute_kw(
            'stock.picking', 'read', [[ODOO_PICKING_ID]],
            {'fields': ['name', 'state', 'origin']}
        )
        if picking:
            pk = picking[0]
            print(f"\n  Picking {ODOO_PICKING_ID}:")
            print(f"    name: {pk.get('name')}")
            print(f"    state: {pk.get('state')}")
            print(f"    origin: {pk.get('origin')}")
        else:
            print(f"\n  Picking {ODOO_PICKING_ID}: NAO ENCONTRADO")
    except Exception as e:
        print(f"\n  Picking {ODOO_PICKING_ID}: ERRO ao ler - {e}")

    # PO
    try:
        po = conn.execute_kw(
            'purchase.order', 'read', [[ODOO_PO_ID]],
            {'fields': ['name', 'state', 'partner_id', 'amount_total']}
        )
        if po:
            p = po[0]
            print(f"\n  PO {ODOO_PO_ID}:")
            print(f"    name: {p.get('name')}")
            print(f"    state: {p.get('state')}")
            print(f"    partner: {p.get('partner_id')}")
            print(f"    amount_total: {p.get('amount_total')}")
        else:
            print(f"\n  PO {ODOO_PO_ID}: NAO ENCONTRADO")
    except Exception as e:
        print(f"\n  PO {ODOO_PO_ID}: ERRO ao ler - {e}")

    # DFe
    try:
        dfe = conn.execute_kw(
            'l10n_br_ciel_it_account.dfe', 'read', [[ODOO_DFE_ID]],
            {'fields': ['name', 'purchase_id', 'l10n_br_status']}
        )
        if dfe:
            d = dfe[0]
            print(f"\n  DFe {ODOO_DFE_ID}:")
            print(f"    name: {d.get('name')}")
            print(f"    purchase_id: {d.get('purchase_id')}")
            print(f"    l10n_br_status: {d.get('l10n_br_status')}")
        else:
            print(f"\n  DFe {ODOO_DFE_ID}: NAO ENCONTRADO")
    except Exception as e:
        print(f"\n  DFe {ODOO_DFE_ID}: ERRO ao ler - {e}")

    # Move Lines (amostra)
    try:
        move_lines = conn.execute_kw(
            'stock.move.line', 'read', [MOVE_LINE_IDS[:3]],
            {'fields': ['id', 'product_id', 'quantity', 'lot_id', 'state']}
        )
        print(f"\n  Move Lines (amostra 3 de {len(MOVE_LINE_IDS)}):")
        for ml in move_lines:
            print(f"    ID={ml['id']}: product={ml.get('product_id')}, "
                  f"qty={ml.get('quantity')}, lot={ml.get('lot_id')}, state={ml.get('state')}")
    except Exception as e:
        print(f"\n  Move Lines: ERRO ao ler - {e}")


def fase_2_cancelar_invoice(conn):
    """FASE 2: Cancelar Invoice (posted -> draft -> cancel)."""
    print("\n" + "=" * 60)
    print("FASE 2: Cancelar Invoice")
    print("=" * 60)

    # Ler estado atual
    invoice = conn.execute_kw(
        'account.move', 'read', [[ODOO_INVOICE_ID]],
        {'fields': ['state']}
    )
    state = invoice[0]['state'] if invoice else None
    print(f"  Estado atual: {state}")

    if state == 'cancel':
        print("  Invoice ja cancelada. Pulando.")
        return True

    # posted -> draft
    if state == 'posted':
        print("  Executando button_draft...")
        try:
            conn.execute_kw('account.move', 'button_draft', [[ODOO_INVOICE_ID]])
            print("  button_draft OK")
        except Exception as e:
            print(f"  button_draft FALHOU: {e}")
            print("  Tentando write state='draft' como fallback...")
            try:
                conn.execute_kw('account.move', 'write', [[ODOO_INVOICE_ID], {'state': 'draft'}])
                print("  write state='draft' OK")
            except Exception as e2:
                print(f"  write state='draft' FALHOU: {e2}")
                return False

    # draft -> cancel
    print("  Executando button_cancel...")
    try:
        conn.execute_kw('account.move', 'button_cancel', [[ODOO_INVOICE_ID]])
        print("  button_cancel OK")
    except Exception as e:
        print(f"  button_cancel FALHOU: {e}")
        print("  Tentando write state='cancel' como fallback...")
        try:
            conn.execute_kw('account.move', 'write', [[ODOO_INVOICE_ID], {'state': 'cancel'}])
            print("  write state='cancel' OK")
        except Exception as e2:
            print(f"  write state='cancel' FALHOU: {e2}")
            return False

    # Verificar
    invoice = conn.execute_kw(
        'account.move', 'read', [[ODOO_INVOICE_ID]],
        {'fields': ['state']}
    )
    final_state = invoice[0]['state'] if invoice else '???'
    print(f"  Estado final: {final_state}")
    return final_state == 'cancel'


def fase_3_reverter_picking(conn):
    """FASE 3: Reverter Picking (ponto mais delicado)."""
    print("\n" + "=" * 60)
    print("FASE 3: Reverter Picking")
    print("=" * 60)

    picking = conn.execute_kw(
        'stock.picking', 'read', [[ODOO_PICKING_ID]],
        {'fields': ['state']}
    )
    state = picking[0]['state'] if picking else None
    print(f"  Estado atual: {state}")

    if state == 'cancel':
        print("  Picking ja cancelado. Pulando.")
        return True

    # Tentativa 1: action_cancel
    print("\n  Tentativa 1: action_cancel no picking...")
    try:
        conn.execute_kw('stock.picking', 'action_cancel', [[ODOO_PICKING_ID]])
        print("  action_cancel OK")
        return True
    except Exception as e:
        print(f"  action_cancel FALHOU: {e}")

    # Tentativa 2: unlink dos move_lines
    print("\n  Tentativa 2: unlink dos move_lines...")
    try:
        conn.execute_kw('stock.move.line', 'unlink', [MOVE_LINE_IDS])
        print(f"  unlink de {len(MOVE_LINE_IDS)} move_lines OK")
        return True
    except Exception as e:
        print(f"  unlink FALHOU: {e}")

    # Tentativa 3: zerar quantity em cada move_line
    print("\n  Tentativa 3: zerar quantity nos move_lines...")
    try:
        for ml_id in MOVE_LINE_IDS:
            conn.execute_kw('stock.move.line', 'write', [[ml_id], {'quantity': 0}])
        print(f"  Zeradas {len(MOVE_LINE_IDS)} move_lines")
        return True
    except Exception as e:
        print(f"  Zerar quantity FALHOU: {e}")

    # Tentativa 4: forcar state do picking
    print("\n  Tentativa 4: write state='cancel' no picking...")
    try:
        conn.execute_kw('stock.picking', 'write', [[ODOO_PICKING_ID], {'state': 'cancel'}])
        print("  write state='cancel' OK")
        return True
    except Exception as e:
        print(f"  write state='cancel' FALHOU: {e}")

    print("\n  AVISO: Nenhuma tentativa de reversao do picking funcionou.")
    print("  O worker (etapa 10) e idempotente — continuando mesmo assim.")
    return False


def fase_4_cancelar_po(conn):
    """FASE 4: Cancelar PO."""
    print("\n" + "=" * 60)
    print("FASE 4: Cancelar PO")
    print("=" * 60)

    po = conn.execute_kw(
        'purchase.order', 'read', [[ODOO_PO_ID]],
        {'fields': ['state']}
    )
    state = po[0]['state'] if po else None
    print(f"  Estado atual: {state}")

    if state == 'cancel':
        print("  PO ja cancelada. Pulando.")
        return True

    print("  Executando button_cancel...")
    try:
        conn.execute_kw('purchase.order', 'button_cancel', [[ODOO_PO_ID]])
        print("  button_cancel OK")
    except Exception as e:
        print(f"  button_cancel FALHOU: {e}")
        print("  Tentando write state='cancel' como fallback...")
        try:
            conn.execute_kw('purchase.order', 'write', [[ODOO_PO_ID], {'state': 'cancel'}])
            print("  write state='cancel' OK")
        except Exception as e2:
            print(f"  write state='cancel' FALHOU: {e2}")
            return False

    # Verificar
    po = conn.execute_kw(
        'purchase.order', 'read', [[ODOO_PO_ID]],
        {'fields': ['state']}
    )
    final_state = po[0]['state'] if po else '???'
    print(f"  Estado final: {final_state}")
    return final_state == 'cancel'


def fase_5_desvincular_dfe(conn):
    """FASE 5: Desvincular DFe do PO (sem resetar l10n_br_status)."""
    print("\n" + "=" * 60)
    print("FASE 5: Desvincular DFe")
    print("=" * 60)

    dfe = conn.execute_kw(
        'l10n_br_ciel_it_account.dfe', 'read', [[ODOO_DFE_ID]],
        {'fields': ['purchase_id']}
    )
    purchase_id = dfe[0]['purchase_id'] if dfe else None
    print(f"  purchase_id atual: {purchase_id}")

    if not purchase_id:
        print("  DFe ja desvinculado. Pulando.")
        return True

    print("  Desvinculando (purchase_id = False)...")
    try:
        conn.execute_kw(
            'l10n_br_ciel_it_account.dfe', 'write',
            [[ODOO_DFE_ID], {'purchase_id': False}]
        )
        print("  Desvinculado OK")
    except Exception as e:
        print(f"  FALHOU: {e}")
        return False

    # Verificar
    dfe = conn.execute_kw(
        'l10n_br_ciel_it_account.dfe', 'read', [[ODOO_DFE_ID]],
        {'fields': ['purchase_id']}
    )
    purchase_id = dfe[0]['purchase_id'] if dfe else '???'
    print(f"  purchase_id apos: {purchase_id}")
    return not purchase_id


def fase_6_reset_local(app):
    """FASE 6: Reset do banco local."""
    print("\n" + "=" * 60)
    print("FASE 6: Reset local (DB)")
    print("=" * 60)

    with app.app_context():
        rec = db.session.get(RecebimentoLf, RECEBIMENTO_LF_ID)
        if not rec:
            print(f"  RecebimentoLf id={RECEBIMENTO_LF_ID} NAO ENCONTRADO!")
            return False

        print(f"  Estado atual: status={rec.status}, etapa={rec.etapa_atual}, fase={rec.fase_atual}")

        # Reset RecebimentoLf
        rec.status = 'pendente'
        rec.etapa_atual = 0
        rec.fase_atual = 0
        rec.ultimo_checkpoint_em = None
        rec.processado_em = None
        rec.erro_mensagem = None
        rec.tentativas = 0
        rec.job_id = None
        rec.odoo_po_id = None
        rec.odoo_po_name = None
        rec.odoo_picking_id = None
        rec.odoo_picking_name = None
        rec.odoo_invoice_id = None
        rec.odoo_invoice_name = None

        print("  RecebimentoLf resetado.")

        # Reset lotes
        lotes = rec.lotes.all()
        print(f"  Resetando {len(lotes)} lotes...")
        for lote in lotes:
            lote.processado = False
            lote.odoo_lot_id = None
            lote.odoo_move_line_id = None

        db.session.commit()
        print(f"  {len(lotes)} lotes resetados.")
        print(f"  Estado final: status={rec.status}, etapa={rec.etapa_atual}")
        return True


def fase_7_enfileirar_job(app):
    """FASE 7: Re-enfileirar job RQ."""
    print("\n" + "=" * 60)
    print("FASE 7: Re-enfileirar job RQ")
    print("=" * 60)

    with app.app_context():
        rec = db.session.get(RecebimentoLf, RECEBIMENTO_LF_ID)
        if not rec:
            print(f"  RecebimentoLf id={RECEBIMENTO_LF_ID} NAO ENCONTRADO!")
            return False

        if rec.status != 'pendente':
            print(f"  Status inesperado: {rec.status} (esperado: pendente)")
            return False

        try:
            from app.recebimento.workers.recebimento_lf_jobs import processar_recebimento_lf_job
            from app.portal.workers import enqueue_job
            from rq import Retry

            retry_config = Retry(max=3, interval=[30, 120, 480])

            job = enqueue_job(
                processar_recebimento_lf_job,
                rec.id,
                'reset-e2e-precos',
                queue_name='recebimento',
                timeout='30m',
                retry=retry_config,
            )
            rec.job_id = job.id
            db.session.commit()
            print(f"  Job enfileirado: {job.id}")
            print(f"  Fila: recebimento")
            print(f"  Timeout: 30m")
            print(f"  Retry: max=3, intervals=[30s, 120s, 480s]")
            return True
        except Exception as e:
            print(f"  ERRO ao enfileirar: {e}")
            logger.exception("Erro ao enfileirar job")
            return False


def main():
    print("=" * 60)
    print("RESET E2E: NF 12794 (RecebimentoLf id=1)")
    print("=" * 60)
    print()
    print("Este script vai:")
    print("  1. Ler estado Odoo (read-only)")
    print("  2. Cancelar Invoice 495837")
    print("  3. Reverter Picking 302074")
    print("  4. Cancelar PO 35782")
    print("  5. Desvincular DFe 37390")
    print("  6. Resetar banco local")
    print("  7. Re-enfileirar job RQ para reprocessamento")
    print()

    app = create_app()

    with app.app_context():
        conn = get_odoo_connection()
        if not conn.authenticate():
            print("ERRO: Falha na autenticacao com Odoo!")
            sys.exit(1)
        print("Conexao Odoo OK.\n")

        # FASE 1: Leitura (read-only)
        fase_1_ler_estado_odoo(conn)

        # Confirmacao
        print("\n" + "-" * 60)
        resposta = input("\nProsseguir com o reset? (sim/nao): ").strip().lower()
        if resposta not in ('sim', 's', 'yes', 'y'):
            print("Operacao cancelada pelo usuario.")
            sys.exit(0)

        # FASE 2: Cancelar Invoice
        ok = fase_2_cancelar_invoice(conn)
        if not ok:
            print("\n  AVISO: Invoice nao cancelada. Continuando mesmo assim...")

        # FASE 3: Reverter Picking
        ok = fase_3_reverter_picking(conn)
        if not ok:
            print("\n  AVISO: Picking nao revertido completamente. Worker e idempotente.")

        # FASE 4: Cancelar PO
        ok = fase_4_cancelar_po(conn)
        if not ok:
            print("\n  AVISO: PO nao cancelada. Continuando...")

        # FASE 5: Desvincular DFe
        ok = fase_5_desvincular_dfe(conn)
        if not ok:
            print("\n  AVISO: DFe nao desvinculado. Etapa 2 e idempotente.")

    # FASE 6: Reset local (contexto separado para commit limpo)
    ok = fase_6_reset_local(app)
    if not ok:
        print("\n  ERRO CRITICO: Reset local falhou!")
        sys.exit(1)

    # FASE 7: Enfileirar job
    ok = fase_7_enfileirar_job(app)
    if not ok:
        print("\n  ERRO: Job nao enfileirado. Verificar Redis e worker.")
        print("  Voce pode enfileirar manualmente via tela de status.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("RESET COMPLETO!")
    print("=" * 60)
    print()
    print("Proximos passos:")
    print("  1. Verificar que o worker RQ esta rodando (fila 'recebimento')")
    print("  2. Monitorar via tela de status: /recebimento/lf/status")
    print("  3. Apos processamento, verificar:")
    print("     - status=processado, etapa_atual=18")
    print("     - Precos no PO Odoo com precisao completa")
    print("     - Sem erros de tipo Decimal/float nos logs")


if __name__ == '__main__':
    main()
