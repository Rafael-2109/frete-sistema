"""
Script para corrigir problema de migração no Render
Problema: Can't locate revision identified by '1d81b88a3038'
"""

import os
import psycopg2
from urllib.parse import urlparse

def fix_migration():
    """Corrige a revisão no alembic_version para apontar para o head correto"""
    
    # Obter DATABASE_URL do ambiente
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada nas variáveis de ambiente")
        return False
    
    # Parse da URL
    result = urlparse(database_url)
    
    try:
        # Conectar ao banco
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        cur = conn.cursor()
        
        print("✅ Conectado ao banco de dados")
        
        # Verificar a revisão atual
        cur.execute("SELECT version_num FROM alembic_version")
        current_version = cur.fetchone()
        
        if current_version:
            print(f"📍 Revisão atual no banco: {current_version[0]}")
        else:
            print("⚠️ Nenhuma revisão encontrada na tabela alembic_version")
            
        # Atualizar para o head correto (última migração válida)
        # De acordo com o histórico, o head é: 0c6e9779f29c
        new_version = '0c6e9779f29c'
        
        if current_version:
            cur.execute("UPDATE alembic_version SET version_num = %s", (new_version,))
            print(f"✅ Revisão atualizada para: {new_version}")
        else:
            cur.execute("INSERT INTO alembic_version (version_num) VALUES (%s)", (new_version,))
            print(f"✅ Revisão inserida: {new_version}")
        
        # Commit das alterações
        conn.commit()
        print("✅ Alterações salvas no banco")
        
        # Verificar se a coluna peso_unitario_produto existe
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'faturamento_produto' 
            AND column_name IN ('peso_unitario_produto', 'peso_total')
        """)
        
        existing_columns = [row[0] for row in cur.fetchall()]
        
        if 'peso_unitario_produto' not in existing_columns:
            print("⚠️ Coluna 'peso_unitario_produto' não existe - aplicando migração...")
            try:
                cur.execute("""
                    ALTER TABLE faturamento_produto 
                    ADD COLUMN peso_unitario_produto NUMERIC(15, 3) DEFAULT 0
                """)
                print("✅ Coluna 'peso_unitario_produto' adicionada")
            except Exception as e:
                print(f"❌ Erro ao adicionar coluna peso_unitario_produto: {e}")
                
        if 'peso_total' not in existing_columns:
            print("⚠️ Coluna 'peso_total' não existe - aplicando migração...")
            try:
                cur.execute("""
                    ALTER TABLE faturamento_produto 
                    ADD COLUMN peso_total NUMERIC(15, 3) DEFAULT 0
                """)
                print("✅ Coluna 'peso_total' adicionada")
            except Exception as e:
                print(f"❌ Erro ao adicionar coluna peso_total: {e}")
        
        # Commit final
        conn.commit()
        
        # Fechar conexão
        cur.close()
        conn.close()
        
        print("\n🎉 Correção aplicada com sucesso!")
        print("Agora você pode rodar 'flask db upgrade' novamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir migração: {e}")
        return False

if __name__ == "__main__":
    fix_migration() 