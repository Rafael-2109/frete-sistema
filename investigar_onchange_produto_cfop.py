#!/usr/bin/env python3
"""
Script para investigar como o CFOP é preenchido ao selecionar um produto
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

# 1. Buscar métodos relacionados a onchange de produto
logger.info("\n" + "="*80)
logger.info("🔍 INVESTIGANDO ONCHANGE DE PRODUTO EM SALE.ORDER.LINE")
logger.info("="*80)

try:
    # Buscar todos os campos de sale.order.line
    fields = odoo.execute_kw(
        'sale.order.line',
        'fields_get',
        [],
        {'attributes': ['string', 'type', 'depends', 'compute', 'inverse']}
    )
    
    logger.info("\n📋 Campos relacionados a produto e CFOP:")
    logger.info("-"*80)
    
    # Campos importantes
    campos_interesse = ['product_id', 'l10n_br_cfop_id', 'l10n_br_cfop_codigo', 
                       'fiscal_position_id', 'tax_id']
    
    for field_name in campos_interesse:
        if field_name in fields:
            field_info = fields[field_name]
            logger.info(f"\n• {field_name}:")
            logger.info(f"  Descrição: {field_info.get('string', '')}")
            logger.info(f"  Tipo: {field_info.get('type', '')}")
            if field_info.get('depends'):
                logger.info(f"  Depende de: {field_info.get('depends')}")
            if field_info.get('compute'):
                logger.info(f"  Campo calculado: {field_info.get('compute')}")
            if field_info.get('inverse'):
                logger.info(f"  Inverse: {field_info.get('inverse')}")
                
except Exception as e:
    logger.error(f"Erro: {e}")

# 2. Verificar se existe método onchange_product_id
logger.info("\n" + "="*80)
logger.info("🔍 VERIFICANDO MÉTODOS ONCHANGE")
logger.info("="*80)

try:
    # Listar métodos disponíveis
    logger.info("\nMétodos que podem estar relacionados ao preenchimento do CFOP:")
    logger.info("""
    Possíveis métodos no Odoo Brasil:
    - _onchange_product_id() 
    - _onchange_product_id_fiscal()
    - _compute_l10n_br_cfop()
    - _compute_fiscal_operation()
    - product_id_change()
    """)
    
except Exception as e:
    logger.error(f"Erro: {e}")

# 3. Analisar posições fiscais
logger.info("\n" + "="*80)
logger.info("📊 ANALISANDO POSIÇÕES FISCAIS E MAPEAMENTO DE CFOP")
logger.info("="*80)

try:
    # Buscar posições fiscais
    fiscal_positions = odoo.search_read(
        'account.fiscal.position',
        [],
        ['id', 'name', 'company_id'],
        limit=20
    )
    
    if fiscal_positions:
        logger.info(f"\n✅ {len(fiscal_positions)} Posições Fiscais encontradas:")
        
        # Focar em ZFM e ST
        for fp in fiscal_positions:
            name = fp['name'].upper()
            if any(term in name for term in ['ZFM', 'MANAUS', 'ST', 'SUBSTITUIÇÃO', 'SUBSTITUICAO']):
                logger.info(f"\n⭐ {fp['name']} (ID: {fp['id']})")
                
                # Tentar buscar mapeamento de impostos
                tax_mappings = odoo.search_read(
                    'account.fiscal.position.tax',
                    [('position_id', '=', fp['id'])],
                    ['tax_src_id', 'tax_dest_id'],
                    limit=5
                )
                
                if tax_mappings:
                    logger.info(f"   Mapeamentos de impostos: {len(tax_mappings)}")
                
except Exception as e:
    logger.error(f"Erro: {e}")

# 4. Testar criação de pedido simulando onchange
logger.info("\n" + "="*80)
logger.info("🧪 TESTANDO CRIAÇÃO COM DIFERENTES CLIENTES")
logger.info("="*80)

try:
    # Buscar clientes com diferentes características
    clientes_teste = [
        {'desc': 'Cliente ZFM', 'search': [('name', 'ilike', 'manaus')]},
        {'desc': 'Cliente com ST', 'search': [('l10n_br_cnpj', '=', '75.315.333/0002-90')]},
        {'desc': 'Cliente normal', 'search': [('customer_rank', '>', 0)]},
    ]
    
    for cliente_config in clientes_teste[:2]:  # Testar apenas 2
        cliente = odoo.search_read(
            'res.partner',
            cliente_config['search'],
            ['id', 'name', 'property_account_position_id', 'state_id', 'city'],
            limit=1
        )
        
        if cliente:
            logger.info(f"\n📍 {cliente_config['desc']}: {cliente[0]['name']}")
            
            # Estado e cidade
            if cliente[0].get('state_id'):
                logger.info(f"   Estado: {cliente[0]['state_id'][1] if isinstance(cliente[0]['state_id'], list) else 'N/A'}")
            if cliente[0].get('city'):
                logger.info(f"   Cidade: {cliente[0]['city']}")
            
            # Posição fiscal
            if cliente[0].get('property_account_position_id'):
                fp_id = cliente[0]['property_account_position_id'][0] if isinstance(cliente[0]['property_account_position_id'], list) else cliente[0]['property_account_position_id']
                logger.info(f"   Posição Fiscal: {cliente[0]['property_account_position_id'][1] if isinstance(cliente[0]['property_account_position_id'], list) else 'ID: ' + str(fp_id)}")
                
                # Buscar detalhes da posição fiscal
                fp_details = odoo.search_read(
                    'account.fiscal.position',
                    [('id', '=', fp_id)],
                    ['name', 'note']
                )
                if fp_details and fp_details[0].get('note'):
                    logger.info(f"   Observações FP: {fp_details[0]['note'][:100]}")
            else:
                logger.info("   Sem posição fiscal definida")
                
except Exception as e:
    logger.error(f"Erro: {e}")

# 5. Buscar produtos e seus impostos padrão
logger.info("\n" + "="*80)
logger.info("📦 ANALISANDO PRODUTOS E SEUS IMPOSTOS/CFOP PADRÃO")
logger.info("="*80)

try:
    # Buscar alguns produtos
    produtos = odoo.search_read(
        'product.product',
        [('sale_ok', '=', True)],
        ['id', 'name', 'default_code', 'taxes_id', 'supplier_taxes_id'],
        limit=5
    )
    
    for produto in produtos[:3]:
        logger.info(f"\n📦 {produto['name'][:50]} (Código: {produto.get('default_code', 'N/A')})")
        
        if produto.get('taxes_id'):
            logger.info(f"   Impostos de venda: {len(produto['taxes_id'])} impostos")
            
            # Buscar detalhes dos impostos
            for tax_id in produto['taxes_id'][:2]:
                tax = odoo.search_read(
                    'account.tax',
                    [('id', '=', tax_id)],
                    ['name', 'amount', 'type_tax_use', 'description']
                )
                if tax:
                    logger.info(f"     • {tax[0]['name']} ({tax[0]['amount']}%)")
                    
except Exception as e:
    logger.error(f"Erro: {e}")

# 6. Simular o processo completo
logger.info("\n" + "="*80)
logger.info("🎯 SIMULANDO PROCESSO COMPLETO DE CRIAÇÃO")
logger.info("="*80)

try:
    # Pegar um cliente e produto específicos
    cliente = odoo.search_read(
        'res.partner',
        [('l10n_br_cnpj', '=', '75.315.333/0002-90')],
        ['id', 'name', 'property_account_position_id'],
        limit=1
    )
    
    produto = odoo.search_read(
        'product.product',
        [('default_code', '=', '4310162')],
        ['id', 'name', 'taxes_id'],
        limit=1
    )
    
    if cliente and produto:
        logger.info(f"Cliente: {cliente[0]['name']}")
        logger.info(f"Produto: {produto[0]['name']}")
        
        # Criar pedido COM posição fiscal
        fiscal_position_id = None
        if cliente[0].get('property_account_position_id'):
            fiscal_position_id = cliente[0]['property_account_position_id'][0] if isinstance(cliente[0]['property_account_position_id'], list) else cliente[0]['property_account_position_id']
            logger.info(f"Posição Fiscal: ID {fiscal_position_id}")
        
        # Criar pedido
        order_data = {
            'partner_id': cliente[0]['id'],
            'company_id': 4,  # NACOM GOYA - CD
        }
        
        if fiscal_position_id:
            order_data['fiscal_position_id'] = fiscal_position_id
            
        order_id = odoo.execute_kw(
            'sale.order',
            'create',
            [order_data]
        )
        
        logger.info(f"\nPedido criado: ID {order_id}")
        
        # Agora adicionar linha COM tax_id do produto
        line_data = {
            'order_id': order_id,
            'product_id': produto[0]['id'],
            'product_uom_qty': 1,
            'price_unit': 100.00,
        }
        
        # Adicionar impostos do produto
        if produto[0].get('taxes_id'):
            line_data['tax_id'] = [(6, 0, produto[0]['taxes_id'])]
            logger.info(f"Impostos do produto adicionados: {produto[0]['taxes_id']}")
        
        line_id = odoo.execute_kw(
            'sale.order.line',
            'create',
            [line_data]
        )
        
        logger.info(f"Linha criada: ID {line_id}")
        
        # Verificar CFOP
        line = odoo.search_read(
            'sale.order.line',
            [('id', '=', line_id)],
            ['product_id', 'l10n_br_cfop_id', 'l10n_br_cfop_codigo', 'tax_id']
        )
        
        if line:
            logger.info("\n📋 Resultado:")
            logger.info(f"   CFOP ID: {line[0].get('l10n_br_cfop_id', 'VAZIO')}")
            logger.info(f"   CFOP Código: {line[0].get('l10n_br_cfop_codigo', 'VAZIO')}")
            logger.info(f"   Impostos: {len(line[0].get('tax_id', []))} impostos")
            
            # Se não tem CFOP, tentar método write para forçar onchange
            if not line[0].get('l10n_br_cfop_id'):
                logger.info("\n🔄 Tentando forçar recálculo via write...")
                
                # Fazer um update dummy para forçar onchange
                odoo.execute_kw(
                    'sale.order.line',
                    'write',
                    [[line_id], {'product_uom_qty': 1}]
                )
                
                # Verificar novamente
                line = odoo.search_read(
                    'sale.order.line',
                    [('id', '=', line_id)],
                    ['l10n_br_cfop_id', 'l10n_br_cfop_codigo']
                )
                
                if line:
                    logger.info(f"   CFOP após write: {line[0].get('l10n_br_cfop_codigo', 'AINDA VAZIO')}")
                    
except Exception as e:
    logger.error(f"Erro: {e}")

logger.info("\n" + "="*80)
logger.info("💡 CONCLUSÕES")
logger.info("="*80)
logger.info("""
O CFOP é preenchido através de:

1. **Onchange do produto** (interface web):
   - Ao selecionar produto, o Odoo executa _onchange_product_id()
   - Este método considera a posição fiscal do cliente
   - Aplica regras baseadas em ZFM, ST, estado do cliente, etc.

2. **Via API (XML-RPC)**:
   - Onchange NÃO funciona automaticamente via API
   - Precisamos simular o comportamento do onchange manualmente
   - Ou executar uma Server Action que faça isso

3. **Regras de CFOP**:
   - ZFM (Zona Franca de Manaus): CFOPs específicos (6109, 6110)
   - ST (Substituição Tributária): CFOPs 5405/6405
   - Mesmo estado: 5xxx
   - Estados diferentes: 6xxx

4. **Solução**:
   - Determinar a posição fiscal correta do cliente
   - Aplicar a lógica de CFOP baseada nas regras
   - Ou criar uma Server Action customizada que execute o onchange
""")