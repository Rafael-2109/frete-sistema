#!/usr/bin/env python3
"""
Script para aplicar migração direta via psycopg2
Resolve problema de codificação UTF-8
"""

import os
import psycopg2
from urllib.parse import urlparse

def aplicar_migração_direta():
    """Aplica migração usando psycopg2 direto com encoding explícito"""
    
    try:
        print("🔄 Conectando diretamente ao PostgreSQL...")
        
        # Obter DATABASE_URL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL não encontrada")
            return False
            
        # Parse da URL
        url = urlparse(database_url)
        
        # Conectar com encoding explícito
        conn = psycopg2.connect(
            host=url.hostname,
            database=url.path[1:],  # Remove '/' do início
            user=url.username,
            password=url.password,
            port=url.port or 5432,
            client_encoding='utf8'
        )
        
        print("✅ Conectado ao banco PostgreSQL!")
        
        cursor = conn.cursor()
        
        # SQL para adicionar colunas
        sql_adicionar_colunas = """
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
        """
        
        print("🔄 Executando SQL de migração...")
        cursor.execute(sql_adicionar_colunas)
        conn.commit()
        
        print("✅ Migração executada com sucesso!")
        
        # Verificar se as colunas foram criadas
        print("\n🔍 Verificando colunas criadas...")
        
        sql_verificar = """
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
        
        cursor.execute(sql_verificar)
        resultado = cursor.fetchall()
        
        if resultado:
            print("\n📊 Colunas encontradas:")
            for row in resultado:
                print(f"  - {row[0]}: {row[1]}({row[3]}), nullable: {row[2]}")
        else:
            print("⚠️ Nenhuma coluna encontrada - pode haver problema")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na migração direta: {str(e)}")
        return False

def popular_dados_rota():
    """Popula as colunas rota e sub_rota com dados existentes"""
    
    try:
        print("\n🔄 Populando dados de rota e sub_rota...")
        
        # Obter DATABASE_URL
        database_url = os.environ.get('DATABASE_URL')
        url = urlparse(database_url)
        
        # Conectar
        conn = psycopg2.connect(
            host=url.hostname,
            database=url.path[1:],
            user=url.username,
            password=url.password,
            port=url.port or 5432,
            client_encoding='utf8'
        )
        
        cursor = conn.cursor()
        
        # Popular rota baseado em cod_uf
        sql_popular_rota = """
        UPDATE carteira_principal 
        SET rota = (
            SELECT cr.rota 
            FROM cadastro_rota cr 
            WHERE cr.cod_uf = carteira_principal.cod_uf 
            AND cr.ativa = true 
            LIMIT 1
        )
        WHERE carteira_principal.rota IS NULL 
        AND carteira_principal.cod_uf IS NOT NULL;
        """
        
        cursor.execute(sql_popular_rota)
        rota_count = cursor.rowcount
        print(f"  📍 {rota_count} registros atualizados com rota")
        
        # Popular sub_rota baseado em cod_uf + nome_cidade
        sql_popular_sub_rota = """
        UPDATE carteira_principal 
        SET sub_rota = (
            SELECT csr.sub_rota 
            FROM cadastro_sub_rota csr 
            WHERE csr.cod_uf = carteira_principal.cod_uf 
            AND csr.nome_cidade = carteira_principal.nome_cidade
            AND csr.ativa = true 
            LIMIT 1
        )
        WHERE carteira_principal.sub_rota IS NULL 
        AND carteira_principal.cod_uf IS NOT NULL 
        AND carteira_principal.nome_cidade IS NOT NULL;
        """
        
        cursor.execute(sql_popular_sub_rota)
        sub_rota_count = cursor.rowcount
        print(f"  🗺️ {sub_rota_count} registros atualizados com sub_rota")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Dados populados com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao popular dados: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Script de Migração Direta - Colunas Rota e Sub-rota")
    print("=" * 55)
    
    # Aplicar migração
    sucesso_migração = aplicar_migração_direta()
    
    if sucesso_migração:
        # Perguntar se quer popular dados
        resposta = input("\n❓ Deseja popular os dados de rota/sub_rota automaticamente? (s/N): ")
        
        if resposta.lower() in ['s', 'sim', 'y', 'yes']:
            popular_dados_rota()
        else:
            print("💡 Dados não populados. Use as funções de carteira que populam dinamicamente.")
    
    print("\n🎯 Script concluído!") 