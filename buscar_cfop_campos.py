#!/usr/bin/env python3
"""
Script para descobrir os campos corretos do modelo CFOP customizado
Data: 2025-01-25
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("🔌 Conectando ao Odoo...")
odoo = get_odoo_connection()

# 1. Descobrir campos do modelo CFOP customizado
logger.info("\n" + "="*80)
logger.info("🔍 DESCOBRINDO CAMPOS DO MODELO l10n_br_ciel_it_account.cfop")
logger.info("="*80)

try:
    fields = odoo.execute_kw(
        'l10n_br_ciel_it_account.cfop',
        'fields_get',
        [],
        {'attributes': ['string', 'type', 'required']}
    )
    
    logger.info("\n✅ Campos disponíveis no modelo CFOP:")
    logger.info("-"*80)
    
    for field_name, field_info in sorted(fields.items()):
        if field_name not in ['__last_update', 'create_uid', 'create_date', 'write_uid', 'write_date']:
            logger.info(f"\n   • {field_name}:")
            logger.info(f"     Descrição: {field_info.get('string', '')}")
            logger.info(f"     Tipo: {field_info.get('type', '')}")
            if field_info.get('required'):
                logger.info(f"     Obrigatório: SIM")
except Exception as e:
    logger.error(f"Erro ao buscar campos: {e}")

# 2. Buscar alguns CFOPs disponíveis com campos corretos
logger.info("\n" + "="*80)
logger.info("📋 LISTANDO CFOPS DISPONÍVEIS")
logger.info("="*80)

try:
    # Primeiro buscar sem campos para ver se funciona
    cfops = odoo.search_read(
        'l10n_br_ciel_it_account.cfop',
        [],
        [],  # Sem campos específicos primeiro
        limit=10
    )
    
    if cfops:
        logger.info(f"\n✅ Exemplos de CFOPs encontrados:")
        logger.info("-"*80)
        
        for cfop in cfops:
            logger.info(f"\n   CFOP ID: {cfop.get('id')}")
            # Mostrar todos os campos disponíveis
            for key, value in cfop.items():
                if key not in ['__last_update', 'create_uid', 'create_date', 'write_uid', 'write_date']:
                    logger.info(f"     {key}: {value}")
                    
        # Agora buscar CFOPs específicos para venda e transferência
        logger.info("\n" + "="*80)
        logger.info("⭐ BUSCANDO CFOPS ESPECÍFICOS")
        logger.info("="*80)
        
        # Tentar buscar pelo campo que descobrimos
        codigo_field = 'codigo_cfop' if 'codigo_cfop' in cfops[0] else 'code'
        
        # CFOPs comuns
        codigos_buscar = ['5102', '6102', '5152', '6152', '5405', '6405']
        
        for codigo in codigos_buscar:
            cfop_especifico = odoo.search_read(
                'l10n_br_ciel_it_account.cfop',
                [(codigo_field, '=', codigo)],
                [],
                limit=1
            )
            
            if cfop_especifico:
                logger.info(f"\n   ✅ CFOP {codigo} encontrado:")
                logger.info(f"      ID: {cfop_especifico[0].get('id')}")
                logger.info(f"      Dados: {cfop_especifico[0]}")
                
except Exception as e:
    logger.error(f"Erro ao buscar CFOPs: {e}")

# 3. Verificar como está configurado em pedidos existentes
logger.info("\n" + "="*80)
logger.info("📊 ANALISANDO PEDIDOS COM CFOP")
logger.info("="*80)

try:
    # Buscar pedidos recentes com CFOP
    orders = odoo.search_read(
        'sale.order',
        [],
        ['name'],
        limit=5,
        order='id desc'
    )
    
    for order in orders:
        logger.info(f"\n📋 Pedido: {order['name']}")
        
        # Buscar linhas deste pedido
        lines = odoo.search_read(
            'sale.order.line',
            [('order_id', '=', order['id'])],
            ['product_id', 'l10n_br_cfop_id', 'l10n_br_cfop_codigo'],
            limit=3
        )
        
        if lines:
            for line in lines:
                produto = line.get('product_id', ['', ''])[1] if line.get('product_id') else 'N/A'
                cfop_id = line.get('l10n_br_cfop_id')
                cfop_codigo = line.get('l10n_br_cfop_codigo', 'N/A')
                
                logger.info(f"   • Produto: {produto[:40]}")
                logger.info(f"     CFOP ID: {cfop_id}")
                logger.info(f"     CFOP Código: {cfop_codigo}")
                
                # Se tem CFOP, buscar detalhes
                if cfop_id and isinstance(cfop_id, list):
                    cfop_details = odoo.search_read(
                        'l10n_br_ciel_it_account.cfop',
                        [('id', '=', cfop_id[0])],
                        [],
                        limit=1
                    )
                    if cfop_details:
                        logger.info(f"     Detalhes CFOP: {cfop_details[0]}")
                        
except Exception as e:
    logger.error(f"Erro: {e}")

logger.info("\n" + "="*80)
logger.info("💡 RESUMO")
logger.info("="*80)
logger.info("""
Com base na análise:

1. O modelo CFOP usado é: l10n_br_ciel_it_account.cfop
2. Os campos em sale.order.line são:
   - l10n_br_cfop_id: Relação many2one com o CFOP
   - l10n_br_cfop_codigo: Código do CFOP (char)
   
3. Para definir o CFOP em uma cotação:
   - Buscar o ID do CFOP desejado no modelo l10n_br_ciel_it_account.cfop
   - Definir l10n_br_cfop_id na linha do pedido
   - O campo l10n_br_cfop_codigo será preenchido automaticamente
   
4. A Server Action ID 863 pode calcular o CFOP baseado na posição fiscal
""")