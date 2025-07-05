#!/usr/bin/env python3
"""
CORREÇÃO DEFINITIVA DAS MIGRAÇÕES
Remove migrações problemáticas e cria uma única migração inicial
"""

import os
import shutil
from datetime import datetime

def backup_migrations():
    """Faz backup das migrações atuais"""
    print("📦 Fazendo backup das migrações...")
    backup_dir = f"migrations_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree("migrations/versions", backup_dir)
    print(f"   ✅ Backup criado: {backup_dir}")
    return backup_dir

def remove_problematic_migrations():
    """Remove as migrações problemáticas"""
    print("🗑️ Removendo migrações problemáticas...")
    
    to_remove = [
        "migrations/versions/render_fix_20250704_204702.py",
        "migrations/versions/ai_consolidada_20250704_201224.py",
        "migrations/versions/merge_heads_20250705_093743.py",
        "migrations/versions/reset_heads_2025.py",
        "migrations/versions/13d736405224_adicionar_tabelas_de_aprendizado_.py"  # Duplicada
    ]
    
    for file in to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"   ❌ Removido: {os.path.basename(file)}")
    
    # Limpar __pycache__
    pycache_dir = "migrations/versions/__pycache__"
    if os.path.exists(pycache_dir):
        shutil.rmtree(pycache_dir)
        print("   ❌ Cache limpo")

def create_initial_migration():
    """Cria migração inicial consolidada"""
    print("✨ Criando migração inicial consolidada...")
    
    migration_content = '''"""Migração inicial consolidada

Revision ID: initial_consolidated_2025
Revises: 
Create Date: 2025-07-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial_consolidated_2025'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """
    Migração inicial que cria todas as tabelas necessárias.
    As tabelas são criadas pelo init_db.py, então esta migração
    apenas marca o banco como atualizado.
    """
    # Esta migração serve apenas para marcar o banco como migrado
    # As tabelas já são criadas pelo init_db.py
    pass

def downgrade():
    """
    Não fazer downgrade da migração inicial
    """
    pass
'''
    
    filename = "migrations/versions/initial_consolidated_2025.py"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(migration_content)
    
    print(f"   ✅ Migração inicial criada: {filename}")

def update_other_migrations():
    """Atualiza outras migrações para apontar para a inicial"""
    print("🔧 Atualizando referências das outras migrações...")
    
    migrations_dir = "migrations/versions"
    
    for filename in os.listdir(migrations_dir):
        if filename.endswith('.py') and filename != 'initial_consolidated_2025.py' and filename != '__init__.py':
            filepath = os.path.join(migrations_dir, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Se a migração tem down_revision = None, atualizar para apontar para inicial
            if "down_revision = None" in content:
                content = content.replace(
                    "down_revision = None",
                    "down_revision = 'initial_consolidated_2025'"
                )
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"   ✏️ Atualizada: {filename}")

def create_render_command():
    """Cria comando simplificado para o Render"""
    print("🚀 Criando comando otimizado para Render...")
    
    command_content = '''#!/bin/bash
# Comando otimizado para o Render

echo "🚀 INICIANDO SISTEMA NO RENDER"

# 1. Aplicar migração inicial se necessário
echo "📌 Aplicando migração inicial..."
flask db stamp initial_consolidated_2025 2>/dev/null || true

# 2. Aplicar outras migrações
echo "🔄 Aplicando migrações..."
flask db upgrade || echo "⚠️ Aviso em migrações, mas continuando..."

# 3. Inicializar banco
echo "🗄️ Inicializando banco..."
python init_db.py

# 4. Iniciar servidor
echo "🌐 Iniciando servidor..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class sync --timeout 600 --max-requests 1000 --max-requests-jitter 100 --keep-alive 10 --preload --worker-tmp-dir /dev/shm run:app
'''
    
    with open('render_command.sh', 'w', encoding='utf-8') as f:
        f.write(command_content)
    
    try:
        os.chmod('render_command.sh', 0o755)
    except:
        pass
    
    print("   ✅ Comando criado: render_command.sh")

def main():
    """Executa correção completa"""
    print("🎯 CORREÇÃO DEFINITIVA DAS MIGRAÇÕES")
    print("=" * 50)
    
    # 1. Backup
    backup_dir = backup_migrations()
    
    # 2. Remover problemáticas
    remove_problematic_migrations()
    
    # 3. Criar inicial
    create_initial_migration()
    
    # 4. Atualizar outras
    update_other_migrations()
    
    # 5. Criar comando Render
    create_render_command()
    
    print("\n" + "=" * 50)
    print("✅ CORREÇÃO CONCLUÍDA!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Executar localmente para testar:")
    print("   python fix_migrations_definitivo.py")
    print("   flask db stamp initial_consolidated_2025")
    print("   flask db upgrade")
    print("\n2. Commit e push:")
    print("   git add .")
    print("   git commit -m 'fix: Correção definitiva migrações - consolidação inicial'")
    print("   git push")
    print("\n3. No Render, usar o Start Command:")
    print("   ./render_command.sh")
    print(f"\n📁 Backup salvo em: {backup_dir}")

if __name__ == "__main__":
    main() 