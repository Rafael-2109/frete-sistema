#!/usr/bin/env python
"""
Verificar estrutura das tabelas de permissões
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Verificar tabela permissao_usuario
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'permissao_usuario'
        ORDER BY ordinal_position
    """)
    
    print("📋 Estrutura da tabela permissao_usuario:")
    for col in cur.fetchall():
        print(f"   - {col[0]}: {col[1]}")
    
    # Verificar tabela modulo_sistema
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'modulo_sistema'
        ORDER BY ordinal_position
    """)
    
    print("\n📋 Estrutura da tabela modulo_sistema:")
    for col in cur.fetchall():
        print(f"   - {col[0]}: {col[1]}")
    
    # Listar todos os módulos
    cur.execute("SELECT id, nome FROM modulo_sistema")
    print("\n📋 Módulos existentes:")
    for mod in cur.fetchall():
        print(f"   - ID {mod[0]}: {mod[1]}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Erro: {e}")