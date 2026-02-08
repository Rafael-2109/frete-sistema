#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria de Extrato Bancário - COMPLETO

Extrai todas as linhas de extrato bancário com:
- Data, valor, referência
- Status de conciliação (conciliado vs livre)
- Parceiro associado
- Conta bancária (diário)
- CONCILIAÇÃO (full_reconcile_id)
- PAGAMENTO vinculado (account.payment)
- TÍTULO/FATURA vinculado (account.move) - via segunda conciliação

FLUXO DE CONCILIAÇÃO:
  Extrato ←→ Pagamento (conciliação A, conta PENDENTES)
  Pagamento ←→ Título (conciliação B, conta FORNECEDORES)

OTIMIZAÇÃO: Usa batch queries para evitar N+1

Autor: Sistema de Fretes
Data: 19/12/2025
"""

import sys
import os
import argparse
import json
from typing import Dict, List, Set
from collections import defaultdict
from datetime import datetime
from app.utils.timezone import agora_utc_naive
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


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
# EXTRAÇÃO COMPLETA (BATCH QUERIES)
# ==============================================================================

def extrair_extrato_completo(odoo, data_inicio: str, data_fim: str, limit: int = 50000) -> Dict:
    """
    Extrai extrato bancário COMPLETO - com conciliação, pagamento e título.

    Usa batch queries para evitar problema N+1.

    Args:
        odoo: Conexão Odoo
        data_inicio: Data início (YYYY-MM-DD)
        data_fim: Data fim (YYYY-MM-DD)
        limit: Limite de linhas
    """
    print(f"\n{'='*70}", file=sys.stderr)
    print(f"AUDITORIA DE EXTRATO BANCÁRIO - COMPLETO", file=sys.stderr)
    print(f"Período: {data_inicio} a {data_fim}", file=sys.stderr)
    print(f"{'='*70}", file=sys.stderr)

    # =========================================================================
    # ETAPA 1: Buscar todas as linhas de extrato
    # =========================================================================
    print(f"\n[1/10] Buscando linhas de extrato...", file=sys.stderr)

    campos_linha = [
        'id', 'date', 'payment_ref', 'amount', 'partner_id',
        'statement_id', 'journal_id', 'move_id',
        'is_reconciled', 'amount_residual', 'company_id',
        'transaction_type', 'account_number', 'partner_name'
    ]

    domain = [
        ('date', '>=', data_inicio),
        ('date', '<=', data_fim),
    ]

    linhas = odoo.search_read(
        'account.bank.statement.line',
        domain,
        fields=campos_linha,
        limit=limit
    )

    linhas.sort(key=lambda x: (x.get('date') or '', x.get('id') or 0))
    print(f"    Encontradas: {len(linhas)} linhas de extrato", file=sys.stderr)

    if not linhas:
        return {
            'periodo': {'data_inicio': data_inicio, 'data_fim': data_fim},
            'totais': {},
            'linhas': []
        }

    # Criar índices
    linha_ids = [ln['id'] for ln in linhas]
    move_ids_extrato = list(set(extrair_id(ln.get('move_id')) for ln in linhas if ln.get('move_id')))

    # =========================================================================
    # ETAPA 2: Buscar todos os parceiros (batch)
    # =========================================================================
    print(f"[2/10] Buscando parceiros...", file=sys.stderr)

    partner_ids = list(set(extrair_id(ln.get('partner_id')) for ln in linhas if ln.get('partner_id')))

    parceiros_por_id = {}
    if partner_ids:
        for chunk in chunked(partner_ids, 200):
            parceiros = odoo.search_read(
                'res.partner',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'l10n_br_cnpj', 'l10n_br_cpf'],
                limit=len(chunk)
            )
            for p in parceiros:
                parceiros_por_id[p['id']] = p

    print(f"    Carregados: {len(parceiros_por_id)} parceiros", file=sys.stderr)

    # =========================================================================
    # ETAPA 3: Buscar todos os diários/contas bancárias (batch)
    # =========================================================================
    print(f"[3/10] Buscando contas bancárias...", file=sys.stderr)

    journal_ids = list(set(extrair_id(ln.get('journal_id')) for ln in linhas if ln.get('journal_id')))

    diarios_por_id = {}
    if journal_ids:
        for chunk in chunked(journal_ids, 200):
            diarios = odoo.search_read(
                'account.journal',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'code', 'bank_account_id', 'type'],
                limit=len(chunk)
            )
            for d in diarios:
                diarios_por_id[d['id']] = d

    print(f"    Carregados: {len(diarios_por_id)} diários/contas", file=sys.stderr)

    # =========================================================================
    # ETAPA 4: Buscar movimentos do extrato (batch)
    # =========================================================================
    print(f"[4/10] Buscando movimentos do extrato...", file=sys.stderr)

    moves_por_id = {}
    if move_ids_extrato:
        for chunk in chunked(move_ids_extrato, 200):
            moves = odoo.search_read(
                'account.move',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'ref', 'date', 'state'],
                limit=len(chunk)
            )
            for m in moves:
                moves_por_id[m['id']] = m

    print(f"    Carregados: {len(moves_por_id)} movimentos", file=sys.stderr)

    # =========================================================================
    # ETAPA 5: Buscar linhas de DÉBITO dos moves do extrato (full_reconcile_id)
    # =========================================================================
    print(f"[5/10] Buscando linhas de débito do extrato (conciliação A)...", file=sys.stderr)

    move_lines_por_move = defaultdict(list)
    reconcile_ids_extrato = set()

    if move_ids_extrato:
        for chunk in chunked(move_ids_extrato, 100):
            move_lines = odoo.search_read(
                'account.move.line',
                [
                    ('move_id', 'in', chunk),
                    ('debit', '>', 0)
                ],
                fields=['id', 'move_id', 'name', 'account_id', 'debit', 'credit',
                        'full_reconcile_id', 'reconciled', 'partner_id'],
                limit=len(chunk) * 5
            )
            for ml in move_lines:
                move_id = extrair_id(ml.get('move_id'))
                move_lines_por_move[move_id].append(ml)
                if ml.get('full_reconcile_id'):
                    reconcile_ids_extrato.add(extrair_id(ml['full_reconcile_id']))

    print(f"    Carregadas: {sum(len(v) for v in move_lines_por_move.values())} linhas", file=sys.stderr)
    print(f"    Conciliações A (extrato↔pagamento): {len(reconcile_ids_extrato)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 6: Buscar todas as linhas da conciliação A (extrato↔pagamento)
    # =========================================================================
    print(f"[6/10] Buscando linhas da conciliação A...", file=sys.stderr)

    linhas_por_reconcile_a = defaultdict(list)

    if reconcile_ids_extrato:
        for chunk in chunked(list(reconcile_ids_extrato), 100):
            reconciled_lines = odoo.search_read(
                'account.move.line',
                [('full_reconcile_id', 'in', chunk)],
                fields=['id', 'move_id', 'full_reconcile_id', 'debit', 'credit', 'name'],
                limit=len(chunk) * 10
            )
            for rl in reconciled_lines:
                rec_id = extrair_id(rl.get('full_reconcile_id'))
                linhas_por_reconcile_a[rec_id].append(rl)

    print(f"    Carregadas: {sum(len(v) for v in linhas_por_reconcile_a.values())} linhas", file=sys.stderr)

    # =========================================================================
    # ETAPA 7: Identificar moves de pagamento e buscar account.payment
    # =========================================================================
    print(f"[7/10] Buscando pagamentos (account.payment)...", file=sys.stderr)

    payment_move_ids = set()
    for rec_id, lines in linhas_por_reconcile_a.items():
        for ln in lines:
            m_id = extrair_id(ln.get('move_id'))
            if m_id not in move_ids_extrato:
                payment_move_ids.add(m_id)

    payments_por_move = {}
    if payment_move_ids:
        for chunk in chunked(list(payment_move_ids), 100):
            payments = odoo.search_read(
                'account.payment',
                [('move_id', 'in', chunk)],
                fields=['id', 'name', 'move_id', 'amount', 'payment_type', 'partner_type',
                        'partner_id', 'date', 'ref', 'state', 'journal_id'],
                limit=len(chunk)
            )
            for p in payments:
                m_id = extrair_id(p.get('move_id'))
                payments_por_move[m_id] = p

    print(f"    Carregados: {len(payments_por_move)} pagamentos", file=sys.stderr)

    # Buscar detalhes dos moves de pagamento
    payment_moves_por_id = {}
    if payment_move_ids:
        for chunk in chunked(list(payment_move_ids), 200):
            moves = odoo.search_read(
                'account.move',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'ref', 'date', 'state', 'move_type', 'partner_id'],
                limit=len(chunk)
            )
            for m in moves:
                payment_moves_por_id[m['id']] = m

    # =========================================================================
    # ETAPA 8: Buscar TODAS as linhas dos pagamentos para encontrar conciliação B
    # =========================================================================
    print(f"[8/10] Buscando linhas dos pagamentos (conciliação B)...", file=sys.stderr)

    # O pagamento tem 2 linhas:
    # - Crédito PENDENTES: reconcilia com extrato (conciliação A) - JÁ TEMOS
    # - Débito FORNECEDORES: reconcilia com título (conciliação B) - QUEREMOS
    # Precisamos buscar a linha de DÉBITO do pagamento (conta FORNECEDORES)
    payment_debit_lines = defaultdict(list)
    reconcile_ids_titulo = set()

    if payment_move_ids:
        for chunk in chunked(list(payment_move_ids), 100):
            # Buscar linhas de DÉBITO (conta liability_payable = FORNECEDORES)
            debit_lines = odoo.search_read(
                'account.move.line',
                [
                    ('move_id', 'in', chunk),
                    ('debit', '>', 0),
                    ('full_reconcile_id', '!=', False)
                ],
                fields=['id', 'move_id', 'name', 'account_id', 'debit',
                        'full_reconcile_id', 'partner_id'],
                limit=len(chunk) * 5
            )
            for dl in debit_lines:
                move_id = extrair_id(dl.get('move_id'))
                rec_id = extrair_id(dl.get('full_reconcile_id'))
                # Apenas conciliações que NÃO são da conciliação A (extrato↔pagamento)
                if rec_id and rec_id not in reconcile_ids_extrato:
                    payment_debit_lines[move_id].append(dl)
                    reconcile_ids_titulo.add(rec_id)

    print(f"    Carregadas: {sum(len(v) for v in payment_debit_lines.values())} linhas de débito", file=sys.stderr)
    print(f"    Conciliações B (pagamento↔título): {len(reconcile_ids_titulo)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 9: Buscar todas as linhas da conciliação B (pagamento↔título)
    # =========================================================================
    print(f"[9/10] Buscando linhas da conciliação B...", file=sys.stderr)

    linhas_por_reconcile_b = defaultdict(list)

    if reconcile_ids_titulo:
        for chunk in chunked(list(reconcile_ids_titulo), 100):
            reconciled_lines = odoo.search_read(
                'account.move.line',
                [('full_reconcile_id', 'in', chunk)],
                fields=['id', 'move_id', 'full_reconcile_id', 'debit', 'credit', 'name'],
                limit=len(chunk) * 10
            )
            for rl in reconciled_lines:
                rec_id = extrair_id(rl.get('full_reconcile_id'))
                linhas_por_reconcile_b[rec_id].append(rl)

    print(f"    Carregadas: {sum(len(v) for v in linhas_por_reconcile_b.values())} linhas", file=sys.stderr)

    # Identificar move_ids dos títulos (diferentes dos pagamentos)
    titulo_move_ids = set()
    for rec_id, lines in linhas_por_reconcile_b.items():
        for ln in lines:
            m_id = extrair_id(ln.get('move_id'))
            if m_id not in payment_move_ids:
                titulo_move_ids.add(m_id)

    # =========================================================================
    # ETAPA 10: Buscar títulos/faturas (account.move)
    # =========================================================================
    print(f"[10/10] Buscando títulos/faturas...", file=sys.stderr)

    titulos_por_id = {}
    if titulo_move_ids:
        for chunk in chunked(list(titulo_move_ids), 200):
            titulos = odoo.search_read(
                'account.move',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'ref', 'date', 'state', 'move_type', 'partner_id',
                        'amount_total', 'amount_residual', 'payment_state', 'invoice_origin'],
                limit=len(chunk)
            )
            for t in titulos:
                titulos_por_id[t['id']] = t

    print(f"    Carregados: {len(titulos_por_id)} títulos/faturas", file=sys.stderr)

    # Criar mapeamento payment_move_id -> titulo
    # Para cada pagamento, qual título está vinculado via conciliação B
    titulo_por_payment_move = {}
    for payment_move_id, debit_lines in payment_debit_lines.items():
        for dl in debit_lines:
            rec_id = extrair_id(dl.get('full_reconcile_id'))
            if rec_id:
                linhas_b = linhas_por_reconcile_b.get(rec_id, [])
                for lb in linhas_b:
                    titulo_move_id = extrair_id(lb.get('move_id'))
                    if titulo_move_id != payment_move_id and titulo_move_id in titulos_por_id:
                        titulo_por_payment_move[payment_move_id] = {
                            'titulo': titulos_por_id[titulo_move_id],
                            'reconcile_id': rec_id,
                        }
                        break
                if payment_move_id in titulo_por_payment_move:
                    break

    # =========================================================================
    # MONTAGEM DOS RESULTADOS COMPLETOS
    # =========================================================================
    print(f"\nMontando resultados completos...", file=sys.stderr)

    resultados = []

    for linha in linhas:
        linha_id = linha['id']
        partner_id = extrair_id(linha.get('partner_id'))
        journal_id = extrair_id(linha.get('journal_id'))
        move_id = extrair_id(linha.get('move_id'))

        parceiro = parceiros_por_id.get(partner_id, {})
        diario = diarios_por_id.get(journal_id, {})
        move = moves_por_id.get(move_id, {})

        cnpj_cpf = parceiro.get('l10n_br_cnpj') or parceiro.get('l10n_br_cpf') or ''
        is_reconciled = linha.get('is_reconciled', False)
        amount = linha.get('amount', 0) or 0

        # Informações de conciliação
        conciliacao_info = None
        pagamento_info = None
        titulo_info = None

        # Buscar linha de débito do extrato com full_reconcile_id
        move_lines = move_lines_por_move.get(move_id, [])
        for ml in move_lines:
            if ml.get('full_reconcile_id'):
                rec_id_a = extrair_id(ml['full_reconcile_id'])
                rec_name_a = extrair_nome(ml['full_reconcile_id'])

                conciliacao_info = {
                    'id': rec_id_a,
                    'nome': rec_name_a,
                    'linha_extrato_id': ml['id'],
                    'conta': extrair_nome(ml.get('account_id')),
                }

                # Buscar pagamento na conciliação A
                linhas_rec_a = linhas_por_reconcile_a.get(rec_id_a, [])
                for lr in linhas_rec_a:
                    lr_move_id = extrair_id(lr.get('move_id'))

                    if lr_move_id != move_id and lr_move_id in payments_por_move:
                        pay = payments_por_move[lr_move_id]
                        pay_move = payment_moves_por_id.get(lr_move_id, {})

                        pagamento_info = {
                            'id': pay['id'],
                            'nome': pay.get('name'),
                            'move_id': lr_move_id,
                            'move_nome': pay_move.get('name'),
                            'valor': pay.get('amount'),
                            'tipo': pay.get('payment_type'),
                            'partner_type': pay.get('partner_type'),
                            'data': pay.get('date'),
                            'ref': pay.get('ref'),
                            'state': pay.get('state'),
                        }

                        # Buscar título via conciliação B
                        titulo_data = titulo_por_payment_move.get(lr_move_id)
                        if titulo_data:
                            tit = titulo_data['titulo']
                            titulo_info = {
                                'id': tit['id'],
                                'nome': tit.get('name'),
                                'tipo': tit.get('move_type'),
                                'data': tit.get('date'),
                                'valor_total': tit.get('amount_total'),
                                'valor_residual': tit.get('amount_residual'),
                                'payment_state': tit.get('payment_state'),
                                'origem': tit.get('invoice_origin'),
                                'conciliacao_id': titulo_data['reconcile_id'],
                            }
                        break

                break

        resultado = {
            'linha_id': linha_id,
            'data': linha.get('date'),
            'referencia': linha.get('payment_ref'),
            'valor': amount,
            'conciliado': is_reconciled,
            'status': 'Conciliado' if is_reconciled else 'Não Conciliado',
            'parceiro': {
                'id': partner_id,
                'nome': parceiro.get('name') or linha.get('partner_name') or extrair_nome(linha.get('partner_id')),
                'cnpj_cpf': cnpj_cpf,
            },
            'conta_bancaria': {
                'id': journal_id,
                'nome': diario.get('name') or extrair_nome(linha.get('journal_id')),
                'codigo': diario.get('code'),
                'tipo': diario.get('type'),
            },
            'movimento': {
                'id': move_id,
                'numero': move.get('name'),
                'ref': move.get('ref'),
                'state': move.get('state'),
            },
            'conciliacao': conciliacao_info,
            'pagamento': pagamento_info,
            'titulo': titulo_info,
            'tipo_transacao': linha.get('transaction_type'),
            'numero_conta': linha.get('account_number'),
        }

        resultados.append(resultado)

    # Calcular totais
    total_linhas = len(resultados)
    total_entradas = sum(r['valor'] for r in resultados if r['valor'] > 0)
    total_saidas = sum(r['valor'] for r in resultados if r['valor'] < 0)
    qtd_conciliados = sum(1 for r in resultados if r['conciliado'])
    qtd_nao_conciliados = sum(1 for r in resultados if not r['conciliado'])
    valor_conciliado = sum(r['valor'] for r in resultados if r['conciliado'])
    valor_nao_conciliado = sum(r['valor'] for r in resultados if not r['conciliado'])
    qtd_com_pagamento = sum(1 for r in resultados if r.get('pagamento'))
    qtd_com_titulo = sum(1 for r in resultados if r.get('titulo'))

    # Agrupar por conta bancária
    por_conta = defaultdict(lambda: {'entradas': 0, 'saidas': 0, 'qtd_conciliado': 0, 'qtd_nao_conciliado': 0, 'qtd': 0})
    for r in resultados:
        conta = r['conta_bancaria']['nome'] or 'Sem conta'
        por_conta[conta]['qtd'] += 1
        if r['valor'] > 0:
            por_conta[conta]['entradas'] += r['valor']
        else:
            por_conta[conta]['saidas'] += r['valor']
        if r['conciliado']:
            por_conta[conta]['qtd_conciliado'] += 1
        else:
            por_conta[conta]['qtd_nao_conciliado'] += 1

    print(f"Processamento concluído!", file=sys.stderr)

    return {
        'periodo': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        },
        'totais': {
            'qtd_linhas': total_linhas,
            'total_entradas': total_entradas,
            'total_saidas': total_saidas,
            'saldo': total_entradas + total_saidas,
            'qtd_conciliados': qtd_conciliados,
            'qtd_nao_conciliados': qtd_nao_conciliados,
            'valor_conciliado': valor_conciliado,
            'valor_nao_conciliado': valor_nao_conciliado,
            'qtd_com_pagamento': qtd_com_pagamento,
            'qtd_com_titulo': qtd_com_titulo,
        },
        'por_conta': dict(por_conta),
        'linhas': resultados,
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


def imprimir_resumo(extrato: Dict):
    """Imprime resumo do extrato."""
    periodo = extrato['periodo']
    totais = extrato['totais']
    por_conta = extrato.get('por_conta', {})

    print(f"\n{'='*70}")
    print(f"RESUMO DO EXTRATO BANCÁRIO")
    print(f"Período: {periodo['data_inicio']} a {periodo['data_fim']}")
    print(f"{'='*70}")

    print(f"\n--- TOTAIS GERAIS ---")
    print(f"Quantidade de linhas: {totais['qtd_linhas']}")
    print(f"Total entradas: {formatar_valor(totais['total_entradas'])}")
    print(f"Total saídas: {formatar_valor(totais['total_saidas'])}")
    print(f"Saldo: {formatar_valor(totais['saldo'])}")

    print(f"\n--- CONCILIAÇÃO ---")
    print(f"Linhas conciliadas: {totais['qtd_conciliados']}")
    print(f"Linhas não conciliadas: {totais['qtd_nao_conciliados']}")
    print(f"Valor conciliado: {formatar_valor(totais['valor_conciliado'])}")
    print(f"Valor não conciliado: {formatar_valor(totais['valor_nao_conciliado'])}")

    print(f"\n--- VÍNCULOS ---")
    print(f"Com pagamento vinculado: {totais.get('qtd_com_pagamento', 0)}")
    print(f"Com título vinculado: {totais.get('qtd_com_titulo', 0)}")

    print(f"\n--- POR CONTA BANCÁRIA ---")
    for conta, dados in sorted(por_conta.items()):
        print(f"\n{conta}:")
        print(f"  Linhas: {dados['qtd']} (Conciliadas: {dados['qtd_conciliado']} | Não: {dados['qtd_nao_conciliado']})")
        print(f"  Entradas: {formatar_valor(dados['entradas'])}")
        print(f"  Saídas: {formatar_valor(dados['saidas'])}")


# ==============================================================================
# EXPORTAÇÃO PARA EXCEL
# ==============================================================================

def exportar_para_json_tabular(extrato: Dict) -> Dict:
    """
    Converte extrato para formato tabular (uma linha por transação).
    Pronto para exportar via skill exportando-arquivos.
    """
    linhas_excel = []

    for ln in extrato['linhas']:
        valor = ln['valor']
        tipo = 'Recebimento' if valor > 0 else 'Pagamento'

        conc = ln.get('conciliacao') or {}
        pag = ln.get('pagamento') or {}
        tit = ln.get('titulo') or {}

        linhas_excel.append({
            'ID': ln['linha_id'],
            'Data': ln['data'],
            'Conta Bancaria': ln['conta_bancaria']['nome'],
            'Codigo Conta': ln['conta_bancaria']['codigo'],
            'Tipo': tipo,
            'Referencia': ln['referencia'],
            'Parceiro': ln['parceiro']['nome'],
            'CNPJ/CPF': ln['parceiro']['cnpj_cpf'],
            'Valor': valor,
            'Conciliado': 'Sim' if ln['conciliado'] else 'Não',
            'Movimento': ln['movimento']['numero'],
            'Movimento Ref': ln['movimento']['ref'],
            # Conciliação A (extrato↔pagamento)
            'Conciliacao A ID': conc.get('id'),
            'Conciliacao A Nome': conc.get('nome'),
            # Pagamento
            'Pagamento ID': pag.get('id'),
            'Pagamento Nome': pag.get('nome'),
            'Pagamento Valor': pag.get('valor'),
            'Pagamento Data': pag.get('data'),
            'Pagamento Ref': pag.get('ref'),
            'Pagamento State': pag.get('state'),
            # Título (via conciliação B)
            'Titulo ID': tit.get('id'),
            'Titulo Nome': tit.get('nome'),
            'Titulo Tipo': tit.get('tipo'),
            'Titulo Valor': tit.get('valor_total'),
            'Titulo Residual': tit.get('valor_residual'),
            'Titulo Payment State': tit.get('payment_state'),
            'Titulo Origem': tit.get('origem'),
            'Conciliacao B ID': tit.get('conciliacao_id'),
        })

    return {'dados': linhas_excel}


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Auditoria de extrato bancário do Odoo (COMPLETO)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Extrato de julho/2024 até hoje
  python auditoria_extrato_bancario.py --inicio 2024-07-01 --fim 2025-12-31

  # Exportar para JSON
  python auditoria_extrato_bancario.py --inicio 2024-07-01 --fim 2025-12-31 --json

  # Exportar para formato tabular (para Excel)
  python auditoria_extrato_bancario.py --inicio 2024-07-01 --fim 2025-12-31 --excel

  # Limitar quantidade
  python auditoria_extrato_bancario.py --inicio 2024-07-01 --fim 2025-12-31 --limit 1000
        """
    )

    parser.add_argument('--inicio', type=str, required=True, help='Data início (YYYY-MM-DD)')
    parser.add_argument('--fim', type=str, required=True, help='Data fim (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=100000, help='Limite de linhas (default: 100000)')
    parser.add_argument('--json', action='store_true', help='Saída em JSON completo')
    parser.add_argument('--excel', action='store_true', help='Saída em JSON tabular (para Excel)')

    args = parser.parse_args()

    try:
        datetime.strptime(args.inicio, '%Y-%m-%d')
        datetime.strptime(args.fim, '%Y-%m-%d')
    except ValueError:
        print("ERRO: Datas devem estar no formato YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    odoo = get_odoo_connection()
    if not odoo.authenticate():
        print("ERRO: Falha na autenticação com Odoo", file=sys.stderr)
        sys.exit(1)

    extrato = extrair_extrato_completo(odoo, args.inicio, args.fim, args.limit)

    if args.json:
        print(json.dumps(extrato, indent=2, ensure_ascii=False, default=str))
    elif args.excel:
        tabular = exportar_para_json_tabular(extrato)
        print(json.dumps(tabular, ensure_ascii=False, default=str))
    else:
        imprimir_resumo(extrato)


if __name__ == '__main__':
    main()
