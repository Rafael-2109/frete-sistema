#!/usr/bin/env python3
"""
Script para aplicar correções finais adicionais de Flask Fallback
"""

import os
import re
from pathlib import Path

def corrigir_imports_callables():
    """Corrige imports de callable nos mappers"""
    
    arquivos = [
        'mappers/context_mapper.py',
        'mappers/field_mapper.py'
    ]
    
    for arquivo in arquivos:
        file_path = Path(arquivo)
        if not file_path.exists():
            print(f"❌ Arquivo não encontrado: {arquivo}")
            continue
            
        print(f"🔧 Corrigindo imports callable em {arquivo}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Corrigir import callable
        if 'from collections import' in content and 'callable' not in content:
            content = content.replace(
                'from collections import defaultdict',
                'from collections import defaultdict\nfrom collections.abc import Callable'
            )
        
        # Substituir callable por Callable nas anotações
        content = re.sub(r'\bcallable\b(?!\s*\()', 'Callable', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ {arquivo} corrigido")

def corrigir_never_iterables():
    """Corrige erros de 'Never' is not iterable"""
    
    arquivo = 'processors/context_processor.py'
    file_path = Path(arquivo)
    
    if not file_path.exists():
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return
        
    print(f"🔧 Corrigindo 'Never' iterables em {arquivo}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Adicionar verificações antes de iterar
    content = re.sub(
        r'for\s+(\w+)\s+in\s+([\w\.]+)\.get\(([^)]+)\)\s*:',
        r'for \1 in (\2.get(\3) or []):',
        content
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"✅ {arquivo} corrigido")

def corrigir_utils_manager():
    """Corrige erro de argumento para classe em utils_manager.py"""
    
    arquivo = 'utils/utils_manager.py'
    file_path = Path(arquivo)
    
    if not file_path.exists():
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return
        
    print(f"🔧 Corrigindo argumento de classe em {arquivo}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar qual é o problema específico na linha 43
    lines = content.split('\n')
    if len(lines) > 42:
        linha_problema = lines[42]
        print(f"   Linha 43: {linha_problema}")
        
        # Se for um problema com herança de class
        if 'class ' in linha_problema and 'BaseUtility' in linha_problema:
            # Adicionar import correto
            if 'from app.claude_ai_novo.utils.base_classes import BaseUtility' not in content:
                import_section = content.split('\n\n')[0]
                new_import = '\nfrom app.claude_ai_novo.utils.base_classes import BaseUtility'
                content = content.replace(import_section, import_section + new_import)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"✅ {arquivo} corrigido")

def main():
    """Executa todas as correções"""
    
    print("🚀 Aplicando correções finais adicionais...")
    print("=" * 60)
    
    # Aplicar correções
    corrigir_imports_callables()
    print()
    
    corrigir_never_iterables()
    print()
    
    corrigir_utils_manager()
    
    print("\n✅ Correções finais aplicadas!")
    print("\n📝 Resumo:")
    print("- Imports de Callable corrigidos nos mappers")
    print("- Erros 'Never' is not iterable corrigidos")
    print("- Erro de argumento para classe corrigido")

if __name__ == "__main__":
    main() 