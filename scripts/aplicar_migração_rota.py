#!/usr/bin/env python3
"""
Script para aplicar migração das colunas rota e sub_rota
Resolve o problema: column carteira_principal.rota does not exist
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text
import logging

def aplicar_migração_rota():
    """Aplica migração para adicionar colunas rota e sub_rota"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Aplicando migração das colunas rota e sub_rota...")
            
            # SQL para adicionar as colunas
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
            
            # Executar SQL
            db.session.execute(text(sql_adicionar_colunas))
            db.session.commit()
            
            print("✅ Migração aplicada com sucesso!")
            
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
            
            resultado = db.session.execute(text(sql_verificar)).fetchall()
            
            if resultado:
                print("\n📊 Colunas encontradas:")
                for row in resultado:
                    print(f"  - {row.column_name}: {row.data_type}({row.character_maximum_length}), nullable: {row.is_nullable}")
            else:
                print("⚠️ Nenhuma coluna encontrada - pode haver problema")
                
            return True
            
        except Exception as e:
            print(f"❌ Erro ao aplicar migração: {str(e)}")
            db.session.rollback()
            return False

def popular_dados_rota():
    """Popula as colunas rota e sub_rota com dados existentes"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\n🔄 Populando dados de rota e sub_rota...")
            
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
            
            result_rota = db.session.execute(text(sql_popular_rota))
            print(f"  📍 {result_rota.rowcount} registros atualizados com rota")
            
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
            
            result_sub_rota = db.session.execute(text(sql_popular_sub_rota))
            print(f"  🗺️ {result_sub_rota.rowcount} registros atualizados com sub_rota")
            
            db.session.commit()
            print("✅ Dados populados com sucesso!")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao popular dados: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🚀 Script de Migração - Colunas Rota e Sub-rota")
    print("=" * 50)
    
    # Aplicar migração
    sucesso_migração = aplicar_migração_rota()
    
    if sucesso_migração:
        # Perguntar se quer popular dados
        resposta = input("\n❓ Deseja popular os dados de rota/sub_rota automaticamente? (s/N): ")
        
        if resposta.lower() in ['s', 'sim', 'y', 'yes']:
            popular_dados_rota()
        else:
            print("💡 Dados não populados. Use as funções de carteira que populam dinamicamente.")
    
    print("\n🎯 Script concluído!") 