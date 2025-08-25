#!/usr/bin/env python3
"""
Script para criar uma cotação de exemplo no Odoo para NACOM GOYA - CD
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

def criar_cotacao_nacom():
    """
    Cria uma cotação no Odoo para a empresa NACOM GOYA - CD
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
            ['id', 'name', 'l10n_br_razao_social'],
            limit=1
        )
        
        if not cliente:
            logger.error(f"❌ Cliente com CNPJ {cnpj_cliente} não encontrado no Odoo")
            logger.info("💡 Tentando buscar cliente por CNPJ parcial ou nome...")
            
            # Tentar buscar por CNPJ parcial (removendo formatação)
            cnpj_limpo = cnpj_cliente.replace('.', '').replace('/', '').replace('-', '')
            cliente = odoo.search_read(
                'res.partner',
                ['|', 
                 ('l10n_br_cnpj', 'ilike', cnpj_limpo[:8]),  # Primeiros 8 dígitos do CNPJ
                 ('vat', 'ilike', cnpj_limpo[:8])
                ],
                ['id', 'name', 'l10n_br_cnpj', 'l10n_br_razao_social'],
                limit=5
            )
            
            if cliente:
                logger.info(f"📋 Clientes encontrados:")
                for c in cliente:
                    logger.info(f"   ID: {c['id']} - {c.get('name', '')} - CNPJ: {c.get('l10n_br_cnpj', 'N/A')}")
                
                # Usar o primeiro cliente encontrado
                cliente = [cliente[0]]
                logger.info(f"✅ Usando cliente: {cliente[0]['name']}")
            else:
                logger.error("❌ Nenhum cliente encontrado. Verifique se o cliente existe no Odoo.")
                return None
        
        partner_id = cliente[0]['id']
        logger.info(f"✅ Cliente encontrado: {cliente[0].get('name', '')} (ID: {partner_id})")
        
        # 2. Preparar linhas de produtos
        logger.info("📦 Preparando produtos da cotação...")
        order_lines = []
        produtos_nao_encontrados = []
        
        for prod in produtos_cotacao:
            # Buscar produto pelo código NA EMPRESA ESPECÍFICA
            logger.info(f"   🔍 Buscando produto: {prod['codigo']} - {prod['descricao']}")
            
            # Primeiro tentar buscar o produto com contexto da empresa
            produto = odoo.execute_kw(
                'product.product',
                'search_read',
                [[('default_code', '=', prod['codigo'])]],
                {'fields': ['id', 'name', 'list_price', 'uom_id'], 
                 'limit': 1,
                 'context': {'company_id': company_id}}
            )
            
            if not produto:
                # Tentar buscar por nome se não encontrar por código
                logger.warning(f"   ⚠️ Produto {prod['codigo']} não encontrado por código, tentando por nome...")
                produto = odoo.execute_kw(
                    'product.product',
                    'search_read',
                    [[('name', 'ilike', prod['descricao'][:20])]],
                    {'fields': ['id', 'name', 'list_price', 'default_code', 'uom_id'], 
                     'limit': 1,
                     'context': {'company_id': company_id}}
                )
            
            if produto:
                logger.info(f"   ✅ Produto encontrado: {produto[0]['name']} (ID: {produto[0]['id']})")
                
                # Adicionar linha do produto
                order_lines.append((0, 0, {
                    'product_id': produto[0]['id'],
                    'name': prod['descricao'],  # Usar a descrição fornecida
                    'product_uom_qty': prod['quantidade'],
                    'price_unit': prod['preco_unitario'],
                    'product_uom': produto[0]['uom_id'][0] if produto[0].get('uom_id') else 1
                }))
            else:
                logger.warning(f"   ❌ Produto não encontrado: {prod['codigo']} - {prod['descricao']}")
                produtos_nao_encontrados.append(prod)
                
                # Adicionar como linha sem produto (apenas descrição)
                order_lines.append((0, 0, {
                    'name': f"{prod['codigo']} - {prod['descricao']}",
                    'product_uom_qty': prod['quantidade'],
                    'price_unit': prod['preco_unitario'],
                    'product_uom': 1  # Unidade padrão
                }))
        
        if not order_lines:
            logger.error("❌ Nenhum produto foi preparado para a cotação")
            return None
        
        # 3. Buscar condições de pagamento e lista de preços da empresa
        logger.info("💳 Buscando configurações adicionais para a empresa NACOM CD...")
        
        # Buscar condição de pagamento
        payment_terms = odoo.execute_kw(
            'account.payment.term',
            'search_read',
            [[]],
            {'fields': ['id', 'name'], 
             'limit': 1,
             'context': {'company_id': company_id}}
        )
        payment_term_id = payment_terms[0]['id'] if payment_terms else False
        if payment_term_id:
            logger.info(f"   ✅ Condição de pagamento: {payment_terms[0]['name']}")
        
        # Buscar lista de preços
        pricelists = odoo.execute_kw(
            'product.pricelist',
            'search_read',
            [[('active', '=', True)]],
            {'fields': ['id', 'name', 'company_id'], 
             'limit': 10,
             'context': {'company_id': company_id}}
        )
        
        # Preferir lista de preços da empresa NACOM CD
        pricelist_id = None
        for pl in pricelists:
            # Verificar se é lista de preços da empresa ou sem empresa (geral)
            if not pl.get('company_id') or (pl.get('company_id') and pl['company_id'][0] == company_id):
                pricelist_id = pl['id']
                logger.info(f"   ✅ Lista de preços: {pl['name']}")
                break
        
        if not pricelist_id and pricelists:
            pricelist_id = pricelists[0]['id']
            logger.info(f"   ℹ️ Usando lista de preços padrão: {pricelists[0]['name']}")
        
        # 4. Criar a cotação COM CONTEXTO DA EMPRESA
        logger.info(f"📝 Criando cotação no Odoo para empresa {empresa_nome}...")
        
        # Preparar dados da cotação
        cotacao_data = {
            'partner_id': partner_id,
            'company_id': company_id,  # ESPECIFICAR A EMPRESA NACOM GOYA - CD
            'warehouse_id': warehouse_id,  # ESPECIFICAR O ARMAZÉM CD
            'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'validity_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'order_line': order_lines,
            'note': f'Cotação criada via API para empresa {empresa_nome} - Armazém CD'
        }
        
        # Adicionar campos opcionais se disponíveis
        if payment_term_id:
            cotacao_data['payment_term_id'] = payment_term_id
        if pricelist_id:
            cotacao_data['pricelist_id'] = pricelist_id
        
        # Criar a cotação com contexto da empresa
        logger.info("   Enviando dados para criar cotação...")
        cotacao_id = odoo.execute_kw(
            'sale.order',
            'create',
            [cotacao_data],
            {'context': {
                'company_id': company_id, 
                'allowed_company_ids': [company_id],
                'default_warehouse_id': warehouse_id
            }}
        )
        
        logger.info(f"✅ Cotação criada com sucesso! ID: {cotacao_id}")
        
        # 5. Buscar informações da cotação criada
        cotacao = odoo.search_read(
            'sale.order',
            [('id', '=', cotacao_id)],
            ['name', 'state', 'amount_untaxed', 'amount_tax', 'amount_total', 
             'date_order', 'validity_date', 'company_id', 'warehouse_id']
        )
        
        if cotacao:
            logger.info("\n" + "="*60)
            logger.info("📊 RESUMO DA COTAÇÃO CRIADA:")
            logger.info("="*60)
            logger.info(f"   🏢 EMPRESA: {cotacao[0]['company_id'][1] if cotacao[0].get('company_id') else 'N/A'}")
            logger.info(f"   🏭 ARMAZÉM: {cotacao[0]['warehouse_id'][1] if cotacao[0].get('warehouse_id') else 'N/A'}")
            logger.info(f"   📋 Número: {cotacao[0]['name']}")
            logger.info(f"   👤 Cliente: {cliente[0].get('name', '')}")
            logger.info(f"   📅 Data: {cotacao[0]['date_order']}")
            logger.info(f"   📅 Validade: {cotacao[0]['validity_date']}")
            logger.info(f"   🏷️ Status: {cotacao[0]['state']}")
            logger.info(f"   💰 Subtotal: R$ {cotacao[0]['amount_untaxed']:,.2f}")
            logger.info(f"   💰 Impostos: R$ {cotacao[0]['amount_tax']:,.2f}")
            logger.info(f"   💰 TOTAL: R$ {cotacao[0]['amount_total']:,.2f}")
            logger.info("="*60)
            
            # Calcular total esperado
            total_esperado = sum(p['quantidade'] * p['preco_unitario'] for p in produtos_cotacao)
            logger.info(f"\n   📊 Total esperado (sem impostos): R$ {total_esperado:,.2f}")
            
            # Buscar linhas da cotação para conferência
            linhas = odoo.search_read(
                'sale.order.line',
                [('order_id', '=', cotacao_id)],
                ['name', 'product_uom_qty', 'price_unit', 'price_subtotal']
            )
            
            if linhas:
                logger.info("\n   📦 PRODUTOS NA COTAÇÃO:")
                logger.info("   " + "-"*50)
                for linha in linhas:
                    logger.info(f"   • {linha['name']}")
                    logger.info(f"     Qtd: {linha['product_uom_qty']} x R$ {linha['price_unit']:,.2f} = R$ {linha['price_subtotal']:,.2f}")
                logger.info("   " + "-"*50)
            
            if produtos_nao_encontrados:
                logger.warning(f"\n⚠️ ATENÇÃO: {len(produtos_nao_encontrados)} produto(s) foram adicionados como linhas manuais")
                for p in produtos_nao_encontrados:
                    logger.warning(f"   • {p['codigo']} - {p['descricao']}")
        
        return cotacao_id
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar cotação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("🚀 Iniciando criação de cotação para NACOM GOYA - CD...")
    logger.info("="*60)
    
    cotacao_id = criar_cotacao_nacom()
    
    if cotacao_id:
        logger.info(f"\n✅ SUCESSO! Cotação criada com ID: {cotacao_id}")
        logger.info("🏢 Empresa: NACOM GOYA - CD")
        logger.info("🏭 Armazém: CD")
        logger.info("💡 Você pode acessar esta cotação no Odoo em: Vendas > Cotações")
    else:
        logger.error("\n❌ Falha ao criar cotação. Verifique os logs acima para mais detalhes.")