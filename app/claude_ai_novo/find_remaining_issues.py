#!/usr/bin/env python3
"""
Script para encontrar problemas restantes em arquivos específicos
"""

import re
import os

files_to_check = [
    "app/claude_ai_novo/memorizers/knowledge_memory.py",
    "app/claude_ai_novo/providers/data_provider.py"
]

def analyze_file(filepath):
    """Analisa arquivo em busca de problemas de try/except"""
    if not os.path.exists(filepath):
        print(f"❌ Arquivo não encontrado: {filepath}")
        return
        
    print(f"\n📁 Analisando: {filepath}")
    print("="*60)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_try_block = False
    try_start_line = 0
    expect_except = False
    indent_stack = []
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Calcular indentação
        indent = len(line) - len(line.lstrip())
        
        if stripped.startswith('try:'):
            if in_try_block and expect_except:
                print(f"⚠️  Linha {i}: Novo 'try:' antes de 'except' do try anterior (linha {try_start_line})")
            in_try_block = True
            try_start_line = i
            expect_except = True
            indent_stack.append(indent)
            print(f"📌 Linha {i}: try: (indent={indent})")
            
        elif stripped.startswith('except'):
            if not in_try_block:
                print(f"❌ Linha {i}: 'except' sem 'try' correspondente")
            else:
                expect_except = False
                print(f"✅ Linha {i}: except (para try da linha {try_start_line})")
                
        elif stripped.startswith('finally:'):
            if in_try_block:
                expect_except = False
                print(f"✅ Linha {i}: finally (para try da linha {try_start_line})")
                
        elif stripped.startswith('else:'):
            # Verificar se o else tem conteúdo na próxima linha
            if i < len(lines):
                next_line = lines[i]
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= indent and next_line.strip():
                    print(f"❌ Linha {i}: 'else:' sem bloco indentado")
                    
        # Verificar se saímos do bloco try
        if in_try_block and indent_stack and indent < indent_stack[-1] and stripped:
            if expect_except:
                print(f"❌ Linha {try_start_line}: 'try:' sem 'except' ou 'finally'")
            in_try_block = False
            if indent_stack:
                indent_stack.pop()
                
    # Verificar try pendente no final do arquivo
    if in_try_block and expect_except:
        print(f"❌ Linha {try_start_line}: 'try:' sem 'except' ou 'finally' (fim do arquivo)")

print("🔍 ANÁLISE DE PROBLEMAS TRY/EXCEPT RESTANTES")
print("="*60)

for filepath in files_to_check:
    analyze_file(filepath)