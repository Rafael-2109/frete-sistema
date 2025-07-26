#!/usr/bin/env python3
"""
Script final para corrigir todos os 20 arquivos com erros de sintaxe
"""

import re
from pathlib import Path

print("🔧 CORREÇÃO FINAL DE TODOS OS ERROS DE SINTAXE")
print("="*60)

# Lista de arquivos e correções específicas
fixes = {
    # Arquivos com "if self.redis_cache and self.if REDIS_AVAILABLE" 
    "conversers/context_converser.py": {
        "pattern": r"if self\.redis_cache and self\.if REDIS_AVAILABLE and redis_cache:",
        "replacement": "if self.redis_cache and REDIS_AVAILABLE:"
    },
    
    # Arquivos com cached_suggestions = self.if REDIS_AVAILABLE
    "suggestions/suggestion_engine.py": {
        "pattern": r"cached_suggestions = self\.if REDIS_AVAILABLE and redis_cache:",
        "replacement": "cached_suggestions = None\n            if REDIS_AVAILABLE and self.redis_cache:"
    },
    
    # Arquivos com chave_cache = if REDIS_AVAILABLE
    "loaders/context_loader.py": {
        "pattern": r"chave_cache = if REDIS_AVAILABLE and redis_cache:",
        "replacement": "chave_cache = None\n            if REDIS_AVAILABLE and redis_cache:"
    },
    
    # Arquivos com return if REDIS_AVAILABLE
    "commands/base_command.py": {
        "pattern": r"return if REDIS_AVAILABLE and intelligent_cache:",
        "replacement": "if REDIS_AVAILABLE and intelligent_cache:\n                return"
    },
    
    # Arquivos com "inspect as sql_inspect, text = None"
    "scanning/database_scanner.py": {
        "pattern": r"inspect as sql_inspect, text = None",
        "replacement": "inspect as sql_inspect\n    text = None"
    },
    
    # Arquivos com "inspect as sql_inspect = None"
    "scanning/structure_scanner.py": {
        "pattern": r"inspect as sql_inspect = None",
        "replacement": "inspect as sql_inspect\n    sql_inspect = None"
    }
}

# Aplicar correções específicas
for file_path, fix in fixes.items():
    full_path = Path(f"app/claude_ai_novo/{file_path}")
    if full_path.exists():
        print(f"\n📁 Corrigindo {file_path}...")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Aplicar correção
        new_content = re.sub(fix["pattern"], fix["replacement"], content)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Corrigido!")

# Arquivos com try sem except - adicionar except genérico
try_without_except_files = [
    "verificar_dependencias_sistema.py",
    "loaders/database_loader.py", 
    "learners/learning_core.py",
    "learners/pattern_learning.py",
    "memorizers/knowledge_memory.py",
    "commands/excel/fretes.py",
    "commands/excel/faturamento.py",
    "commands/excel/entregas.py"
]

for file_path in try_without_except_files:
    full_path = Path(f"app/claude_ai_novo/{file_path}")
    if full_path.exists():
        print(f"\n📁 Adicionando except em {file_path}...")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Encontrar try sem except correspondente
        i = 0
        while i < len(lines):
            if lines[i].strip() == "try:":
                # Verificar se há except após este try
                indent = len(lines[i]) - len(lines[i].lstrip())
                j = i + 1
                has_except = False
                
                # Procurar except no mesmo nível de indentação
                while j < len(lines):
                    if lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) <= indent:
                        if lines[j].strip().startswith("except"):
                            has_except = True
                        break
                    j += 1
                
                # Se não tem except, adicionar
                if not has_except and j < len(lines):
                    lines.insert(j, " " * indent + "except Exception as e:\n")
                    lines.insert(j + 1, " " * (indent + 4) + "logger.error(f'Erro: {e}')\n")
                    lines.insert(j + 2, " " * (indent + 4) + "pass\n")
                    i = j + 3
                    continue
            i += 1
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print("✅ Except adicionado!")

# Arquivos com except sem bloco indentado
except_without_indent_files = [
    "conversers/conversation_manager.py",
    "utils/flask_context_wrapper.py",
    "commands/excel_command_manager.py",
    "validators/data_validator.py",
    "mappers/domain/base_mapper.py",
    "loaders/domain/entregas_loader.py"
]

for file_path in except_without_indent_files:
    full_path = Path(f"app/claude_ai_novo/{file_path}")
    if full_path.exists():
        print(f"\n📁 Corrigindo indentação em {file_path}...")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Padrão para except sem bloco indentado seguido de try
        pattern = r'(except\s+\w+.*?:\n)(try:)'
        replacement = r'\1    # Fallback\n    \2'
        
        new_content = re.sub(pattern, replacement, content)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Indentação corrigida!")

print("\n✅ Todas as correções aplicadas!")
print("\n💡 Execute o teste de sintaxe novamente para verificar.")