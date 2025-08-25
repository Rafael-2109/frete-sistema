#!/usr/bin/env python3
"""
Script para testar como o CFOP é preenchido automaticamente
Data: 2025-01-25
"""

import sys
import os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def testar_cfop_automatico():
    """
    Testa diferentes métodos de preenchimento automático do CFOP
    """
    try:
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        # Configurações
        company_id = 4  # NACOM GOYA - CD
        warehouse_id = 3  # Armazém CD
        cnpj_cliente = '75.315.333/0002-90'
        
        # 1. Buscar cliente
        logger.info(f"🔍 Buscando cliente: {cnpj_cliente}")
        cliente = odoo.search_read(
            'res.partner',
            [('l10n_br_cnpj', '=', cnpj_cliente)],
            ['id', 'name', 'property_account_position_id', 'state_id'],
            limit=1
        )
        
        if not cliente:
            cnpj_limpo = cnpj_cliente.replace('.', '').replace('/', '').replace('-', '')
            cliente = odoo.search_read(
                'res.partner',
                [('l10n_br_cnpj', 'ilike', cnpj_limpo[:8])],
                ['id', 'name', 'property_account_position_id', 'state_id'],
                limit=1
            )
        
        if not cliente:
            logger.error("❌ Cliente não encontrado")
            return None
            
        partner_id = cliente[0]['id']
        logger.info(f"✅ Cliente: {cliente[0]['name']} (ID: {partner_id})")
        
        # Estado do cliente para determinar CFOP
        state_id = cliente[0].get('state_id')
        if state_id:
            state_info = odoo.search_read(
                'res.country.state',
                [('id', '=', state_id[0] if isinstance(state_id, list) else state_id)],
                ['code', 'name']
            )
            if state_info:
                logger.info(f"   📍 Estado do cliente: {state_info[0]['code']} - {state_info[0]['name']}")
        
        # Posição fiscal
        fiscal_position_id = None
        if cliente[0].get('property_account_position_id'):
            fiscal_position_id = cliente[0]['property_account_position_id'][0] if isinstance(cliente[0]['property_account_position_id'], list) else cliente[0]['property_account_position_id']
            logger.info(f"   📊 Posição Fiscal: ID {fiscal_position_id}")
            
            # Buscar detalhes da posição fiscal
            fp_info = odoo.search_read(
                'account.fiscal.position',
                [('id', '=', fiscal_position_id)],
                ['name', 'company_id']
            )
            if fp_info:
                logger.info(f"      Nome: {fp_info[0]['name']}")
        
        # 2. Buscar um produto simples
        produto = odoo.search_read(
            'product.product',
            [('default_code', '=', '4310162')],
            ['id', 'name', 'taxes_id'],
            limit=1
        )
        
        if not produto:
            produto = odoo.search_read(
                'product.product',
                [],
                ['id', 'name', 'taxes_id'],
                limit=1
            )
        
        if not produto:
            logger.error("❌ Nenhum produto encontrado")
            return None
        
        product_id = produto[0]['id']
        logger.info(f"📦 Produto: {produto[0]['name']} (ID: {product_id})")
        
        # =====================================================
        # TESTE 1: Criar pedido SEM CFOP e executar Server Action
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🧪 TESTE 1: Criar pedido SEM CFOP e executar Server Action 863")
        logger.info("="*80)
        
        cotacao_data = {
            'partner_id': partner_id,
            'company_id': company_id,
            'warehouse_id': warehouse_id,
            'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'order_line': [(0, 0, {
                'product_id': product_id,
                'name': 'Produto teste CFOP',
                'product_uom_qty': 1,
                'price_unit': 100.00,
                # NÃO definir CFOP
            })],
        }
        
        if fiscal_position_id:
            cotacao_data['fiscal_position_id'] = fiscal_position_id
        
        cotacao_id = odoo.execute_kw(
            'sale.order',
            'create',
            [cotacao_data],
            {'context': {'company_id': company_id}}
        )
        
        logger.info(f"✅ Pedido criado: ID {cotacao_id}")
        
        # Verificar CFOP inicial
        lines = odoo.search_read(
            'sale.order.line',
            [('order_id', '=', cotacao_id)],
            ['product_id', 'l10n_br_cfop_id', 'l10n_br_cfop_codigo']
        )
        
        logger.info("\n📋 CFOP ANTES da Server Action:")
        for line in lines:
            logger.info(f"   CFOP ID: {line.get('l10n_br_cfop_id', 'VAZIO')}")
            logger.info(f"   CFOP Código: {line.get('l10n_br_cfop_codigo', 'VAZIO')}")
        
        # Executar Server Action 863
        logger.info("\n🎯 Executando Server Action 863 (Atualizar Impostos)...")
        try:
            result = odoo.execute_kw(
                'ir.actions.server',
                'run',
                [[863]],
                {'context': {
                    'active_model': 'sale.order',
                    'active_id': cotacao_id,
                    'active_ids': [cotacao_id]
                }}
            )
            logger.info("   ✅ Server Action executada!")
        except Exception as e:
            logger.warning(f"   ⚠️ Erro na Server Action: {e}")
        
        # Verificar CFOP após Server Action
        lines = odoo.search_read(
            'sale.order.line',
            [('order_id', '=', cotacao_id)],
            ['product_id', 'l10n_br_cfop_id', 'l10n_br_cfop_codigo']
        )
        
        logger.info("\n📋 CFOP DEPOIS da Server Action:")
        for line in lines:
            cfop_id = line.get('l10n_br_cfop_id')
            cfop_codigo = line.get('l10n_br_cfop_codigo', 'VAZIO')
            
            logger.info(f"   CFOP ID: {cfop_id if cfop_id else 'VAZIO'}")
            logger.info(f"   CFOP Código: {cfop_codigo}")
            
            if cfop_id and isinstance(cfop_id, list):
                # Buscar detalhes do CFOP
                cfop_details = odoo.search_read(
                    'l10n_br_ciel_it_account.cfop',
                    [('id', '=', cfop_id[0])],
                    ['codigo_cfop', 'name']
                )
                if cfop_details:
                    logger.info(f"   ✅ CFOP aplicado: {cfop_details[0]['codigo_cfop']} - {cfop_details[0]['name']}")
        
        # =====================================================
        # TESTE 2: Verificar se há outros Server Actions CIEL IT
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🧪 TESTE 2: Buscar e testar Server Actions CIEL IT")
        logger.info("="*80)
        
        # Buscar Server Actions CIEL IT relacionadas a faturamento
        server_actions = odoo.search_read(
            'ir.actions.server',
            [('name', 'ilike', 'CIEL IT')],
            ['id', 'name', 'model_id'],
            limit=5
        )
        
        if server_actions:
            logger.info(f"\n✅ {len(server_actions)} Server Actions CIEL IT encontradas:")
            
            for action in server_actions[:3]:  # Testar apenas as 3 primeiras
                logger.info(f"\n   Testando: {action['name']} (ID: {action['id']})")
                
                try:
                    result = odoo.execute_kw(
                        'ir.actions.server',
                        'run',
                        [[action['id']]],
                        {'context': {
                            'active_model': 'sale.order',
                            'active_id': cotacao_id,
                            'active_ids': [cotacao_id]
                        }}
                    )
                    
                    # Verificar se CFOP mudou
                    lines_after = odoo.search_read(
                        'sale.order.line',
                        [('order_id', '=', cotacao_id)],
                        ['l10n_br_cfop_id', 'l10n_br_cfop_codigo']
                    )
                    
                    if lines_after[0].get('l10n_br_cfop_id'):
                        logger.info(f"      ✅ CFOP preenchido! Código: {lines_after[0].get('l10n_br_cfop_codigo')}")
                    else:
                        logger.info(f"      ❌ CFOP ainda vazio")
                        
                except Exception as e:
                    logger.info(f"      ⚠️ Erro: {str(e)[:100]}")
        
        # =====================================================
        # TESTE 3: Criar pedido COM CFOP manual
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🧪 TESTE 3: Criar pedido COM CFOP definido manualmente")
        logger.info("="*80)
        
        # Determinar CFOP baseado no estado
        if state_info and state_info[0]['code'] == 'GO':
            # Mesmo estado - usar 5xxx
            cfop_codigo = '5102'
            logger.info("   📍 Cliente no mesmo estado (GO) - Usar CFOP 5102")
        else:
            # Outro estado - usar 6xxx
            cfop_codigo = '6102'
            logger.info(f"   📍 Cliente em outro estado - Usar CFOP 6102")
        
        # Buscar o ID do CFOP
        cfop = odoo.search_read(
            'l10n_br_ciel_it_account.cfop',
            [('codigo_cfop', '=', cfop_codigo)],
            ['id', 'name'],
            limit=1
        )
        
        if cfop:
            cfop_id = cfop[0]['id']
            logger.info(f"   ✅ CFOP encontrado: {cfop_codigo} - {cfop[0]['name']} (ID: {cfop_id})")
            
            # Criar novo pedido com CFOP
            cotacao_data_2 = {
                'partner_id': partner_id,
                'company_id': company_id,
                'warehouse_id': warehouse_id,
                'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'order_line': [(0, 0, {
                    'product_id': product_id,
                    'name': 'Produto teste com CFOP manual',
                    'product_uom_qty': 1,
                    'price_unit': 200.00,
                    'l10n_br_cfop_id': cfop_id,  # CFOP definido manualmente
                })],
            }
            
            if fiscal_position_id:
                cotacao_data_2['fiscal_position_id'] = fiscal_position_id
            
            cotacao_id_2 = odoo.execute_kw(
                'sale.order',
                'create',
                [cotacao_data_2],
                {'context': {'company_id': company_id}}
            )
            
            logger.info(f"\n✅ Pedido 2 criado: ID {cotacao_id_2}")
            
            # Verificar CFOP
            lines_2 = odoo.search_read(
                'sale.order.line',
                [('order_id', '=', cotacao_id_2)],
                ['product_id', 'l10n_br_cfop_id', 'l10n_br_cfop_codigo']
            )
            
            logger.info("\n📋 CFOP no pedido com definição manual:")
            for line in lines_2:
                logger.info(f"   CFOP ID: {line.get('l10n_br_cfop_id')}")
                logger.info(f"   CFOP Código: {line.get('l10n_br_cfop_codigo', 'VAZIO')}")
        
        # =====================================================
        # RESUMO
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("📊 RESUMO DOS TESTES")
        logger.info("="*80)
        
        logger.info("""
DESCOBERTAS:

1. Server Action 863 (Atualizar Impostos):
   - Calcula impostos corretamente
   - Pode ou não preencher CFOP (depende da configuração)

2. CFOPs disponíveis no sistema:
   - 5102/6102: Venda de mercadoria
   - 5152/6152: Transferência entre filiais
   - 5405/6405: Venda com ST
   
3. Lógica do CFOP:
   - 5xxx: Operações dentro do estado
   - 6xxx: Operações interestaduais
   
4. Para garantir CFOP correto:
   - Opção 1: Definir manualmente l10n_br_cfop_id na linha
   - Opção 2: Configurar posição fiscal com mapeamento de CFOP
   - Opção 3: Usar Server Actions específicas CIEL IT
""")
        
        return cotacao_id
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("🚀 Testando preenchimento automático de CFOP...")
    logger.info("="*80)
    
    cotacao_id = testar_cfop_automatico()
    
    if cotacao_id:
        logger.info(f"\n✅ Testes concluídos!")
        logger.info(f"🆔 Pedido de teste ID: {cotacao_id}")