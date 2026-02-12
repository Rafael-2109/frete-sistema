#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria Completa de Faturas de Compra - OTIMIZADO

Extrai todas as faturas de compra com:
- Dados da fatura (número, data, status)
- Fornecedor (nome, CNPJ)
- Títulos/parcelas (valor, vencimento, número parcela)
- Pagamentos (data, valor, estorno, devolução)
- Conciliação bancária

OTIMIZAÇÃO: Usa batch queries para evitar N+1

Autor: Sistema de Fretes
Data: 17/12/2025
"""

import sys
import os
import argparse
import json
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
from app.utils.timezone import agora_utc_naive


# ==============================================================================
# CONEXÃO ODOO
# ==============================================================================

def get_odoo_connection():
    """Obtém conexão com Odoo."""
    from app.odoo.utils.connection import get_odoo_connection as get_conn
    return get_conn()


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def extrair_id(valor):
    """Extrai ID de campo many2one."""
    if isinstance(valor, (list, tuple)) and len(valor) > 0:
        return valor[0]
    return valor


def extrair_nome(valor):
    """Extrai nome de campo many2one."""
    if isinstance(valor, (list, tuple)) and len(valor) > 1:
        return valor[1]
    return str(valor) if valor else ''


def chunked(lst: List, size: int):
    """Divide lista em chunks de tamanho especificado."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


# ==============================================================================
# EXTRAÇÃO OTIMIZADA (BATCH QUERIES)
# ==============================================================================

def extrair_auditoria(odoo, mes: int = None, ano: int = None, limit: int = 10000, todos: bool = False) -> Dict:
    """
    Extrai auditoria completa de faturas de compra - VERSÃO OTIMIZADA.

    Usa batch queries para evitar problema N+1.

    Args:
        odoo: Conexão Odoo
        mes: Mês (1-12) - opcional se todos=True
        ano: Ano - opcional se todos=True
        limit: Limite de faturas
        todos: Se True, extrai todo o período disponível
    """
    # Definir período
    if todos:
        data_inicio = None
        data_fim = None
        periodo_desc = "TODO O PERÍODO"
    else:
        data_inicio = f"{ano}-{mes:02d}-01"
        if mes == 12:
            data_fim = f"{ano}-12-31"
        else:
            data_fim = f"{ano}-{mes+1:02d}-01"
        periodo_desc = f"{data_inicio} a {data_fim}"

    print(f"\n{'='*70}")
    print(f"AUDITORIA DE FATURAS DE COMPRA - OTIMIZADO")
    print(f"Período: {periodo_desc}")
    print(f"{'='*70}")

    # =========================================================================
    # ETAPA 1: Buscar todas as faturas
    # =========================================================================
    print(f"\n[1/7] Buscando faturas de compra...")

    campos_fatura = [
        'id', 'name', 'ref', 'partner_id', 'move_type', 'state', 'payment_state',
        'date', 'invoice_date', 'invoice_date_due',
        'amount_total', 'amount_untaxed', 'amount_tax', 'amount_residual',
        'invoice_origin', 'l10n_br_chave_nf', 'l10n_br_numero_nota_fiscal', 'reversed_entry_id',
        'company_id', 'journal_id', 'currency_id'
    ]

    # Montar filtro de datas
    domain = [
        ('move_type', '=', 'in_invoice'),
        ('state', '=', 'posted'),
    ]
    if data_inicio:
        domain.append(('invoice_date', '>=', data_inicio))
    if data_fim:
        domain.append(('invoice_date', '<', data_fim))

    faturas = odoo.search_read(
        'account.move',
        domain,
        fields=campos_fatura,
        limit=limit
    )

    faturas.sort(key=lambda x: (x.get('invoice_date') or '', x.get('name') or ''))
    print(f"    Encontradas: {len(faturas)} faturas")

    if not faturas:
        return {'periodo': {'mes': mes, 'ano': ano, 'todos': todos}, 'totais': {}, 'faturas': []}

    # Criar índices
    fatura_ids = [f['id'] for f in faturas]
    faturas_por_id = {f['id']: f for f in faturas}

    # =========================================================================
    # ETAPA 2: Buscar todos os fornecedores (batch)
    # =========================================================================
    print(f"[2/7] Buscando fornecedores...")

    partner_ids = list(set(extrair_id(f.get('partner_id')) for f in faturas if f.get('partner_id')))

    fornecedores_por_id = {}
    if partner_ids:
        for chunk in chunked(partner_ids, 200):
            parceiros = odoo.search_read(
                'res.partner',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'l10n_br_cnpj', 'l10n_br_ie', 'l10n_br_municipio_id', 'state_id'],
                limit=len(chunk)
            )
            for p in parceiros:
                fornecedores_por_id[p['id']] = p

    print(f"    Carregados: {len(fornecedores_por_id)} fornecedores")

    # =========================================================================
    # ETAPA 3: Buscar todos os títulos (batch)
    # =========================================================================
    print(f"[3/7] Buscando títulos/parcelas...")

    campos_titulo = [
        'id', 'name', 'move_id', 'account_id', 'partner_id',
        'date', 'date_maturity',
        'debit', 'credit', 'balance', 'amount_residual',
        'reconciled', 'full_reconcile_id', 'matched_debit_ids', 'matched_credit_ids',
        'statement_line_id', 'payment_id'
    ]

    titulos_por_fatura = defaultdict(list)
    todos_titulos = []

    for chunk in chunked(fatura_ids, 100):
        titulos = odoo.search_read(
            'account.move.line',
            [
                ('move_id', 'in', chunk),
                ('account_id.account_type', '=', 'liability_payable'),
            ],
            fields=campos_titulo,
            limit=5000
        )
        todos_titulos.extend(titulos)
        for t in titulos:
            move_id = extrair_id(t.get('move_id'))
            titulos_por_fatura[move_id].append(t)

    # Ordenar títulos por vencimento
    for move_id in titulos_por_fatura:
        titulos_por_fatura[move_id].sort(key=lambda x: x.get('date_maturity') or '')

    print(f"    Carregados: {len(todos_titulos)} títulos")

    # =========================================================================
    # ETAPA 4: Buscar todas as conciliações parciais (batch)
    # =========================================================================
    print(f"[4/7] Buscando conciliações parciais...")

    # Coletar todos os matched_ids
    todos_matched_ids: Set[int] = set()
    for t in todos_titulos:
        todos_matched_ids.update(t.get('matched_debit_ids') or [])
        todos_matched_ids.update(t.get('matched_credit_ids') or [])

    partials_por_id = {}
    if todos_matched_ids:
        matched_list = list(todos_matched_ids)
        for chunk in chunked(matched_list, 200):
            partials = odoo.search_read(
                'account.partial.reconcile',
                [('id', 'in', chunk)],
                fields=['id', 'debit_move_id', 'credit_move_id', 'amount', 'create_date'],
                limit=len(chunk)
            )
            for p in partials:
                partials_por_id[p['id']] = p

    print(f"    Carregadas: {len(partials_por_id)} conciliações")

    # =========================================================================
    # ETAPA 5: Buscar linhas de pagamento e movimentos (batch)
    # =========================================================================
    print(f"[5/7] Buscando movimentos de pagamento...")

    # Identificar todas as linhas de pagamento (contrapartidas dos títulos)
    titulo_ids = {t['id'] for t in todos_titulos}
    pagamento_line_ids: Set[int] = set()

    for partial in partials_por_id.values():
        debit_id = extrair_id(partial.get('debit_move_id'))
        credit_id = extrair_id(partial.get('credit_move_id'))

        if debit_id and debit_id not in titulo_ids:
            pagamento_line_ids.add(debit_id)
        if credit_id and credit_id not in titulo_ids:
            pagamento_line_ids.add(credit_id)

    # Buscar linhas de pagamento
    linhas_pag_por_id = {}
    if pagamento_line_ids:
        pag_list = list(pagamento_line_ids)
        for chunk in chunked(pag_list, 200):
            linhas = odoo.search_read(
                'account.move.line',
                [('id', 'in', chunk)],
                fields=['id', 'move_id', 'date'],
                limit=len(chunk)
            )
            for linha in linhas:
                linhas_pag_por_id[linha['id']] = linha

    # Buscar movimentos de pagamento
    move_ids_pag: Set[int] = set()
    for linha in linhas_pag_por_id.values():
        move_id = extrair_id(linha.get('move_id'))
        if move_id:
            move_ids_pag.add(move_id)

    moves_pag_por_id = {}
    if move_ids_pag:
        move_list = list(move_ids_pag)
        for chunk in chunked(move_list, 200):
            moves = odoo.search_read(
                'account.move',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'ref', 'date', 'move_type'],
                limit=len(chunk)
            )
            for m in moves:
                moves_pag_por_id[m['id']] = m

    print(f"    Carregados: {len(moves_pag_por_id)} movimentos de pagamento")

    # =========================================================================
    # ETAPA 6: Buscar linhas de extrato (batch)
    # =========================================================================
    print(f"[6/7] Buscando extratos bancários...")

    statement_line_ids: Set[int] = set()
    for t in todos_titulos:
        stmt_id = extrair_id(t.get('statement_line_id'))
        if stmt_id:
            statement_line_ids.add(stmt_id)

    extratos_por_id = {}
    if statement_line_ids:
        stmt_list = list(statement_line_ids)
        for chunk in chunked(stmt_list, 200):
            stmts = odoo.search_read(
                'account.bank.statement.line',
                [('id', 'in', chunk)],
                fields=['id', 'date', 'payment_ref', 'amount'],
                limit=len(chunk)
            )
            for s in stmts:
                extratos_por_id[s['id']] = s

    print(f"    Carregados: {len(extratos_por_id)} extratos")

    # =========================================================================
    # ETAPA 7: Buscar notas de crédito/estornos (batch)
    # =========================================================================
    print(f"[7/7] Buscando notas de crédito...")

    notas_credito_por_fatura = defaultdict(list)

    for chunk in chunked(fatura_ids, 100):
        creditos = odoo.search_read(
            'account.move',
            [
                ('reversed_entry_id', 'in', chunk),
                ('move_type', '=', 'in_refund'),
            ],
            fields=['id', 'name', 'date', 'invoice_date', 'amount_total', 'state', 'reversed_entry_id'],
            limit=1000
        )
        for nc in creditos:
            fatura_orig_id = extrair_id(nc.get('reversed_entry_id'))
            notas_credito_por_fatura[fatura_orig_id].append(nc)

    total_nc = sum(len(v) for v in notas_credito_por_fatura.values())
    print(f"    Carregadas: {total_nc} notas de crédito")

    # =========================================================================
    # MONTAGEM DOS RESULTADOS
    # =========================================================================
    print(f"\nMontando resultados...")

    resultados = []

    for fatura in faturas:
        fatura_id = fatura['id']
        partner_id = extrair_id(fatura.get('partner_id'))
        fornecedor = fornecedores_por_id.get(partner_id, {})
        titulos = titulos_por_fatura.get(fatura_id, [])
        notas_credito = notas_credito_por_fatura.get(fatura_id, [])

        # Processar títulos
        titulos_processados = []
        for i, titulo in enumerate(titulos, 1):
            titulo_id = titulo['id']

            # Montar pagamentos do título
            pagamentos = []
            matched_ids = (titulo.get('matched_debit_ids') or []) + (titulo.get('matched_credit_ids') or [])

            for match_id in matched_ids:
                partial = partials_por_id.get(match_id)
                if not partial:
                    continue

                debit_id = extrair_id(partial.get('debit_move_id'))
                credit_id = extrair_id(partial.get('credit_move_id'))
                pag_line_id = credit_id if debit_id == titulo_id else debit_id

                if pag_line_id and pag_line_id != titulo_id:
                    linha_pag = linhas_pag_por_id.get(pag_line_id, {})
                    move_id = extrair_id(linha_pag.get('move_id'))
                    move_pag = moves_pag_por_id.get(move_id, {})

                    if move_pag:
                        pagamentos.append({
                            'partial_id': match_id,
                            'valor': partial.get('amount', 0),
                            'data_conciliacao': partial.get('create_date'),
                            'move_id': move_id,
                            'move_name': move_pag.get('name'),
                            'move_ref': move_pag.get('ref'),
                            'move_date': move_pag.get('date'),
                            'move_type': move_pag.get('move_type'),
                        })

            # Montar conciliação
            stmt_line_id = extrair_id(titulo.get('statement_line_id'))
            stmt = extratos_por_id.get(stmt_line_id, {})
            full_rec_id = extrair_id(titulo.get('full_reconcile_id'))

            conciliacao = {
                'conciliado': titulo.get('reconciled', False),
                'full_reconcile_id': full_rec_id,
                'full_reconcile_name': f"RECONCILE/{full_rec_id}" if full_rec_id else None,
                'statement_line_id': stmt_line_id,
                'statement_date': stmt.get('date'),
                'statement_amount': stmt.get('amount'),
                'statement_ref': stmt.get('payment_ref'),
            }

            titulos_processados.append({
                'parcela': i,
                'titulo_id': titulo_id,
                'name': titulo.get('name'),
                'vencimento': titulo.get('date_maturity'),
                'valor': abs(titulo.get('credit') or titulo.get('debit') or 0),
                'saldo_aberto': abs(titulo.get('amount_residual', 0)),
                'reconciliado': titulo.get('reconciled', False),
                'pagamentos': pagamentos,
                'conciliacao': conciliacao,
            })

        # Montar resultado da fatura
        resultados.append({
            'fatura': {
                'id': fatura_id,
                'numero': fatura.get('name'),
                'ref': fatura.get('ref'),
                'data_fatura': fatura.get('invoice_date'),
                'data_lancamento': fatura.get('date'),
                'vencimento': fatura.get('invoice_date_due'),
                'valor_total': fatura.get('amount_total'),
                'valor_liquido': fatura.get('amount_untaxed'),
                'valor_impostos': fatura.get('amount_tax'),
                'saldo_aberto': fatura.get('amount_residual'),
                'status': fatura.get('state'),
                'status_pagamento': fatura.get('payment_state'),
                'origem': fatura.get('invoice_origin'),
                'numero_nota_fiscal': fatura.get('l10n_br_numero_nota_fiscal'),
                'chave_nf': fatura.get('l10n_br_chave_nf'),
            },
            'fornecedor': {
                'id': fornecedor.get('id'),
                'nome': fornecedor.get('name') or extrair_nome(fatura.get('partner_id')),
                'cnpj': fornecedor.get('l10n_br_cnpj'),
                'ie': fornecedor.get('l10n_br_ie'),
                'cidade': extrair_nome(fornecedor.get('l10n_br_municipio_id')).split('(')[0].strip() if fornecedor.get('l10n_br_municipio_id') else None,
                'estado': extrair_nome(fornecedor.get('state_id')),
            },
            'titulos': titulos_processados,
            'notas_credito': [{
                'id': nc['id'],
                'numero': nc['name'],
                'data': nc.get('invoice_date'),
                'valor': nc.get('amount_total'),
                'status': nc.get('state'),
            } for nc in notas_credito],
            'resumo': {
                'qtd_parcelas': len(titulos_processados),
                'valor_total': fatura.get('amount_total'),
                'total_pago': sum(sum(p.get('valor', 0) for p in t.get('pagamentos', [])) for t in titulos_processados),
                'saldo_aberto': fatura.get('amount_residual'),
                'totalmente_conciliado': all(t.get('conciliacao', {}).get('conciliado', False) for t in titulos_processados) if titulos_processados else False,
                'tem_estorno': len(notas_credito) > 0,
            }
        })

    # Calcular totais
    total_faturas = len(resultados)
    total_valor = sum(r['fatura'].get('valor_total', 0) or 0 for r in resultados)
    total_aberto = sum(r['fatura'].get('saldo_aberto', 0) or 0 for r in resultados)
    total_parcelas = sum(r['resumo'].get('qtd_parcelas', 0) for r in resultados)
    total_conciliados = sum(1 for r in resultados if r['resumo'].get('totalmente_conciliado', False))
    total_com_estorno = sum(1 for r in resultados if r['resumo'].get('tem_estorno', False))

    print(f"Processamento concluído!")

    return {
        'periodo': {
            'mes': mes,
            'ano': ano,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'todos': todos,
        },
        'totais': {
            'qtd_faturas': total_faturas,
            'valor_total': total_valor,
            'saldo_aberto': total_aberto,
            'total_parcelas': total_parcelas,
            'faturas_conciliadas': total_conciliados,
            'faturas_com_estorno': total_com_estorno,
        },
        'faturas': resultados,
        'timestamp': agora_utc_naive().isoformat(),
    }




# ==============================================================================
# FORMATAÇÃO DE SAÍDA
# ==============================================================================

def formatar_valor(valor):
    """Formata valor monetário."""
    if valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def imprimir_resumo(auditoria: Dict):
    """Imprime resumo da auditoria."""
    periodo = auditoria['periodo']
    totais = auditoria['totais']

    print(f"\n{'='*70}")
    if periodo.get('todos'):
        print(f"RESUMO DA AUDITORIA - TODO O PERÍODO")
    else:
        print(f"RESUMO DA AUDITORIA - {periodo['mes']:02d}/{periodo['ano']}")
    print(f"{'='*70}")
    print(f"\nQuantidade de faturas: {totais['qtd_faturas']}")
    print(f"Total de parcelas: {totais['total_parcelas']}")
    print(f"Valor total: {formatar_valor(totais['valor_total'])}")
    print(f"Saldo em aberto: {formatar_valor(totais['saldo_aberto'])}")
    print(f"Faturas totalmente conciliadas: {totais['faturas_conciliadas']}")
    print(f"Faturas com estorno/devolução: {totais['faturas_com_estorno']}")

    # Amostra das primeiras faturas
    print(f"\n{'='*70}")
    print(f"AMOSTRA - PRIMEIRAS 5 FATURAS")
    print(f"{'='*70}")

    for fatura_data in auditoria['faturas'][:5]:
        f = fatura_data['fatura']
        fornecedor = fatura_data['fornecedor']

        print(f"\n📄 {f.get('numero')} | {f.get('data_fatura')} | {f.get('status_pagamento')}")
        print(f"   Fornecedor: {fornecedor.get('nome')} | CNPJ: {fornecedor.get('cnpj')}")
        print(f"   Valor: {formatar_valor(f.get('valor_total'))} | Aberto: {formatar_valor(f.get('saldo_aberto'))}")

        for titulo in fatura_data['titulos']:
            status = "✓" if titulo.get('reconciliado') else "○"
            conc_ext = "📊" if titulo.get('conciliacao', {}).get('statement_line_id') else ""
            print(f"   {status} Parc {titulo['parcela']}: {formatar_valor(titulo['valor'])} venc:{titulo['vencimento']} {conc_ext}")

            for pag in titulo.get('pagamentos', []):
                print(f"      💰 Pago: {formatar_valor(pag['valor'])} em {pag.get('move_date')} ({pag.get('move_name')})")

        if fatura_data['notas_credito']:
            for nc in fatura_data['notas_credito']:
                print(f"   🔄 Estorno: {nc['numero']} - {formatar_valor(nc['valor'])} em {nc['data']}")


# ==============================================================================
# EXPORTAÇÃO PARA EXCEL
# ==============================================================================

def exportar_para_json_tabular(auditoria: Dict) -> Dict:
    """
    Converte auditoria para formato tabular (uma linha por título).
    Pronto para exportar via skill exportando-arquivos.
    """
    linhas = []

    for fatura_data in auditoria['faturas']:
        f = fatura_data['fatura']
        fornecedor = fatura_data['fornecedor']
        titulos = fatura_data['titulos']
        notas_credito = fatura_data.get('notas_credito', [])

        # Calcular totais de estorno
        valor_estorno_total = sum(nc.get('valor', 0) or 0 for nc in notas_credito)
        numeros_nc = ', '.join(nc.get('numero', '') for nc in notas_credito if nc.get('numero'))
        datas_nc = ', '.join(nc.get('data', '') for nc in notas_credito if nc.get('data'))

        if not titulos:
            # Fatura sem títulos (raro)
            linhas.append({
                'Fatura': f.get('numero'),
                'Numero NF': f.get('numero_nota_fiscal'),
                'Ref': f.get('ref'),
                'Data Fatura': f.get('data_fatura'),
                'Data Lancamento': f.get('data_lancamento'),
                'Fornecedor': fornecedor.get('nome'),
                'CNPJ': fornecedor.get('cnpj'),
                'Valor Total': f.get('valor_total'),
                'Saldo Aberto': f.get('saldo_aberto'),
                'Status Pagamento': f.get('status_pagamento'),
                'Parcela': '-',
                'Vencimento': f.get('vencimento'),
                'Valor Parcela': f.get('valor_total'),
                'Saldo Parcela': f.get('saldo_aberto'),
                'Conciliado': 'Não',
                'Data Pagamento': None,
                'Valor Pago': None,
                'Documento Pagamento': None,
                'Conciliado Extrato': 'Não',
                'Estorno': 'Sim' if notas_credito else 'Não',
                'Valor Estorno': valor_estorno_total if notas_credito else None,
                'Numero NC': numeros_nc if notas_credito else None,
                'Data Estorno': datas_nc if notas_credito else None,
                'Chave NF': f.get('chave_nf'),
                'Origem': f.get('origem'),
            })
        else:
            for titulo in titulos:
                pagamentos = titulo.get('pagamentos', [])
                pag = pagamentos[0] if pagamentos else {}
                conc = titulo.get('conciliacao', {})

                linhas.append({
                    'Fatura': f.get('numero'),
                    'Numero NF': f.get('numero_nota_fiscal'),
                    'Ref': f.get('ref'),
                    'Data Fatura': f.get('data_fatura'),
                    'Data Lancamento': f.get('data_lancamento'),
                    'Fornecedor': fornecedor.get('nome'),
                    'CNPJ': fornecedor.get('cnpj'),
                    'Valor Total': f.get('valor_total'),
                    'Saldo Aberto': f.get('saldo_aberto'),
                    'Status Pagamento': f.get('status_pagamento'),
                    'Parcela': titulo.get('parcela'),
                    'Vencimento': titulo.get('vencimento'),
                    'Valor Parcela': titulo.get('valor'),
                    'Saldo Parcela': titulo.get('saldo_aberto'),
                    'Conciliado': 'Sim' if titulo.get('reconciliado') else 'Não',
                    'Data Pagamento': pag.get('move_date'),
                    'Valor Pago': pag.get('valor'),
                    'Documento Pagamento': pag.get('move_name'),
                    'Conciliado Extrato': 'Sim' if conc.get('statement_line_id') else 'Não',
                    'Estorno': 'Sim' if notas_credito else 'Não',
                    'Valor Estorno': valor_estorno_total if notas_credito else None,
                    'Numero NC': numeros_nc if notas_credito else None,
                    'Data Estorno': datas_nc if notas_credito else None,
                    'Chave NF': f.get('chave_nf'),
                    'Origem': f.get('origem'),
                })

    return {'dados': linhas}


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Auditoria completa de faturas de compra do Odoo (OTIMIZADO)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Auditoria de novembro/2025
  python auditoria_faturas_compra.py --mes 11 --ano 2025

  # TODO O PERÍODO (todas as faturas)
  python auditoria_faturas_compra.py --all

  # Exportar para JSON
  python auditoria_faturas_compra.py --mes 11 --ano 2025 --json

  # Exportar para formato tabular (para Excel)
  python auditoria_faturas_compra.py --mes 11 --ano 2025 --excel

  # Limitar quantidade
  python auditoria_faturas_compra.py --mes 11 --ano 2025 --limit 50

  # Todo o período com limite maior
  python auditoria_faturas_compra.py --all --limit 20000 --excel
        """
    )

    parser.add_argument('--mes', type=int, help='Mês (1-12) - obrigatório se não usar --all')
    parser.add_argument('--ano', type=int, help='Ano (ex: 2025) - obrigatório se não usar --all')
    parser.add_argument('--all', action='store_true', dest='todos', help='Extrair TODO o período disponível')
    parser.add_argument('--limit', type=int, default=10000, help='Limite de faturas (default: 10000)')
    parser.add_argument('--json', action='store_true', help='Saída em JSON completo')
    parser.add_argument('--excel', action='store_true', help='Saída em JSON tabular (para Excel)')

    args = parser.parse_args()

    # Validar argumentos
    if not args.todos:
        if not args.mes or not args.ano:
            print("ERRO: --mes e --ano são obrigatórios (ou use --all para todo período)", file=sys.stderr)
            sys.exit(1)
        if args.mes < 1 or args.mes > 12:
            print("ERRO: Mês deve estar entre 1 e 12", file=sys.stderr)
            sys.exit(1)

    odoo = get_odoo_connection()
    if not odoo.authenticate():
        print("ERRO: Falha na autenticação com Odoo", file=sys.stderr)
        sys.exit(1)

    auditoria = extrair_auditoria(odoo, args.mes, args.ano, args.limit, args.todos)

    if args.json:
        print(json.dumps(auditoria, indent=2, ensure_ascii=False, default=str))
    elif args.excel:
        tabular = exportar_para_json_tabular(auditoria)
        print(json.dumps(tabular, ensure_ascii=False, default=str))
    else:
        imprimir_resumo(auditoria)


if __name__ == '__main__':
    main()
