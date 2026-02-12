# -*- coding: utf-8 -*-
"""
Remediação: Reconciliar extratos soltos no Odoo (Strategy 3 fallback)
=====================================================================

78 itens de ENTRADA marcados como CONCILIADO localmente mas com
extrato NÃO reconciliado no Odoo. Estes passaram pelo fallback
Strategy 3 de _marcar_conciliado_local().

Mensagem identificadora:
  "Título já quitado no Odoo - extrato não reconciliado
   (payment original não usou conta PENDENTES e extrato não reconciliado no Odoo)"

O script re-executa a lógica de reconciliação melhorada:
1. Busca título no Odoo → matched_credit_ids
2. Busca linha PENDENTES do payment
3. Troca conta do extrato (TRANSITÓRIA → PENDENTES)
4. Reconcilia payment_line ↔ extrato_line
5. Atualiza partial_reconcile_id no sistema local

Se o extrato já tiver sido reconciliado no Odoo (manualmente desde
a marcação local), apenas sincroniza os IDs.

Uso:
    source .venv/bin/activate
    python scripts/migrations/remediar_strategy3_extrato_solto.py --dry-run
    python scripts/migrations/remediar_strategy3_extrato_solto.py
    python scripts/migrations/remediar_strategy3_extrato_solto.py --limit 5

Ref: Investigação de 2026-02-11 (78 itens, R$ 1.04M)
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def buscar_itens_strategy3():
    """
    Busca os itens que passaram pelo Strategy 3 fallback.

    Critérios:
    - status = 'CONCILIADO'
    - partial_reconcile_id IS NULL
    - full_reconcile_id IS NULL
    - mensagem LIKE 'Título já quitado no Odoo - extrato não reconciliado%'
    """
    from app.financeiro.models import ExtratoItem

    itens = ExtratoItem.query.filter(
        ExtratoItem.status == 'CONCILIADO',
        ExtratoItem.partial_reconcile_id.is_(None),
        ExtratoItem.full_reconcile_id.is_(None),
        ExtratoItem.mensagem.like(
            'Título já quitado no Odoo - extrato não reconciliado%'
        )
    ).order_by(ExtratoItem.id).all()

    return itens


def remediar_item(item, conciliacao_service, dry_run=False):
    """
    Tenta reconciliar o extrato no Odoo para um item Strategy 3.

    Fluxo:
    1. Verificar se extrato já foi reconciliado no Odoo → sincronizar IDs
    2. Buscar título no Odoo → matched_credit_ids
    3. Buscar linha PENDENTES do payment
    4. Trocar conta do extrato
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
                'id', 'reconciled',
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
                    '(remediação Strategy 3)'
                )
                db.session.flush()

            return {
                'status': 'ja_reconciliado',
                'partial_reconcile_id': matched[-1] if matched else None,
                'mensagem': 'Extrato já reconciliado no Odoo - sincronizado'
            }
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
                f'(conta={payment_account_id})'
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
        if payment_account_id == CONTA_PAGAMENTOS_PENDENTES:
            conciliacao_service._trocar_conta_extrato(item.move_id)
        else:
            conciliacao_service._trocar_conta_extrato_para(
                item.move_id, payment_account_id
            )

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
            f"Extrato reconciliado com payment existente (remediação) "
            f"(partial_reconcile={partial_id}, conta={payment_account_id})"
        )
        db.session.flush()

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
            'Remediação: reconciliar extratos soltos no Odoo '
            '(Strategy 3 fallback)'
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
        print("REMEDIACAO: Extrato solto no Odoo (Strategy 3 fallback)")
        print(f"Modo: {'DRY-RUN (simulacao)' if args.dry_run else 'EXECUCAO REAL'}")
        print("=" * 70)

        # Buscar itens
        itens = buscar_itens_strategy3()

        if args.limit:
            itens = itens[:args.limit]

        print(f"\nItens encontrados: {len(itens)}")

        if not itens:
            print("Nenhum item para remediar.")
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
            'reconciliavel': 0,  # dry-run only
            'sem_linha': 0,
            'sem_payment': 0,
            'erro': 0,
            'erro_reconciliacao': 0,
        }

        for idx, item in enumerate(itens, 1):
            print(
                f"--- [{idx}/{len(itens)}] Item {item.id}: "
                f"NF {item.titulo_nf} P{item.titulo_parcela} "
                f"R$ {abs(item.valor or 0):,.2f} ---"
            )

            resultado = remediar_item(item, service, dry_run=args.dry_run)
            status = resultado['status']
            stats[status] = stats.get(status, 0) + 1

            indicador = {
                'reconciliado': '[OK]',
                'ja_reconciliado': '[SYNC]',
                'reconciliavel': '[DRY]',
                'sem_linha': '[SKIP]',
                'sem_payment': '[SKIP]',
                'erro': '[ERRO]',
                'erro_reconciliacao': '[ERRO]',
            }.get(status, '[???]')

            print(f"  {indicador} {resultado['mensagem']}")

        if not args.dry_run:
            db.session.commit()

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
        total_erro = stats['erro'] + stats['erro_reconciliacao']

        print()
        if args.dry_run:
            reconciliavel = stats['reconciliavel']
            print(
                f"DRY-RUN: {reconciliavel} reconciliaveis, "
                f"{stats['ja_reconciliado']} ja reconciliados, "
                f"{total_pendente} sem linha disponivel, "
                f"{total_erro} com erro"
            )
            print("Para executar: remova --dry-run")
        else:
            print(
                f"RESULTADO: {total_sucesso} reconciliados, "
                f"{total_pendente} sem linha disponivel, "
                f"{total_erro} com erro"
            )


if __name__ == '__main__':
    executar()
