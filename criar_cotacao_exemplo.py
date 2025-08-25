#!/usr/bin/env python3
"""
Script para criar uma cotação de exemplo no Odoo
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

def criar_cotacao_exemplo():
    """
    Cria uma cotação no Odoo com os produtos especificados
    """
    try:
        # Conectar ao Odoo
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        if not odoo:
            logger.error("❌ Não foi possível conectar ao Odoo")
            return None
        
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
                
                # Listar alguns clientes para referência
                logger.info("📋 Listando alguns clientes disponíveis:")
                clientes_exemplo = odoo.search_read(
                    'res.partner',
                    [('customer_rank', '>', 0)],  # Apenas clientes
                    ['id', 'name', 'l10n_br_cnpj'],
                    limit=10
                )
                for c in clientes_exemplo:
                    if c.get('l10n_br_cnpj'):
                        logger.info(f"   ID: {c['id']} - {c['name']} - CNPJ: {c.get('l10n_br_cnpj', 'N/A')}")
                
                return None
        
        partner_id = cliente[0]['id']
        logger.info(f"✅ Cliente encontrado: {cliente[0].get('name', '')} (ID: {partner_id})")
        
        # 2. Preparar linhas de produtos
        logger.info("📦 Preparando produtos da cotação...")
        order_lines = []
        produtos_nao_encontrados = []
        
        for prod in produtos_cotacao:
            # Buscar produto pelo código
            logger.info(f"   🔍 Buscando produto: {prod['codigo']} - {prod['descricao']}")
            
            produto = odoo.search_read(
                'product.product',
                [('default_code', '=', prod['codigo'])],
                ['id', 'name', 'list_price', 'uom_id'],
                limit=1
            )
            
            if not produto:
                # Tentar buscar por nome se não encontrar por código
                logger.warning(f"   ⚠️ Produto {prod['codigo']} não encontrado por código, tentando por nome...")
                produto = odoo.search_read(
                    'product.product',
                    [('name', 'ilike', prod['descricao'][:20])],  # Busca parcial pelo nome
                    ['id', 'name', 'list_price', 'default_code', 'uom_id'],
                    limit=1
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
        
        # 3. Buscar condições de pagamento e lista de preços (opcional)
        logger.info("💳 Buscando configurações adicionais...")
        
        # Buscar condição de pagamento padrão
        payment_terms = odoo.search_read(
            'account.payment.term',
            [],
            ['id', 'name'],
            limit=1
        )
        payment_term_id = payment_terms[0]['id'] if payment_terms else False
        
        # Buscar lista de preços padrão
        pricelists = odoo.search_read(
            'product.pricelist',
            [('active', '=', True)],
            ['id', 'name'],
            limit=1
        )
        pricelist_id = pricelists[0]['id'] if pricelists else False
        
        # 4. Criar a cotação
        logger.info("📝 Criando cotação no Odoo...")
        
        # Preparar dados da cotação
        cotacao_data = {
            'partner_id': partner_id,
            'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'validity_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'order_line': order_lines,
            'note': 'Cotação criada via API - Exemplo de integração'
        }
        
        # Adicionar campos opcionais se disponíveis
        if payment_term_id:
            cotacao_data['payment_term_id'] = payment_term_id
        if pricelist_id:
            cotacao_data['pricelist_id'] = pricelist_id
        
        # Criar a cotação
        cotacao_id = odoo.execute_kw(
            'sale.order',
            'create',
            [cotacao_data]
        )
        
        logger.info(f"✅ Cotação criada com sucesso! ID: {cotacao_id}")
        
        # 5. Buscar informações da cotação criada
        cotacao = odoo.search_read(
            'sale.order',
            [('id', '=', cotacao_id)],
            ['name', 'state', 'amount_untaxed', 'amount_tax', 'amount_total', 'date_order', 'validity_date']
        )
        
        if cotacao:
            logger.info("\n" + "="*60)
            logger.info("📊 RESUMO DA COTAÇÃO CRIADA:")
            logger.info("="*60)
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
                logger.warning(f"\n⚠️ ATENÇÃO: {len(produtos_nao_encontrados)} produto(s) foram adicionados como linhas manuais (sem vínculo com produto)")
                for p in produtos_nao_encontrados:
                    logger.warning(f"   • {p['codigo']} - {p['descricao']}")
        
        return cotacao_id
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar cotação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("🚀 Iniciando criação de cotação de exemplo no Odoo...")
    logger.info("="*60)
    
    cotacao_id = criar_cotacao_exemplo()
    
    if cotacao_id:
        logger.info(f"\n✅ SUCESSO! Cotação criada com ID: {cotacao_id}")
        logger.info("💡 Você pode acessar esta cotação no Odoo em: Vendas > Cotações")
    else:
        logger.error("\n❌ Falha ao criar cotação. Verifique os logs acima para mais detalhes.")