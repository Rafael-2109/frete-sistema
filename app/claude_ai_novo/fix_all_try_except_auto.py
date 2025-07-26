#!/usr/bin/env python3
"""
Script para corrigir automaticamente problemas de try/except no claude_ai_novo
"""

import os
import re
from pathlib import Path

def fix_duplicate_try(file_path):
    """Corrige todos os try duplicados em um arquivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern para encontrar try duplicado
        # Procura por try:\n<espaços>try: ou try:\ntry:
        pattern = r'(\s*)try:\s*\n\s*try:'
        
        # Substituir por um único try com indentação correta
        content = re.sub(pattern, r'\1try:', content)
        
        # Se houve mudanças, salvar
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
    except Exception as e:
        print(f"Erro ao corrigir {file_path}: {e}")
    
    return False

def fix_flask_fallback_specific():
    """Corrige o erro específico no flask_fallback.py linha 325"""
    file_path = "/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo/utils/flask_fallback.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Procurar e corrigir o problema específico na linha 325-326
        for i in range(len(lines)):
            if i >= 324 and i < 330:  # Linhas 325-330
                if lines[i].strip() == 'try:' and i > 0:
                    # Verificar se a linha anterior também é try:
                    prev_line_idx = i - 1
                    while prev_line_idx >= 0 and not lines[prev_line_idx].strip():
                        prev_line_idx -= 1
                    
                    if prev_line_idx >= 0 and lines[prev_line_idx].strip() == 'try:':
                        # Remover o try duplicado
                        lines[i] = ''  # Remove a linha do try duplicado
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        
                        print(f"✅ Corrigido flask_fallback.py linha {i+1}")
                        return True
    
    except Exception as e:
        print(f"Erro ao corrigir flask_fallback.py: {e}")
    
    return False

def fix_imports_blocks(file_path):
    """Corrige blocos de imports com try/except quebrados"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern para try: seguido de import sem except
        pattern1 = r'(try:\s*\n\s*from .+ import .+)\s*\n\s*try:'
        replacement1 = r'\1\nexcept ImportError:\n    pass\n\ntry:'
        
        content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)
        
        # Pattern para except sem try correspondente (órfão)
        # Este é mais complexo e precisa de análise contextual
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
    except Exception as e:
        print(f"Erro ao corrigir imports em {file_path}: {e}")
    
    return False

def find_and_fix_all():
    """Encontra e corrige todos os problemas automaticamente"""
    base_dir = "/home/rafaelnascimento/projetos/frete_sistema/app/claude_ai_novo"
    fixed_count = 0
    
    print("🔧 Corrigindo problemas de try/except automaticamente...")
    
    # Primeiro, corrigir o flask_fallback.py especificamente
    if fix_flask_fallback_specific():
        fixed_count += 1
    
    # Depois, corrigir todos os try duplicados
    for py_file in Path(base_dir).rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
        
        if fix_duplicate_try(py_file):
            print(f"✅ Corrigido try duplicado em: {os.path.relpath(py_file, base_dir)}")
            fixed_count += 1
    
    print(f"\n✅ Total de arquivos corrigidos: {fixed_count}")
    
    # Lista de arquivos que precisam correção manual específica
    manual_fixes = {
        "utils/base_classes.py": "Linha 39 - verificar estrutura try/except",
        "analyzers/nlp_enhanced_analyzer.py": "Linha 29-30 - try duplicado",
        "providers/data_provider.py": "Linha 150-151 - try duplicado",
        "memorizers/knowledge_memory.py": "Linhas 495-496, 589-590 - try duplicado",
        "mappers/domain/base_mapper.py": "Linha 95-96 - try duplicado",
        "loaders/domain/entregas_loader.py": "Múltiplos try duplicados",
        "commands/excel/*.py": "Vários arquivos com try duplicado"
    }
    
    print("\n⚠️  Arquivos que precisam correção manual:")
    for file, issue in manual_fixes.items():
        print(f"   📄 {file}: {issue}")

if __name__ == "__main__":
    find_and_fix_all()