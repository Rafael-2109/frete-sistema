#!/usr/bin/env python3
"""
Script para corrigir flask_context_wrapper.py
"""

import re

file_path = "app/claude_ai_novo/utils/flask_context_wrapper.py"

print(f"🔧 Corrigindo {file_path}...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Padrão para encontrar todos os blocos try mal formatados
pattern = r'(\s+)try:\n(\s*)from flask import current_app\n\s*FLASK_AVAILABLE = True\nexcept ImportError:\n\s*current_app = None\n\s*FLASK_AVAILABLE = False'

# Substituir por estrutura correta
def fix_try_block(match):
    indent = match.group(1)
    return f'{indent}try:\n{indent}    from flask import current_app\n{indent}except ImportError:\n{indent}    current_app = None'

new_content = re.sub(pattern, fix_try_block, content)

# Também corrigir casos onde há apenas try: sem bloco
pattern2 = r'(\s+)try:\n(\s+)except'
replacement2 = r'\1try:\n\1    pass\n\2except'
new_content = re.sub(pattern2, replacement2, new_content)

# Salvar arquivo corrigido
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ flask_context_wrapper.py corrigido!")
print("\n💡 Teste a sintaxe novamente.")