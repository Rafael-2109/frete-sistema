#!/usr/bin/env python3
"""
Script para corrigir a estrutura da tabela saldo_estoque_cache no Render
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_saldo_estoque_cache():
    """Corrige a estrutura da tabela saldo_estoque_cache"""
    
    # Obter URL do banco de dados
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL não encontrada nas variáveis de ambiente")
        sys.exit(1)
    
    try:
        # Conectar ao banco
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        logger.info("Conectado ao banco de dados")
        
        # Verificar se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'saldo_estoque_cache'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            logger.info("Tabela saldo_estoque_cache existe, verificando colunas...")
            
            # Lista de colunas necessárias
            columns_to_check = [
                ('saldo_atual', 'NUMERIC(15,3) DEFAULT 0'),
                ('qtd_carteira', 'NUMERIC(15,3) DEFAULT 0'),
                ('qtd_pre_separacao', 'NUMERIC(15,3) DEFAULT 0'),
                ('qtd_separacao', 'NUMERIC(15,3) DEFAULT 0'),
                ('previsao_ruptura_7d', 'DATE'),
                ('status_ruptura', 'VARCHAR(20)'),
                ('ultima_atualizacao_saldo', 'TIMESTAMP'),
                ('ultima_atualizacao_carteira', 'TIMESTAMP'),
                ('ultima_atualizacao_projecao', 'TIMESTAMP')
            ]
            
            for column_name, column_type in columns_to_check:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'saldo_estoque_cache' 
                        AND column_name = %s
                    )
                """, (column_name,))
                
                column_exists = cursor.fetchone()[0]
                
                if not column_exists:
                    logger.info(f"Adicionando coluna {column_name}...")
                    cursor.execute(f"""
                        ALTER TABLE saldo_estoque_cache 
                        ADD COLUMN {column_name} {column_type}
                    """)
                    logger.info(f"✅ Coluna {column_name} adicionada")
                else:
                    logger.info(f"✓ Coluna {column_name} já existe")
            
        else:
            logger.info("Tabela não existe, criando saldo_estoque_cache...")
            
            cursor.execute("""
                CREATE TABLE saldo_estoque_cache (
                    id SERIAL PRIMARY KEY,
                    cod_produto VARCHAR(50) NOT NULL,
                    nome_produto VARCHAR(255),
                    saldo_atual NUMERIC(15,3) DEFAULT 0,
                    qtd_carteira NUMERIC(15,3) DEFAULT 0,
                    qtd_pre_separacao NUMERIC(15,3) DEFAULT 0,
                    qtd_separacao NUMERIC(15,3) DEFAULT 0,
                    previsao_ruptura_7d DATE,
                    status_ruptura VARCHAR(20),
                    ultima_atualizacao_saldo TIMESTAMP,
                    ultima_atualizacao_carteira TIMESTAMP,
                    ultima_atualizacao_projecao TIMESTAMP,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Criar índices
            cursor.execute("CREATE INDEX idx_saldo_estoque_cache_produto ON saldo_estoque_cache(cod_produto)")
            cursor.execute("CREATE INDEX idx_saldo_estoque_cache_ruptura ON saldo_estoque_cache(status_ruptura)")
            
            logger.info("✅ Tabela saldo_estoque_cache criada com sucesso")
        
        # Confirmar mudanças
        conn.commit()
        
        # Verificar estrutura final
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name = 'saldo_estoque_cache'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        logger.info("\n📊 Estrutura final da tabela saldo_estoque_cache:")
        for col in columns:
            col_name, data_type, char_max, num_prec, num_scale = col
            if data_type == 'character varying':
                type_str = f"VARCHAR({char_max})"
            elif data_type == 'numeric':
                type_str = f"NUMERIC({num_prec},{num_scale})"
            else:
                type_str = data_type.upper()
            logger.info(f"  - {col_name}: {type_str}")
        
        logger.info("\n✅ Correção concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro ao corrigir tabela: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_saldo_estoque_cache()