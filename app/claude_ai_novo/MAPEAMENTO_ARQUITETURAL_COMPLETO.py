#!/usr/bin/env python3
"""
MAPEAMENTO ARQUITETURAL COMPLETO - Claude AI Novo
Analisa toda a estrutura de pastas, arquivos, classes e métodos
"""

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

class ArchitecturalAnalyzer:
    """Analisador completo da arquitetura do sistema"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.structure = {}
        self.statistics = {}
        
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analisa um arquivo Python específico"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            file_info = {
                'path': str(file_path),
                'size_lines': len(content.splitlines()),
                'size_bytes': len(content.encode('utf-8')),
                'classes': [],
                'functions': [],
                'imports': [],
                'constants': [],
                'docstring': ast.get_docstring(tree) or "Sem documentação"
            }
            
            # Analisar nós do AST
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = self._analyze_class(node)
                    file_info['classes'].append(class_info)
                
                elif isinstance(node, ast.FunctionDef):
                    # Apenas funções de nível superior (não métodos)
                    if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree) 
                             if hasattr(parent, 'body') and node in getattr(parent, 'body', [])):
                        func_info = self._analyze_function(node)
                        file_info['functions'].append(func_info)
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        file_info['imports'].append({
                            'type': 'import',
                            'module': alias.name,
                            'alias': alias.asname
                        })
                
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        file_info['imports'].append({
                            'type': 'from_import',
                            'module': node.module,
                            'name': alias.name,
                            'alias': alias.asname
                        })
                
                elif isinstance(node, ast.Assign):
                    # Constantes de nível superior
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            file_info['constants'].append(target.id)
            
            return file_info
            
        except Exception as e:
            return {
                'path': str(file_path),
                'error': str(e),
                'size_lines': 0,
                'size_bytes': 0,
                'classes': [],
                'functions': [],
                'imports': [],
                'constants': []
            }
    
    def _analyze_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Analisa uma classe específica"""
        class_info = {
            'name': node.name,
            'bases': [self._get_name(base) for base in node.bases],
            'methods': [],
            'properties': [],
            'docstring': ast.get_docstring(node) or "Sem documentação",
            'decorators': [self._get_name(dec) for dec in node.decorator_list]
        }
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._analyze_function(item, is_method=True)
                if item.name.startswith('_') and not item.name.startswith('__'):
                    method_info['visibility'] = 'private'
                elif item.name.startswith('__'):
                    method_info['visibility'] = 'special'
                else:
                    method_info['visibility'] = 'public'
                
                class_info['methods'].append(method_info)
            
            elif isinstance(item, ast.Assign):
                # Propriedades da classe
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_info['properties'].append(target.id)
        
        return class_info
    
    def _analyze_function(self, node: ast.FunctionDef, is_method: bool = False) -> Dict[str, Any]:
        """Analisa uma função específica"""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        return {
            'name': node.name,
            'args': args,
            'is_async': isinstance(node, ast.AsyncFunctionDef),
            'is_method': is_method,
            'decorators': [self._get_name(dec) for dec in node.decorator_list],
            'docstring': ast.get_docstring(node) or "Sem documentação",
            'returns': self._get_name(node.returns) if node.returns else None
        }
    
    def _get_name(self, node) -> str:
        """Extrai nome de um nó AST"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        else:
            return str(type(node).__name__)
    
    def analyze_directory(self, dir_path: Optional[Path] = None) -> Dict[str, Any]:
        """Analisa uma pasta completa"""
        if dir_path is None:
            dir_path = self.base_path
        
        dir_info = {
            'path': str(dir_path),
            'files': {},
            'subdirectories': {},
            'python_files_count': 0,
            'total_lines': 0,
            'total_classes': 0,
            'total_functions': 0
        }
        
        try:
            for item in dir_path.iterdir():
                if item.is_file() and item.suffix == '.py':
                    file_info = self.analyze_file(item)
                    dir_info['files'][item.name] = file_info
                    dir_info['python_files_count'] += 1
                    dir_info['total_lines'] += file_info.get('size_lines', 0)
                    dir_info['total_classes'] += len(file_info.get('classes', []))
                    dir_info['total_functions'] += len(file_info.get('functions', []))
                
                elif item.is_dir() and not item.name.startswith('.') and item.name != '__pycache__':
                    subdir_info = self.analyze_directory(item)
                    dir_info['subdirectories'][item.name] = subdir_info
                    dir_info['python_files_count'] += subdir_info['python_files_count']
                    dir_info['total_lines'] += subdir_info['total_lines']
                    dir_info['total_classes'] += subdir_info['total_classes']
                    dir_info['total_functions'] += subdir_info['total_functions']
        
        except PermissionError:
            dir_info['error'] = 'Permission denied'
        
        return dir_info
    
    def generate_summary(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Gera resumo estatístico da arquitetura"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_directories': 0,
            'total_python_files': structure.get('python_files_count', 0),
            'total_lines_of_code': structure.get('total_lines', 0),
            'total_classes': structure.get('total_classes', 0),
            'total_functions': structure.get('total_functions', 0),
            'directories_by_purpose': {},
            'largest_files': [],
            'most_complex_classes': [],
            'architectural_insights': []
        }
        
        # Contar diretórios
        def count_dirs(struct):
            count = 0
            if 'subdirectories' in struct:
                count += len(struct['subdirectories'])
                for subdir in struct['subdirectories'].values():
                    count += count_dirs(subdir)
            return count
        
        summary['total_directories'] = count_dirs(structure)
        
        # Classificar diretórios por propósito
        if 'subdirectories' in structure:
            for dir_name, dir_info in structure['subdirectories'].items():
                purpose = self._classify_directory_purpose(dir_name)
                if purpose not in summary['directories_by_purpose']:
                    summary['directories_by_purpose'][purpose] = []
                summary['directories_by_purpose'][purpose].append({
                    'name': dir_name,
                    'files': dir_info['python_files_count'],
                    'lines': dir_info['total_lines'],
                    'classes': dir_info['total_classes']
                })
        
        # Encontrar arquivos maiores
        def collect_files(struct, files_list=[]):
            if 'files' in struct:
                for filename, file_info in struct['files'].items():
                    files_list.append({
                        'name': filename,
                        'path': file_info['path'],
                        'lines': file_info.get('size_lines', 0),
                        'classes': len(file_info.get('classes', [])),
                        'functions': len(file_info.get('functions', []))
                    })
            
            if 'subdirectories' in struct:
                for subdir in struct['subdirectories'].values():
                    collect_files(subdir, files_list)
            
            return files_list
        
        all_files = collect_files(structure)
        summary['largest_files'] = sorted(all_files, key=lambda x: x['lines'], reverse=True)[:10]
        
        # Classes mais complexas (por número de métodos)
        def collect_classes(struct, classes_list=[]):
            if 'files' in struct:
                for filename, file_info in struct['files'].items():
                    for class_info in file_info.get('classes', []):
                        classes_list.append({
                            'name': class_info['name'],
                            'file': filename,
                            'path': file_info['path'],
                            'methods': len(class_info.get('methods', [])),
                            'bases': class_info.get('bases', [])
                        })
            
            if 'subdirectories' in struct:
                for subdir in struct['subdirectories'].values():
                    collect_classes(subdir, classes_list)
            
            return classes_list
        
        all_classes = collect_classes(structure)
        summary['most_complex_classes'] = sorted(all_classes, key=lambda x: x['methods'], reverse=True)[:10]
        
        # Insights arquiteturais
        summary['architectural_insights'] = self._generate_insights(structure, summary)
        
        return summary
    
    def _classify_directory_purpose(self, dir_name: str) -> str:
        """Classifica o propósito de um diretório"""
        mapping = {
            'analyzers': 'Analysis',
            'processors': 'Processing', 
            'orchestrators': 'Orchestration',
            'coordinators': 'Coordination',
            'managers': 'Management',
            'loaders': 'Data Loading',
            'mappers': 'Data Mapping',
            'validators': 'Validation',
            'enrichers': 'Data Enrichment',
            'learners': 'Machine Learning',
            'memorizers': 'Memory Management',
            'conversers': 'Conversation',
            'scanning': 'Code Analysis',
            'integration': 'External Integration',
            'commands': 'Command Processing',
            'tools': 'Utilities',
            'config': 'Configuration',
            'security': 'Security',
            'tests': 'Testing',
            'utils': 'Utilities'
        }
        return mapping.get(dir_name, 'Other')
    
    def _generate_insights(self, structure: Dict[str, Any], summary: Dict[str, Any]) -> List[str]:
        """Gera insights arquiteturais"""
        insights = []
        
        # Verificar complexidade
        avg_lines_per_file = summary['total_lines_of_code'] / max(summary['total_python_files'], 1)
        if avg_lines_per_file > 300:
            insights.append(f"⚠️ Arquivos grandes: média de {avg_lines_per_file:.0f} linhas por arquivo")
        
        # Verificar duplicações de responsabilidade
        dir_purposes = summary['directories_by_purpose']
        if 'Orchestration' in dir_purposes and 'Coordination' in dir_purposes:
            insights.append("🔄 Possível duplicação: Orchestrators e Coordinators podem ter responsabilidades sobrepostas")
        
        # Verificar distribuição de classes
        if summary['total_classes'] > summary['total_python_files'] * 2:
            insights.append("📊 Alta densidade de classes: considerar quebrar arquivos grandes")
        
        # Verificar padrões de nomenclatura
        largest_files = summary['largest_files']
        if any(file['lines'] > 500 for file in largest_files[:5]):
            insights.append("📏 Arquivos muito grandes detectados: considerar refatoração")
        
        return insights
    
    def run_complete_analysis(self) -> Dict[str, Any]:
        """Executa análise completa da arquitetura"""
        print("🔍 Iniciando análise arquitetural completa...")
        
        # Analisar estrutura
        self.structure = self.analyze_directory()
        
        # Gerar resumo
        self.statistics = self.generate_summary(self.structure)
        
        # Resultado completo
        result = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'base_path': str(self.base_path),
                'analyzer_version': '1.0.0'
            },
            'structure': self.structure,
            'summary': self.statistics
        }
        
        print("✅ Análise completa finalizada!")
        return result
    
    def save_results(self, results: Dict[str, Any], output_file: str = "ARQUITETURA_COMPLETA.json"):
        """Salva resultados em arquivo JSON"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Resultados salvos em: {output_file}")
    
    def print_summary(self, summary: Dict[str, Any]):
        """Imprime resumo formatado"""
        print("\n" + "="*80)
        print("📊 RESUMO ARQUITETURAL - CLAUDE AI NOVO")
        print("="*80)
        
        print(f"📁 Total de diretórios: {summary['total_directories']}")
        print(f"📄 Total de arquivos Python: {summary['total_python_files']}")
        print(f"📏 Total de linhas de código: {summary['total_lines_of_code']:,}")
        print(f"🏛️ Total de classes: {summary['total_classes']}")
        print(f"⚙️ Total de funções: {summary['total_functions']}")
        
        print(f"\n📊 DISTRIBUIÇÃO POR PROPÓSITO:")
        for purpose, dirs in summary['directories_by_purpose'].items():
            total_files = sum(d['files'] for d in dirs)
            total_lines = sum(d['lines'] for d in dirs)
            print(f"  {purpose:20} | {len(dirs):2d} dirs | {total_files:3d} files | {total_lines:6,d} lines")
        
        print(f"\n📏 MAIORES ARQUIVOS:")
        for i, file_info in enumerate(summary['largest_files'][:5]):
            print(f"  {i+1}. {file_info['name']:30} | {file_info['lines']:4d} lines | {file_info['classes']:2d} classes")
        
        print(f"\n🏛️ CLASSES MAIS COMPLEXAS:")
        for i, class_info in enumerate(summary['most_complex_classes'][:5]):
            print(f"  {i+1}. {class_info['name']:25} | {class_info['methods']:3d} methods | {class_info['file']}")
        
        if summary['architectural_insights']:
            print(f"\n💡 INSIGHTS ARQUITETURAIS:")
            for insight in summary['architectural_insights']:
                print(f"  {insight}")
        
        print("="*80)

def main():
    """Função principal"""
    analyzer = ArchitecturalAnalyzer()
    
    # Executar análise completa
    results = analyzer.run_complete_analysis()
    
    # Salvar resultados
    analyzer.save_results(results)
    
    # Mostrar resumo
    analyzer.print_summary(results['summary'])
    
    return results

if __name__ == "__main__":
    main() 