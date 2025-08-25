#!/usr/bin/env python3
"""
Script para criar uma cotação no Odoo com impostos calculados corretamente
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

def criar_cotacao_com_impostos():
    """
    Cria uma cotação no Odoo com impostos calculados corretamente
    usando a posição fiscal do cliente
    """
    try:
        # Conectar ao Odoo
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        if not odoo:
            logger.error("❌ Não foi possível conectar ao Odoo")
            return None
        
        # Definir a empresa NACOM GOYA - CD
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
        
        # 1. Buscar cliente com dados fiscais completos
        logger.info(f"🔍 Buscando cliente com CNPJ: {cnpj_cliente}")
        cliente = odoo.search_read(
            'res.partner',
            [('l10n_br_cnpj', '=', cnpj_cliente)],
            ['id', 'name', 'l10n_br_razao_social', 
             'property_account_position_id',  # Posição fiscal
             'property_product_pricelist',     # Lista de preços
             'property_payment_term_id',       # Condição de pagamento
             'property_supplier_payment_term_id',
             'user_id',                        # Vendedor
             'team_id'                         # Equipe
            ],
            limit=1
        )
        
        if not cliente:
            # Tentar buscar por CNPJ parcial
            cnpj_limpo = cnpj_cliente.replace('.', '').replace('/', '').replace('-', '')
            cliente = odoo.search_read(
                'res.partner',
                [('l10n_br_cnpj', 'ilike', cnpj_limpo[:8])],
                ['id', 'name', 'l10n_br_cnpj', 
                 'property_account_position_id',
                 'property_product_pricelist',
                 'property_payment_term_id'],
                limit=1
            )
            
            if not cliente:
                logger.error("❌ Nenhum cliente encontrado")
                return None
        
        partner_id = cliente[0]['id']
        logger.info(f"✅ Cliente encontrado: {cliente[0].get('name', '')} (ID: {partner_id})")
        
        # Extrair dados fiscais do cliente
        fiscal_position_id = None
        pricelist_id = None
        payment_term_id = None
        
        if cliente[0].get('property_account_position_id'):
            fiscal_position_id = cliente[0]['property_account_position_id'][0] if isinstance(cliente[0]['property_account_position_id'], list) else cliente[0]['property_account_position_id']
            logger.info(f"   📊 Posição Fiscal do Cliente: ID {fiscal_position_id}")
        
        if cliente[0].get('property_product_pricelist'):
            pricelist_id = cliente[0]['property_product_pricelist'][0] if isinstance(cliente[0]['property_product_pricelist'], list) else cliente[0]['property_product_pricelist']
            logger.info(f"   💰 Lista de Preços do Cliente: ID {pricelist_id}")
        
        if cliente[0].get('property_payment_term_id'):
            payment_term_id = cliente[0]['property_payment_term_id'][0] if isinstance(cliente[0]['property_payment_term_id'], list) else cliente[0]['property_payment_term_id']
            logger.info(f"   💳 Condição de Pagamento do Cliente: ID {payment_term_id}")
        
        # 2. Se não houver posição fiscal no cliente, buscar a padrão
        if not fiscal_position_id:
            logger.info("🔍 Cliente sem posição fiscal, buscando padrão...")
            fiscal_positions = odoo.search_read(
                'account.fiscal.position',
                [('company_id', '=', company_id)],
                ['id', 'name', 'auto_apply'],
                limit=5
            )
            
            if fiscal_positions:
                # Preferir uma com auto_apply
                for fp in fiscal_positions:
                    if fp.get('auto_apply'):
                        fiscal_position_id = fp['id']
                        logger.info(f"   ✅ Usando posição fiscal automática: {fp['name']}")
                        break
                
                if not fiscal_position_id:
                    fiscal_position_id = fiscal_positions[0]['id']
                    logger.info(f"   ✅ Usando posição fiscal: {fiscal_positions[0]['name']}")
        
        # 3. Buscar detalhes da posição fiscal
        fiscal_position_details = None
        if fiscal_position_id:
            fiscal_position_details = odoo.search_read(
                'account.fiscal.position',
                [('id', '=', fiscal_position_id)],
                ['id', 'name', 'tax_ids']
            )
            if fiscal_position_details:
                logger.info(f"   📋 Posição Fiscal: {fiscal_position_details[0]['name']}")
        
        # 4. Preparar linhas de produtos com impostos mapeados
        logger.info("📦 Preparando produtos com impostos corretos...")
        order_lines = []
        
        for prod in produtos_cotacao:
            logger.info(f"\n   🔍 Processando: {prod['codigo']} - {prod['descricao']}")
            
            # Buscar produto com impostos
            produto = odoo.search_read(
                'product.product',
                [('default_code', '=', prod['codigo'])],
                ['id', 'name', 'taxes_id', 'supplier_taxes_id', 'uom_id', 'categ_id'],
                limit=1
            )
            
            if not produto:
                # Tentar por nome
                produto = odoo.search_read(
                    'product.product',
                    [('name', 'ilike', prod['descricao'][:20])],
                    ['id', 'name', 'taxes_id', 'supplier_taxes_id', 'uom_id', 'categ_id'],
                    limit=1
                )
            
            if produto:
                product_id = produto[0]['id']
                logger.info(f"   ✅ Produto encontrado: {produto[0]['name']} (ID: {product_id})")
                
                # Impostos originais do produto
                impostos_produto = produto[0].get('taxes_id', [])
                logger.info(f"   💰 Impostos do produto (IDs): {impostos_produto}")
                
                # Se houver impostos, buscar detalhes
                if impostos_produto:
                    detalhes_impostos = odoo.search_read(
                        'account.tax',
                        [('id', 'in', impostos_produto)],
                        ['id', 'name', 'amount', 'type_tax_use']
                    )
                    for imp in detalhes_impostos:
                        logger.info(f"      • {imp['name']} - {imp['amount']}%")
                
                # Mapear impostos usando a posição fiscal
                impostos_mapeados = impostos_produto  # Default: usar impostos do produto
                
                if fiscal_position_id and impostos_produto:
                    logger.info(f"   🔄 Mapeando impostos com posição fiscal...")
                    
                    # Buscar mapeamento de impostos da posição fiscal
                    tax_mappings = odoo.search_read(
                        'account.fiscal.position.tax',
                        [('position_id', '=', fiscal_position_id)],
                        ['tax_src_id', 'tax_dest_id']
                    )
                    
                    if tax_mappings:
                        logger.info(f"      Encontrados {len(tax_mappings)} mapeamentos")
                        
                        # Criar dicionário de mapeamento
                        map_dict = {}
                        for mapping in tax_mappings:
                            src_id = mapping['tax_src_id'][0] if mapping.get('tax_src_id') else None
                            dest_id = mapping['tax_dest_id'][0] if mapping.get('tax_dest_id') else None
                            if src_id:
                                map_dict[src_id] = dest_id
                        
                        # Aplicar mapeamento
                        impostos_mapeados = []
                        for tax_id in impostos_produto:
                            if tax_id in map_dict:
                                if map_dict[tax_id]:  # Se não for None (remoção de imposto)
                                    impostos_mapeados.append(map_dict[tax_id])
                                    logger.info(f"      Imposto {tax_id} → {map_dict[tax_id]}")
                                else:
                                    logger.info(f"      Imposto {tax_id} → Removido")
                            else:
                                impostos_mapeados.append(tax_id)
                                logger.info(f"      Imposto {tax_id} → Mantido")
                
                logger.info(f"   ✅ Impostos finais (IDs): {impostos_mapeados}")
                
                # Montar linha do produto
                line_values = {
                    'product_id': product_id,
                    'name': prod['descricao'],  # Usar nossa descrição
                    'product_uom_qty': prod['quantidade'],
                    'price_unit': prod['preco_unitario'],
                    'product_uom': produto[0]['uom_id'][0] if produto[0].get('uom_id') else 1
                }
                
                # Adicionar impostos mapeados
                if impostos_mapeados:
                    line_values['tax_id'] = [(6, 0, impostos_mapeados)]  # (6, 0, ids) = substituir todos
                    
                order_lines.append((0, 0, line_values))
            else:
                logger.warning(f"   ❌ Produto não encontrado: {prod['codigo']}")
                # Adicionar linha manual sem impostos
                order_lines.append((0, 0, {
                    'name': f"{prod['codigo']} - {prod['descricao']}",
                    'product_uom_qty': prod['quantidade'],
                    'price_unit': prod['preco_unitario'],
                    'product_uom': 1,
                    'tax_id': [(6, 0, [])]  # Sem impostos
                }))
        
        # 5. Criar a cotação com todos os dados fiscais
        logger.info("\n📝 Criando cotação com impostos configurados...")
        
        cotacao_data = {
            'partner_id': partner_id,
            'company_id': company_id,
            'warehouse_id': warehouse_id,
            'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'validity_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'order_line': order_lines,
            'note': f'Cotação com impostos mapeados - {empresa_nome}'
        }
        
        # Adicionar campos fiscais se disponíveis
        if fiscal_position_id:
            cotacao_data['fiscal_position_id'] = fiscal_position_id
        if pricelist_id:
            cotacao_data['pricelist_id'] = pricelist_id
        if payment_term_id:
            cotacao_data['payment_term_id'] = payment_term_id
        
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
        
        # 6. Forçar recálculo dos totais (write vazio)
        logger.info("🔄 Forçando recálculo dos totais...")
        try:
            odoo.execute_kw(
                'sale.order',
                'write',
                [[cotacao_id], {'state': 'draft'}],  # Write do mesmo valor força recálculo
                {'context': {'company_id': company_id}}
            )
            logger.info("   ✅ Recálculo executado")
        except Exception as e:
            logger.warning(f"   ⚠️ Não foi possível forçar recálculo: {e}")
        
        # 7. Buscar cotação criada com totais
        logger.info("📊 Buscando cotação criada...")
        cotacao = odoo.search_read(
            'sale.order',
            [('id', '=', cotacao_id)],
            ['name', 'state', 'amount_untaxed', 'amount_tax', 'amount_total', 
             'fiscal_position_id', 'company_id', 'warehouse_id']
        )
        
        if cotacao:
            logger.info("\n" + "="*70)
            logger.info("📊 RESUMO DA COTAÇÃO COM IMPOSTOS:")
            logger.info("="*70)
            logger.info(f"   🏢 EMPRESA: {cotacao[0]['company_id'][1] if cotacao[0].get('company_id') else 'N/A'}")
            logger.info(f"   🏭 ARMAZÉM: {cotacao[0]['warehouse_id'][1] if cotacao[0].get('warehouse_id') else 'N/A'}")
            logger.info(f"   📋 Número: {cotacao[0]['name']}")
            logger.info(f"   👤 Cliente: {cliente[0].get('name', '')}")
            logger.info(f"   📊 Posição Fiscal: {cotacao[0]['fiscal_position_id'][1] if cotacao[0].get('fiscal_position_id') else 'Não definida'}")
            logger.info(f"   🏷️ Status: {cotacao[0]['state']}")
            logger.info(f"   💰 Subtotal: R$ {cotacao[0]['amount_untaxed']:,.2f}")
            logger.info(f"   💰 IMPOSTOS: R$ {cotacao[0]['amount_tax']:,.2f}")
            logger.info(f"   💰 TOTAL: R$ {cotacao[0]['amount_total']:,.2f}")
            
            # Porcentagem de impostos
            if cotacao[0]['amount_untaxed'] > 0:
                percent_tax = (cotacao[0]['amount_tax'] / cotacao[0]['amount_untaxed']) * 100
                logger.info(f"   📊 Impostos representam: {percent_tax:.2f}% do subtotal")
            
            logger.info("="*70)
            
            # Buscar linhas com detalhes dos impostos
            linhas = odoo.search_read(
                'sale.order.line',
                [('order_id', '=', cotacao_id)],
                ['name', 'product_uom_qty', 'price_unit', 'price_subtotal', 
                 'price_tax', 'price_total', 'tax_id']
            )
            
            if linhas:
                logger.info("\n📦 DETALHAMENTO DOS PRODUTOS:")
                logger.info("-"*70)
                
                total_impostos_linhas = 0
                
                for i, linha in enumerate(linhas, 1):
                    logger.info(f"\n{i}. {linha['name']}")
                    logger.info(f"   Quantidade: {linha['product_uom_qty']} unidades")
                    logger.info(f"   Preço Unit: R$ {linha['price_unit']:,.2f}")
                    logger.info(f"   Subtotal: R$ {linha['price_subtotal']:,.2f}")
                    
                    # Buscar detalhes dos impostos aplicados
                    if linha.get('tax_id'):
                        impostos = odoo.search_read(
                            'account.tax',
                            [('id', 'in', linha['tax_id'])],
                            ['name', 'amount', 'description']
                        )
                        
                        if impostos:
                            logger.info(f"   Impostos aplicados:")
                            for imp in impostos:
                                logger.info(f"      • {imp['name']}: {imp['amount']}%")
                            
                            valor_imposto = linha.get('price_tax', 0)
                            total_impostos_linhas += valor_imposto
                            logger.info(f"   Valor dos Impostos: R$ {valor_imposto:,.2f}")
                        else:
                            logger.info(f"   Impostos: Nenhum")
                    else:
                        logger.info(f"   Impostos: Nenhum")
                    
                    logger.info(f"   TOTAL com Impostos: R$ {linha.get('price_total', linha['price_subtotal']):,.2f}")
                
                logger.info("-"*70)
                logger.info(f"\n📊 TOTAL DE IMPOSTOS DAS LINHAS: R$ {total_impostos_linhas:,.2f}")
                logger.info("="*70)
        
        return cotacao_id
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar cotação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("🚀 Iniciando criação de cotação com impostos corretos...")
    logger.info("="*70)
    
    cotacao_id = criar_cotacao_com_impostos()
    
    if cotacao_id:
        logger.info(f"\n✅ SUCESSO! Cotação criada com impostos!")
        logger.info(f"🆔 ID: {cotacao_id}")
        logger.info("💡 Os impostos foram mapeados usando a posição fiscal")
        logger.info("📋 Verifique no Odoo se os impostos foram aplicados corretamente")
    else:
        logger.error("\n❌ Falha ao criar cotação")