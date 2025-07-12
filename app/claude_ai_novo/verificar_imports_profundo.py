#!/usr/bin/env python3
"""
🔍 VERIFICADOR PROFUNDO DE IMPORTS
==================================

Detecta TODOS os imports, incluindo:
- Imports dentro de funções
- Imports dentro de try/except
- Imports condicionais
- Placeholders e fallbacks
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import json
from datetime import datetime

class DeepImportAnalyzer(ast.NodeVisitor):
    """Analisador profundo de imports em todos os contextos"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.all_imports = []
        self.function_imports = []
        self.try_imports = []
        self.placeholders = []
        self.current_function = None
        self.current_class = None
        self.in_try = False
        self.in_except = False
        
    def visit_FunctionDef(self, node):
        """Rastreia função atual"""
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func
        
    def visit_ClassDef(self, node):
        """Rastreia classe atual"""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_Try(self, node):
        """Rastreia blocos try/except"""
        old_try = self.in_try
        self.in_try = True
        
        # Visitar corpo do try
        for stmt in node.body:
            self.visit(stmt)
            
        self.in_try = old_try
        
        # Visitar handlers
        for handler in node.handlers:
            old_except = self.in_except
            self.in_except = True
            
            for stmt in handler.body:
                # Detectar placeholders/fallbacks
                if isinstance(stmt, ast.Return):
                    if isinstance(stmt.value, ast.Constant):
                        if 'placeholder' in str(stmt.value.value).lower() or 'mock' in str(stmt.value.value).lower():
                            self.placeholders.append({
                                'type': 'return_placeholder',
                                'value': str(stmt.value.value),
                                'line': stmt.lineno,
                                'context': self._get_context()
                            })
                elif isinstance(stmt, ast.Assign):
                    # Detectar assignments de None ou Mock
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            if isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
                                self.placeholders.append({
                                    'type': 'none_assignment',
                                    'variable': target.id,
                                    'line': stmt.lineno,
                                    'context': self._get_context()
                                })
                            elif isinstance(stmt.value, ast.Call):
                                if hasattr(stmt.value.func, 'id') and 'mock' in stmt.value.func.id.lower():
                                    self.placeholders.append({
                                        'type': 'mock_assignment',
                                        'variable': target.id,
                                        'line': stmt.lineno,
                                        'context': self._get_context()
                                    })
                                    
                self.visit(stmt)
                
            self.in_except = old_except
            
        self.generic_visit(node)
        
    def visit_Import(self, node):
        """Registra todos os imports"""
        for alias in node.names:
            import_info = {
                'type': 'import',
                'module': alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'context': self._get_context(),
                'in_function': self.current_function is not None,
                'in_try': self.in_try,
                'in_except': self.in_except
            }
            
            self.all_imports.append(import_info)
            
            if self.current_function:
                self.function_imports.append(import_info)
            if self.in_try or self.in_except:
                self.try_imports.append(import_info)
                
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        """Registra todos os imports from"""
        module = node.module or ''
        
        for alias in node.names:
            import_info = {
                'type': 'from',
                'module': module,
                'name': alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'context': self._get_context(),
                'in_function': self.current_function is not None,
                'in_try': self.in_try,
                'in_except': self.in_except
            }
            
            self.all_imports.append(import_info)
            
            if self.current_function:
                self.function_imports.append(import_info)
            if self.in_try or self.in_except:
                self.try_imports.append(import_info)
                
        self.generic_visit(node)
        
    def _get_context(self):
        """Retorna contexto atual"""
        context = []
        if self.current_class:
            context.append(f"class:{self.current_class}")
        if self.current_function:
            context.append(f"function:{self.current_function}")
        if self.in_try:
            context.append("in_try")
        if self.in_except:
            context.append("in_except")
        return " > ".join(context) if context else "module_level"

def verificar_import_existe(module_path: str, base_dir: Path) -> Tuple[bool, str]:
    """Verifica se um import realmente existe"""
    
    # Casos especiais de imports built-in ou externos
    builtin_modules = {
        'os', 'sys', 'json', 'ast', 'logging', 'typing', 'datetime', 
        'pathlib', 'asyncio', 're', 'inspect', 'functools', 'collections',
        'unittest', 'mock'
    }
    
    external_modules = {
        'flask', 'sqlalchemy', 'redis', 'pandas', 'numpy', 'requests',
        'anthropic', 'openai'
    }
    
    # Verificar se é built-in ou externo
    root_module = module_path.split('.')[0]
    if root_module in builtin_modules:
        return True, "builtin"
    if root_module in external_modules:
        return True, "external"
        
    # Converter import path para file path
    if module_path.startswith('app.'):
        # Import absoluto
        rel_path = module_path.replace('app.', '').replace('.', os.sep)
        file_path = base_dir.parent / rel_path
    else:
        # Import relativo ou local
        file_path = base_dir / module_path.replace('.', os.sep)
    
    # Verificar se existe como arquivo ou diretório
    py_file = Path(str(file_path) + '.py')
    init_file = file_path / '__init__.py'
    
    if py_file.exists():
        return True, str(py_file)
    elif file_path.exists() and init_file.exists():
        return True, str(init_file)
    else:
        return False, "not_found"

def analisar_arquivo(filepath: Path, base_dir: Path) -> Dict[str, any]:
    """Analisa um arquivo em busca de imports e placeholders"""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        analyzer = DeepImportAnalyzer(str(filepath))
        analyzer.visit(tree)
        
        # Verificar quais imports estão quebrados
        imports_quebrados = []
        for imp in analyzer.all_imports:
            module = imp['module']
            if imp['type'] == 'from' and imp['name']:
                # Para from X import Y, verificar X
                exists, location = verificar_import_existe(module, base_dir)
                if not exists:
                    imp['status'] = 'broken'
                    imp['reason'] = 'module_not_found'
                    imports_quebrados.append(imp)
            else:
                # Para import X
                exists, location = verificar_import_existe(module, base_dir)
                if not exists:
                    imp['status'] = 'broken'
                    imp['reason'] = 'module_not_found'
                    imports_quebrados.append(imp)
        
        return {
            'arquivo': str(filepath.relative_to(base_dir)),
            'total_imports': len(analyzer.all_imports),
            'imports_em_funcoes': len(analyzer.function_imports),
            'imports_em_try': len(analyzer.try_imports),
            'imports_quebrados': imports_quebrados,
            'placeholders': analyzer.placeholders,
            'tem_problemas': len(imports_quebrados) > 0 or len(analyzer.placeholders) > 0
        }
        
    except Exception as e:
        return {
            'arquivo': str(filepath.relative_to(base_dir)),
            'erro': str(e),
            'tem_problemas': False
        }

def main():
    """Função principal"""
    print("🔍 VERIFICAÇÃO PROFUNDA DE IMPORTS")
    print("=" * 50)
    
    base_dir = Path(__file__).parent
    problemas_encontrados = {
        'imports_quebrados': [],
        'placeholders': [],
        'arquivos_com_problemas': []
    }
    
    total_arquivos = 0
    
    # Analisar todos os arquivos Python
    for arquivo in base_dir.rglob("*.py"):
        # Pular arquivos de teste e este próprio script
        if any(x in str(arquivo) for x in ['__pycache__', 'verificar_imports_profundo.py']):
            continue
            
        total_arquivos += 1
        resultado = analisar_arquivo(arquivo, base_dir)
        
        if resultado.get('tem_problemas'):
            problemas_encontrados['arquivos_com_problemas'].append(resultado['arquivo'])
            
            if resultado.get('imports_quebrados'):
                for imp in resultado['imports_quebrados']:
                    imp['arquivo'] = resultado['arquivo']
                    problemas_encontrados['imports_quebrados'].append(imp)
                    
            if resultado.get('placeholders'):
                for ph in resultado['placeholders']:
                    ph['arquivo'] = resultado['arquivo']
                    problemas_encontrados['placeholders'].append(ph)
    
    # Gerar relatório
    relatorio = {
        'timestamp': datetime.now().isoformat(),
        'total_arquivos': total_arquivos,
        'arquivos_com_problemas': len(problemas_encontrados['arquivos_com_problemas']),
        'total_imports_quebrados': len(problemas_encontrados['imports_quebrados']),
        'total_placeholders': len(problemas_encontrados['placeholders']),
        'detalhes': problemas_encontrados
    }
    
    # Salvar JSON
    with open('imports_profundos.json', 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    # Gerar relatório Markdown
    with open('RELATORIO_IMPORTS_PROFUNDO.md', 'w', encoding='utf-8') as f:
        f.write("# 🔍 RELATÓRIO DE VERIFICAÇÃO PROFUNDA DE IMPORTS\n\n")
        f.write(f"**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total de arquivos**: {total_arquivos}\n")
        f.write(f"**Arquivos com problemas**: {len(problemas_encontrados['arquivos_com_problemas'])}\n")
        f.write(f"**Imports quebrados**: {len(problemas_encontrados['imports_quebrados'])}\n")
        f.write(f"**Placeholders encontrados**: {len(problemas_encontrados['placeholders'])}\n\n")
        
        if problemas_encontrados['imports_quebrados']:
            f.write("## ❌ IMPORTS QUEBRADOS\n\n")
            for imp in problemas_encontrados['imports_quebrados']:
                f.write(f"### {imp['arquivo']}:{imp['line']}\n")
                f.write(f"- **Import**: `{imp['module']}`")
                if imp.get('name'):
                    f.write(f" (from ... import {imp['name']})")
                f.write("\n")
                f.write(f"- **Contexto**: {imp['context']}\n")
                if imp['in_function']:
                    f.write(f"- ⚠️ **Dentro de função**\n")
                if imp['in_try']:
                    f.write(f"- ⚠️ **Dentro de try/except**\n")
                f.write("\n")
        
        if problemas_encontrados['placeholders']:
            f.write("## 🔧 PLACEHOLDERS E FALLBACKS\n\n")
            for ph in problemas_encontrados['placeholders']:
                f.write(f"### {ph['arquivo']}:{ph['line']}\n")
                f.write(f"- **Tipo**: {ph['type']}\n")
                if ph.get('variable'):
                    f.write(f"- **Variável**: `{ph['variable']}`\n")
                if ph.get('value'):
                    f.write(f"- **Valor**: `{ph['value']}`\n")
                f.write(f"- **Contexto**: {ph['context']}\n\n")
    
    print(f"\n✅ Análise completa!")
    print(f"📊 Arquivos com problemas: {len(problemas_encontrados['arquivos_com_problemas'])}")
    print(f"❌ Imports quebrados: {len(problemas_encontrados['imports_quebrados'])}")
    print(f"🔧 Placeholders: {len(problemas_encontrados['placeholders'])}")
    print(f"📄 Relatório salvo em: RELATORIO_IMPORTS_PROFUNDO.md")

if __name__ == "__main__":
    main() 