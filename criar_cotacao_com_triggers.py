#!/usr/bin/env python3
"""
Script para criar uma cotação no Odoo com triggers/onchange ativados
Data: 2025-01-25
"""

import sys
import os
from datetime import datetime, timedelta

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def criar_cotacao_com_triggers():
    """
    Cria uma cotação no Odoo acionando os triggers/onchange para calcular impostos
    """
    try:
        # Conectar ao Odoo
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        if not odoo:
            logger.error("❌ Não foi possível conectar ao Odoo")
            return None
        
        # Definir a empresa NACOM GOYA - CD (ID: 4)
        company_id = 4  # NACOM GOYA - CD
        warehouse_id = 3  # Armazém CD
        empresa_nome = "NACOM GOYA - CD"
        
        logger.info(f"🏢 Usando empresa: {empresa_nome} (ID: {company_id})")
        logger.info(f"🏭 Usando armazém: CD (ID: {warehouse_id})")
        
        # Dados da cotação
        cnpj_cliente = '75.315.333/0002-90'
        produtos_cotacao = [
            {
                'codigo': '4310162',
                'descricao': 'AZEITONA VERDE CAMPO BELO BALDE',
                'quantidade': 70,
                'preco_unitario': 196.83
            },
            {
                'codigo': '4320147',
                'descricao': 'AZEITONA VERDE CAMPO BELO FAT.POUCH',
                'quantidade': 112,
                'preco_unitario': 79.25
            },
            {
                'codigo': '4320172',
                'descricao': 'AZEITONA VERDE CAMPO BELO FAT.VIDRO',
                'quantidade': 44,
                'preco_unitario': 99.91
            }
        ]
        
        # 1. Buscar cliente pelo CNPJ
        logger.info(f"🔍 Buscando cliente com CNPJ: {cnpj_cliente}")
        cliente = odoo.search_read(
            'res.partner',
            [('l10n_br_cnpj', '=', cnpj_cliente)],
            ['id', 'name', 'l10n_br_razao_social', 'property_account_position_id'],
            limit=1
        )
        
        if not cliente:
            logger.error(f"❌ Cliente com CNPJ {cnpj_cliente} não encontrado")
            # Tentar buscar por CNPJ parcial
            cnpj_limpo = cnpj_cliente.replace('.', '').replace('/', '').replace('-', '')
            cliente = odoo.search_read(
                'res.partner',
                [('l10n_br_cnpj', 'ilike', cnpj_limpo[:8])],
                ['id', 'name', 'l10n_br_cnpj', 'property_account_position_id'],
                limit=1
            )
            
            if not cliente:
                logger.error("❌ Nenhum cliente encontrado")
                return None
        
        partner_id = cliente[0]['id']
        logger.info(f"✅ Cliente encontrado: {cliente[0].get('name', '')} (ID: {partner_id})")
        
        # Posição fiscal do cliente (importante para impostos)
        fiscal_position_id = cliente[0].get('property_account_position_id')
        if fiscal_position_id:
            fiscal_position_id = fiscal_position_id[0] if isinstance(fiscal_position_id, list) else fiscal_position_id
            logger.info(f"   📊 Posição fiscal do cliente: ID {fiscal_position_id}")
        
        # 2. MÉTODO 1: Usar onchange para obter valores calculados
        logger.info("🔄 Executando onchange para obter valores calculados do parceiro...")
        
        # Chamar onchange do partner_id para obter valores padrão
        onchange_result = odoo.execute_kw(
            'sale.order',
            'onchange',
            [[], ['partner_id']],  # IDs vazios, campos a monitorar
            {
                'values': {
                    'partner_id': partner_id,
                    'company_id': company_id
                },
                'field_name': 'partner_id',
                'field_onchange': {
                    'partner_id': '1',
                    'partner_invoice_id': '',
                    'partner_shipping_id': '',
                    'pricelist_id': '',
                    'payment_term_id': '',
                    'fiscal_position_id': ''
                },
                'context': {'company_id': company_id}
            }
        )
        
        # Extrair valores do onchange
        valores_padrao = {}
        if onchange_result and 'value' in onchange_result:
            valores_padrao = onchange_result['value']
            logger.info(f"   ✅ Valores obtidos do onchange: {list(valores_padrao.keys())}")
            
            # Log dos valores importantes
            if 'fiscal_position_id' in valores_padrao:
                logger.info(f"   📊 Posição fiscal calculada: {valores_padrao['fiscal_position_id']}")
            if 'payment_term_id' in valores_padrao:
                logger.info(f"   💳 Condição de pagamento padrão: {valores_padrao['payment_term_id']}")
            if 'pricelist_id' in valores_padrao:
                logger.info(f"   💰 Lista de preços padrão: {valores_padrao['pricelist_id']}")
        
        # 3. Preparar linhas de produtos COM IMPOSTOS
        logger.info("📦 Preparando produtos com cálculo de impostos...")
        order_lines = []
        
        for prod in produtos_cotacao:
            logger.info(f"   🔍 Processando: {prod['codigo']} - {prod['descricao']}")
            
            # Buscar produto
            produto = odoo.execute_kw(
                'product.product',
                'search_read',
                [[('default_code', '=', prod['codigo'])]],
                {'fields': ['id', 'name', 'taxes_id', 'supplier_taxes_id', 'uom_id'], 
                 'limit': 1,
                 'context': {'company_id': company_id}}
            )
            
            if not produto:
                # Tentar por nome
                produto = odoo.execute_kw(
                    'product.product',
                    'search_read',
                    [[('name', 'ilike', prod['descricao'][:20])]],
                    {'fields': ['id', 'name', 'taxes_id', 'supplier_taxes_id', 'uom_id'], 
                     'limit': 1,
                     'context': {'company_id': company_id}}
                )
            
            if produto:
                product_id = produto[0]['id']
                logger.info(f"   ✅ Produto encontrado: {produto[0]['name']} (ID: {product_id})")
                
                # Impostos do produto
                taxes_id = produto[0].get('taxes_id', [])
                if taxes_id:
                    logger.info(f"   💰 Impostos do produto: {taxes_id}")
                
                # MÉTODO 2: Chamar onchange para linha do produto
                logger.info(f"   🔄 Calculando impostos via onchange para produto {product_id}...")
                
                line_onchange = odoo.execute_kw(
                    'sale.order.line',
                    'onchange',
                    [[], ['product_id']],
                    {
                        'values': {
                            'product_id': product_id,
                            'product_uom_qty': prod['quantidade'],
                            'order_id': False  # Ainda não temos o ID da ordem
                        },
                        'field_name': 'product_id',
                        'field_onchange': {
                            'product_id': '1',
                            'name': '',
                            'price_unit': '',
                            'product_uom': '',
                            'tax_id': ''
                        },
                        'context': {
                            'company_id': company_id,
                            'partner_id': partner_id,
                            'quantity': prod['quantidade'],
                            'pricelist': valores_padrao.get('pricelist_id'),
                            'fiscal_position': valores_padrao.get('fiscal_position_id')
                        }
                    }
                )
                
                # Extrair valores da linha
                line_values = {
                    'product_id': product_id,
                    'product_uom_qty': prod['quantidade'],
                    'price_unit': prod['preco_unitario']  # Usar nosso preço
                }
                
                if line_onchange and 'value' in line_onchange:
                    line_data = line_onchange['value']
                    
                    # Pegar nome e UOM do onchange
                    if 'name' in line_data:
                        line_values['name'] = line_data['name']
                    else:
                        line_values['name'] = prod['descricao']
                    
                    if 'product_uom' in line_data:
                        line_values['product_uom'] = line_data['product_uom']
                    elif produto[0].get('uom_id'):
                        line_values['product_uom'] = produto[0]['uom_id'][0]
                    
                    # IMPORTANTE: Pegar os impostos calculados
                    if 'tax_id' in line_data and line_data['tax_id']:
                        # tax_id vem como [(6, 0, [ids])] ou lista direta
                        if isinstance(line_data['tax_id'], list):
                            if line_data['tax_id'] and isinstance(line_data['tax_id'][0], tuple):
                                # Formato (6, 0, [ids])
                                line_values['tax_id'] = line_data['tax_id']
                            else:
                                # Lista direta de IDs
                                line_values['tax_id'] = [(6, 0, line_data['tax_id'])]
                        logger.info(f"   ✅ Impostos calculados: {line_data.get('tax_id')}")
                else:
                    line_values['name'] = prod['descricao']
                    if produto[0].get('uom_id'):
                        line_values['product_uom'] = produto[0]['uom_id'][0]
                    
                    # Se não teve onchange, usar impostos do produto diretamente
                    if taxes_id:
                        line_values['tax_id'] = [(6, 0, taxes_id)]
                
                order_lines.append((0, 0, line_values))
            else:
                logger.warning(f"   ❌ Produto não encontrado: {prod['codigo']}")
                # Adicionar linha manual
                order_lines.append((0, 0, {
                    'name': f"{prod['codigo']} - {prod['descricao']}",
                    'product_uom_qty': prod['quantidade'],
                    'price_unit': prod['preco_unitario'],
                    'product_uom': 1
                }))
        
        # 4. Criar a cotação com todos os valores calculados
        logger.info("📝 Criando cotação com valores calculados e impostos...")
        
        # Montar dados da cotação com valores do onchange
        cotacao_data = {
            'partner_id': partner_id,
            'company_id': company_id,
            'warehouse_id': warehouse_id,
            'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'validity_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'order_line': order_lines,
            'note': f'Cotação com impostos calculados - {empresa_nome}'
        }
        
        # Adicionar valores do onchange do partner
        if valores_padrao:
            if 'partner_invoice_id' in valores_padrao:
                cotacao_data['partner_invoice_id'] = valores_padrao['partner_invoice_id']
            if 'partner_shipping_id' in valores_padrao:
                cotacao_data['partner_shipping_id'] = valores_padrao['partner_shipping_id']
            if 'payment_term_id' in valores_padrao:
                cotacao_data['payment_term_id'] = valores_padrao['payment_term_id']
            if 'pricelist_id' in valores_padrao:
                cotacao_data['pricelist_id'] = valores_padrao['pricelist_id']
            if 'fiscal_position_id' in valores_padrao:
                cotacao_data['fiscal_position_id'] = valores_padrao['fiscal_position_id']
        
        # Criar a cotação
        cotacao_id = odoo.execute_kw(
            'sale.order',
            'create',
            [cotacao_data],
            {'context': {
                'company_id': company_id,
                'allowed_company_ids': [company_id]
            }}
        )
        
        logger.info(f"✅ Cotação criada! ID: {cotacao_id}")
        
        # 5. MÉTODO 3: Forçar recálculo após criação
        logger.info("🔄 Forçando recálculo de impostos e totais...")
        
        # Chamar _compute_tax_id para recalcular impostos
        try:
            odoo.execute_kw(
                'sale.order',
                'button_dummy',  # Método que força recálculo
                [[cotacao_id]],
                {'context': {'company_id': company_id}}
            )
            logger.info("   ✅ Recálculo executado")
        except:
            logger.info("   ℹ️ Método button_dummy não disponível")
        
        # Alternativa: Escrever e ler para forçar recálculo
        try:
            # Fazer um write vazio para acionar computes
            odoo.execute_kw(
                'sale.order',
                'write',
                [[cotacao_id], {}],
                {'context': {'company_id': company_id}}
            )
            logger.info("   ✅ Write vazio para forçar computes")
        except:
            pass
        
        # 6. Buscar cotação atualizada
        cotacao = odoo.search_read(
            'sale.order',
            [('id', '=', cotacao_id)],
            ['name', 'state', 'amount_untaxed', 'amount_tax', 'amount_total', 
             'fiscal_position_id', 'company_id']
        )
        
        if cotacao:
            logger.info("\n" + "="*60)
            logger.info("📊 RESUMO DA COTAÇÃO COM IMPOSTOS:")
            logger.info("="*60)
            logger.info(f"   🏢 EMPRESA: {cotacao[0]['company_id'][1] if cotacao[0].get('company_id') else 'N/A'}")
            logger.info(f"   📋 Número: {cotacao[0]['name']}")
            logger.info(f"   👤 Cliente: {cliente[0].get('name', '')}")
            logger.info(f"   📊 Posição Fiscal: {cotacao[0]['fiscal_position_id'][1] if cotacao[0].get('fiscal_position_id') else 'Não definida'}")
            logger.info(f"   🏷️ Status: {cotacao[0]['state']}")
            logger.info(f"   💰 Subtotal: R$ {cotacao[0]['amount_untaxed']:,.2f}")
            logger.info(f"   💰 IMPOSTOS: R$ {cotacao[0]['amount_tax']:,.2f}")
            logger.info(f"   💰 TOTAL: R$ {cotacao[0]['amount_total']:,.2f}")
            logger.info("="*60)
            
            # Buscar linhas com impostos
            linhas = odoo.search_read(
                'sale.order.line',
                [('order_id', '=', cotacao_id)],
                ['name', 'product_uom_qty', 'price_unit', 'price_subtotal', 
                 'price_tax', 'price_total', 'tax_id']
            )
            
            if linhas:
                logger.info("\n   📦 PRODUTOS COM IMPOSTOS:")
                logger.info("   " + "-"*50)
                for linha in linhas:
                    logger.info(f"   • {linha['name']}")
                    logger.info(f"     Qtd: {linha['product_uom_qty']} x R$ {linha['price_unit']:,.2f}")
                    logger.info(f"     Subtotal: R$ {linha['price_subtotal']:,.2f}")
                    
                    if linha.get('tax_id'):
                        # Buscar detalhes dos impostos
                        impostos = odoo.search_read(
                            'account.tax',
                            [('id', 'in', linha['tax_id'])],
                            ['name', 'amount']
                        )
                        if impostos:
                            nomes_impostos = [f"{t['name']} ({t['amount']}%)" for t in impostos]
                            logger.info(f"     Impostos: {', '.join(nomes_impostos)}")
                            logger.info(f"     Valor Impostos: R$ {linha.get('price_tax', 0):,.2f}")
                    
                    logger.info(f"     Total c/ Impostos: R$ {linha.get('price_total', linha['price_subtotal']):,.2f}")
                    logger.info("   " + "-"*50)
        
        return cotacao_id
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar cotação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("🚀 Iniciando criação de cotação com triggers/impostos...")
    logger.info("="*60)
    
    cotacao_id = criar_cotacao_com_triggers()
    
    if cotacao_id:
        logger.info(f"\n✅ SUCESSO! Cotação criada com impostos calculados!")
        logger.info(f"🆔 ID: {cotacao_id}")
        logger.info("💡 Os impostos foram calculados usando onchange do Odoo")
    else:
        logger.error("\n❌ Falha ao criar cotação")