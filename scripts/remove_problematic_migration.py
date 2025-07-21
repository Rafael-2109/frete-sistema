#!/usr/bin/env python3
"""
Script para remover migration problemática e resetar estado
"""

import os
import sys
from app import create_app
from flask_migrate import stamp

def main():
    print("🔧 Removendo migration problemática...")
    
    # Encontrar e remover migration problemática
    migrations_dir = "migrations/versions"
    problematic_files = []
    
    if os.path.exists(migrations_dir):
        for filename in os.listdir(migrations_dir):
            if "016dfad" in filename or "migração_equipe_vendas" in filename:
                problematic_files.append(filename)
    
    if problematic_files:
        print(f"📁 Encontrados arquivos problemáticos: {problematic_files}")
        for file in problematic_files:
            file_path = os.path.join(migrations_dir, file)
            try:
                os.remove(file_path)
                print(f"✅ Removido: {file}")
            except Exception as e:
                print(f"❌ Erro ao remover {file}: {e}")
    else:
        print("✅ Nenhum arquivo problemático encontrado")
    
    # Resetar alembic para versão estável
    try:
        app = create_app()
        with app.app_context():
            stamp('add_permissions_equipe_vendas')
            print("✅ Alembic resetado para versão estável")
            return True
    except Exception as e:
        print(f"❌ Erro ao resetar alembic: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)