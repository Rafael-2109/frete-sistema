#!/usr/bin/env python3
"""
Script para buscar CFOPs no modelo customizado CIEL IT
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

# 1. Buscar CFOPs disponíveis no modelo CIEL IT
logger.info("\n" + "="*80)
logger.info("📋 CFOPS DISPONÍVEIS (l10n_br_ciel_it_account.cfop)")
logger.info("="*80)

try:
    cfops = odoo.search_read(
        'l10n_br_ciel_it_account.cfop',
        [],
        ['id', 'codigo_cfop', 'descricao_cfop', 'tipo_cfop'],
        limit=30
    )
    
    if cfops:
        logger.info(f"\n✅ {len(cfops)} CFOPs encontrados:")
        
        # Separar por tipo
        cfops_saida = []
        cfops_entrada = []
        cfops_transferencia = []
        
        for cfop in cfops:
            codigo = cfop.get('codigo_cfop', '')
            
            # Classificar por código
            if codigo.startswith('5') or codigo.startswith('6'):
                cfops_saida.append(cfop)
            elif codigo.startswith('1') or codigo.startswith('2'):
                cfops_entrada.append(cfop)
            
            # Verificar se é transferência
            if 'TRANSF' in str(cfop.get('descricao_cfop', '')).upper():
                cfops_transferencia.append(cfop)
        
        if cfops_transferencia:
            logger.info("\n🔄 CFOPs de TRANSFERÊNCIA:")
            for cfop in cfops_transferencia:
                logger.info(f"   • ID: {cfop['id']:3} | {cfop.get('codigo_cfop', 'N/A'):6} - {cfop.get('descricao_cfop', 'N/A')[:60]}")
                logger.info(f"     ⭐ CFOP para transferência entre filiais")
        
        if cfops_saida:
            logger.info("\n📤 CFOPs de SAÍDA (5xxx/6xxx):")
            for cfop in cfops_saida[:10]:
                logger.info(f"   • ID: {cfop['id']:3} | {cfop.get('codigo_cfop', 'N/A'):6} - {cfop.get('descricao_cfop', 'N/A')[:60]}")
        
        if cfops_entrada:
            logger.info("\n📥 CFOPs de ENTRADA (1xxx/2xxx):")
            for cfop in cfops_entrada[:10]:
                logger.info(f"   • ID: {cfop['id']:3} | {cfop.get('codigo_cfop', 'N/A'):6} - {cfop.get('descricao_cfop', 'N/A')[:60]}")
        
        # Buscar CFOPs mais comuns
        cfops_comuns = ['5102', '5405', '5152', '6102', '6405', '6152', '5409', '6409']
        logger.info("\n⭐ CFOPs COMUNS para vendas/transferências:")
        for codigo in cfops_comuns:
            cfop_found = [c for c in cfops if c.get('codigo_cfop') == codigo]
            if cfop_found:
                cfop = cfop_found[0]
                logger.info(f"   • {cfop.get('codigo_cfop')} - {cfop.get('descricao_cfop', 'N/A')[:60]} (ID: {cfop['id']})")
                
except Exception as e:
    logger.error(f"Erro: {e}")

# 2. Verificar linhas de pedidos existentes com CFOP
logger.info("\n" + "="*80)
logger.info("🔍 VERIFICANDO PEDIDOS COM CFOP PREENCHIDO")
logger.info("="*80)

try:
    # Buscar linhas com CFOP
    lines = odoo.search_read(
        'sale.order.line',
        [('l10n_br_cfop_id', '!=', False)],
        ['order_id', 'product_id', 'l10n_br_cfop_id', 'l10n_br_cfop_codigo'],
        limit=10
    )
    
    if lines:
        logger.info(f"\n✅ Exemplos de linhas com CFOP:")
        for line in lines:
            pedido = line.get('order_id', ['', ''])[1] if line.get('order_id') else 'N/A'
            produto = line.get('product_id', ['', ''])[1] if line.get('product_id') else 'N/A'
            cfop_nome = line.get('l10n_br_cfop_id', ['', ''])[1] if line.get('l10n_br_cfop_id') else 'N/A'
            cfop_codigo = line.get('l10n_br_cfop_codigo', 'N/A')
            
            logger.info(f"\n   Pedido: {pedido}")
            logger.info(f"   Produto: {produto[:50]}")
            logger.info(f"   CFOP: {cfop_codigo} - {cfop_nome}")
    else:
        logger.info("❌ Nenhuma linha com CFOP encontrada")
        
except Exception as e:
    logger.error(f"Erro: {e}")

# 3. Verificar se há método para calcular CFOP
logger.info("\n" + "="*80)
logger.info("🔧 COMO DEFINIR O CFOP")
logger.info("="*80)

logger.info("""
Para definir o CFOP em uma linha de pedido:

1. **Direto na criação da linha**:
   'order_line': [(0, 0, {
       'product_id': product_id,
       'l10n_br_cfop_id': cfop_id,  # ID do CFOP
       'l10n_br_cfop_codigo': '5102',  # Código do CFOP
   })]

2. **Após criar o pedido**:
   - Executar Server Action ID 863 (Atualizar Impostos)
   - Esta action pode calcular o CFOP baseado na posição fiscal

3. **CFOPs comuns**:
   - 5102/6102: Venda de mercadoria
   - 5405/6405: Venda de mercadoria (ST)
   - 5152/6152: Transferência entre filiais
   - 5409/6409: Transferência (ST)

4. **Para transferência entre filiais CD**:
   - Usar CFOP 5152 ou 6152 dependendo do estado
   - A posição fiscal "SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS" pode mapear automaticamente
""")