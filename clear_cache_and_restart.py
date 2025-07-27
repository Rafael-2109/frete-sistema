#!/usr/bin/env python
"""
Clear Flask cache and session to apply decorator changes
"""

import os
import shutil
import sys

def clear_cache():
    """Clear all cache and session files"""
    
    print("🧹 Limpando cache e sessões...")
    
    # Clear Flask session files
    session_path = "flask_session"
    if os.path.exists(session_path):
        shutil.rmtree(session_path)
        print(f"✅ Removido: {session_path}")
    
    # Clear instance folder
    instance_path = "instance"
    if os.path.exists(instance_path):
        # Keep the folder but clear its contents
        for filename in os.listdir(instance_path):
            file_path = os.path.join(instance_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                print(f"✅ Removido: {file_path}")
            except Exception as e:
                print(f"❌ Erro ao remover {file_path}: {e}")
    
    # Clear __pycache__ from permissions module
    pycache_paths = [
        "app/permissions/__pycache__",
        "app/__pycache__",
        "__pycache__"
    ]
    
    for path in pycache_paths:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"✅ Removido: {path}")
    
    # Clear specific decorator cache files
    decorator_files = [
        "app/permissions/decorators_patch.pyc",
        "app/permissions/decorators_simple.pyc",
        "app/permissions/decorators.pyc"
    ]
    
    for file in decorator_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"✅ Removido: {file}")
    
    print("\n✅ Cache limpo com sucesso!")
    print("\n📝 PRÓXIMOS PASSOS:")
    print("1. Reinicie a aplicação Flask")
    print("2. Faça logout e login novamente")
    print("3. Tente acessar /permissions/hierarchical-manager")
    
    return True

if __name__ == "__main__":
    clear_cache()