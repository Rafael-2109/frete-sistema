#!/usr/bin/env python3
"""
🔍 ANÁLISE DE IMPORTS QUEBRADOS - Claude AI Novo
==============================================

Script para detectar:
- Imports quebrados (não encontrados)
- Símbolos não definidos
- Imports não utilizados
- Dependências circulares
- Problemas de nomenclatura

Análise completa da pasta claude_ai_novo
"""

import os
import ast
import sys
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, Counter
import re
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImportAnalyzer:
    """Analisador de imports para detectar problemas"""
    
    def __init__(self, root_dir: str = "app/claude_ai_novo"):
        self.root_dir = Path(root_dir)
        self.results = {
            'broken_imports': [],
            'undefined_symbols': [],
            'unused_imports': [],
            'circular_dependencies': [],
            'naming_issues': [],
            'missing_modules': [],
            'statistics': {}
        }
        self.python_files = []
        self.module_graph = defaultdict(set)
        self.import_usage = defaultdict(list)
        
        # Padrões comuns de problemas
        self.common_issues = {
            'flask_context': ['current_app', 'g', 'request', 'session'],
            'database': ['db', 'session', 'models'],
            'auth': ['login_required', 'current_user'],
            'missing_inits': []
        }
    
    def scan_directory(self) -> Dict[str, Any]:
        """Escaneia diretório completo"""
        logger.info(f"🔍 Iniciando análise de imports em: {self.root_dir}")
        
        # 1. Coletar todos os arquivos Python
        self._collect_python_files()
        
        # 2. Analisar cada arquivo
        self._analyze_files()
        
        # 3. Detectar problemas específicos
        self._detect_broken_imports()
        self._detect_undefined_symbols()
        self._detect_unused_imports()
        self._detect_circular_dependencies()
        self._detect_naming_issues()
        self._detect_missing_modules()
        
        # 4. Gerar estatísticas
        self._generate_statistics()
        
        # 5. Gerar relatório
        return self._generate_report()
    
    def _collect_python_files(self):
        """Coleta todos os arquivos Python"""
        self.python_files = []
        
        for root, dirs, files in os.walk(self.root_dir):
            # Ignorar __pycache__ e diretórios ocultos
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    self.python_files.append(file_path)
        
        logger.info(f"📁 Encontrados {len(self.python_files)} arquivos Python")
    
    def _analyze_files(self):
        """Analisa cada arquivo Python"""
        for file_path in self.python_files:
            try:
                self._analyze_single_file(file_path)
            except Exception as e:
                logger.error(f"❌ Erro ao analisar {file_path}: {e}")
    
    def _analyze_single_file(self, file_path: Path):
        """Analisa um arquivo Python específico"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content, filename=str(file_path))
            
            # Extrair imports
            imports = self._extract_imports(tree)
            
            # Extrair símbolos usados
            symbols = self._extract_symbols(tree)
            
            # Armazenar informações
            rel_path = str(file_path.relative_to(self.root_dir))
            self.import_usage[rel_path] = {
                'imports': imports,
                'symbols': symbols,
                'content': content,
                'tree': tree
            }
            
        except SyntaxError as e:
            logger.error(f"❌ Erro de sintaxe em {file_path}: {e}")
            self.results['broken_imports'].append({
                'file': str(file_path),
                'error': f"Syntax Error: {e}",
                'type': 'syntax_error'
            })
        except Exception as e:
            logger.error(f"❌ Erro ao processar {file_path}: {e}")
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict]:
        """Extrai imports de um AST"""
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
        """Extrai símbolos usados no código"""
        symbols = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                symbols.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Para casos como module.function
                if isinstance(node.value, ast.Name):
                    symbols.add(f"{node.value.id}.{node.attr}")
        
        return symbols
    
    def _detect_broken_imports(self):
        """Detecta imports quebrados"""
        logger.info("🔍 Detectando imports quebrados...")
        
        for file_path, info in self.import_usage.items():
            for import_info in info['imports']:
                try:
                    # Tentar resolver import
                    if import_info['type'] == 'import':
                        module_name = import_info['module']
                    else:  # from_import
                        module_name = import_info['module']
                    
                    # Verificar se é import relativo ou absoluto
                    if import_info.get('level', 0) > 0:
                        # Import relativo
                        success = self._check_relative_import(file_path, import_info)
                    else:
                        # Import absoluto
                        success = self._check_absolute_import(module_name)
                    
                    if not success:
                        self.results['broken_imports'].append({
                            'file': file_path,
                            'import': import_info,
                            'error': f"Módulo '{module_name}' não encontrado",
                            'type': 'module_not_found'
                        })
                        
                except Exception as e:
                    self.results['broken_imports'].append({
                        'file': file_path,
                        'import': import_info,
                        'error': str(e),
                        'type': 'import_error'
                    })
    
    def _check_relative_import(self, file_path: str, import_info: Dict) -> bool:
        """Verifica import relativo"""
        try:
            # Calcular caminho relativo
            current_dir = Path(file_path).parent
            level = import_info.get('level', 1)
            
            # Subir níveis necessários
            target_dir = current_dir
            for _ in range(level):
                target_dir = target_dir.parent
            
            # Verificar se módulo existe
            module_name = import_info['module']
            if module_name:
                module_path = target_dir / module_name.replace('.', '/')
                return module_path.exists() or (module_path.with_suffix('.py')).exists()
            
            return True
            
        except Exception:
            return False
    
    def _check_absolute_import(self, module_name: str) -> bool:
        """Verifica import absoluto"""
        try:
            # Verificar se é módulo built-in
            if module_name in sys.builtin_module_names:
                return True
            
            # Tentar importar
            spec = importlib.util.find_spec(module_name)
            return spec is not None
            
        except Exception:
            return False
    
    def _detect_undefined_symbols(self):
        """Detecta símbolos não definidos"""
        logger.info("🔍 Detectando símbolos não definidos...")
        
        for file_path, info in self.import_usage.items():
            # Símbolos importados
            imported_symbols = set()
            for import_info in info['imports']:
                if import_info['type'] == 'import':
                    name = import_info['alias'] or import_info['module'].split('.')[-1]
                    imported_symbols.add(name)
                else:  # from_import
                    name = import_info['alias'] or import_info['name']
                    imported_symbols.add(name)
            
            # Símbolos definidos localmente
            defined_symbols = set()
            for node in ast.walk(info['tree']):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    defined_symbols.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            defined_symbols.add(target.id)
            
            # Símbolos built-in
            builtin_symbols = set(dir(__builtins__))
            
            # Verificar símbolos usados
            all_available = imported_symbols | defined_symbols | builtin_symbols
            
            for symbol in info['symbols']:
                # Separar símbolos compostos (module.function)
                base_symbol = symbol.split('.')[0]
                
                if base_symbol not in all_available and not base_symbol.startswith('_'):
                    self.results['undefined_symbols'].append({
                        'file': file_path,
                        'symbol': symbol,
                        'line': 'unknown',  # Seria necessário mais análise AST
                        'type': 'undefined_symbol'
                    })
    
    def _detect_unused_imports(self):
        """Detecta imports não utilizados"""
        logger.info("🔍 Detectando imports não utilizados...")
        
        for file_path, info in self.import_usage.items():
            for import_info in info['imports']:
                # Nome do símbolo importado
                if import_info['type'] == 'import':
                    symbol_name = import_info['alias'] or import_info['module'].split('.')[-1]
                else:  # from_import
                    symbol_name = import_info['alias'] or import_info['name']
                
                # Verificar se é usado
                if symbol_name not in info['symbols']:
                    # Verificar se é usado como parte de outros símbolos
                    used_in_composite = any(
                        symbol.startswith(f"{symbol_name}.") 
                        for symbol in info['symbols']
                    )
                    
                    if not used_in_composite:
                        self.results['unused_imports'].append({
                            'file': file_path,
                            'import': import_info,
                            'symbol': symbol_name,
                            'type': 'unused_import'
                        })
    
    def _detect_circular_dependencies(self):
        """Detecta dependências circulares"""
        logger.info("🔍 Detectando dependências circulares...")
        
        # Construir grafo de dependências
        for file_path, info in self.import_usage.items():
            for import_info in info['imports']:
                if import_info.get('level', 0) > 0:  # Import relativo
                    # Calcular módulo alvo
                    target_module = self._resolve_relative_import(file_path, import_info)
                    if target_module:
                        self.module_graph[file_path].add(target_module)
        
        # Detectar ciclos usando DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node, path):
            if node in rec_stack:
                # Encontrou ciclo
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                self.results['circular_dependencies'].append({
                    'cycle': cycle,
                    'type': 'circular_dependency'
                })
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.module_graph[node]:
                if has_cycle(neighbor, path):
                    return True
            
            rec_stack.remove(node)
            path.pop()
            return False
        
        for node in self.module_graph:
            if node not in visited:
                has_cycle(node, [])
    
    def _resolve_relative_import(self, file_path: str, import_info: Dict) -> Optional[str]:
        """Resolve import relativo para caminho absoluto"""
        try:
            current_dir = Path(file_path).parent
            level = import_info.get('level', 1)
            
            # Subir níveis necessários
            target_dir = current_dir
            for _ in range(level):
                target_dir = target_dir.parent
            
            # Adicionar módulo
            module_name = import_info['module']
            if module_name:
                target_path = target_dir / module_name.replace('.', '/')
                return str(target_path.relative_to(self.root_dir))
            
            return str(target_dir.relative_to(self.root_dir))
            
        except Exception:
            return None
    
    def _detect_naming_issues(self):
        """Detecta problemas de nomenclatura"""
        logger.info("🔍 Detectando problemas de nomenclatura...")
        
        for file_path, info in self.import_usage.items():
            for import_info in info['imports']:
                # Verificar convenções de nomenclatura
                module_name = import_info['module']
                
                # Verificar snake_case vs camelCase
                if module_name and re.search(r'[A-Z]', module_name):
                    if not re.match(r'^[A-Z][a-zA-Z]*$', module_name):  # Não é PascalCase
                        self.results['naming_issues'].append({
                            'file': file_path,
                            'import': import_info,
                            'issue': f"Módulo '{module_name}' não segue convenção snake_case",
                            'type': 'naming_convention'
                        })
                
                # Verificar imports de nomes similares
                if import_info['type'] == 'from_import':
                    name = import_info['name']
                    if name and name.lower() in ['utils', 'helper', 'manager'] and not name.endswith('s'):
                        self.results['naming_issues'].append({
                            'file': file_path,
                            'import': import_info,
                            'issue': f"Nome '{name}' pode ser ambíguo",
                            'type': 'ambiguous_name'
                        })
    
    def _detect_missing_modules(self):
        """Detecta módulos que deveriam existir"""
        logger.info("🔍 Detectando módulos ausentes...")
        
        # Verificar se pastas têm __init__.py
        for root, dirs, files in os.walk(self.root_dir):
            if '__init__.py' not in files and any(f.endswith('.py') for f in files):
                rel_path = str(Path(root).relative_to(self.root_dir))
                self.results['missing_modules'].append({
                    'directory': rel_path,
                    'issue': 'Falta __init__.py',
                    'type': 'missing_init'
                })
    
    def _generate_statistics(self):
        """Gera estatísticas da análise"""
        stats = {
            'total_files': len(self.python_files),
            'total_imports': sum(len(info['imports']) for info in self.import_usage.values()),
            'broken_imports': len(self.results['broken_imports']),
            'undefined_symbols': len(self.results['undefined_symbols']),
            'unused_imports': len(self.results['unused_imports']),
            'circular_dependencies': len(self.results['circular_dependencies']),
            'naming_issues': len(self.results['naming_issues']),
            'missing_modules': len(self.results['missing_modules']),
        }
        
        # Estatísticas por tipo
        import_types = Counter()
        for info in self.import_usage.values():
            for import_info in info['imports']:
                import_types[import_info['type']] += 1
        
        stats['import_types'] = dict(import_types)
        
        # Módulos mais importados
        module_counts = Counter()
        for info in self.import_usage.values():
            for import_info in info['imports']:
                module_counts[import_info['module']] += 1
        
        stats['most_imported'] = dict(module_counts.most_common(10))
        
        self.results['statistics'] = stats
    
    def _generate_report(self) -> Dict[str, Any]:
        """Gera relatório final"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        report = {
            'timestamp': timestamp,
            'summary': {
                'total_files_analyzed': self.results['statistics']['total_files'],
                'total_imports': self.results['statistics']['total_imports'],
                'total_issues': (
                    self.results['statistics']['broken_imports'] +
                    self.results['statistics']['undefined_symbols'] +
                    self.results['statistics']['unused_imports'] +
                    self.results['statistics']['circular_dependencies'] +
                    self.results['statistics']['naming_issues'] +
                    self.results['statistics']['missing_modules']
                )
            },
            'issues': self.results,
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[Dict]:
        """Gera recomendações baseadas nos problemas encontrados"""
        recommendations = []
        
        if self.results['broken_imports']:
            recommendations.append({
                'type': 'broken_imports',
                'priority': 'high',
                'description': 'Corrigir imports quebrados',
                'action': 'Verificar caminhos de módulos e instalar dependências ausentes'
            })
        
        if self.results['undefined_symbols']:
            recommendations.append({
                'type': 'undefined_symbols',
                'priority': 'high',
                'description': 'Definir símbolos não encontrados',
                'action': 'Adicionar imports necessários ou implementar símbolos ausentes'
            })
        
        if self.results['unused_imports']:
            recommendations.append({
                'type': 'unused_imports',
                'priority': 'medium',
                'description': 'Remover imports não utilizados',
                'action': 'Limpar imports desnecessários para melhorar performance'
            })
        
        if self.results['circular_dependencies']:
            recommendations.append({
                'type': 'circular_dependencies',
                'priority': 'high',
                'description': 'Resolver dependências circulares',
                'action': 'Refatorar código para eliminar imports circulares'
            })
        
        if self.results['missing_modules']:
            recommendations.append({
                'type': 'missing_modules',
                'priority': 'medium',
                'description': 'Adicionar arquivos __init__.py',
                'action': 'Criar arquivos __init__.py em diretórios Python'
            })
        
        return recommendations

def print_report(report: Dict[str, Any]):
    """Imprime relatório formatado"""
    print("\n🔍 RELATÓRIO DE ANÁLISE DE IMPORTS")
    print("=" * 50)
    print(f"⏰ Timestamp: {report['timestamp']}")
    print(f"📁 Arquivos analisados: {report['summary']['total_files_analyzed']}")
    print(f"📦 Total de imports: {report['summary']['total_imports']}")
    print(f"⚠️ Total de problemas: {report['summary']['total_issues']}")
    
    print("\n📊 RESUMO DE PROBLEMAS:")
    print("-" * 30)
    issues = report['issues']
    print(f"❌ Imports quebrados: {len(issues['broken_imports'])}")
    print(f"❓ Símbolos não definidos: {len(issues['undefined_symbols'])}")
    print(f"🗑️ Imports não utilizados: {len(issues['unused_imports'])}")
    print(f"🔄 Dependências circulares: {len(issues['circular_dependencies'])}")
    print(f"📝 Problemas de nomenclatura: {len(issues['naming_issues'])}")
    print(f"📂 Módulos ausentes: {len(issues['missing_modules'])}")
    
    # Detalhes dos problemas
    if issues['broken_imports']:
        print("\n❌ IMPORTS QUEBRADOS:")
        for issue in issues['broken_imports'][:5]:  # Mostrar apenas os primeiros 5
            print(f"  • {issue['file']}: {issue['error']}")
        if len(issues['broken_imports']) > 5:
            print(f"  ... e mais {len(issues['broken_imports']) - 5} imports quebrados")
    
    if issues['undefined_symbols']:
        print("\n❓ SÍMBOLOS NÃO DEFINIDOS:")
        for issue in issues['undefined_symbols'][:5]:
            print(f"  • {issue['file']}: {issue['symbol']}")
        if len(issues['undefined_symbols']) > 5:
            print(f"  ... e mais {len(issues['undefined_symbols']) - 5} símbolos não definidos")
    
    if issues['unused_imports']:
        print("\n🗑️ IMPORTS NÃO UTILIZADOS:")
        for issue in issues['unused_imports'][:5]:
            print(f"  • {issue['file']}: {issue['symbol']}")
        if len(issues['unused_imports']) > 5:
            print(f"  ... e mais {len(issues['unused_imports']) - 5} imports não utilizados")
    
    print("\n🎯 RECOMENDAÇÕES:")
    print("-" * 20)
    for rec in report['recommendations']:
        priority_emoji = "🔴" if rec['priority'] == 'high' else "🟡"
        print(f"{priority_emoji} {rec['description']}")
        print(f"   Ação: {rec['action']}")
    
    print("\n📈 ESTATÍSTICAS EXTRAS:")
    print("-" * 25)
    stats = report['issues']['statistics']
    print(f"📊 Tipos de import:")
    for import_type, count in stats['import_types'].items():
        print(f"  • {import_type}: {count}")
    
    print(f"\n📦 Módulos mais importados:")
    for module, count in list(stats['most_imported'].items())[:5]:
        print(f"  • {module}: {count} vezes")

def main():
    """Função principal"""
    print("🚀 Iniciando análise de imports...")
    
    # Analisar pasta claude_ai_novo
    analyzer = ImportAnalyzer("app/claude_ai_novo")
    report = analyzer.scan_directory()
    
    # Imprimir relatório
    print_report(report)
    
    # Salvar relatório em arquivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"app/claude_ai_novo/relatorio_imports_{timestamp}.json"
    
    try:
        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Relatório salvo em: {report_file}")
    except Exception as e:
        print(f"❌ Erro ao salvar relatório: {e}")

if __name__ == "__main__":
    main() 