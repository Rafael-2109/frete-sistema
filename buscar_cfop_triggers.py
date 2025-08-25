#!/usr/bin/env python3
"""
Script para descobrir como o CFOP é preenchido no Odoo
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

# 1. Verificar campos CFOP em sale.order.line
logger.info("\n" + "="*80)
logger.info("🔍 CAMPOS CFOP EM SALE.ORDER.LINE")
logger.info("="*80)

try:
    fields = odoo.execute_kw(
        'sale.order.line',
        'fields_get',
        [],
        {'attributes': ['string', 'type', 'relation', 'compute', 'depends']}
    )
    
    logger.info("\nCampos relacionados a CFOP:")
    for field_name, field_info in fields.items():
        if 'cfop' in field_name.lower() or 'fiscal' in field_name.lower():
            logger.info(f"\n   • {field_name}:")
            logger.info(f"     Descrição: {field_info.get('string', '')}")
            logger.info(f"     Tipo: {field_info.get('type', '')}")
            if field_info.get('relation'):
                logger.info(f"     Modelo relacionado: {field_info.get('relation')}")
            if field_info.get('compute'):
                logger.info(f"     Campo calculado: {field_info.get('compute')}")
            if field_info.get('depends'):
                logger.info(f"     Depende de: {field_info.get('depends')}")
except Exception as e:
    logger.error(f"Erro: {e}")

# 2. Buscar Server Actions relacionadas a CFOP
logger.info("\n" + "="*80)
logger.info("🎯 SERVER ACTIONS RELACIONADAS A CFOP/FISCAL")
logger.info("="*80)

try:
    server_actions = odoo.search_read(
        'ir.actions.server',
        ['|', '|', 
         ('code', 'ilike', 'cfop'),
         ('code', 'ilike', 'fiscal'),
         ('name', 'ilike', 'fiscal')],
        ['id', 'name', 'state', 'code', 'model_id']
    )
    
    if server_actions:
        logger.info(f"\n✅ {len(server_actions)} Server Actions encontradas:")
        for action in server_actions:
            logger.info(f"\n   {action['name']} (ID: {action['id']})")
            if action.get('code'):
                # Mostrar se menciona CFOP
                if 'cfop' in action['code'].lower():
                    logger.info(f"     ⭐ Contém código CFOP!")
                    code_lines = [l for l in action['code'].split('\n') if 'cfop' in l.lower()][:3]
                    for line in code_lines:
                        logger.info(f"       {line.strip()[:80]}")
except Exception as e:
    logger.error(f"Erro: {e}")

# 3. Buscar CFOPs disponíveis
logger.info("\n" + "="*80)
logger.info("📋 CFOPS DISPONÍVEIS (l10n_br.cfop)")
logger.info("="*80)

try:
    cfops = odoo.search_read(
        'l10n_br.cfop',
        [],
        ['id', 'code', 'name', 'type', 'destination', 'state_from', 'state_to'],
        limit=20
    )
    
    if cfops:
        logger.info(f"\n✅ Exemplos de CFOPs cadastrados:")
        logger.info("-"*80)
        
        # Agrupar por tipo
        cfops_saida = [c for c in cfops if c.get('type') == 'output' or (c.get('code', '').startswith('5') or c.get('code', '').startswith('6'))]
        cfops_entrada = [c for c in cfops if c.get('type') == 'input' or (c.get('code', '').startswith('1') or c.get('code', '').startswith('2'))]
        
        if cfops_saida:
            logger.info("\n📤 CFOPs de SAÍDA (vendas):")
            for cfop in cfops_saida[:10]:
                logger.info(f"   • {cfop['code']} - {cfop['name'][:60]}")
                if cfop.get('destination'):
                    logger.info(f"     Destino: {cfop['destination']}")
        
        if cfops_entrada:
            logger.info("\n📥 CFOPs de ENTRADA (compras):")
            for cfop in cfops_entrada[:5]:
                logger.info(f"   • {cfop['code']} - {cfop['name'][:60]}")
    else:
        logger.info("❌ Nenhum CFOP encontrado")
except Exception as e:
    logger.info(f"ℹ️ Modelo l10n_br.cfop não disponível: {e}")

# 4. Verificar operações fiscais
logger.info("\n" + "="*80)
logger.info("🏭 OPERAÇÕES FISCAIS (l10n_br.fiscal.operation)")
logger.info("="*80)

try:
    operations = odoo.search_read(
        'l10n_br.fiscal.operation',
        [],
        ['id', 'name', 'code', 'fiscal_operation_type', 'default_cfop_id'],
        limit=10
    )
    
    if operations:
        logger.info(f"\n✅ Operações Fiscais encontradas:")
        for op in operations:
            logger.info(f"\n   • {op['name']} (ID: {op['id']})")
            logger.info(f"     Código: {op.get('code', 'N/A')}")
            logger.info(f"     Tipo: {op.get('fiscal_operation_type', 'N/A')}")
            if op.get('default_cfop_id'):
                logger.info(f"     CFOP padrão: {op['default_cfop_id']}")
except Exception as e:
    logger.info(f"ℹ️ Modelo l10n_br.fiscal.operation não disponível: {e}")

# 5. Verificar como o CFOP é determinado em pedidos existentes
logger.info("\n" + "="*80)
logger.info("🔍 ANALISANDO PEDIDOS EXISTENTES")
logger.info("="*80)

try:
    # Buscar pedidos com linhas que tenham CFOP
    order_lines = odoo.search_read(
        'sale.order.line',
        [('l10n_br_cfop_id', '!=', False)],
        ['order_id', 'product_id', 'l10n_br_cfop_id', 'fiscal_operation_id', 
         'fiscal_operation_line_id', 'fiscal_position_id'],
        limit=5
    )
    
    if order_lines:
        logger.info(f"\n✅ Exemplos de linhas com CFOP preenchido:")
        for line in order_lines:
            logger.info(f"\n   Pedido: {line.get('order_id', ['', ''])[1] if line.get('order_id') else 'N/A'}")
            logger.info(f"   Produto: {line.get('product_id', ['', ''])[1] if line.get('product_id') else 'N/A'}")
            logger.info(f"   CFOP: {line.get('l10n_br_cfop_id', ['', ''])[1] if line.get('l10n_br_cfop_id') else 'N/A'}")
            
            if line.get('fiscal_operation_id'):
                logger.info(f"   Operação Fiscal: {line['fiscal_operation_id'][1]}")
            if line.get('fiscal_position_id'):
                logger.info(f"   Posição Fiscal: {line['fiscal_position_id'][1]}")
    else:
        logger.info("❌ Nenhuma linha com CFOP encontrada")
except Exception as e:
    logger.info(f"Erro ao buscar linhas: {e}")

# 6. Verificar mapeamento de CFOP na posição fiscal
logger.info("\n" + "="*80)
logger.info("🗺️ MAPEAMENTO DE CFOP NA POSIÇÃO FISCAL")
logger.info("="*80)

try:
    # Buscar posição fiscal de transferência
    fiscal_positions = odoo.search_read(
        'account.fiscal.position',
        [('name', 'ilike', 'transfer')],
        ['id', 'name', 'company_id'],
        limit=5
    )
    
    if fiscal_positions:
        for fp in fiscal_positions:
            logger.info(f"\n📊 Posição Fiscal: {fp['name']} (ID: {fp['id']})")
            
            # Buscar mapeamentos de CFOP desta posição
            try:
                # Tentar buscar mapeamentos de operação fiscal
                mappings = odoo.search_read(
                    'l10n_br.fiscal.operation.line',
                    [('fiscal_position_id', '=', fp['id'])],
                    ['fiscal_operation_id', 'cfop_id'],
                    limit=5
                )
                
                if mappings:
                    logger.info("   Mapeamentos de CFOP:")
                    for m in mappings:
                        logger.info(f"     • Operação: {m.get('fiscal_operation_id', 'N/A')}")
                        logger.info(f"       CFOP: {m.get('cfop_id', 'N/A')}")
            except:
                pass
except Exception as e:
    logger.info(f"Erro: {e}")

# 7. Buscar métodos relacionados
logger.info("\n" + "="*80)
logger.info("🔧 MÉTODOS PARA CALCULAR CFOP")
logger.info("="*80)

logger.info("""
Métodos comuns no Odoo Brasil para CFOP:

1. **_compute_l10n_br_cfop()** - Calcula CFOP baseado na operação fiscal
2. **_onchange_fiscal_operation_id()** - Atualiza CFOP quando muda operação
3. **_fiscal_operation_map()** - Mapeia operação fiscal para CFOP
4. **onchange_l10n_br_calcular_imposto()** - Calcula impostos E CFOP

Para acionar o cálculo de CFOP:
- Definir fiscal_operation_id ou fiscal_operation_line_id na linha
- Executar Server Action de cálculo fiscal (ID 863)
- Definir a posição fiscal correta no pedido
""")