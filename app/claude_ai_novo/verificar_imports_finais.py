#!/usr/bin/env python3
"""
Verifica se todos os imports estão corretos após aplicação do Flask fallback
"""

import os
import re

def verificar_imports():
    """Verifica arquivos que podem ter problemas de imports"""
    
    problemas = []
    arquivos_verificados = 0
    
    # Pastas para verificar
    pastas = [
        'loaders', 'processors', 'providers', 'memorizers',
        'learners', 'scanning', 'validators', 'commands',
        'analyzers', 'integration', 'suggestions'
    ]
    
    for pasta in pastas:
        caminho_pasta = f'./{pasta}'
        if not os.path.exists(caminho_pasta):
            continue
            
        for root, dirs, files in os.walk(caminho_pasta):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    filepath = os.path.join(root, file)
                    arquivos_verificados += 1
                    
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Verificar se tem get_db sem import
                    if 'get_db()' in content and 'from app.claude_ai_novo.utils.flask_fallback import get_db' not in content:
                        problemas.append(f"{filepath}: usa get_db() mas não importa")
                        
                    # Verificar se usa db. sem self.db
                    if re.search(r'\bdb\.(session|engine|execute)', content):
                        # Mas deve ter property db
                        if '@property\n    def db(self):' not in content:
                            problemas.append(f"{filepath}: usa db.* mas não tem property db")
                            
    print(f"📊 Verificados {arquivos_verificados} arquivos")
    
    if problemas:
        print(f"\n❌ Encontrados {len(problemas)} problemas:")
        for p in problemas:
            print(f"  - {p}")
    else:
        print("\n✅ Todos os imports estão corretos!")
        
    return len(problemas) == 0

if __name__ == "__main__":
    sucesso = verificar_imports()
    exit(0 if sucesso else 1) 