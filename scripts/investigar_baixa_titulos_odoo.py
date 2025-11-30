#!/usr/bin/env python3
"""
Investigação: Campos de Baixa de Títulos no Odoo
=================================================

Script para descobrir quais campos estão disponíveis no Odoo
relacionados à baixa/pagamento de títulos (contas a receber).

Modelos a investigar:
- account.move.line (linhas de movimento contábil - parcelas)
- account.move (faturas/documentos fiscais)
- account.payment (pagamentos)
- account.partial.reconcile (reconciliações parciais)

Autor: Sistema de Fretes
Data: 2025-11-28
"""

import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection
import json

def investigar_campos_modelo(connection, modelo: str, descricao: str):
    """Investiga campos de um modelo específico"""
    print(f"\n{'='*80}")
    print(f"MODELO: {modelo}")
    print(f"Descrição: {descricao}")
    print('='*80)

    try:
        # Buscar todos os campos do modelo
        campos = connection.execute_kw(
            modelo,
            'fields_get',
            [],
            {'attributes': ['string', 'type', 'help', 'selection']}
        )

        # Filtrar campos relacionados a pagamento/baixa
        keywords = [
            'pag', 'pay', 'paid', 'baixa', 'liquidat', 'reconcil',
            'quitad', 'recebi', 'receber', 'status', 'state', 'amount',
            'residual', 'saldo', 'balance', 'date', 'data'
        ]

        campos_relevantes = {}
        campos_todos = {}

        for nome_campo, info in campos.items():
            campos_todos[nome_campo] = info

            # Verificar se é relevante
            nome_lower = nome_campo.lower()
            string_lower = info.get('string', '').lower()
            help_lower = (info.get('help') or '').lower()

            for keyword in keywords:
                if keyword in nome_lower or keyword in string_lower or keyword in help_lower:
                    campos_relevantes[nome_campo] = info
                    break

        print(f"\n📊 Total de campos no modelo: {len(campos)}")
        print(f"🎯 Campos potencialmente relevantes: {len(campos_relevantes)}")

        # Mostrar campos relevantes
        if campos_relevantes:
            print(f"\n{'─'*40}")
            print("CAMPOS RELEVANTES:")
            print('─'*40)

            for nome, info in sorted(campos_relevantes.items()):
                tipo = info.get('type', '?')
                label = info.get('string', '')
                help_text = info.get('help', '')
                selection = info.get('selection', [])

                print(f"\n🔹 {nome}")
                print(f"   Label: {label}")
                print(f"   Tipo: {tipo}")
                if selection:
                    print(f"   Opções: {selection}")
                if help_text:
                    print(f"   Help: {help_text[:200]}...")

        return campos_todos, campos_relevantes

    except Exception as e:
        print(f"❌ Erro ao investigar modelo {modelo}: {e}")
        return {}, {}


def buscar_exemplo_titulo_pago(connection):
    """Busca um exemplo de título já pago para ver os valores"""
    print(f"\n{'='*80}")
    print("EXEMPLO: TÍTULO PAGO (para ver valores reais)")
    print('='*80)

    try:
        # Buscar um título marcado como pago
        titulos_pagos = connection.search_read(
            'account.move.line',
            [
                ['l10n_br_paga', '=', True],
                ['account_type', '=', 'asset_receivable'],
                ['x_studio_nf_e', '!=', False]
            ],
            fields=[
                'id', 'name', 'x_studio_nf_e', 'l10n_br_cobranca_parcela',
                'l10n_br_paga', 'balance', 'amount_residual', 'amount_currency',
                'reconciled', 'full_reconcile_id', 'matched_debit_ids', 'matched_credit_ids',
                'date', 'date_maturity', 'payment_id', 'statement_line_id',
                'x_studio_status_de_pagamento', 'parent_state', 'move_id'
            ],
            limit=5
        )

        if titulos_pagos:
            print(f"\n✅ Encontrados {len(titulos_pagos)} títulos pagos")
            for titulo in titulos_pagos:
                print(f"\n{'─'*40}")
                print(f"ID: {titulo.get('id')}")
                print(f"NF-e: {titulo.get('x_studio_nf_e')}")
                print(f"Parcela: {titulo.get('l10n_br_cobranca_parcela')}")
                print(f"l10n_br_paga: {titulo.get('l10n_br_paga')}")
                print(f"Balance: {titulo.get('balance')}")
                print(f"Amount Residual: {titulo.get('amount_residual')}")
                print(f"Reconciled: {titulo.get('reconciled')}")
                print(f"Full Reconcile ID: {titulo.get('full_reconcile_id')}")
                print(f"Matched Debit IDs: {titulo.get('matched_debit_ids')}")
                print(f"Matched Credit IDs: {titulo.get('matched_credit_ids')}")
                print(f"Payment ID: {titulo.get('payment_id')}")
                print(f"Statement Line ID: {titulo.get('statement_line_id')}")
                print(f"Status Pagamento: {titulo.get('x_studio_status_de_pagamento')}")
                print(f"Parent State: {titulo.get('parent_state')}")
        else:
            print("⚠️ Nenhum título pago encontrado")

    except Exception as e:
        print(f"❌ Erro ao buscar título pago: {e}")


def buscar_exemplo_titulo_aberto(connection):
    """Busca um exemplo de título em aberto para comparação"""
    print(f"\n{'='*80}")
    print("EXEMPLO: TÍTULO EM ABERTO (para comparação)")
    print('='*80)

    try:
        # Buscar um título em aberto
        titulos_abertos = connection.search_read(
            'account.move.line',
            [
                ['l10n_br_paga', '=', False],
                ['account_type', '=', 'asset_receivable'],
                ['x_studio_nf_e', '!=', False],
                ['balance', '>', 0]
            ],
            fields=[
                'id', 'name', 'x_studio_nf_e', 'l10n_br_cobranca_parcela',
                'l10n_br_paga', 'balance', 'amount_residual', 'amount_currency',
                'reconciled', 'full_reconcile_id', 'matched_debit_ids', 'matched_credit_ids',
                'date', 'date_maturity', 'payment_id', 'statement_line_id',
                'x_studio_status_de_pagamento', 'parent_state', 'move_id'
            ],
            limit=3
        )

        if titulos_abertos:
            print(f"\n✅ Encontrados {len(titulos_abertos)} títulos em aberto")
            for titulo in titulos_abertos:
                print(f"\n{'─'*40}")
                print(f"ID: {titulo.get('id')}")
                print(f"NF-e: {titulo.get('x_studio_nf_e')}")
                print(f"Parcela: {titulo.get('l10n_br_cobranca_parcela')}")
                print(f"l10n_br_paga: {titulo.get('l10n_br_paga')}")
                print(f"Balance: {titulo.get('balance')}")
                print(f"Amount Residual: {titulo.get('amount_residual')}")
                print(f"Reconciled: {titulo.get('reconciled')}")
                print(f"Full Reconcile ID: {titulo.get('full_reconcile_id')}")
                print(f"Status Pagamento: {titulo.get('x_studio_status_de_pagamento')}")
        else:
            print("⚠️ Nenhum título em aberto encontrado")

    except Exception as e:
        print(f"❌ Erro ao buscar título aberto: {e}")


def investigar_pagamentos(connection):
    """Investiga modelo account.payment"""
    print(f"\n{'='*80}")
    print("MODELO: account.payment (Pagamentos)")
    print('='*80)

    try:
        # Buscar exemplo de pagamento
        pagamentos = connection.search_read(
            'account.payment',
            [['payment_type', '=', 'inbound']],  # Recebimentos
            fields=[
                'id', 'name', 'payment_type', 'partner_type', 'partner_id',
                'amount', 'currency_id', 'date', 'state', 'ref',
                'reconciled_invoice_ids', 'reconciled_invoices_count',
                'move_id', 'journal_id'
            ],
            limit=5
        )

        if pagamentos:
            print(f"\n✅ Encontrados {len(pagamentos)} pagamentos (recebimentos)")
            for pag in pagamentos:
                print(f"\n{'─'*40}")
                print(f"ID: {pag.get('id')}")
                print(f"Name: {pag.get('name')}")
                print(f"Valor: {pag.get('amount')}")
                print(f"Data: {pag.get('date')}")
                print(f"State: {pag.get('state')}")
                print(f"Partner: {pag.get('partner_id')}")
                print(f"Reconciled Invoices: {pag.get('reconciled_invoice_ids')}")
                print(f"Ref: {pag.get('ref')}")
        else:
            print("⚠️ Nenhum pagamento encontrado")

    except Exception as e:
        print(f"❌ Erro ao investigar pagamentos: {e}")


def main():
    """Função principal"""
    print("="*80)
    print("INVESTIGAÇÃO: BAIXA DE TÍTULOS NO ODOO")
    print("="*80)

    app = create_app()

    with app.app_context():
        connection = get_odoo_connection()

        if not connection.authenticate():
            print("❌ Falha na autenticação com Odoo")
            return

        print("✅ Conectado ao Odoo com sucesso!")

        # 1. Investigar account.move.line (onde estão as parcelas)
        campos_aml, relevantes_aml = investigar_campos_modelo(
            connection,
            'account.move.line',
            'Linhas de movimento contábil - onde estão as parcelas a receber'
        )

        # 2. Investigar account.move (documento fiscal/fatura)
        campos_am, relevantes_am = investigar_campos_modelo(
            connection,
            'account.move',
            'Documento fiscal/fatura principal'
        )

        # 3. Investigar account.payment (pagamentos)
        campos_ap, relevantes_ap = investigar_campos_modelo(
            connection,
            'account.payment',
            'Pagamentos registrados no sistema'
        )

        # 4. Buscar exemplos reais
        buscar_exemplo_titulo_pago(connection)
        buscar_exemplo_titulo_aberto(connection)
        investigar_pagamentos(connection)

        # Salvar resultado completo em JSON
        resultado = {
            'account_move_line': {
                'total_campos': len(campos_aml),
                'campos_relevantes': {k: str(v) for k, v in relevantes_aml.items()}
            },
            'account_move': {
                'total_campos': len(campos_am),
                'campos_relevantes': {k: str(v) for k, v in relevantes_am.items()}
            },
            'account_payment': {
                'total_campos': len(campos_ap),
                'campos_relevantes': {k: str(v) for k, v in relevantes_ap.items()}
            }
        }

        # Salvar em arquivo
        output_file = os.path.join(os.path.dirname(__file__), 'resultado_investigacao_baixa_odoo.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)

        print(f"\n\n{'='*80}")
        print(f"✅ Resultado salvo em: {output_file}")
        print('='*80)


if __name__ == '__main__':
    main()
