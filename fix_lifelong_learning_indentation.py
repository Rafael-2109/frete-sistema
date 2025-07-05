#!/usr/bin/env python3
"""
Script para corrigir erros de indentação em lifelong_learning.py
"""
import re

print("🔧 Corrigindo erros de indentação em lifelong_learning.py...")

# Ler o arquivo
with open('app/claude_ai/lifelong_learning.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Lista de correções necessárias
# Cada tupla contém: (padrão a buscar, substituição)
corrections = [
    # Correção 1: _salvar_padrao (linha ~140)
    (
        r'(with current_app\.app_context\(\):\n\s+try:\n)(\s+# Verificar se já existe)',
        r'\1    \2'
    ),
    # Correção 2: _aprender_mapeamento_cliente (linha ~198)
    (
        r'("""Aprende como usuários se referem a clientes"""\n\s+with current_app\.app_context\(\):\n\s+try:\n)(\s+# Extrair termos)',
        r'\1    \2'
    ),
    # Correção 3: _salvar_historico (linha ~378)
    (
        r'("""Salva histórico completo da interação"""\n\s+with current_app\.app_context\(\):\n\s+try:\n)(\s+_get_db_session)',
        r'\1    \2'
    ),
    # Correção 4: _atualizar_metricas (linha ~670)
    (
        r'("""Atualiza métricas de performance"""\n\s+with current_app\.app_context\(\):\n\s+try:\n)(\s+# Calcular satisfação)',
        r'\1    \2'
    )
]

# Aplicar correções
for pattern, replacement in corrections:
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

# Correção mais genérica para blocos try sem indentação
# Procurar por "try:\n<linha sem indentação suficiente>"
lines = content.split('\n')
corrected_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    corrected_lines.append(line)
    
    # Se encontrar um "try:" seguido de uma linha com menos indentação que deveria
    if line.strip() == 'try:' and i + 1 < len(lines):
        # Calcular indentação do try
        try_indent = len(line) - len(line.lstrip())
        expected_indent = try_indent + 4  # Python usa 4 espaços por padrão
        
        # Verificar próxima linha
        next_line = lines[i + 1]
        if next_line.strip() and not next_line.startswith(' ' * expected_indent):
            # Corrigir indentação das próximas linhas até encontrar except
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('except'):
                if lines[i].strip():  # Ignorar linhas vazias
                    # Adicionar 4 espaços de indentação
                    corrected_lines.append('    ' + lines[i])
                else:
                    corrected_lines.append(lines[i])
                i += 1
            i -= 1  # Voltar um para processar o except normalmente
    
    i += 1

# Juntar linhas corrigidas
corrected_content = '\n'.join(corrected_lines)

# Salvar arquivo corrigido
with open('app/claude_ai/lifelong_learning.py', 'w', encoding='utf-8') as f:
    f.write(corrected_content)

print("✅ Correções aplicadas com sucesso!")
print("📋 Erros de indentação corrigidos em 4 blocos try:")
print("   1. _salvar_padrao")
print("   2. _aprender_mapeamento_cliente") 
print("   3. _salvar_historico")
print("   4. _atualizar_metricas") 