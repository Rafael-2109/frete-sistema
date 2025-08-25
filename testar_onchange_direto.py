#!/usr/bin/env python3
"""
Script para testar como chamar o onchange do produto diretamente via API
Data: 2025-01-25
"""

import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def testar_onchange_direto():
    """
    Tenta chamar o método onchange diretamente no Odoo
    """
    try:
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        # Configurações
        company_id = 4  # NACOM GOYA - CD
        warehouse_id = 3
        cnpj_cliente = '75.315.333/0002-90'  # ATACADAO MS
        
        # 1. Buscar cliente
        logger.info(f"🔍 Buscando cliente: {cnpj_cliente}")
        cliente = odoo.search_read(
            'res.partner',
            [('l10n_br_cnpj', '=', cnpj_cliente)],
            ['id', 'name', 'property_account_position_id'],
            limit=1
        )
        
        if not cliente:
            cnpj_limpo = cnpj_cliente.replace('.', '').replace('/', '').replace('-', '')
            cliente = odoo.search_read(
                'res.partner',
                [('l10n_br_cnpj', 'ilike', cnpj_limpo[:8])],
                ['id', 'name', 'property_account_position_id'],
                limit=1
            )
        
        if not cliente:
            logger.error("❌ Cliente não encontrado")
            return None
            
        partner_id = cliente[0]['id']
        logger.info(f"✅ Cliente: {cliente[0]['name']} (ID: {partner_id})")
        
        fiscal_position_id = None
        if cliente[0].get('property_account_position_id'):
            fiscal_position_id = cliente[0]['property_account_position_id'][0] if isinstance(cliente[0]['property_account_position_id'], list) else cliente[0]['property_account_position_id']
            logger.info(f"   📊 Posição Fiscal: ID {fiscal_position_id}")
        
        # 2. Buscar produto
        produto = odoo.search_read(
            'product.product',
            [('default_code', '=', '4310162')],
            ['id', 'name'],
            limit=1
        )
        
        if not produto:
            logger.error("❌ Produto não encontrado")
            return None
        
        product_id = produto[0]['id']
        logger.info(f"📦 Produto: {produto[0]['name']} (ID: {product_id})")
        
        # =====================================================
        # TESTE 1: Tentar chamar onchange diretamente
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🧪 TESTE 1: Chamar onchange diretamente via execute_kw")
        logger.info("="*80)
        
        # Primeiro criar um pedido base
        order_data = {
            'partner_id': partner_id,
            'company_id': company_id,
            'warehouse_id': warehouse_id,
        }
        
        if fiscal_position_id:
            order_data['fiscal_position_id'] = fiscal_position_id
        
        order_id = odoo.execute_kw(
            'sale.order',
            'create',
            [order_data]
        )
        
        logger.info(f"✅ Pedido base criado: ID {order_id}")
        
        # Preparar dados para o onchange
        logger.info("\n🔄 Tentando chamar onchange do produto...")
        
        # Valores atuais da linha (simulando uma linha nova)
        line_values = {
            'order_id': order_id,
            'product_id': product_id,
            'product_uom_qty': 1,
            'price_unit': 0,
            'name': '',
            'tax_id': [[6, False, []]],
            'l10n_br_cfop_id': False,
            'l10n_br_cfop_codigo': False,
        }
        
        # Tentar diferentes formas de chamar onchange
        
        # Método 1: Usando onchange diretamente
        logger.info("\n📌 Método 1: Chamando onchange diretamente...")
        try:
            result = odoo.execute_kw(
                'sale.order.line',
                'onchange',
                [[], line_values, 'product_id', {'product_id': product_id}]
            )
            logger.info(f"   Resultado: {result}")
            
            if result and result.get('value'):
                logger.info("   ✅ Onchange retornou valores!")
                for key, value in result['value'].items():
                    if 'cfop' in key.lower():
                        logger.info(f"      {key}: {value}")
        except Exception as e:
            logger.warning(f"   ❌ Erro: {str(e)[:200]}")
        
        # Método 2: Usando fields_view_get para obter onchange
        logger.info("\n📌 Método 2: Verificando onchange via fields_view_get...")
        try:
            view_info = odoo.execute_kw(
                'sale.order.line',
                'fields_view_get',
                [],
                {'view_type': 'form'}
            )
            
            # Procurar por onchange no campo product_id
            if 'fields' in view_info and 'product_id' in view_info['fields']:
                field_info = view_info['fields']['product_id']
                if 'on_change' in field_info:
                    logger.info(f"   ✅ Onchange encontrado para product_id!")
                    logger.info(f"      {field_info['on_change']}")
        except Exception as e:
            logger.warning(f"   ❌ Erro: {str(e)[:200]}")
        
        # Método 3: Criar linha e depois atualizar produto
        logger.info("\n📌 Método 3: Criar linha vazia e atualizar produto...")
        try:
            # Criar linha vazia
            line_id = odoo.execute_kw(
                'sale.order.line',
                'create',
                [{
                    'order_id': order_id,
                    'product_id': False,
                    'name': 'Linha teste',
                    'product_uom_qty': 1,
                    'price_unit': 100,
                }]
            )
            logger.info(f"   Linha criada: ID {line_id}")
            
            # Atualizar com produto (pode disparar onchange)
            odoo.execute_kw(
                'sale.order.line',
                'write',
                [[line_id], {'product_id': product_id}]
            )
            logger.info("   Produto atualizado via write")
            
            # Verificar CFOP
            line = odoo.search_read(
                'sale.order.line',
                [('id', '=', line_id)],
                ['l10n_br_cfop_id', 'l10n_br_cfop_codigo', 'name', 'price_unit']
            )[0]
            
            logger.info(f"   CFOP após write: {line.get('l10n_br_cfop_codigo', 'VAZIO')}")
            logger.info(f"   Nome: {line.get('name', 'VAZIO')}")
            logger.info(f"   Preço: {line.get('price_unit', 0)}")
            
        except Exception as e:
            logger.warning(f"   ❌ Erro: {str(e)[:200]}")
        
        # =====================================================
        # TESTE 2: Usar método product_id_change se existir
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🧪 TESTE 2: Tentar método product_id_change")
        logger.info("="*80)
        
        try:
            # Alguns Odoo têm método product_id_change
            result = odoo.execute_kw(
                'sale.order.line',
                'product_id_change',
                [],
                {
                    'pricelist': 1,
                    'product': product_id,
                    'qty': 1,
                    'uom': 1,
                    'partner_id': partner_id,
                    'fiscal_position': fiscal_position_id or False,
                }
            )
            
            logger.info(f"✅ product_id_change executado!")
            logger.info(f"   Resultado: {result}")
            
            if result and result.get('value'):
                for key, value in result['value'].items():
                    if 'cfop' in key.lower() or 'tax' in key.lower():
                        logger.info(f"      {key}: {value}")
                        
        except Exception as e:
            logger.warning(f"❌ Método product_id_change não disponível: {str(e)[:200]}")
        
        # =====================================================
        # TESTE 3: Verificar métodos disponíveis
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🧪 TESTE 3: Listar métodos disponíveis em sale.order.line")
        logger.info("="*80)
        
        try:
            # Tentar listar métodos (nem sempre funciona)
            logger.info("\nMétodos que podem estar disponíveis:")
            logger.info("""
            Métodos comuns em sale.order.line:
            - create
            - write
            - unlink
            - read
            - search
            - onchange (se configurado)
            - product_id_change (Odoo < 13)
            - _onchange_product_id (Odoo >= 13)
            - _compute_tax_id
            - _prepare_invoice_line
            """)
            
        except Exception as e:
            logger.warning(f"Erro: {e}")
        
        # =====================================================
        # TESTE 4: Server Action customizada
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🧪 TESTE 4: Criar Server Action customizada para onchange")
        logger.info("="*80)
        
        logger.info("""
        💡 SOLUÇÃO ALTERNATIVA:
        
        Se não conseguirmos chamar o onchange diretamente, podemos:
        
        1. Criar uma Server Action customizada no Odoo que:
           - Recebe o ID da linha do pedido
           - Executa o onchange do produto
           - Preenche o CFOP e outros campos
        
        2. Código da Server Action seria algo como:
           ```python
           for record in records:
               record._onchange_product_id()
               # ou
               record.onchange_product_id_fiscal()
           ```
        
        3. Chamar essa Server Action via API após criar a linha
        
        Isso garantiria que usamos a lógica REAL do Odoo!
        """)
        
        return order_id
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("🚀 Testando como chamar onchange diretamente no Odoo...")
    logger.info("="*80)
    
    order_id = testar_onchange_direto()
    
    if order_id:
        logger.info(f"\n📊 Testes concluídos!")
        logger.info(f"🆔 Pedido de teste: ID {order_id}")
        
        logger.info("\n" + "="*80)
        logger.info("📝 CONCLUSÃO")
        logger.info("="*80)
        logger.info("""
        O Odoo via XML-RPC tem limitações para onchange:
        
        ❌ LIMITAÇÕES:
        - Onchange não funciona automaticamente via API
        - Método 'onchange' pode não estar disponível
        - product_id_change depende da versão do Odoo
        
        ✅ SOLUÇÕES POSSÍVEIS:
        
        1. **Server Action Customizada** (MELHOR OPÇÃO):
           - Criar uma Server Action no Odoo
           - Que execute o onchange real do sistema
           - Chamar via API após criar a linha
        
        2. **Endpoint customizado**:
           - Criar um controller/endpoint no Odoo
           - Que execute o onchange e retorne os valores
        
        3. **Módulo customizado**:
           - Criar método que expõe o onchange via API
        
        A Server Action é a solução mais simples e segura!
        """)