#!/usr/bin/env python3
"""
Verifica se todos os imports estão corretos após aplicação do Flask fallback
Versão melhorada que considera diferentes padrões de import
"""

import os
import re

def verificar_imports():
    """Verifica arquivos que podem ter problemas de imports"""
    
    problemas_reais = []
    arquivos_verificados = 0
    arquivos_ok = []
    
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
                    
                    has_problem = False
                    
                    # Verificar se tem get_db sem import (considerando variações)
                    if 'get_db()' in content:
                        # Aceitar diferentes formas de import
                        import_patterns = [
                            'from app.claude_ai_novo.utils.flask_fallback import get_db',
                            'from ..utils.flask_fallback import get_db',
                            'from ...utils.flask_fallback import get_db',
                            'from .utils.flask_fallback import get_db',
                            'from utils.flask_fallback import get_db'
                        ]
                        
                        has_import = any(pattern in content for pattern in import_patterns)
                        
                        if not has_import:
                            problemas_reais.append(f"{filepath}: usa get_db() mas não importa corretamente")
                            has_problem = True
                    
                    # Verificar se usa db. sem self.db (e não está em property)
                    db_usage = re.search(r'\bdb\.(session|engine|execute)', content)
                    if db_usage:
                        # Verificar se está dentro de uma property ou tem property db
                        has_property = '@property' in content and 'def db(self):' in content
                        in_flask_context = '_try_flask_connection' in content  # Exceção para database_connection.py
                        
                        if not has_property and not in_flask_context:
                            problemas_reais.append(f"{filepath}: usa db.* mas não tem property db")
                            has_problem = True
                    
                    if not has_problem:
                        arquivos_ok.append(os.path.basename(filepath))
                            
    print(f"📊 Verificados {arquivos_verificados} arquivos")
    print(f"✅ {len(arquivos_ok)} arquivos estão corretos")
    
    if problemas_reais:
        print(f"\n❌ Encontrados {len(problemas_reais)} problemas REAIS:")
        for p in problemas_reais:
            print(f"  - {p}")
    else:
        print("\n🎉 TODOS OS IMPORTS ESTÃO CORRETOS!")
        
    return len(problemas_reais) == 0

if __name__ == "__main__":
    sucesso = verificar_imports()
    exit(0 if sucesso else 1) 