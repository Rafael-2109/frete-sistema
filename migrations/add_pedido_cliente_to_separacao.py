#!/usr/bin/env python3
"""
Migração para adicionar campo pedido_cliente na tabela separacao
Data: 2025-08-23
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def adicionar_campo_pedido_cliente():
    """
    Adiciona campo pedido_cliente na tabela separacao
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar se o campo já existe
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'separacao' 
                AND column_name = 'pedido_cliente'
            """))
            
            if result.fetchone():
                logger.info("Campo pedido_cliente já existe na tabela separacao")
                return
            
            # Adicionar o campo
            logger.info("Adicionando campo pedido_cliente na tabela separacao...")
            db.session.execute(text("""
                ALTER TABLE separacao 
                ADD COLUMN pedido_cliente VARCHAR(100)
            """))
            
            # Criar índice para melhor performance
            logger.info("Criando índice para pedido_cliente...")
            db.session.execute(text("""
                CREATE INDEX idx_separacao_pedido_cliente 
                ON separacao(pedido_cliente)
            """))
            
            # Preencher campo com dados existentes da CarteiraPrincipal
            logger.info("Preenchendo pedido_cliente com dados existentes...")
            db.session.execute(text("""
                UPDATE separacao s
                SET pedido_cliente = (
                    SELECT cp.pedido_cliente
                    FROM carteira_principal cp
                    WHERE cp.num_pedido = s.num_pedido
                    AND cp.ativo = true
                    LIMIT 1
                )
                WHERE s.pedido_cliente IS NULL
            """))
            
            db.session.commit()
            
            # Verificar quantos registros foram atualizados
            result = db.session.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(pedido_cliente) as com_pedido_cliente
                FROM separacao
            """))
            row = result.fetchone()
            
            logger.info(f"✅ Campo adicionado com sucesso!")
            logger.info(f"   Total de registros: {row[0]}")
            logger.info(f"   Registros com pedido_cliente: {row[1]}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar campo: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    adicionar_campo_pedido_cliente()