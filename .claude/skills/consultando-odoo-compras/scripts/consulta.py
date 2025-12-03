#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consulta Compras - Pedidos de Compra no Odoo

Skill: consultando-odoo-compras
Modelos: purchase.order, purchase.order.line
"""

import argparse
import json
import sys
import os
from datetime import date

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from typing import Dict, Any, List


# ==============================================================================
# CONFIGURACAO DOS MODELOS
# ==============================================================================

MODELO_CONFIG = {
    'compras': {
        'modelo': 'purchase.order',
        'modelo_linha': 'purchase.order.line',
        'campos_principais': [
            'id',
            'name',                      # Numero PO (ex: PO00123)
            'partner_ref',               # Referencia do fornecedor
            'origin',                    # Documento origem (ex: SO0001)
            'state',                     # Status (draft, purchase, done, cancel)
            'invoice_status',            # Status faturamento
            'receipt_status',            # Status recebimento
            'partner_id',                # Fornecedor
            'date_order',                # Data do pedido
            'date_planned',              # Data prevista entrega
            'date_approve',              # Data aprovacao
            'effective_date',            # Data efetiva entrega
            'amount_untaxed',            # Valor sem impostos
            'amount_tax',                # Total impostos
            'amount_total',              # Valor total
            'currency_id',               # Moeda
            'company_id',                # Empresa
            'user_id',                   # Comprador responsavel
            'notes',                     # Observacoes
        ],
        'campos_fiscais': [
            # Totais fiscais brasileiros
            'l10n_br_total_nfe',         # Total NF-e
            'l10n_br_prod_valor',        # Total produtos
            'l10n_br_frete',             # Total frete
            'l10n_br_seguro',            # Total seguro
            'l10n_br_desc_valor',        # Total desconto
            'l10n_br_despesas_acessorias', # Despesas acessorias
            'l10n_br_total_tributos',    # Total tributos
            # Impostos
            'l10n_br_icms_valor',        # Total ICMS
            'l10n_br_icmsst_valor',      # Total ICMS-ST
            'l10n_br_ipi_valor',         # Total IPI
            'l10n_br_pis_valor',         # Total PIS
            'l10n_br_cofins_valor',      # Total COFINS
            # Retencoes
            'l10n_br_pis_ret_valor',     # PIS Retido
            'l10n_br_cofins_ret_valor',  # COFINS Retido
            'l10n_br_csll_ret_valor',    # CSLL Retido
            'l10n_br_irpj_ret_valor',    # IRPJ Retido
            'l10n_br_inss_ret_valor',    # INSS Retido
            # Configuracoes
            'l10n_br_cfop_id',           # CFOP padrao
            'l10n_br_tipo_pedido',       # Tipo do pedido
            'l10n_br_compra_indcom',     # Destinacao de uso
            'l10n_br_informacao_complementar',  # Info complementar
            'l10n_br_informacao_fiscal', # Info fiscal
        ],
        'campos_linha': [
            'id',
            'name',                      # Descricao
            'order_id',                  # PO pai
            'product_id',                # Produto
            'product_qty',               # Quantidade pedida
            'qty_received',              # Quantidade recebida
            'qty_invoiced',              # Quantidade faturada
            'price_unit',                # Preco unitario
            'price_subtotal',            # Subtotal
            'price_total',               # Total com impostos
            'date_planned',              # Data prevista
            'state',                     # Status
        ],
        'campos_linha_fiscais': [
            'l10n_br_cfop_id',           # CFOP
            'l10n_br_cfop_codigo',       # Codigo CFOP
            'l10n_br_prod_valor',        # Valor produto
            'l10n_br_total_nfe',         # Valor total item
            'l10n_br_frete',             # Frete
            'l10n_br_seguro',            # Seguro
            'l10n_br_desc_valor',        # Desconto
            # ICMS
            'l10n_br_icms_cst',          # CST ICMS
            'l10n_br_icms_base',         # Base ICMS
            'l10n_br_icms_aliquota',     # Aliquota ICMS
            'l10n_br_icms_valor',        # Valor ICMS
            # IPI
            'l10n_br_ipi_cst',           # CST IPI
            'l10n_br_ipi_base',          # Base IPI
            'l10n_br_ipi_aliquota',      # Aliquota IPI
            'l10n_br_ipi_valor',         # Valor IPI
            # PIS/COFINS
            'l10n_br_pis_cst',           # CST PIS
            'l10n_br_pis_valor',         # Valor PIS
            'l10n_br_cofins_cst',        # CST COFINS
            'l10n_br_cofins_valor',      # Valor COFINS
            # NCM (campo customizado)
            'x_studio_related_field_4ep_1if0glmph',  # NCM
        ],
    }
}


# ==============================================================================
# FUNCOES AUXILIARES
# ==============================================================================

def get_odoo_connection():
    """Obtem conexao com Odoo usando integracao existente."""
    from app.odoo.utils.connection import get_odoo_connection as get_conn
    return get_conn()


def extrair_nome_many2one(valor):
    """Extrai nome de um campo many2one (retorna tupla [id, nome])."""
    if valor and isinstance(valor, (list, tuple)) and len(valor) > 1:
        return valor[1]
    return valor if isinstance(valor, str) else ''


def formatar_valor(valor):
    """Formata valor monetario."""
    if valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def traduzir_state(state):
    """Traduz state para portugues."""
    estados = {
        'draft': 'Rascunho',
        'sent': 'Cotacao Enviada',
        'to approve': 'Aguardando Aprovacao',
        'purchase': 'Pedido Confirmado',
        'done': 'Concluido',
        'cancel': 'Cancelado',
    }
    return estados.get(state, state or 'N/A')


def traduzir_invoice_status(status):
    """Traduz invoice_status para portugues."""
    estados = {
        'no': 'Nada a Faturar',
        'to invoice': 'Aguardando Faturamento',
        'invoiced': 'Faturado',
    }
    return estados.get(status, status or 'N/A')


def traduzir_receipt_status(status):
    """Traduz receipt_status para portugues."""
    estados = {
        'pending': 'Aguardando',
        'partial': 'Parcial',
        'full': 'Recebido',
    }
    return estados.get(status, status or 'N/A')


# ==============================================================================
# FUNCAO PRINCIPAL DE CONSULTA
# ==============================================================================

def consultar_compras(args) -> Dict[str, Any]:
    """Consulta pedidos de compra no Odoo."""
    resultado = {
        'sucesso': False,
        'tipo': 'compras',
        'subtipo': args.subtipo,
        'total': 0,
        'pedidos': [],
        'resumo': {},
        'erro': None
    }

    try:
        odoo = get_odoo_connection()
        config = MODELO_CONFIG['compras']

        # Montar filtros base
        filtros = []

        # Filtrar por subtipo
        if args.subtipo == 'pendentes':
            filtros.append(('state', 'in', ['draft', 'sent', 'to approve']))
        elif args.subtipo == 'confirmados':
            filtros.append(('state', '=', 'purchase'))
        elif args.subtipo == 'recebidos':
            filtros.append(('state', '=', 'done'))
        elif args.subtipo == 'a-faturar':
            filtros.append(('invoice_status', '=', 'to invoice'))
        elif args.subtipo == 'cancelados':
            filtros.append(('state', '=', 'cancel'))
        # 'todos' nao adiciona filtro

        # Filtrar por fornecedor (nome)
        if args.fornecedor:
            filtros.append(('partner_id.name', 'ilike', args.fornecedor))

        # Filtrar por CNPJ
        if args.cnpj:
            cnpj_limpo = args.cnpj.replace('.', '').replace('/', '').replace('-', '')
            filtros.append(('partner_id.vat', 'ilike', cnpj_limpo))

        # Filtrar por numero PO
        if getattr(args, 'numero_po', None):
            filtros.append(('name', 'ilike', args.numero_po))

        # Filtrar por data
        if args.data_inicio:
            filtros.append(('date_order', '>=', args.data_inicio))
        if args.data_fim:
            filtros.append(('date_order', '<=', args.data_fim + ' 23:59:59'))

        # Filtrar por valor minimo
        if getattr(args, 'valor_min', None):
            filtros.append(('amount_total', '>=', args.valor_min))

        # Filtrar por valor maximo
        if getattr(args, 'valor_max', None):
            filtros.append(('amount_total', '<=', args.valor_max))

        # Filtrar por origem
        if getattr(args, 'origem', None):
            filtros.append(('origin', 'ilike', args.origem))

        # Montar lista de campos a buscar
        campos_busca = list(config['campos_principais'])

        # Incluir campos fiscais se solicitado
        if getattr(args, 'fiscais', False):
            campos_busca.extend(config['campos_fiscais'])

        # Executar busca
        pedidos = odoo.search_read(
            config['modelo'],
            filtros,
            fields=campos_busca,
            limit=args.limit or 100
        )

        # Montar campos de linha a buscar
        campos_linha_busca = list(config['campos_linha'])
        if getattr(args, 'fiscais', False):
            campos_linha_busca.extend(config['campos_linha_fiscais'])

        # Verificar se precisa filtrar por produto
        filtrar_produto = getattr(args, 'produto', None)

        if filtrar_produto or getattr(args, 'detalhes', False):
            pedidos_filtrados = []
            for pedido in pedidos:
                linhas = odoo.search_read(
                    config['modelo_linha'],
                    [('order_id', '=', pedido['id'])],
                    fields=campos_linha_busca,
                    limit=200
                )

                # Filtrar por produto se especificado
                if filtrar_produto:
                    termo = filtrar_produto.lower()
                    linhas_match = [
                        linha for linha in linhas
                        if termo in (linha.get('name') or '').lower() or
                           termo in extrair_nome_many2one(linha.get('product_id')).lower()
                    ]
                    if not linhas_match:
                        continue  # Pular pedido se nenhuma linha combina
                    linhas = linhas_match

                pedido['linhas'] = linhas
                pedido['qtd_produtos'] = len(linhas)
                pedidos_filtrados.append(pedido)

            pedidos = pedidos_filtrados

        # Calcular resumo se solicitado
        if getattr(args, 'resumo', False):
            total_pedidos = len(pedidos)
            valor_total = sum(pedido.get('amount_total', 0) or 0 for pedido in pedidos)
            valor_impostos = sum(pedido.get('amount_tax', 0) or 0 for pedido in pedidos)
            valor_liquido = sum(pedido.get('amount_untaxed', 0) or 0 for pedido in pedidos)

            # Contar por status
            por_status = {}
            for pedido in pedidos:
                st = pedido.get('state', 'N/A')
                por_status[st] = por_status.get(st, 0) + 1

            resultado['resumo'] = {
                'total_pedidos': total_pedidos,
                'valor_total': valor_total,
                'valor_impostos': valor_impostos,
                'valor_liquido': valor_liquido,
                'por_status': por_status,
            }

        resultado['sucesso'] = True
        resultado['total'] = len(pedidos)
        resultado['pedidos'] = pedidos

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Consulta pedidos de compra no Odoo (purchase.order)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Pedidos pendentes de aprovacao
  python consulta.py --tipo compras --subtipo pendentes

  # Pedidos de um fornecedor
  python consulta.py --tipo compras --fornecedor "vale sul"

  # Pedidos confirmados aguardando recebimento
  python consulta.py --tipo compras --subtipo confirmados

  # Pedidos pendentes de faturamento
  python consulta.py --tipo compras --subtipo a-faturar

  # Buscar por periodo
  python consulta.py --tipo compras --data-inicio 2025-11-01 --data-fim 2025-11-30

  # Buscar PO especifico com detalhes
  python consulta.py --tipo compras --numero-po "PO00123" --detalhes

  # Buscar por produto
  python consulta.py --tipo compras --produto "pupunha" --detalhes

  # Resumo de compras do periodo
  python consulta.py --tipo compras --data-inicio 2025-11-01 --resumo
        """
    )

    # Argumentos obrigatorios
    parser.add_argument('--tipo', required=True, choices=['compras'],
                        help='Tipo de consulta')

    # Subtipos
    parser.add_argument('--subtipo', default='todos',
                        choices=['pendentes', 'confirmados', 'recebidos', 'a-faturar', 'cancelados', 'todos'],
                        help='Subtipo: pendentes, confirmados, recebidos, a-faturar, cancelados, todos')

    # Filtros basicos
    parser.add_argument('--fornecedor', help='Nome do fornecedor (busca parcial)')
    parser.add_argument('--cnpj', help='CNPJ do fornecedor (busca parcial)')
    parser.add_argument('--numero-po', help='Numero do PO (busca parcial)')
    parser.add_argument('--data-inicio', help='Data inicial (YYYY-MM-DD)')
    parser.add_argument('--data-fim', help='Data final (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=100, help='Limite de resultados')

    # Filtros avancados
    parser.add_argument('--valor-min', type=float, help='Valor minimo do PO')
    parser.add_argument('--valor-max', type=float, help='Valor maximo do PO')
    parser.add_argument('--produto', help='Nome do produto (busca nas linhas)')
    parser.add_argument('--origem', help='Documento de origem (ex: SO0001)')

    # Opcoes de saida
    parser.add_argument('--detalhes', action='store_true',
                        help='Incluir linhas/produtos')
    parser.add_argument('--fiscais', action='store_true',
                        help='Incluir campos fiscais/tributarios')
    parser.add_argument('--resumo', action='store_true',
                        help='Mostrar apenas totalizadores')
    parser.add_argument('--json', action='store_true', help='Saida em JSON')

    args = parser.parse_args()

    # Executar consulta
    resultado = consultar_compras(args)

    # Formatar saida
    if args.json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
    else:
        if resultado['sucesso']:
            subtipo_nome = {
                'pendentes': 'PENDENTES',
                'confirmados': 'CONFIRMADOS',
                'recebidos': 'RECEBIDOS',
                'a-faturar': 'AGUARDANDO FATURAMENTO',
                'cancelados': 'CANCELADOS',
                'todos': 'TODOS'
            }.get(args.subtipo, args.subtipo.upper())

            print(f"\n=== PEDIDOS DE COMPRA - {subtipo_nome} ===")
            print(f"Total encontrado: {resultado['total']}")

            # Mostrar resumo se solicitado
            if args.resumo and resultado['resumo']:
                r = resultado['resumo']
                print(f"\n--- RESUMO ---")
                print(f"Pedidos: {r['total_pedidos']}")
                print(f"Valor Total: {formatar_valor(r['valor_total'])}")
                print(f"Valor Impostos: {formatar_valor(r['valor_impostos'])}")
                print(f"Valor Liquido: {formatar_valor(r['valor_liquido'])}")
                print(f"\nPor Status:")
                for st, qtd in r['por_status'].items():
                    print(f"  - {traduzir_state(st)}: {qtd}")
                print()
            else:
                print()

                for pedido in resultado['pedidos'][:20]:
                    nome = pedido.get('name') or 'S/N'
                    fornecedor = extrair_nome_many2one(pedido.get('partner_id'))
                    state = traduzir_state(pedido.get('state'))
                    invoice_status = traduzir_invoice_status(pedido.get('invoice_status'))
                    receipt_status = traduzir_receipt_status(pedido.get('receipt_status'))
                    data_pedido = (pedido.get('date_order') or '')[:10]
                    data_prevista = (pedido.get('date_planned') or '')[:10]
                    valor_total = pedido.get('amount_total') or 0
                    origem = pedido.get('origin') or ''

                    print(f"[{pedido['id']}] {nome}")
                    print(f"  Fornecedor: {fornecedor}")
                    print(f"  Status: {state} | Fatura: {invoice_status} | Receb: {receipt_status}")
                    print(f"  Data Pedido: {data_pedido} | Prevista: {data_prevista}")
                    print(f"  Valor Total: {formatar_valor(valor_total)}")

                    if origem:
                        print(f"  Origem: {origem}")

                    # Campos fiscais se solicitado
                    if getattr(args, 'fiscais', False):
                        icms = pedido.get('l10n_br_icms_valor', 0) or 0
                        ipi = pedido.get('l10n_br_ipi_valor', 0) or 0
                        pis = pedido.get('l10n_br_pis_valor', 0) or 0
                        cofins = pedido.get('l10n_br_cofins_valor', 0) or 0
                        frete = pedido.get('l10n_br_frete', 0) or 0

                        if any([icms, ipi, pis, cofins, frete]):
                            impostos = []
                            if icms: impostos.append(f"ICMS:{formatar_valor(icms)}")
                            if ipi: impostos.append(f"IPI:{formatar_valor(ipi)}")
                            if pis: impostos.append(f"PIS:{formatar_valor(pis)}")
                            if cofins: impostos.append(f"COFINS:{formatar_valor(cofins)}")
                            if frete: impostos.append(f"Frete:{formatar_valor(frete)}")
                            print(f"  Tributos: {', '.join(impostos)}")

                    # Linhas se detalhes solicitado
                    if 'linhas' in pedido and pedido['linhas']:
                        print(f"  Produtos ({len(pedido['linhas'])}):")
                        for linha in pedido['linhas'][:5]:
                            produto = extrair_nome_many2one(linha.get('product_id')) or linha.get('name', 'N/A')
                            qtd = linha.get('product_qty', 0) or 0
                            qtd_rec = linha.get('qty_received', 0) or 0
                            preco = linha.get('price_unit', 0) or 0
                            subtotal = linha.get('price_subtotal', 0) or 0

                            # Info fiscal da linha
                            info_fiscal = ""
                            if getattr(args, 'fiscais', False):
                                cfop = linha.get('l10n_br_cfop_codigo', '')
                                cst_icms = linha.get('l10n_br_icms_cst', '')
                                if cfop or cst_icms:
                                    info_fiscal = f" [CFOP:{cfop} CST:{cst_icms}]"

                            print(f"    - {produto[:40]}: {qtd:,.0f} (rec:{qtd_rec:,.0f}) x {formatar_valor(preco)} = {formatar_valor(subtotal)}{info_fiscal}")

                        if len(pedido['linhas']) > 5:
                            print(f"    ... e mais {len(pedido['linhas']) - 5} produto(s)")

                    print()

                if resultado['total'] > 20:
                    print(f"... e mais {resultado['total'] - 20} pedido(s)")
        else:
            print(f"\nERRO: {resultado['erro']}")


if __name__ == '__main__':
    main()
