#!/usr/bin/env python3
"""
Script de inicialização para corrigir problemas no banco de dados
Este script deve ser executado automaticamente na inicialização
"""
import os
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

def fix_projecao_estoque_cache_table(app, db):
    """Adiciona colunas faltantes na tabela projecao_estoque_cache"""
    try:
        with app.app_context():
            # Verificar se as colunas já existem
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'projecao_estoque_cache'
            """))
            
            existing_columns = {row[0] for row in result}
            logger.info(f"Colunas existentes em projecao_estoque_cache: {existing_columns}")
            
            # Lista de colunas necessárias
            required_columns = {
                'dia_offset': 'INTEGER DEFAULT 0',
                'estoque_inicial': 'NUMERIC(15,3) DEFAULT 0',
                'saida_prevista': 'NUMERIC(15,3) DEFAULT 0',
                'producao_programada': 'NUMERIC(15,3) DEFAULT 0',
                'estoque_final': 'NUMERIC(15,3) DEFAULT 0',
                'atualizado_em': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            
            # Adicionar colunas faltantes
            columns_added = []
            for column_name, column_type in required_columns.items():
                if column_name not in existing_columns:
                    try:
                        db.session.execute(text(f"""
                            ALTER TABLE projecao_estoque_cache 
                            ADD COLUMN {column_name} {column_type}
                        """))
                        columns_added.append(column_name)
                        logger.info(f"✅ Coluna {column_name} adicionada")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao adicionar coluna {column_name}: {e}")
            
            if columns_added:
                # Preencher dia_offset se foi adicionado
                if 'dia_offset' in columns_added:
                    db.session.execute(text("""
                        UPDATE projecao_estoque_cache p1
                        SET dia_offset = COALESCE((
                            SELECT COUNT(DISTINCT p2.data_projecao)
                            FROM projecao_estoque_cache p2
                            WHERE p2.cod_produto = p1.cod_produto
                            AND p2.data_projecao < p1.data_projecao
                        ), 0)
                        WHERE dia_offset IS NULL
                    """))
                    
                    # Tornar NOT NULL após preencher
                    db.session.execute(text("""
                        ALTER TABLE projecao_estoque_cache 
                        ALTER COLUMN dia_offset SET NOT NULL
                    """))
                
                db.session.commit()
                logger.info(f"✅ Tabela projecao_estoque_cache corrigida. Colunas adicionadas: {columns_added}")
            else:
                logger.info("✅ Tabela projecao_estoque_cache já está correta")
                
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro ao corrigir tabela projecao_estoque_cache: {e}")
        db.session.rollback()
        return False

def run_all_fixes(app, db):
    """Executa todas as correções necessárias"""
    logger.info("🔧 Iniciando correções no banco de dados...")
    
    # Fix 1: Corrigir tabela projecao_estoque_cache
    fix_projecao_estoque_cache_table(app, db)
    
    logger.info("✅ Correções concluídas")

if __name__ == "__main__":
    # Para execução manual
    from app import create_app, db
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = create_app()
    run_all_fixes(app, db)