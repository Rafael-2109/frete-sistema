# -*- coding: utf-8 -*-
"""
Remediação: 6 itens GRA1 com extrato não reconciliado (bug filtro debit>0)
=========================================================================

6 itens de ENTRADA (GRA1) marcados como CONCILIADO localmente mas com
extrato NÃO reconciliado no Odoo. Estes falharam silenciosamente porque
_trocar_conta_extrato() usava filtro ['debit', '>', 0], que não encontra
linhas de CRÉDITO na conta TRANSITÓRIA (recebíveis têm CREDIT, não DEBIT).

Bug corrigido em extrato_conciliacao_service.py (remoção do filtro debit>0
de _trocar_conta_extrato e _trocar_conta_extrato_para).

Itens afetados (R$ 185.951,73):
- ID 849:   A & B ALIMENTOS,  NF 138538, R$  10.980,00  (lote 71)
- ID 19293: L E G ALIMENTOS,  NF 143643, R$     105,00  (lote 516)
- ID 19297: JF FOOD SERVICE,  NF 143067, R$   7.835,10  (lote 516)
- ID 19299: PRASO PLATAFORMA, NF 142778, R$  24.349,37  (lote 516)
- ID 19300: PRASO DIST,       NF 142786, R$  21.477,94  (lote 516)
- ID 19302: PRASO DIST,       NF 142774, R$ 121.204,32  (lote 516)

Mensagem identificadora:
  "Conciliado: Saldo 0.0 -> 0.0" (com payment_id IS NULL e partial_reconcile_id IS NULL)

Fluxo de remediação por item:
1. Verificar se extrato já foi reconciliado no Odoo → sincronizar IDs
2. Buscar título no Odoo → matched_credit_ids
3. Buscar linha PENDENTES do payment
4. Trocar conta do extrato (TRANSITÓRIA → PENDENTES) — agora funciona!
5. Reconciliar payment_line ↔ extrato_line
6. Atualizar partial_reconcile_id no sistema local

Uso:
    source .venv/bin/activate
    python scripts/migrations/remediar_extrato_gra1_debit_filter_bug.py --dry-run
    python scripts/migrations/remediar_extrato_gra1_debit_filter_bug.py
    python scripts/migrations/remediar_extrato_gra1_debit_filter_bug.py --limit 2

Ref: Investigação de 2026-02-13 (bug _trocar_conta_extrato filtro debit>0)
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# IDs fixos dos 6 itens afetados
ITEM_IDS_AFETADOS = [849, 19293, 19297, 19299, 19300, 19302]


def buscar_itens_afetados():
    """
    Busca os 6 itens afetados pelo bug do filtro debit>0.

    Critérios de segurança:
    - IDs específicos (lista fixa)
    - status = 'CONCILIADO' (para não reprocessar se já corrigido)
    - payment_id IS NULL (confirma que não houve payment criado)
    """
    from app.financeiro.models import ExtratoItem

    itens = ExtratoItem.query.filter(
        ExtratoItem.id.in_(ITEM_IDS_AFETADOS),
        ExtratoItem.status == 'CONCILIADO',
        ExtratoItem.payment_id.is_(None),
    ).order_by(ExtratoItem.id).all()

    return itens


def remediar_item(item, conciliacao_service, dry_run=False):
    """
    Tenta reconciliar o extrato no Odoo para um item afetado.

    Fluxo idêntico ao remediar_strategy3_extrato_solto.py:
    1. Verificar se extrato já foi reconciliado no Odoo → sincronizar IDs
    2. Buscar título no Odoo → matched_credit_ids
    3. Buscar linha PENDENTES do payment
    4. Trocar conta do extrato (TRANSITÓRIA → PENDENTES)
    5. Reconciliar no Odoo
    6. Atualizar partial_reconcile_id localmente

    Returns:
        Dict com 'status' e 'mensagem'
    """
    from app.financeiro.models import ContasAReceber
    from app import db

    # Verificar dados mínimos
    if not item.titulo_receber_id:
        return {'status': 'erro', 'mensagem': 'Sem titulo_receber_id'}

    if not item.credit_line_id:
        return {'status': 'erro', 'mensagem': 'Sem credit_line_id'}

    if not item.move_id:
        return {'status': 'erro', 'mensagem': 'Sem move_id'}

    titulo_local = db.session.get(ContasAReceber, item.titulo_receber_id)
    if not titulo_local:
        return {
            'status': 'erro',
            'mensagem': f'Titulo {item.titulo_receber_id} não encontrado'
        }

    conn = conciliacao_service.connection

    # =====================================================================
    # PASSO 1: Verificar se extrato já foi reconciliado no Odoo
    # =====================================================================
    try:
        linhas = conn.search_read(
            'account.move.line',
            [['id', '=', item.credit_line_id]],
            fields=[
                'id', 'reconciled', 'account_id',
                'matched_debit_ids', 'matched_credit_ids',
                'full_reconcile_id'
            ]
        )

        if linhas and linhas[0].get('reconciled'):
            # Já reconciliado no Odoo! Apenas sincronizar IDs
            matched = (
                linhas[0].get('matched_debit_ids', [])
                or linhas[0].get('matched_credit_ids', [])
            )
            full_rec = linhas[0].get('full_reconcile_id')

            if not dry_run:
                if matched:
                    item.partial_reconcile_id = matched[-1]
                if full_rec:
                    item.full_reconcile_id = (
                        full_rec[0]
                        if isinstance(full_rec, (list, tuple))
                        else full_rec
                    )
                item.mensagem = (
                    'Extrato já reconciliado no Odoo - IDs sincronizados '
                    '(remediação bug debit>0)'
                )

            return {
                'status': 'ja_reconciliado',
                'partial_reconcile_id': matched[-1] if matched else None,
                'mensagem': 'Extrato já reconciliado no Odoo - sincronizado'
            }

        # Mostrar estado atual da linha
        if linhas:
            account = linhas[0].get('account_id', '?')
            print(f"  Estado Odoo: credit_line {item.credit_line_id} → "
                  f"reconciled={linhas[0].get('reconciled')}, "
                  f"account={account}")

    except Exception as e:
        logger.warning(f"  Erro ao verificar linha {item.credit_line_id}: {e}")

    # =====================================================================
    # PASSO 2: Buscar título no Odoo
    # =====================================================================
    titulo_odoo = conciliacao_service._buscar_titulo_odoo_multicompany(
        titulo_local.titulo_nf, titulo_local.parcela
    )

    if not titulo_odoo:
        return {
            'status': 'erro',
            'mensagem': (
                f'Título NF {titulo_local.titulo_nf} '
                f'P{titulo_local.parcela} não encontrado no Odoo'
            )
        }

    matched_credit_ids = titulo_odoo.get('matched_credit_ids', [])
    if not matched_credit_ids:
        return {
            'status': 'sem_payment',
            'mensagem': 'Título sem matched_credit_ids no Odoo'
        }

    # =====================================================================
    # PASSO 3: Buscar linha PENDENTES do payment
    # =====================================================================
    payment_pendente_line = conciliacao_service._buscar_linha_payment_pendentes(
        matched_credit_ids
    )

    if not payment_pendente_line:
        return {
            'status': 'sem_linha',
            'mensagem': 'Sem linha PENDENTES disponível no payment'
        }

    payment_pendente_line_id = payment_pendente_line['id']
    payment_account_id = payment_pendente_line.get('account_id')
    if isinstance(payment_account_id, (list, tuple)):
        payment_account_id = payment_account_id[0]

    if dry_run:
        return {
            'status': 'reconciliavel',
            'payment_line_id': payment_pendente_line_id,
            'account_id': payment_account_id,
            'mensagem': (
                f'Linha PENDENTES encontrada: {payment_pendente_line_id} '
                f'(conta={payment_account_id}). Pronto para reconciliar.'
            )
        }

    # =====================================================================
    # PASSO 4: Executar reconciliação no Odoo
    # =====================================================================
    try:
        from app.financeiro.services.extrato_conciliacao_service import (
            CONTA_PAGAMENTOS_PENDENTES,
        )

        # Trocar conta do extrato (TRANSITÓRIA → PENDENTES ou bancária)
        # Este é o passo que falhava antes do fix (filtro debit>0)
        if payment_account_id == CONTA_PAGAMENTOS_PENDENTES:
            troca_ok = conciliacao_service._trocar_conta_extrato(item.move_id)
        else:
            troca_ok = conciliacao_service._trocar_conta_extrato_para(
                item.move_id, payment_account_id
            )

        if not troca_ok:
            return {
                'status': 'erro_troca',
                'mensagem': (
                    f'Falha ao trocar conta do extrato '
                    f'(move {item.move_id}). Verificar Odoo manualmente.'
                )
            }

        print(f"  Conta trocada com sucesso (move {item.move_id})")

        # Reconciliar: payment_line ↔ extrato_line
        conciliacao_service._executar_reconcile(
            payment_pendente_line_id, item.credit_line_id
        )

        # Atualizar partner e rótulo do extrato
        p_id, p_name = conciliacao_service._extrair_partner_dados(titulo_odoo)
        conciliacao_service._atualizar_campos_extrato(item, p_id, p_name)

        # Buscar partial_reconcile_id criado
        partial_id = conciliacao_service._buscar_partial_reconcile_linha(
            payment_pendente_line_id
        )
        item.partial_reconcile_id = partial_id
        item.mensagem = (
            f"Extrato reconciliado no Odoo (remediação bug debit>0) "
            f"(partial_reconcile={partial_id}, conta={payment_account_id})"
        )

        return {
            'status': 'reconciliado',
            'partial_reconcile_id': partial_id,
            'mensagem': (
                f'Reconciliado com sucesso '
                f'(partial={partial_id}, conta={payment_account_id})'
            )
        }

    except Exception as e:
        return {
            'status': 'erro_reconciliacao',
            'mensagem': f'Erro ao reconciliar no Odoo: {e}'
        }


def executar():
    parser = argparse.ArgumentParser(
        description=(
            'Remediação: 6 itens GRA1 com extrato não reconciliado '
            '(bug filtro debit>0 em _trocar_conta_extrato)'
        )
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Simular sem executar reconciliações no Odoo'
    )
    parser.add_argument(
        '--limit', type=int, default=None,
        help='Limitar quantidade de itens a processar'
    )
    args = parser.parse_args()

    from app import create_app
    from app.financeiro.services.extrato_conciliacao_service import (
        ExtratoConciliacaoService,
    )

    app = create_app()
    with app.app_context():
        from app import db

        print("=" * 70)
        print("REMEDIACAO: 6 itens GRA1 (bug filtro debit>0)")
        print(f"Modo: {'DRY-RUN (simulacao)' if args.dry_run else 'EXECUCAO REAL'}")
        print("=" * 70)

        # Buscar itens
        itens = buscar_itens_afetados()

        if args.limit:
            itens = itens[:args.limit]

        print(f"\nItens encontrados: {len(itens)} de {len(ITEM_IDS_AFETADOS)} esperados")

        if len(itens) < len(ITEM_IDS_AFETADOS):
            ids_encontrados = {i.id for i in itens}
            ids_faltando = set(ITEM_IDS_AFETADOS) - ids_encontrados
            if ids_faltando:
                print(f"  IDs não encontrados (já remediados?): {sorted(ids_faltando)}")

        if not itens:
            print("Nenhum item para remediar. Todos já foram corrigidos.")
            return

        # Mostrar resumo
        valor_total = sum(abs(i.valor or 0) for i in itens)
        print(f"Valor total: R$ {valor_total:,.2f}")

        # Listar lotes afetados
        lotes = set(i.lote_id for i in itens)
        print(f"Lotes afetados: {sorted(lotes)}")
        print()

        # Inicializar serviço de conciliação
        service = ExtratoConciliacaoService()

        # Contadores
        stats = {
            'reconciliado': 0,
            'ja_reconciliado': 0,
            'reconciliavel': 0,
            'sem_linha': 0,
            'sem_payment': 0,
            'erro': 0,
            'erro_troca': 0,
            'erro_reconciliacao': 0,
        }

        for idx, item in enumerate(itens, 1):
            print(
                f"--- [{idx}/{len(itens)}] Item {item.id}: "
                f"NF {item.titulo_nf} P{item.titulo_parcela} "
                f"R$ {abs(item.valor or 0):,.2f} "
                f"({item.titulo_cliente}) ---"
            )

            try:
                resultado = remediar_item(item, service, dry_run=args.dry_run)
                status = resultado['status']

                # Commit atômico por item (sucesso salva imediatamente)
                if not args.dry_run and status in (
                    'reconciliado', 'ja_reconciliado'
                ):
                    db.session.commit()

            except Exception as e:
                db.session.rollback()
                resultado = {'status': 'erro', 'mensagem': str(e)}
                status = 'erro'

            stats[status] = stats.get(status, 0) + 1

            indicador = {
                'reconciliado': '[OK]',
                'ja_reconciliado': '[SYNC]',
                'reconciliavel': '[DRY]',
                'sem_linha': '[SKIP]',
                'sem_payment': '[SKIP]',
                'erro': '[ERRO]',
                'erro_troca': '[ERRO]',
                'erro_reconciliacao': '[ERRO]',
            }.get(status, '[???]')

            print(f"  {indicador} {resultado['mensagem']}")
            print()

        # Resumo final
        print()
        print("=" * 70)
        print("RESUMO")
        print("=" * 70)
        for k, v in stats.items():
            if v > 0:
                print(f"  {k}: {v}")

        total_sucesso = stats['reconciliado'] + stats['ja_reconciliado']
        total_pendente = stats['sem_linha'] + stats['sem_payment']
        total_erro = (
            stats['erro'] + stats['erro_troca'] + stats['erro_reconciliacao']
        )

        print()
        if args.dry_run:
            reconciliavel = stats['reconciliavel']
            print(
                f"DRY-RUN: {reconciliavel} item(ns) reconciliáveis. "
                f"Execute sem --dry-run para reconciliar no Odoo."
            )
        else:
            print(
                f"Resultado: {total_sucesso} sucesso, "
                f"{total_pendente} sem linha, "
                f"{total_erro} erro(s)"
            )

        print()


if __name__ == '__main__':
    executar()
