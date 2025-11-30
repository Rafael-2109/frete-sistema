#!/usr/bin/env python3
"""
Investigação: ABATIMENTOS NO ODOO
=================================

Objetivo: Entender como abatimentos (descontos, devoluções, bonificações)
são registrados no Odoo e como afetam os títulos.

Autor: Sistema de Fretes
Data: 2025-11-28
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection


def buscar_notas_credito(connection):
    """Busca notas de crédito (credit_note) que podem ser abatimentos"""
    print(f"\n{'='*80}")
    print("1. NOTAS DE CRÉDITO (out_refund / credit_note)")
    print("   Usadas para: devoluções, abatimentos, bonificações")
    print('='*80)

    # Buscar notas de crédito recentes
    notas_credito = connection.search_read(
        'account.move',
        [
            ['move_type', '=', 'out_refund'],  # Nota de crédito de cliente
            ['state', '=', 'posted']
        ],
        fields=[
            'id', 'name', 'ref', 'partner_id', 'amount_total',
            'date', 'invoice_origin', 'payment_state',
            'reversed_entry_id', 'reversal_move_id'
        ],
        limit=10
    )

    if notas_credito:
        print(f"\n✅ Encontradas {len(notas_credito)} notas de crédito")
        for nc in notas_credito:
            print(f"\n{'─'*40}")
            print(f"ID: {nc.get('id')}")
            print(f"Número: {nc.get('name')}")
            print(f"Referência: {nc.get('ref')}")
            print(f"Cliente: {nc.get('partner_id')}")
            print(f"Valor: R$ {nc.get('amount_total')}")
            print(f"Data: {nc.get('date')}")
            print(f"Origem (fatura): {nc.get('invoice_origin')}")
            print(f"Payment State: {nc.get('payment_state')}")
            print(f"Reversed Entry: {nc.get('reversed_entry_id')}")
            print(f"Reversal Move: {nc.get('reversal_move_id')}")

            # Buscar linhas da nota de crédito
            if nc.get('id'):
                linhas = connection.search_read(
                    'account.move.line',
                    [
                        ['move_id', '=', nc.get('id')],
                        ['account_type', '=', 'asset_receivable']
                    ],
                    fields=['id', 'name', 'credit', 'debit', 'balance', 'reconciled', 'matched_debit_ids'],
                    limit=5
                )
                if linhas:
                    print(f"\n  📋 Linhas a receber da nota de crédito:")
                    for l in linhas:
                        print(f"    - ID: {l.get('id')} | Crédito: {l.get('credit')} | Reconciled: {l.get('reconciled')}")
                        print(f"      Matched Debit IDs: {l.get('matched_debit_ids')}")
    else:
        print("\n⚠️ Nenhuma nota de crédito encontrada")


def buscar_abatimentos_na_fatura(connection):
    """Busca faturas que tiveram abatimentos/descontos aplicados"""
    print(f"\n{'='*80}")
    print("2. FATURAS COM DESCONTO CONCEDIDO")
    print("   Campo: desconto_concedido (desconto após emissão)")
    print('='*80)

    # Buscar faturas com desconto
    faturas_desconto = connection.search_read(
        'account.move.line',
        [
            ['account_type', '=', 'asset_receivable'],
            ['desconto_concedido', '>', 0],
            ['parent_state', '=', 'posted']
        ],
        fields=[
            'id', 'x_studio_nf_e', 'l10n_br_cobranca_parcela',
            'balance', 'desconto_concedido', 'desconto_concedido_percentual',
            'amount_residual', 'l10n_br_paga', 'reconciled',
            'partner_id', 'date_maturity'
        ],
        limit=10
    )

    if faturas_desconto:
        print(f"\n✅ Encontradas {len(faturas_desconto)} parcelas com desconto concedido")
        for f in faturas_desconto:
            print(f"\n{'─'*40}")
            print(f"NF: {f.get('x_studio_nf_e')} - Parcela: {f.get('l10n_br_cobranca_parcela')}")
            print(f"Valor Original (Balance): R$ {f.get('balance')}")
            print(f"Desconto Concedido: R$ {f.get('desconto_concedido')}")
            print(f"Desconto %: {f.get('desconto_concedido_percentual')}")
            print(f"Valor Residual: R$ {f.get('amount_residual')}")
            print(f"Paga: {f.get('l10n_br_paga')}")
            print(f"Reconciliada: {f.get('reconciled')}")
    else:
        print("\n⚠️ Nenhuma parcela com desconto concedido encontrada")


def buscar_reconciliacoes_parciais(connection):
    """Busca títulos parcialmente pagos (podem ter abatimentos)"""
    print(f"\n{'='*80}")
    print("3. TÍTULOS COM PAGAMENTO PARCIAL")
    print("   Quando há abatimento, o título pode ser baixado parcialmente")
    print('='*80)

    # Buscar títulos com reconciliação mas não totalmente pagos
    titulos_parciais = connection.search_read(
        'account.move.line',
        [
            ['account_type', '=', 'asset_receivable'],
            ['x_studio_nf_e', '!=', False],
            ['reconciled', '=', False],  # Não totalmente reconciliado
            ['amount_residual', '>', 0],
            ['amount_residual', '<', 'balance'],  # Residual menor que original
            ['parent_state', '=', 'posted']
        ],
        fields=[
            'id', 'x_studio_nf_e', 'l10n_br_cobranca_parcela',
            'balance', 'amount_residual', 'matched_credit_ids',
            'partner_id'
        ],
        limit=10
    )

    # Corrigir: a comparação amount_residual < balance não funciona assim
    # Vamos buscar de outra forma
    titulos_parciais = connection.search_read(
        'account.move.line',
        [
            ['account_type', '=', 'asset_receivable'],
            ['x_studio_nf_e', '!=', False],
            ['matched_credit_ids', '!=', False],  # Tem alguma reconciliação
            ['amount_residual', '>', 0],  # Mas ainda tem saldo
            ['parent_state', '=', 'posted']
        ],
        fields=[
            'id', 'x_studio_nf_e', 'l10n_br_cobranca_parcela',
            'balance', 'amount_residual', 'matched_credit_ids',
            'partner_id', 'x_studio_status_de_pagamento'
        ],
        limit=10
    )

    if titulos_parciais:
        print(f"\n✅ Encontrados {len(titulos_parciais)} títulos parcialmente pagos")
        for t in titulos_parciais:
            print(f"\n{'─'*40}")
            print(f"NF: {t.get('x_studio_nf_e')} - Parcela: {t.get('l10n_br_cobranca_parcela')}")
            print(f"Valor Original: R$ {t.get('balance')}")
            print(f"Valor Residual: R$ {t.get('amount_residual')}")
            print(f"Valor Pago/Abatido: R$ {t.get('balance', 0) - t.get('amount_residual', 0)}")
            print(f"Status Pagamento: {t.get('x_studio_status_de_pagamento')}")
            print(f"Matched Credit IDs: {t.get('matched_credit_ids')}")

            # Investigar o que baixou parcialmente
            if t.get('matched_credit_ids'):
                reconciles = connection.search_read(
                    'account.partial.reconcile',
                    [['id', 'in', t.get('matched_credit_ids')]],
                    fields=['id', 'credit_move_id', 'amount', 'create_date'],
                    limit=5
                )
                for rec in reconciles:
                    print(f"\n  📌 Reconciliação parcial ID: {rec.get('id')}")
                    print(f"     Valor: R$ {rec.get('amount')}")
                    print(f"     Crédito: {rec.get('credit_move_id')}")
    else:
        print("\n⚠️ Nenhum título parcialmente pago encontrado")


def buscar_tipos_move_credito(connection):
    """Busca todos os tipos de documentos que geram crédito em contas a receber"""
    print(f"\n{'='*80}")
    print("4. TIPOS DE DOCUMENTOS QUE GERAM ABATIMENTO")
    print("   (linhas de CRÉDITO em contas a receber)")
    print('='*80)

    # Buscar linhas de crédito em contas a receber
    creditos = connection.search_read(
        'account.move.line',
        [
            ['account_type', '=', 'asset_receivable'],
            ['credit', '>', 0],
            ['parent_state', '=', 'posted']
        ],
        fields=['move_type', 'journal_id', 'payment_id', 'name', 'ref', 'credit', 'move_name'],
        limit=100
    )

    # Agrupar por move_type e journal
    tipos = {}
    for c in creditos:
        mt = c.get('move_type', 'unknown')
        journal = c.get('journal_id')
        journal_name = journal[1] if isinstance(journal, (list, tuple)) and len(journal) > 1 else str(journal)
        has_payment = bool(c.get('payment_id'))

        key = f"{mt} | {journal_name} | Payment: {has_payment}"
        if key not in tipos:
            tipos[key] = {'count': 0, 'examples': [], 'total_credit': 0}
        tipos[key]['count'] += 1
        tipos[key]['total_credit'] += c.get('credit', 0)
        if len(tipos[key]['examples']) < 2:
            tipos[key]['examples'].append({
                'name': c.get('name'),
                'ref': c.get('ref'),
                'move_name': c.get('move_name'),
                'credit': c.get('credit')
            })

    print(f"\n📊 Tipos de documentos que geram crédito (abatimento):")
    for key, info in sorted(tipos.items(), key=lambda x: -x[1]['count']):
        print(f"\n  [{key}]")
        print(f"    Quantidade: {info['count']}")
        print(f"    Total Crédito: R$ {info['total_credit']:,.2f}")
        print(f"    Exemplos:")
        for ex in info['examples']:
            print(f"      - {ex['move_name']} | {ex['name'][:50] if ex['name'] else '-'} | R$ {ex['credit']}")


def investigar_write_off(connection):
    """Busca write-offs (baixas por diferença/ajuste)"""
    print(f"\n{'='*80}")
    print("5. WRITE-OFFS (Baixas por ajuste/diferença)")
    print("   Usado quando há pequena diferença ou abatimento manual")
    print('='*80)

    # Buscar linhas de ajuste (geralmente em diário de ajuste)
    ajustes = connection.search_read(
        'account.move.line',
        [
            ['account_type', '=', 'asset_receivable'],
            ['credit', '>', 0],
            ['payment_id', '=', False],  # Não é pagamento
            ['parent_state', '=', 'posted']
        ],
        fields=['id', 'name', 'ref', 'credit', 'move_name', 'move_type', 'journal_id', 'partner_id', 'date'],
        limit=20
    )

    if ajustes:
        print(f"\n✅ Encontrados {len(ajustes)} lançamentos de crédito sem pagamento")
        print("   (Podem ser ajustes, write-offs ou notas de crédito)")

        for a in ajustes:
            journal = a.get('journal_id')
            journal_name = journal[1] if isinstance(journal, (list, tuple)) and len(journal) > 1 else str(journal)
            print(f"\n{'─'*40}")
            print(f"Move: {a.get('move_name')}")
            print(f"Nome: {a.get('name')}")
            print(f"Ref: {a.get('ref')}")
            print(f"Tipo: {a.get('move_type')}")
            print(f"Diário: {journal_name}")
            print(f"Valor Crédito: R$ {a.get('credit')}")
            print(f"Data: {a.get('date')}")
    else:
        print("\n⚠️ Nenhum write-off encontrado")


def main():
    """Função principal"""
    print("="*80)
    print("INVESTIGAÇÃO: ONDE FICAM OS ABATIMENTOS NO ODOO")
    print("="*80)

    app = create_app()

    with app.app_context():
        connection = get_odoo_connection()

        if not connection.authenticate():
            print("❌ Falha na autenticação com Odoo")
            return

        print("✅ Conectado ao Odoo!")

        # 1. Notas de crédito
        buscar_notas_credito(connection)

        # 2. Descontos concedidos
        buscar_abatimentos_na_fatura(connection)

        # 3. Títulos parcialmente pagos
        buscar_reconciliacoes_parciais(connection)

        # 4. Tipos de documentos
        buscar_tipos_move_credito(connection)

        # 5. Write-offs
        investigar_write_off(connection)

        print(f"\n\n{'='*80}")
        print("CONCLUSÃO: ONDE FICAM OS ABATIMENTOS NO ODOO")
        print('='*80)
        print("""
📌 TIPOS DE ABATIMENTOS E ONDE SÃO REGISTRADOS:

┌─────────────────────────────────────────────────────────────────────┐
│ 1. DESCONTO CONTRATUAL (na emissão)                                 │
│    - Registrado DIRETAMENTE no título (account.move.line)           │
│    - Campo: desconto_concedido / desconto_concedido_percentual      │
│    - NÃO gera documento separado                                    │
│    - Reduz o valor a receber desde a emissão                        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 2. NOTA DE CRÉDITO / DEVOLUÇÃO                                      │
│    - Documento: account.move (move_type = 'out_refund')             │
│    - Gera linha de CRÉDITO em contas a receber                      │
│    - Pode ser reconciliada com o título original                    │
│    - Comum para: devoluções, bonificações, abatimentos formais      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 3. PAGAMENTO COM DIFERENÇA (Write-off)                              │
│    - Documento: account.payment + ajuste                            │
│    - Cliente paga menos, diferença vai para conta de ajuste         │
│    - Comum para: descontos comerciais, arredondamentos              │
│    - Gera reconciliação parcial + write-off                         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 4. LANÇAMENTO DE AJUSTE MANUAL                                      │
│    - Documento: account.move (move_type = 'entry')                  │
│    - Lançamento contábil manual                                     │
│    - Débito em conta de despesa/abatimento                          │
│    - Crédito em contas a receber                                    │
│    - Reconciliado manualmente com o título                          │
└─────────────────────────────────────────────────────────────────────┘

📊 MECANISMO COMUM A TODOS (exceto desconto contratual):
   1. Gera linha de CRÉDITO em contas a receber
   2. Essa linha é RECONCILIADA com o título (DÉBITO)
   3. O amount_residual do título DIMINUI
   4. Se amount_residual = 0, título é considerado QUITADO
""")


if __name__ == '__main__':
    main()
