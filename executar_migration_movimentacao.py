#!/usr/bin/env python3
"""
Script para executar migration de MovimentacaoEstoque no Render
========================================================

Este script adiciona os novos campos estruturados em MovimentacaoEstoque
e migra os dados históricos extraindo informações do campo observacao.

Uso:
    python executar_migration_movimentacao.py

Autor: Sistema de Fretes
Data: 01/09/2025
"""

import os
import sys
import logging
from datetime import datetime
import psycopg2
from psycopg2 import sql

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Obter conexão com o banco de dados"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        logger.error("DATABASE_URL não encontrada nas variáveis de ambiente")
        sys.exit(1)
    
    # Render usa postgres://, mas psycopg2 precisa de postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco: {e}")
        sys.exit(1)

def executar_migration():
    """Executar a migration de MovimentacaoEstoque"""
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        logger.info("========================================")
        logger.info("INICIANDO MIGRATION DE MovimentacaoEstoque")
        logger.info("========================================")
        
        # 1. Adicionar novos campos
        logger.info("1. Adicionando novos campos estruturados...")
        
        cur.execute("""
            ALTER TABLE movimentacao_estoque 
            ADD COLUMN IF NOT EXISTS separacao_lote_id VARCHAR(50),
            ADD COLUMN IF NOT EXISTS numero_nf VARCHAR(20),
            ADD COLUMN IF NOT EXISTS num_pedido VARCHAR(50),
            ADD COLUMN IF NOT EXISTS tipo_origem VARCHAR(20),
            ADD COLUMN IF NOT EXISTS status_nf VARCHAR(20),
            ADD COLUMN IF NOT EXISTS codigo_embarque INTEGER
        """)
        
        logger.info("✅ Campos adicionados com sucesso")
        
        # 2. Criar índices
        logger.info("2. Criando índices para performance...")
        
        indices = [
            ("idx_movimentacao_lote", "separacao_lote_id"),
            ("idx_movimentacao_nf", "numero_nf"),
            ("idx_movimentacao_pedido", "num_pedido"),
            ("idx_movimentacao_tipo_origem", "tipo_origem"),
            ("idx_movimentacao_status_nf", "status_nf")
        ]
        
        for idx_name, column in indices:
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS {idx_name} 
                ON movimentacao_estoque({column})
            """)
            logger.info(f"  ✓ Índice {idx_name} criado")
        
        # 3. Adicionar foreign key para embarque
        logger.info("3. Adicionando foreign key para embarque...")
        
        cur.execute("""
            DO $$ 
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'embarques') THEN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'fk_movimentacao_embarque'
                    ) THEN
                        ALTER TABLE movimentacao_estoque 
                        ADD CONSTRAINT fk_movimentacao_embarque 
                        FOREIGN KEY (codigo_embarque) 
                        REFERENCES embarques(id)
                        ON DELETE SET NULL;
                    END IF;
                END IF;
            END $$;
        """)
        
        logger.info("✅ Foreign key configurada")
        
        # 4. Adicionar campos em Separacao
        logger.info("4. Adicionando campos de sincronização em Separacao...")
        
        cur.execute("""
            ALTER TABLE separacao
            ADD COLUMN IF NOT EXISTS data_sincronizacao TIMESTAMP,
            ADD COLUMN IF NOT EXISTS zerado_por_sync BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS data_zeragem TIMESTAMP
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_separacao_sincronizado_nf 
            ON separacao(sincronizado_nf)
        """)
        
        logger.info("✅ Campos de sincronização adicionados")
        
        # 5. Migrar dados históricos
        logger.info("5. Migrando dados históricos do campo observacao...")
        
        # Contar registros antes da migração
        cur.execute("SELECT COUNT(*) FROM movimentacao_estoque WHERE numero_nf IS NULL AND observacao IS NOT NULL")
        total_migrar = cur.fetchone()[0]
        
        if total_migrar > 0:
            logger.info(f"  Migrando {total_migrar} registros...")
            
            # Migração com extração de dados
            cur.execute("""
                UPDATE movimentacao_estoque 
                SET 
                    numero_nf = CASE 
                        WHEN observacao LIKE '%NF %' THEN 
                            SUBSTRING(observacao FROM 'NF ([0-9]+)')
                        ELSE NULL 
                    END,
                    separacao_lote_id = CASE 
                        WHEN observacao LIKE '%lote separação %' OR observacao LIKE '%Lote %' THEN 
                            SUBSTRING(observacao FROM '[Ll]ote[ separação]* ([A-Za-z0-9_-]+)')
                        ELSE NULL 
                    END,
                    tipo_origem = CASE
                        WHEN observacao LIKE '%TAGPLUS%' THEN 'TAGPLUS'
                        WHEN observacao LIKE '%automática%' THEN 'ODOO'
                        ELSE 'LEGADO'
                    END,
                    status_nf = 'FATURADO'
                WHERE 
                    numero_nf IS NULL 
                    AND observacao IS NOT NULL
                    AND observacao != ''
            """)
            
            registros_atualizados = cur.rowcount
            logger.info(f"  ✓ {registros_atualizados} registros migrados")
            
            # Marcar movimentações "Sem Separação"
            cur.execute("""
                UPDATE movimentacao_estoque 
                SET 
                    tipo_origem = COALESCE(tipo_origem, 'LEGADO'),
                    status_nf = 'FATURADO'
                WHERE 
                    observacao LIKE '%Sem Separação%'
                    AND tipo_origem IS NULL
            """)
            
            sem_separacao = cur.rowcount
            if sem_separacao > 0:
                logger.info(f"  ✓ {sem_separacao} registros 'Sem Separação' marcados")
        else:
            logger.info("  ℹ️ Nenhum registro para migrar")
        
        # 6. Estatísticas finais
        logger.info("6. Coletando estatísticas pós-migração...")
        
        cur.execute("SELECT COUNT(*) FROM movimentacao_estoque")
        total_registros = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM movimentacao_estoque WHERE numero_nf IS NOT NULL")
        registros_com_nf = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM movimentacao_estoque WHERE separacao_lote_id IS NOT NULL")
        registros_com_lote = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM movimentacao_estoque WHERE tipo_origem = 'LEGADO'")
        registros_legado = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM movimentacao_estoque WHERE tipo_origem = 'ODOO'")
        registros_odoo = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM movimentacao_estoque WHERE tipo_origem = 'TAGPLUS'")
        registros_tagplus = cur.fetchone()[0]
        
        # Commit das alterações
        conn.commit()
        
        logger.info("========================================")
        logger.info("✅ MIGRATION CONCLUÍDA COM SUCESSO")
        logger.info("========================================")
        logger.info(f"Total de registros: {total_registros}")
        logger.info(f"Registros com NF: {registros_com_nf} ({registros_com_nf*100/total_registros:.1f}%)")
        logger.info(f"Registros com lote: {registros_com_lote} ({registros_com_lote*100/total_registros:.1f}%)")
        logger.info(f"Registros ODOO: {registros_odoo}")
        logger.info(f"Registros TAGPLUS: {registros_tagplus}")
        logger.info(f"Registros LEGADO: {registros_legado}")
        logger.info("========================================")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro durante a migration: {e}")
        conn.rollback()
        return False
        
    finally:
        cur.close()
        conn.close()

def verificar_estrutura_atual():
    """Verificar estrutura atual da tabela antes da migration"""
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        logger.info("Verificando estrutura atual da tabela movimentacao_estoque...")
        
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'movimentacao_estoque'
            ORDER BY ordinal_position
        """)
        
        colunas = cur.fetchall()
        
        logger.info("Colunas atuais:")
        for col in colunas:
            if col[2]:
                logger.info(f"  - {col[0]}: {col[1]}({col[2]})")
            else:
                logger.info(f"  - {col[0]}: {col[1]}")
        
        # Verificar se os novos campos já existem
        novos_campos = ['separacao_lote_id', 'numero_nf', 'num_pedido', 'tipo_origem', 'status_nf', 'codigo_embarque']
        campos_existentes = [col[0] for col in colunas]
        
        campos_faltando = [campo for campo in novos_campos if campo not in campos_existentes]
        
        if not campos_faltando:
            logger.warning("⚠️ Todos os campos já existem. Migration pode já ter sido executada.")
            resposta = input("Deseja continuar mesmo assim? (s/n): ")
            if resposta.lower() != 's':
                return False
        else:
            logger.info(f"Campos a serem adicionados: {', '.join(campos_faltando)}")
        
        return True
        
    finally:
        cur.close()
        conn.close()

def main():
    """Função principal"""
    
    logger.info("========================================")
    logger.info("MIGRATION DE MOVIMENTACAO_ESTOQUE")
    logger.info("========================================")
    logger.info(f"Data/Hora: {datetime.now()}")
    logger.info("========================================")
    
    # Verificar estrutura atual
    if not verificar_estrutura_atual():
        logger.info("Migration cancelada pelo usuário")
        return
    
    # Confirmar execução
    logger.info("")
    logger.warning("⚠️ ATENÇÃO: Esta migration irá:")
    logger.warning("  1. Adicionar novos campos em movimentacao_estoque")
    logger.warning("  2. Criar índices para melhor performance")
    logger.warning("  3. Migrar dados históricos do campo observacao")
    logger.warning("  4. Adicionar campos de sincronização em separacao")
    logger.info("")
    
    if os.environ.get('RENDER'):
        # No Render, executar automaticamente
        logger.info("Ambiente Render detectado. Executando automaticamente...")
        executar = True
    else:
        # Em ambiente local, pedir confirmação
        resposta = input("Deseja continuar? (s/n): ")
        executar = resposta.lower() == 's'
    
    if executar:
        sucesso = executar_migration()
        if sucesso:
            logger.info("✅ Migration executada com sucesso!")
            sys.exit(0)
        else:
            logger.error("❌ Migration falhou!")
            sys.exit(1)
    else:
        logger.info("Migration cancelada pelo usuário")
        sys.exit(0)

if __name__ == "__main__":
    main()