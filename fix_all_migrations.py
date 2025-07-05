#!/usr/bin/env python3
"""
Script robusto para corrigir TODAS as migrações fantasmas no PostgreSQL
"""

import os
import psycopg2
from urllib.parse import urlparse
import subprocess

def get_db_connection():
    """Conecta ao banco PostgreSQL"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("⚠️ DATABASE_URL não encontrada")
        return None
    
    url = urlparse(database_url)
    return psycopg2.connect(
        host=url.hostname,
        port=url.port,
        database=url.path[1:],
        user=url.username,
        password=url.password,
        sslmode='require'
    )

def list_all_migrations():
    """Lista todas as migrações no banco"""
    print("\n📋 Listando migrações no banco de dados...")
    
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute("SELECT version_num FROM alembic_version")
        migrations = cursor.fetchall()
        
        print(f"✅ {len(migrations)} migrações encontradas:")
        for mig in migrations:
            print(f"   - {mig[0]}")
        
        cursor.close()
        conn.close()
        
        return [m[0] for m in migrations]
        
    except Exception as e:
        print(f"❌ Erro ao listar migrações: {e}")
        return []

def get_valid_migrations():
    """Obtém lista de migrações válidas do diretório"""
    print("\n📁 Listando migrações válidas no sistema...")
    
    migrations_dir = "migrations/versions"
    valid_migrations = []
    
    if os.path.exists(migrations_dir):
        for file in os.listdir(migrations_dir):
            if file.endswith('.py') and not file.startswith('__'):
                # Extrai o ID da migração do nome do arquivo
                migration_id = file.split('_')[0]
                valid_migrations.append(migration_id)
                print(f"   ✓ {migration_id}")
    else:
        print("❌ Diretório de migrações não encontrado")
    
    return valid_migrations

def remove_phantom_migrations():
    """Remove migrações fantasmas do banco"""
    print("\n🔧 Verificando migrações fantasmas...")
    
    db_migrations = list_all_migrations()
    valid_migrations = get_valid_migrations()
    
    if not db_migrations:
        print("⚠️ Nenhuma migração no banco")
        return
    
    phantom_migrations = [m for m in db_migrations if m not in valid_migrations]
    
    if not phantom_migrations:
        print("✅ Nenhuma migração fantasma encontrada!")
        return
    
    print(f"\n⚠️ {len(phantom_migrations)} migrações fantasmas encontradas:")
    for phantom in phantom_migrations:
        print(f"   - {phantom}")
    
    try:
        conn = get_db_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        for phantom in phantom_migrations:
            print(f"\n🗑️ Removendo migração fantasma: {phantom}")
            cursor.execute("DELETE FROM alembic_version WHERE version_num = %s", (phantom,))
            print(f"   ✅ Removida!")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Todas as migrações fantasmas foram removidas!")
        
    except Exception as e:
        print(f"❌ Erro ao remover migrações: {e}")

def fix_current_migration():
    """Corrige a migração atual para a mais recente válida"""
    print("\n🔄 Corrigindo migração atual...")
    
    valid_migrations = get_valid_migrations()
    if not valid_migrations:
        print("❌ Nenhuma migração válida encontrada")
        return
    
    # Ordena para pegar a mais recente
    valid_migrations.sort(reverse=True)
    latest_migration = valid_migrations[0]
    
    try:
        conn = get_db_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # Limpa tabela de migrações
        cursor.execute("DELETE FROM alembic_version")
        
        # Insere a migração mais recente
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES (%s)", (latest_migration,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Migração atual definida para: {latest_migration}")
        
    except Exception as e:
        print(f"❌ Erro ao corrigir migração: {e}")

def main():
    """Executa todas as correções"""
    print("🚀 CORRETOR DE MIGRAÇÕES DO RENDER")
    print("=" * 50)
    
    # 1. Remove migrações fantasmas
    remove_phantom_migrations()
    
    # 2. Corrige migração atual
    fix_current_migration()
    
    # 3. Lista estado final
    print("\n📊 ESTADO FINAL:")
    list_all_migrations()
    
    print("\n✅ Processo concluído!")

if __name__ == "__main__":
    main() 