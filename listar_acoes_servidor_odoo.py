#!/usr/bin/env python3
"""
Script para listar Ações do Servidor e Ações Automatizadas do Odoo
relacionadas a sale.order (cotações/pedidos de venda)
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
    Lista todas as ações do servidor e ações automatizadas relacionadas a sale.order
    """
    try:
        # Conectar ao Odoo
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        if not odoo:
            logger.error("❌ Não foi possível conectar ao Odoo")
            return None
        
        logger.info("="*80)
        logger.info("🎯 AÇÕES DO SERVIDOR (Server Actions)")
        logger.info("="*80)
        
        # 1. Buscar Server Actions para sale.order
        logger.info("\n📋 Buscando Server Actions para sale.order...")
        server_actions = odoo.search_read(
            'ir.actions.server',
            ['|', ('model_id.model', '=', 'sale.order'), 
                  ('model_id.model', '=', 'sale.order.line')],
            ['id', 'name', 'state', 'code', 'model_id', 'trigger', 
             'crud_model_name', 'link_field_id', 'create_date']
        )
        
        if server_actions:
            logger.info(f"\n✅ Encontradas {len(server_actions)} Server Actions:")
            for i, action in enumerate(server_actions, 1):
                logger.info(f"\n{i}. {action['name']}")
                logger.info(f"   🆔 ID: {action['id']}")
                logger.info(f"   📊 Modelo: {action['model_id'][1] if action.get('model_id') else 'N/A'}")
                logger.info(f"   🔧 Tipo: {action['state']}")
                
                if action['state'] == 'code' and action.get('code'):
                    logger.info(f"   💻 Código Python:")
                    # Mostrar primeiras linhas do código
                    code_lines = action['code'].split('\n')[:5]
                    for line in code_lines:
                        if line.strip():
                            logger.info(f"      {line[:100]}")
                    if len(action['code'].split('\n')) > 5:
                        logger.info(f"      ... (mais {len(action['code'].split('\n')) - 5} linhas)")
                
                logger.info("-"*70)
        else:
            logger.info("❌ Nenhuma Server Action encontrada para sale.order")
        
        # 2. Buscar Automated Actions (base.automation)
        logger.info("\n" + "="*80)
        logger.info("🤖 AÇÕES AUTOMATIZADAS (Automated Actions)")
        logger.info("="*80)
        
        logger.info("\n📋 Buscando Automated Actions para sale.order...")
        automated_actions = odoo.search_read(
            'base.automation',
            ['|', ('model_id.model', '=', 'sale.order'),
                  ('model_id.model', '=', 'sale.order.line')],
            ['id', 'name', 'trigger', 'active', 'model_id', 
             'action_server_id', 'filter_domain', 'on_change_field_ids',
             'trigger_field_ids', 'state']
        )
        
        if automated_actions:
            logger.info(f"\n✅ Encontradas {len(automated_actions)} Automated Actions:")
            for i, action in enumerate(automated_actions, 1):
                logger.info(f"\n{i}. {action['name']}")
                logger.info(f"   🆔 ID: {action['id']}")
                logger.info(f"   📊 Modelo: {action['model_id'][1] if action.get('model_id') else 'N/A'}")
                logger.info(f"   ⚡ Trigger: {action['trigger']}")
                logger.info(f"   🟢 Ativa: {'Sim' if action.get('active') else 'Não'}")
                
                # Interpretar o trigger
                trigger_desc = {
                    'on_create': '➕ Na criação do registro',
                    'on_write': '✏️ Na atualização do registro',
                    'on_create_or_write': '➕✏️ Na criação ou atualização',
                    'on_unlink': '🗑️ Na exclusão do registro',
                    'on_change': '🔄 Na mudança de campo específico',
                    'on_time': '⏰ Baseado em tempo'
                }
                logger.info(f"   📝 Quando: {trigger_desc.get(action['trigger'], action['trigger'])}")
                
                if action.get('filter_domain'):
                    logger.info(f"   🔍 Filtro: {action['filter_domain']}")
                
                if action.get('on_change_field_ids'):
                    # Buscar nomes dos campos
                    field_ids = action['on_change_field_ids']
                    fields = odoo.search_read(
                        'ir.model.fields',
                        [('id', 'in', field_ids)],
                        ['name', 'field_description']
                    )
                    field_names = [f"{f['name']} ({f['field_description']})" for f in fields]
                    logger.info(f"   🔄 Campos monitorados: {', '.join(field_names)}")
                
                logger.info("-"*70)
        else:
            logger.info("❌ Nenhuma Automated Action encontrada para sale.order")
        
        # 3. Buscar Business Rules (se existir o modelo)
        logger.info("\n" + "="*80)
        logger.info("📏 REGRAS DE NEGÓCIO (Business Rules)")
        logger.info("="*80)
        
        try:
            # Tentar buscar regras de validação
            constraints = odoo.execute_kw(
                'ir.model.constraint',
                'search_read',
                [[('model', 'in', ['sale.order', 'sale.order.line'])]],
                {'fields': ['name', 'model', 'type', 'message']}
            )
            
            if constraints:
                logger.info(f"\n✅ Encontradas {len(constraints)} Constraints:")
                for constraint in constraints:
                    logger.info(f"   • {constraint['name']}")
                    logger.info(f"     Tipo: {constraint['type']}")
                    if constraint.get('message'):
                        logger.info(f"     Mensagem: {constraint['message']}")
            else:
                logger.info("❌ Nenhuma Constraint encontrada")
        except:
            logger.info("ℹ️ Modelo ir.model.constraint não disponível")
        
        # 4. Buscar Computed Fields que são acionados
        logger.info("\n" + "="*80)
        logger.info("🧮 CAMPOS CALCULADOS (Computed Fields)")
        logger.info("="*80)
        
        logger.info("\n📋 Buscando campos calculados de sale.order...")
        computed_fields = odoo.search_read(
            'ir.model.fields',
            [('model', '=', 'sale.order'), ('compute', '!=', False)],
            ['name', 'field_description', 'compute', 'depends', 'store'],
            limit=20
        )
        
        if computed_fields:
            logger.info(f"\n✅ Encontrados {len(computed_fields)} campos calculados:")
            for field in computed_fields:
                logger.info(f"   • {field['name']} - {field['field_description']}")
                if field.get('depends'):
                    logger.info(f"     Depende de: {field['depends']}")
                logger.info(f"     Armazenado: {'Sim' if field.get('store') else 'Não'}")
        
        # 5. Buscar Onchange Methods
        logger.info("\n" + "="*80)
        logger.info("🔄 MÉTODOS ONCHANGE")
        logger.info("="*80)
        
        logger.info("\n📋 Buscando campos com onchange em sale.order...")
        onchange_fields = odoo.search_read(
            'ir.model.fields',
            [('model', '=', 'sale.order'), ('on_change', '!=', False)],
            ['name', 'field_description', 'on_change'],
            limit=20
        )
        
        if onchange_fields:
            logger.info(f"\n✅ Encontrados {len(onchange_fields)} campos com onchange:")
            for field in onchange_fields:
                logger.info(f"   • {field['name']} - {field['field_description']}")
                if field.get('on_change'):
                    logger.info(f"     Onchange: {field['on_change']}")
        else:
            logger.info("ℹ️ Nenhum campo com onchange explícito encontrado")
        
        # 6. Buscar métodos do modelo sale.order
        logger.info("\n" + "="*80)
        logger.info("🔧 MÉTODOS DISPONÍVEIS DO MODELO")
        logger.info("="*80)
        
        try:
            # Tentar obter metadados do modelo
            model_info = odoo.execute_kw(
                'sale.order',
                'fields_view_get',
                [],
                {'view_type': 'form', 'context': {}}
            )
            
            if model_info and 'arch' in model_info:
                # Procurar por botões que executam ações
                import re
                arch = model_info['arch']
                buttons = re.findall(r'<button[^>]*name="([^"]*)"[^>]*>', arch)
                
                if buttons:
                    logger.info(f"\n✅ Botões/Ações encontrados no formulário:")
                    unique_buttons = list(set(buttons))
                    for btn in unique_buttons[:10]:
                        if not btn.startswith('%'):
                            logger.info(f"   • {btn}")
        except Exception as e:
            logger.info(f"ℹ️ Não foi possível obter métodos do formulário: {e}")
        
        # 7. Resumo
        logger.info("\n" + "="*80)
        logger.info("📊 RESUMO")
        logger.info("="*80)
        logger.info(f"""
   Server Actions: {len(server_actions) if server_actions else 0}
   Automated Actions: {len(automated_actions) if automated_actions else 0}
   Computed Fields: {len(computed_fields) if computed_fields else 0}
   Onchange Fields: {len(onchange_fields) if onchange_fields else 0}
        """)
        
        return {
            'server_actions': server_actions,
            'automated_actions': automated_actions,
            'computed_fields': computed_fields,
            'onchange_fields': onchange_fields
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar ações: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("🚀 Iniciando análise de ações e triggers do Odoo...")
    logger.info("="*80)
    
    resultado = listar_acoes_servidor()
    
    if resultado:
        logger.info(f"\n✅ Análise concluída!")
        logger.info("💡 Verifique as ações acima para entender o que acontece ao criar pedidos")
    else:
        logger.error("\n❌ Falha na análise")