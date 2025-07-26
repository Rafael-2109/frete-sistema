#!/usr/bin/env python3
"""
Script para corrigir todos os blocos else: com try mal indentado em data_provider.py
"""

import re

file_path = "app/claude_ai_novo/providers/data_provider.py"

print(f"🔧 Corrigindo {file_path}...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Padrão para corrigir todos os blocos problemáticos de uma vez
# Este padrão captura else: seguido de comentário e try mal indentado
pattern = r'(\s*)else:\n\n(\s*)# Fallback\n\n(\s*)try:\n(\s*)from unittest\.mock import Mock\nexcept ImportError:\n(\s*)class Mock:'

# Função de substituição
def fix_indentation(match):
    indent = match.group(1)  # Indentação do else:
    return f'''{indent}else:
{indent}    # Fallback
{indent}    try:
{indent}        from unittest.mock import Mock
{indent}    except ImportError:
{indent}        class Mock:'''

# Aplicar correção
new_content = re.sub(pattern, fix_indentation, content)

# Também corrigir os blocos que estão com return incorreto
# Encontrar padrões onde return está no lugar errado dentro da classe Mock
pattern2 = r'(class Mock:\n\s*def __init__.*?\n\s*def __call__.*?\n\s*def __getattr__.*?\n)(\s*return self\n)(\s*return Mock\(\))'

def fix_return(match):
    class_def = match.group(1)
    return_self = match.group(2)
    # Remover o return self mal posicionado e manter apenas o return Mock()
    return class_def + match.group(3)

new_content = re.sub(pattern2, fix_return, new_content, flags=re.DOTALL)

# Corrigir blocos onde há return self seguido de return Mock em linhas erradas
pattern3 = r'(def __getattr__\(self, name\):\n)\s*return self\n\s*return Mock'

def fix_getattr(match):
    return match.group(1) + '                        return self\n            return Mock'

new_content = re.sub(pattern3, fix_getattr, new_content)

# Salvar arquivo corrigido
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ data_provider.py corrigido!")
print("\n💡 Execute o teste de sintaxe para verificar.")