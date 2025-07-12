#!/usr/bin/env python3
"""
Analisador REAL de Imports - Verifica se arquivos existem
Elimina duplicatas e falsos problemas
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

class RealImportAnalyzer:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.project_root = self.base_dir.parent.parent  # frete_sistema/
        self.claude_ai_novo = self.base_dir
        
        # Cache de arquivos existentes
        self.existing_files = set()
        self._scan_existing_files()
        
        # Módulos Python padrão que sempre existem
        self.stdlib_modules = {
            'abc', 'argparse', 'ast', 'asyncio', 'base64', 'collections',
            'concurrent', 'contextlib', 'copy', 'dataclasses', 'datetime',
            'decimal', 'enum', 'functools', 'hashlib', 'importlib', 'inspect',
            'io', 'itertools', 'json', 'logging', 'math', 'os', 'pathlib',
            'random', 're', 'signal', 'statistics', 'subprocess', 'sys',
            'tempfile', 'threading', 'time', 'traceback', 'typing', 'uuid',
            'warnings', 'weakref'
        }
        
        # Módulos instalados via pip
        self.pip_modules = {
            'flask', 'flask_login', 'flask_sqlalchemy', 'sqlalchemy',
            'werkzeug', 'jinja2', 'click', 'itsdangerous', 'markupsafe',
            'openpyxl', 'pandas', 'numpy', 'redis', 'anthropic',
            'requests', 'urllib3', 'certifi', 'charset_normalizer'
        }
    
    def _scan_existing_files(self):
        """Escaneia todos os arquivos Python existentes no projeto"""
        print("🔍 Escaneando arquivos existentes...")
        
        # Escaneia claude_ai_novo
        for path in self.claude_ai_novo.rglob("*.py"):
            if "__pycache__" not in str(path):
                self.existing_files.add(path.relative_to(self.claude_ai_novo))
        
        # Escaneia app/
        app_dir = self.project_root / "app"
        for path in app_dir.rglob("*.py"):
            if "__pycache__" not in str(path) and "claude_ai_novo" not in str(path):
                self.existing_files.add(path.relative_to(self.project_root))
        
        print(f"✅ Encontrados {len(self.existing_files)} arquivos Python")
    
    def _resolve_import(self, module: str, from_file: str) -> Tuple[bool, str]:
        """Tenta resolver um import e verifica se existe"""
        
        # 1. Biblioteca padrão Python
        base_module = module.split('.')[0]
        if base_module in self.stdlib_modules:
            return True, "stdlib"
        
        # 2. Módulos pip
        if base_module in self.pip_modules:
            return True, "pip"
        
        # 3. Import relativo dentro do claude_ai_novo
        if not module.startswith('app.'):
            # Tenta resolver como caminho relativo
            from_path = Path(from_file).parent
            
            # Converte pontos em barras
            module_path = module.replace('.', '/')
            
            # Tenta várias combinações
            attempts = [
                f"{module_path}.py",
                f"{module_path}/__init__.py",
                f"{from_path}/{module_path}.py",
                f"{from_path}/{module_path}/__init__.py"
            ]
            
            for attempt in attempts:
                path = Path(attempt)
                if path in self.existing_files or (self.claude_ai_novo / path).exists():
                    return True, "internal"
        
        # 4. Import absoluto (app.xxx)
        else:
            # Remove 'app.' e converte
            module_path = module.replace('app.', '').replace('.', '/')
            
            attempts = [
                f"app/{module_path}.py",
                f"app/{module_path}/__init__.py"
            ]
            
            for attempt in attempts:
                path = Path(attempt)
                if path in self.existing_files or (self.project_root / path).exists():
                    return True, "app"
        
        return False, "missing"
    
    def analyze_real_problems(self, imports_file: str = 'imports_reais_problematicos.json'):
        """Analisa apenas problemas REALMENTE reais"""
        
        # Carrega dados
        with open(self.base_dir / imports_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Agrupa imports únicos (elimina duplicatas)
        unique_imports = {}
        stats = {
            'total_reported': 0,
            'unique_imports': 0,
            'really_missing': 0,
            'false_alarms': 0,
            'by_type': defaultdict(int)
        }
        
        print("\n📊 Analisando imports reportados como problemáticos...")
        
        for file_path, problems in data['real_problems'].items():
            for problem in problems:
                stats['total_reported'] += 1
                module = problem.get('module', 'unknown')
                
                # Cria chave única
                key = f"{module}|{file_path}"
                
                if key not in unique_imports:
                    unique_imports[key] = {
                        'module': module,
                        'file': file_path,
                        'occurrences': []
                    }
                
                unique_imports[key]['occurrences'].append({
                    'line': problem.get('line', 0),
                    'context': problem.get('context', '')
                })
        
        stats['unique_imports'] = len(unique_imports)
        
        # Verifica cada import único
        really_missing = {}
        false_alarms = defaultdict(list)
        
        print(f"\n🔍 Verificando {len(unique_imports)} imports únicos...")
        
        for key, import_data in unique_imports.items():
            module = import_data['module']
            file_path = import_data['file']
            
            exists, import_type = self._resolve_import(module, file_path)
            stats['by_type'][import_type] += 1
            
            if exists:
                stats['false_alarms'] += 1
                false_alarms[import_type].append(module)
            else:
                stats['really_missing'] += 1
                really_missing[module] = import_data
        
        return {
            'stats': stats,
            'really_missing': really_missing,
            'false_alarms': dict(false_alarms)
        }
    
    def generate_real_report(self, analysis: Dict):
        """Gera relatório com problemas REALMENTE reais"""
        
        report = []
        report.append("# 🎯 IMPORTS REALMENTE PROBLEMÁTICOS - ANÁLISE FINAL")
        report.append("## Verificação com arquivos existentes\n")
        
        stats = analysis['stats']
        report.append("## 📊 ESTATÍSTICAS REAIS")
        report.append(f"- **Total reportado inicialmente**: {stats['total_reported']}")
        report.append(f"- **Imports únicos**: {stats['unique_imports']}")
        report.append(f"- **REALMENTE faltando**: {stats['really_missing']}")
        report.append(f"- **Falsos alarmes**: {stats['false_alarms']}")
        report.append("")
        
        # Taxa de falsos alarmes
        if stats['unique_imports'] > 0:
            false_rate = (stats['false_alarms'] / stats['unique_imports']) * 100
            report.append(f"### 📈 Taxa de Falsos Alarmes: {false_rate:.1f}%")
        
        # Por tipo
        report.append("\n### 📋 Distribuição por Tipo")
        for import_type, count in sorted(stats['by_type'].items()):
            report.append(f"- **{import_type}**: {count}")
        report.append("")
        
        # Imports realmente faltando
        if analysis['really_missing']:
            report.append("## 🚨 IMPORTS REALMENTE FALTANDO\n")
            
            # Agrupa por categoria
            by_category = defaultdict(list)
            for module, data in analysis['really_missing'].items():
                if module.startswith('app.'):
                    by_category['App Modules'].append(module)
                elif any(module.endswith(suffix) for suffix in ['_manager', '_loader', '_processor']):
                    by_category['Internal Components'].append(module)
                else:
                    by_category['Other'].append(module)
            
            for category, modules in sorted(by_category.items()):
                report.append(f"### {category} ({len(modules)} módulos)")
                for module in sorted(modules)[:10]:
                    report.append(f"- `{module}`")
                if len(modules) > 10:
                    report.append(f"- ... e mais {len(modules) - 10}")
                report.append("")
        else:
            report.append("## ✅ NENHUM IMPORT REALMENTE FALTANDO!")
            report.append("Todos os imports reportados como problemáticos na verdade existem!")
        
        # Falsos alarmes
        if analysis['false_alarms']:
            report.append("\n## 📝 FALSOS ALARMES POR TIPO")
            for import_type, modules in analysis['false_alarms'].items():
                report.append(f"\n### {import_type} ({len(modules)} módulos)")
                for module in sorted(modules)[:5]:
                    report.append(f"- `{module}`")
                if len(modules) > 5:
                    report.append(f"- ... e mais {len(modules) - 5}")
        
        # Salva relatório
        report_path = self.base_dir / 'IMPORTS_REALMENTE_FALTANDO.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        return report_path

def main():
    print("🔍 Análise REAL de Imports Problemáticos")
    print("=" * 60)
    
    analyzer = RealImportAnalyzer()
    
    # Analisa
    print("\n📊 Verificando imports contra arquivos existentes...")
    analysis = analyzer.analyze_real_problems()
    
    # Gera relatório
    print("\n📝 Gerando relatório final...")
    report_path = analyzer.generate_real_report(analysis)
    
    # Mostra resumo
    stats = analysis['stats']
    print(f"\n✅ Análise concluída!")
    print(f"\n📊 RESUMO FINAL:")
    print(f"  - Reportados: {stats['total_reported']}")
    print(f"  - Únicos: {stats['unique_imports']}")
    print(f"  - REALMENTE faltando: {stats['really_missing']}")
    print(f"  - Falsos alarmes: {stats['false_alarms']}")
    
    if stats['unique_imports'] > 0:
        false_rate = (stats['false_alarms'] / stats['unique_imports']) * 100
        print(f"  - Taxa falsos alarmes: {false_rate:.1f}%")
    
    print(f"\n📄 Relatório salvo em: {report_path}")
    
    if stats['really_missing'] < 50:
        print("\n✅ ÓTIMA NOTÍCIA! Apenas alguns imports realmente faltam!")
        print("A maioria dos 800 'problemas' eram falsos alarmes!")

if __name__ == "__main__":
    main() 