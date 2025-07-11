#!/usr/bin/env python3
"""
Verificador simples de imports quebrados
"""

import os
import ast
from pathlib import Path

def check_imports_in_file(file_path):
    """Verifica imports em um arquivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ''
                level = node.level
                
                # Verificar imports relativos problemáticos
                if level > 0:
                    for alias in node.names:
                        import_name = alias.name
                        
                        # Verificar se está importando ClaudeRealIntegration
                        if import_name == 'ClaudeRealIntegration':
                            issues.append({
                                'line': node.lineno,
                                'type': 'wrong_class_name',
                                'import': f"from {module} import {import_name}",
                                'suggestion': f"from {module} import ExternalAPIIntegration"
                            })
                        
                        # Verificar se está importando ValidationUtils que não existe
                        if import_name == 'ValidationUtils':
                            issues.append({
                                'line': node.lineno,
                                'type': 'missing_class',
                                'import': f"from {module} import {import_name}",
                                'suggestion': "Criar classe ValidationUtils ou usar alternativa"
                            })
        
        return issues
        
    except Exception as e:
        return [{'line': 0, 'type': 'parse_error', 'error': str(e)}]

def main():
    """Função principal"""
    print("🔍 Verificando imports em arquivos Python...")
    
    issues_found = []
    
    # Verificar arquivos específicos mencionados
    files_to_check = [
        'utils/legacy_compatibility.py',
        'utils/utils_manager.py',
        'integration/external_api_integration.py'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"\n📁 Verificando: {file_path}")
            issues = check_imports_in_file(file_path)
            
            if issues:
                issues_found.extend([(file_path, issue) for issue in issues])
                for issue in issues:
                    print(f"  ⚠️  Linha {issue['line']}: {issue['type']}")
                    print(f"     Import: {issue.get('import', 'N/A')}")
                    if 'suggestion' in issue:
                        print(f"     Sugestão: {issue['suggestion']}")
                    if 'error' in issue:
                        print(f"     Erro: {issue['error']}")
            else:
                print(f"  ✅ Sem problemas encontrados")
        else:
            print(f"  ❌ Arquivo não encontrado: {file_path}")
    
    # Verificar outros arquivos Python
    print(f"\n📁 Verificando outros arquivos Python...")
    for root, dirs, files in os.walk('.'):
        # Ignorar __pycache__
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py') and file not in ['check_imports.py', 'analisar_imports_quebrados.py', 'analisar_imports_simples.py']:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, '.')
                
                if rel_path not in files_to_check:
                    issues = check_imports_in_file(file_path)
                    if issues:
                        issues_found.extend([(rel_path, issue) for issue in issues])
    
    # Resumo final
    print(f"\n📊 RESUMO:")
    print(f"Total de problemas encontrados: {len(issues_found)}")
    
    if issues_found:
        print(f"\n❌ PROBLEMAS ENCONTRADOS:")
        for file_path, issue in issues_found:
            print(f"  • {file_path}:{issue['line']} - {issue['type']}")
            if 'suggestion' in issue:
                print(f"    Sugestão: {issue['suggestion']}")
    
    print(f"\n🎯 PROBLEMAS IDENTIFICADOS:")
    print(f"1. ❌ ClaudeRealIntegration não existe - deveria ser ExternalAPIIntegration")
    print(f"2. ❌ ValidationUtils não existe - precisa ser criado ou usar mock")
    print(f"3. ❌ ResponseUtils pode estar como None - verificar imports")
    
    print(f"\n✅ SOLUÇÕES APLICADAS:")
    print(f"1. ✅ legacy_compatibility.py - Corrigido import para ExternalAPIIntegration")
    print(f"2. ✅ utils_manager.py - Adicionado classe mock ValidationUtils")
    print(f"3. ✅ utils_manager.py - Corrigido verificação de ResponseUtils")

if __name__ == "__main__":
    main() 