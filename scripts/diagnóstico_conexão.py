#!/usr/bin/env python3
"""
Script para diagnosticar problema de encoding na conexão PostgreSQL
"""

import os
from urllib.parse import urlparse

def diagnosticar_database_url():
    """Diagnostica a DATABASE_URL caracter por caracter"""
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada")
        return False
    
    print(f"🔍 DATABASE_URL: {database_url}")
    print(f"📏 Comprimento: {len(database_url)} caracteres")
    
    # Mostrar caracter na posição 82 (onde está dando erro)
    if len(database_url) > 82:
        char_82 = database_url[82]
        print(f"🎯 Caracter na posição 82: '{char_82}' (ord: {ord(char_82)})")
        
        # Mostrar contexto ao redor da posição 82
        start = max(0, 82 - 10)
        end = min(len(database_url), 82 + 10)
        contexto = database_url[start:end]
        print(f"📍 Contexto (pos {start}-{end}): '{contexto}'")
    else:
        print("⚠️ String menor que 82 caracteres")
    
    # Tentar parse da URL
    try:
        url = urlparse(database_url)
        print(f"✅ Parse URL:")
        print(f"  - Host: {url.hostname}")
        print(f"  - Database: {url.path[1:]}")
        print(f"  - User: {url.username}")
        print(f"  - Port: {url.port}")
        return True
    except Exception as e:
        print(f"❌ Erro no parse da URL: {e}")
        return False

def tentar_conexão_simples():
    """Tenta conexão mais básica possível"""
    
    try:
        import psycopg2
        
        database_url = os.environ.get('DATABASE_URL')
        
        # Tentar encoding latin-1 primeiro
        print("\n🔄 Tentando conexão com encoding latin-1...")
        
        url = urlparse(database_url)
        
        conn = psycopg2.connect(
            host=url.hostname,
            database=url.path[1:],
            user=url.username,
            password=url.password,
            port=url.port or 5432,
            client_encoding='latin-1'  # Tentar encoding diferente
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        if version:
            print(f"✅ Conectado! PostgreSQL version: {version[0]}")
        else:
            print("✅ Conectado! (versão não obtida)")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def criar_migração_sql_arquivo():
    """Cria arquivo SQL que pode ser executado externamente"""
    
    sql_content = """-- Migração para adicionar colunas rota e sub_rota
-- Execute este SQL diretamente no banco PostgreSQL

DO $$
BEGIN
    -- Adicionar coluna rota se não existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'carteira_principal' 
        AND column_name = 'rota'
    ) THEN
        ALTER TABLE carteira_principal ADD COLUMN rota VARCHAR(50);
        RAISE NOTICE 'Coluna rota adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna rota já existe';
    END IF;

    -- Adicionar coluna sub_rota se não existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'carteira_principal' 
        AND column_name = 'sub_rota'
    ) THEN
        ALTER TABLE carteira_principal ADD COLUMN sub_rota VARCHAR(50);
        RAISE NOTICE 'Coluna sub_rota adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna sub_rota já existe';
    END IF;
END $$;

-- Verificar se as colunas foram criadas
SELECT 
    column_name,
    data_type,
    is_nullable,
    character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'carteira_principal' 
AND column_name IN ('rota', 'sub_rota')
ORDER BY column_name;
"""
    
    with open('scripts/migração_manual.sql', 'w', encoding='utf-8') as f:
        f.write(sql_content)
    
    print("📝 Arquivo SQL criado: scripts/migração_manual.sql")
    print("💡 Execute este arquivo diretamente no banco PostgreSQL via:")
    print("   - Render Dashboard → Database → Query")
    print("   - ou pgAdmin, DBeaver, etc.")

if __name__ == "__main__":
    print("🔍 Diagnóstico de Conexão PostgreSQL")
    print("=" * 40)
    
    # Diagnosticar URL
    if diagnosticar_database_url():
        
        # Tentar conexão simples
        if not tentar_conexão_simples():
            print("\n💡 Conexão falhou. Criando arquivo SQL para execução manual...")
            criar_migração_sql_arquivo()
    
    print("\n🎯 Diagnóstico concluído!") 