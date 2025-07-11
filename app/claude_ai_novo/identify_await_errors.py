"""
🔍 IDENTIFICAR ERROS DE AWAIT - Script de Identificação
======================================================

Script para identificar erros de await no sistema sem corrigir.
"""

from fix_await_errors import AwaitErrorFixer
import logging

def main():
    logging.basicConfig(level=logging.INFO)

    print('🔍 IDENTIFICANDO ERROS DE AWAIT...')
    print('='*50)

    fixer = AwaitErrorFixer()

    # Detectar erros gerais
    general_errors = fixer.scan_await_errors()
    print(f'Erros gerais encontrados: {len(general_errors)}')

    # Detectar erros específicos
    specific_errors = fixer.detect_specific_await_dict_errors()
    print(f'Erros específicos encontrados: {len(specific_errors)}')

    # Consolidar erros únicos
    all_errors = general_errors + specific_errors
    unique_errors = []
    seen = set()
    for error in all_errors:
        key = (error['file'], error['line'], error['content'])
        if key not in seen:
            unique_errors.append(error)
            seen.add(key)

    print(f'\nTotal de erros únicos: {len(unique_errors)}')
    print('='*50)

    # Mostrar erros críticos
    critical_errors = [e for e in unique_errors if e.get('severity') == 'critical']
    high_errors = [e for e in unique_errors if e.get('severity') == 'high']

    print(f'🚨 ERROS CRÍTICOS: {len(critical_errors)}')
    for error in critical_errors:
        file_name = error['file'].split('/')[-1].split('\\')[-1]
        print(f'  - {file_name}:{error["line"]} - {error["content"]}')

    print(f'\n⚠️  ERROS DE ALTA PRIORIDADE: {len(high_errors)}')
    for error in high_errors:
        file_name = error['file'].split('/')[-1].split('\\')[-1]
        print(f'  - {file_name}:{error["line"]} - {error["content"]}')

    print(f'\n📋 TODOS OS ERROS:')
    for error in unique_errors:
        severity = error.get('severity', 'normal')
        file_name = error['file'].split('/')[-1].split('\\')[-1]
        print(f'  [{severity}] {file_name}:{error["line"]} - {error["content"]}')

    # Relatório por tipo
    print(f'\n📊 RELATÓRIO POR TIPO:')
    types = {}
    for error in unique_errors:
        error_type = error.get('type', 'unknown')
        if error_type not in types:
            types[error_type] = 0
        types[error_type] += 1
    
    for error_type, count in types.items():
        print(f'  - {error_type}: {count}')

    return unique_errors

if __name__ == "__main__":
    main() 