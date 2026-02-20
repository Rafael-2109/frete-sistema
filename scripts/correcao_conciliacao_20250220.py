"""
Correção: Re-processar itens de conciliação Odoo falhados em 20/02/2026.

Contexto: Conciliação gerou 2 tipos de erro:
- ERRO 1: Lançamento 12201 — "Expected singleton: res.company(1, 4)" (cross-company)
- ERRO 2: 18 itens extrato — "Record does not exist" (credit_line_id stale)

3 correções de código já aplicadas:
1. comprovante_lancamento_service — validação de empresa antes de reconciliar
2. extrato_conciliacao_service._preparar_extrato_para_reconciliacao() — atualiza item.credit_line_id
3. extrato_conciliacao_service._conciliar_item_pagamento() — reordena operações per O12

Este script:
- Parte A: Re-processa 18 itens de extrato (lote 3532) com status ERRO
- Parte B: Completa reconciliação extrato do lançamento 12201 (payment já existe)

Uso:
    python scripts/correcao_conciliacao_20250220.py [--dry-run] [--skip-extrato] [--skip-lancamento]
"""
import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.financeiro.models import ExtratoItem

logger = logging.getLogger(__name__)

# IDs dos itens do lote 3532 com status ERRO (batch de 20/02/2026)
ITEM_IDS_ERRO = [
    19544, 19561, 19564, 19569, 19581, 19582, 19583, 19584, 19585,
    19596, 19601, 19603, 19606, 19618, 19620, 19630, 19632, 19635,
]

# Lançamento 12201 — dados fixos (payment já existe no Odoo)
LANC_12201 = {
    'id': 12201,
    'odoo_credit_line_id': 3131608,   # payment credit line
    'odoo_move_id': 418547,           # extrato move_id (via comprovante)
    'odoo_statement_line_id': 15889,  # extrato statement_line_id
    'odoo_partner_id': 205237,        # partner
    'valor_pago': 3660.27,
    'odoo_partner_name': None,        # será buscado do banco
}


def processar_itens_extrato(dry_run: bool):
    """Parte A: Re-processa 18 itens de extrato com status ERRO."""
    print(f"\n{'='*60}")
    print("PARTE A: ITENS DE EXTRATO (ERRO 2 — Record does not exist)")
    print(f"{'='*60}\n")

    itens = ExtratoItem.query.filter(
        ExtratoItem.id.in_(ITEM_IDS_ERRO)
    ).order_by(ExtratoItem.id).all()

    print(f"Encontrados: {len(itens)} de {len(ITEM_IDS_ERRO)} esperados\n")

    itens_erro = []
    for item in itens:
        status_ok = item.status == 'ERRO'
        print(
            f"  ID={item.id} | NF={item.titulo_nf} P{item.titulo_parcela} | "
            f"status={item.status} | move_id={item.move_id} | "
            f"credit_line={item.credit_line_id} | "
            f"{'→ ELEGÍVEL' if status_ok else '→ SKIP'}"
        )
        if status_ok:
            itens_erro.append(item)

    print(f"\n{len(itens_erro)} itens elegíveis para re-processamento")

    if dry_run:
        print("[DRY-RUN] Nenhuma alteração feita.\n")
        return 0, 0

    if not itens_erro:
        print("Nenhum item para processar.\n")
        return 0, 0

    # Reset status
    for item in itens_erro:
        item.status = 'APROVADO'
        item.mensagem = None
    db.session.commit()
    print(f"\n{len(itens_erro)} itens resetados: ERRO → APROVADO")

    # Re-executar conciliação
    from app.financeiro.services.extrato_conciliacao_service import ExtratoConciliacaoService
    service = ExtratoConciliacaoService()

    sucesso = 0
    erros = 0

    for item in itens_erro:
        try:
            db.session.refresh(item)
            item.status = 'CONCILIANDO'
            db.session.commit()

            resultado = service.conciliar_item(item)

            if resultado.get('sucesso') or resultado.get('success'):
                item.status = 'CONCILIADO'
                item.mensagem = 'Conciliado via script de correção 20/02'
                sucesso += 1
                print(f"  ✓ ID={item.id} NF={item.titulo_nf} P{item.titulo_parcela} — CONCILIADO")
            else:
                item.status = 'ERRO'
                erro_msg = resultado.get('erro') or resultado.get('error') or str(resultado)
                item.mensagem = f"Re-proc: {erro_msg[:500]}"
                erros += 1
                print(f"  ✗ ID={item.id} NF={item.titulo_nf} P{item.titulo_parcela} — {erro_msg[:100]}")

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            item.status = 'ERRO'
            item.mensagem = f"Re-proc exception: {str(e)[:500]}"
            db.session.commit()
            erros += 1
            print(f"  ✗ ID={item.id} NF={item.titulo_nf} P{item.titulo_parcela} — EXCEPTION: {e}")

    return sucesso, erros


def processar_lancamento_12201(dry_run: bool):
    """
    Parte B: Completa reconciliação extrato do lançamento 12201.

    O payment 36705 já existe no Odoo (etapas 1-3 do lancar_no_odoo completaram).
    A reconciliação payment↔título foi corretamente pulada (cross-company).
    Falta a reconciliação payment↔extrato (etapa 5 nunca executou).
    """
    print(f"\n{'='*60}")
    print("PARTE B: LANÇAMENTO 12201 (ERRO 1 — Expected singleton)")
    print(f"{'='*60}\n")

    from app.financeiro.models_comprovante import LancamentoComprovante

    lanc = db.session.get(LancamentoComprovante, 12201)
    if not lanc:
        print("  Lançamento 12201 não encontrado no banco.")
        return False

    print(f"  status={lanc.status}")
    print(f"  odoo_payment_id={lanc.odoo_payment_id}")
    print(f"  odoo_credit_line_id={lanc.odoo_credit_line_id}")
    print(f"  odoo_full_reconcile_id={lanc.odoo_full_reconcile_id}")

    comp = lanc.comprovante
    if not comp:
        print("  Comprovante associado não encontrado.")
        return False

    print(f"  odoo_statement_line_id={comp.odoo_statement_line_id}")
    print(f"  odoo_move_id={comp.odoo_move_id}")
    print(f"  odoo_is_reconciled={getattr(comp, 'odoo_is_reconciled', 'N/A')}")

    # Verificar se já foi reconciliado
    if lanc.status == 'LANCADO':
        print("\n  Lançamento já está LANCADO. Nada a fazer.")
        return True

    if not lanc.odoo_credit_line_id:
        print("\n  Sem credit_line_id do payment. Não é possível reconciliar.")
        return False

    if not comp.odoo_statement_line_id or not comp.odoo_move_id:
        print("\n  Sem vínculo com extrato Odoo. Não é possível reconciliar.")
        return False

    if dry_run:
        print("\n  [DRY-RUN] Faria: preparar_extrato → buscar_debit → reconciliar")
        return True

    # Executar reconciliação extrato
    try:
        from app.financeiro.services.baixa_pagamentos_service import BaixaPagamentosService

        baixa_service = BaixaPagamentosService()

        # 5a. Preparar extrato (consolidado: partner + rótulo + conta)
        partner_name = lanc.odoo_partner_name or ''
        rotulo = BaixaPagamentosService.formatar_rotulo_pagamento(
            valor=float(comp.valor_pago),
            nome_fornecedor=partner_name,
            data_pagamento=comp.data_pagamento,
        )
        print(f"\n  Preparando extrato: move={comp.odoo_move_id}, stmt={comp.odoo_statement_line_id}")
        baixa_service.preparar_extrato_para_reconciliacao(
            move_id=comp.odoo_move_id,
            statement_line_id=comp.odoo_statement_line_id,
            partner_id=lanc.odoo_partner_id,
            rotulo=rotulo,
        )

        # 5b. Buscar linha de débito do extrato
        debit_line_extrato = baixa_service.buscar_linha_debito_extrato(comp.odoo_move_id)
        if not debit_line_extrato:
            print("  ✗ Linha de débito do extrato não encontrada!")
            return False

        print(f"  Debit line extrato: {debit_line_extrato}")

        # 5c. Reconciliar payment com extrato
        credit_line_id = lanc.odoo_credit_line_id
        print(f"  Reconciliando: credit={credit_line_id} ↔ debit={debit_line_extrato}")
        baixa_service.reconciliar(credit_line_id, debit_line_extrato)
        print("  ✓ Reconciliado: payment ↔ extrato")

        # 5d. Buscar full_reconcile_id
        linha_ext = baixa_service.connection.search_read(
            'account.move.line',
            [['id', '=', debit_line_extrato]],
            fields=['full_reconcile_id'],
            limit=1,
        )
        if linha_ext and linha_ext[0].get('full_reconcile_id'):
            full_rec = linha_ext[0]['full_reconcile_id']
            full_rec_id = full_rec[0] if isinstance(full_rec, (list, tuple)) else full_rec
            lanc.odoo_full_reconcile_extrato_id = full_rec_id
            print(f"  full_reconcile_extrato_id: {full_rec_id}")

        # 6. Atualizar status
        from app.utils.timezone import agora_utc_naive
        lanc.status = 'LANCADO'
        lanc.lancado_em = agora_utc_naive()
        lanc.lancado_por = 'script_correcao_20250220'
        lanc.erro_lancamento = None

        comp.odoo_is_reconciled = True

        db.session.commit()
        print("  ✓ Status atualizado: LANCADO")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"  ✗ EXCEPTION: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Corrigir conciliação Odoo falhada em 20/02/2026'
    )
    parser.add_argument('--dry-run', action='store_true', help='Apenas diagnosticar')
    parser.add_argument('--skip-extrato', action='store_true', help='Pular parte A (itens extrato)')
    parser.add_argument('--skip-lancamento', action='store_true', help='Pular parte B (lanc 12201)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Parte A: Itens de extrato
        if not args.skip_extrato:
            sucesso_a, erros_a = processar_itens_extrato(args.dry_run)
        else:
            print("\n[SKIP] Parte A (itens extrato)")
            sucesso_a, erros_a = 0, 0

        # Parte B: Lançamento 12201
        if not args.skip_lancamento:
            ok_b = processar_lancamento_12201(args.dry_run)
        else:
            print("\n[SKIP] Parte B (lançamento 12201)")
            ok_b = None

        # Resultado final
        print(f"\n{'='*60}")
        print("RESULTADO FINAL")
        print(f"{'='*60}")
        if not args.skip_extrato:
            print(f"  Parte A: {sucesso_a} sucesso, {erros_a} erros (de {len(ITEM_IDS_ERRO)} itens)")
        if not args.skip_lancamento:
            status_b = "OK" if ok_b else ("DRY-RUN" if args.dry_run else "FALHOU")
            print(f"  Parte B: {status_b}")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
