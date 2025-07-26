#!/usr/bin/env python3
"""
Script para corrigir definitivamente knowledge_memory.py
"""

import re

file_path = "app/claude_ai_novo/memorizers/knowledge_memory.py"

print(f"🔧 Corrigindo {file_path}...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Padrão problemático: except seguido de try/except do sqlalchemy fora do bloco
pattern = r'''(        except Exception as e:\n            logger\.error\(f'Erro: \{e\}'\)\n            pass\n)(try:\n    from sqlalchemy import text\n    SQLALCHEMY_AVAILABLE = True\nexcept ImportError:\n    text = None\n    SQLALCHEMY_AVAILABLE = False\n)(\s+)(\s+\w+.*)'''

# Função de substituição
def fix_pattern(match):
    except_block = match.group(1)  # O bloco except original
    # sqlalchemy_import = match.group(2)  # Ignorar - já está importado no topo
    # indent = match.group(3)  # Indentação
    code_after = match.group(4)  # Código que deveria estar dentro do with
    
    # Retornar apenas o código que deveria estar dentro do with
    # sem o except e sem o import do sqlalchemy
    return "                " + code_after

# Aplicar correção
new_content = re.sub(pattern, fix_pattern, content, flags=re.MULTILINE)

# Também corrigir casos onde há apenas o try/except do sqlalchemy mal posicionado
pattern2 = r'''(        except Exception as e:\n            logger\.error\(f'Erro: \{e\}'\)\n            pass\n)(\s+from flask import current_app\n\s+FLASK_AVAILABLE = True\nexcept ImportError:\n\s+current_app = None\n\s+FLASK_AVAILABLE = False\n)'''

def fix_pattern2(match):
    return match.group(1)  # Manter apenas o except, remover o import mal posicionado

new_content = re.sub(pattern2, fix_pattern2, new_content, flags=re.MULTILINE)

# Corrigir casos onde o código está fora do bloco try/with
# Encontrar blocos where with termina prematuramente
pattern3 = r'(with current_app\.app_context\(\):\n\s+from app\.claude_ai_novo\.utils\.flask_fallback import get_db)\n(\s+except)'

def fix_pattern3(match):
    return match.group(1) + "\n                pass  # Placeholder\n" + match.group(2)

new_content = re.sub(pattern3, fix_pattern3, new_content)

# Salvar arquivo corrigido
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ knowledge_memory.py corrigido!")
print("\n💡 Execute o teste de sintaxe para verificar.")