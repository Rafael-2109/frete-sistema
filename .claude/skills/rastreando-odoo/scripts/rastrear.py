#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rastreamento de Fluxos Documentais no Odoo

Rastreia o fluxo completo de documentos a partir de qualquer ponto de entrada:
- NF de compra → Requisição → PO → Fatura → Títulos → Conciliação
- NF de venda → SO → Picking → Fatura → Títulos → Conciliação
- Devolução → NF original → Pedido original

Autor: Sistema de Fretes
Data: 16/12/2025
"""

import sys
import os
import argparse
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# Import do módulo de normalização (mesmo diretório)
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from normalizar import normalizar_entidade, get_odoo_connection


# ==============================================================================
# CAMPOS PADRÃO PARA CADA MODELO
# ==============================================================================

CAMPOS = {
    'dfe': [
        'id', 'protnfe_infnfe_chnfe', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
        'nfe_infnfe_ide_finnfe', 'nfe_infnfe_ide_dhemi', 'nfe_infnfe_emit_cnpj',
        'nfe_infnfe_emit_xnome', 'nfe_infnfe_dest_cnpj', 'nfe_infnfe_total_icmstot_vnf',
        'l10n_br_status', 'is_cte', 'purchase_id', 'invoice_ids',
        # Campos de impostos (CTe/NF-e)
        'nfe_infnfe_total_icmstot_vicms',   # Valor ICMS
        'nfe_infnfe_total_icmstot_vbcicms', # Base ICMS
        'nfe_infnfe_total_icmstot_vpis',    # Valor PIS
        'nfe_infnfe_total_icmstot_vcofins', # Valor COFINS
        'nfe_infnfe_total_icmstot_vprod',   # Valor Produtos/Servicos
    ],
    'purchase_requisition': [
        'id', 'name', 'state', 'ordering_date', 'purchase_ids',
    ],
    'purchase_order': [
        'id', 'name', 'partner_id', 'state', 'date_order', 'date_planned',
        'amount_total', 'amount_untaxed', 'amount_tax', 'invoice_status',
        'invoice_ids', 'requisition_id', 'origin',
    ],
    'sale_order': [
        'id', 'name', 'partner_id', 'state', 'date_order', 'amount_total',
        'amount_untaxed', 'amount_tax', 'invoice_status', 'invoice_ids',
        'picking_ids',
    ],
    'stock_picking': [
        'id', 'name', 'partner_id', 'state', 'scheduled_date', 'date_done',
        'origin', 'sale_id', 'picking_type_id',
    ],
    'account_move': [
        'id', 'name', 'ref', 'partner_id', 'move_type', 'state', 'payment_state',
        'date', 'invoice_date', 'invoice_date_due', 'amount_total', 'amount_untaxed',
        'amount_tax', 'amount_residual', 'invoice_origin', 'l10n_br_chave_nf',
        'reversed_entry_id', 'picking_ids',
    ],
    'account_move_line': [
        'id', 'name', 'move_id', 'account_id', 'partner_id', 'date', 'date_maturity',
        'debit', 'credit', 'balance', 'amount_residual', 'reconciled',
        'full_reconcile_id', 'statement_line_id',
    ],
    'account_full_reconcile': [
        'id', 'name', 'reconciled_line_ids', 'partial_reconcile_ids',
    ],
    'account_bank_statement_line': [
        'id', 'date', 'payment_ref', 'partner_id', 'amount', 'move_id',
    ],
}

# Tipos de documento (finnfe no DFE)
TIPOS_DFE = {
    '1': 'normal',
    '2': 'complementar',
    '3': 'ajuste',
    '4': 'devolucao',
}

# Tipos de fatura
TIPOS_FATURA = {
    'out_invoice': 'fatura_venda',
    'out_refund': 'credito_venda',
    'in_invoice': 'fatura_compra',
    'in_refund': 'credito_compra',
    'entry': 'lancamento',
}


# ==============================================================================
# FUNÇÕES DE BUSCA INDIVIDUAL
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


def buscar_dfe(odoo, filtros: list, limit: int = 20) -> List[Dict]:
    """Busca DFE com filtros."""
    return odoo.search_read(
        'l10n_br_ciel_it_account.dfe',
        filtros,
        fields=CAMPOS['dfe'],
        limit=limit
    )


def buscar_dfe_por_chave(odoo, chave: str) -> Optional[Dict]:
    """Busca DFE por chave NF-e."""
    dfes = buscar_dfe(odoo, [('protnfe_infnfe_chnfe', '=', chave)], limit=1)
    return dfes[0] if dfes else None


def buscar_po(odoo, po_id: int) -> Optional[Dict]:
    """Busca purchase.order por ID."""
    pos = odoo.search_read(
        'purchase.order',
        [('id', '=', po_id)],
        fields=CAMPOS['purchase_order'],
        limit=1
    )
    return pos[0] if pos else None


def buscar_requisicao(odoo, requisition_id: int) -> Optional[Dict]:
    """Busca purchase.requisition por ID."""
    reqs = odoo.search_read(
        'purchase.requisition',
        [('id', '=', requisition_id)],
        fields=CAMPOS['purchase_requisition'],
        limit=1
    )
    return reqs[0] if reqs else None


def buscar_so(odoo, so_id: int) -> Optional[Dict]:
    """Busca sale.order por ID."""
    sos = odoo.search_read(
        'sale.order',
        [('id', '=', so_id)],
        fields=CAMPOS['sale_order'],
        limit=1
    )
    return sos[0] if sos else None


def buscar_so_por_nome(odoo, nome: str) -> Optional[Dict]:
    """Busca sale.order por nome."""
    sos = odoo.search_read(
        'sale.order',
        [('name', 'ilike', nome)],
        fields=CAMPOS['sale_order'],
        limit=1
    )
    return sos[0] if sos else None


def buscar_picking(odoo, picking_id: int) -> Optional[Dict]:
    """Busca stock.picking por ID."""
    pickings = odoo.search_read(
        'stock.picking',
        [('id', '=', picking_id)],
        fields=CAMPOS['stock_picking'],
        limit=1
    )
    return pickings[0] if pickings else None


def buscar_fatura(odoo, move_id: int) -> Optional[Dict]:
    """Busca account.move por ID."""
    faturas = odoo.search_read(
        'account.move',
        [('id', '=', move_id)],
        fields=CAMPOS['account_move'],
        limit=1
    )
    return faturas[0] if faturas else None


def buscar_fatura_por_chave(odoo, chave: str) -> Optional[Dict]:
    """Busca account.move por chave NF-e."""
    faturas = odoo.search_read(
        'account.move',
        [('l10n_br_chave_nf', '=', chave)],
        fields=CAMPOS['account_move'],
        limit=1
    )
    return faturas[0] if faturas else None


def buscar_titulos(odoo, move_id: int, apenas_pendentes: bool = False) -> List[Dict]:
    """Busca títulos (account.move.line) de uma fatura."""
    filtros = [
        ('move_id', '=', move_id),
        ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable'])
    ]
    if apenas_pendentes:
        filtros.append(('reconciled', '=', False))

    return odoo.search_read(
        'account.move.line',
        filtros,
        fields=CAMPOS['account_move_line'],
        limit=50
    )


def buscar_lancamentos_diario(odoo, move_id: int) -> List[Dict]:
    """Busca todas as linhas do diário de uma fatura."""
    return odoo.search_read(
        'account.move.line',
        [('move_id', '=', move_id)],
        fields=CAMPOS['account_move_line'],
        limit=100
    )


def buscar_conciliacao(odoo, reconcile_id: int) -> Optional[Dict]:
    """Busca account.full.reconcile por ID."""
    recs = odoo.search_read(
        'account.full.reconcile',
        [('id', '=', reconcile_id)],
        fields=CAMPOS['account_full_reconcile'],
        limit=1
    )
    return recs[0] if recs else None


def buscar_extrato_linhas(odoo, statement_line_ids: List[int]) -> List[Dict]:
    """Busca linhas de extrato bancário."""
    if not statement_line_ids:
        return []
    return odoo.search_read(
        'account.bank.statement.line',
        [('id', 'in', statement_line_ids)],
        fields=CAMPOS['account_bank_statement_line'],
        limit=50
    )


# ==============================================================================
# FUNÇÕES DE RASTREAMENTO DE FLUXO
# ==============================================================================

def rastrear_fluxo_compra(odoo, dfe: Dict) -> Dict[str, Any]:
    """
    Rastreia fluxo de compra a partir de um DFE.

    DFE → PO → Requisição → Fatura → Títulos → Conciliação
    """
    fluxo = {
        'tipo': 'compra',
        'dfe': dfe,
        'pedido_compra': None,
        'requisicao': None,
        'fatura': None,
        'titulos': [],
        'lancamentos_diario': [],
        'conciliacoes': [],
        'extrato': [],
    }

    # 1. Buscar PO vinculado ao DFE
    po_id = extrair_id(dfe.get('purchase_id'))
    if po_id:
        fluxo['pedido_compra'] = buscar_po(odoo, po_id)

        # 2. Buscar requisição do PO
        if fluxo['pedido_compra']:
            req_id = extrair_id(fluxo['pedido_compra'].get('requisition_id'))
            if req_id:
                fluxo['requisicao'] = buscar_requisicao(odoo, req_id)

    # 3. Buscar fatura vinculada ao DFE
    invoice_ids = dfe.get('invoice_ids', [])
    if invoice_ids:
        fatura_id = invoice_ids[0] if isinstance(invoice_ids, list) else invoice_ids
        fluxo['fatura'] = buscar_fatura(odoo, fatura_id)
    else:
        # Tentar buscar pela chave NF-e
        chave = dfe.get('protnfe_infnfe_chnfe')
        if chave:
            fluxo['fatura'] = buscar_fatura_por_chave(odoo, chave)

    # 4. Se não achou fatura mas achou PO, buscar faturas do PO
    if not fluxo['fatura'] and fluxo['pedido_compra']:
        po_invoice_ids = fluxo['pedido_compra'].get('invoice_ids', [])
        if po_invoice_ids:
            fluxo['fatura'] = buscar_fatura(odoo, po_invoice_ids[0])

    # 5. Buscar títulos e lançamentos da fatura
    if fluxo['fatura']:
        move_id = fluxo['fatura']['id']
        fluxo['titulos'] = buscar_titulos(odoo, move_id)
        fluxo['lancamentos_diario'] = buscar_lancamentos_diario(odoo, move_id)

        # 6. Buscar conciliações
        for titulo in fluxo['titulos']:
            reconcile_id = extrair_id(titulo.get('full_reconcile_id'))
            if reconcile_id:
                conc = buscar_conciliacao(odoo, reconcile_id)
                if conc and conc not in fluxo['conciliacoes']:
                    fluxo['conciliacoes'].append(conc)

            # 7. Buscar linhas de extrato
            stmt_line_id = extrair_id(titulo.get('statement_line_id'))
            if stmt_line_id:
                extrato = buscar_extrato_linhas(odoo, [stmt_line_id])
                fluxo['extrato'].extend(extrato)

    return fluxo


def rastrear_fluxo_venda(odoo, so: Dict) -> Dict[str, Any]:
    """
    Rastreia fluxo de venda a partir de um sale.order.

    SO → Pickings → Fatura → Títulos → Conciliação
    """
    fluxo = {
        'tipo': 'venda',
        'pedido_venda': so,
        'pickings': [],
        'faturas': [],
        'titulos': [],
        'lancamentos_diario': [],
        'conciliacoes': [],
        'extrato': [],
    }

    # 1. Buscar pickings do SO
    picking_ids = so.get('picking_ids', [])
    for picking_id in picking_ids:
        picking = buscar_picking(odoo, picking_id)
        if picking:
            fluxo['pickings'].append(picking)

    # 2. Buscar faturas do SO
    invoice_ids = so.get('invoice_ids', [])
    for invoice_id in invoice_ids:
        fatura = buscar_fatura(odoo, invoice_id)
        if fatura:
            fluxo['faturas'].append(fatura)

            # 3. Buscar títulos de cada fatura
            titulos = buscar_titulos(odoo, invoice_id)
            fluxo['titulos'].extend(titulos)

            # 4. Buscar lançamentos do diário
            lancamentos = buscar_lancamentos_diario(odoo, invoice_id)
            fluxo['lancamentos_diario'].extend(lancamentos)

    # 5. Buscar conciliações e extrato
    for titulo in fluxo['titulos']:
        reconcile_id = extrair_id(titulo.get('full_reconcile_id'))
        if reconcile_id:
            conc = buscar_conciliacao(odoo, reconcile_id)
            if conc and conc not in fluxo['conciliacoes']:
                fluxo['conciliacoes'].append(conc)

        stmt_line_id = extrair_id(titulo.get('statement_line_id'))
        if stmt_line_id:
            extrato = buscar_extrato_linhas(odoo, [stmt_line_id])
            fluxo['extrato'].extend(extrato)

    return fluxo


def rastrear_fluxo_devolucao(odoo, dfe: Dict) -> Dict[str, Any]:
    """
    Rastreia fluxo de devolução a partir de um DFE.

    DFE (devolução) → Nota de Crédito → NF Original → Pedido Original
    """
    fluxo = {
        'tipo': 'devolucao',
        'dfe_devolucao': dfe,
        'nota_credito': None,
        'nf_original': None,
        'pedido_original': None,
        'tipo_devolucao': None,  # 'venda' ou 'compra'
    }

    # 1. Buscar nota de crédito vinculada
    invoice_ids = dfe.get('invoice_ids', [])
    if invoice_ids:
        fluxo['nota_credito'] = buscar_fatura(odoo, invoice_ids[0])

    # 2. Buscar NF original via reversed_entry_id
    if fluxo['nota_credito']:
        reversed_id = extrair_id(fluxo['nota_credito'].get('reversed_entry_id'))
        if reversed_id:
            fluxo['nf_original'] = buscar_fatura(odoo, reversed_id)

    # 3. Determinar tipo e buscar pedido original
    if fluxo['nf_original']:
        move_type = fluxo['nf_original'].get('move_type', '')
        origin = fluxo['nf_original'].get('invoice_origin', '')

        if move_type == 'out_invoice':
            fluxo['tipo_devolucao'] = 'venda'
            # Buscar SO pelo origin
            if origin:
                fluxo['pedido_original'] = buscar_so_por_nome(odoo, origin)

        elif move_type == 'in_invoice':
            fluxo['tipo_devolucao'] = 'compra'
            # Buscar PO pelo origin
            if origin:
                pos = odoo.search_read(
                    'purchase.order',
                    [('name', 'ilike', origin)],
                    fields=CAMPOS['purchase_order'],
                    limit=1
                )
                if pos:
                    fluxo['pedido_original'] = pos[0]

    return fluxo


# ==============================================================================
# FUNÇÃO PRINCIPAL DE RASTREAMENTO
# ==============================================================================

def rastrear(odoo, entrada: str, fluxo_forcado: str = None) -> Dict[str, Any]:
    """
    Rastreia o fluxo completo a partir de qualquer entrada.

    Args:
        odoo: Conexão Odoo
        entrada: Termo de busca (nome, CNPJ, NF, PO, SO, chave)
        fluxo_forcado: 'compra', 'venda' ou None (auto-detectar)

    Returns:
        Dict com o fluxo completo rastreado
    """
    resultado = {
        'entrada': entrada,
        'timestamp': datetime.now().isoformat(),
        'sucesso': False,
        'fluxo': None,
        'erro': None,
    }

    try:
        # 1. Normalizar entrada
        normalizacao = normalizar_entidade(odoo, entrada)

        if not normalizacao.get('sucesso'):
            resultado['erro'] = f"Falha na normalização: {normalizacao.get('erro')}"
            return resultado

        tipo = normalizacao.get('tipo')
        resultado['normalizacao'] = normalizacao

        # 2. Rastrear baseado no tipo detectado
        if tipo == 'chave_nfe':
            # Buscar DFE ou fatura pela chave
            dfe = normalizacao.get('dfe')
            fatura = normalizacao.get('fatura')

            if dfe:
                finnfe = dfe.get('nfe_infnfe_ide_finnfe', '1')
                if finnfe == '4':
                    resultado['fluxo'] = rastrear_fluxo_devolucao(odoo, dfe)
                else:
                    resultado['fluxo'] = rastrear_fluxo_compra(odoo, dfe)
            elif fatura:
                move_type = fatura.get('move_type', '')
                if 'out' in move_type:
                    # Buscar SO pelo origin
                    origin = fatura.get('invoice_origin', '')
                    if origin:
                        so = buscar_so_por_nome(odoo, origin)
                        if so:
                            resultado['fluxo'] = rastrear_fluxo_venda(odoo, so)
                else:
                    # Tentar encontrar DFE pela chave
                    chave = normalizacao['termo_original']
                    dfe = buscar_dfe_por_chave(odoo, chave)
                    if dfe:
                        resultado['fluxo'] = rastrear_fluxo_compra(odoo, dfe)

        elif tipo == 'nf_numero':
            # Tentar DFE primeiro, depois faturas
            dfes = normalizacao.get('dfe', [])
            if dfes:
                dfe = dfes[0]
                finnfe = dfe.get('nfe_infnfe_ide_finnfe', '1')
                is_cte = dfe.get('is_cte', False)

                if finnfe == '4':
                    resultado['fluxo'] = rastrear_fluxo_devolucao(odoo, dfe)
                elif is_cte:
                    resultado['fluxo'] = {'tipo': 'cte', 'dfe': dfe}
                else:
                    resultado['fluxo'] = rastrear_fluxo_compra(odoo, dfe)
            else:
                faturas = normalizacao.get('faturas', [])
                if faturas:
                    fatura = faturas[0]
                    move_type = fatura.get('move_type', '')
                    if 'out' in move_type:
                        origin = fatura.get('invoice_origin', '')
                        if origin:
                            so = buscar_so_por_nome(odoo, origin)
                            if so:
                                resultado['fluxo'] = rastrear_fluxo_venda(odoo, so)

        elif tipo == 'po':
            pos = normalizacao.get('encontrados', [])
            if pos:
                po = pos[0]
                # Criar fluxo a partir do PO
                resultado['fluxo'] = {
                    'tipo': 'compra',
                    'pedido_compra': po,
                    'requisicao': None,
                    'dfe': None,
                    'fatura': None,
                    'titulos': [],
                    'lancamentos_diario': [],
                    'conciliacoes': [],
                    'extrato': [],
                }

                # Buscar requisição
                req_id = extrair_id(po.get('requisition_id'))
                if req_id:
                    resultado['fluxo']['requisicao'] = buscar_requisicao(odoo, req_id)

                # Buscar faturas
                invoice_ids = po.get('invoice_ids', [])
                if invoice_ids:
                    resultado['fluxo']['fatura'] = buscar_fatura(odoo, invoice_ids[0])

                    # Buscar títulos
                    resultado['fluxo']['titulos'] = buscar_titulos(odoo, invoice_ids[0])
                    resultado['fluxo']['lancamentos_diario'] = buscar_lancamentos_diario(odoo, invoice_ids[0])

        elif tipo == 'so':
            sos = normalizacao.get('encontrados', [])
            if sos:
                resultado['fluxo'] = rastrear_fluxo_venda(odoo, sos[0])

        elif tipo in ['parceiro', 'cnpj']:
            # Para parceiros, retornar documentos recentes
            parceiros = normalizacao.get('encontrados', [])
            if parceiros:
                partner_ids = [p['id'] for p in parceiros]

                # Buscar últimas faturas do parceiro
                faturas = odoo.search_read(
                    'account.move',
                    [('partner_id', 'in', partner_ids), ('state', '=', 'posted')],
                    fields=CAMPOS['account_move'],
                    limit=20,
                    order='invoice_date desc'
                )

                # Buscar últimos DFEs do parceiro
                dfes = buscar_dfe(odoo, [
                    '|',
                    ('nfe_infnfe_emit_cnpj', 'ilike', normalizacao.get('cnpj_formatado', '')),
                    ('nfe_infnfe_dest_cnpj', 'ilike', normalizacao.get('cnpj_formatado', ''))
                ], limit=20)

                resultado['fluxo'] = {
                    'tipo': 'parceiro',
                    'parceiros': parceiros,
                    'faturas_recentes': faturas,
                    'dfes_recentes': dfes,
                }

        resultado['sucesso'] = resultado['fluxo'] is not None

        if not resultado['sucesso']:
            resultado['erro'] = "Não foi possível rastrear o fluxo a partir da entrada fornecida"

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


# ==============================================================================
# FORMATAÇÃO DE SAÍDA
# ==============================================================================

def formatar_valor(valor):
    """Formata valor monetário."""
    if valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def formatar_data(data_str):
    """Formata data."""
    if not data_str:
        return "N/A"
    if isinstance(data_str, str):
        return data_str[:10] if len(data_str) >= 10 else data_str
    return str(data_str)


def imprimir_fluxo(resultado: Dict):
    """Imprime o fluxo de forma legível."""
    print(f"\n{'='*70}")
    print(f"RASTREAMENTO: {resultado.get('entrada')}")
    print(f"Timestamp: {resultado.get('timestamp')}")
    print(f"{'='*70}")

    if not resultado.get('sucesso'):
        print(f"\n❌ ERRO: {resultado.get('erro')}")
        return

    fluxo = resultado.get('fluxo', {})
    tipo = fluxo.get('tipo', 'desconhecido')
    print(f"\n📋 TIPO DE FLUXO: {tipo.upper()}")

    if tipo == 'compra':
        # DFE
        dfe = fluxo.get('dfe')
        if dfe:
            finnfe = TIPOS_DFE.get(dfe.get('nfe_infnfe_ide_finnfe', '1'), 'normal')
            print(f"\n📄 DFE (NF Entrada) - {finnfe.upper()}")
            print(f"   NF: {dfe.get('nfe_infnfe_ide_nnf')}-{dfe.get('nfe_infnfe_ide_serie', '1')}")
            print(f"   Chave: {dfe.get('protnfe_infnfe_chnfe', 'N/A')}")
            print(f"   Emitente: {dfe.get('nfe_infnfe_emit_xnome')} ({dfe.get('nfe_infnfe_emit_cnpj')})")
            print(f"   Valor: {formatar_valor(dfe.get('nfe_infnfe_total_icmstot_vnf'))}")
            print(f"   Data: {formatar_data(dfe.get('nfe_infnfe_ide_dhemi'))}")

        # Requisição
        req = fluxo.get('requisicao')
        if req:
            print(f"\n📝 REQUISIÇÃO DE COMPRA")
            print(f"   Número: {req.get('name')}")
            print(f"   Status: {req.get('state')}")

        # PO
        po = fluxo.get('pedido_compra')
        if po:
            print(f"\n🛒 PEDIDO DE COMPRA")
            print(f"   Número: {po.get('name')}")
            print(f"   Fornecedor: {extrair_nome(po.get('partner_id'))}")
            print(f"   Status: {po.get('state')} | Fatura: {po.get('invoice_status')}")
            print(f"   Valor: {formatar_valor(po.get('amount_total'))}")
            print(f"   Data: {formatar_data(po.get('date_order'))}")

        # Fatura
        fatura = fluxo.get('fatura')
        if fatura:
            print(f"\n💰 FATURA (account.move)")
            print(f"   Número: {fatura.get('name')}")
            print(f"   Tipo: {TIPOS_FATURA.get(fatura.get('move_type'), fatura.get('move_type'))}")
            print(f"   Status: {fatura.get('state')} | Pagamento: {fatura.get('payment_state')}")
            print(f"   Valor: {formatar_valor(fatura.get('amount_total'))} | Em aberto: {formatar_valor(fatura.get('amount_residual'))}")

        # Títulos
        titulos = fluxo.get('titulos', [])
        if titulos:
            print(f"\n📋 TÍTULOS ({len(titulos)})")
            for t in titulos[:5]:
                venc = formatar_data(t.get('date_maturity'))
                valor = t.get('debit') or t.get('credit') or 0
                residual = t.get('amount_residual', 0)
                status = "✓ Conciliado" if t.get('reconciled') else "○ Pendente"
                print(f"   [{t.get('id')}] {formatar_valor(valor)} venc:{venc} res:{formatar_valor(residual)} {status}")

        # Conciliações
        concs = fluxo.get('conciliacoes', [])
        if concs:
            print(f"\n🔗 CONCILIAÇÕES ({len(concs)})")
            for c in concs[:3]:
                print(f"   [{c.get('id')}] {c.get('name', 'N/A')}")

    elif tipo == 'venda':
        # SO
        so = fluxo.get('pedido_venda')
        if so:
            print(f"\n🛍️ PEDIDO DE VENDA")
            print(f"   Número: {so.get('name')}")
            print(f"   Cliente: {extrair_nome(so.get('partner_id'))}")
            print(f"   Status: {so.get('state')} | Fatura: {so.get('invoice_status')}")
            print(f"   Valor: {formatar_valor(so.get('amount_total'))}")
            print(f"   Data: {formatar_data(so.get('date_order'))}")

        # Pickings
        pickings = fluxo.get('pickings', [])
        if pickings:
            print(f"\n📦 EXPEDIÇÕES ({len(pickings)})")
            for p in pickings[:3]:
                print(f"   [{p.get('id')}] {p.get('name')} - {p.get('state')} - {formatar_data(p.get('date_done'))}")

        # Faturas
        faturas = fluxo.get('faturas', [])
        if faturas:
            print(f"\n💰 FATURAS ({len(faturas)})")
            for f in faturas[:3]:
                print(f"   [{f.get('id')}] {f.get('name')} - {TIPOS_FATURA.get(f.get('move_type'))} - {formatar_valor(f.get('amount_total'))}")

        # Títulos
        titulos = fluxo.get('titulos', [])
        if titulos:
            print(f"\n📋 TÍTULOS ({len(titulos)})")
            for t in titulos[:5]:
                venc = formatar_data(t.get('date_maturity'))
                valor = t.get('debit') or t.get('credit') or 0
                residual = t.get('amount_residual', 0)
                status = "✓ Conciliado" if t.get('reconciled') else "○ Pendente"
                print(f"   [{t.get('id')}] {formatar_valor(valor)} venc:{venc} res:{formatar_valor(residual)} {status}")

    elif tipo == 'devolucao':
        dfe = fluxo.get('dfe_devolucao')
        if dfe:
            print(f"\n🔄 DFE DEVOLUÇÃO")
            print(f"   NF: {dfe.get('nfe_infnfe_ide_nnf')}")
            print(f"   Emitente: {dfe.get('nfe_infnfe_emit_xnome')}")
            print(f"   Valor: {formatar_valor(dfe.get('nfe_infnfe_total_icmstot_vnf'))}")

        nc = fluxo.get('nota_credito')
        if nc:
            print(f"\n💳 NOTA DE CRÉDITO")
            print(f"   Número: {nc.get('name')}")
            print(f"   Tipo: {TIPOS_FATURA.get(nc.get('move_type'))}")

        nf_orig = fluxo.get('nf_original')
        if nf_orig:
            print(f"\n📄 NF ORIGINAL")
            print(f"   Número: {nf_orig.get('name')}")
            print(f"   Valor: {formatar_valor(nf_orig.get('amount_total'))}")

        pedido = fluxo.get('pedido_original')
        if pedido:
            tipo_ped = fluxo.get('tipo_devolucao', 'desconhecido')
            print(f"\n📦 PEDIDO ORIGINAL ({tipo_ped.upper()})")
            print(f"   Número: {pedido.get('name')}")

    elif tipo == 'parceiro':
        parceiros = fluxo.get('parceiros', [])
        print(f"\n👤 PARCEIROS ({len(parceiros)})")
        for p in parceiros[:5]:
            print(f"   [{p.get('id')}] {p.get('name')} - {p.get('l10n_br_cnpj', 'N/A')}")

        faturas = fluxo.get('faturas_recentes', [])
        if faturas:
            print(f"\n💰 FATURAS RECENTES ({len(faturas)})")
            for f in faturas[:5]:
                print(f"   [{f.get('id')}] {f.get('name')} - {TIPOS_FATURA.get(f.get('move_type'))} - {formatar_valor(f.get('amount_total'))}")

        dfes = fluxo.get('dfes_recentes', [])
        if dfes:
            print(f"\n📄 DFEs RECENTES ({len(dfes)})")
            for d in dfes[:5]:
                print(f"   [{d.get('id')}] NF {d.get('nfe_infnfe_ide_nnf')} - {d.get('nfe_infnfe_emit_xnome')}")

    print()


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Rastreia fluxos documentais completos no Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Rastrear por chave NF-e
  python rastrear.py "35251218467441000163550010000123451000000017"

  # Rastrear por número de NF
  python rastrear.py "NF 12345"
  python rastrear.py "12345"

  # Rastrear por PO
  python rastrear.py "PO00789"

  # Rastrear por SO (pedido de venda)
  python rastrear.py "VCD123"
  python rastrear.py "VFB456"

  # Rastrear por cliente/fornecedor
  python rastrear.py "Atacadão"
  python rastrear.py "18467441"  # CNPJ

Fluxos suportados:
  - COMPRA: DFE → PO → Requisição → Fatura → Títulos → Conciliação
  - VENDA: SO → Picking → Fatura → Títulos → Conciliação
  - DEVOLUÇÃO: DFE → Nota Crédito → NF Original → Pedido Original
        """
    )

    parser.add_argument('entrada', help='Termo a rastrear (NF, PO, SO, chave, cliente)')
    parser.add_argument('--fluxo', choices=['compra', 'venda'], help='Forçar tipo de fluxo')
    parser.add_argument('--json', action='store_true', help='Saída em JSON')

    args = parser.parse_args()

    odoo = get_odoo_connection()
    if not odoo.authenticate():
        print("ERRO: Falha na autenticação com Odoo")
        sys.exit(1)

    resultado = rastrear(odoo, args.entrada, args.fluxo)

    if args.json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
    else:
        imprimir_fluxo(resultado)


if __name__ == '__main__':
    main()
