#!/usr/bin/env python
"""
Verificar estrutura das tabelas
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Verificar estrutura da tabela perfil_usuario
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'perfil_usuario'
        ORDER BY ordinal_position
    """)
    
    print("📋 Estrutura da tabela perfil_usuario:")
    for col in cur.fetchall():
        print(f"   - {col[0]}: {col[1]}")
    
    # Verificar estrutura da tabela usuarios
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'usuarios'
        AND column_name IN ('id', 'nome', 'email', 'perfil_id', 'perfil_nome')
        ORDER BY ordinal_position
    """)
    
    print("\n📋 Campos relevantes da tabela usuarios:")
    for col in cur.fetchall():
        print(f"   - {col[0]}: {col[1]}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Erro: {e}")