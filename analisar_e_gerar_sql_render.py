#!/usr/bin/env python3
"""
Script para analisar o banco de dados local e gerar SQL de atualização para o Render
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adicionar o caminho do projeto ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_local_database_url():
    """Obter URL do banco de dados local do arquivo .env"""
    try:
        with open('.env', 'r') as f:
            for line in f:
                if 'DATABASE_URL' in line and not line.strip().startswith('#'):
                    # Extrair o valor da URL
                    url = line.split('=', 1)[1].strip()
                    # Remover aspas se houver
                    url = url.strip('"').strip("'")
                    return url
    except FileNotFoundError:
        logger.error("Arquivo .env não encontrado")
        return None
    return None

def analyze_database_structure(engine):
    """Analisar estrutura do banco de dados"""
    inspector = inspect(engine)
    tables_info = {}
    
    logger.info("Analisando estrutura do banco de dados...")
    
    for table_name in inspector.get_table_names():
        logger.info(f"Analisando tabela: {table_name}")
        
        # Obter colunas
        columns = inspector.get_columns(table_name)
        
        # Obter índices
        indexes = inspector.get_indexes(table_name)
        
        # Obter constraints
        foreign_keys = inspector.get_foreign_keys(table_name)
        primary_keys = inspector.get_pk_constraint(table_name)
        unique_constraints = inspector.get_unique_constraints(table_name)
        
        tables_info[table_name] = {
            'columns': columns,
            'indexes': indexes,
            'foreign_keys': foreign_keys,
            'primary_keys': primary_keys,
            'unique_constraints': unique_constraints
        }
    
    return tables_info

def compare_with_backup(tables_info):
    """Comparar com as tabelas do backup do Render"""
    # Tabelas identificadas no backup do Render
    render_tables = set([
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
    ])
    
    local_tables = set(tables_info.keys())
    
    # Tabelas que existem no Render mas não no local
    missing_in_local = render_tables - local_tables
    
    # Tabelas que existem no local mas não no Render
    missing_in_render = local_tables - render_tables
    
    # Tabelas comuns
    common_tables = local_tables & render_tables
    
    return {
        'missing_in_local': missing_in_local,
        'missing_in_render': missing_in_render,
        'common_tables': common_tables
    }

def generate_sql_updates(tables_info, comparison):
    """Gerar script SQL com as atualizações necessárias"""
    sql_script = []
    
    # Cabeçalho
    sql_script.append(f"""-- =====================================================
-- Script SQL de Atualização do Banco de Dados Render
-- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- =====================================================

-- IMPORTANTE: Este script contém verificações de segurança
-- Execute com cuidado e faça backup antes!

\\echo 'Iniciando atualização do banco de dados...'

-- Configurações de segurança
SET statement_timeout = '30min';
SET lock_timeout = '1min';

BEGIN; -- Iniciar transação

""")

    # 1. Adicionar colunas faltantes em tabelas críticas
    critical_updates = {
        'separacao': [
            ('separacao_lote_id', 'VARCHAR(50)', None),
            ('tipo_envio', 'VARCHAR(10)', "'total'")
        ],
        'pre_separacao_itens': [
            ('tipo_envio', 'VARCHAR(10)', "'total'")
        ],
        'carteira_principal': [
            ('qtd_pre_separacoes', 'INTEGER', '0'),
            ('qtd_separacoes', 'INTEGER', '0')
        ]
    }
    
    for table, columns in critical_updates.items():
        if table in comparison['common_tables']:
            sql_script.append(f"-- Verificando e adicionando colunas na tabela {table}")
            for col_name, col_type, default_val in columns:
                sql_script.append(f"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = '{table}' 
        AND column_name = '{col_name}'
    ) THEN
        ALTER TABLE public.{table} ADD COLUMN {col_name} {col_type}{' DEFAULT ' + default_val if default_val else ''};
        RAISE NOTICE 'Coluna {col_name} adicionada na tabela {table}';
    ELSE
        RAISE NOTICE 'Coluna {col_name} já existe na tabela {table}';
    END IF;
END $$;
""")

    # 2. Criar tabelas que existem no local mas não no Render
    for table_name in comparison['missing_in_render']:
        if table_name in tables_info:
            sql_script.append(f"\n-- Criando tabela {table_name} (se não existir)")
            sql_script.append(f"CREATE TABLE IF NOT EXISTS public.{table_name} (")
            
            columns = []
            for col in tables_info[table_name]['columns']:
                col_def = f"    {col['name']} {col['type']}"
                if not col.get('nullable', True):
                    col_def += " NOT NULL"
                if col.get('default'):
                    col_def += f" DEFAULT {col['default']}"
                columns.append(col_def)
            
            sql_script.append(",\n".join(columns))
            
            # Adicionar primary key se existir
            pk = tables_info[table_name]['primary_keys']
            if pk and pk['constrained_columns']:
                sql_script.append(f",\n    PRIMARY KEY ({', '.join(pk['constrained_columns'])})")
            
            sql_script.append(");\n")

    # 3. Criar índices importantes
    important_indexes = [
        ('separacao', 'idx_separacao_lote_id', 'separacao_lote_id'),
        ('separacao', 'idx_separacao_num_pedido', 'num_pedido'),
        ('pre_separacao_itens', 'idx_pre_separacao_carteira_id', 'carteira_principal_id'),
        ('carteira_principal', 'idx_carteira_num_pedido', 'num_pedido'),
        ('carteira_principal', 'idx_carteira_cod_produto', 'cod_produto'),
        ('vinculacao_carteira_separacao', 'idx_vinculacao_lote', 'separacao_lote_id'),
        ('vinculacao_carteira_separacao', 'idx_vinculacao_pedido', 'num_pedido')
    ]
    
    sql_script.append("\n-- Criando índices para performance")
    for table, index_name, column in important_indexes:
        if table in comparison['common_tables']:
            sql_script.append(f"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = '{table}' 
        AND indexname = '{index_name}'
    ) THEN
        CREATE INDEX {index_name} ON public.{table} ({column});
        RAISE NOTICE 'Índice {index_name} criado na tabela {table}';
    ELSE
        RAISE NOTICE 'Índice {index_name} já existe na tabela {table}';
    END IF;
END $$;
""")

    # 4. Atualizar sequences se necessário
    sql_script.append("\n-- Ajustando sequences")
    sequences_to_check = [
        'carteira_principal_id_seq',
        'separacao_id_seq',
        'pre_separacao_itens_id_seq',
        'vinculacao_carteira_separacao_id_seq'
    ]
    
    for seq in sequences_to_check:
        table = seq.replace('_id_seq', '')
        sql_script.append(f"""
DO $$
DECLARE
    max_id INTEGER;
BEGIN
    -- Verificar se a tabela existe
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}') THEN
        -- Obter o máximo ID da tabela
        EXECUTE 'SELECT COALESCE(MAX(id), 0) FROM public.{table}' INTO max_id;
        
        -- Ajustar a sequence se existir
        IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = '{seq}') THEN
            PERFORM setval('public.{seq}', max_id + 1, false);
            RAISE NOTICE 'Sequence {seq} ajustada para %', max_id + 1;
        END IF;
    END IF;
END $$;
""")

    # 5. Limpar dados órfãos
    sql_script.append("""
-- Limpeza de dados órfãos
\\echo 'Limpando dados órfãos...'

-- Remover pré-separações sem carteira correspondente
DELETE FROM public.pre_separacao_itens psi
WHERE NOT EXISTS (
    SELECT 1 FROM public.carteira_principal cp 
    WHERE cp.id = psi.carteira_principal_id
);

-- Remover separações com lote_id inválido
UPDATE public.separacao 
SET separacao_lote_id = NULL 
WHERE separacao_lote_id = '' OR separacao_lote_id = 'null';

""")

    # 6. Validações finais
    sql_script.append("""
-- Validações finais
\\echo 'Executando validações...'

DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Verificar integridade das tabelas principais
    SELECT COUNT(*) INTO v_count FROM public.carteira_principal;
    RAISE NOTICE 'Registros em carteira_principal: %', v_count;
    
    SELECT COUNT(*) INTO v_count FROM public.separacao;
    RAISE NOTICE 'Registros em separacao: %', v_count;
    
    SELECT COUNT(*) INTO v_count FROM public.pre_separacao_itens;
    RAISE NOTICE 'Registros em pre_separacao_itens: %', v_count;
    
    -- Verificar colunas críticas
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'separacao' AND column_name = 'separacao_lote_id'
    ) THEN
        RAISE EXCEPTION 'ERRO: Coluna separacao_lote_id não foi criada!';
    END IF;
END $$;

COMMIT; -- Confirmar transação

\\echo 'Atualização concluída com sucesso!'
\\echo 'IMPORTANTE: Execute VACUUM ANALYZE após este script!'
""")

    return '\n'.join(sql_script)

def main():
    """Função principal"""
    logger.info("Iniciando análise do banco de dados...")
    
    # Obter URL do banco de dados
    db_url = get_local_database_url()
    if not db_url:
        logger.error("Não foi possível obter a URL do banco de dados")
        return
    
    try:
        # Criar engine
        engine = create_engine(db_url)
        
        # Analisar estrutura
        tables_info = analyze_database_structure(engine)
        
        # Comparar com backup
        comparison = compare_with_backup(tables_info)
        
        logger.info(f"Tabelas no local: {len(tables_info)}")
        logger.info(f"Tabelas faltando no local: {len(comparison['missing_in_local'])}")
        logger.info(f"Tabelas faltando no Render: {len(comparison['missing_in_render'])}")
        logger.info(f"Tabelas em comum: {len(comparison['common_tables'])}")
        
        # Gerar SQL
        sql_script = generate_sql_updates(tables_info, comparison)
        
        # Salvar arquivo SQL
        output_file = 'atualizar_render_database.sql'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(sql_script)
        
        logger.info(f"Script SQL gerado: {output_file}")
        
        # Gerar relatório
        report = f"""
=====================================
RELATÓRIO DE ANÁLISE DO BANCO DE DADOS
=====================================

Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RESUMO:
-------
- Tabelas no banco local: {len(tables_info)}
- Tabelas no backup Render: 91
- Tabelas em comum: {len(comparison['common_tables'])}
- Tabelas faltando no Render: {len(comparison['missing_in_render'])}

TABELAS FALTANDO NO RENDER:
{', '.join(sorted(comparison['missing_in_render'])) if comparison['missing_in_render'] else 'Nenhuma'}

AÇÕES GERADAS NO SCRIPT SQL:
1. Adicionar colunas faltantes em tabelas críticas
2. Criar tabelas que não existem no Render
3. Criar índices para performance
4. Ajustar sequences
5. Limpar dados órfãos
6. Validações de integridade

PRÓXIMOS PASSOS:
1. Revisar o arquivo 'atualizar_render_database.sql'
2. Fazer backup do banco no Render
3. Executar o script SQL no Render
4. Executar VACUUM ANALYZE após o script
5. Testar o sistema

"""
        
        print(report)
        
        # Salvar relatório
        with open('relatorio_analise_banco.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info("Análise concluída com sucesso!")
        
    except SQLAlchemyError as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")

if __name__ == "__main__":
    main()