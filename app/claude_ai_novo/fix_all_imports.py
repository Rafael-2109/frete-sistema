#!/usr/bin/env python3
"""
Script para corrigir automaticamente todos os imports com fallback
"""

import os
import re
from typing import List, Dict, Any

# Mapeamento de imports para fallback
IMPORT_FALLBACK_MAP = {
    # Utils Mock
    "from unittest.mock import Mock": "try:\n    from unittest.mock import Mock\nexcept ImportError:\n    class Mock:\n        def __init__(self, *args, **kwargs):\n            pass\n        def __call__(self, *args, **kwargs):\n            return self\n        def __getattr__(self, name):\n            return self",
    
    # Flask
    "from flask import": "try:\n    from flask import {imports}\n    FLASK_AVAILABLE = True\nexcept ImportError:\n    {imports} = None\n    FLASK_AVAILABLE = False",
    
    # Flask Login
    "from flask_login import": "try:\n    from flask_login import {imports}\n    FLASK_LOGIN_AVAILABLE = True\nexcept ImportError:\n    from unittest.mock import Mock\n    {imports} = Mock()\n    FLASK_LOGIN_AVAILABLE = False",
    
    # SQLAlchemy
    "from sqlalchemy import": "try:\n    from sqlalchemy import {imports}\n    SQLALCHEMY_AVAILABLE = True\nexcept ImportError:\n    {imports} = None\n    SQLALCHEMY_AVAILABLE = False",
    
    # Openpyxl
    "from openpyxl import": "try:\n    from openpyxl import {imports}\n    OPENPYXL_AVAILABLE = True\nexcept ImportError:\n    from unittest.mock import Mock\n    {imports} = Mock()\n    OPENPYXL_AVAILABLE = False",
    
    # Anthropic
    "import anthropic": "try:\n    import anthropic\n    ANTHROPIC_AVAILABLE = True\nexcept ImportError:\n    anthropic = None\n    ANTHROPIC_AVAILABLE = False",
    
    # Fuzzy
    "from fuzzywuzzy import": "try:\n    from fuzzywuzzy import {imports}\n    FUZZY_AVAILABLE = True\nexcept ImportError:\n    class FuzzMock:\n        def ratio(self, a, b): return 0\n        def partial_ratio(self, a, b): return 0\n        def token_sort_ratio(self, a, b): return 0\n        def token_set_ratio(self, a, b): return 0\n    {imports} = FuzzMock()\n    FUZZY_AVAILABLE = False",
    
    # Spacy/NLTK
    "from spacy import": "try:\n    from spacy import {imports}\n    SPACY_AVAILABLE = True\nexcept ImportError:\n    {imports} = None\n    SPACY_AVAILABLE = False",
    
    "from nltk import": "try:\n    from nltk import {imports}\n    NLTK_AVAILABLE = True\nexcept ImportError:\n    {imports} = None\n    NLTK_AVAILABLE = False",
}

def extract_imports(line: str) -> List[str]:
    """Extrai imports de uma linha"""
    # Padrão para: from X import A, B, C
    pattern = r'from\s+[\w.]+\s+import\s+(.+)'
    match = re.match(pattern, line.strip())
    if match:
        imports_str = match.group(1)
        # Limpar e separar imports
        imports = [imp.strip() for imp in imports_str.split(',')]
        return imports
    return []

def fix_imports_in_file(filepath: str) -> bool:
    """Corrige imports em um arquivo"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        new_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            replaced = False
            
            # Verificar cada padrão de import
            for pattern, replacement in IMPORT_FALLBACK_MAP.items():
                if pattern in line and not line.strip().startswith('try:'):
                    imports = extract_imports(line)
                    if imports:
                        imports_str = ', '.join(imports)
                        # Substituir {imports} no template
                        new_import = replacement.replace('{imports}', imports_str)
                        new_lines.append(new_import + '\n')
                        replaced = True
                        modified = True
                        break
            
            if not replaced:
                new_lines.append(line)
            
            i += 1
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
        
        return False
        
    except Exception as e:
        print(f"Erro ao processar {filepath}: {e}")
        return False

def fix_redis_usage(filepath: str) -> bool:
    """Corrige uso do Redis sem verificação"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Padrões de uso do Redis
        redis_patterns = [
            (r'(redis_cache\.\w+)', r'if REDIS_AVAILABLE and redis_cache:\n            \1'),
            (r'(intelligent_cache\.\w+)', r'if REDIS_AVAILABLE and intelligent_cache:\n            \1'),
            (r'(cache_obj\.\w+)', r'if cache_obj:\n            \1'),
        ]
        
        modified = False
        for pattern, replacement in redis_patterns:
            if re.search(pattern, content):
                # Adicionar verificação antes do uso
                content = re.sub(pattern, replacement, content)
                modified = True
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Erro ao corrigir Redis em {filepath}: {e}")
        return False

def main():
    """Função principal"""
    print("🔧 Iniciando correção automática de imports...")
    
    # Diretório do claude_ai_novo
    base_dir = "/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo"
    
    # Estatísticas
    total_files = 0
    fixed_imports = 0
    fixed_redis = 0
    
    # Percorrer todos os arquivos Python
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                total_files += 1
                
                # Corrigir imports
                if fix_imports_in_file(filepath):
                    fixed_imports += 1
                    print(f"✅ Imports corrigidos: {filepath}")
                
                # Corrigir uso do Redis
                if fix_redis_usage(filepath):
                    fixed_redis += 1
                    print(f"✅ Redis corrigido: {filepath}")
    
    print(f"\n📊 Resumo:")
    print(f"- Total de arquivos: {total_files}")
    print(f"- Imports corrigidos: {fixed_imports}")
    print(f"- Redis corrigidos: {fixed_redis}")
    print("\n✨ Correção automática concluída!")

if __name__ == "__main__":
    main()