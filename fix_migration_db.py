#!/usr/bin/env python3
"""
Script para remover migração fantasma do banco PostgreSQL no Render
"""
import os
import psycopg2
from urllib.parse import urlparse

# Obter URL do banco do Render
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL não encontrada. Execute no Render!")
    exit(1)

# Parse da URL
url = urlparse(DATABASE_URL)

try:
    # Conectar ao PostgreSQL
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port,
        database=url.path[1:],
        user=url.username,
        password=url.password,
        sslmode='require'
    )
    cur = conn.cursor()
    
    print("✅ Conectado ao PostgreSQL no Render")
    
    # Verificar migrações atuais
    cur.execute("SELECT version_num FROM alembic_version")
    migrations = cur.fetchall()
    print(f"\n📋 Migrações atuais: {[m[0] for m in migrations]}")
    
    # Remover migração fantasma
    cur.execute("DELETE FROM alembic_version WHERE version_num = '1d81b88a3038'")
    deleted = cur.rowcount
    
    if deleted > 0:
        conn.commit()
        print(f"✅ Removida migração fantasma '1d81b88a3038'")
    else:
        print("ℹ️ Migração fantasma não encontrada (já removida?)")
    
    # Verificar migrações após limpeza
    cur.execute("SELECT version_num FROM alembic_version")
    migrations = cur.fetchall()
    print(f"\n📋 Migrações após limpeza: {[m[0] for m in migrations]}")
    
    # Se não houver migrações, adicionar a inicial
    if not migrations:
        cur.execute("INSERT INTO alembic_version (version_num) VALUES ('initial_consolidated_2025')")
        conn.commit()
        print("✅ Adicionada migração inicial")
    
    cur.close()
    conn.close()
    print("\n✅ Banco de dados limpo com sucesso!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)
