#!/usr/bin/env python3
"""
Verificador de Imports Quebrados - Claude AI Novo
Detecta e reporta todos os imports que estão falhando no sistema
"""

import os
import sys
import ast
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from datetime import datetime
import json

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class ImportChecker:
    """Verifica imports quebrados no sistema"""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path if base_path is not None else os.path.dirname(os.path.abspath(__file__))
        self.results = {
            'total_files': 0,
            'files_with_errors': 0,
            'total_imports': 0,
            'broken_imports': 0,
            'errors': [],
            'summary': {}
        }
        self.checked_modules = set()
        
    def check_directory(self, directory: Optional[str] = None) -> Dict:
        """Verifica todos os arquivos Python em um diretório"""
        if directory is None:
            directory = self.base_path
            
        print(f"\n🔍 Verificando imports em: {directory}")
        print("=" * 80)
        
        for root, dirs, files in os.walk(directory):
            # Pular diretórios especiais
            dirs[:] = [d for d in dirs if not d.startswith(('__', '.', 'venv', 'env'))]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    filepath = os.path.join(root, file)
                    self.check_file(filepath)
                    
        return self.results
    
    def check_file(self, filepath: str) -> List[Dict]:
        """Verifica imports em um arquivo específico"""
        self.results['total_files'] += 1
        relative_path = os.path.relpath(filepath, self.base_path)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse do AST para encontrar imports
            tree = ast.parse(content, filename=filepath)
            imports = self.extract_imports(tree)
            
            if not imports:
                return []
                
            print(f"\n📄 Verificando: {relative_path}")
            file_errors = []
            
            for imp in imports:
                self.results['total_imports'] += 1
                error = self.check_import(imp, filepath)
                
                if error:
                    file_errors.append(error)
                    self.results['broken_imports'] += 1
                    
            if file_errors:
                self.results['files_with_errors'] += 1
                self.results['errors'].extend(file_errors)
                
                # Agrupar por tipo de erro
                for error in file_errors:
                    error_type = error['error_type']
                    if error_type not in self.results['summary']:
                        self.results['summary'][error_type] = []
                    self.results['summary'][error_type].append(error)
                    
            return file_errors
            
        except Exception as e:
            print(f"   ❌ Erro ao processar arquivo: {e}")
            return []
    
    def extract_imports(self, tree: ast.AST) -> List[Dict]:
        """Extrai todos os imports de um AST"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })
                    
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                level = node.level
                
                # Construir nome completo do módulo
                if level > 0:
                    # Import relativo
                    module_name = '.' * level + module
                else:
                    module_name = module
                    
                for alias in node.names:
                    imports.append({
                        'type': 'from',
                        'module': module_name,
                        'name': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno,
                        'level': level
                    })
                    
        return imports
    
    def check_import(self, imp: Dict, filepath: str) -> Dict:
        """Verifica se um import específico funciona"""
        try:
            if imp['type'] == 'import':
                # import module
                module_name = imp['module']
                
                # Pular módulos já verificados
                if module_name in self.checked_modules:
                    return None
                    
                importlib.import_module(module_name)
                self.checked_modules.add(module_name)
                
            else:
                # from module import name
                module_name = imp['module']
                name = imp['name']
                
                # Resolver imports relativos
                if imp['level'] > 0:
                    # Calcular módulo pai baseado no arquivo
                    file_module = self.filepath_to_module(filepath)
                    parent_parts = file_module.split('.')
                    
                    # Subir níveis conforme especificado
                    for _ in range(imp['level']):
                        if parent_parts:
                            parent_parts.pop()
                            
                    # Construir nome completo
                    if module_name.lstrip('.'):
                        parent_parts.append(module_name.lstrip('.'))
                        
                    module_name = '.'.join(parent_parts)
                
                # Tentar importar
                if name == '*':
                    # from module import *
                    module = importlib.import_module(module_name)
                else:
                    # from module import specific
                    module = importlib.import_module(module_name)
                    if not hasattr(module, name):
                        raise AttributeError(f"Module '{module_name}' has no attribute '{name}'")
                        
            return None  # Import OK
            
        except ImportError as e:
            return {
                'file': os.path.relpath(filepath, self.base_path),
                'line': imp['line'],
                'import': self.format_import(imp),
                'error': str(e),
                'error_type': 'ImportError',
                'module': imp.get('module', ''),
                'name': imp.get('name', '')
            }
            
        except AttributeError as e:
            return {
                'file': os.path.relpath(filepath, self.base_path),
                'line': imp['line'],
                'import': self.format_import(imp),
                'error': str(e),
                'error_type': 'AttributeError',
                'module': imp.get('module', ''),
                'name': imp.get('name', '')
            }
            
        except Exception as e:
            return {
                'file': os.path.relpath(filepath, self.base_path),
                'line': imp['line'],
                'import': self.format_import(imp),
                'error': str(e),
                'error_type': type(e).__name__,
                'module': imp.get('module', ''),
                'name': imp.get('name', '')
            }
    
    def filepath_to_module(self, filepath: str) -> str:
        """Converte filepath para nome de módulo"""
        # Remover extensão .py
        module_path = filepath[:-3]
        
        # Converter para nome de módulo
        parts = []
        current = module_path
        
        while current:
            head, tail = os.path.split(current)
            if tail:
                parts.insert(0, tail)
            if head == self.base_path or not head:
                break
            current = head
            
        # Adicionar prefixo app.claude_ai_novo
        parts.insert(0, 'claude_ai_novo')
        parts.insert(0, 'app')
        
        return '.'.join(parts)
    
    def format_import(self, imp: Dict) -> str:
        """Formata import para exibição"""
        if imp['type'] == 'import':
            if imp['alias']:
                return f"import {imp['module']} as {imp['alias']}"
            return f"import {imp['module']}"
        else:
            base = f"from {imp['module']} import {imp['name']}"
            if imp['alias']:
                base += f" as {imp['alias']}"
            return base
    
    def print_report(self):
        """Imprime relatório detalhado"""
        print("\n" + "=" * 80)
        print("📊 RELATÓRIO DE IMPORTS QUEBRADOS")
        print("=" * 80)
        
        print(f"\n📈 Estatísticas:")
        print(f"   Total de arquivos: {self.results['total_files']}")
        print(f"   Arquivos com erros: {self.results['files_with_errors']}")
        print(f"   Total de imports: {self.results['total_imports']}")
        print(f"   Imports quebrados: {self.results['broken_imports']}")
        
        if self.results['broken_imports'] > 0:
            percentage = (self.results['broken_imports'] / self.results['total_imports']) * 100
            print(f"   Taxa de erro: {percentage:.1f}%")
        
        if self.results['errors']:
            print(f"\n❌ IMPORTS QUEBRADOS ({len(self.results['errors'])} total):")
            print("-" * 80)
            
            # Agrupar por arquivo
            by_file = {}
            for error in self.results['errors']:
                file = error['file']
                if file not in by_file:
                    by_file[file] = []
                by_file[file].append(error)
            
            # Exibir por arquivo
            for file, errors in sorted(by_file.items()):
                print(f"\n📄 {file}:")
                for error in errors:
                    print(f"   Linha {error['line']}: {error['import']}")
                    print(f"   ❌ {error['error_type']}: {error['error']}")
                    
        # Resumo por tipo de erro
        if self.results['summary']:
            print(f"\n📊 RESUMO POR TIPO DE ERRO:")
            print("-" * 80)
            
            for error_type, errors in sorted(self.results['summary'].items()):
                print(f"\n{error_type} ({len(errors)} ocorrências):")
                
                # Agrupar por módulo
                by_module = {}
                for error in errors:
                    module = error['module']
                    if module not in by_module:
                        by_module[module] = 0
                    by_module[module] += 1
                
                for module, count in sorted(by_module.items(), key=lambda x: x[1], reverse=True):
                    print(f"   - {module}: {count} erro(s)")
                    
    def save_report(self, filename: Optional[str] = None):
        """Salva relatório em JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"import_errors_{timestamp}.json"
            
        filepath = os.path.join(self.base_path, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
            
        print(f"\n💾 Relatório salvo em: {filepath}")


def main():
    """Função principal"""
    print("🔍 VERIFICADOR DE IMPORTS - CLAUDE AI NOVO")
    print("=" * 80)
    
    # Criar verificador
    checker = ImportChecker()
    
    # Verificar diretório
    results = checker.check_directory()
    
    # Exibir relatório
    checker.print_report()
    
    # Salvar relatório
    if results['broken_imports'] > 0:
        checker.save_report()
        
    # Retornar código de saída
    if results['broken_imports'] > 0:
        print(f"\n❌ Encontrados {results['broken_imports']} imports quebrados!")
        return 1
    else:
        print("\n✅ Todos os imports estão funcionando corretamente!")
        return 0


if __name__ == "__main__":
    sys.exit(main()) 