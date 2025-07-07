#!/usr/bin/env python3
"""
🗺️ MAPEAMENTO COMPLETO CLAUDE AI
Script para mapear todas as funções, classes e dependências do módulo claude_ai
"""

import os
import ast
import re
from typing import Dict, List, Set, Tuple
from pathlib import Path

class CodeAnalyzer:
    """Analisador de código Python"""
    
    def __init__(self):
        self.files_data = {}
        self.dependencies = {}
        
    def analyze_file(self, file_path: str) -> Dict:
        """Analisa um arquivo Python e extrai informações"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                return {
                    'error': f'Erro de sintaxe: {e}',
                    'functions': [],
                    'classes': [],
                    'imports': [],
                    'lines': len(content.split('\n')),
                    'size': len(content)
                }
            
            # Extrair informações
            analyzer = ASTAnalyzer()
            analyzer.visit(tree)
            
            # Extrair imports via regex (mais confiável para imports complexos)
            imports = self._extract_imports_regex(content)
            
            return {
                'functions': analyzer.functions,
                'classes': analyzer.classes,
                'imports': imports,
                'ast_imports': analyzer.imports,
                'lines': len(content.split('\n')),
                'size': len(content),
                'decorators': analyzer.decorators,
                'globals': analyzer.globals
            }
            
        except Exception as e:
            return {
                'error': f'Erro ao analisar: {e}',
                'functions': [],
                'classes': [],
                'imports': [],
                'lines': 0,
                'size': 0
            }
    
    def _extract_imports_regex(self, content: str) -> List[Dict]:
        """Extrai imports usando regex"""
        imports = []
        
        # from X import Y
        from_imports = re.findall(r'from\s+([^\s]+)\s+import\s+([^#\n]+)', content)
        for module, items in from_imports:
            imports.append({
                'type': 'from',
                'module': module.strip(),
                'items': [item.strip() for item in items.split(',')]
            })
        
        # import X
        direct_imports = re.findall(r'^import\s+([^#\n]+)', content, re.MULTILINE)
        for imp in direct_imports:
            imports.append({
                'type': 'import',
                'module': imp.strip(),
                'items': []
            })
        
        return imports

class ASTAnalyzer(ast.NodeVisitor):
    """Visitor para analisar AST"""
    
    def __init__(self):
        self.functions = []
        self.classes = []
        self.imports = []
        self.decorators = []
        self.globals = []
        self.current_class = None
        
    def visit_FunctionDef(self, node):
        """Visita definições de função"""
        # Extrair decoradores
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        # Argumentos
        args = [arg.arg for arg in node.args.args]
        
        func_info = {
            'name': node.name,
            'line': node.lineno,
            'args': args,
            'decorators': decorators,
            'class': self.current_class,
            'is_async': isinstance(node, ast.AsyncFunctionDef),
            'docstring': ast.get_docstring(node) or ''
        }
        
        self.functions.append(func_info)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Visita funções async"""
        self.visit_FunctionDef(node)
    
    def visit_ClassDef(self, node):
        """Visita definições de classe"""
        # Extrair bases
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}" if hasattr(base.value, 'id') else str(base.attr))
        
        class_info = {
            'name': node.name,
            'line': node.lineno,
            'bases': bases,
            'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
            'docstring': ast.get_docstring(node) or ''
        }
        
        self.classes.append(class_info)
        
        # Entrar na classe
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_Import(self, node):
        """Visita imports diretos"""
        for alias in node.names:
            self.imports.append({
                'type': 'import',
                'name': alias.name,
                'asname': alias.asname
            })
    
    def visit_ImportFrom(self, node):
        """Visita imports from"""
        module = node.module or ''
        for alias in node.names:
            self.imports.append({
                'type': 'from',
                'module': module,
                'name': alias.name,
                'asname': alias.asname
            })
    
    def _get_decorator_name(self, decorator):
        """Extrai nome do decorador"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        else:
            return str(decorator)

def mapear_claude_ai():
    """Mapeia todo o módulo claude_ai"""
    print("🗺️ MAPEAMENTO COMPLETO DO MÓDULO CLAUDE AI")
    print("=" * 80)
    
    analyzer = CodeAnalyzer()
    claude_ai_dir = "app/claude_ai"
    
    if not os.path.exists(claude_ai_dir):
        print(f"❌ Diretório não encontrado: {claude_ai_dir}")
        return
    
    # Listar todos os arquivos Python
    python_files = []
    for root, dirs, files in os.walk(claude_ai_dir):
        for file in files:
            if file.endswith('.py') and not file.startswith('.'):
                file_path = os.path.join(root, file)
                python_files.append(file_path)
    
    print(f"📁 Encontrados {len(python_files)} arquivos Python")
    print()
    
    # Analisar cada arquivo
    total_functions = 0
    total_classes = 0
    total_lines = 0
    
    file_analysis = {}
    
    for file_path in sorted(python_files):
        rel_path = os.path.relpath(file_path, claude_ai_dir)
        print(f"🔍 Analisando: {rel_path}")
        
        analysis = analyzer.analyze_file(file_path)
        file_analysis[rel_path] = analysis
        
        if 'error' in analysis:
            print(f"   ❌ {analysis['error']}")
        else:
            functions = len(analysis['functions'])
            classes = len(analysis['classes'])
            lines = analysis['lines']
            
            print(f"   📊 {functions} funções, {classes} classes, {lines} linhas")
            
            total_functions += functions
            total_classes += classes
            total_lines += lines
    
    print()
    print("📊 RESUMO GERAL:")
    print(f"   Total de arquivos: {len(python_files)}")
    print(f"   Total de funções: {total_functions}")
    print(f"   Total de classes: {total_classes}")
    print(f"   Total de linhas: {total_lines:,}")
    
    # Gerar relatório detalhado
    gerar_relatorio_detalhado(file_analysis)
    
    # Gerar mapa de dependências
    gerar_mapa_dependencias(file_analysis)
    
    # Gerar plano de migração
    gerar_plano_migracao(file_analysis)

def gerar_relatorio_detalhado(file_analysis: Dict):
    """Gera relatório detalhado de cada arquivo"""
    print("\n" + "=" * 80)
    print("📋 RELATÓRIO DETALHADO POR ARQUIVO")
    print("=" * 80)
    
    for file_name, analysis in file_analysis.items():
        print(f"\n📄 {file_name}")
        print("-" * 60)
        
        if 'error' in analysis:
            print(f"   ❌ ERRO: {analysis['error']}")
            continue
        
        # Estatísticas
        print(f"   📊 {analysis['lines']} linhas, {analysis['size']} bytes")
        print(f"   🔧 {len(analysis['functions'])} funções, {len(analysis['classes'])} classes")
        
        # Classes
        if analysis['classes']:
            print(f"\n   🏗️ CLASSES ({len(analysis['classes'])}):")
            for cls in analysis['classes']:
                bases_str = f" : {', '.join(cls['bases'])}" if cls['bases'] else ""
                print(f"      • {cls['name']}{bases_str} (linha {cls['line']})")
                if cls['docstring']:
                    doc_preview = cls['docstring'][:50] + "..." if len(cls['docstring']) > 50 else cls['docstring']
                    print(f"        📝 {doc_preview}")
        
        # Funções
        if analysis['functions']:
            print(f"\n   ⚙️ FUNÇÕES ({len(analysis['functions'])}):")
            
            # Agrupar por classe
            functions_by_class = {}
            for func in analysis['functions']:
                class_name = func['class'] or 'Global'
                if class_name not in functions_by_class:
                    functions_by_class[class_name] = []
                functions_by_class[class_name].append(func)
            
            for class_name, functions in functions_by_class.items():
                if class_name != 'Global':
                    print(f"      📁 {class_name}:")
                
                for func in functions:
                    # Decoradores
                    decorators_str = ""
                    if func['decorators']:
                        decorators_str = f" @{', @'.join(func['decorators'])}"
                    
                    # Argumentos
                    args_str = f"({', '.join(func['args'])})" if func['args'] else "()"
                    
                    # Async
                    async_str = "async " if func['is_async'] else ""
                    
                    prefix = "        " if class_name != 'Global' else "      "
                    print(f"{prefix}• {async_str}{func['name']}{args_str}{decorators_str} (linha {func['line']})")
        
        # Imports principais
        if analysis['imports']:
            imports_internos = [imp for imp in analysis['imports'] 
                              if imp['module'].startswith('.') or 'claude_ai' in imp['module']]
            
            if imports_internos:
                print(f"\n   🔗 IMPORTS INTERNOS ({len(imports_internos)}):")
                for imp in imports_internos[:5]:  # Primeiros 5
                    if imp['type'] == 'from':
                        items_str = ', '.join(imp['items'][:3])
                        if len(imp['items']) > 3:
                            items_str += "..."
                        print(f"      • from {imp['module']} import {items_str}")
                    else:
                        print(f"      • import {imp['module']}")
                
                if len(imports_internos) > 5:
                    print(f"      ... e mais {len(imports_internos) - 5} imports")

def gerar_mapa_dependencias(file_analysis: Dict):
    """Gera mapa de dependências entre arquivos"""
    print("\n" + "=" * 80)
    print("🔗 MAPA DE DEPENDÊNCIAS")
    print("=" * 80)
    
    dependencies = {}
    
    for file_name, analysis in file_analysis.items():
        if 'error' in analysis:
            continue
        
        deps = set()
        
        for imp in analysis['imports']:
            module = imp['module']
            
            # Detectar imports internos do claude_ai
            if module.startswith('.'):
                # Import relativo
                if module.startswith('..'):
                    continue  # Fora do módulo
                
                # Converter para nome de arquivo
                if module == '.':
                    continue
                
                module_file = module[1:] + '.py'  # Remove o ponto inicial
                deps.add(module_file)
            
            elif any(keyword in module.lower() for keyword in ['claude', 'conversation', 'learning', 'mcp']):
                # Possível dependência interna
                parts = module.split('.')
                if len(parts) > 1:
                    possible_file = parts[-1] + '.py'
                    deps.add(possible_file)
        
        if deps:
            dependencies[file_name] = deps
    
    # Mostrar dependências
    for file_name, deps in dependencies.items():
        print(f"\n📄 {file_name}")
        print(f"   🔗 Depende de: {', '.join(sorted(deps))}")
    
    # Encontrar arquivos independentes
    all_files = set(file_analysis.keys())
    dependent_files = set()
    for deps in dependencies.values():
        dependent_files.update(deps)
    
    independent_files = all_files - dependent_files
    
    print(f"\n🆓 ARQUIVOS INDEPENDENTES ({len(independent_files)}):")
    for file_name in sorted(independent_files):
        if 'error' not in file_analysis[file_name]:
            funcs = len(file_analysis[file_name]['functions'])
            classes = len(file_analysis[file_name]['classes'])
            print(f"   • {file_name} ({funcs} funções, {classes} classes)")

def gerar_plano_migracao(file_analysis: Dict):
    """Gera plano de migração baseado na análise"""
    print("\n" + "=" * 80)
    print("🚀 PLANO DE MIGRAÇÃO SUGERIDO")
    print("=" * 80)
    
    # Categorizar arquivos
    categorias = {
        'core': [],
        'intelligence': [],
        'analyzers': [],
        'tools': [],
        'security': [],
        'integrations': [],
        'interfaces': [],
        'config': [],
        'deprecated': []
    }
    
    # Classificar arquivos
    for file_name, analysis in file_analysis.items():
        if 'error' in analysis:
            categorias['deprecated'].append((file_name, 'Erro de sintaxe'))
            continue
        
        file_lower = file_name.lower()
        functions = analysis['functions']
        classes = analysis['classes']
        
        # Regras de classificação
        if any(keyword in file_lower for keyword in ['config', 'settings']):
            categorias['config'].append((file_name, f"{len(functions)} funções"))
        
        elif any(keyword in file_lower for keyword in ['security', 'guard', 'validator']):
            categorias['security'].append((file_name, f"{len(functions)} funções"))
        
        elif any(keyword in file_lower for keyword in ['excel', 'generator', 'export']):
            categorias['tools'].append((file_name, f"{len(functions)} funções"))
        
        elif any(keyword in file_lower for keyword in ['learning', 'context', 'feedback']):
            categorias['intelligence'].append((file_name, f"{len(functions)} funções"))
        
        elif any(keyword in file_lower for keyword in ['analyzer', 'nlp', 'query', 'intelligent']):
            categorias['analyzers'].append((file_name, f"{len(functions)} funções"))
        
        elif any(keyword in file_lower for keyword in ['mcp', 'connector', 'integration']):
            categorias['integrations'].append((file_name, f"{len(functions)} funções"))
        
        elif any(keyword in file_lower for keyword in ['routes', 'interface', 'mode']):
            categorias['interfaces'].append((file_name, f"{len(functions)} funções"))
        
        elif 'claude_real_integration' in file_lower:
            categorias['core'].append((file_name, f"GIGANTE: {len(functions)} funções - DIVIDIR"))
        
        else:
            categorias['core'].append((file_name, f"{len(functions)} funções"))
    
    # Mostrar plano
    prioridades = [
        ('🧠 CORE (Núcleo)', 'core', 1),
        ('⚙️ CONFIG (Configurações)', 'config', 1),
        ('🔒 SECURITY (Segurança)', 'security', 2),
        ('🤖 INTELLIGENCE (Inteligência)', 'intelligence', 2),
        ('🔍 ANALYZERS (Análise)', 'analyzers', 3),
        ('🛠️ TOOLS (Ferramentas)', 'tools', 3),
        ('🔌 INTEGRATIONS (Integrações)', 'integrations', 4),
        ('🖥️ INTERFACES (Interfaces)', 'interfaces', 4),
        ('🗑️ DEPRECATED (Problemáticos)', 'deprecated', 5)
    ]
    
    for titulo, categoria, prioridade in prioridades:
        arquivos = categorias[categoria]
        if not arquivos:
            continue
        
        print(f"\n{titulo} (Prioridade {prioridade}):")
        print("-" * 50)
        
        for file_name, descricao in arquivos:
            print(f"   📁 app/claude_ai_novo/{categoria}/{file_name}")
            print(f"      📋 {descricao}")
            
            # Sugestões específicas
            if categoria == 'core' and 'claude_real_integration' in file_name:
                print(f"      ⚠️ DIVIDIR EM: core/claude_client.py, core/query_processor.py")
            
            elif categoria == 'deprecated':
                print(f"      🔧 CORRIGIR: {descricao}")
    
    print(f"\n🎯 RESUMO DO PLANO:")
    print(f"   Fase 1 (Prioridade 1): {len(categorias['core']) + len(categorias['config'])} arquivos")
    print(f"   Fase 2 (Prioridade 2): {len(categorias['security']) + len(categorias['intelligence'])} arquivos") 
    print(f"   Fase 3 (Prioridade 3): {len(categorias['analyzers']) + len(categorias['tools'])} arquivos")
    print(f"   Fase 4 (Prioridade 4): {len(categorias['integrations']) + len(categorias['interfaces'])} arquivos")
    
    print(f"\n💡 PRÓXIMO PASSO RECOMENDADO:")
    print(f"   Começar com arquivos de Prioridade 1 (config e core básico)")

if __name__ == "__main__":
    mapear_claude_ai() 