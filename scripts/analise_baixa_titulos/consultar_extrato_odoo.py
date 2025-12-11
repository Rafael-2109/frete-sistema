# -*- coding: utf-8 -*-
"""
Script para consultar e analisar extrato bancário no Odoo.

Objetivo:
- Identificar linhas de extrato não conciliadas
- Identificar recebimentos (amount > 0)
- Entender a estrutura de dados disponível para matching

Autor: Sistema de Fretes
Data: 2025-12-11
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.odoo.utils.connection import get_odoo_connection


def listar_journals_banco():
    """Lista journals do tipo bank/cash que podem ter extrato."""
    print("\n" + "=" * 80)
    print("JOURNALS BANCÁRIOS (podem ter extrato)")
    print("=" * 80)

    conn = get_odoo_connection()
    if not conn.authenticate():
        print("Erro de autenticação")
        return

    journals = conn.search_read(
        'account.journal',
        [['type', 'in', ['bank', 'cash']]],
        fields=['id', 'name', 'code', 'type', 'company_id', 'bank_statements_source'],
        order='company_id, type, name'
    )

    print(f"\nTotal: {len(journals)} journals\n")

    # Agrupar por empresa
    por_empresa = {}
    for j in journals:
        company = j.get('company_id', [0, 'Sem empresa'])
        company_name = company[1] if isinstance(company, (list, tuple)) else str(company)
        if company_name not in por_empresa:
            por_empresa[company_name] = []
        por_empresa[company_name].append(j)

    for empresa, jnls in por_empresa.items():
        print(f"\n--- {empresa} ---")
        for j in jnls:
            source = j.get('bank_statements_source', 'undefined')
            print(f"  ID={j['id']:4} | {j['code']:10} | {j['type']:5} | {j['name'][:40]:40} | source={source}")

    return journals


def contar_linhas_extrato_por_journal():
    """Conta linhas de extrato por journal, separando conciliadas e não conciliadas."""
    print("\n" + "=" * 80)
    print("CONTAGEM DE LINHAS DE EXTRATO POR JOURNAL")
    print("=" * 80)

    conn = get_odoo_connection()
    if not conn.authenticate():
        print("Erro de autenticação")
        return

    # Buscar journals de banco/caixa
    journals = conn.search_read(
        'account.journal',
        [['type', 'in', ['bank', 'cash']]],
        fields=['id', 'name', 'code', 'company_id']
    )

    resultados = []

    for j in journals:
        # Contar total
        total = conn.execute_kw(
            'account.bank.statement.line', 'search_count',
            [[['journal_id', '=', j['id']]]]
        )

        # Contar não conciliadas
        nao_conciliadas = conn.execute_kw(
            'account.bank.statement.line', 'search_count',
            [[['journal_id', '=', j['id']], ['is_reconciled', '=', False]]]
        )

        # Contar não conciliadas com amount > 0 (recebimentos)
        recebimentos_pendentes = conn.execute_kw(
            'account.bank.statement.line', 'search_count',
            [[
                ['journal_id', '=', j['id']],
                ['is_reconciled', '=', False],
                ['amount', '>', 0]
            ]]
        )

        resultados.append({
            'journal_id': j['id'],
            'journal_code': j['code'],
            'journal_name': j['name'],
            'company': j['company_id'][1] if j['company_id'] else 'N/A',
            'total': total,
            'nao_conciliadas': nao_conciliadas,
            'recebimentos_pendentes': recebimentos_pendentes
        })

    print(f"\n{'Journal':<12} | {'Empresa':<25} | {'Total':>8} | {'Pendentes':>10} | {'Receb. Pend.':>12}")
    print("-" * 85)

    for r in resultados:
        if r['total'] > 0:  # Só mostrar journals com linhas
            print(f"{r['journal_code']:<12} | {r['company'][:25]:<25} | {r['total']:>8} | {r['nao_conciliadas']:>10} | {r['recebimentos_pendentes']:>12}")

    total_pendentes = sum(r['nao_conciliadas'] for r in resultados)
    total_receb_pend = sum(r['recebimentos_pendentes'] for r in resultados)
    print("-" * 85)
    print(f"{'TOTAL':<12} | {'':<25} | {'':<8} | {total_pendentes:>10} | {total_receb_pend:>12}")

    return resultados


def listar_recebimentos_nao_conciliados(journal_code=None, limit=20):
    """Lista recebimentos não conciliados de um journal específico ou todos."""
    print("\n" + "=" * 80)
    print(f"RECEBIMENTOS NÃO CONCILIADOS (limit={limit})")
    print("=" * 80)

    conn = get_odoo_connection()
    if not conn.authenticate():
        print("Erro de autenticação")
        return

    # Construir domínio
    domain = [
        ['is_reconciled', '=', False],
        ['amount', '>', 0]  # Recebimentos = amount positivo
    ]

    if journal_code:
        # Buscar journal_id pelo código
        journals = conn.search_read(
            'account.journal',
            [['code', '=', journal_code]],
            fields=['id'],
            limit=1
        )
        if journals:
            domain.append(['journal_id', '=', journals[0]['id']])
            print(f"Filtro: journal_code = {journal_code}")

    # Campos a buscar
    fields = [
        'id', 'date', 'payment_ref', 'amount', 'partner_id', 'partner_name',
        'journal_id', 'account_number', 'transaction_type', 'is_reconciled',
        'amount_residual', 'statement_id', 'move_id', 'create_date'
    ]

    linhas = conn.search_read(
        'account.bank.statement.line',
        domain,
        fields=fields,
        limit=limit
    )

    print(f"\nEncontradas: {len(linhas)} linhas\n")

    if not linhas:
        print("Nenhum recebimento não conciliado encontrado.")
        return []

    for linha in linhas:
        print(f"--- ID: {linha['id']} ---")
        print(f"  Data: {linha.get('date')}")
        print(f"  Journal: {linha.get('journal_id', [0, 'N/A'])[1] if linha.get('journal_id') else 'N/A'}")
        print(f"  Valor: R$ {linha.get('amount', 0):,.2f}")
        print(f"  Residual: R$ {linha.get('amount_residual', 0):,.2f}")
        print(f"  Label/Ref: {linha.get('payment_ref', 'N/A')}")
        print(f"  Partner: {linha.get('partner_id', [0, 'N/A'])[1] if linha.get('partner_id') else linha.get('partner_name', 'N/A')}")
        print(f"  Conta: {linha.get('account_number', 'N/A')}")
        print(f"  Tipo: {linha.get('transaction_type', 'N/A')}")
        print(f"  Statement: {linha.get('statement_id', [0, 'N/A'])[1] if linha.get('statement_id') else 'N/A'}")
        print()

    return linhas


def analisar_linha_extrato(linha_id):
    """Analisa uma linha de extrato específica em detalhes."""
    print("\n" + "=" * 80)
    print(f"ANÁLISE DETALHADA - LINHA DE EXTRATO ID: {linha_id}")
    print("=" * 80)

    conn = get_odoo_connection()
    if not conn.authenticate():
        print("Erro de autenticação")
        return

    # Buscar todos os campos da linha
    campos_principais = [
        'id', 'date', 'payment_ref', 'amount', 'amount_currency', 'amount_residual',
        'partner_id', 'partner_name', 'account_number',
        'journal_id', 'statement_id', 'move_id', 'payment_ids',
        'is_reconciled', 'transaction_type', 'transaction_details',
        'unique_import_id', 'online_transaction_identifier',
        'company_id', 'currency_id', 'foreign_currency_id',
        'create_date', 'write_date'
    ]

    linhas = conn.search_read(
        'account.bank.statement.line',
        [['id', '=', linha_id]],
        fields=campos_principais,
        limit=1
    )

    if not linhas:
        print(f"Linha {linha_id} não encontrada")
        return

    linha = linhas[0]

    print("\n=== DADOS DA LINHA ===")
    for campo, valor in linha.items():
        if isinstance(valor, (list, tuple)) and len(valor) == 2 and isinstance(valor[0], int):
            # Campo many2one
            print(f"  {campo}: {valor[1]} (ID={valor[0]})")
        elif isinstance(valor, dict):
            print(f"  {campo}: {json.dumps(valor, indent=4, default=str)}")
        else:
            print(f"  {campo}: {valor}")

    # Se tem move_id, buscar as linhas contábeis
    if linha.get('move_id'):
        move_id = linha['move_id'][0] if isinstance(linha['move_id'], (list, tuple)) else linha['move_id']

        print("\n=== LINHAS CONTÁBEIS (account.move.line) ===")
        move_lines = conn.search_read(
            'account.move.line',
            [['move_id', '=', move_id]],
            fields=[
                'id', 'name', 'account_id', 'debit', 'credit', 'balance',
                'amount_residual', 'reconciled', 'partner_id',
                'matched_credit_ids', 'matched_debit_ids', 'full_reconcile_id'
            ]
        )

        for ml in move_lines:
            print(f"\n  --- Line ID: {ml['id']} ---")
            account = ml.get('account_id', [0, 'N/A'])
            account_name = account[1] if isinstance(account, (list, tuple)) else str(account)
            print(f"    Conta: {account_name}")
            print(f"    Débito: {ml.get('debit', 0):,.2f} | Crédito: {ml.get('credit', 0):,.2f}")
            print(f"    Saldo: {ml.get('balance', 0):,.2f} | Residual: {ml.get('amount_residual', 0):,.2f}")
            print(f"    Reconciliado: {ml.get('reconciled')}")
            print(f"    matched_credit_ids: {ml.get('matched_credit_ids', [])}")
            print(f"    matched_debit_ids: {ml.get('matched_debit_ids', [])}")

    return linha


def exportar_recebimentos_pendentes(journal_code=None, output_file=None):
    """Exporta recebimentos pendentes para JSON."""
    print("\n" + "=" * 80)
    print("EXPORTANDO RECEBIMENTOS PENDENTES")
    print("=" * 80)

    conn = get_odoo_connection()
    if not conn.authenticate():
        print("Erro de autenticação")
        return

    domain = [
        ['is_reconciled', '=', False],
        ['amount', '>', 0]
    ]

    if journal_code:
        journals = conn.search_read(
            'account.journal',
            [['code', '=', journal_code]],
            fields=['id'],
            limit=1
        )
        if journals:
            domain.append(['journal_id', '=', journals[0]['id']])

    fields = [
        'id', 'date', 'payment_ref', 'amount', 'amount_residual',
        'partner_id', 'partner_name', 'account_number',
        'journal_id', 'statement_id', 'transaction_type',
        'company_id', 'create_date'
    ]

    linhas = conn.search_read(
        'account.bank.statement.line',
        domain,
        fields=fields,
        order='date desc, id desc'
    )

    print(f"Total: {len(linhas)} linhas")

    # Preparar para exportação
    dados = {
        'exportado_em': datetime.now().isoformat(),
        'filtro': {
            'journal_code': journal_code,
            'is_reconciled': False,
            'amount': '> 0 (recebimentos)'
        },
        'total': len(linhas),
        'linhas': linhas
    }

    if not output_file:
        output_file = f"scripts/analise_baixa_titulos/snapshots/recebimentos_pendentes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=2, default=str, ensure_ascii=False)

    print(f"Exportado para: {output_file}")

    return dados


def menu_interativo():
    """Menu interativo para explorar o extrato."""
    while True:
        print("\n" + "=" * 80)
        print("MENU - ANÁLISE DE EXTRATO BANCÁRIO ODOO")
        print("=" * 80)
        print("1. Listar journals bancários")
        print("2. Contar linhas de extrato por journal")
        print("3. Listar recebimentos não conciliados")
        print("4. Analisar linha de extrato específica")
        print("5. Exportar recebimentos pendentes para JSON")
        print("0. Sair")

        opcao = input("\nEscolha uma opção: ").strip()

        if opcao == '1':
            listar_journals_banco()
        elif opcao == '2':
            contar_linhas_extrato_por_journal()
        elif opcao == '3':
            journal = input("Journal code (Enter para todos): ").strip() or None
            limit = input("Limit (Enter para 20): ").strip()
            limit = int(limit) if limit else 20
            listar_recebimentos_nao_conciliados(journal, limit)
        elif opcao == '4':
            linha_id = input("ID da linha de extrato: ").strip()
            if linha_id.isdigit():
                analisar_linha_extrato(int(linha_id))
            else:
                print("ID inválido")
        elif opcao == '5':
            journal = input("Journal code (Enter para todos): ").strip() or None
            exportar_recebimentos_pendentes(journal)
        elif opcao == '0':
            print("Saindo...")
            break
        else:
            print("Opção inválida")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Análise de Extrato Bancário Odoo')
    parser.add_argument('--interativo', action='store_true', help='Modo interativo')
    parser.add_argument('--journals', action='store_true', help='Listar journals')
    parser.add_argument('--contar', action='store_true', help='Contar linhas por journal')
    parser.add_argument('--recebimentos', action='store_true', help='Listar recebimentos pendentes')
    parser.add_argument('--journal', type=str, help='Código do journal para filtrar')
    parser.add_argument('--limit', type=int, default=20, help='Limite de registros')
    parser.add_argument('--analisar', type=int, help='ID da linha para analisar')
    parser.add_argument('--exportar', action='store_true', help='Exportar recebimentos pendentes')

    args = parser.parse_args()

    if args.interativo:
        menu_interativo()
    elif args.journals:
        listar_journals_banco()
    elif args.contar:
        contar_linhas_extrato_por_journal()
    elif args.recebimentos:
        listar_recebimentos_nao_conciliados(args.journal, args.limit)
    elif args.analisar:
        analisar_linha_extrato(args.analisar)
    elif args.exportar:
        exportar_recebimentos_pendentes(args.journal)
    else:
        menu_interativo()
