#!/usr/bin/env python3
"""
Script para executar migração de alertas de separações COTADAS
Pode ser executado localmente ou no Render
"""

import os
import psycopg2
from psycopg2 import sql
from urllib.parse import urlparse

def executar_migracao():
    """Executa a migração do banco de dados"""
    
    # Obter DATABASE_URL do ambiente
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada!")
        return False
    
    # Parse da URL
    parsed = urlparse(database_url)
    
    try:
        # Conectar ao banco
        print("🔌 Conectando ao banco de dados...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Executar migração
        print("📊 Criando tabela alertas_separacao_cotada...")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alertas_separacao_cotada (
                id SERIAL PRIMARY KEY,
                separacao_lote_id VARCHAR(50) NOT NULL,
                num_pedido VARCHAR(50) NOT NULL,
                cod_produto VARCHAR(50) NOT NULL,
                tipo_alteracao VARCHAR(20) NOT NULL CHECK (tipo_alteracao IN ('REDUCAO', 'AUMENTO', 'REMOCAO', 'ADICAO')),
                qtd_anterior NUMERIC(15,3) DEFAULT 0,
                qtd_nova NUMERIC(15,3) DEFAULT 0,
                qtd_diferenca NUMERIC(15,3) DEFAULT 0,
                reimpresso BOOLEAN DEFAULT FALSE NOT NULL,
                data_alerta TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                data_reimpressao TIMESTAMP,
                reimpresso_por VARCHAR(100),
                nome_produto VARCHAR(255),
                cliente VARCHAR(255),
                embarque_numero INTEGER,
                tipo_separacao VARCHAR(10) CHECK (tipo_separacao IN ('TOTAL', 'PARCIAL')),
                observacao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print("📑 Criando índices...")
        
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_alertas_separacao_lote ON alertas_separacao_cotada(separacao_lote_id)",
            "CREATE INDEX IF NOT EXISTS idx_alertas_num_pedido ON alertas_separacao_cotada(num_pedido)",
            "CREATE INDEX IF NOT EXISTS idx_alertas_reimpresso ON alertas_separacao_cotada(reimpresso)",
            "CREATE INDEX IF NOT EXISTS idx_alertas_data_alerta ON alertas_separacao_cotada(data_alerta DESC)"
        ]
        
        for idx_sql in indices:
            cur.execute(idx_sql)
        
        print("🔧 Criando trigger para updated_at...")
        
        cur.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)
        
        cur.execute("""
            CREATE TRIGGER update_alertas_separacao_updated_at 
            BEFORE UPDATE ON alertas_separacao_cotada 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column()
        """)
        
        # Commit das alterações
        conn.commit()
        
        # Verificar se tabela foi criada
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'alertas_separacao_cotada'
            )
        """)
        
        existe = cur.fetchone()[0]
        
        if existe:
            print("✅ Tabela criada com sucesso!")
            
            # Contar colunas
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'alertas_separacao_cotada'
            """)
            
            num_colunas = cur.fetchone()[0]
            print(f"📋 Tabela possui {num_colunas} colunas")
            
            return True
        else:
            print("❌ Erro: Tabela não foi criada")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao executar migração: {e}")
        return False
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        print("🔌 Conexão fechada")

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 MIGRAÇÃO: Alertas de Separações COTADAS")
    print("=" * 50)
    
    sucesso = executar_migracao()
    
    if sucesso:
        print("\n✨ Migração concluída com sucesso!")
    else:
        print("\n❌ Migração falhou!")
        exit(1)