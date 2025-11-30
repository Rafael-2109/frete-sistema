#!/usr/bin/env python3
"""
Investigação: MECANISMO DE BAIXA DE TÍTULOS no Odoo
====================================================

Objetivo: Entender COMO um título é baixado no Odoo
- Existe documento que gera a baixa?
- A baixa é direta no título?
- Qual a relação entre account.payment, account.move.line e reconciliação?

Autor: Sistema de Fretes
Data: 2025-11-28
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection


def investigar_reconciliacao(connection, titulo_pago):
    """Investiga os detalhes da reconciliação de um título pago"""
    print(f"\n{'='*80}")
    print(f"RASTREANDO BAIXA DO TÍTULO: NF {titulo_pago.get('x_studio_nf_e')} - Parcela {titulo_pago.get('l10n_br_cobranca_parcela')}")
    print('='*80)

    titulo_id = titulo_pago.get('id')

    # 1. Verificar matched_credit_ids (créditos que baixaram este débito)
    matched_credit_ids = titulo_pago.get('matched_credit_ids', [])
    print(f"\n📌 matched_credit_ids: {matched_credit_ids}")

    if matched_credit_ids:
        print("\n🔍 Buscando detalhes dos créditos correspondentes (account.partial.reconcile)...")

        # Buscar os registros de reconciliação parcial
        reconciles = connection.search_read(
            'account.partial.reconcile',
            [['id', 'in', matched_credit_ids]],
            fields=[
                'id', 'debit_move_id', 'credit_move_id', 'amount',
                'debit_amount_currency', 'credit_amount_currency',
                'full_reconcile_id', 'create_date', 'write_date'
            ],
            limit=10
        )

        for rec in reconciles:
            print(f"\n{'─'*40}")
            print(f"Reconciliação ID: {rec.get('id')}")
            print(f"  Débito (título): {rec.get('debit_move_id')}")
            print(f"  Crédito (pagamento): {rec.get('credit_move_id')}")
            print(f"  Valor: {rec.get('amount')}")
            print(f"  Full Reconcile: {rec.get('full_reconcile_id')}")
            print(f"  Criado em: {rec.get('create_date')}")

            # Buscar detalhes da linha de crédito (o que baixou o título)
            credit_move_id = rec.get('credit_move_id')
            if credit_move_id and isinstance(credit_move_id, (list, tuple)):
                credit_line_id = credit_move_id[0]
                print(f"\n  📄 Buscando detalhes da LINHA DE CRÉDITO (o que gerou a baixa)...")

                credit_lines = connection.search_read(
                    'account.move.line',
                    [['id', '=', credit_line_id]],
                    fields=[
                        'id', 'name', 'ref', 'move_id', 'move_name', 'move_type',
                        'payment_id', 'statement_line_id', 'journal_id',
                        'partner_id', 'balance', 'credit', 'debit',
                        'date', 'parent_state'
                    ],
                    limit=1
                )

                if credit_lines:
                    cl = credit_lines[0]
                    print(f"\n  LINHA DE CRÉDITO (origem da baixa):")
                    print(f"    ID: {cl.get('id')}")
                    print(f"    Nome: {cl.get('name')}")
                    print(f"    Ref: {cl.get('ref')}")
                    print(f"    Move (documento): {cl.get('move_id')}")
                    print(f"    Move Name: {cl.get('move_name')}")
                    print(f"    Move Type: {cl.get('move_type')}")
                    print(f"    Payment ID: {cl.get('payment_id')}")
                    print(f"    Statement Line ID: {cl.get('statement_line_id')}")
                    print(f"    Journal: {cl.get('journal_id')}")
                    print(f"    Parceiro: {cl.get('partner_id')}")
                    print(f"    Balance: {cl.get('balance')}")
                    print(f"    Crédito: {cl.get('credit')}")
                    print(f"    Data: {cl.get('date')}")

                    # Se tem payment_id, buscar detalhes do pagamento
                    payment_id = cl.get('payment_id')
                    if payment_id and isinstance(payment_id, (list, tuple)):
                        print(f"\n  💰 PAGAMENTO ENCONTRADO! Buscando detalhes...")

                        payments = connection.search_read(
                            'account.payment',
                            [['id', '=', payment_id[0]]],
                            fields=[
                                'id', 'name', 'payment_type', 'partner_type',
                                'partner_id', 'amount', 'date', 'state', 'ref',
                                'payment_method_line_id', 'journal_id',
                                'reconciled_invoice_ids', 'move_id'
                            ],
                            limit=1
                        )

                        if payments:
                            pag = payments[0]
                            print(f"\n  DOCUMENTO DE PAGAMENTO:")
                            print(f"    ID: {pag.get('id')}")
                            print(f"    Número: {pag.get('name')}")
                            print(f"    Tipo: {pag.get('payment_type')}")
                            print(f"    Partner Type: {pag.get('partner_type')}")
                            print(f"    Parceiro: {pag.get('partner_id')}")
                            print(f"    Valor: {pag.get('amount')}")
                            print(f"    Data: {pag.get('date')}")
                            print(f"    Estado: {pag.get('state')}")
                            print(f"    Referência: {pag.get('ref')}")
                            print(f"    Método: {pag.get('payment_method_line_id')}")
                            print(f"    Diário: {pag.get('journal_id')}")
                            print(f"    Faturas Reconciliadas: {pag.get('reconciled_invoice_ids')}")
                            print(f"    Move ID: {pag.get('move_id')}")

                    # Se tem move_id, buscar detalhes do documento contábil
                    move_id = cl.get('move_id')
                    if move_id and isinstance(move_id, (list, tuple)):
                        print(f"\n  📑 Buscando detalhes do DOCUMENTO CONTÁBIL...")

                        moves = connection.search_read(
                            'account.move',
                            [['id', '=', move_id[0]]],
                            fields=[
                                'id', 'name', 'move_type', 'state', 'date',
                                'ref', 'payment_id', 'journal_id', 'partner_id',
                                'amount_total', 'payment_state'
                            ],
                            limit=1
                        )

                        if moves:
                            mv = moves[0]
                            print(f"\n  DOCUMENTO CONTÁBIL (account.move):")
                            print(f"    ID: {mv.get('id')}")
                            print(f"    Número: {mv.get('name')}")
                            print(f"    Tipo: {mv.get('move_type')}")
                            print(f"    Estado: {mv.get('state')}")
                            print(f"    Data: {mv.get('date')}")
                            print(f"    Referência: {mv.get('ref')}")
                            print(f"    Payment ID: {mv.get('payment_id')}")
                            print(f"    Diário: {mv.get('journal_id')}")
                            print(f"    Parceiro: {mv.get('partner_id')}")
                            print(f"    Valor Total: {mv.get('amount_total')}")
                            print(f"    Payment State: {mv.get('payment_state')}")


def investigar_full_reconcile(connection, titulo_pago):
    """Investiga o full_reconcile_id para entender a reconciliação completa"""
    full_reconcile = titulo_pago.get('full_reconcile_id')

    if not full_reconcile:
        print("\n⚠️ Título não tem full_reconcile_id")
        return

    full_rec_id = full_reconcile[0] if isinstance(full_reconcile, (list, tuple)) else full_reconcile

    print(f"\n{'='*80}")
    print(f"RECONCILIAÇÃO COMPLETA (full_reconcile_id = {full_rec_id})")
    print('='*80)

    # Buscar todas as linhas que participaram dessa reconciliação
    full_recs = connection.search_read(
        'account.full.reconcile',
        [['id', '=', full_rec_id]],
        fields=['id', 'name', 'partial_reconcile_ids', 'reconciled_line_ids', 'exchange_move_id'],
        limit=1
    )

    if full_recs:
        fr = full_recs[0]
        print(f"\nFull Reconcile: {fr.get('name')}")
        print(f"Partial Reconcile IDs: {fr.get('partial_reconcile_ids')}")
        print(f"Reconciled Line IDs: {fr.get('reconciled_line_ids')}")
        print(f"Exchange Move ID: {fr.get('exchange_move_id')}")

        # Buscar detalhes de todas as linhas reconciliadas
        rec_line_ids = fr.get('reconciled_line_ids', [])
        if rec_line_ids:
            print(f"\n📋 Buscando todas as {len(rec_line_ids)} linhas envolvidas na reconciliação...")

            rec_lines = connection.search_read(
                'account.move.line',
                [['id', 'in', rec_line_ids]],
                fields=[
                    'id', 'name', 'ref', 'move_name', 'move_type',
                    'debit', 'credit', 'balance', 'date',
                    'account_id', 'journal_id', 'partner_id',
                    'payment_id', 'x_studio_nf_e'
                ],
                limit=20
            )

            print(f"\n{'─'*80}")
            print("LINHAS ENVOLVIDAS NA RECONCILIAÇÃO:")
            print('─'*80)

            for rl in rec_lines:
                tipo = "DÉBITO (título)" if rl.get('debit', 0) > 0 else "CRÉDITO (pagamento)"
                print(f"\n  [{tipo}]")
                print(f"    ID: {rl.get('id')}")
                print(f"    Nome: {rl.get('name')}")
                print(f"    Ref: {rl.get('ref')}")
                print(f"    Move: {rl.get('move_name')}")
                print(f"    Move Type: {rl.get('move_type')}")
                print(f"    Débito: {rl.get('debit')}")
                print(f"    Crédito: {rl.get('credit')}")
                print(f"    Data: {rl.get('date')}")
                print(f"    Conta: {rl.get('account_id')}")
                print(f"    Diário: {rl.get('journal_id')}")
                print(f"    NF-e: {rl.get('x_studio_nf_e')}")
                print(f"    Payment ID: {rl.get('payment_id')}")


def investigar_tipos_documentos_baixa(connection):
    """Lista os tipos de documentos que podem gerar baixa"""
    print(f"\n{'='*80}")
    print("TIPOS DE DOCUMENTOS QUE PODEM GERAR BAIXA")
    print('='*80)

    # Buscar tipos de move_type usados em créditos (baixas)
    print("\n🔍 Buscando tipos de documentos usados em créditos (linhas com credit > 0)...")

    # Buscar linhas de crédito em contas a receber
    credit_lines = connection.search_read(
        'account.move.line',
        [
            ['account_type', '=', 'asset_receivable'],
            ['credit', '>', 0],
            ['parent_state', '=', 'posted']
        ],
        fields=['move_type', 'move_name', 'journal_id', 'payment_id', 'name', 'ref'],
        limit=50
    )

    # Agrupar por tipo
    tipos = {}
    for cl in credit_lines:
        mt = cl.get('move_type', 'unknown')
        journal = cl.get('journal_id')
        journal_name = journal[1] if isinstance(journal, (list, tuple)) and len(journal) > 1 else str(journal)

        if mt not in tipos:
            tipos[mt] = {'count': 0, 'journals': set(), 'examples': []}
        tipos[mt]['count'] += 1
        tipos[mt]['journals'].add(journal_name)
        if len(tipos[mt]['examples']) < 3:
            tipos[mt]['examples'].append({
                'name': cl.get('name'),
                'ref': cl.get('ref'),
                'move_name': cl.get('move_name'),
                'payment_id': cl.get('payment_id')
            })

    print(f"\n📊 Tipos de documentos encontrados:")
    for mt, info in sorted(tipos.items(), key=lambda x: -x[1]['count']):
        print(f"\n  {mt}: {info['count']} linhas")
        print(f"    Diários: {', '.join(info['journals'])}")
        print(f"    Exemplos:")
        for ex in info['examples']:
            print(f"      - {ex['move_name']} | {ex['name']} | Payment: {ex['payment_id']}")


def main():
    """Função principal"""
    print("="*80)
    print("INVESTIGAÇÃO: MECANISMO DE BAIXA DE TÍTULOS NO ODOO")
    print("="*80)

    app = create_app()

    with app.app_context():
        connection = get_odoo_connection()

        if not connection.authenticate():
            print("❌ Falha na autenticação com Odoo")
            return

        print("✅ Conectado ao Odoo!")

        # 1. Buscar um título pago para investigar
        print("\n🔍 Buscando título pago para análise detalhada...")

        titulos_pagos = connection.search_read(
            'account.move.line',
            [
                ['l10n_br_paga', '=', True],
                ['account_type', '=', 'asset_receivable'],
                ['x_studio_nf_e', '!=', False],
                ['reconciled', '=', True],
                ['full_reconcile_id', '!=', False]
            ],
            fields=[
                'id', 'name', 'x_studio_nf_e', 'l10n_br_cobranca_parcela',
                'l10n_br_paga', 'balance', 'amount_residual',
                'reconciled', 'full_reconcile_id',
                'matched_debit_ids', 'matched_credit_ids',
                'date', 'date_maturity', 'payment_id',
                'partner_id', 'move_id', 'move_name'
            ],
            limit=3
        )

        if titulos_pagos:
            # Investigar o primeiro título pago
            titulo = titulos_pagos[0]
            print(f"\n✅ Título encontrado: NF {titulo.get('x_studio_nf_e')} - Parcela {titulo.get('l10n_br_cobranca_parcela')}")

            # Investigar reconciliação
            investigar_reconciliacao(connection, titulo)

            # Investigar full_reconcile
            investigar_full_reconcile(connection, titulo)
        else:
            print("⚠️ Nenhum título pago encontrado para análise")

        # 2. Investigar tipos de documentos que geram baixa
        investigar_tipos_documentos_baixa(connection)

        print(f"\n\n{'='*80}")
        print("CONCLUSÃO DA INVESTIGAÇÃO")
        print('='*80)
        print("""
📌 RESUMO DO MECANISMO DE BAIXA NO ODOO:

1. A BAIXA NÃO É DIRETA NO TÍTULO
   - O campo l10n_br_paga é CALCULADO/DERIVADO
   - Não é uma simples marcação manual

2. A BAIXA É FEITA POR RECONCILIAÇÃO CONTÁBIL
   - Um documento de CRÉDITO é lançado
   - Esse crédito é "casado" (reconciliado) com o DÉBITO (título)
   - Quando o saldo residual chega a 0, o título é considerado pago

3. DOCUMENTOS QUE GERAM BAIXA:
   - account.payment (Pagamento/Recebimento)
   - Lançamentos de ajuste (account.move tipo 'entry')
   - Notas de crédito (credit_note)

4. TABELAS ENVOLVIDAS:
   - account.move.line: Linha do título (débito) e linha do pagamento (crédito)
   - account.partial.reconcile: Registro do "casamento" entre débito e crédito
   - account.full.reconcile: Reconciliação completa (quando saldo = 0)
   - account.payment: Documento de pagamento (opcional, mas comum)

5. FLUXO TÍPICO:
   Fatura Emitida → Linha de Débito (título a receber)
                           ↓
   Pagamento Registrado → Linha de Crédito
                           ↓
   Reconciliação → account.partial.reconcile
                           ↓
   Se saldo = 0 → account.full.reconcile → l10n_br_paga = True
""")


if __name__ == '__main__':
    main()
