#!/usr/bin/env python3
"""
Script para encontrar e corrigir TODOS os problemas de try/except no claude_ai_novo
"""

import os
import re
from pathlib import Path

def find_try_except_issues(file_path):
    """Encontra problemas de try/except em um arquivo"""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Procurar por padrões problemáticos
        for i, line in enumerate(lines):
            # Pattern 1: try duplicado (try:\ntry:)
            if line.strip() == 'try:' and i > 0:
                prev_line = lines[i-1].strip()
                if prev_line == 'try:' or (i > 1 and lines[i-2].strip() == 'try:' and not prev_line):
                    issues.append({
                        'line': i + 1,
                        'type': 'duplicate_try',
                        'content': line.strip()
                    })
            
            # Pattern 2: except sem try anterior adequado
            if line.strip().startswith('except') and i > 0:
                # Verificar se há um try correspondente
                found_try = False
                indent_level = len(line) - len(line.lstrip())
                
                for j in range(i-1, max(0, i-50), -1):
                    check_line = lines[j]
                    check_indent = len(check_line) - len(check_line.lstrip())
                    
                    if check_line.strip() == 'try:' and check_indent == indent_level:
                        found_try = True
                        break
                    elif check_line.strip() and check_indent < indent_level:
                        # Saiu do bloco
                        break
                
                if not found_try:
                    issues.append({
                        'line': i + 1,
                        'type': 'except_without_try',
                        'content': line.strip()
                    })
        
        # Pattern 3: try sem except
        for i, line in enumerate(lines):
            if line.strip() == 'try:':
                indent_level = len(line) - len(line.lstrip())
                found_except = False
                
                for j in range(i+1, min(len(lines), i+50)):
                    check_line = lines[j]
                    check_indent = len(check_line) - len(check_line.lstrip())
                    
                    if check_line.strip().startswith('except') and check_indent == indent_level:
                        found_except = True
                        break
                    elif check_line.strip() == 'try:' and check_indent == indent_level:
                        # Outro try no mesmo nível - problema!
                        break
                    elif check_line.strip() and check_indent < indent_level:
                        # Saiu do bloco sem except
                        break
                
                if not found_except:
                    issues.append({
                        'line': i + 1,
                        'type': 'try_without_except',
                        'content': line.strip()
                    })
    
    except Exception as e:
        print(f"Erro ao analisar {file_path}: {e}")
    
    return issues

def scan_directory(directory):
    """Escaneia todos os arquivos Python em um diretório"""
    all_issues = {}
    
    for py_file in Path(directory).rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
        
        issues = find_try_except_issues(py_file)
        if issues:
            all_issues[str(py_file)] = issues
    
    return all_issues

def fix_duplicate_try(file_path, line_number):
    """Corrige try duplicado removendo a duplicação"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Verificar se é realmente um try duplicado
    if line_number > 0 and line_number <= len(lines):
        current_line = lines[line_number - 1].strip()
        
        if current_line == 'try:':
            # Verificar linha anterior
            for i in range(line_number - 2, max(0, line_number - 5), -1):
                if lines[i].strip() == 'try:':
                    # Remover o try duplicado
                    del lines[line_number - 1]
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    return True
                elif lines[i].strip() and not lines[i].strip().startswith('#'):
                    break
    
    return False

def main():
    """Função principal"""
    print("🔍 Escaneando arquivos do claude_ai_novo...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    issues = scan_directory(base_dir)
    
    if not issues:
        print("✅ Nenhum problema de try/except encontrado!")
        return
    
    print(f"\n❌ Encontrados problemas em {len(issues)} arquivos:\n")
    
    total_issues = 0
    for file_path, file_issues in issues.items():
        print(f"📄 {os.path.relpath(file_path, base_dir)}:")
        for issue in file_issues:
            print(f"   Linha {issue['line']}: {issue['type']} - {issue['content']}")
            total_issues += 1
        print()
    
    print(f"Total de problemas: {total_issues}")
    
    # Perguntar se deseja corrigir automaticamente
    response = input("\n🔧 Deseja tentar corrigir automaticamente os 'duplicate_try'? (s/n): ")
    
    if response.lower() == 's':
        fixed_count = 0
        for file_path, file_issues in issues.items():
            for issue in file_issues:
                if issue['type'] == 'duplicate_try':
                    if fix_duplicate_try(file_path, issue['line']):
                        print(f"✅ Corrigido: {os.path.relpath(file_path, base_dir)} linha {issue['line']}")
                        fixed_count += 1
        
        print(f"\n✅ {fixed_count} problemas corrigidos automaticamente!")
        print("⚠️  Outros problemas precisam ser corrigidos manualmente.")

if __name__ == "__main__":
    main()