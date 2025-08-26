#!/usr/bin/env python3
"""
Script para verificar compatibilidade das bibliotecas no requirements.txt
e sugerir correções para Python 3.12+
"""

import sys
import re
from pathlib import Path

def check_requirements():
    """Verifica e sugere correções no requirements.txt"""
    
    print("=" * 60)
    print("VERIFICAÇÃO DE COMPATIBILIDADE - PYTHON 3.12+")
    print("=" * 60)
    
    # Bibliotecas com problemas conhecidos em Python 3.13
    problematic_libs = {
        'python-Levenshtein': {
            'issue': 'Incompatível com Python 3.13 (erro _PyLong_AsByteArray)',
            'solution': 'Use rapidfuzz==3.10.1 ou python-Levenshtein-wheels==0.13.2',
            'critical': True
        },
        'greenlet': {
            'issue': 'Versões < 3.1 incompatíveis com Python 3.12+ (erro _PyCFrame)',
            'solution': 'Use greenlet>=3.1.1',
            'critical': True,
            'min_version': '3.1.1'
        },
        'gevent': {
            'issue': 'Precisa ser compatível com greenlet 3.1+',
            'solution': 'Use gevent>=24.11.1',
            'critical': False,
            'min_version': '24.11.1'
        },
        'PyPDF2': {
            'issue': 'Biblioteca descontinuada',
            'solution': 'Use pypdf ao invés (sucessor oficial)',
            'critical': False
        },
        'cryptography': {
            'issue': 'Versões antigas têm vulnerabilidades',
            'solution': 'Use cryptography>=43.0.0',
            'critical': False,
            'min_version': '43.0.0'
        }
    }
    
    # Ler requirements.txt
    req_file = Path('requirements.txt')
    if not req_file.exists():
        print("❌ Arquivo requirements.txt não encontrado!")
        return
    
    lines = req_file.read_text().splitlines()
    
    issues_found = []
    warnings_found = []
    fixes_applied = []
    
    print("\n📋 Analisando requirements.txt...\n")
    
    for i, line in enumerate(lines):
        # Pular comentários e linhas vazias
        if line.strip().startswith('#') or not line.strip():
            continue
        
        # Extrair nome do pacote e versão
        match = re.match(r'^([a-zA-Z0-9\-_]+)(==|>=|<=|>|<)?(.+)?', line.strip())
        if not match:
            continue
        
        package = match.group(1)
        operator = match.group(2) or ''
        version = match.group(3) or ''
        
        # Remover comentários inline
        if version and '#' in version:
            version = version.split('#')[0].strip()
        
        # Verificar problemas conhecidos
        if package in problematic_libs:
            lib_info = problematic_libs[package]
            
            if lib_info['critical']:
                # Verificar versão mínima se especificada
                if 'min_version' in lib_info:
                    if operator == '==' and version:
                        try:
                            current_ver = tuple(map(int, version.split('.')))
                            min_ver = tuple(map(int, lib_info['min_version'].split('.')))
                            
                            if current_ver < min_ver:
                                issues_found.append({
                                    'package': package,
                                    'line': i + 1,
                                    'current': f"{package}{operator}{version}",
                                    'issue': lib_info['issue'],
                                    'solution': lib_info['solution']
                                })
                            else:
                                fixes_applied.append(f"✅ {package} já está na versão correta ({version})")
                        except:
                            warnings_found.append(f"⚠️  Não foi possível verificar versão de {package}")
                elif package == 'python-Levenshtein':
                    issues_found.append({
                        'package': package,
                        'line': i + 1,
                        'current': line.strip(),
                        'issue': lib_info['issue'],
                        'solution': lib_info['solution']
                    })
            else:
                warnings_found.append(f"⚠️  {package}: {lib_info['issue']}")
    
    # Relatório
    if issues_found:
        print("❌ PROBLEMAS CRÍTICOS ENCONTRADOS:\n")
        for issue in issues_found:
            print(f"   Linha {issue['line']}: {issue['current']}")
            print(f"   Problema: {issue['issue']}")
            print(f"   Solução: {issue['solution']}\n")
    
    if warnings_found:
        print("\n⚠️  AVISOS:\n")
        for warning in warnings_found:
            print(f"   {warning}")
    
    if fixes_applied:
        print("\n✅ CORREÇÕES JÁ APLICADAS:\n")
        for fix in fixes_applied:
            print(f"   {fix}")
    
    # Verificar runtime.txt
    print("\n" + "=" * 60)
    print("VERIFICANDO CONFIGURAÇÃO DO PYTHON")
    print("=" * 60)
    
    runtime_file = Path('runtime.txt')
    if runtime_file.exists():
        runtime_version = runtime_file.read_text().strip()
        print(f"\n✅ runtime.txt encontrado: {runtime_version}")
        
        if '3.13' in runtime_version:
            print("   ⚠️  Python 3.13 pode ter incompatibilidades!")
            print("   💡 Recomendado: python-3.12.7")
        elif '3.12' in runtime_version:
            print("   ✅ Python 3.12 é compatível com todas as bibliotecas")
        else:
            print(f"   ℹ️  Versão: {runtime_version}")
    else:
        print("\n⚠️  Arquivo runtime.txt não encontrado!")
        print("   💡 Crie um arquivo runtime.txt com: python-3.12.7")
    
    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    
    if not issues_found:
        print("\n✅ Nenhum problema crítico encontrado!")
        print("   Seu requirements.txt está compatível com Python 3.12+")
    else:
        print(f"\n❌ {len(issues_found)} problemas críticos encontrados")
        print("   Execute as correções sugeridas acima")
    
    if not runtime_file.exists() or '3.13' in (runtime_file.read_text() if runtime_file.exists() else ''):
        print("\n📝 AÇÃO NECESSÁRIA:")
        print("   1. Crie/edite runtime.txt com: python-3.12.7")
        print("   2. Commit e push das mudanças")
        print("   3. Deploy no Render")
    
    print("\n" + "=" * 60)
    print("✨ Verificação concluída!")
    print("=" * 60)

if __name__ == "__main__":
    check_requirements()