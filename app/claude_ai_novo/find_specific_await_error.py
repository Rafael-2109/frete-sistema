"""
🔍 ENCONTRAR ERRO ESPECÍFICO DE AWAIT - Script Direcionado
==========================================================

Script para encontrar especificamente o erro:
"object dict can't be used in 'await' expression"
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def find_await_dict_errors():
    """Encontra especificamente erros de await em dict."""
    
    print('🔍 PROCURANDO ERRO ESPECÍFICO: "object dict can\'t be used in \'await\' expression"')
    print('='*70)
    
    base_path = Path('.')
    errors_found = []
    
    # Padrões mais específicos
    patterns = [
        r'await\s+\{',                           # await {dict}
        r'await\s+\w+_dict',                     # await some_dict
        r'await\s+\w+\s*\{.*\}',                 # await var{...}
        r'await\s+[a-zA-Z_]\w*\s*\[',            # await dict[key]
        r'await\s+[a-zA-Z_]\w*\s*\(',            # await func() que pode retornar dict
        r'await\s+\w+\.\w+\s*\(',                # await obj.method() que pode retornar dict
    ]
    
    # Procurar em todos os arquivos Python
    for py_file in base_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    stripped = line.strip()
                    
                    if 'await' in stripped:
                        # Verificar padrões
                        for pattern in patterns:
                            if re.search(pattern, stripped):
                                errors_found.append({
                                    'file': str(py_file),
                                    'line': line_num,
                                    'content': stripped,
                                    'pattern': pattern,
                                    'full_line': line
                                })
                                
        except Exception as e:
            logger.warning(f"Erro ao processar {py_file}: {e}")
    
    print(f'Encontrados {len(errors_found)} possíveis erros de await')
    print('='*70)
    
    # Mostrar erros encontrados
    for error in errors_found:
        file_name = error['file'].split('/')[-1].split('\\')[-1]
        print(f'📁 {file_name}:{error["line"]}')
        print(f'   {error["content"]}')
        print(f'   Padrão: {error["pattern"]}')
        print()
    
    return errors_found

def find_specific_function_calls():
    """Encontra chamadas específicas que podem estar causando o erro."""
    
    print('🔍 PROCURANDO CHAMADAS ESPECÍFICAS...')
    print('='*50)
    
    # Funções que podem retornar dict e estar sendo aguardadas incorretamente
    functions_to_check = [
        'process_query',
        'get_system_status',
        'get_integration_status',
        'orchestrate_operation',
        'process_unified_query',
        'get_orchestrator_status',
        'validate_operation_security'
    ]
    
    base_path = Path('.')
    found_calls = []
    
    for py_file in base_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    stripped = line.strip()
                    
                    for func_name in functions_to_check:
                        if f'await {func_name}' in stripped or f'await self.{func_name}' in stripped:
                            found_calls.append({
                                'file': str(py_file),
                                'line': line_num,
                                'content': stripped,
                                'function': func_name
                            })
                            
        except Exception as e:
            logger.warning(f"Erro ao processar {py_file}: {e}")
    
    print(f'Encontradas {len(found_calls)} chamadas suspeitas')
    print('='*50)
    
    for call in found_calls:
        file_name = call['file'].split('/')[-1].split('\\')[-1]
        print(f'📁 {file_name}:{call["line"]}')
        print(f'   {call["content"]}')
        print(f'   Função: {call["function"]}')
        print()
    
    return found_calls

def check_function_definitions():
    """Verifica se funções estão definidas como async quando deveriam ser."""
    
    print('🔍 VERIFICANDO DEFINIÇÕES DE FUNÇÕES...')
    print('='*50)
    
    base_path = Path('.')
    issues = []
    
    # Funções que podem precisar ser async
    functions_to_check = [
        'process_query',
        'process_unified_query',
        'orchestrate_operation',
        'get_system_status',
        'get_integration_status'
    ]
    
    for py_file in base_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    stripped = line.strip()
                    
                    for func_name in functions_to_check:
                        # Função definida como não async
                        if f'def {func_name}' in stripped and 'async' not in stripped:
                            issues.append({
                                'file': str(py_file),
                                'line': line_num,
                                'content': stripped,
                                'function': func_name,
                                'issue': 'function_not_async'
                            })
                        
                        # Função definida como async
                        elif f'async def {func_name}' in stripped:
                            issues.append({
                                'file': str(py_file),
                                'line': line_num,
                                'content': stripped,
                                'function': func_name,
                                'issue': 'function_is_async'
                            })
                            
        except Exception as e:
            logger.warning(f"Erro ao processar {py_file}: {e}")
    
    print(f'Encontradas {len(issues)} definições de funções')
    print('='*50)
    
    for issue in issues:
        file_name = issue['file'].split('/')[-1].split('\\')[-1]
        status = "✅ ASYNC" if issue['issue'] == 'function_is_async' else "❌ NOT ASYNC"
        print(f'{status} {file_name}:{issue["line"]}')
        print(f'   {issue["content"]}')
        print()
    
    return issues

def main():
    """Função principal."""
    logging.basicConfig(level=logging.INFO)
    
    print('🚀 ANÁLISE COMPLETA DE ERROS DE AWAIT')
    print('='*70)
    
    # 1. Procurar erros específicos de await
    await_errors = find_await_dict_errors()
    
    # 2. Procurar chamadas específicas
    function_calls = find_specific_function_calls()
    
    # 3. Verificar definições de funções
    function_defs = check_function_definitions()
    
    # Resumo
    print('\n' + '='*70)
    print('📊 RESUMO DA ANÁLISE')
    print('='*70)
    print(f'Erros de await encontrados: {len(await_errors)}')
    print(f'Chamadas suspeitas encontradas: {len(function_calls)}')
    print(f'Definições de funções analisadas: {len(function_defs)}')
    
    # Prioridades
    if function_calls:
        print('\n🚨 PRIORIDADE ALTA - Chamadas await suspeitas:')
        for call in function_calls:
            file_name = call['file'].split('/')[-1].split('\\')[-1]
            print(f'  - {file_name}:{call["line"]} - {call["function"]}')
    
    return {
        'await_errors': await_errors,
        'function_calls': function_calls,
        'function_definitions': function_defs
    }

if __name__ == "__main__":
    main() 