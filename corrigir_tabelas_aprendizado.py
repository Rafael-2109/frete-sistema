#!/usr/bin/env python3
"""
Script para corrigir e verificar tabelas de aprendizado do Claude AI
"""
import os
import sys
import psycopg2
from psycopg2 import sql
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Conecta ao banco PostgreSQL do Render"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL não encontrada!")
        return None
    
    try:
        conn = psycopg2.connect(database_url, sslmode='require')
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco: {e}")
        return None

def verificar_tabelas(conn):
    """Verifica se as tabelas existem"""
    tabelas_esperadas = [
        'ai_knowledge_patterns',
        'ai_semantic_mappings', 
        'ai_learning_history',
        'ai_grupos_empresariais',
        'ai_business_contexts',
        'ai_response_templates',
        'ai_learning_metrics'
    ]
    
    cur = conn.cursor()
    tabelas_existentes = []
    
    for tabela in tabelas_esperadas:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (tabela,))
        
        existe = cur.fetchone()[0]
        if existe:
            tabelas_existentes.append(tabela)
            logger.info(f"✅ Tabela {tabela} existe")
        else:
            logger.warning(f"❌ Tabela {tabela} NÃO existe")
    
    return tabelas_existentes

def corrigir_grupos_empresariais(conn):
    """Adiciona dados iniciais na tabela de grupos empresariais"""
    cur = conn.cursor()
    
    try:
        # Verificar se já existem dados
        cur.execute("SELECT COUNT(*) FROM ai_grupos_empresariais")
        count = cur.fetchone()[0]
        
        if count == 0:
            logger.info("Inserindo grupos empresariais iniciais...")
            
            grupos = [
                {
                    'nome': 'Assai',
                    'tipo': 'Atacarejo',
                    'prefixos': ['06.057.223/'],
                    'palavras': ['assai', 'assaí'],
                    'filtro': "cliente ILIKE '%assai%' OR cnpj_cliente LIKE '06.057.223/%'"
                },
                {
                    'nome': 'Atacadão',
                    'tipo': 'Atacarejo',
                    'prefixos': ['75.315.333/', '00.063.960/', '93.209.765/'],
                    'palavras': ['atacadao', 'atacadão'],
                    'filtro': "cliente ILIKE '%atacadao%' OR cnpj_cliente LIKE '75.315.333/%' OR cnpj_cliente LIKE '00.063.960/%'"
                },
                {
                    'nome': 'Carrefour',
                    'tipo': 'Varejo',
                    'prefixos': ['45.543.915/'],
                    'palavras': ['carrefour'],
                    'filtro': "cliente ILIKE '%carrefour%' OR cnpj_cliente LIKE '45.543.915/%'"
                }
            ]
            
            for grupo in grupos:
                cur.execute("""
                    INSERT INTO ai_grupos_empresariais 
                    (nome_grupo, tipo_negocio, cnpj_prefixos, palavras_chave, filtro_sql, ativo)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    ON CONFLICT (nome_grupo) DO NOTHING
                """, (
                    grupo['nome'],
                    grupo['tipo'],
                    grupo['prefixos'],
                    grupo['palavras'],
                    grupo['filtro']
                ))
            
            conn.commit()
            logger.info(f"✅ {len(grupos)} grupos empresariais inseridos")
        else:
            logger.info(f"ℹ️ Já existem {count} grupos empresariais")
            
    except Exception as e:
        logger.error(f"Erro ao corrigir grupos empresariais: {e}")
        conn.rollback()

def adicionar_padroes_iniciais(conn):
    """Adiciona padrões de consulta iniciais"""
    cur = conn.cursor()
    
    try:
        # Verificar se já existem padrões
        cur.execute("SELECT COUNT(*) FROM ai_knowledge_patterns")
        count = cur.fetchone()[0]
        
        if count < 10:  # Se tem poucos padrões
            logger.info("Inserindo padrões iniciais...")
            
            padroes = [
                {
                    'tipo': 'intencao',
                    'texto': 'melhor',
                    'interpretacao': {'acao': 'status', 'contexto': 'melhoria'}
                },
                {
                    'tipo': 'periodo',
                    'texto': 'hoje',
                    'interpretacao': {'periodo_dias': 0, 'tipo': 'dia_especifico'}
                },
                {
                    'tipo': 'periodo',
                    'texto': 'ontem',
                    'interpretacao': {'periodo_dias': 1, 'tipo': 'dia_anterior'}
                },
                {
                    'tipo': 'dominio',
                    'texto': 'entregas',
                    'interpretacao': {'modelo': 'EntregaMonitorada', 'foco': 'monitoramento'}
                }
            ]
            
            for padrao in padroes:
                cur.execute("""
                    INSERT INTO ai_knowledge_patterns 
                    (pattern_type, pattern_text, interpretation, confidence, created_by)
                    VALUES (%s, %s, %s::jsonb, 0.7, 'sistema')
                    ON CONFLICT (pattern_type, pattern_text) DO NOTHING
                """, (
                    padrao['tipo'],
                    padrao['texto'],
                    str(padrao['interpretacao']).replace("'", '"')
                ))
            
            conn.commit()
            logger.info(f"✅ Padrões iniciais inseridos")
            
    except Exception as e:
        logger.error(f"Erro ao adicionar padrões: {e}")
        conn.rollback()

def verificar_integridade(conn):
    """Verifica integridade das tabelas"""
    cur = conn.cursor()
    
    # Verificar tipos de dados
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'ai_grupos_empresariais' 
        AND column_name = 'ativo'
    """)
    
    result = cur.fetchone()
    if result:
        logger.info(f"✅ Campo 'ativo' em ai_grupos_empresariais: tipo {result[1]}")
    
    # Verificar índices
    cur.execute("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename LIKE 'ai_%'
    """)
    
    indices = cur.fetchall()
    logger.info(f"✅ {len(indices)} índices encontrados nas tabelas AI")

def main():
    """Função principal"""
    logger.info("🔧 Iniciando correção das tabelas de aprendizado...")
    
    conn = get_db_connection()
    if not conn:
        logger.error("Não foi possível conectar ao banco!")
        return 1
    
    try:
        # Verificar tabelas
        tabelas = verificar_tabelas(conn)
        
        if len(tabelas) < 7:
            logger.error("❌ Nem todas as tabelas existem! Execute aplicar_tabelas_ai_render.py primeiro")
            return 1
        
        # Corrigir e adicionar dados
        corrigir_grupos_empresariais(conn)
        adicionar_padroes_iniciais(conn)
        verificar_integridade(conn)
        
        logger.info("✅ Correções aplicadas com sucesso!")
        return 0
        
    except Exception as e:
        logger.error(f"Erro durante correção: {e}")
        return 1
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main()) 