#!/usr/bin/env python3
"""
Script para corrigir os últimos problemas de try/except
"""

import re
import os
from datetime import datetime

print("🔧 CORREÇÃO FINAL DE PROBLEMAS TRY/EXCEPT")
print("="*60)
print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("="*60)

# Corrigir data_provider.py - else sem bloco indentado
file_path = "app/claude_ai_novo/providers/data_provider.py"
print(f"\n📁 Corrigindo {file_path}...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Padrão para encontrar else: seguido de try: não indentado
pattern = r'(\s*)else:\n(try:)'
replacement = r'\1else:\n\1    # Fallback\n\1    \2'

# Aplicar correção
new_content = re.sub(pattern, replacement, content)

# Salvar arquivo corrigido
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ data_provider.py corrigido!")

# Corrigir knowledge_memory.py - try sem except
file_path = "app/claude_ai_novo/memorizers/knowledge_memory.py"
print(f"\n📁 Corrigindo {file_path}...")

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Linha 135 - adicionar except
for i in range(len(lines)):
    if i == 134 and lines[i].strip().startswith('try:'):  # Linha 135 (0-indexed)
        # Encontrar onde adicionar o except
        j = i + 1
        indent = len(lines[i]) - len(lines[i].lstrip())
        
        # Procurar até encontrar uma linha com indentação menor ou igual
        while j < len(lines) and (not lines[j].strip() or 
                                 len(lines[j]) - len(lines[j].lstrip()) > indent):
            j += 1
            
        # Inserir except antes dessa linha
        lines.insert(j, ' ' * indent + 'except Exception as e:\n')
        lines.insert(j + 1, ' ' * (indent + 4) + 'logger.error(f"Erro: {e}")\n')
        lines.insert(j + 2, ' ' * (indent + 4) + 'return None\n')
        break

# Salvar arquivo corrigido
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ knowledge_memory.py corrigido!")

print("\n✅ Correções finais aplicadas!")
print("\n💡 Execute o teste de sintaxe novamente para verificar.")