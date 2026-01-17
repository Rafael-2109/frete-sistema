#!/usr/bin/env python3
"""
Auditoria de Conciliação - Fatos Documentados

Extrai vínculos REAIS entre:
- FATURAS ↔ EXTRATOS (via account.partial.reconcile)
- FATURAS ↔ NOTAS DE CRÉDITO (via reversed_entry_id)
- EXTRATOS sem vínculo

Sem suposições, apenas relacionamentos documentados no Odoo.

Uso:
    python auditoria_conciliacao.py --json
    python auditoria_conciliacao.py --excel
"""

import sys
import os
import json
import argparse
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app.odoo.utils.connection import get_odoo_connection # noqa: E402


def chunked(lst: List, n: int):
    """Divide lista em chunks de tamanho n."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


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


def executar_auditoria(data_inicio: str = '2024-01-01', data_fim: str = '2099-12-31') -> Dict:
    """
    Executa auditoria de conciliação extraindo apenas vínculos documentados.

    Retorna dicionário com:
    - faturas: Lista de faturas com vínculos reais
    - extratos: Lista de extratos negativos com vínculos reais
    - notas_credito: Lista de NCs com vínculo à fatura origem
    - vinculos: Lista expandida 1:1 de cada vínculo fatura↔extrato
    """
    odoo = get_odoo_connection()

    resultado = {
        'faturas': [],
        'extratos': [],
        'notas_credito': [],
        'vinculos_fatura_extrato': [],
        'resumo': {}
    }

    # =========================================================================
    # ETAPA 1: BUSCAR TODAS AS FATURAS DE COMPRA
    # =========================================================================
    print(f"[1/8] Buscando faturas de compra...", file=sys.stderr)

    faturas_raw = odoo.search_read(
        'account.move',
        [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
        ],
        fields=[
            'id', 'name', 'ref', 'partner_id', 'invoice_date', 'company_id',
            'amount_total', 'amount_residual', 'payment_state', 'invoice_origin',
            'l10n_br_numero_nota_fiscal', 'l10n_br_chave_nf'
        ],
        limit=100000
    )
    print(f"    Faturas encontradas: {len(faturas_raw)}", file=sys.stderr)

    fatura_por_id = {f['id']: f for f in faturas_raw}
    fatura_ids = list(fatura_por_id.keys())

    # =========================================================================
    # ETAPA 2: BUSCAR TODAS AS NOTAS DE CRÉDITO
    # =========================================================================
    print(f"[2/8] Buscando notas de crédito...", file=sys.stderr)

    ncs_raw = odoo.search_read(
        'account.move',
        [
            ('move_type', '=', 'in_refund'),
            ('state', '=', 'posted'),
        ],
        fields=[
            'id', 'name', 'ref', 'partner_id', 'invoice_date', 'company_id',
            'amount_total', 'amount_residual', 'payment_state',
            'reversed_entry_id', 'l10n_br_numero_nota_fiscal'
        ],
        limit=50000
    )
    print(f"    Notas de crédito encontradas: {len(ncs_raw)}", file=sys.stderr)

    # Mapear NC por fatura origem (reversed_entry_id)
    nc_por_fatura_origem: Dict[int, List[Dict]] = defaultdict(list)
    for nc in ncs_raw:
        orig_id = extrair_id(nc.get('reversed_entry_id'))
        if orig_id:
            nc_por_fatura_origem[orig_id].append(nc)

    # =========================================================================
    # ETAPA 3: BUSCAR TODOS OS EXTRATOS NEGATIVOS (PAGAMENTOS)
    # =========================================================================
    print(f"[3/8] Buscando extratos negativos (pagamentos)...", file=sys.stderr)

    extratos_raw = odoo.search_read(
        'account.bank.statement.line',
        [
            ('amount', '<', 0),  # Apenas pagamentos (saídas)
        ],
        fields=[
            'id', 'date', 'payment_ref', 'amount', 'partner_id', 'company_id',
            'move_id', 'journal_id', 'is_reconciled', 'amount_residual'
        ],
        limit=100000
    )
    print(f"    Extratos negativos encontrados: {len(extratos_raw)}", file=sys.stderr)

    extrato_por_id = {e['id']: e for e in extratos_raw}
    extrato_move_ids = {extrair_id(e.get('move_id')): e['id'] for e in extratos_raw if e.get('move_id')}

    # =========================================================================
    # ETAPA 4: BUSCAR TÍTULOS DAS FATURAS (account.move.line)
    # =========================================================================
    print(f"[4/8] Buscando títulos das faturas...", file=sys.stderr)

    titulos_por_fatura: Dict[int, List[Dict]] = defaultdict(list)
    titulo_por_id: Dict[int, Dict] = {}

    if fatura_ids:
        for chunk in chunked(fatura_ids, 200):
            titulos = odoo.search_read(
                'account.move.line',
                [
                    ('move_id', 'in', chunk),
                    ('account_type', '=', 'liability_payable'),
                    ('parent_state', '=', 'posted'),
                ],
                fields=[
                    'id', 'move_id', 'date_maturity', 'credit', 'debit',
                    'amount_residual', 'reconciled', 'full_reconcile_id',
                    'l10n_br_cobranca_parcela', 'partner_id'
                ],
                limit=len(chunk) * 10
            )
            for t in titulos:
                move_id = extrair_id(t.get('move_id'))
                titulos_por_fatura[move_id].append(t)
                titulo_por_id[t['id']] = t

    print(f"    Títulos encontrados: {len(titulo_por_id)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 5: BUSCAR PARTIAL RECONCILES (VÍNCULOS REAIS)
    # =========================================================================
    print(f"[5/8] Buscando vínculos de conciliação (partial_reconcile)...", file=sys.stderr)

    # Buscar todos os partial_reconciles
    partials_raw = odoo.search_read(
        'account.partial.reconcile',
        [],
        fields=['id', 'debit_move_id', 'credit_move_id', 'amount', 'full_reconcile_id'],
        limit=100000
    )
    print(f"    Partial reconciles: {len(partials_raw)}", file=sys.stderr)

    # Coletar todos os move.line IDs para buscar detalhes
    all_line_ids: Set[int] = set()
    for pr in partials_raw:
        all_line_ids.add(extrair_id(pr.get('debit_move_id')))
        all_line_ids.add(extrair_id(pr.get('credit_move_id')))
    all_line_ids.discard(None)

    # =========================================================================
    # ETAPA 6: BUSCAR DETALHES DAS LINHAS (para identificar extrato vs título)
    # =========================================================================
    print(f"[6/8] Buscando detalhes das linhas de conciliação...", file=sys.stderr)

    linha_por_id: Dict[int, Dict] = {}
    if all_line_ids:
        for chunk in chunked(list(all_line_ids), 500):
            linhas = odoo.search_read(
                'account.move.line',
                [('id', 'in', chunk)],
                fields=[
                    'id', 'move_id', 'statement_line_id', 'account_type',
                    'debit', 'credit', 'partner_id'
                ],
                limit=len(chunk)
            )
            for ln in linhas:
                linha_por_id[ln['id']] = ln

    print(f"    Linhas carregadas: {len(linha_por_id)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 7: MAPEAR VÍNCULOS VIA PAYMENT (Extrato → Payment → Título → Fatura)
    # =========================================================================
    print(f"[7/8] Mapeando vínculos via payment (2 etapas)...", file=sys.stderr)

    # PASSO 1: Classificar partial_reconciles em Conciliação A e B
    conc_a = []  # Extrato ↔ Payment
    conc_b = []  # Payment ↔ Título

    for pr in partials_raw:
        debit_line_id = extrair_id(pr.get('debit_move_id'))
        credit_line_id = extrair_id(pr.get('credit_move_id'))

        debit_line = linha_por_id.get(debit_line_id, {})
        credit_line = linha_por_id.get(credit_line_id, {})

        debit_stmt = extrair_id(debit_line.get('statement_line_id'))
        credit_stmt = extrair_id(credit_line.get('statement_line_id'))
        debit_is_titulo = 'payable' in str(debit_line.get('account_type', ''))
        credit_is_titulo = 'payable' in str(credit_line.get('account_type', ''))

        # Conciliação A: tem extrato
        if debit_stmt or credit_stmt:
            extrato_id = debit_stmt if debit_stmt and debit_stmt in extrato_por_id else None
            if not extrato_id:
                extrato_id = credit_stmt if credit_stmt and credit_stmt in extrato_por_id else None

            # O outro lado é do payment
            if debit_stmt:
                payment_move_id = extrair_id(credit_line.get('move_id'))
            else:
                payment_move_id = extrair_id(debit_line.get('move_id'))

            if extrato_id and payment_move_id:
                conc_a.append({
                    'partial_id': pr['id'],
                    'extrato_id': extrato_id,
                    'payment_move_id': payment_move_id,
                    'valor': pr.get('amount', 0),
                    'full_reconcile_id': extrair_id(pr.get('full_reconcile_id'))
                })

        # Conciliação B: tem título payable (e não tem extrato)
        elif debit_is_titulo or credit_is_titulo:
            debit_move_id = extrair_id(debit_line.get('move_id'))
            credit_move_id = extrair_id(credit_line.get('move_id'))

            # Identificar qual é fatura vs payment usando fatura_por_id
            if debit_move_id in fatura_por_id:
                titulo_fatura_id = debit_move_id
                payment_move_id = credit_move_id
            elif credit_move_id in fatura_por_id:
                titulo_fatura_id = credit_move_id
                payment_move_id = debit_move_id
            else:
                # Nenhum é fatura conhecida (pode ser NC, ajuste, etc)
                continue

            if titulo_fatura_id and payment_move_id:
                conc_b.append({
                    'partial_id': pr['id'],
                    'titulo_fatura_id': titulo_fatura_id,
                    'payment_move_id': payment_move_id,
                    'valor': pr.get('amount', 0),
                    'full_reconcile_id': extrair_id(pr.get('full_reconcile_id'))
                })

    print(f"    Conciliações A (extrato↔payment): {len(conc_a)}", file=sys.stderr)
    print(f"    Conciliações B (payment↔título): {len(conc_b)}", file=sys.stderr)

    # PASSO 2: Indexar por payment_move_id
    conc_a_por_payment = defaultdict(list)
    for ca in conc_a:
        conc_a_por_payment[ca['payment_move_id']].append(ca)

    conc_b_por_payment = defaultdict(list)
    for cb in conc_b:
        conc_b_por_payment[cb['payment_move_id']].append(cb)

    # PASSO 3: Cruzar para obter Extrato → Fatura
    fatura_para_extratos: Dict[int, Set[int]] = defaultdict(set)
    extrato_para_faturas: Dict[int, Set[int]] = defaultdict(set)
    vinculos_detalhados: List[Dict] = []

    for payment_move_id, lista_a in conc_a_por_payment.items():
        lista_b = conc_b_por_payment.get(payment_move_id, [])

        for ca in lista_a:
            extrato_id = ca['extrato_id']

            for cb in lista_b:
                fatura_id = cb['titulo_fatura_id']

                # Só registrar se a fatura existe no nosso índice
                if fatura_id in fatura_por_id:
                    fatura_para_extratos[fatura_id].add(extrato_id)
                    extrato_para_faturas[extrato_id].add(fatura_id)

                    vinculos_detalhados.append({
                        'partial_a_id': ca['partial_id'],
                        'partial_b_id': cb['partial_id'],
                        'fatura_id': fatura_id,
                        'extrato_id': extrato_id,
                        'valor_a': ca['valor'],
                        'valor_b': cb['valor'],
                        'payment_move_id': payment_move_id,
                        'full_reconcile_a': ca['full_reconcile_id'],
                        'full_reconcile_b': cb['full_reconcile_id'],
                    })

    print(f"    Vínculos mapeados (extrato↔fatura via payment): {len(vinculos_detalhados)}", file=sys.stderr)

    # =========================================================================
    # ETAPA 8: BUSCAR PARCEIROS E EMPRESAS
    # =========================================================================
    print(f"[8/8] Buscando parceiros e empresas...", file=sys.stderr)

    # Coletar IDs de parceiros e empresas
    partner_ids: Set[int] = set()
    company_ids: Set[int] = set()
    journal_ids: Set[int] = set()

    for f in faturas_raw:
        pid = extrair_id(f.get('partner_id'))
        cid = extrair_id(f.get('company_id'))
        if pid: partner_ids.add(pid) # type: ignore # noqa: E701
        if cid: company_ids.add(cid) # type: ignore # noqa: E701

    for nc in ncs_raw:
        pid = extrair_id(nc.get('partner_id'))
        cid = extrair_id(nc.get('company_id'))
        if pid: partner_ids.add(pid) # type: ignore # noqa: E701
        if cid: company_ids.add(cid) # type: ignore # noqa: E701

    for e in extratos_raw:
        pid = extrair_id(e.get('partner_id'))
        cid = extrair_id(e.get('company_id'))
        jid = extrair_id(e.get('journal_id'))
        if pid: partner_ids.add(pid) # type: ignore # noqa: E701
        if cid: company_ids.add(cid) # type: ignore # noqa: E701
        if jid: journal_ids.add(jid) # type: ignore # noqa: E701

    # Buscar parceiros
    parceiros_por_id: Dict[int, Dict] = {}
    if partner_ids:
        for chunk in chunked(list(partner_ids), 200):
            parceiros = odoo.search_read(
                'res.partner',
                [('id', 'in', chunk)],
                fields=['id', 'name', 'l10n_br_cnpj', 'l10n_br_cpf'],
                limit=len(chunk)
            )
            for p in parceiros:
                parceiros_por_id[p['id']] = p

    # Buscar empresas
    empresas_por_id: Dict[int, Dict] = {}
    if company_ids:
        empresas = odoo.search_read(
            'res.company',
            [('id', 'in', list(company_ids))],
            fields=['id', 'name'],
            limit=len(company_ids)
        )
        for emp in empresas:
            empresas_por_id[emp['id']] = emp

    # Buscar diários (contas bancárias)
    diarios_por_id: Dict[int, Dict] = {}
    if journal_ids:
        diarios = odoo.search_read(
            'account.journal',
            [('id', 'in', list(journal_ids))],
            fields=['id', 'name', 'code'],
            limit=len(journal_ids)
        )
        for d in diarios:
            diarios_por_id[d['id']] = d

    print(f"    Parceiros: {len(parceiros_por_id)}, Empresas: {len(empresas_por_id)}", file=sys.stderr)

    # =========================================================================
    # MONTAR RESULTADO: FATURAS
    # =========================================================================
    for fatura in faturas_raw:
        fat_id = fatura['id']
        partner_id = extrair_id(fatura.get('partner_id'))
        company_id = extrair_id(fatura.get('company_id'))
        parceiro = parceiros_por_id.get(partner_id, {})
        empresa = empresas_por_id.get(company_id, {})

        extrato_ids = list(fatura_para_extratos.get(fat_id, []))
        nc_ids = [nc['id'] for nc in nc_por_fatura_origem.get(fat_id, [])]

        resultado['faturas'].append({
            'id': fat_id,
            'numero': fatura.get('name'),
            'ref': fatura.get('ref'),
            'numero_nf': fatura.get('l10n_br_numero_nota_fiscal'),
            'chave_nfe': fatura.get('l10n_br_chave_nf'),
            'data': fatura.get('invoice_date'),
            'empresa_id': company_id,
            'empresa': empresa.get('name', ''),
            'parceiro_id': partner_id,
            'parceiro': parceiro.get('name') or extrair_nome(fatura.get('partner_id')),
            'cnpj': parceiro.get('l10n_br_cnpj') or parceiro.get('l10n_br_cpf') or '',
            'valor_total': fatura.get('amount_total'),
            'valor_residual': fatura.get('amount_residual'),
            'status_pagamento': fatura.get('payment_state'),
            'origem': fatura.get('invoice_origin'),
            # VÍNCULOS DOCUMENTADOS
            'extrato_ids': extrato_ids,
            'nota_credito_ids': nc_ids,
            'qtd_extratos': len(extrato_ids),
            'qtd_ncs': len(nc_ids),
        })

    # =========================================================================
    # MONTAR RESULTADO: EXTRATOS
    # =========================================================================
    for extrato in extratos_raw:
        ext_id = extrato['id']
        partner_id = extrair_id(extrato.get('partner_id'))
        company_id = extrair_id(extrato.get('company_id'))
        journal_id = extrair_id(extrato.get('journal_id'))
        parceiro = parceiros_por_id.get(partner_id, {})
        empresa = empresas_por_id.get(company_id, {})
        diario = diarios_por_id.get(journal_id, {})

        fatura_ids = list(extrato_para_faturas.get(ext_id, []))

        resultado['extratos'].append({
            'id': ext_id,
            'data': extrato.get('date'),
            'referencia': extrato.get('payment_ref'),
            'valor': extrato.get('amount'),
            'empresa_id': company_id,
            'empresa': empresa.get('name', ''),
            'parceiro_id': partner_id,
            'parceiro': parceiro.get('name') or extrair_nome(extrato.get('partner_id')),
            'cnpj': parceiro.get('l10n_br_cnpj') or parceiro.get('l10n_br_cpf') or '',
            'conta_bancaria': diario.get('name', ''),
            'conta_codigo': diario.get('code', ''),
            'conciliado': extrato.get('is_reconciled', False),
            'residual': extrato.get('amount_residual'),
            # VÍNCULOS DOCUMENTADOS
            'fatura_ids': fatura_ids,
            'qtd_faturas': len(fatura_ids),
        })

    # =========================================================================
    # MONTAR RESULTADO: NOTAS DE CRÉDITO
    # =========================================================================
    for nc in ncs_raw:
        nc_id = nc['id']
        partner_id = extrair_id(nc.get('partner_id'))
        company_id = extrair_id(nc.get('company_id'))
        fatura_orig_id = extrair_id(nc.get('reversed_entry_id'))
        parceiro = parceiros_por_id.get(partner_id, {})
        empresa = empresas_por_id.get(company_id, {})
        fatura_orig = fatura_por_id.get(fatura_orig_id, {})

        resultado['notas_credito'].append({
            'id': nc_id,
            'numero': nc.get('name'),
            'ref': nc.get('ref'),
            'numero_nf': nc.get('l10n_br_numero_nota_fiscal'),
            'data': nc.get('invoice_date'),
            'empresa_id': company_id,
            'empresa': empresa.get('name', ''),
            'parceiro_id': partner_id,
            'parceiro': parceiro.get('name') or extrair_nome(nc.get('partner_id')),
            'cnpj': parceiro.get('l10n_br_cnpj') or parceiro.get('l10n_br_cpf') or '',
            'valor_total': nc.get('amount_total'),
            'valor_residual': nc.get('amount_residual'),
            'status_pagamento': nc.get('payment_state'),
            # VÍNCULO DOCUMENTADO
            'fatura_origem_id': fatura_orig_id,
            'fatura_origem_numero': fatura_orig.get('name', ''),
            'tem_fatura_origem': fatura_orig_id is not None,
        })

    # =========================================================================
    # MONTAR RESULTADO: VÍNCULOS 1:1 (EXPANDIDO)
    # =========================================================================
    for v in vinculos_detalhados:
        fatura = fatura_por_id.get(v['fatura_id'], {})
        extrato = extrato_por_id.get(v['extrato_id'], {})

        partner_id_fat = extrair_id(fatura.get('partner_id'))
        partner_id_ext = extrair_id(extrato.get('partner_id'))
        company_id_fat = extrair_id(fatura.get('company_id'))
        company_id_ext = extrair_id(extrato.get('company_id'))

        parceiro_fat = parceiros_por_id.get(partner_id_fat, {})
        parceiro_ext = parceiros_por_id.get(partner_id_ext, {})
        empresa_fat = empresas_por_id.get(company_id_fat, {})
        empresa_ext = empresas_por_id.get(company_id_ext, {})

        resultado['vinculos_fatura_extrato'].append({
            # CONCILIAÇÃO VIA DUAS ETAPAS
            'partial_a_id': v['partial_a_id'],
            'partial_b_id': v['partial_b_id'],
            'payment_move_id': v['payment_move_id'],
            'valor_conc_a': v['valor_a'],
            'valor_conc_b': v['valor_b'],
            'full_reconcile_a': v['full_reconcile_a'],
            'full_reconcile_b': v['full_reconcile_b'],
            # FATURA
            'fatura_id': v['fatura_id'],
            'fatura_numero': fatura.get('name'),
            'fatura_nf': fatura.get('l10n_br_numero_nota_fiscal'),
            'fatura_data': fatura.get('invoice_date'),
            'fatura_valor': fatura.get('amount_total'),
            'fatura_empresa': empresa_fat.get('name', ''),
            'fatura_parceiro': parceiro_fat.get('name', ''),
            'fatura_cnpj': parceiro_fat.get('l10n_br_cnpj') or parceiro_fat.get('l10n_br_cpf') or '',
            # EXTRATO
            'extrato_id': v['extrato_id'],
            'extrato_data': extrato.get('date'),
            'extrato_ref': extrato.get('payment_ref'),
            'extrato_valor': extrato.get('amount'),
            'extrato_empresa': empresa_ext.get('name', ''),
            'extrato_parceiro': parceiro_ext.get('name', ''),
            'extrato_cnpj': parceiro_ext.get('l10n_br_cnpj') or parceiro_ext.get('l10n_br_cpf') or '',
        })

    # =========================================================================
    # RESUMO
    # =========================================================================
    faturas_com_extrato = len([f for f in resultado['faturas'] if f['qtd_extratos'] > 0])
    faturas_sem_extrato = len([f for f in resultado['faturas'] if f['qtd_extratos'] == 0])
    extratos_com_fatura = len([e for e in resultado['extratos'] if e['qtd_faturas'] > 0])
    extratos_sem_fatura = len([e for e in resultado['extratos'] if e['qtd_faturas'] == 0])
    ncs_com_origem = len([nc for nc in resultado['notas_credito'] if nc['tem_fatura_origem']])
    ncs_sem_origem = len([nc for nc in resultado['notas_credito'] if not nc['tem_fatura_origem']])

    resultado['resumo'] = {
        'total_faturas': len(resultado['faturas']),
        'faturas_com_extrato': faturas_com_extrato,
        'faturas_sem_extrato': faturas_sem_extrato,
        'total_extratos': len(resultado['extratos']),
        'extratos_com_fatura': extratos_com_fatura,
        'extratos_sem_fatura': extratos_sem_fatura,
        'total_notas_credito': len(resultado['notas_credito']),
        'ncs_com_fatura_origem': ncs_com_origem,
        'ncs_sem_fatura_origem': ncs_sem_origem,
        'total_vinculos': len(resultado['vinculos_fatura_extrato']),
        'gerado_em': datetime.now().isoformat(),
    }

    return resultado


def formatar_excel(dados: Dict) -> Dict[str, List[Dict]]:
    """Formata dados para exportação Excel."""
    abas = {}

    # ABA 1: FATURAS
    abas['faturas'] = []
    for fat in dados['faturas']:
        abas['faturas'].append({
            'ID': fat['id'],
            'Numero': fat['numero'],
            'Ref': fat['ref'],
            'Numero NF': fat['numero_nf'],
            'Chave NFe': fat['chave_nfe'],
            'Data': fat['data'],
            'Empresa': fat['empresa'],
            'Parceiro': fat['parceiro'],
            'CNPJ': fat['cnpj'],
            'Valor Total': fat['valor_total'],
            'Valor Residual': fat['valor_residual'],
            'Status Pagamento': fat['status_pagamento'],
            'Origem': fat['origem'],
            # VÍNCULOS
            'Extrato IDs': ', '.join(map(str, fat['extrato_ids'])) if fat['extrato_ids'] else '',
            'NC IDs': ', '.join(map(str, fat['nota_credito_ids'])) if fat['nota_credito_ids'] else '',
            'Qtd Extratos': fat['qtd_extratos'],
            'Qtd NCs': fat['qtd_ncs'],
        })

    # ABA 2: EXTRATOS (negativos)
    abas['extratos'] = []
    for ext in dados['extratos']:
        abas['extratos'].append({
            'ID': ext['id'],
            'Data': ext['data'],
            'Referencia': ext['referencia'],
            'Valor': ext['valor'],
            'Empresa': ext['empresa'],
            'Parceiro': ext['parceiro'],
            'CNPJ': ext['cnpj'],
            'Conta Bancaria': ext['conta_bancaria'],
            'Conta Codigo': ext['conta_codigo'],
            'Conciliado': 'Sim' if ext['conciliado'] else 'Não',
            'Residual': ext['residual'],
            # VÍNCULOS
            'Fatura IDs': ', '.join(map(str, ext['fatura_ids'])) if ext['fatura_ids'] else '',
            'Qtd Faturas': ext['qtd_faturas'],
        })

    # ABA 3: NOTAS DE CRÉDITO
    abas['notas_credito'] = []
    for nc in dados['notas_credito']:
        abas['notas_credito'].append({
            'ID': nc['id'],
            'Numero': nc['numero'],
            'Ref': nc['ref'],
            'Numero NF': nc['numero_nf'],
            'Data': nc['data'],
            'Empresa': nc['empresa'],
            'Parceiro': nc['parceiro'],
            'CNPJ': nc['cnpj'],
            'Valor Total': nc['valor_total'],
            'Valor Residual': nc['valor_residual'],
            'Status Pagamento': nc['status_pagamento'],
            # VÍNCULO
            'Fatura Origem ID': nc['fatura_origem_id'] or '',
            'Fatura Origem Numero': nc['fatura_origem_numero'],
            'Tem Fatura Origem': 'Sim' if nc['tem_fatura_origem'] else 'NÃO',
        })

    # ABA 4: VÍNCULOS (EXTRATO ↔ PAYMENT ↔ FATURA)
    abas['vinculos'] = []
    for v in dados['vinculos_fatura_extrato']:
        abas['vinculos'].append({
            # CONCILIAÇÃO EM DUAS ETAPAS
            'Partial A (Ext↔Pay)': v['partial_a_id'],
            'Partial B (Pay↔Tit)': v['partial_b_id'],
            'Payment Move ID': v['payment_move_id'],
            'Valor Conc A': v['valor_conc_a'],
            'Valor Conc B': v['valor_conc_b'],
            'Full Reconcile A': v['full_reconcile_a'] or '',
            'Full Reconcile B': v['full_reconcile_b'] or '',
            # FATURA
            'Fatura ID': v['fatura_id'],
            'Fatura Numero': v['fatura_numero'],
            'Fatura NF': v['fatura_nf'],
            'Fatura Data': v['fatura_data'],
            'Fatura Valor': v['fatura_valor'],
            'Fatura Empresa': v['fatura_empresa'],
            'Fatura Parceiro': v['fatura_parceiro'],
            'Fatura CNPJ': v['fatura_cnpj'],
            # EXTRATO
            'Extrato ID': v['extrato_id'],
            'Extrato Data': v['extrato_data'],
            'Extrato Ref': v['extrato_ref'],
            'Extrato Valor': v['extrato_valor'],
            'Extrato Empresa': v['extrato_empresa'],
            'Extrato Parceiro': v['extrato_parceiro'],
            'Extrato CNPJ': v['extrato_cnpj'],
        })

    # ABA 5: RESUMO
    abas['resumo'] = [dados['resumo']]

    return abas


def main():
    parser = argparse.ArgumentParser(description='Auditoria de Conciliação - Fatos Documentados')
    parser.add_argument('--json', action='store_true', help='Saída em JSON')
    parser.add_argument('--excel', action='store_true', help='Saída formatada para Excel')

    args = parser.parse_args()

    dados = executar_auditoria()

    if args.excel:
        abas = formatar_excel(dados)
        print(json.dumps(abas, ensure_ascii=False, default=str))
    else:
        print(json.dumps(dados, ensure_ascii=False, default=str, indent=2))


if __name__ == '__main__':
    main()
