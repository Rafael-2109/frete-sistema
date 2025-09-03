#!/usr/bin/env python3
"""
Script de Migração: Pedido → Separacao
Data: 2025-01-29

Objetivo: Copiar dados da tabela Pedido para os novos campos em Separacao
Estratégia: Cópia direta sem transformações
"""

import os
import sys
from datetime import datetime
import logging

# Configurar path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from sqlalchemy import text

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrar_dados():
    """
    Migra dados de Pedido para Separacao via UPDATE direto
    """
    
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("Iniciando migração Pedido → Separacao...")
            
            # Query SQL direta para UPDATE em massa
            # Copia os campos diretamente sem transformação
            sql_update = text("""
                UPDATE separacao s
                SET 
                    -- Status do pedido (cópia direta)
                    status = COALESCE(p.status, 'ABERTO'),
                    
                    -- Flag NF no CD
                    nf_cd = COALESCE(p.nf_cd, FALSE),
                    
                    -- Data de embarque
                    data_embarque = p.data_embarque,
                    
                    -- Campos normalizados de localização
                    cidade_normalizada = p.cidade_normalizada,
                    uf_normalizada = p.uf_normalizada,
                    codigo_ibge = p.codigo_ibge,
                    
                    -- Controle de impressão (assumir false se não existir)
                    separacao_impressa = COALESCE(p.separacao_impressa, FALSE),
                    separacao_impressa_em = p.separacao_impressa_em,
                    separacao_impressa_por = p.separacao_impressa_por
                    
                FROM pedidos p
                WHERE s.separacao_lote_id = p.separacao_lote_id
                AND s.separacao_lote_id IS NOT NULL
                AND p.separacao_lote_id IS NOT NULL
            """)
            
            logger.info("Executando UPDATE em massa...")
            result = db.session.execute(sql_update)
            linhas_atualizadas = result.rowcount
            
            logger.info(f"✅ {linhas_atualizadas} registros atualizados em Separacao")
            
            # Verificar quantos registros ficaram sem atualização
            sql_verificacao = text("""
                SELECT COUNT(*) as total
                FROM separacao s
                WHERE s.separacao_lote_id IS NOT NULL
                AND s.status IS NULL
            """)
            
            result = db.session.execute(sql_verificacao).fetchone()
            sem_atualizacao = result.total if result else 0
            
            if sem_atualizacao > 0:
                logger.warning(f"⚠️ {sem_atualizacao} registros em Separacao sem correspondência em Pedido")
            
            # Estatísticas finais
            sql_stats = text("""
                SELECT 
                    status,
                    COUNT(*) as total,
                    COUNT(DISTINCT separacao_lote_id) as lotes_distintos
                FROM separacao
                WHERE separacao_lote_id IS NOT NULL
                GROUP BY status
                ORDER BY total DESC
            """)
            
            logger.info("\n📊 Distribuição de status após migração:")
            for row in db.session.execute(sql_stats):
                logger.info(f"  - {row.status or 'NULL'}: {row.total} registros ({row.lotes_distintos} lotes)")
            
            # Commit das alterações
            db.session.commit()
            logger.info("\n✅ Migração concluída com sucesso!")
            
            # Informações adicionais
            logger.info("\n📋 Próximos passos:")
            logger.info("1. Criar VIEW pedidos para manter compatibilidade")
            logger.info("2. Atualizar aplicação para usar Separacao como fonte principal")
            logger.info("3. Remover tabela Pedido após validação completa")
            
        except Exception as e:
            logger.error(f"❌ Erro durante migração: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()

if __name__ == "__main__":
    migrar_dados()