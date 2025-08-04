#!/usr/bin/env python3
"""
Análise completa e profunda do banco de dados
Compara banco local com backup do Render
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Adicionar o caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_local_database_url():
    """Obter URL do banco local"""
    try:
        with open('.env', 'r') as f:
            for line in f:
                if 'DATABASE_URL' in line and not line.strip().startswith('#'):
                    url = line.split('=', 1)[1].strip()
                    return url.strip('"').strip("'")
    except:
        return None

def analyze_local_database():
    """Analisar banco local detalhadamente"""
    db_url = get_local_database_url()
    if not db_url:
        logger.error("DATABASE_URL não encontrada")
        return None
    
    engine = create_engine(db_url)
    inspector = inspect(engine)
    
    # Obter todas as tabelas
    local_tables = set(inspector.get_table_names())
    
    # Analisar cada tabela
    table_details = {}
    for table in sorted(local_tables):
        columns = inspector.get_columns(table)
        table_details[table] = {
            'columns': [col['name'] for col in columns],
            'column_count': len(columns)
        }
    
    return local_tables, table_details

def get_render_tables():
    """Lista de tabelas do backup do Render"""
    # Baseado na análise do arquivo toc.dat
    render_tables = {
        'agendamentos_entrega', 'ai_advanced_sessions', 'ai_business_contexts',
        'ai_feedback_history', 'ai_grupos_empresariais', 'ai_knowledge_patterns',
        'ai_learning_history', 'ai_learning_metrics', 'ai_learning_patterns',
        'ai_performance_metrics', 'ai_response_templates', 'ai_semantic_embeddings',
        'ai_semantic_mappings', 'ai_system_config', 'alembic_version',
        'aprovacao_mudanca_carteira', 'aprovacoes_frete', 'arquivo_entrega',
        'batch_permission_operation', 'cadastro_palletizacao', 'cadastro_rota',
        'cadastro_sub_rota', 'carteira_copia', 'carteira_principal', 'cidades',
        'cidades_atendidas', 'comentarios_nf', 'conta_corrente_transportadoras',
        'contatos_agendamento', 'controle_alteracao_carga', 'controle_cruzado_separacao',
        'controle_descasamento_nf', 'controle_portaria', 'cotacao_itens', 'cotacoes',
        'custos_extra_entrega', 'despesas_extras', 'embarque_itens', 'embarques',
        'entregas_monitoradas', 'equipe_vendas', 'evento_carteira', 'eventos_entrega',
        'faturamento_parcial_justificativa', 'faturamento_produto', 'faturas_frete',
        'fretes', 'fretes_lancados', 'funcao_modulo', 'historico_data_prevista',
        'historico_faturamento', 'historico_tabelas_frete', 'inconsistencia_faturamento',
        'log_atualizacao_carteira', 'log_permissao', 'logs_entrega', 'modulo_sistema',
        'motoristas', 'movimentacao_estoque', 'pedidos', 'pendencias_financeiras_nf',
        'perfil_usuario', 'permissao_equipe', 'permissao_usuario', 'permissao_vendedor',
        'permission_cache', 'permission_category', 'permission_module', 'permission_submodule',
        'permission_template', 'pre_separacao_item', 'pre_separacao_itens',
        'programacao_producao', 'relatorio_faturamento_importado', 'saldo_standby',
        'separacao', 'snapshot_carteira', 'submodule', 'tabelas_frete', 'tipo_carga',
        'tipo_envio', 'transportadoras', 'unificacao_codigos', 'user_permission',
        'usuario_equipe_vendas', 'usuario_vendedor', 'usuarios', 'validacao_nf_simples',
        'veiculos', 'vendedor', 'vinculacao_carteira_separacao'
    }
    return render_tables

def main():
    print("="*80)
    print("ANÁLISE COMPLETA DO BANCO DE DADOS")
    print("="*80)
    
    # Analisar banco local
    result = analyze_local_database()
    if not result:
        return
    
    local_tables, table_details = result
    render_tables = get_render_tables()
    
    # Comparação
    missing_in_render = local_tables - render_tables
    missing_in_local = render_tables - local_tables
    common_tables = local_tables & render_tables
    
    print(f"\n📊 RESUMO GERAL:")
    print(f"   Tabelas no banco LOCAL: {len(local_tables)}")
    print(f"   Tabelas no backup RENDER: {len(render_tables)}")
    print(f"   Tabelas em COMUM: {len(common_tables)}")
    print(f"   Tabelas que FALTAM no Render: {len(missing_in_render)}")
    print(f"   Tabelas que FALTAM no Local: {len(missing_in_local)}")
    
    print(f"\n🔴 TABELAS QUE EXISTEM NO LOCAL MAS NÃO NO RENDER ({len(missing_in_render)}):")
    print("-"*60)
    for i, table in enumerate(sorted(missing_in_render), 1):
        cols = table_details[table]['column_count']
        print(f"{i:3}. {table:<40} ({cols} colunas)")
    
    print(f"\n🟡 TABELAS QUE EXISTEM NO RENDER MAS NÃO NO LOCAL ({len(missing_in_local)}):")
    print("-"*60)
    for i, table in enumerate(sorted(missing_in_local), 1):
        print(f"{i:3}. {table}")
    
    # Análise especial de tabelas importantes
    print(f"\n🔍 ANÁLISE DE TABELAS CRÍTICAS:")
    print("-"*60)
    
    critical_tables = [
        'cadastro_cliente',
        'carteira_principal', 
        'separacao',
        'pre_separacao_itens',
        'saldo_estoque_cache',
        'projecao_estoque_cache'
    ]
    
    for table in critical_tables:
        if table in local_tables:
            status = "✅ LOCAL" if table not in render_tables else "✅ AMBOS"
            cols = table_details[table]['column_count']
            print(f"   {table:<30} {status:<15} ({cols} colunas)")
        elif table in render_tables:
            print(f"   {table:<30} ⚠️  APENAS RENDER")
        else:
            print(f"   {table:<30} ❌ NÃO EXISTE")
    
    # Gerar lista de CREATE TABLE para tabelas faltantes
    print(f"\n📝 TABELAS QUE PRECISAM SER CRIADAS NO RENDER:")
    print("-"*60)
    
    importantes = [
        'cadastro_cliente',
        'saldo_estoque_cache',
        'projecao_estoque_cache',
        'cache_update_log',
        'batch_operation',
        'permission_log',
        'user_vendedor',
        'user_equipe',
        'vendedor_permission',
        'equipe_permission'
    ]
    
    for table in importantes:
        if table in missing_in_render:
            print(f"   ⭐ {table} - IMPORTANTE")
    
    for table in sorted(missing_in_render):
        if table not in importantes:
            print(f"   • {table}")
    
    # Salvar relatório
    with open('analise_completa_banco.txt', 'w') as f:
        f.write("="*80 + "\n")
        f.write("ANÁLISE COMPLETA - TABELAS FALTANTES NO RENDER\n")
        f.write("="*80 + "\n\n")
        
        f.write("TABELAS CRÍTICAS QUE FALTAM NO RENDER:\n")
        f.write("-"*40 + "\n")
        for table in sorted(missing_in_render):
            if table in importantes:
                f.write(f"⭐ {table}\n")
        
        f.write("\nOUTRAS TABELAS QUE FALTAM NO RENDER:\n")
        f.write("-"*40 + "\n")
        for table in sorted(missing_in_render):
            if table not in importantes:
                f.write(f"• {table}\n")
    
    print("\n✅ Relatório salvo em: analise_completa_banco.txt")

if __name__ == "__main__":
    main()