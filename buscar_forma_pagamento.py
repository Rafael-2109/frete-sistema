#!/usr/bin/env python3
"""
Script para buscar Formas de Pagamento (payment providers) no Odoo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conectar
logger.info("🔌 Conectando ao Odoo...")
odoo = get_odoo_connection()

# 1. Primeiro vamos descobrir qual modelo é usado para payment_provider_id
logger.info("\n🔍 Verificando campo payment_provider_id em sale.order...")
try:
    fields = odoo.execute_kw(
        'sale.order',
        'fields_get',
        [['payment_provider_id']],
        {'attributes': ['string', 'type', 'relation']}
    )
    
    if 'payment_provider_id' in fields:
        field_info = fields['payment_provider_id']
        logger.info(f"   Campo encontrado:")
        logger.info(f"   • Nome: payment_provider_id")
        logger.info(f"   • Descrição: {field_info.get('string', '')}")
        logger.info(f"   • Tipo: {field_info.get('type', '')}")
        logger.info(f"   • Modelo Relacionado: {field_info.get('relation', '')}")
        
        model_name = field_info.get('relation', 'payment.provider')
    else:
        logger.info("   ⚠️ Campo payment_provider_id não encontrado")
        model_name = 'payment.provider'
except Exception as e:
    logger.error(f"Erro ao verificar campo: {e}")
    model_name = 'payment.provider'

# 2. Buscar Payment Providers
logger.info(f"\n💳 BUSCANDO FORMAS DE PAGAMENTO ({model_name})...")
try:
    providers = odoo.search_read(
        model_name,
        [],
        ['id', 'name', 'display_name', 'state', 'company_id']
    )
    
    if providers:
        logger.info(f"\n✅ {len(providers)} Formas de Pagamento encontradas:")
        logger.info("-" * 70)
        
        for prov in providers:
            company = prov.get('company_id', ['', ''])[1] if prov.get('company_id') else 'Todas'
            state = prov.get('state', 'N/A')
            logger.info(f"   • ID: {prov['id']:3} | Nome: {prov.get('name', prov.get('display_name', 'N/A')):40} | Empresa: {company:20} | Status: {state}")
            
            # Destacar se encontrar Transferência Bancária CD
            if any(term in str(prov.get('name', '')).upper() for term in ['TRANSF', 'BANC', 'CD']):
                logger.info(f"     ⭐ POSSÍVEL MATCH: {prov.get('name', '')}")
    else:
        logger.info("❌ Nenhuma forma de pagamento encontrada")
except Exception as e:
    logger.error(f"Erro ao buscar {model_name}: {e}")
    
    # Tentar modelo alternativo payment.acquirer (versões antigas do Odoo)
    logger.info("\n💳 Tentando modelo alternativo payment.acquirer...")
    try:
        providers = odoo.search_read(
            'payment.acquirer',
            [],
            ['id', 'name', 'display_name', 'state', 'company_id', 'provider']
        )
        
        if providers:
            logger.info(f"\n✅ {len(providers)} Payment Acquirers encontrados:")
            logger.info("-" * 70)
            
            for prov in providers:
                company = prov.get('company_id', ['', ''])[1] if prov.get('company_id') else 'Todas'
                state = prov.get('state', 'N/A')
                provider_type = prov.get('provider', 'N/A')
                logger.info(f"   • ID: {prov['id']:3} | Nome: {prov.get('name', 'N/A'):30} | Tipo: {provider_type:15} | Empresa: {company:20}")
                
                # Destacar se encontrar Transferência
                if any(term in str(prov.get('name', '')).upper() for term in ['TRANSF', 'BANC', 'CD', 'WIRE']):
                    logger.info(f"     ⭐ POSSÍVEL MATCH: {prov.get('name', '')}")
    except Exception as e2:
        logger.error(f"Erro ao buscar payment.acquirer: {e2}")

# 3. Buscar também em account.payment.method se existir
logger.info("\n🏦 Buscando métodos de pagamento alternativos...")
try:
    methods = odoo.search_read(
        'account.payment.method',
        [],
        ['id', 'name', 'code', 'payment_type']
    )
    
    if methods:
        logger.info(f"\n✅ {len(methods)} Métodos de Pagamento encontrados:")
        for method in methods:
            logger.info(f"   • ID: {method['id']:3} | Código: {method.get('code', 'N/A'):20} | Nome: {method.get('name', 'N/A'):30} | Tipo: {method.get('payment_type', 'N/A')}")
            
            if any(term in str(method.get('name', '')).upper() for term in ['TRANSF', 'BANC']):
                logger.info(f"     ⭐ POSSÍVEL: {method.get('name', '')}")
except:
    logger.info("   ℹ️ Modelo account.payment.method não disponível")

# 4. Verificar um pedido existente para ver qual valor está sendo usado
logger.info("\n📋 Verificando pedidos existentes para exemplo...")
try:
    orders = odoo.search_read(
        'sale.order',
        [('payment_provider_id', '!=', False)],
        ['name', 'payment_provider_id'],
        limit=3
    )
    
    if orders:
        logger.info(f"\nExemplos de pedidos com forma de pagamento:")
        for order in orders:
            logger.info(f"   • Pedido {order['name']}: payment_provider_id = {order['payment_provider_id']}")
except Exception as e:
    logger.info(f"   ℹ️ Não foi possível buscar exemplos: {e}")