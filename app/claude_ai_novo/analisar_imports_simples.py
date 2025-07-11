#!/usr/bin/env python3
"""
🔍 ANÁLISE SIMPLES DE IMPORTS - Claude AI Novo
==============================================

Script simples para detectar problemas de imports
"""

import os
import ast
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class SimpleImportAnalyzer:
    """Analisador simples de imports"""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.broken_imports = []
        self.undefined_symbols = []
        self.unused_imports = []
        self.python_files = []
        self.file_imports = {}
        self.file_symbols = {}
        
    def analyze(self) -> Dict[str, Any]:
        """Analisa todos os arquivos Python"""
        logger.info(f"🔍 Analisando imports em: {self.root_dir}")
        
        # 1. Coletar arquivos Python
        self._collect_python_files()
        
        # 2. Analisar imports e símbolos
        self._analyze_files()
        
        # 3. Detectar problemas
        self._detect_broken_imports()
        self._detect_undefined_symbols()
        self._detect_unused_imports()
        
        # 4. Gerar relatório
        return self._generate_report()
    
    def _collect_python_files(self):
        """Coleta todos os arquivos Python"""
        self.python_files = []
        for root, dirs, files in os.walk(self.root_dir):
            # Ignorar __pycache__
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    self.python_files.append(Path(root) / file)
        
        logger.info(f"📁 Encontrados {len(self.python_files)} arquivos Python")
    
    def _analyze_files(self):
        """Analisa imports e símbolos de todos os arquivos"""
        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                # Extrair imports
                imports = self._extract_imports(tree)
                
                # Extrair símbolos usados
                symbols = self._extract_symbols(tree)
                
                # Armazenar
                rel_path = str(file_path.relative_to(self.root_dir))
                self.file_imports[rel_path] = imports
                self.file_symbols[rel_path] = symbols
                
            except Exception as e:
                logger.error(f"❌ Erro ao analisar {file_path}: {e}")
                self.broken_imports.append({
                    'file': str(file_path),
                    'error': str(e),
                    'type': 'parse_error'
                })
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict]:
        """Extrai informações de imports"""
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
                for alias in node.names:
                    imports.append({
                        'type': 'from_import',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno,
                        'level': node.level
                    })
        
        return imports
    
    def _extract_symbols(self, tree: ast.AST) -> Set[str]:
        """Extrai símbolos usados"""
        symbols = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                symbols.add(node.id)
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                symbols.add(node.value.id)
                symbols.add(f"{node.value.id}.{node.attr}")
        
        return symbols
    
    def _detect_broken_imports(self):
        """Detecta imports quebrados"""
        logger.info("🔍 Detectando imports quebrados...")
        
        for file_path, imports in self.file_imports.items():
            for import_info in imports:
                try:
                    module_name = import_info['module']
                    
                    # Verificar se é import relativo
                    if import_info.get('level', 0) > 0:
                        # Import relativo - verificação básica
                        if not module_name or module_name.strip() == '':
                            continue  # Import relativo de pasta atual
                        
                        # Verificar se arquivo/módulo existe
                        success = self._check_relative_import(file_path, import_info)
                        if not success:
                            self.broken_imports.append({
                                'file': file_path,
                                'import': f"from {'.' * import_info['level']}{module_name} import {import_info['name']}",
                                'line': import_info['line'],
                                'error': f"Módulo relativo '{module_name}' não encontrado",
                                'type': 'relative_import_error'
                            })
                    else:
                        # Import absoluto
                        if not self._check_absolute_import(module_name):
                            self.broken_imports.append({
                                'file': file_path,
                                'import': f"import {module_name}" if import_info['type'] == 'import' else f"from {module_name} import {import_info['name']}",
                                'line': import_info['line'],
                                'error': f"Módulo '{module_name}' não encontrado",
                                'type': 'absolute_import_error'
                            })
                
                except Exception as e:
                    self.broken_imports.append({
                        'file': file_path,
                        'import': str(import_info),
                        'line': import_info.get('line', 0),
                        'error': str(e),
                        'type': 'import_check_error'
                    })
    
    def _check_relative_import(self, file_path: str, import_info: Dict) -> bool:
        """Verifica import relativo"""
        try:
            # Calcular caminho do arquivo atual
            current_dir = Path(file_path).parent
            
            # Subir níveis
            level = import_info.get('level', 1)
            target_dir = current_dir
            for _ in range(level):
                target_dir = target_dir.parent
            
            # Verificar se módulo existe
            module_name = import_info['module']
            if module_name:
                # Verificar se é pasta com __init__.py
                module_path = target_dir / module_name.replace('.', '/')
                if module_path.is_dir():
                    return (module_path / '__init__.py').exists()
                
                # Verificar se é arquivo .py
                module_file = target_dir / f"{module_name.replace('.', '/')}.py"
                return module_file.exists()
            
            return True
            
        except Exception:
            return False
    
    def _check_absolute_import(self, module_name: str) -> bool:
        """Verifica import absoluto"""
        try:
            # Verificar módulos built-in
            if module_name in sys.builtin_module_names:
                return True
            
            # Tentar encontrar spec do módulo
            spec = importlib.util.find_spec(module_name)
            return spec is not None
            
        except Exception:
            return False
    
    def _detect_undefined_symbols(self):
        """Detecta símbolos não definidos"""
        logger.info("🔍 Detectando símbolos não definidos...")
        
        for file_path, imports in self.file_imports.items():
            if file_path not in self.file_symbols:
                continue
                
            # Símbolos importados
            imported_symbols = set()
            for import_info in imports:
                if import_info['type'] == 'import':
                    symbol = import_info['alias'] or import_info['module'].split('.')[-1]
                    imported_symbols.add(symbol)
                else:  # from_import
                    symbol = import_info['alias'] or import_info['name']
                    imported_symbols.add(symbol)
            
            # Símbolos built-in
            builtin_symbols = set(dir(__builtins__))
            
            # Símbolos usados
            used_symbols = self.file_symbols[file_path]
            
            # Verificar símbolos não definidos
            for symbol in used_symbols:
                base_symbol = symbol.split('.')[0]
                
                if (base_symbol not in imported_symbols and 
                    base_symbol not in builtin_symbols and
                    not base_symbol.startswith('_') and
                    base_symbol not in ['self', 'cls']):
                    
                    self.undefined_symbols.append({
                        'file': file_path,
                        'symbol': symbol,
                        'base_symbol': base_symbol,
                        'type': 'undefined_symbol'
                    })
    
    def _detect_unused_imports(self):
        """Detecta imports não utilizados"""
        logger.info("🔍 Detectando imports não utilizados...")
        
        for file_path, imports in self.file_imports.items():
            if file_path not in self.file_symbols:
                continue
                
            used_symbols = self.file_symbols[file_path]
            
            for import_info in imports:
                # Determinar nome do símbolo
                if import_info['type'] == 'import':
                    symbol_name = import_info['alias'] or import_info['module'].split('.')[-1]
                else:  # from_import
                    symbol_name = import_info['alias'] or import_info['name']
                
                # Verificar se é usado
                if symbol_name not in used_symbols:
                    # Verificar se é usado como prefixo
                    used_as_prefix = any(
                        symbol.startswith(f"{symbol_name}.") 
                        for symbol in used_symbols
                    )
                    
                    if not used_as_prefix:
                        self.unused_imports.append({
                            'file': file_path,
                            'import': f"import {import_info['module']}" if import_info['type'] == 'import' else f"from {import_info['module']} import {import_info['name']}",
                            'symbol': symbol_name,
                            'line': import_info['line'],
                            'type': 'unused_import'
                        })
    
    def _generate_report(self) -> Dict[str, Any]:
        """Gera relatório final"""
        total_issues = len(self.broken_imports) + len(self.undefined_symbols) + len(self.unused_imports)
        
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_files': len(self.python_files),
                'total_issues': total_issues,
                'broken_imports': len(self.broken_imports),
                'undefined_symbols': len(self.undefined_symbols),
                'unused_imports': len(self.unused_imports)
            },
            'details': {
                'broken_imports': self.broken_imports,
                'undefined_symbols': self.undefined_symbols,
                'unused_imports': self.unused_imports
            }
        }
        
        return report

def print_report(report: Dict[str, Any]):
    """Imprime relatório"""
    print("\n🔍 RELATÓRIO DE ANÁLISE DE IMPORTS")
    print("=" * 50)
    print(f"⏰ Timestamp: {report['timestamp']}")
    print(f"📁 Arquivos analisados: {report['summary']['total_files']}")
    print(f"⚠️ Total de problemas: {report['summary']['total_issues']}")
    
    print("\n📊 RESUMO:")
    print("-" * 20)
    print(f"❌ Imports quebrados: {report['summary']['broken_imports']}")
    print(f"❓ Símbolos não definidos: {report['summary']['undefined_symbols']}")
    print(f"🗑️ Imports não utilizados: {report['summary']['unused_imports']}")
    
    # Detalhes dos imports quebrados
    if report['details']['broken_imports']:
        print("\n❌ IMPORTS QUEBRADOS:")
        for i, issue in enumerate(report['details']['broken_imports'][:10]):
            print(f"  {i+1}. {issue['file']}:{issue.get('line', '?')}")
            print(f"     {issue['error']}")
            print(f"     {issue.get('import', 'N/A')}")
        
        if len(report['details']['broken_imports']) > 10:
            print(f"     ... e mais {len(report['details']['broken_imports']) - 10} imports quebrados")
    
    # Detalhes dos símbolos não definidos
    if report['details']['undefined_symbols']:
        print("\n❓ SÍMBOLOS NÃO DEFINIDOS:")
        for i, issue in enumerate(report['details']['undefined_symbols'][:10]):
            print(f"  {i+1}. {issue['file']}: {issue['symbol']}")
        
        if len(report['details']['undefined_symbols']) > 10:
            print(f"     ... e mais {len(report['details']['undefined_symbols']) - 10} símbolos não definidos")
    
    # Detalhes dos imports não utilizados
    if report['details']['unused_imports']:
        print("\n🗑️ IMPORTS NÃO UTILIZADOS:")
        for i, issue in enumerate(report['details']['unused_imports'][:10]):
            print(f"  {i+1}. {issue['file']}:{issue.get('line', '?')}")
            print(f"     {issue['import']}")
        
        if len(report['details']['unused_imports']) > 10:
            print(f"     ... e mais {len(report['details']['unused_imports']) - 10} imports não utilizados")

def main():
    """Função principal"""
    print("🚀 Iniciando análise simples de imports...")
    
    # Analisar diretório atual
    analyzer = SimpleImportAnalyzer(".")
    report = analyzer.analyze()
    
    # Imprimir relatório
    print_report(report)
    
    # Salvar relatório
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"relatorio_imports_simples_{timestamp}.json"
    
    try:
        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Relatório salvo em: {report_file}")
    except Exception as e:
        print(f"❌ Erro ao salvar relatório: {e}")

if __name__ == "__main__":
    main() 