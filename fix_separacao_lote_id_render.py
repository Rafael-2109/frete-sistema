#!/usr/bin/env python
"""
Script EMERGENCIAL para adicionar campo separacao_lote_id no Render
"""
import os
import psycopg2
from urllib.parse import urlparse

# Conectar ao banco
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("❌ DATABASE_URL não encontrada!")
    exit(1)

result = urlparse(database_url)
conn = psycopg2.connect(
    database=result.path[1:],
    user=result.username,
    password=result.password,
    host=result.hostname,
    port=result.port
)
cur = conn.cursor()

print("🔧 Adicionando campo separacao_lote_id AGORA...")

try:
    # 1. Verificar se o campo existe
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'pre_separacao_item' 
        AND column_name = 'separacao_lote_id'
    """)
    
    if not cur.fetchone():
        print("❌ Campo NÃO existe! Adicionando imediatamente...")
        
        # Adicionar o campo
        cur.execute("""
            ALTER TABLE pre_separacao_item 
            ADD COLUMN separacao_lote_id VARCHAR(50)
        """)
        
        # Criar índice
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_pre_separacao_item_separacao_lote_id 
            ON pre_separacao_item(separacao_lote_id)
        """)
        
        conn.commit()
        print("✅ Campo adicionado com sucesso!")
    else:
        print("✅ Campo já existe")
    
    # 2. Verificar estrutura final
    cur.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'pre_separacao_item' 
        ORDER BY ordinal_position
    """)
    
    print("\n📊 Estrutura atual da tabela:")
    for col in cur.fetchall():
        print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
    
    print("\n✅ PRONTO! O campo foi adicionado.")
    
except Exception as e:
    conn.rollback()
    print(f"❌ ERRO: {e}")
    raise
finally:
    cur.close()
    conn.close() 