#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mapeamento Completo de Vínculos Financeiros no Odoo
====================================================

Extrai 4 visões cruzadas para garantir consistência:
1. Extratos → IDs de títulos, notas de crédito, faturas
2. Títulos → IDs de extratos, notas de crédito, faturas
3. Faturas → IDs de extratos, títulos, notas de crédito
4. Notas de Crédito → IDs de extratos, títulos, faturas
5. [BÔNUS] Pagamentos → IDs de extratos, títulos (elo de ligação)

OBJETIVO: Identificar registros "soltos" (sem vínculo) para casamento manual.

FLUXO DE CONCILIAÇÃO:
  Extrato ←→ Pagamento (conciliação A, conta PENDENTES)
  Pagamento ←→ Título (conciliação B, conta FORNECEDORES)

Autor: Sistema de Fretes
Data: 21/12/2025
"""

import sys
import os
import argparse
import json
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict

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

def extrair_id(valor) -> Optional[int]:
    """Extrai ID de campo many2one."""
    if isinstance(valor, (list, tuple)) and len(valor) > 0:
        return valor[0]
    return valor if valor else None # type: ignore


def extrair_nome(valor) -> str:
    """Extrai nome de campo many2one."""
    if isinstance(valor, (list, tuple)) and len(valor) > 1:
        return valor[1]
    return str(valor) if valor else ''


def chunked(lst: List, size: int):
    """Divide lista em chunks."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def safe_list(valor) -> List:
    """Converte valor para lista segura."""
    if valor is None:
        return []
    if isinstance(valor, (list, tuple)):
        return list(valor)
    return [valor]


# ==============================================================================
# EXTRAÇÃO COMPLETA
# ==============================================================================

def extrair_mapeamento_completo(
    odoo,
    data_inicio: str,
    data_fim: str,
    limit: int = 50000,
    apenas_pagamentos: bool = False
) -> Dict:
    """
    Extrai mapeamento completo de vínculos financeiros.

    Args:
        odoo: Conexão Odoo
        data_inicio: Data início (YYYY-MM-DD)
        data_fim: Data fim (YYYY-MM-DD)
        limit: Limite por tipo de registro
        apenas_pagamentos: Se True, filtra apenas extratos < 0 (pagamentos)
    """
    print(f"\n{'='*70}", file=sys.stderr)
    print(f"MAPEAMENTO COMPLETO DE VÍNCULOS FINANCEIROS", file=sys.stderr)
    print(f"Período: {data_inicio} a {data_fim}", file=sys.stderr)
    print(f"Filtro: {'Apenas pagamentos (< 0)' if apenas_pagamentos else 'Todos'}", file=sys.stderr)
    print(f"{'='*70}", file=sys.stderr)

    resultado = {
        'periodo': {'data_inicio': data_inicio, 'data_fim': data_fim},
        'timestamp': datetime.now().isoformat(),
        'extratos': [],
        'titulos': [],
        'faturas': [],
        'notas_credito': [],
        'pagamentos': [],
        'resumo': {}
    }

    # =========================================================================
    # ETAPA 1: EXTRAIR LINHAS DE EXTRATO
    # =========================================================================
    print(f"\n[1/11] Buscando linhas de extrato...", file=sys.stderr)

    domain_extrato = [
        ('date', '>=', data_inicio),
        ('date', '<=', data_fim),
    ]
    if apenas_pagamentos:
        domain_extrato.append(('amount', '<', 0))

    extratos_raw = odoo.search_read(
        'account.bank.statement.line',
        domain_extrato,
        fields=[
            'id', 'date', 'payment_ref', 'amount', 'partner_id',
            'journal_id', 'move_id', 'is_reconciled', 'amount_residual'
        ],
        limit=limit
    )
    print(f"    Encontradas: {len(extratos_raw)} linhas de extrato", file=sys.stderr)

    # Índices para navegação
    extrato_por_id = {e['id']: e for e in extratos_raw}
    extrato_move_ids = [extrair_id(e.get('move_id')) for e in extratos_raw if e.get('move_id')]

    # =========================================================================
    # ETAPA 1.1: BUSCAR PARCEIROS COM CNPJ (BATCH)
    # =========================================================================
    print(f"[1.1/11] Buscando CNPJs dos parceiros...", file=sys.stderr)

    # Coletar todos os partner_ids únicos
    all_partner_ids: Set[int] = set()
    for e in extratos_raw:
        pid = extrair_id(e.get('partner_id'))
        if pid:
            all_partner_ids.add(pid)

    parceiros_por_id: Dict[int, Dict] = {}
    if all_partner_ids:
        for chunk in chunked(list(all_partner_ids), 200):
            parceiros = odoo.search_read(
                'res.partner',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'l10n_br_cnpj', 'l10n_br_cpf'],
                limit=len(chunk)
            )
            for p in parceiros:
                parceiros_por_id[p['id']] = p

    print(f"    Parceiros carregados: {len(parceiros_por_id)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 1.2: BUSCAR DIÁRIOS/CONTAS BANCÁRIAS (BATCH)
    # =========================================================================
    print(f"[1.2/11] Buscando contas bancárias...", file=sys.stderr)

    journal_ids = list(set(extrair_id(e.get('journal_id')) for e in extratos_raw if e.get('journal_id')))
    diarios_por_id: Dict[int, Dict] = {}
    if journal_ids:
        for chunk in chunked(journal_ids, 100):
            diarios = odoo.search_read(
                'account.journal',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'code', 'type'],
                limit=len(chunk)
            )
            for d in diarios:
                diarios_por_id[d['id']] = d

    print(f"    Diários carregados: {len(diarios_por_id)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 2: BUSCAR LINHAS DOS MOVES DE EXTRATO
    # =========================================================================
    print(f"[2/11] Buscando linhas dos moves de extrato...", file=sys.stderr)

    linhas_extrato_por_move = defaultdict(list)
    reconcile_ids_a: Set[int] = set()  # Conciliações A (extrato↔pagamento)

    if extrato_move_ids:
        for chunk in chunked(list(set(extrato_move_ids)), 100):
            linhas = odoo.search_read(
                'account.move.line',
                [('move_id', 'in', chunk)],
                fields=['id', 'move_id', 'debit', 'credit', 'full_reconcile_id', 'account_id'],
                limit=len(chunk) * 5
            )
            for ln in linhas:
                move_id = extrair_id(ln.get('move_id'))
                linhas_extrato_por_move[move_id].append(ln)
                if ln.get('full_reconcile_id'):
                    reconcile_ids_a.add(extrair_id(ln['full_reconcile_id']))

    print(f"    Conciliações A (extrato↔pagamento): {len(reconcile_ids_a)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 3: BUSCAR LINHAS DAS CONCILIAÇÕES A
    # =========================================================================
    print(f"[3/11] Buscando linhas das conciliações A...", file=sys.stderr)

    linhas_por_reconcile_a = defaultdict(list)
    payment_move_ids: Set[int] = set()

    if reconcile_ids_a:
        for chunk in chunked(list(reconcile_ids_a), 100):
            linhas = odoo.search_read(
                'account.move.line',
                [('full_reconcile_id', 'in', chunk)],
                fields=['id', 'move_id', 'full_reconcile_id', 'debit', 'credit'],
                limit=len(chunk) * 10
            )
            for ln in linhas:
                rec_id = extrair_id(ln.get('full_reconcile_id'))
                linhas_por_reconcile_a[rec_id].append(ln)
                move_id = extrair_id(ln.get('move_id'))
                if move_id not in extrato_move_ids:
                    payment_move_ids.add(move_id)

    print(f"    Moves de pagamento candidatos: {len(payment_move_ids)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 4: BUSCAR PAGAMENTOS (account.payment)
    # =========================================================================
    print(f"[4/11] Buscando pagamentos...", file=sys.stderr)

    payments_por_move = {}
    if payment_move_ids:
        for chunk in chunked(list(payment_move_ids), 100):
            payments = odoo.search_read(
                'account.payment',
                [('move_id', 'in', chunk)],
                fields=['id', 'name', 'move_id', 'amount', 'payment_type',
                        'partner_id', 'date', 'ref', 'state'],
                limit=len(chunk)
            )
            for p in payments:
                m_id = extrair_id(p.get('move_id'))
                payments_por_move[m_id] = p

    print(f"    Pagamentos encontrados: {len(payments_por_move)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 5: BUSCAR LINHAS DE DÉBITO DOS PAGAMENTOS (conciliação B)
    # =========================================================================
    print(f"[5/11] Buscando conciliações B (pagamento↔título)...", file=sys.stderr)

    payment_debit_lines = defaultdict(list)
    reconcile_ids_b: Set[int] = set()

    if payment_move_ids:
        for chunk in chunked(list(payment_move_ids), 100):
            linhas = odoo.search_read(
                'account.move.line',
                [
                    ('move_id', 'in', chunk),
                    ('debit', '>', 0),
                    ('account_type', '=', 'liability_payable')
                ],
                fields=['id', 'move_id', 'full_reconcile_id', 'debit', 'partner_id'],
                limit=len(chunk) * 5
            )
            for ln in linhas:
                move_id = extrair_id(ln.get('move_id'))
                payment_debit_lines[move_id].append(ln)
                if ln.get('full_reconcile_id'):
                    rec_id = extrair_id(ln['full_reconcile_id'])
                    if rec_id not in reconcile_ids_a:
                        reconcile_ids_b.add(rec_id)

    print(f"    Conciliações B (pagamento↔título): {len(reconcile_ids_b)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 6: BUSCAR LINHAS DAS CONCILIAÇÕES B
    # =========================================================================
    print(f"[6/11] Buscando linhas das conciliações B...", file=sys.stderr)

    linhas_por_reconcile_b = defaultdict(list)
    titulo_move_ids: Set[int] = set()

    if reconcile_ids_b:
        for chunk in chunked(list(reconcile_ids_b), 100):
            linhas = odoo.search_read(
                'account.move.line',
                [('full_reconcile_id', 'in', chunk)],
                fields=['id', 'move_id', 'full_reconcile_id', 'debit', 'credit',
                        'date_maturity', 'partner_id'],
                limit=len(chunk) * 10
            )
            for ln in linhas:
                rec_id = extrair_id(ln.get('full_reconcile_id'))
                linhas_por_reconcile_b[rec_id].append(ln)
                move_id = extrair_id(ln.get('move_id'))
                if move_id not in payment_move_ids:
                    titulo_move_ids.add(move_id)

    print(f"    Moves de título candidatos: {len(titulo_move_ids)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 7: BUSCAR FATURAS E NOTAS DE CRÉDITO
    # =========================================================================
    print(f"[7/11] Buscando faturas do período...", file=sys.stderr)

    domain_fatura = [
        ('move_type', 'in', ['in_invoice', 'in_refund']),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', data_inicio),
        ('invoice_date', '<=', data_fim),
    ]

    faturas_raw = odoo.search_read(
        'account.move',
        domain_fatura,
        fields=[
            'id', 'name', 'ref', 'move_type', 'partner_id', 'invoice_date',
            'amount_total', 'amount_residual', 'payment_state', 'invoice_origin',
            'reversed_entry_id', 'l10n_br_numero_nota_fiscal', 'l10n_br_chave_nf'
        ],
        limit=limit
    )

    # Separar faturas e notas de crédito
    faturas_lista = [f for f in faturas_raw if f.get('move_type') == 'in_invoice']
    notas_credito_lista = [f for f in faturas_raw if f.get('move_type') == 'in_refund']

    print(f"    Faturas: {len(faturas_lista)}, Notas de crédito: {len(notas_credito_lista)}", file=sys.stderr)

    fatura_ids = [f['id'] for f in faturas_lista]
    nc_ids = [nc['id'] for nc in notas_credito_lista]

    # =========================================================================
    # ETAPA 8: BUSCAR TÍTULOS DAS FATURAS
    # =========================================================================
    print(f"[8/11] Buscando títulos das faturas...", file=sys.stderr)

    titulos_por_fatura = defaultdict(list)
    todos_titulos = []

    all_fatura_ids = list(set(fatura_ids + list(titulo_move_ids)))
    if all_fatura_ids:
        for chunk in chunked(all_fatura_ids, 100):
            titulos = odoo.search_read(
                'account.move.line',
                [
                    ('move_id', 'in', chunk),
                    ('account_type', '=', 'liability_payable'),
                    ('parent_state', '=', 'posted')
                ],
                fields=[
                    'id', 'name', 'move_id', 'date_maturity', 'debit', 'credit',
                    'amount_residual', 'reconciled', 'full_reconcile_id',
                    'matched_debit_ids', 'matched_credit_ids', 'partner_id',
                    'statement_line_id', 'l10n_br_cobranca_parcela', 'account_id'
                ],
                limit=len(chunk) * 10
            )
            todos_titulos.extend(titulos)
            for t in titulos:
                move_id = extrair_id(t.get('move_id'))
                titulos_por_fatura[move_id].append(t)

    print(f"    Títulos encontrados: {len(todos_titulos)}", file=sys.stderr)

    titulo_por_id = {t['id']: t for t in todos_titulos}

    # =========================================================================
    # ETAPA 9: BUSCAR NOTAS DE CRÉDITO VINCULADAS (reversed_entry_id)
    # =========================================================================
    print(f"[9/11] Mapeando notas de crédito vinculadas...", file=sys.stderr)

    nc_por_fatura_origem = defaultdict(list)
    for nc in notas_credito_lista:
        orig_id = extrair_id(nc.get('reversed_entry_id'))
        if orig_id:
            nc_por_fatura_origem[orig_id].append(nc['id'])

    print(f"    Faturas com NC vinculada: {len(nc_por_fatura_origem)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 10: COLETAR TODOS OS PARCEIROS (para CNPJ)
    # =========================================================================
    print(f"[10/11] Coletando CNPJs de todos os parceiros...", file=sys.stderr)

    # Adicionar parceiros das faturas e títulos
    for f in faturas_raw:
        pid = extrair_id(f.get('partner_id'))
        if pid:
            all_partner_ids.add(pid)
    for t in todos_titulos:
        pid = extrair_id(t.get('partner_id'))
        if pid:
            all_partner_ids.add(pid)
    for p in payments_por_move.values():
        pid = extrair_id(p.get('partner_id'))
        if pid:
            all_partner_ids.add(pid)

    # Buscar parceiros que ainda não temos
    parceiros_faltantes = all_partner_ids - set(parceiros_por_id.keys())
    if parceiros_faltantes:
        for chunk in chunked(list(parceiros_faltantes), 200):
            parceiros = odoo.search_read(
                'res.partner',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'l10n_br_cnpj', 'l10n_br_cpf'],
                limit=len(chunk)
            )
            for p in parceiros:
                parceiros_por_id[p['id']] = p

    print(f"    Total parceiros com CNPJ: {len(parceiros_por_id)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 11: MONTAR VISÕES CRUZADAS
    # =========================================================================
    print(f"[11/11] Montando visões cruzadas...", file=sys.stderr)

    # Mapear extrato_id -> conciliação A -> payment_move_id -> conciliação B -> titulo_id
    extrato_para_titulos = defaultdict(set)
    extrato_para_faturas = defaultdict(set)
    extrato_para_ncs = defaultdict(set)
    extrato_para_payments = defaultdict(set)

    titulo_para_extratos = defaultdict(set)
    titulo_para_payments = defaultdict(set)

    payment_para_extratos = defaultdict(set)
    payment_para_titulos = defaultdict(set)

    for extrato in extratos_raw:
        extrato_id = extrato['id']
        move_id = extrair_id(extrato.get('move_id'))

        if not move_id:
            continue

        # Buscar linhas do extrato com conciliação
        for ln_ext in linhas_extrato_por_move.get(move_id, []):
            rec_a_id = extrair_id(ln_ext.get('full_reconcile_id'))
            if not rec_a_id:
                continue

            # Buscar linhas da conciliação A
            for ln_rec_a in linhas_por_reconcile_a.get(rec_a_id, []):
                pmt_move_id = extrair_id(ln_rec_a.get('move_id'))
                if pmt_move_id == move_id:
                    continue  # É o próprio extrato

                # Verificar se é um payment
                if pmt_move_id in payments_por_move:
                    payment = payments_por_move[pmt_move_id]
                    extrato_para_payments[extrato_id].add(payment['id'])
                    payment_para_extratos[payment['id']].add(extrato_id)

                    # Buscar títulos via conciliação B
                    for ln_pmt in payment_debit_lines.get(pmt_move_id, []):
                        rec_b_id = extrair_id(ln_pmt.get('full_reconcile_id'))
                        if not rec_b_id:
                            continue

                        for ln_rec_b in linhas_por_reconcile_b.get(rec_b_id, []):
                            titulo_move_id = extrair_id(ln_rec_b.get('move_id'))
                            if titulo_move_id == pmt_move_id:
                                continue

                            # Buscar título pelo ID da linha
                            titulo_id = ln_rec_b['id']
                            if titulo_id in titulo_por_id:
                                extrato_para_titulos[extrato_id].add(titulo_id)
                                titulo_para_extratos[titulo_id].add(extrato_id)
                                titulo_para_payments[titulo_id].add(payment['id'])
                                payment_para_titulos[payment['id']].add(titulo_id)

                                # Fatura do título
                                fatura_id = titulo_move_id
                                extrato_para_faturas[extrato_id].add(fatura_id)

                                # Notas de crédito da fatura
                                for nc_id in nc_por_fatura_origem.get(fatura_id, []):
                                    extrato_para_ncs[extrato_id].add(nc_id)

    # -------------------------------------------------------------------------
    # VISÃO 1: EXTRATOS
    # -------------------------------------------------------------------------
    for extrato in extratos_raw:
        ext_id = extrato['id']
        partner_id = extrair_id(extrato.get('partner_id'))
        journal_id = extrair_id(extrato.get('journal_id'))
        parceiro = parceiros_por_id.get(partner_id, {})
        diario = diarios_por_id.get(journal_id, {})

        resultado['extratos'].append({
            'id': ext_id,
            'data': extrato.get('date'),
            'referencia': extrato.get('payment_ref'),
            'valor': extrato.get('amount'),
            'conciliado': extrato.get('is_reconciled', False),
            'residual': extrato.get('amount_residual'),
            'parceiro_id': partner_id,
            'parceiro_nome': parceiro.get('name') or extrair_nome(extrato.get('partner_id')),
            'parceiro_cnpj': parceiro.get('l10n_br_cnpj') or parceiro.get('l10n_br_cpf') or '',
            'move_id': extrair_id(extrato.get('move_id')),
            'journal_id': journal_id,
            'conta_bancaria': diario.get('name') or extrair_nome(extrato.get('journal_id')),
            'conta_codigo': diario.get('code') or '',
            # VÍNCULOS
            'titulo_ids': list(extrato_para_titulos.get(ext_id, [])),
            'fatura_ids': list(extrato_para_faturas.get(ext_id, [])),
            'nota_credito_ids': list(extrato_para_ncs.get(ext_id, [])),
            'payment_ids': list(extrato_para_payments.get(ext_id, [])),
            # STATUS
            'tem_vinculo': len(extrato_para_titulos.get(ext_id, [])) > 0,
        })

    # -------------------------------------------------------------------------
    # VISÃO 2: TÍTULOS
    # -------------------------------------------------------------------------
    # Criar índice de faturas para buscar número NF
    faturas_por_id = {f['id']: f for f in faturas_raw}

    for titulo in todos_titulos:
        tit_id = titulo['id']
        fatura_id = extrair_id(titulo.get('move_id'))
        partner_id = extrair_id(titulo.get('partner_id'))
        parceiro = parceiros_por_id.get(partner_id, {})
        fatura_ref = faturas_por_id.get(fatura_id, {})

        # Buscar notas de crédito da fatura
        ncs_fatura = nc_por_fatura_origem.get(fatura_id, [])

        # Buscar extrato direto (statement_line_id)
        stmt_line_id = extrair_id(titulo.get('statement_line_id'))
        extrato_ids_titulo = set(titulo_para_extratos.get(tit_id, []))
        if stmt_line_id:
            extrato_ids_titulo.add(stmt_line_id)

        resultado['titulos'].append({
            'id': tit_id,
            'nome': titulo.get('name'),
            'vencimento': titulo.get('date_maturity'),
            'valor': abs(titulo.get('credit') or titulo.get('debit') or 0),
            'residual': abs(titulo.get('amount_residual') or 0),
            'conciliado': titulo.get('reconciled', False),
            'full_reconcile_id': extrair_id(titulo.get('full_reconcile_id')),
            'parcela': titulo.get('l10n_br_cobranca_parcela'),
            'conta_contabil': extrair_nome(titulo.get('account_id')),
            'parceiro_id': partner_id,
            'parceiro_nome': parceiro.get('name') or extrair_nome(titulo.get('partner_id')),
            'parceiro_cnpj': parceiro.get('l10n_br_cnpj') or parceiro.get('l10n_br_cpf') or '',
            # VÍNCULOS
            'fatura_id': fatura_id,
            'fatura_numero': fatura_ref.get('name'),
            'fatura_nf': fatura_ref.get('l10n_br_numero_nota_fiscal'),
            'extrato_ids': list(extrato_ids_titulo),
            'nota_credito_ids': ncs_fatura,
            'payment_ids': list(titulo_para_payments.get(tit_id, [])),
            # STATUS
            'tem_extrato': len(extrato_ids_titulo) > 0,
        })

    # -------------------------------------------------------------------------
    # VISÃO 3: FATURAS
    # -------------------------------------------------------------------------
    fatura_para_extratos = defaultdict(set)
    fatura_para_titulos = defaultdict(set)

    for tit_id, ext_ids in titulo_para_extratos.items():
        titulo = titulo_por_id.get(tit_id, {})
        fatura_id = extrair_id(titulo.get('move_id'))
        if fatura_id:
            fatura_para_extratos[fatura_id].update(ext_ids)
            fatura_para_titulos[fatura_id].add(tit_id)

    for fatura in faturas_lista:
        fat_id = fatura['id']
        titulos_fat = titulos_por_fatura.get(fat_id, [])
        partner_id = extrair_id(fatura.get('partner_id'))
        parceiro = parceiros_por_id.get(partner_id, {})

        resultado['faturas'].append({
            'id': fat_id,
            'numero': fatura.get('name'),
            'ref': fatura.get('ref'),
            'numero_nf': fatura.get('l10n_br_numero_nota_fiscal'),
            'chave_nfe': fatura.get('l10n_br_chave_nf'),
            'data': fatura.get('invoice_date'),
            'valor_total': fatura.get('amount_total'),
            'valor_residual': fatura.get('amount_residual'),
            'status_pagamento': fatura.get('payment_state'),
            'origem': fatura.get('invoice_origin'),
            'parceiro_id': partner_id,
            'parceiro_nome': parceiro.get('name') or extrair_nome(fatura.get('partner_id')),
            'parceiro_cnpj': parceiro.get('l10n_br_cnpj') or parceiro.get('l10n_br_cpf') or '',
            # VÍNCULOS
            'titulo_ids': [t['id'] for t in titulos_fat],
            'extrato_ids': list(fatura_para_extratos.get(fat_id, [])),
            'nota_credito_ids': nc_por_fatura_origem.get(fat_id, []),
            # STATUS
            'tem_extrato': len(fatura_para_extratos.get(fat_id, [])) > 0,
            'qtd_titulos': len(titulos_fat),
        })

    # -------------------------------------------------------------------------
    # VISÃO 4: NOTAS DE CRÉDITO
    # -------------------------------------------------------------------------
    for nc in notas_credito_lista:
        nc_id = nc['id']
        fatura_orig_id = extrair_id(nc.get('reversed_entry_id'))
        partner_id = extrair_id(nc.get('partner_id'))
        parceiro = parceiros_por_id.get(partner_id, {})
        fatura_orig = faturas_por_id.get(fatura_orig_id, {})

        # Buscar títulos e extratos da fatura original
        titulos_orig = [t['id'] for t in titulos_por_fatura.get(fatura_orig_id, [])] if fatura_orig_id else []
        extratos_orig = list(fatura_para_extratos.get(fatura_orig_id, [])) if fatura_orig_id else []

        resultado['notas_credito'].append({
            'id': nc_id,
            'numero': nc.get('name'),
            'ref': nc.get('ref'),
            'data': nc.get('invoice_date'),
            'valor_total': nc.get('amount_total'),
            'valor_residual': nc.get('amount_residual'),
            'parceiro_id': partner_id,
            'parceiro_nome': parceiro.get('name') or extrair_nome(nc.get('partner_id')),
            'parceiro_cnpj': parceiro.get('l10n_br_cnpj') or parceiro.get('l10n_br_cpf') or '',
            # VÍNCULOS
            'fatura_origem_id': fatura_orig_id,
            'fatura_origem_numero': fatura_orig.get('name'),
            'titulo_ids': titulos_orig,
            'extrato_ids': extratos_orig,
            # STATUS
            'tem_fatura_origem': fatura_orig_id is not None,
        })

    # -------------------------------------------------------------------------
    # VISÃO 5: PAGAMENTOS (BÔNUS - elo de ligação)
    # -------------------------------------------------------------------------
    for payment in payments_por_move.values():
        pmt_id = payment['id']
        partner_id = extrair_id(payment.get('partner_id'))
        parceiro = parceiros_por_id.get(partner_id, {})

        resultado['pagamentos'].append({
            'id': pmt_id,
            'nome': payment.get('name'),
            'data': payment.get('date'),
            'valor': payment.get('amount'),
            'tipo': payment.get('payment_type'),
            'ref': payment.get('ref'),
            'state': payment.get('state'),
            'move_id': extrair_id(payment.get('move_id')),
            'parceiro_id': partner_id,
            'parceiro_nome': parceiro.get('name') or extrair_nome(payment.get('partner_id')),
            'parceiro_cnpj': parceiro.get('l10n_br_cnpj') or parceiro.get('l10n_br_cpf') or '',
            # VÍNCULOS
            'extrato_ids': list(payment_para_extratos.get(pmt_id, [])),
            'titulo_ids': list(payment_para_titulos.get(pmt_id, [])),
        })

    # -------------------------------------------------------------------------
    # RESUMO
    # -------------------------------------------------------------------------
    resultado['resumo'] = {
        'total_extratos': len(resultado['extratos']),
        'extratos_com_vinculo': sum(1 for e in resultado['extratos'] if e['tem_vinculo']),
        'extratos_sem_vinculo': sum(1 for e in resultado['extratos'] if not e['tem_vinculo']),
        'total_titulos': len(resultado['titulos']),
        'titulos_com_extrato': sum(1 for t in resultado['titulos'] if t['tem_extrato']),
        'titulos_sem_extrato': sum(1 for t in resultado['titulos'] if not t['tem_extrato']),
        'total_faturas': len(resultado['faturas']),
        'faturas_com_extrato': sum(1 for f in resultado['faturas'] if f['tem_extrato']),
        'faturas_sem_extrato': sum(1 for f in resultado['faturas'] if not f['tem_extrato']),
        'total_notas_credito': len(resultado['notas_credito']),
        'ncs_com_fatura_origem': sum(1 for nc in resultado['notas_credito'] if nc['tem_fatura_origem']),
        'total_pagamentos': len(resultado['pagamentos']),
    }

    print(f"\n{'='*70}", file=sys.stderr)
    print(f"RESUMO", file=sys.stderr)
    print(f"{'='*70}", file=sys.stderr)
    for k, v in resultado['resumo'].items():
        print(f"  {k}: {v}", file=sys.stderr)

    return resultado


# ==============================================================================
# EXPORTAÇÃO PARA EXCEL
# ==============================================================================

def exportar_para_excel(dados: Dict) -> Dict:
    """
    Converte dados para formato tabular (múltiplas abas).
    """
    abas = {}

    # ABA 1: EXTRATOS
    abas['extratos'] = []
    for ext in dados['extratos']:
        abas['extratos'].append({
            'ID': ext['id'],
            'Data': ext['data'],
            'Referencia': ext['referencia'],
            'Valor': ext['valor'],
            'Conciliado': 'Sim' if ext['conciliado'] else 'Não',
            'Residual': ext['residual'],
            'Parceiro ID': ext['parceiro_id'],
            'Parceiro': ext['parceiro_nome'],
            'CNPJ': ext.get('parceiro_cnpj', ''),
            'Conta Bancaria': ext.get('conta_bancaria', ''),
            'Conta Codigo': ext.get('conta_codigo', ''),
            'Move ID': ext['move_id'],
            'Journal ID': ext['journal_id'],
            # VÍNCULOS
            'Titulo IDs': ', '.join(map(str, ext['titulo_ids'])) if ext['titulo_ids'] else '',
            'Fatura IDs': ', '.join(map(str, ext['fatura_ids'])) if ext['fatura_ids'] else '',
            'NC IDs': ', '.join(map(str, ext['nota_credito_ids'])) if ext['nota_credito_ids'] else '',
            'Payment IDs': ', '.join(map(str, ext['payment_ids'])) if ext['payment_ids'] else '',
            'Tem Vinculo': 'Sim' if ext['tem_vinculo'] else 'NÃO',
        })

    # ABA 2: TÍTULOS
    abas['titulos'] = []
    for tit in dados['titulos']:
        abas['titulos'].append({
            'ID': tit['id'],
            'Nome': tit['nome'],
            'Vencimento': tit['vencimento'],
            'Valor': tit['valor'],
            'Residual': tit['residual'],
            'Parcela': tit.get('parcela', ''),
            'Conta Contabil': tit.get('conta_contabil', ''),
            'Conciliado': 'Sim' if tit['conciliado'] else 'Não',
            'Full Reconcile ID': tit['full_reconcile_id'],
            'Parceiro ID': tit['parceiro_id'],
            'Parceiro': tit['parceiro_nome'],
            'CNPJ': tit.get('parceiro_cnpj', ''),
            # VÍNCULOS
            'Fatura ID': tit['fatura_id'],
            'Fatura Numero': tit.get('fatura_numero', ''),
            'Fatura NF': tit.get('fatura_nf', ''),
            'Extrato IDs': ', '.join(map(str, tit['extrato_ids'])) if tit['extrato_ids'] else '',
            'NC IDs': ', '.join(map(str, tit['nota_credito_ids'])) if tit['nota_credito_ids'] else '',
            'Payment IDs': ', '.join(map(str, tit['payment_ids'])) if tit['payment_ids'] else '',
            'Tem Extrato': 'Sim' if tit['tem_extrato'] else 'NÃO',
        })

    # ABA 3: FATURAS
    abas['faturas'] = []
    for fat in dados['faturas']:
        abas['faturas'].append({
            'ID': fat['id'],
            'Numero': fat['numero'],
            'Ref': fat['ref'],
            'Numero NF': fat['numero_nf'],
            'Chave NFe': fat.get('chave_nfe', ''),
            'Data': fat['data'],
            'Valor Total': fat['valor_total'],
            'Valor Residual': fat['valor_residual'],
            'Status Pagamento': fat['status_pagamento'],
            'Origem': fat['origem'],
            'Parceiro ID': fat['parceiro_id'],
            'Parceiro': fat['parceiro_nome'],
            'CNPJ': fat.get('parceiro_cnpj', ''),
            # VÍNCULOS
            'Titulo IDs': ', '.join(map(str, fat['titulo_ids'])) if fat['titulo_ids'] else '',
            'Extrato IDs': ', '.join(map(str, fat['extrato_ids'])) if fat['extrato_ids'] else '',
            'NC IDs': ', '.join(map(str, fat['nota_credito_ids'])) if fat['nota_credito_ids'] else '',
            'Tem Extrato': 'Sim' if fat['tem_extrato'] else 'NÃO',
            'Qtd Titulos': fat['qtd_titulos'],
        })

    # ABA 4: NOTAS DE CRÉDITO
    abas['notas_credito'] = []
    for nc in dados['notas_credito']:
        abas['notas_credito'].append({
            'ID': nc['id'],
            'Numero': nc['numero'],
            'Ref': nc['ref'],
            'Data': nc['data'],
            'Valor Total': nc['valor_total'],
            'Valor Residual': nc.get('valor_residual', ''),
            'Parceiro ID': nc['parceiro_id'],
            'Parceiro': nc['parceiro_nome'],
            'CNPJ': nc.get('parceiro_cnpj', ''),
            # VÍNCULOS
            'Fatura Origem ID': nc['fatura_origem_id'],
            'Fatura Origem Numero': nc.get('fatura_origem_numero', ''),
            'Titulo IDs': ', '.join(map(str, nc['titulo_ids'])) if nc['titulo_ids'] else '',
            'Extrato IDs': ', '.join(map(str, nc['extrato_ids'])) if nc['extrato_ids'] else '',
            'Tem Fatura Origem': 'Sim' if nc['tem_fatura_origem'] else 'NÃO',
        })

    # ABA 5: PAGAMENTOS
    abas['pagamentos'] = []
    for pmt in dados['pagamentos']:
        abas['pagamentos'].append({
            'ID': pmt['id'],
            'Nome': pmt['nome'],
            'Data': pmt['data'],
            'Valor': pmt['valor'],
            'Tipo': pmt['tipo'],
            'Ref': pmt['ref'],
            'State': pmt['state'],
            'Move ID': pmt['move_id'],
            'Parceiro ID': pmt['parceiro_id'],
            'Parceiro': pmt['parceiro_nome'],
            'CNPJ': pmt.get('parceiro_cnpj', ''),
            # VÍNCULOS
            'Extrato IDs': ', '.join(map(str, pmt['extrato_ids'])) if pmt['extrato_ids'] else '',
            'Titulo IDs': ', '.join(map(str, pmt['titulo_ids'])) if pmt['titulo_ids'] else '',
        })

    # ABA 6: RESUMO
    abas['resumo'] = [dados['resumo']]

    return abas


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Mapeamento completo de vínculos financeiros no Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Extrato de 2024 até hoje
  python mapeamento_vinculos_completo.py --inicio 2024-07-01 --fim 2025-12-31

  # Apenas pagamentos (< 0)
  python mapeamento_vinculos_completo.py --inicio 2024-07-01 --fim 2025-12-31 --pagamentos

  # Exportar JSON completo
  python mapeamento_vinculos_completo.py --inicio 2024-07-01 --fim 2025-12-31 --json

  # Exportar formato Excel (JSON tabular)
  python mapeamento_vinculos_completo.py --inicio 2024-07-01 --fim 2025-12-31 --excel
        """
    )

    parser.add_argument('--inicio', type=str, required=True, help='Data início (YYYY-MM-DD)')
    parser.add_argument('--fim', type=str, required=True, help='Data fim (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=50000, help='Limite por tipo (default: 50000)')
    parser.add_argument('--pagamentos', action='store_true', help='Apenas extratos < 0 (pagamentos)')
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

    dados = extrair_mapeamento_completo(
        odoo,
        args.inicio,
        args.fim,
        args.limit,
        args.pagamentos
    )

    if args.json:
        print(json.dumps(dados, indent=2, ensure_ascii=False, default=str))
    elif args.excel:
        tabular = exportar_para_excel(dados)
        print(json.dumps(tabular, ensure_ascii=False, default=str))
    else:
        # Apenas resumo
        print(json.dumps(dados['resumo'], indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
