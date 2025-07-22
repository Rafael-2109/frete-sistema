#!/usr/bin/env python3
import os
import glob

def main():
    print("🧹 Limpando migrations problemáticas...")
    
    # Encontrar e remover migrations problemáticas
    migrations_dir = "migrations/versions"
    removed_count = 0
    
    if os.path.exists(migrations_dir):
        # Buscar por migrations problemáticas
        problematic_patterns = [
            "*016dfad*",
            "*ef5eaa*", 
            "*migração*",
            "*correção*"
        ]
        
        for pattern in problematic_patterns:
            files = glob.glob(os.path.join(migrations_dir, pattern))
            for file_path in files:
                try:
                    os.remove(file_path)
                    print(f"🗑️ Removido: {os.path.basename(file_path)}")
                    removed_count += 1
                except Exception as e:
                    print(f"❌ Erro ao remover {file_path}: {e}")
    
    print(f"✅ Removidas {removed_count} migrations problemáticas")
    return True

if __name__ == "__main__":
    main()