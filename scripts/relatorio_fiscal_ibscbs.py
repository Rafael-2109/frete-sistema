#!/usr/bin/env python3
"""
Relatório de Documentos Fiscais com IBS/CBS
==========================================

Réplica exata do relatório "Documentos Fiscais" do Odoo
com adição dos campos IBS/CBS da reforma tributária.

Estrutura: 98 colunas originais + 21 campos IBS/CBS

Uso:
    source .venv/bin/activate
    python scripts/relatorio_fiscal_ibscbs.py

Autor: Sistema de Fretes
Data: 2025-01-14
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from app.odoo.utils.connection import get_odoo_connection


def extrair_relatorio_fiscal_datas(data_ini, data_fim, tipos: list = None):
    """
    Extrai relatório fiscal idêntico ao Odoo + campos IBS/CBS
    (Versão com datas explícitas - usada pelo endpoint Flask)

    Args:
        data_ini: Data inicial (datetime.date)
        data_fim: Data final (datetime.date)
        tipos: Lista de tipos de documento ['out_invoice', 'in_invoice', etc.]

    Returns:
        Caminho do arquivo Excel gerado ou None
    """
    return _extrair_relatorio_fiscal_impl(data_ini, data_fim, tipos)


def extrair_relatorio_fiscal(dias_atras: int = 2, tipos: list = None):
    """
    Extrai relatório fiscal idêntico ao Odoo + campos IBS/CBS

    Args:
        dias_atras: Quantidade de dias para buscar (padrão: 2)
        tipos: Lista de tipos de documento ['out_invoice', 'in_invoice', etc.]
    """
    # Calcular período
    data_fim = datetime.now().date()
    data_ini = data_fim - timedelta(days=dias_atras)
    return _extrair_relatorio_fiscal_impl(data_ini, data_fim, tipos)


def _extrair_relatorio_fiscal_impl(data_ini, data_fim, tipos: list = None):
    """
    Implementação interna da extração do relatório fiscal

    Args:
        data_ini: Data inicial (datetime.date)
        data_fim: Data final (datetime.date)
        tipos: Lista de tipos de documento ['out_invoice', 'in_invoice', etc.]
    """
    print("=" * 80)
    print("RELATÓRIO DE DOCUMENTOS FISCAIS COM IBS/CBS")
    print("(Réplica do Odoo + Campos Reforma Tributária)")
    print("=" * 80)

    # Conectar ao Odoo
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        print("❌ Falha na autenticação com Odoo")
        return None

    print("✅ Conectado ao Odoo")

    print(f"📅 Período: {data_ini.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")

    # Tipos de documento padrão
    if tipos is None:
        tipos = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']

    # Filtro para buscar faturas
    domain = [
        ['invoice_date', '>=', data_ini.isoformat()],
        ['invoice_date', '<=', data_fim.isoformat()],
        ['move_type', 'in', tipos],
        ['state', '=', 'posted']
    ]

    print(f"\n🔍 Buscando faturas...")

    # ========================================================================
    # CAMPOS DO CABEÇALHO (account.move)
    # ========================================================================
    campos_move = [
        'id', 'name', 'journal_id', 'company_id', 'partner_id',
        'invoice_date', 'date', 'move_type', 'state',
        'amount_total', 'amount_untaxed',
        # Campos fiscais brasileiros
        'l10n_br_tipo_pedido', 'l10n_br_tipo_pedido_entrada',
        'l10n_br_tipo_documento', 'l10n_br_numero_nf', 'l10n_br_serie_nf',
        'l10n_br_chave_nf', 'l10n_br_situacao_nf',
        'l10n_br_informacao_fiscal', 'l10n_br_informacao_complementar',
        'l10n_br_pedido_compra', 'l10n_br_total_nfe',
        'l10n_br_carrier_id', 'l10n_br_frete',
        'l10n_br_icms_dest_valor', 'l10n_br_icmsst_valor',
        'l10n_br_operacao_id',
        # Vínculo com sale.order (para obter dados do pedido)
        'invoice_origin',
        # IBS/CBS totais (cabeçalho)
        'l10n_br_ibscbs_base', 'l10n_br_ibs_valor',
        'l10n_br_ibs_uf_valor', 'l10n_br_ibs_mun_valor', 'l10n_br_cbs_valor'
    ]

    # ========================================================================
    # CAMPOS DAS LINHAS (account.move.line)
    # ========================================================================
    campos_line = [
        'id', 'move_id', 'product_id', 'name', 'quantity',
        'price_unit', 'price_subtotal', 'price_total', 'account_id',
        # Produto
        'l10n_br_ncm_id', 'l10n_br_origem',
        'l10n_br_codigo_servico', 'l10n_br_codigo_tributacao_servico',
        'l10n_br_nat_bc_cred',
        # CFOP
        'l10n_br_cfop_id', 'l10n_br_cfop_codigo',
        # Frete item
        'l10n_br_frete',
        # ICMS
        'l10n_br_icms_base', 'l10n_br_icms_aliquota', 'l10n_br_icms_valor', 'l10n_br_icms_cst',
        'l10n_br_icms_dest_valor',
        # ICMS ST
        'l10n_br_icmsst_valor',
        'l10n_br_icmsst_retido_valor', 'l10n_br_icmsst_substituto_valor',
        # IPI
        'l10n_br_ipi_base', 'l10n_br_ipi_aliquota', 'l10n_br_ipi_valor',
        'l10n_br_ipi_valor_isento', 'l10n_br_ipi_valor_outros', 'l10n_br_ipi_cst',
        # ISS
        'l10n_br_iss_aliquota', 'l10n_br_iss_valor',
        # PIS
        'l10n_br_pis_base', 'l10n_br_pis_aliquota', 'l10n_br_pis_valor', 'l10n_br_pis_cst',
        # COFINS
        'l10n_br_cofins_base', 'l10n_br_cofins_aliquota', 'l10n_br_cofins_valor', 'l10n_br_cofins_cst',
        # Retenções
        'l10n_br_pis_ret_aliquota', 'l10n_br_pis_ret_valor',
        'l10n_br_cofins_ret_aliquota', 'l10n_br_cofins_ret_valor',
        'l10n_br_csll_ret_aliquota', 'l10n_br_csll_ret_valor',
        'l10n_br_irpj_ret_aliquota', 'l10n_br_irpj_ret_valor',
        'l10n_br_inss_ret_aliquota', 'l10n_br_inss_ret_valor',
        'l10n_br_iss_ret_aliquota', 'l10n_br_iss_ret_valor',
        # IBS/CBS (NOVOS - Reforma Tributária)
        'l10n_br_ibscbs_cst', 'l10n_br_ibscbs_classtrib_id',
        'l10n_br_ibscbs_base', 'l10n_br_ibscbs_reducao', 'l10n_br_ibscbs_diferido',
        'l10n_br_ibs_uf_aliquota', 'l10n_br_ibs_uf_aliquota_reducao', 'l10n_br_ibs_uf_valor',
        'l10n_br_ibs_mun_aliquota', 'l10n_br_ibs_mun_aliquota_reducao', 'l10n_br_ibs_mun_valor',
        'l10n_br_ibs_valor',
        'l10n_br_cbs_aliquota', 'l10n_br_cbs_aliquota_reducao', 'l10n_br_cbs_valor',
        # Linhas analíticas (para centros de custo)
        'analytic_line_ids',
    ]

    # Buscar cabeçalhos
    moves = odoo.search_read('account.move', domain, campos_move)
    print(f"📄 Encontradas {len(moves)} faturas")

    if not moves:
        print("⚠️ Nenhuma fatura encontrada no período")
        return None

    move_ids = [m['id'] for m in moves]

    print(f"🔍 Buscando linhas das faturas...")

    # Buscar linhas (apenas produtos)
    domain_lines = [
        ['move_id', 'in', move_ids],
        ['display_type', '=', 'product']
    ]
    lines = odoo.search_read('account.move.line', domain_lines, campos_line)
    print(f"📝 Encontradas {len(lines)} linhas de produto")

    # ========================================================================
    # BUSCAR DADOS RELACIONADOS (para exibir nomes em vez de IDs)
    # ========================================================================
    print(f"🔗 Carregando dados relacionados...")

    # Parceiros (clientes/fornecedores)
    partner_ids = list(set(m['partner_id'][0] for m in moves if m.get('partner_id')))
    partners = {}
    if partner_ids:
        partner_data = odoo.search_read(
            'res.partner',
            [['id', 'in', partner_ids]],
            ['id', 'name', 'l10n_br_razao_social', 'l10n_br_cnpj', 'l10n_br_cpf',
             'l10n_br_ie', 'l10n_br_municipio_id', 'state_id', 'country_id']
        )
        partners = {p['id']: p for p in partner_data}

    # Empresas
    company_ids = list(set(m['company_id'][0] for m in moves if m.get('company_id')))
    companies = {}
    if company_ids:
        company_data = odoo.search_read(
            'res.company',
            [['id', 'in', company_ids]],
            ['id', 'name', 'l10n_br_cnpj', 'l10n_br_ie']
        )
        companies = {c['id']: c for c in company_data}

    # Diários
    journal_ids = list(set(m['journal_id'][0] for m in moves if m.get('journal_id')))
    journals = {}
    if journal_ids:
        journal_data = odoo.search_read(
            'account.journal',
            [['id', 'in', journal_ids]],
            ['id', 'name']
        )
        journals = {j['id']: j for j in journal_data}

    # Produtos
    product_ids = list(set(ln['product_id'][0] for ln in lines if ln.get('product_id')))
    products = {}
    if product_ids:
        product_data = odoo.search_read(
            'product.product',
            [['id', 'in', product_ids]],
            ['id', 'default_code', 'name']
        )
        products = {p['id']: p for p in product_data}

    # Contas contábeis
    account_ids = list(set(ln['account_id'][0] for ln in lines if ln.get('account_id')))
    accounts = {}
    if account_ids:
        account_data = odoo.search_read(
            'account.account',
            [['id', 'in', account_ids]],
            ['id', 'code', 'name']
        )
        accounts = {a['id']: f"{a['code']} {a['name']}" for a in account_data}

    # Transportadoras
    carrier_ids = list(set(m['l10n_br_carrier_id'][0] for m in moves if m.get('l10n_br_carrier_id')))
    carriers = {}
    if carrier_ids:
        carrier_data = odoo.search_read(
            'res.partner',
            [['id', 'in', carrier_ids]],
            ['id', 'name', 'l10n_br_cnpj']
        )
        carriers = {c['id']: c for c in carrier_data}

    # Operações fiscais
    operacao_ids = list(set(m['l10n_br_operacao_id'][0] for m in moves if m.get('l10n_br_operacao_id')))
    operacoes = {}
    if operacao_ids:
        operacao_data = odoo.search_read(
            'l10n_br_ciel_it_account.operacao',
            [['id', 'in', operacao_ids]],
            ['id', 'name']
        )
        operacoes = {o['id']: o['name'] for o in operacao_data}

    # NCMs
    ncm_ids = list(set(ln['l10n_br_ncm_id'][0] for ln in lines if ln.get('l10n_br_ncm_id')))
    ncms = {}
    if ncm_ids:
        ncm_data = odoo.search_read(
            'l10n_br_ciel_it_account.ncm',
            [['id', 'in', ncm_ids]],
            ['id', 'codigo_ncm']
        )
        ncms = {n['id']: n['codigo_ncm'] for n in ncm_data}

    # CFOPs
    cfop_ids = list(set(ln['l10n_br_cfop_id'][0] for ln in lines if ln.get('l10n_br_cfop_id')))
    cfops = {}
    if cfop_ids:
        cfop_data = odoo.search_read(
            'l10n_br_ciel_it_account.cfop',
            [['id', 'in', cfop_ids]],
            ['id', 'codigo_cfop']
        )
        cfops = {c['id']: c['codigo_cfop'] for c in cfop_data}

    # Classificação Tributária IBS/CBS (modelo correto)
    classtrib_ids = list(set(ln['l10n_br_ibscbs_classtrib_id'][0] for ln in lines if ln.get('l10n_br_ibscbs_classtrib_id')))
    classtribs = {}
    if classtrib_ids:
        try:
            classtrib_data = odoo.search_read(
                'l10n_br_ciel_it_account.classificacao.tributaria.ibscbs',
                [['id', 'in', classtrib_ids]],
                ['id', 'codigo', 'name']
            )
            # Guardar código e nome separados
            classtribs = {c['id']: {'codigo': c.get('codigo', ''), 'name': c.get('name', '')} for c in classtrib_data}
        except Exception as e:
            print(f"⚠️ Erro ao buscar classificação tributária: {e}")

    # ========================================================================
    # BUSCAR SALE.ORDER (para Número Pedido, Data Pedido, Data Entrega, Representante)
    # ========================================================================
    print(f"🔗 Carregando dados de pedidos de venda...")

    # Coletar todos os invoice_origin únicos (nome do pedido de venda)
    sale_order_names = list(set(
        m['invoice_origin'] for m in moves
        if m.get('invoice_origin') and m.get('move_type') in ['out_invoice', 'out_refund']
    ))

    sale_orders = {}
    sale_users = {}
    if sale_order_names:
        try:
            # Buscar sale.order pelo name
            so_data = odoo.search_read(
                'sale.order',
                [['name', 'in', sale_order_names]],
                ['id', 'name', 'date_order', 'commitment_date', 'user_id']
            )
            sale_orders = {so['name']: so for so in so_data}

            # Buscar nomes dos usuários (representantes)
            user_ids = list(set(so['user_id'][0] for so in so_data if so.get('user_id')))
            if user_ids:
                users_data = odoo.search_read(
                    'res.users',
                    [['id', 'in', user_ids]],
                    ['id', 'name']
                )
                sale_users = {u['id']: u['name'] for u in users_data}
        except Exception as e:
            print(f"⚠️ Erro ao buscar pedidos de venda: {e}")

    # ========================================================================
    # BUSCAR LINHAS ANALÍTICAS (para centros de custo)
    # ========================================================================
    print(f"🔗 Carregando centros de custo analíticos...")

    # Coletar IDs das linhas analíticas
    analytic_line_ids = []
    for ln in lines:
        if ln.get('analytic_line_ids'):
            analytic_line_ids.extend(ln['analytic_line_ids'])
    analytic_line_ids = list(set(analytic_line_ids))

    analytic_lines = {}
    analytic_accounts = {}
    if analytic_line_ids:
        try:
            # Buscar linhas analíticas com os planos customizados
            al_data = odoo.search_read(
                'account.analytic.line',
                [['id', 'in', analytic_line_ids]],
                ['id', 'move_line_id', 'account_id', 'amount',
                 'x_plan5_id', 'x_plan6_id', 'x_plan7_id', 'x_plan16_id', 'x_plan36_id']
            )

            # Indexar por move_line_id
            for al in al_data:
                move_line_id = al['move_line_id'][0] if al.get('move_line_id') else None
                if move_line_id:
                    if move_line_id not in analytic_lines:
                        analytic_lines[move_line_id] = []
                    analytic_lines[move_line_id].append(al)

            # Coletar IDs das contas analíticas para buscar nomes
            acc_ids = set()
            for al in al_data:
                if al.get('account_id'):
                    acc_ids.add(al['account_id'][0])
                for plan in ['x_plan5_id', 'x_plan6_id', 'x_plan7_id', 'x_plan16_id', 'x_plan36_id']:
                    if al.get(plan):
                        acc_ids.add(al[plan][0])

            if acc_ids:
                acc_data = odoo.search_read(
                    'account.analytic.account',
                    [['id', 'in', list(acc_ids)]],
                    ['id', 'name']
                )
                analytic_accounts = {a['id']: a['name'] for a in acc_data}
        except Exception as e:
            print(f"⚠️ Erro ao buscar linhas analíticas: {e}")

    # ========================================================================
    # BUSCAR STOCK.VALUATION.LAYER (para estoque físico/fiscal)
    # ========================================================================
    print(f"🔗 Carregando valores de estoque...")

    stock_valuations = {}
    try:
        # Buscar camadas de valorização vinculadas às faturas
        svl_data = odoo.search_read(
            'stock.valuation.layer',
            [['account_move_id', 'in', move_ids]],
            ['id', 'account_move_id', 'account_move_line_id', 'product_id',
             'quantity', 'value', 'unit_cost', 'remaining_qty', 'remaining_value',
             'price_diff_value']
        )

        # Indexar por account_move_line_id
        for svl in svl_data:
            line_id = svl['account_move_line_id'][0] if svl.get('account_move_line_id') else None
            if line_id:
                stock_valuations[line_id] = svl
    except Exception as e:
        print(f"⚠️ Erro ao buscar valorização de estoque: {e}")

    # ========================================================================
    # MONTAR DATAFRAME COM ESTRUTURA DO ODOO
    # ========================================================================
    print(f"📊 Montando relatório...")

    # Criar índice de moves por ID
    moves_dict = {m['id']: m for m in moves}

    # Montar linhas do relatório
    rows = []
    for line in lines:
        move_id = line['move_id'][0] if line.get('move_id') else None
        move = moves_dict.get(move_id, {})

        # Dados do parceiro
        partner_id = move.get('partner_id', [None])[0] if move.get('partner_id') else None
        partner = partners.get(partner_id, {})

        # Dados da empresa
        company_id = move.get('company_id', [None])[0] if move.get('company_id') else None
        company = companies.get(company_id, {})

        # Dados do diário
        journal_id = move.get('journal_id', [None])[0] if move.get('journal_id') else None
        journal = journals.get(journal_id, {})

        # Dados do produto
        product_id = line.get('product_id', [None])[0] if line.get('product_id') else None
        product = products.get(product_id, {})

        # Dados da transportadora
        carrier_id = move.get('l10n_br_carrier_id', [None])[0] if move.get('l10n_br_carrier_id') else None
        carrier = carriers.get(carrier_id, {})

        # Operação
        operacao_id = move.get('l10n_br_operacao_id', [None])[0] if move.get('l10n_br_operacao_id') else None
        operacao = operacoes.get(operacao_id, '')

        # NCM
        ncm_id = line.get('l10n_br_ncm_id', [None])[0] if line.get('l10n_br_ncm_id') else None
        ncm = ncms.get(ncm_id, '')

        # CFOP
        cfop_id = line.get('l10n_br_cfop_id', [None])[0] if line.get('l10n_br_cfop_id') else None
        cfop = cfops.get(cfop_id, line.get('l10n_br_cfop_codigo', ''))

        # Conta contábil
        account_id = line.get('account_id', [None])[0] if line.get('account_id') else None
        conta = accounts.get(account_id, '')

        # Classificação tributária IBS/CBS (código e nome separados)
        classtrib_id = line.get('l10n_br_ibscbs_classtrib_id', [None])[0] if line.get('l10n_br_ibscbs_classtrib_id') else None
        classtrib_data = classtribs.get(classtrib_id, {})
        classtrib_codigo = classtrib_data.get('codigo', '') if isinstance(classtrib_data, dict) else ''
        classtrib_nome = classtrib_data.get('name', '') if isinstance(classtrib_data, dict) else ''

        # Dados do pedido de venda (sale.order)
        invoice_origin = move.get('invoice_origin', '')
        sale_order = sale_orders.get(invoice_origin, {})
        numero_pedido = sale_order.get('name', '') if sale_order else invoice_origin
        data_pedido = sale_order.get('date_order', '') if sale_order else ''
        # commitment_date pode ser False quando não definido
        commitment = sale_order.get('commitment_date') if sale_order else None
        data_entrega_pedido = commitment if commitment and commitment is not False else ''
        # Representante (user_id do sale.order)
        representante = ''
        if sale_order and sale_order.get('user_id'):
            user_id = sale_order['user_id'][0]
            representante = sale_users.get(user_id, '')

        # Centros de custo analíticos
        line_id = line.get('id')
        line_analytics = analytic_lines.get(line_id, [])

        # Extrair valores de cada plano analítico
        fabrica_conservas = ''
        fabrica_oleo_molho = ''
        aux_producao = ''
        aux_servicos = ''
        adm_mkt = ''
        projeto = ''

        for al in line_analytics:
            # account_id = FABRICA DE CONSERVAS (plano principal)
            if al.get('account_id'):
                acc_id = al['account_id'][0]
                fabrica_conservas = analytic_accounts.get(acc_id, '')
            # x_plan5_id = FABRICA DE OLEO E MOLHOS
            if al.get('x_plan5_id'):
                acc_id = al['x_plan5_id'][0]
                fabrica_oleo_molho = analytic_accounts.get(acc_id, '')
            # x_plan6_id = AUXILIARES DE PRODUCAO
            if al.get('x_plan6_id'):
                acc_id = al['x_plan6_id'][0]
                aux_producao = analytic_accounts.get(acc_id, '')
            # x_plan7_id = AUXILIARES DE SERVICOS
            if al.get('x_plan7_id'):
                acc_id = al['x_plan7_id'][0]
                aux_servicos = analytic_accounts.get(acc_id, '')
            # x_plan16_id = ADM/COM/MKT
            if al.get('x_plan16_id'):
                acc_id = al['x_plan16_id'][0]
                adm_mkt = analytic_accounts.get(acc_id, '')
            # x_plan36_id = Projects (Projetos)
            if al.get('x_plan36_id'):
                acc_id = al['x_plan36_id'][0]
                projeto = analytic_accounts.get(acc_id, '')

        # Valores de estoque (stock.valuation.layer)
        svl = stock_valuations.get(line_id, {})
        valor_estoque_fisico = svl.get('value', 0) if svl else 0
        # O valor fiscal seria o mesmo value, mas com ajustes contábeis
        valor_estoque_fiscal = valor_estoque_fisico  # Simplificado
        variacao_fisico_fiscal = svl.get('price_diff_value', 0) if svl else 0

        # Estado do parceiro
        state_name = ''
        if partner.get('state_id'):
            state_name = partner['state_id'][1] if isinstance(partner['state_id'], list) else ''

        # País do parceiro
        country_name = ''
        if partner.get('country_id'):
            country_name = partner['country_id'][1] if isinstance(partner['country_id'], list) else ''

        # Mapeamento do tipo de documento
        tipo_map = {
            'out_invoice': 'Customer Invoice',
            'out_refund': 'Customer Credit Note',
            'in_invoice': 'Vendor Bill',
            'in_refund': 'Vendor Credit Note'
        }

        # Transportadora formatada
        transp_str = ''
        if carrier:
            cnpj = carrier.get('l10n_br_cnpj', '')
            nome = carrier.get('name', '')
            transp_str = f"({cnpj}) {nome}" if cnpj else nome

        row = {
            # ============ COLUNAS ORIGINAIS DO ODOO (98 colunas) ============
            'Fatura': move.get('name', ''),
            'Diário': journal.get('name', ''),
            'Nome Empresa': company.get('name', ''),
            'CNPJ Empresa': company.get('l10n_br_cnpj', ''),
            'I.E. Empresa': company.get('l10n_br_ie', ''),
            'Tipo de Pedido (saída)': move.get('l10n_br_tipo_pedido', ''),
            'Tipo de Pedido (entrada)': move.get('l10n_br_tipo_pedido_entrada', ''),
            'Tipo Documento Fiscal': move.get('l10n_br_tipo_documento', ''),
            'Número NF': move.get('l10n_br_numero_nf', ''),
            'Série NF': move.get('l10n_br_serie_nf', ''),
            'Chave NF': move.get('l10n_br_chave_nf', ''),
            'Tipo': tipo_map.get(move.get('move_type', ''), move.get('move_type', '')),
            'Status': move.get('state', ''),
            'Situação': move.get('l10n_br_situacao_nf', ''),
            'Informação Fiscal': move.get('l10n_br_informacao_fiscal', ''),
            'Informação Complementar': move.get('l10n_br_informacao_complementar', ''),
            'Número Pedido': numero_pedido,
            'Data Pedido': data_pedido,
            'Data Entrega Pedido': data_entrega_pedido,
            'Nome Cliente/Fornecedor': partner.get('name', ''),
            'Razão Social Cliente/Fornecedor': partner.get('l10n_br_razao_social', ''),
            'CNPJ Cliente/Fornecedor': partner.get('l10n_br_cnpj', ''),
            'CPF Cliente/Fornecedor': partner.get('l10n_br_cpf', ''),
            'I.E. Cliente/Fornecedor': partner.get('l10n_br_ie', ''),
            'Cidade Cliente/Fornecedor': (partner.get('l10n_br_municipio_id', [None, ''])[1].split('(')[0].strip() if partner.get('l10n_br_municipio_id') and isinstance(partner.get('l10n_br_municipio_id'), (list, tuple)) and len(partner.get('l10n_br_municipio_id')) > 1 else ''),
            'Estado Cliente/Fornecedor': state_name,
            'País Cliente/Fornecedor': country_name,
            'Data Emissão NF': move.get('invoice_date', ''),
            'Data de Lançamento NF': move.get('date', ''),
            'Valor NF': move.get('l10n_br_total_nfe', 0) or move.get('amount_total', 0),
            'Representante': representante,
            'Transportadora': transp_str,
            'Valor Frete': move.get('l10n_br_frete', 0),
            'Total R$ ICMS DIFAL': move.get('l10n_br_icms_dest_valor', 0),
            'Total R$ ICMS ST': move.get('l10n_br_icmsst_valor', 0),
            'Operação': operacao,
            'Código Item': product.get('default_code', ''),
            'Nome Item': product.get('name', '') or line.get('name', ''),
            'NCM': ncm,
            'Origem': line.get('l10n_br_origem', ''),
            'Código Serviço': line.get('l10n_br_codigo_servico', ''),
            'Código Tributação Serviço': line.get('l10n_br_codigo_tributacao_servico', ''),
            'Natureza da Base de Cálculo dos Créditos': line.get('l10n_br_nat_bc_cred', ''),
            'Quantidade': line.get('quantity', 0),
            'Valor Unitário': line.get('price_unit', 0),
            'Valor Total Produto': line.get('price_subtotal', 0),
            'Valor Total': line.get('price_total', 0),
            'CFOP': cfop,
            'Valor Frete Item': line.get('l10n_br_frete', 0),
            'Base ICMS': line.get('l10n_br_icms_base', 0),
            '% ICMS': line.get('l10n_br_icms_aliquota', 0),
            'R$ ICMS': line.get('l10n_br_icms_valor', 0),
            'CST ICMS': line.get('l10n_br_icms_cst', ''),
            'R$ ICMS DIFAL': line.get('l10n_br_icms_dest_valor', 0),
            'R$ ICMS ST': line.get('l10n_br_icmsst_valor', 0),
            'CST ICMS ST': '',  # Campo não existe separadamente
            'R$ ICMS ST Ret.': line.get('l10n_br_icmsst_retido_valor', 0),
            'R$ ICMS ST Sub.': line.get('l10n_br_icmsst_substituto_valor', 0),
            'Base IPI': line.get('l10n_br_ipi_base', 0),
            '% IPI': line.get('l10n_br_ipi_aliquota', 0),
            'R$ IPI': line.get('l10n_br_ipi_valor', 0),
            'R$ IPI Isento': line.get('l10n_br_ipi_valor_isento', 0),
            'R$ IPI Outros': line.get('l10n_br_ipi_valor_outros', 0),
            'CST IPI': line.get('l10n_br_ipi_cst', ''),
            '% ISS': line.get('l10n_br_iss_aliquota', 0),
            'R$ ISS': line.get('l10n_br_iss_valor', 0),
            'Base PIS': line.get('l10n_br_pis_base', 0),
            '% PIS': line.get('l10n_br_pis_aliquota', 0),
            'R$ PIS': line.get('l10n_br_pis_valor', 0),
            'CST PIS': line.get('l10n_br_pis_cst', ''),
            'Base COFINS': line.get('l10n_br_cofins_base', 0),
            '% COFINS': line.get('l10n_br_cofins_aliquota', 0),
            'R$ COFINS': line.get('l10n_br_cofins_valor', 0),
            'CST COFINS': line.get('l10n_br_cofins_cst', ''),
            '% PIS Ret.': line.get('l10n_br_pis_ret_aliquota', 0),
            'R$ PIS Ret.': line.get('l10n_br_pis_ret_valor', 0),
            '% COFINS Ret.': line.get('l10n_br_cofins_ret_aliquota', 0),
            'R$ COFINS Ret.': line.get('l10n_br_cofins_ret_valor', 0),
            '% CSLL Ret.': line.get('l10n_br_csll_ret_aliquota', 0),
            'R$ CSLL Ret.': line.get('l10n_br_csll_ret_valor', 0),
            '% IRPJ Ret.': line.get('l10n_br_irpj_ret_aliquota', 0),
            'R$ IRPJ Ret.': line.get('l10n_br_irpj_ret_valor', 0),
            '% INSS Ret.': line.get('l10n_br_inss_ret_aliquota', 0),
            'R$ INSS Ret.': line.get('l10n_br_inss_ret_valor', 0),
            '% ISS Ret.': line.get('l10n_br_iss_ret_aliquota', 0),
            'R$ ISS Ret.': line.get('l10n_br_iss_ret_valor', 0),
            'Valor NF (Sem Retenções)': line.get('price_total', 0),  # Simplificado
            'Município do Serviço': '',  # Campo não mapeado diretamente
            'Conta Contábil': conta,

            # ============ ESTOQUE (Físico/Fiscal) ============
            'Valor Estoque Físico': valor_estoque_fisico,
            'Valor Estoque Fiscal': valor_estoque_fiscal,
            'Variação Físico/Fiscal?': 'Sim' if variacao_fisico_fiscal != 0 else '',

            # ============ CENTROS DE CUSTO ANALÍTICOS ============
            'FABRICA DE CONSERVAS': fabrica_conservas,
            'FABRICA DE OLEO E MOLHO': fabrica_oleo_molho,
            'AUXILIARES DE PRODUÇÃO': aux_producao,
            'AUXILIARES DE SERVIÇOS': aux_servicos,
            'ADM/MKT': adm_mkt,
            'Projeto': projeto,

            # ============ NOVOS CAMPOS IBS/CBS (Reforma Tributária) ============
            'CST IBS/CBS': line.get('l10n_br_ibscbs_cst', ''),
            'Código Class. Trib. IBS/CBS': classtrib_codigo,
            'Nome Class. Trib. IBS/CBS': classtrib_nome,
            'Base IBS/CBS': line.get('l10n_br_ibscbs_base', 0),
            '% Redução IBS/CBS': line.get('l10n_br_ibscbs_reducao', 0),
            '% Diferimento IBS/CBS': line.get('l10n_br_ibscbs_diferido', 0),
            '% IBS UF': line.get('l10n_br_ibs_uf_aliquota', 0),
            '% IBS UF Reduzida': line.get('l10n_br_ibs_uf_aliquota_reducao', 0),
            'R$ IBS UF': line.get('l10n_br_ibs_uf_valor', 0),
            '% IBS Município': line.get('l10n_br_ibs_mun_aliquota', 0),
            '% IBS Mun Reduzida': line.get('l10n_br_ibs_mun_aliquota_reducao', 0),
            'R$ IBS Município': line.get('l10n_br_ibs_mun_valor', 0),
            'R$ IBS Total': line.get('l10n_br_ibs_valor', 0),
            '% CBS': line.get('l10n_br_cbs_aliquota', 0),
            '% CBS Reduzida': line.get('l10n_br_cbs_aliquota_reducao', 0),
            'R$ CBS': line.get('l10n_br_cbs_valor', 0),
        }
        rows.append(row)

    # Criar DataFrame
    df = pd.DataFrame(rows)

    # ========================================================================
    # GERAR ARQUIVO EXCEL
    # ========================================================================
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Usar caminho absoluto baseado na raiz do projeto (não relativo ao cwd)
    project_root = Path(__file__).parent.parent
    output_dir = project_root / 'exports'
    output_dir.mkdir(exist_ok=True)

    filename = output_dir / f'relatorio_fiscal_ibscbs_{timestamp}.xlsx'

    print(f"\n💾 Gerando arquivo Excel...")

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Aba principal: Documentos Fiscais (idêntica ao Odoo + IBS/CBS)
        df.to_excel(writer, sheet_name='Documentos Fiscais', index=False)

        # Aba: Resumo por CFOP (idêntica ao Odoo + IBS/CBS)
        resumo_cfop = df.groupby('CFOP').agg({
            'R$ ICMS': 'sum',
            'R$ ICMS DIFAL': 'sum',
            'R$ ICMS ST': 'sum',
            'R$ ICMS ST Ret.': 'sum',
            'R$ ICMS ST Sub.': 'sum',
            'R$ IPI': 'sum',
            'R$ ISS': 'sum',
            'R$ PIS': 'sum',
            'R$ COFINS': 'sum',
            'R$ PIS Ret.': 'sum',
            'R$ COFINS Ret.': 'sum',
            'R$ CSLL Ret.': 'sum',
            'R$ IRPJ Ret.': 'sum',
            'R$ INSS Ret.': 'sum',
            'R$ ISS Ret.': 'sum',
            # IBS/CBS
            'R$ IBS UF': 'sum',
            'R$ IBS Município': 'sum',
            'R$ IBS Total': 'sum',
            'R$ CBS': 'sum',
        }).reset_index()
        resumo_cfop.to_excel(writer, sheet_name='Resumo por CFOP', index=False)

        # Aba: Resumo IBS/CBS
        resumo_ibscbs = df.groupby('Fatura').agg({
            'Valor NF': 'first',
            'Base IBS/CBS': 'sum',
            'R$ IBS UF': 'sum',
            'R$ IBS Município': 'sum',
            'R$ IBS Total': 'sum',
            'R$ CBS': 'sum',
        }).reset_index()
        resumo_ibscbs.to_excel(writer, sheet_name='Resumo IBS-CBS', index=False)

    print(f"✅ Arquivo gerado: {filename}")

    # Estatísticas
    n_cols_original = 89  # Colunas do Odoo original
    n_cols_ibscbs = 12   # Colunas novas IBS/CBS
    print(f"\n📊 Resumo do relatório:")
    print(f"   - Faturas: {len(moves)}")
    print(f"   - Linhas: {len(lines)}")
    print(f"   - Colunas originais Odoo: {n_cols_original}")
    print(f"   - Colunas IBS/CBS (novas): {n_cols_ibscbs}")
    print(f"   - Total de colunas: {len(df.columns)}")

    # Totais IBS/CBS
    print(f"\n📈 Totais IBS/CBS do período:")
    print(f"   Base IBS/CBS:   R$ {df['Base IBS/CBS'].sum():>15,.2f}")
    print(f"   IBS UF:         R$ {df['R$ IBS UF'].sum():>15,.2f}")
    print(f"   IBS Município:  R$ {df['R$ IBS Município'].sum():>15,.2f}")
    print(f"   IBS Total:      R$ {df['R$ IBS Total'].sum():>15,.2f}")
    print(f"   CBS:            R$ {df['R$ CBS'].sum():>15,.2f}")

    return filename


def main():
    """Função principal"""
    import argparse

    parser = argparse.ArgumentParser(description='Relatório Fiscal com IBS/CBS (Réplica Odoo)')
    parser.add_argument('--dias', type=int, default=2, help='Dias para buscar (padrão: 2)')
    parser.add_argument('--saidas', action='store_true', help='Incluir apenas saídas (vendas)')
    parser.add_argument('--entradas', action='store_true', help='Incluir apenas entradas (compras)')

    args = parser.parse_args()

    # Definir tipos de documento
    tipos = None
    if args.saidas:
        tipos = ['out_invoice', 'out_refund']
    elif args.entradas:
        tipos = ['in_invoice', 'in_refund']

    # Executar extração
    arquivo = extrair_relatorio_fiscal(dias_atras=args.dias, tipos=tipos)

    if arquivo:
        print(f"\n🎉 Relatório gerado com sucesso!")
        print(f"   Arquivo: {arquivo}")


if __name__ == '__main__':
    main()
