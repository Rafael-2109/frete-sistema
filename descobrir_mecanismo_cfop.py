#!/usr/bin/env python3
"""
Script para descobrir o mecanismo real de preenchimento do CFOP no Odoo
Data: 2025-01-25
"""

import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def descobrir_mecanismo_cfop():
    """
    Tenta descobrir como o CFOP é preenchido automaticamente
    """
    try:
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        if not odoo:
            logger.error("❌ Não foi possível conectar ao Odoo")
            return None
        
        # =====================================================
        # 1. VERIFICAR ESTRUTURA DO CAMPO CFOP
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("📋 VERIFICANDO ESTRUTURA DOS CAMPOS CFOP")
        logger.info("="*80)
        
        try:
            # Buscar informações sobre os campos
            fields_info = odoo.execute_kw(
                'sale.order.line',
                'fields_get',
                [],
                {'attributes': ['string', 'type', 'compute', 'related', 'depends', 'inverse', 'ondelete']}
            )
            
            # Filtrar campos relacionados a CFOP
            cfop_fields = {k: v for k, v in fields_info.items() if 'cfop' in k.lower() or 'fiscal' in k.lower()}
            
            logger.info(f"\n✅ Encontrados {len(cfop_fields)} campos relacionados a CFOP/Fiscal:")
            
            for field_name, field_info in cfop_fields.items():
                logger.info(f"\n📌 Campo: {field_name}")
                logger.info(f"   Label: {field_info.get('string', 'N/A')}")
                logger.info(f"   Tipo: {field_info.get('type', 'N/A')}")
                
                if field_info.get('compute'):
                    logger.info(f"   ⚙️ COMPUTE: {field_info.get('compute')}")
                if field_info.get('related'):
                    logger.info(f"   🔗 RELATED: {field_info.get('related')}")
                if field_info.get('depends'):
                    logger.info(f"   📊 DEPENDS: {field_info.get('depends')}")
                if field_info.get('inverse'):
                    logger.info(f"   🔄 INVERSE: {field_info.get('inverse')}")
                    
        except Exception as e:
            logger.error(f"Erro ao buscar estrutura dos campos: {e}")
        
        # =====================================================
        # 2. BUSCAR SERVER ACTIONS RELACIONADAS
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🎯 BUSCANDO SERVER ACTIONS RELACIONADAS A CFOP/FISCAL")
        logger.info("="*80)
        
        try:
            # Buscar Server Actions que possam estar relacionadas
            server_actions = odoo.search_read(
                'ir.actions.server',
                ['|', '|', '|',
                 ('name', 'ilike', 'cfop'),
                 ('name', 'ilike', 'fiscal'),
                 ('name', 'ilike', 'imposto'),
                 ('name', 'ilike', 'onchange')],
                ['id', 'name', 'model_id', 'code'],
                limit=20
            )
            
            if server_actions:
                logger.info(f"\n✅ {len(server_actions)} Server Actions encontradas:")
                for action in server_actions[:10]:
                    logger.info(f"\n   ID: {action['id']} - {action['name']}")
                    if action.get('model_id'):
                        logger.info(f"      Modelo: {action['model_id'][1] if isinstance(action['model_id'], list) else action['model_id']}")
                    if action.get('code'):
                        # Mostrar primeiras linhas do código
                        code_lines = action['code'].split('\n')[:3]
                        logger.info(f"      Código (preview): {' '.join(code_lines)[:100]}...")
            else:
                logger.info("   Nenhuma Server Action relacionada encontrada")
                
        except Exception as e:
            logger.error(f"Erro ao buscar Server Actions: {e}")
        
        # =====================================================
        # 3. VERIFICAR AUTOMATED ACTIONS
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🤖 VERIFICANDO AUTOMATED ACTIONS")
        logger.info("="*80)
        
        try:
            # Buscar Automated Actions no modelo sale.order.line
            automated_actions = odoo.search_read(
                'base.automation',
                [('model_id.model', '=', 'sale.order.line')],
                ['id', 'name', 'trigger', 'action_server_id'],
                limit=10
            )
            
            if automated_actions:
                logger.info(f"\n✅ {len(automated_actions)} Automated Actions encontradas:")
                for auto_action in automated_actions:
                    logger.info(f"\n   {auto_action['name']}")
                    logger.info(f"      Trigger: {auto_action.get('trigger', 'N/A')}")
                    if auto_action.get('action_server_id'):
                        logger.info(f"      Server Action: {auto_action['action_server_id'][1] if isinstance(auto_action['action_server_id'], list) else auto_action['action_server_id']}")
            else:
                logger.info("   Nenhuma Automated Action encontrada para sale.order.line")
                
        except Exception as e:
            logger.warning(f"Modelo base.automation pode não estar disponível: {e}")
        
        # =====================================================
        # 4. TESTAR MÉTODOS DIRETOS
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🧪 TESTANDO MÉTODOS DISPONÍVEIS NO MODELO")
        logger.info("="*80)
        
        # Criar um pedido de teste
        cliente = odoo.search_read(
            'res.partner',
            [('l10n_br_cnpj', '=', '75.315.333/0002-90')],
            ['id', 'name'],
            limit=1
        )
        
        if cliente:
            order_data = {
                'partner_id': cliente[0]['id'],
                'company_id': 4,
            }
            
            order_id = odoo.execute_kw(
                'sale.order',
                'create',
                [order_data]
            )
            
            logger.info(f"\n✅ Pedido teste criado: ID {order_id}")
            
            # Tentar diferentes métodos
            methods_to_test = [
                '_onchange_product_id',
                'onchange_product_id', 
                '_compute_tax_id',
                '_compute_l10n_br_cfop',
                '_onchange_fiscal_operation_id',
                '_onchange_fiscal_operation_line_id',
                'product_id_change',
                '_get_compute_price',
            ]
            
            logger.info("\n📌 Testando métodos possíveis:")
            
            for method_name in methods_to_test:
                try:
                    # Tentar chamar o método
                    result = odoo.execute_kw(
                        'sale.order.line',
                        method_name,
                        []
                    )
                    logger.info(f"   ✅ {method_name} - EXISTE!")
                except Exception as e:
                    error_msg = str(e)
                    if 'does not exist' in error_msg or 'no attribute' in error_msg:
                        logger.info(f"   ❌ {method_name} - não existe")
                    else:
                        logger.info(f"   ⚠️ {method_name} - erro: {error_msg[:50]}")
        
        # =====================================================
        # 5. BUSCAR NO MÓDULO L10N_BR
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("🇧🇷 VERIFICANDO MÓDULOS BRASILEIROS INSTALADOS")
        logger.info("="*80)
        
        try:
            # Buscar módulos l10n_br instalados
            modules = odoo.search_read(
                'ir.module.module',
                [('name', 'ilike', 'l10n_br'), ('state', '=', 'installed')],
                ['name', 'summary'],
                limit=20
            )
            
            if modules:
                logger.info(f"\n✅ {len(modules)} módulos brasileiros instalados:")
                for module in modules:
                    logger.info(f"   • {module['name']}: {module.get('summary', 'N/A')[:50]}")
                    
            # Buscar também módulos CIEL IT
            ciel_modules = odoo.search_read(
                'ir.module.module',
                [('name', 'ilike', 'ciel'), ('state', '=', 'installed')],
                ['name', 'summary'],
                limit=20
            )
            
            if ciel_modules:
                logger.info(f"\n✅ {len(ciel_modules)} módulos CIEL IT instalados:")
                for module in ciel_modules:
                    logger.info(f"   • {module['name']}: {module.get('summary', 'N/A')[:50]}")
                    
        except Exception as e:
            logger.error(f"Erro ao buscar módulos: {e}")
        
        # =====================================================
        # CONCLUSÕES
        # =====================================================
        logger.info("\n" + "="*80)
        logger.info("💡 INFORMAÇÕES PARA VERIFICAR NOS LOGS DO ODOO")
        logger.info("="*80)
        
        logger.info("""
PARA DESCOBRIR O MECANISMO REAL DO CFOP, PRECISO VER NOS LOGS:

1. **Quando você seleciona um produto na interface web:**
   - Nome do método JavaScript que dispara o evento
   - Chamada RPC feita ao backend
   - Método Python executado no servidor
   
2. **No backend do Odoo (Python):**
   - Se existe método @api.onchange('product_id')
   - Se existe campo compute para l10n_br_cfop_id
   - Se existe método _compute_l10n_br_cfop ou similar
   - Qual módulo implementa essa lógica (l10n_br_sale, ciel_it_account, etc)

3. **Informações específicas necessárias:**
   - Nome exato do método que preenche o CFOP
   - Parâmetros que esse método recebe
   - Se usa fiscal_position_id, fiscal_operation_id ou outro campo
   
4. **Para capturar isso, no Odoo:**
   Settings → Technical → Logging
   - Definir nível: DEBUG
   - Filtrar por: sale.order.line
   - Executar ação de selecionar produto
   - Verificar logs gerados

5. **Ou adicionar logging na Server Action 1955:**
   ```python
   import logging
   _logger = logging.getLogger(__name__)
   
   for record in records:
       # Listar todos os métodos
       all_methods = dir(record)
       fiscal_methods = [m for m in all_methods if 'fiscal' in m.lower() or 'cfop' in m.lower()]
       _logger.info(f"Métodos fiscais disponíveis: {fiscal_methods}")
       
       # Verificar se existe fiscal_operation_id
       if hasattr(record, 'fiscal_operation_id'):
           _logger.info(f"fiscal_operation_id: {record.fiscal_operation_id}")
       
       # Tentar chamar compute se existir
       if hasattr(record, '_compute_tax_id'):
           record._compute_tax_id()
   ```

Com essas informações dos logs, poderei criar um script que acione 
o mecanismo REAL do Odoo para preencher o CFOP, sem deduzir regras.
""")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("🚀 Descobrindo mecanismo de preenchimento do CFOP...")
    logger.info("="*80)
    
    sucesso = descobrir_mecanismo_cfop()
    
    if sucesso:
        logger.info("\n✅ Análise concluída!")
        logger.info("📋 Verifique os logs do Odoo para capturar o comportamento real")