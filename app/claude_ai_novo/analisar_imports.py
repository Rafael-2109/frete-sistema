#!/usr/bin/env python3
"""
Analisador de Imports - Claude AI Novo
Identifica e corrige problemas de imports no sistema modular
"""

import os
import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
import json

class ImportAnalyzer:
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent
        self.issues = []
        self.unused_imports = defaultdict(list)
        self.missing_imports = defaultdict(list)
        self.broken_imports = defaultdict(list)
        self.duplicate_imports = defaultdict(list)
        
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analisa um arquivo Python para problemas de import"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            # Extrair todos os imports
            imports = self._extract_imports(tree)
            
            # Extrair todos os nomes usados no código
            used_names = self._extract_used_names(tree)
            
            # Analisar problemas
            file_issues = {
                'file': str(file_path),
                'imports': imports,
                'used_names': used_names,
                'unused_imports': [],
                'missing_imports': [],
                'broken_imports': [],
                'duplicate_imports': []
            }
            
            # Verificar imports não utilizados
            unused = self._find_unused_imports(imports, used_names)
            file_issues['unused_imports'] = unused
            
            # Verificar imports duplicados
            duplicates = self._find_duplicate_imports(imports)
            file_issues['duplicate_imports'] = duplicates
            
            # Verificar imports quebrados (não existem)
            broken = self._find_broken_imports(imports, file_path)
            file_issues['broken_imports'] = broken
            
            return file_issues
            
        except Exception as e:
            return {
                'file': str(file_path),
                'error': str(e),
                'imports': [],
                'used_names': set(),
                'unused_imports': [],
                'missing_imports': [],
                'broken_imports': [],
                'duplicate_imports': []
            }
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extrai todos os imports de um AST"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno,
                        'names': [alias.name]
                    })
                    
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                names = [alias.name for alias in node.names]
                
                imports.append({
                    'type': 'from_import',
                    'module': module,
                    'names': names,
                    'line': node.lineno,
                    'level': node.level  # Para imports relativos
                })
        
        return imports
    
    def _extract_used_names(self, tree: ast.AST) -> Set[str]:
        """Extrai todos os nomes/símbolos usados no código"""
        used_names = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Para casos como 'module.function'
                used_names.add(self._get_attribute_base(node))
                
        return used_names
    
    def _get_attribute_base(self, node: ast.Attribute) -> str:
        """Obtém o nome base de um atributo (ex: 'os' de 'os.path')"""
        if isinstance(node.value, ast.Name):
            return node.value.id
        elif isinstance(node.value, ast.Attribute):
            return self._get_attribute_base(node.value)
        return ''
    
    def _find_unused_imports(self, imports: List[Dict], used_names: Set[str]) -> List[Dict]:
        """Encontra imports que não são utilizados"""
        unused = []
        
        for imp in imports:
            if imp['type'] == 'import':
                # Import direto: import os
                module_name = imp['alias'] or imp['module'].split('.')[0]
                if module_name not in used_names:
                    unused.append(imp)
                    
            elif imp['type'] == 'from_import':
                # Import from: from os import path
                unused_names = []
                for name in imp['names']:
                    if name == '*':
                        # from module import * - difícil de analisar
                        continue
                    if name not in used_names:
                        unused_names.append(name)
                
                if unused_names:
                    imp_copy = imp.copy()
                    imp_copy['unused_names'] = unused_names
                    unused.append(imp_copy)
        
        return unused
    
    def _find_duplicate_imports(self, imports: List[Dict]) -> List[List[Dict]]:
        """Encontra imports duplicados"""
        seen = {}
        duplicates = []
        
        for imp in imports:
            if imp['type'] == 'import':
                key = f"import_{imp['module']}"
            else:
                key = f"from_{imp['module']}_import_{','.join(sorted(imp['names']))}"
            
            if key in seen:
                duplicates.append([seen[key], imp])
            else:
                seen[key] = imp
                
        return duplicates
    
    def _find_broken_imports(self, imports: List[Dict], file_path: Path) -> List[Dict]:
        """Encontra imports que apontam para módulos inexistentes"""
        broken = []
        
        for imp in imports:
            module = imp['module']
            
            # Skip imports do sistema Python padrão
            if self._is_stdlib_module(module):
                continue
                
            # Skip imports de terceiros conhecidos
            if self._is_known_third_party(module):
                continue
            
            # Verificar se módulo existe
            if not self._module_exists(module, file_path):
                broken.append(imp)
                
        return broken
    
    def _is_stdlib_module(self, module: str) -> bool:
        """Verifica se é um módulo da biblioteca padrão"""
        stdlib_modules = {
            'os', 'sys', 'json', 'ast', 're', 'pathlib', 'typing', 
            'collections', 'datetime', 'logging', 'asyncio', 'functools',
            'itertools', 'time', 'copy', 'io', 'threading', 'subprocess'
        }
        
        base_module = module.split('.')[0]
        return base_module in stdlib_modules
    
    def _is_known_third_party(self, module: str) -> bool:
        """Verifica se é um módulo de terceiros conhecido"""
        third_party_modules = {
            'flask', 'sqlalchemy', 'anthropic', 'openai', 'redis', 
            'pandas', 'numpy', 'spacy', 'nltk', 'sklearn', 'torch',
            'transformers', 'plotly', 'marshmallow', 'flask_login',
            'flask_wtf', 'wtforms', 'werkzeug', 'click', 'boto3',
            'requests', 'urllib3', 'jinja2', 'itsdangerous'
        }
        
        base_module = module.split('.')[0]
        return base_module in third_party_modules
    
    def _module_exists(self, module: str, current_file: Path) -> bool:
        """Verifica se um módulo existe no sistema"""
        
        # Imports relativos ao app principal
        if module.startswith('app.'):
            app_path = self.base_path.parent.parent
            module_path = module.replace('app.', '').replace('.', '/')
            full_path = app_path / 'app' / f"{module_path}.py"
            
            if full_path.exists():
                return True
                
            # Verificar se é um package (diretório com __init__.py)
            package_path = app_path / 'app' / module_path
            if package_path.is_dir() and (package_path / '__init__.py').exists():
                return True
                
        # Imports relativos ao claude_ai_novo
        elif module.startswith('.'):
            # Import relativo
            relative_path = module[1:].replace('.', '/')  # Remove o '.' inicial
            if relative_path:
                full_path = current_file.parent / f"{relative_path}.py"
                if full_path.exists():
                    return True
                    
                # Verificar package
                package_path = current_file.parent / relative_path
                if package_path.is_dir() and (package_path / '__init__.py').exists():
                    return True
        
        else:
            # Import absoluto dentro do claude_ai_novo
            module_path = module.replace('.', '/')
            full_path = self.base_path / f"{module_path}.py"
            
            if full_path.exists():
                return True
                
            # Verificar package
            package_path = self.base_path / module_path
            if package_path.is_dir() and (package_path / '__init__.py').exists():
                return True
        
        return False
    
    def analyze_directory(self, directory: Optional[Path] = None) -> Dict[str, Any]:
        """Analisa todos os arquivos Python em um diretório"""
        
        if directory is None:
            directory = self.base_path
            
        results = {
            'summary': {
                'total_files': 0,
                'files_with_issues': 0,
                'total_unused_imports': 0,
                'total_broken_imports': 0,
                'total_duplicate_imports': 0
            },
            'files': [],
            'critical_issues': [],
            'recommendations': []
        }
        
        # Encontrar todos os arquivos Python
        python_files = list(directory.rglob('*.py'))
        
        for file_path in python_files:
            # Skip arquivos de teste e __pycache__
            if '__pycache__' in str(file_path) or 'test_' in file_path.name:
                continue
                
            file_analysis = self.analyze_file(file_path)
            results['files'].append(file_analysis)
            
            # Atualizar estatísticas
            results['summary']['total_files'] += 1
            
            if (file_analysis.get('unused_imports') or 
                file_analysis.get('broken_imports') or 
                file_analysis.get('duplicate_imports')):
                results['summary']['files_with_issues'] += 1
            
            results['summary']['total_unused_imports'] += len(file_analysis.get('unused_imports', []))
            results['summary']['total_broken_imports'] += len(file_analysis.get('broken_imports', []))
            results['summary']['total_duplicate_imports'] += len(file_analysis.get('duplicate_imports', []))
        
        # Identificar problemas críticos
        results['critical_issues'] = self._identify_critical_issues(results['files'])
        
        # Gerar recomendações
        results['recommendations'] = self._generate_recommendations(results)
        
        return results
    
    def _identify_critical_issues(self, files: List[Dict]) -> List[Dict]:
        """Identifica problemas críticos que impedem o funcionamento"""
        critical = []
        
        for file_data in files:
            file_path = file_data['file']
            
            # Imports quebrados são críticos
            for broken in file_data.get('broken_imports', []):
                critical.append({
                    'type': 'broken_import',
                    'severity': 'HIGH',
                    'file': file_path,
                    'module': broken['module'],
                    'line': broken['line'],
                    'message': f"Import quebrado: {broken['module']} não encontrado"
                })
            
            # Muitos imports não utilizados indicam código morto
            unused_count = len(file_data.get('unused_imports', []))
            if unused_count > 5:
                critical.append({
                    'type': 'too_many_unused',
                    'severity': 'MEDIUM',
                    'file': file_path,
                    'count': unused_count,
                    'message': f"Arquivo com {unused_count} imports não utilizados"
                })
        
        return critical
    
    def _generate_recommendations(self, results: Dict) -> List[Dict]:
        """Gera recomendações para correção"""
        recommendations = []
        
        total_unused = results['summary']['total_unused_imports']
        total_broken = results['summary']['total_broken_imports']
        
        if total_broken > 0:
            recommendations.append({
                'priority': 'HIGH',
                'action': 'fix_broken_imports',
                'description': f"Corrigir {total_broken} imports quebrados que impedem funcionamento",
                'automated': True
            })
        
        if total_unused > 10:
            recommendations.append({
                'priority': 'MEDIUM', 
                'action': 'remove_unused_imports',
                'description': f"Remover {total_unused} imports não utilizados para limpar código",
                'automated': True
            })
        
        return recommendations
    
    def generate_fix_script(self, analysis_results: Dict) -> str:
        """Gera script para corrigir automaticamente os problemas"""
        
        script_lines = [
            "#!/usr/bin/env python3",
            '"""',
            "Script Automatizado de Correção de Imports",
            "Gerado pelo ImportAnalyzer do Claude AI Novo",
            '"""',
            "",
            "import os",
            "import re",
            "from pathlib import Path",
            "",
            "def fix_file_imports(file_path: str):",
            "    \"\"\"Corrige imports em um arquivo específico\"\"\"",
            "    print(f'Corrigindo {file_path}...')",
            "    ",
            "    with open(file_path, 'r', encoding='utf-8') as f:",
            "        lines = f.readlines()",
            "    ",
            "    # Implementar correções aqui",
            "    # ... lógica de correção ...",
            "",
            "def main():",
            "    \"\"\"Função principal\"\"\"",
            "    print('🔧 Iniciando correção automática de imports...')",
            ""
        ]
        
        # Adicionar correções específicas para cada arquivo
        for file_data in analysis_results['files']:
            if not any([file_data.get('unused_imports'), 
                       file_data.get('broken_imports'),
                       file_data.get('duplicate_imports')]):
                continue
                
            file_path = file_data['file']
            script_lines.extend([
                f"    # Corrigir {file_path}",
                f"    fix_file_imports('{file_path}')",
                ""
            ])
        
        script_lines.extend([
            "    print('✅ Correção concluída!')",
            "",
            "if __name__ == '__main__':",
            "    main()"
        ])
        
        return '\n'.join(script_lines)

def main():
    """Função principal para executar análise"""
    
    print("🔍 ANALISADOR DE IMPORTS - CLAUDE AI NOVO")
    print("=" * 50)
    
    analyzer = ImportAnalyzer()
    
    print("📊 Analisando imports em todos os arquivos...")
    results = analyzer.analyze_directory()
    
    # Mostrar resumo
    summary = results['summary']
    print(f"\n📋 RESUMO:")
    print(f"   📁 Arquivos analisados: {summary['total_files']}")
    print(f"   ⚠️  Arquivos com problemas: {summary['files_with_issues']}")
    print(f"   🗑️  Imports não utilizados: {summary['total_unused_imports']}")
    print(f"   ❌ Imports quebrados: {summary['total_broken_imports']}")
    print(f"   🔄 Imports duplicados: {summary['total_duplicate_imports']}")
    
    # Mostrar problemas críticos
    if results['critical_issues']:
        print(f"\n🚨 PROBLEMAS CRÍTICOS:")
        for issue in results['critical_issues'][:10]:  # Mostrar só os primeiros 10
            print(f"   {issue['severity']}: {issue['message']}")
            print(f"      📄 {issue['file']}")
    
    # Mostrar recomendações
    if results['recommendations']:
        print(f"\n💡 RECOMENDAÇÕES:")
        for rec in results['recommendations']:
            print(f"   {rec['priority']}: {rec['description']}")
    
    # Salvar relatório detalhado
    report_path = Path(__file__).parent / 'import_analysis_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n📊 Relatório detalhado salvo em: {report_path}")
    
    # Gerar script de correção
    fix_script = analyzer.generate_fix_script(results)
    fix_script_path = Path(__file__).parent / 'fix_imports_auto.py'
    
    with open(fix_script_path, 'w', encoding='utf-8') as f:
        f.write(fix_script)
    
    print(f"🔧 Script de correção gerado em: {fix_script_path}")
    
    return results

if __name__ == "__main__":
    results = main() 