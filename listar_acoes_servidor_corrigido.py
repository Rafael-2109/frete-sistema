#!/usr/bin/env python3
"""
Script corrigido para listar Ações do Servidor do Odoo
Data: 2025-01-25
"""

import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def listar_acoes_servidor():
    """
    Lista ações do servidor e campos disponíveis
    """
    try:
        # Conectar ao Odoo
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        if not odoo:
            logger.error("❌ Não foi possível conectar ao Odoo")
            return None
        
        # 1. Primeiro, vamos descobrir quais campos existem em ir.actions.server
        logger.info("\n" + "="*80)
        logger.info("🔍 DESCOBRINDO CAMPOS DE ir.actions.server")
        logger.info("="*80)
        
        try:
            fields_info = odoo.execute_kw(
                'ir.actions.server',
                'fields_get',
                [],
                {'attributes': ['string', 'type', 'required']}
            )
            
            logger.info("\nCampos disponíveis em ir.actions.server:")
            for field_name, field_info in list(fields_info.items())[:20]:
                logger.info(f"   • {field_name}: {field_info.get('string', '')} ({field_info.get('type', '')})")
        except Exception as e:
            logger.error(f"Erro ao buscar campos: {e}")
        
        # 2. Buscar Server Actions com campos válidos
        logger.info("\n" + "="*80)
        logger.info("🎯 SERVER ACTIONS PARA SALE.ORDER")
        logger.info("="*80)
        
        try:
            server_actions = odoo.search_read(
                'ir.actions.server',
                ['|', ('model_id.model', '=', 'sale.order'), 
                      ('model_id.model', '=', 'sale.order.line')],
                ['id', 'name', 'state', 'code', 'model_id', 'sequence']
            )
            
            if server_actions:
                logger.info(f"\n✅ Encontradas {len(server_actions)} Server Actions:")
                for i, action in enumerate(server_actions, 1):
                    logger.info(f"\n{i}. {action['name']}")
                    logger.info(f"   🆔 ID: {action['id']}")
                    logger.info(f"   📊 Modelo: {action['model_id'][1] if action.get('model_id') else 'N/A'}")
                    logger.info(f"   🔧 Tipo: {action['state']}")
                    
                    if action['state'] == 'code' and action.get('code'):
                        logger.info(f"   💻 Código Python (primeiras linhas):")
                        code_lines = action['code'].split('\n')[:3]
                        for line in code_lines:
                            if line.strip():
                                logger.info(f"      {line[:80]}")
            else:
                logger.info("❌ Nenhuma Server Action encontrada")
        except Exception as e:
            logger.error(f"Erro ao buscar server actions: {e}")
        
        # 3. Buscar Automated Actions (base.automation) - verificar se existe
        logger.info("\n" + "="*80)
        logger.info("🤖 AUTOMATED ACTIONS")
        logger.info("="*80)
        
        try:
            # Verificar se o modelo existe
            models = odoo.search_read(
                'ir.model',
                [('model', '=', 'base.automation')],
                ['id', 'name', 'model']
            )
            
            if models:
                logger.info("✅ Modelo base.automation existe")
                
                # Buscar campos disponíveis
                fields_info = odoo.execute_kw(
                    'base.automation',
                    'fields_get',
                    [],
                    {'attributes': ['string', 'type']}
                )
                
                logger.info("\nCampos disponíveis em base.automation:")
                for field_name in ['name', 'active', 'model_id', 'trigger', 'state']:
                    if field_name in fields_info:
                        logger.info(f"   • {field_name}: {fields_info[field_name].get('string', '')}")
                
                # Buscar automated actions
                automated_actions = odoo.search_read(
                    'base.automation',
                    ['|', ('model_id.model', '=', 'sale.order'),
                          ('model_id.model', '=', 'sale.order.line')],
                    ['id', 'name', 'active', 'model_id']
                )
                
                if automated_actions:
                    logger.info(f"\n✅ Encontradas {len(automated_actions)} Automated Actions:")
                    for action in automated_actions:
                        logger.info(f"   • {action['name']} (Ativa: {'Sim' if action.get('active') else 'Não'})")
                else:
                    logger.info("❌ Nenhuma Automated Action encontrada para sale.order")
            else:
                logger.info("ℹ️ Modelo base.automation não disponível neste Odoo")
        except Exception as e:
            logger.info(f"ℹ️ base.automation não acessível: {e}")
        
        # 4. Buscar campos calculados de sale.order
        logger.info("\n" + "="*80)
        logger.info("🧮 CAMPOS CALCULADOS DE SALE.ORDER")
        logger.info("="*80)
        
        try:
            computed_fields = odoo.search_read(
                'ir.model.fields',
                [('model', '=', 'sale.order'), ('compute', '!=', False)],
                ['name', 'field_description', 'compute', 'store'],
                limit=15
            )
            
            if computed_fields:
                logger.info(f"\n✅ Principais campos calculados (impostos e totais):")
                
                # Filtrar campos importantes
                important_fields = ['amount_untaxed', 'amount_tax', 'amount_total', 
                                  'tax_totals', 'tax_totals_json']
                
                for field in computed_fields:
                    if any(imp in field['name'] for imp in ['amount', 'tax', 'total']):
                        logger.info(f"   • {field['name']}: {field['field_description']}")
                        logger.info(f"     Armazenado: {'Sim' if field.get('store') else 'Não (calculado em tempo real)'}")
        except Exception as e:
            logger.error(f"Erro ao buscar campos calculados: {e}")
        
        # 5. Buscar métodos disponíveis em sale.order
        logger.info("\n" + "="*80)
        logger.info("🔧 MÉTODOS DISPONÍVEIS EM SALE.ORDER")
        logger.info("="*80)
        
        try:
            # Buscar alguns pedidos para testar métodos
            sample_order = odoo.search_read(
                'sale.order',
                [],
                ['id', 'name'],
                limit=1
            )
            
            if sample_order:
                # Tentar listar métodos comuns
                common_methods = [
                    '_compute_amounts',
                    '_compute_tax_id', 
                    'action_confirm',
                    'action_quotation_send',
                    'action_cancel',
                    '_amount_all',
                    '_get_tax_amount_by_group'
                ]
                
                logger.info("\n📋 Métodos relacionados a impostos e cálculos:")
                for method in common_methods:
                    logger.info(f"   • {method}")
        except:
            pass
        
        # 6. Buscar informações sobre impostos em sale.order.line
        logger.info("\n" + "="*80)
        logger.info("💰 CAMPOS DE IMPOSTOS EM SALE.ORDER.LINE")
        logger.info("="*80)
        
        try:
            tax_fields = odoo.search_read(
                'ir.model.fields',
                [('model', '=', 'sale.order.line'), 
                 ('name', 'in', ['tax_id', 'price_tax', 'price_total', 'price_subtotal'])],
                ['name', 'field_description', 'relation', 'compute']
            )
            
            if tax_fields:
                logger.info("\n✅ Campos de impostos nas linhas:")
                for field in tax_fields:
                    logger.info(f"   • {field['name']}: {field['field_description']}")
                    if field.get('relation'):
                        logger.info(f"     Relacionado a: {field['relation']}")
                    if field.get('compute'):
                        logger.info(f"     Calculado por: {field['compute']}")
        except Exception as e:
            logger.error(f"Erro: {e}")
        
        # 7. Solução para aplicar impostos
        logger.info("\n" + "="*80)
        logger.info("✅ SOLUÇÃO PARA APLICAR IMPOSTOS VIA API")
        logger.info("="*80)
        
        logger.info("""
Para garantir que os impostos sejam aplicados ao criar cotações via API:

1. **Incluir tax_id nas linhas**:
   'order_line': [(0, 0, {
       'product_id': product_id,
       'tax_id': [(6, 0, [tax_ids])]  # Lista de IDs dos impostos
   })]

2. **Buscar impostos do produto**:
   produto = odoo.search_read('product.product', 
                              [('id', '=', product_id)],
                              ['taxes_id'])
   tax_ids = produto[0]['taxes_id']

3. **Aplicar posição fiscal do cliente**:
   - Buscar property_account_position_id do cliente
   - Mapear impostos usando a posição fiscal

4. **Forçar recálculo após criação**:
   odoo.execute_kw('sale.order', 'write', 
                   [[order_id], {'state': 'draft'}])

5. **Alternativa - Usar o botão de recálculo**:
   Alguns Odoo têm action_recalculate_taxes
        """)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro geral: {str(e)}")
        return None

if __name__ == "__main__":
    logger.info("🚀 Analisando configurações do Odoo...")
    logger.info("="*80)
    
    resultado = listar_acoes_servidor()
    
    if resultado:
        logger.info(f"\n✅ Análise concluída!")
    else:
        logger.error("\n❌ Falha na análise")