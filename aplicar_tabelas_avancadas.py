#!/usr/bin/env python3
"""
Script para aplicar tabelas avançadas de IA no PostgreSQL
Executa o arquivo create_ai_tables_clean.sql no banco de produção
"""

import psycopg2
import os
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def conectar_banco():
    """Conecta ao banco PostgreSQL do Render"""
    try:
        # Configurações do banco (usar variáveis de ambiente em produção)
        db_config = {
            'host': 'dpg-d13m38vfte5s738t6p50-a.oregon-postgres.render.com',
            'port': 5432,
            'database': 'sistema_fretes',
            'user': 'sistema_user',
            'password': 'R80cswDpRJGsmpTdA73XxvV2xqEfzYm9'
        }
        
        conn = psycopg2.connect(**db_config)
        logger.info("✅ Conectado ao PostgreSQL com sucesso")
        return conn
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco: {e}")
        return None

def executar_sql_file(conn, arquivo_sql):
    """Executa arquivo SQL no banco"""
    try:
        if not os.path.exists(arquivo_sql):
            logger.error(f"❌ Arquivo não encontrado: {arquivo_sql}")
            return False
            
        # Ler arquivo SQL
        with open(arquivo_sql, 'r', encoding='utf-8') as f:
            sql_content = f.read()
            
        # Executar SQL
        cursor = conn.cursor()
        cursor.execute(sql_content)
        conn.commit()
        cursor.close()
        
        logger.info(f"✅ Arquivo SQL executado com sucesso: {arquivo_sql}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao executar SQL: {e}")
        conn.rollback()
        return False

def verificar_tabelas_criadas(conn):
    """Verifica se as tabelas foram criadas corretamente"""
    try:
        cursor = conn.cursor()
        
        # Lista de tabelas que devem existir
        tabelas_esperadas = [
            'ai_advanced_sessions',
            'ai_feedback_history', 
            'ai_learning_patterns',
            'ai_performance_metrics',
            'ai_semantic_embeddings',
            'ai_system_config'
        ]
        
        tabelas_encontradas = []
        
        for tabela in tabelas_esperadas:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, (tabela,))
            
            existe = cursor.fetchone()[0]
            if existe:
                tabelas_encontradas.append(tabela)
                logger.info(f"✅ Tabela encontrada: {tabela}")
            else:
                logger.warning(f"⚠️ Tabela não encontrada: {tabela}")
        
        cursor.close()
        
        logger.info(f"📊 Resumo: {len(tabelas_encontradas)}/{len(tabelas_esperadas)} tabelas criadas")
        return len(tabelas_encontradas) == len(tabelas_esperadas)
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar tabelas: {e}")
        return False

def verificar_indices(conn):
    """Verifica se os índices foram criados"""
    try:
        cursor = conn.cursor()
        
        # Verificar alguns índices importantes
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename LIKE 'ai_%' 
            ORDER BY indexname;
        """)
        
        indices = cursor.fetchall()
        logger.info(f"📈 Índices criados: {len(indices)}")
        
        for idx in indices:
            logger.info(f"  - {idx[0]}")
            
        cursor.close()
        return len(indices) > 0
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar índices: {e}")
        return False

def verificar_views(conn):
    """Verifica se as views foram criadas"""
    try:
        cursor = conn.cursor()
        
        views_esperadas = ['ai_session_analytics', 'ai_feedback_analytics']
        
        for view in views_esperadas:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.views 
                    WHERE table_name = %s
                );
            """, (view,))
            
            existe = cursor.fetchone()[0]
            if existe:
                logger.info(f"✅ View encontrada: {view}")
            else:
                logger.warning(f"⚠️ View não encontrada: {view}")
        
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar views: {e}")
        return False

def testar_insercao(conn):
    """Testa inserção de dados nas tabelas"""
    try:
        cursor = conn.cursor()
        
        # Testar inserção na tabela de configurações
        cursor.execute("""
            INSERT INTO ai_system_config (config_key, config_value, description)
            VALUES ('test_config', '{"test": true}'::jsonb, 'Configuração de teste')
            ON CONFLICT (config_key) DO UPDATE SET
                config_value = EXCLUDED.config_value,
                updated_at = CURRENT_TIMESTAMP;
        """)
        
        # Verificar se foi inserido
        cursor.execute("SELECT COUNT(*) FROM ai_system_config WHERE config_key = 'test_config'")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.info("✅ Teste de inserção bem-sucedido")
            
            # Limpar teste
            cursor.execute("DELETE FROM ai_system_config WHERE config_key = 'test_config'")
            
        conn.commit()
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro no teste de inserção: {e}")
        conn.rollback()
        return False

def main():
    """Função principal"""
    print("🚀 APLICAÇÃO DE TABELAS AVANÇADAS DE IA")
    print("=" * 50)
    
    # Conectar ao banco
    conn = conectar_banco()
    if not conn:
        print("❌ Falha na conexão. Abortando.")
        return False
    
    try:
        # Executar arquivo SQL
        print("\n📝 Executando create_ai_tables_clean.sql...")
        if not executar_sql_file(conn, 'create_ai_tables_clean.sql'):
            print("❌ Falha na execução do SQL. Abortando.")
            return False
        
        print("\n🔍 Verificando tabelas criadas...")
        if not verificar_tabelas_criadas(conn):
            print("⚠️ Nem todas as tabelas foram criadas")
        
        print("\n📊 Verificando índices...")
        verificar_indices(conn)
        
        print("\n👁️ Verificando views...")
        verificar_views(conn)
        
        print("\n🧪 Testando inserção...")
        if not testar_insercao(conn):
            print("⚠️ Falha no teste de inserção")
        
        print("\n" + "=" * 50)
        print("✅ APLICAÇÃO CONCLUÍDA COM SUCESSO!")
        print("🚀 Sistema avançado de IA pronto para uso")
        print("\n📋 Próximos passos:")
        print("1. Reiniciar aplicação Flask")
        print("2. Testar rotas avançadas em /claude-ai/advanced-dashboard")
        print("3. Configurar ANTHROPIC_API_KEY se necessário")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na execução principal: {e}")
        return False
        
    finally:
        if conn:
            conn.close()
            logger.info("🔌 Conexão fechada")

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 