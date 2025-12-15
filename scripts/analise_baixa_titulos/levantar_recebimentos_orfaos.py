# -*- coding: utf-8 -*-
"""
Script para levantar recebimentos orfaos no Odoo.

Objetivo:
- Identificar account.payment do tipo inbound (recebimentos)
- Que estao postados (state = posted)
- Mas NAO tem reconciliacao com titulos (matched_debit_ids vazio)

Estes sao os recebimentos que foram criados mas nao vinculados
a nenhum titulo, provavelmente por falta de saldo na parcela
no momento da tentativa de reconciliacao.

Autor: Sistema de Fretes
Data: 2025-12-15
"""

import sys
import os
from datetime import datetime, date
from typing import List, Dict, Optional

import pandas as pd

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.odoo.utils.connection import get_odoo_connection


def buscar_pagamentos_conciliados_mesma_nf(conn, ref: str, partner_id: int, orfao_id: int) -> List[Dict]:
    """
    Busca pagamentos CONCILIADOS (corretos) da mesma NF para comparacao.

    Args:
        conn: Conexao Odoo
        ref: Referencia do pagamento orfao (nome da NF)
        partner_id: ID do parceiro
        orfao_id: ID do pagamento orfao (para excluir da busca)

    Returns:
        Lista de pagamentos conciliados da mesma NF
    """
    if not ref:
        return []

    # Limpar ref para busca (remover prefixos como "DESCONTO - ", etc)
    ref_limpa = ref.replace('DESCONTO - ', '').replace('ACORDO - ', '').replace('DEVOLUCAO - ', '').replace('JUROS - ', '').strip()

    if not ref_limpa:
        return []

    # Buscar pagamentos do mesmo partner com mesma ref
    pagamentos = conn.search_read(
        'account.payment',
        [
            ['payment_type', '=', 'inbound'],
            ['state', '=', 'posted'],
            ['partner_id', '=', partner_id],
            ['ref', 'ilike', ref_limpa],
            ['id', '!=', orfao_id]
        ],
        fields=['id', 'name', 'date', 'amount', 'ref', 'journal_id', 'move_id'],
        limit=10
    )

    conciliados = []

    for pag in pagamentos:
        move_id = pag.get('move_id')
        if not move_id:
            continue

        move_id_val = move_id[0] if isinstance(move_id, (list, tuple)) else move_id

        # Verificar se esta conciliado
        linhas = conn.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id_val],
                ['account_type', '=', 'asset_receivable']
            ],
            fields=['id', 'matched_debit_ids', 'reconciled', 'full_reconcile_id']
        )

        if not linhas:
            continue

        linha = linhas[0]
        matched_debit_ids = linha.get('matched_debit_ids', [])
        reconciled = linha.get('reconciled', False)
        full_reconcile_id = linha.get('full_reconcile_id')

        # Se TEM reconciliacao, e o pagamento "correto"
        if matched_debit_ids or reconciled or full_reconcile_id:
            journal = pag.get('journal_id')
            journal_name = journal[1] if isinstance(journal, (list, tuple)) else str(journal)

            conciliados.append({
                'payment_id': pag.get('id'),
                'payment_name': pag.get('name'),
                'payment_date': pag.get('date'),
                'amount': pag.get('amount'),
                'journal_name': journal_name,
                'ref': pag.get('ref'),
                'reconciled': True
            })

    return conciliados


def levantar_recebimentos_orfaos(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    journal_ids: Optional[List[int]] = None,
    usuario: Optional[str] = None,
    exportar_csv: bool = True
) -> List[Dict]:
    """
    Busca recebimentos (account.payment inbound) que estao postados
    mas nao foram reconciliados com nenhum titulo.

    Um recebimento e considerado orfao se:
    1. E do tipo inbound (recebimento)
    2. Esta postado (state = posted)
    3. A linha de credito (asset_receivable) nao tem matched_debit_ids

    Args:
        data_inicio: Data inicial (YYYY-MM-DD) - default: 2024-01-01
        data_fim: Data final (YYYY-MM-DD) - default: hoje
        journal_ids: Lista de IDs de journals para filtrar (opcional)
        usuario: Nome do usuario criador para filtrar (opcional)
        exportar_csv: Se deve exportar para CSV

    Returns:
        Lista de pagamentos orfaos
    """
    print("\n" + "=" * 80)
    print("LEVANTAMENTO DE RECEBIMENTOS ORFAOS")
    print("=" * 80)

    conn = get_odoo_connection()
    if not conn.authenticate():
        print("Erro de autenticacao")
        return []

    # Definir periodo
    if not data_inicio:
        data_inicio = '2024-01-01'
    if not data_fim:
        data_fim = date.today().strftime('%Y-%m-%d')

    print(f"\nPeriodo: {data_inicio} a {data_fim}")

    # Filtros para pagamentos
    filtros = [
        ['payment_type', '=', 'inbound'],  # Recebimentos
        ['state', '=', 'posted'],           # Postados
        ['date', '>=', data_inicio],
        ['date', '<=', data_fim],
    ]

    if journal_ids:
        filtros.append(['journal_id', 'in', journal_ids])
        print(f"Journals: {journal_ids}")

    # Filtrar por usuario criador
    if usuario:
        # Buscar ID do usuario pelo nome
        usuarios = conn.search_read(
            'res.users',
            [['name', 'ilike', usuario]],
            fields=['id', 'name'],
            limit=5
        )
        if usuarios:
            user_ids = [u['id'] for u in usuarios]
            filtros.append(['create_uid', 'in', user_ids])
            print(f"Usuario: {usuario} (IDs: {user_ids})")
            for u in usuarios:
                print(f"  - {u['name']} (ID: {u['id']})")
        else:
            print(f"AVISO: Usuario '{usuario}' nao encontrado no Odoo")
            return []

    # Buscar pagamentos
    print("\nBuscando pagamentos...")

    pagamentos = conn.search_read(
        'account.payment',
        filtros,
        fields=[
            'id', 'name', 'date', 'amount',
            'partner_id', 'journal_id', 'ref',
            'move_id', 'company_id', 'create_date'
        ],
        limit=5000  # Limite de seguranca
    )

    # Ordenar por data (decrescente)
    pagamentos.sort(key=lambda x: x.get('date', ''), reverse=True)

    print(f"Pagamentos encontrados: {len(pagamentos)}")

    if not pagamentos:
        print("Nenhum pagamento encontrado no periodo.")
        return []

    # Verificar reconciliacao de cada pagamento
    orfaos = []
    processados = 0

    print("\nVerificando reconciliacao...")

    for pag in pagamentos:
        processados += 1
        if processados % 100 == 0:
            print(f"  Processados: {processados}/{len(pagamentos)}")

        move_id = pag.get('move_id')
        if not move_id:
            continue

        move_id_val = move_id[0] if isinstance(move_id, (list, tuple)) else move_id

        # Buscar linha de credito (asset_receivable) do pagamento
        linhas = conn.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id_val],
                ['account_type', '=', 'asset_receivable']
            ],
            fields=['id', 'credit', 'matched_debit_ids', 'reconciled', 'full_reconcile_id']
        )

        if not linhas:
            continue

        linha = linhas[0]
        matched_debit_ids = linha.get('matched_debit_ids', [])
        full_reconcile_id = linha.get('full_reconcile_id')
        reconciled = linha.get('reconciled', False)

        # Se nao tem matched_debit_ids e nao esta reconciliado, e orfao
        if not matched_debit_ids and not reconciled and not full_reconcile_id:
            partner = pag.get('partner_id')
            partner_id_val = partner[0] if isinstance(partner, (list, tuple)) else partner
            partner_name = partner[1] if isinstance(partner, (list, tuple)) else str(partner)

            journal = pag.get('journal_id')
            journal_name = journal[1] if isinstance(journal, (list, tuple)) else str(journal)

            company = pag.get('company_id')
            company_name = company[1] if isinstance(company, (list, tuple)) else str(company)

            ref = pag.get('ref')

            # Buscar pagamentos CONCILIADOS da mesma NF para comparacao
            conciliados = buscar_pagamentos_conciliados_mesma_nf(
                conn, ref, partner_id_val, pag.get('id')
            )

            # Formatar info dos conciliados
            if conciliados:
                conciliado_info = '; '.join([
                    f"{c['payment_name']} ({c['journal_name']}) R${c['amount']:.2f}"
                    for c in conciliados
                ])
                conciliado_total = sum(c['amount'] for c in conciliados)
            else:
                conciliado_info = ''
                conciliado_total = 0

            orfao = {
                'payment_id': pag.get('id'),
                'payment_name': pag.get('name'),
                'payment_date': pag.get('date'),
                'amount': pag.get('amount'),
                'ref': ref,
                'partner_id': partner_id_val,
                'partner_name': partner_name,
                'journal_id': journal[0] if isinstance(journal, (list, tuple)) else journal,
                'journal_name': journal_name,
                'company_id': company[0] if isinstance(company, (list, tuple)) else company,
                'company_name': company_name,
                'move_line_id': linha.get('id'),
                'credit': linha.get('credit'),
                'create_date': pag.get('create_date'),
                # Campos de comparacao com conciliados
                'conciliado_existe': 'SIM' if conciliados else 'NAO',
                'conciliado_pagamentos': conciliado_info,
                'conciliado_total': conciliado_total,
                'conciliado_qtd': len(conciliados)
            }
            orfaos.append(orfao)

    print(f"\nTotal de orfaos encontrados: {len(orfaos)}")

    # Agrupar por journal
    por_journal = {}
    for o in orfaos:
        jname = o['journal_name']
        if jname not in por_journal:
            por_journal[jname] = {'qtd': 0, 'total': 0}
        por_journal[jname]['qtd'] += 1
        por_journal[jname]['total'] += o['amount'] or 0

    if por_journal:
        print("\n--- Resumo por Journal ---")
        for jname, dados in sorted(por_journal.items(), key=lambda x: x[1]['total'], reverse=True):
            print(f"  {jname}: {dados['qtd']} pagamentos, R$ {dados['total']:,.2f}")

    # Agrupar por partner (top 20)
    por_partner = {}
    for o in orfaos:
        pname = o['partner_name']
        if pname not in por_partner:
            por_partner[pname] = {'qtd': 0, 'total': 0}
        por_partner[pname]['qtd'] += 1
        por_partner[pname]['total'] += o['amount'] or 0

    if por_partner:
        print("\n--- Top 20 Clientes com mais orfaos ---")
        top_20 = sorted(por_partner.items(), key=lambda x: x[1]['total'], reverse=True)[:20]
        for pname, dados in top_20:
            print(f"  {pname[:50]:50} | {dados['qtd']:4} pag | R$ {dados['total']:>12,.2f}")

    # Exportar XLSX
    if exportar_csv and orfaos:
        arquivo = f"recebimentos_orfaos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        caminho = os.path.join(os.path.dirname(__file__), arquivo)

        # Criar DataFrame com colunas ordenadas
        colunas_ordenadas = [
            'payment_id', 'payment_name', 'payment_date', 'amount', 'ref',
            'journal_name', 'partner_name', 'company_name',
            'conciliado_existe', 'conciliado_pagamentos', 'conciliado_total', 'conciliado_qtd',
            'create_date', 'partner_id', 'journal_id', 'company_id', 'move_line_id', 'credit'
        ]

        df = pd.DataFrame(orfaos)
        # Reordenar colunas (apenas as que existem)
        colunas_existentes = [c for c in colunas_ordenadas if c in df.columns]
        df = df[colunas_existentes]

        # Renomear colunas para melhor legibilidade
        df = df.rename(columns={
            'payment_id': 'ID_Pagamento',
            'payment_name': 'Nome_Pagamento',
            'payment_date': 'Data',
            'amount': 'Valor_Orfao',
            'ref': 'Referencia_NF',
            'journal_name': 'Journal',
            'partner_name': 'Cliente',
            'company_name': 'Empresa',
            'conciliado_existe': 'Tem_Conciliado',
            'conciliado_pagamentos': 'Pagamentos_Conciliados',
            'conciliado_total': 'Valor_Conciliado',
            'conciliado_qtd': 'Qtd_Conciliados',
            'create_date': 'Criado_Em',
            'partner_id': 'ID_Cliente',
            'journal_id': 'ID_Journal',
            'company_id': 'ID_Empresa',
            'move_line_id': 'ID_MoveLine',
            'credit': 'Credito'
        })

        # Exportar para Excel
        with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Orfaos')

            # Ajustar largura das colunas
            worksheet = writer.sheets['Orfaos']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx) if idx < 26 else f'{chr(65 + idx // 26 - 1)}{chr(65 + idx % 26)}'].width = min(max_length, 50)

        print(f"\n*** Exportado para: {caminho}")

    return orfaos


def analisar_orfao_detalhado(payment_id: int) -> Dict:
    """
    Analisa um pagamento especifico para entender por que esta orfao.

    Args:
        payment_id: ID do account.payment

    Returns:
        Dict com analise detalhada
    """
    print(f"\n" + "=" * 80)
    print(f"ANALISE DETALHADA - Payment ID: {payment_id}")
    print("=" * 80)

    conn = get_odoo_connection()
    if not conn.authenticate():
        print("Erro de autenticacao")
        return {}

    # Buscar pagamento
    pag = conn.search_read(
        'account.payment',
        [['id', '=', payment_id]],
        fields=['id', 'name', 'date', 'amount', 'ref', 'partner_id', 'journal_id', 'move_id', 'state']
    )

    if not pag:
        print(f"Pagamento {payment_id} nao encontrado")
        return {}

    pag = pag[0]
    print(f"\n--- Dados do Pagamento ---")
    print(f"  Nome: {pag.get('name')}")
    print(f"  Data: {pag.get('date')}")
    print(f"  Valor: R$ {pag.get('amount'):,.2f}")
    print(f"  Ref: {pag.get('ref')}")
    print(f"  Partner: {pag.get('partner_id')}")
    print(f"  Journal: {pag.get('journal_id')}")
    print(f"  State: {pag.get('state')}")

    move_id = pag.get('move_id')
    if not move_id:
        print("  ERRO: Sem move_id!")
        return pag

    move_id_val = move_id[0] if isinstance(move_id, (list, tuple)) else move_id

    # Buscar linhas do move
    linhas = conn.search_read(
        'account.move.line',
        [['move_id', '=', move_id_val]],
        fields=[
            'id', 'name', 'debit', 'credit', 'account_type',
            'matched_debit_ids', 'matched_credit_ids', 'reconciled', 'full_reconcile_id'
        ]
    )

    print(f"\n--- Linhas do Move (ID={move_id_val}) ---")
    for linha_move in linhas:
        print(f"  ID={linha_move['id']:8} | {linha_move['account_type']:20} | D={linha_move['debit']:>10.2f} | C={linha_move['credit']:>10.2f}")
        print(f"            matched_debit_ids={linha_move.get('matched_debit_ids')}")
        print(f"            matched_credit_ids={linha_move.get('matched_credit_ids')}")
        print(f"            reconciled={linha_move.get('reconciled')}, full_reconcile={linha_move.get('full_reconcile_id')}")

    # Tentar identificar o titulo original pela ref
    ref = pag.get('ref', '')
    if ref:
        print(f"\n--- Buscando titulo pela ref: {ref} ---")

        # Extrair NF da ref (geralmente no formato "VND/2025/00123" ou numero direto)
        partes = ref.replace('DESCONTO - ', '').replace('ACORDO - ', '').replace('DEVOLUCAO - ', '').replace('JUROS - ', '').strip()

        # Buscar titulos com esse ref ou nome
        titulos = conn.search_read(
            'account.move.line',
            [
                ['move_id.name', 'ilike', partes],
                ['account_type', '=', 'asset_receivable']
            ],
            fields=['id', 'name', 'debit', 'amount_residual', 'reconciled', 'move_id', 'l10n_br_cobranca_parcela'],
            limit=10
        )

        if titulos:
            print(f"  Titulos encontrados para '{partes}':")
            for t in titulos:
                print(f"    ID={t['id']:8} | Saldo={t['amount_residual']:>10.2f} | Reconciled={t['reconciled']} | P{t.get('l10n_br_cobranca_parcela', 'N/A')}")
        else:
            print(f"  Nenhum titulo encontrado para '{partes}'")

    return pag


def main():
    """Menu principal"""
    import argparse

    parser = argparse.ArgumentParser(description='Levantar recebimentos orfaos no Odoo')
    parser.add_argument('--inicio', help='Data inicio (YYYY-MM-DD)', default=None)
    parser.add_argument('--fim', help='Data fim (YYYY-MM-DD)', default=None)
    parser.add_argument('--journals', help='IDs de journals separados por virgula', default=None)
    parser.add_argument('--usuario', help='Nome do usuario criador para filtrar', default=None)
    parser.add_argument('--analisar', type=int, help='ID do pagamento para analise detalhada', default=None)
    parser.add_argument('--no-csv', action='store_true', help='Nao exportar CSV')

    args = parser.parse_args()

    if args.analisar:
        analisar_orfao_detalhado(args.analisar)
    else:
        journal_ids = None
        if args.journals:
            journal_ids = [int(x.strip()) for x in args.journals.split(',')]

        levantar_recebimentos_orfaos(
            data_inicio=args.inicio,
            data_fim=args.fim,
            journal_ids=journal_ids,
            usuario=args.usuario,
            exportar_csv=not args.no_csv
        )


if __name__ == '__main__':
    main()
