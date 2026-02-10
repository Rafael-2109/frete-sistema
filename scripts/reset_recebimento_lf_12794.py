"""
Reset E2E: Reverter NF 12794 (RecebimentoLf id=1) e reprocessar.

Contexto:
    NF 12794 foi a primeira NF processada pelo fluxo automatizado de Recebimento LF.
    Apos a migration de precisao de quantidades (Numeric(15,3) -> Numeric(18,6)),
    precisamos reprocessar para validar que o fluxo E2E preserva quantidades completas.

    Os dados locais em recebimento_lf_lote.quantidade ainda carregam truncamento
    da era Numeric(15,3) (ex: 0.928000 em vez de 0.9284). Este script faz refresh
    das quantidades a partir do DFe Odoo (fonte de verdade) antes de resetar.

IDs fixos (apos ultimo processamento):
    - RecebimentoLf: id=1
    - PO Odoo: 35804 (C2615012)
    - Picking Odoo: 302139 (FB/IN/11530)
    - Invoice Odoo: 496258
    - DFe Odoo: 37390
    - Lotes locais: 17 registros (move_line IDs 217488968-217488984)

Fases:
    1. Ler estado Odoo (read-only)
    2. Cancelar Invoice
    3. Reverter Picking
    4. Cancelar PO
    5. Desvincular DFe
    6. Refresh quantidades dos lotes locais via DFe Odoo
    7. Reset local DB
    8. Re-processar direto (sem worker RQ)

Uso:
    source .venv/bin/activate
    python scripts/reset_recebimento_lf_12794.py
"""

import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.odoo.utils.connection import get_odoo_connection
from app.recebimento.models import RecebimentoLf
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# IDs fixos da NF 12794 (apos ultimo processamento)
RECEBIMENTO_LF_ID = 1
ODOO_PO_ID = 35804
ODOO_PICKING_ID = 302139
ODOO_INVOICE_ID = 496258
ODOO_DFE_ID = 37390
MOVE_LINE_IDS = list(range(217488968, 217488985))  # 217488968 a 217488984 (17 lotes)


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


def fase_6_refresh_quantidades_dfe(app, conn):
    """FASE 6: Refresh quantidades dos 17 lotes locais a partir do DFe Odoo."""
    print("\n" + "=" * 60)
    print("FASE 6: Refresh quantidades dos lotes (DFe -> local)")
    print("=" * 60)

    # Ler DFe lines do Odoo (fonte de verdade das quantidades NF-e)
    print(f"  Lendo DFe lines do Odoo (dfe_id={ODOO_DFE_ID})...")
    try:
        dfe_lines = conn.execute_kw(
            'l10n_br_ciel_it_account.dfe.line', 'search_read',
            [[['dfe_id', '=', ODOO_DFE_ID]]],
            {'fields': ['id', 'det_prod_qcom', 'det_prod_cprod', 'det_prod_xprod']}
        )
        print(f"  Encontradas {len(dfe_lines)} DFe lines no Odoo")
    except Exception as e:
        print(f"  ERRO ao ler DFe lines: {e}")
        return False

    if not dfe_lines:
        print("  AVISO: Nenhuma DFe line encontrada! Pulando refresh.")
        return False

    # Indexar por ID para lookup rapido
    dfe_lines_by_id = {line['id']: line for line in dfe_lines}

    with app.app_context():
        rec = db.session.get(RecebimentoLf, RECEBIMENTO_LF_ID)
        if not rec:
            print(f"  RecebimentoLf id={RECEBIMENTO_LF_ID} NAO ENCONTRADO!")
            return False

        lotes = rec.lotes.all()
        print(f"  Encontrados {len(lotes)} lotes locais")

        atualizados = 0
        sem_match = 0
        inalterados = 0

        for lote in lotes:
            if lote.odoo_dfe_line_id and lote.odoo_dfe_line_id in dfe_lines_by_id:
                dfe_line = dfe_lines_by_id[lote.odoo_dfe_line_id]
                old_qty = lote.quantidade
                new_qty = Decimal(str(dfe_line['det_prod_qcom']))

                if old_qty != new_qty:
                    lote.quantidade = new_qty
                    print(f"    Lote {lote.id} ({lote.lote_nome}): {old_qty} -> {new_qty}"
                          f"  [{dfe_line.get('det_prod_xprod', '?')[:30]}]")
                    atualizados += 1
                else:
                    inalterados += 1
            else:
                print(f"    Lote {lote.id} ({lote.lote_nome}): SEM MATCH no DFe "
                      f"(odoo_dfe_line_id={lote.odoo_dfe_line_id})")
                sem_match += 1

        db.session.commit()

        print(f"\n  Resumo:")
        print(f"    Atualizados: {atualizados}")
        print(f"    Inalterados: {inalterados}")
        print(f"    Sem match:   {sem_match}")

        return True


def fase_7_reset_local(app):
    """FASE 7: Reset do banco local."""
    print("\n" + "=" * 60)
    print("FASE 7: Reset local (DB)")
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

        # Reset lotes (manter quantidades atualizadas na fase 6)
        lotes = rec.lotes.all()
        print(f"  Resetando {len(lotes)} lotes (mantendo quantidades frescas)...")
        for lote in lotes:
            lote.processado = False
            lote.odoo_lot_id = None
            lote.odoo_move_line_id = None

        db.session.commit()
        print(f"  {len(lotes)} lotes resetados.")
        print(f"  Estado final: status={rec.status}, etapa={rec.etapa_atual}")
        return True


def fase_8_processar_direto(app):
    """FASE 8: Re-processar direto (sem worker RQ)."""
    print("\n" + "=" * 60)
    print("FASE 8: Processamento direto (sem worker RQ)")
    print("=" * 60)

    with app.app_context():
        rec = db.session.get(RecebimentoLf, RECEBIMENTO_LF_ID)
        if not rec:
            print(f"  RecebimentoLf id={RECEBIMENTO_LF_ID} NAO ENCONTRADO!")
            return False

        if rec.status != 'pendente':
            print(f"  Status inesperado: {rec.status} (esperado: pendente)")
            return False

        print(f"  Iniciando processamento do RecebimentoLf id={rec.id}...")
        print(f"  DFe: {rec.odoo_dfe_id}, NF: {rec.numero_nf}")

        try:
            from app.recebimento.services.recebimento_lf_odoo_service import RecebimentoLfOdooService

            service = RecebimentoLfOdooService()
            resultado = service.processar_recebimento(rec.id, 'reset-e2e-quantidades')

            print(f"\n  Resultado: {resultado}")

            # Recarregar para verificar estado final
            db.session.refresh(rec)
            print(f"  Estado final: status={rec.status}, etapa={rec.etapa_atual}")
            print(f"  PO: {rec.odoo_po_name} (id={rec.odoo_po_id})")
            print(f"  Picking: {rec.odoo_picking_name} (id={rec.odoo_picking_id})")
            print(f"  Invoice: {rec.odoo_invoice_name} (id={rec.odoo_invoice_id})")

            return rec.status == 'processado'
        except Exception as e:
            print(f"  ERRO ao processar: {e}")
            logger.exception("Erro no processamento direto")
            return False


def verificar_quantidades(app, conn):
    """Verificacao pos-processamento: compara quantidades locais vs Odoo."""
    print("\n" + "=" * 60)
    print("VERIFICACAO: Quantidades locais vs Odoo")
    print("=" * 60)

    with app.app_context():
        rec = db.session.get(RecebimentoLf, RECEBIMENTO_LF_ID)
        if not rec or rec.status != 'processado':
            print(f"  RecebimentoLf nao processado. Pulando verificacao.")
            return

        lotes = rec.lotes.all()
        lotes_com_ml = [l for l in lotes if l.odoo_move_line_id]

        if not lotes_com_ml:
            print("  Nenhum lote com move_line_id. Pulando.")
            return

        # Ler move lines do Odoo
        ml_ids = [l.odoo_move_line_id for l in lotes_com_ml]
        try:
            odoo_mls = conn.execute_kw(
                'stock.move.line', 'read', [ml_ids],
                {'fields': ['id', 'quantity']}
            )
            odoo_ml_by_id = {ml['id']: ml for ml in odoo_mls}
        except Exception as e:
            print(f"  ERRO ao ler move lines do Odoo: {e}")
            return

        divergencias = 0
        for lote in lotes_com_ml:
            odoo_ml = odoo_ml_by_id.get(lote.odoo_move_line_id)
            if not odoo_ml:
                print(f"    Lote {lote.id}: move_line {lote.odoo_move_line_id} NAO ENCONTRADO no Odoo")
                divergencias += 1
                continue

            local_qty = float(lote.quantidade) if lote.quantidade else 0
            odoo_qty = float(odoo_ml['quantity']) if odoo_ml.get('quantity') else 0

            if abs(local_qty - odoo_qty) > 0.0001:
                print(f"    DIVERGENCIA Lote {lote.id} ({lote.lote_nome}):"
                      f" local={local_qty} vs odoo={odoo_qty}")
                divergencias += 1

        if divergencias == 0:
            print(f"  TODAS as {len(lotes_com_ml)} quantidades conferem!")
        else:
            print(f"\n  {divergencias} divergencia(s) encontrada(s) de {len(lotes_com_ml)} lotes")


def main():
    print("=" * 60)
    print("RESET E2E: NF 12794 (RecebimentoLf id=1)")
    print("  Versao: v2 — Refresh quantidades + processamento direto")
    print("=" * 60)
    print()
    print("Este script vai:")
    print("  1. Ler estado Odoo (read-only)")
    print("  2. Cancelar Invoice 496258")
    print("  3. Reverter Picking 302139")
    print("  4. Cancelar PO 35804")
    print("  5. Desvincular DFe 37390")
    print("  6. Refresh quantidades dos lotes (DFe -> local)")
    print("  7. Resetar banco local")
    print("  8. Re-processar direto (sem worker RQ)")
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

    # FASE 6: Refresh quantidades (contexto separado, mas precisa conn)
    with app.app_context():
        conn = get_odoo_connection()
        conn.authenticate()
        ok = fase_6_refresh_quantidades_dfe(app, conn)
        if not ok:
            print("\n  AVISO: Refresh de quantidades falhou. Quantidades podem estar truncadas.")

    # FASE 7: Reset local (contexto separado para commit limpo)
    ok = fase_7_reset_local(app)
    if not ok:
        print("\n  ERRO CRITICO: Reset local falhou!")
        sys.exit(1)

    # FASE 8: Processar direto
    ok = fase_8_processar_direto(app)
    if not ok:
        print("\n  ERRO: Processamento direto falhou!")
        print("  Verifique os logs acima para identificar o problema.")
        print("  Voce pode tentar via tela de status: /recebimento/lf/status")
        sys.exit(1)

    # Verificacao pos-processamento
    with app.app_context():
        conn = get_odoo_connection()
        conn.authenticate()
        verificar_quantidades(app, conn)

    print("\n" + "=" * 60)
    print("RESET + REPROCESSAMENTO COMPLETO!")
    print("=" * 60)
    print()
    print("Verificacoes manuais recomendadas:")
    print("  1. Quantidades locais corretas (ex: 0.9284, nao 0.928000)")
    print("  2. Precos mantidos com 8 casas decimais")
    print("  3. information_schema: 0 colunas numeric(15,3) em picking_recebimento_*")
    print("  4. Status final: processado, etapa_atual=18")


if __name__ == '__main__':
    main()
