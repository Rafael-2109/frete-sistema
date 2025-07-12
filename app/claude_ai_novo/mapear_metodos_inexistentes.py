#!/usr/bin/env python3
"""
🔍 MAPEADOR DE MÉTODOS INEXISTENTES
===================================

Detecta chamadas a métodos que não existem nos objetos.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json
from datetime import datetime

class MethodCallVisitor(ast.NodeVisitor):
    """Visitor que detecta chamadas de métodos"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.method_calls = []
        self.defined_methods = set()
        self.imported_names = set()
        self.class_definitions = {}
        self.current_class = None
        
    def visit_Import(self, node):
        """Registra imports"""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names.add(name)
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        """Registra imports from"""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names.add(name)
        self.generic_visit(node)
        
    def visit_ClassDef(self, node):
        """Registra definições de classes"""
        old_class = self.current_class
        self.current_class = node.name
        self.class_definitions[node.name] = set()
        
        # Registrar métodos da classe
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.class_definitions[node.name].add(item.name)
                self.defined_methods.add(f"{node.name}.{item.name}")
                
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        """Registra definições de funções"""
        if self.current_class:
            self.defined_methods.add(f"{self.current_class}.{node.name}")
        else:
            self.defined_methods.add(node.name)
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        """Detecta acessos a atributos/métodos"""
        if isinstance(node.ctx, ast.Load):
            # Tentar obter o nome do objeto
            obj_name = self._get_object_name(node.value)
            if obj_name:
                # Registrar com informações de localização
                self.method_calls.append({
                    'object': obj_name,
                    'method': node.attr,
                    'line': node.lineno,
                    'file': self.filename,
                    'full_call': f"{obj_name}.{node.attr}"
                })
        self.generic_visit(node)
        
    def _get_object_name(self, node):
        """Extrai o nome do objeto de um nó"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_object_name(node.value)
            if base:
                return f"{base}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_object_name(node.func)
        return None

def analyze_file(filepath: Path) -> Dict[str, any]:
    """Analisa um arquivo Python em busca de métodos inexistentes"""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        visitor = MethodCallVisitor(str(filepath))
        visitor.visit(tree)
        
        return {
            'file': str(filepath),
            'method_calls': visitor.method_calls,
            'defined_methods': visitor.defined_methods,
            'imported_names': visitor.imported_names
        }
    except Exception as e:
        return {
            'file': str(filepath),
            'error': str(e),
            'method_calls': [],
            'defined_methods': set(),
            'imported_names': set()
        }

def find_undefined_methods(base_dir: Path) -> Dict[str, any]:
    """Encontra métodos não definidos em todo o projeto"""
    
    all_method_calls = []
    all_defined_methods = set()
    files_analyzed = 0
    
    # Métodos conhecidos de bibliotecas padrão e frameworks
    known_methods = {
        'logger': {'info', 'debug', 'warning', 'error', 'critical'},
        'self': {'__init__', '__str__', '__repr__'},
        'db': {'session', 'commit', 'rollback', 'query'},
        'request': {'json', 'form', 'args', 'method'},
        'datetime': {'now', 'strftime', 'date', 'time'},
        'Path': {'exists', 'is_file', 'is_dir', 'parent'},
        'os': {'path', 'environ', 'getcwd'},
        'json': {'dumps', 'loads'},
        'ast': {'parse', 'visit', 'generic_visit'},
    }
    
    # Analisar todos os arquivos Python
    for py_file in base_dir.rglob("*.py"):
        if '__pycache__' in str(py_file):
            continue
            
        result = analyze_file(py_file)
        files_analyzed += 1
        
        if 'error' not in result:
            all_method_calls.extend(result['method_calls'])
            all_defined_methods.update(result['defined_methods'])
    
    # Filtrar métodos potencialmente indefinidos
    undefined_methods = []
    method_summary = {}  # Para agrupar por método
    
    for call in all_method_calls:
        obj_name = call['object']
        method_name = call['method']
        full_call = call['full_call']
        
        # Pular métodos conhecidos
        if obj_name in known_methods and method_name in known_methods[obj_name]:
            continue
            
        # Pular métodos mágicos
        if method_name.startswith('__') and method_name.endswith('__'):
            continue
            
        # Verificar se está definido
        if full_call not in all_defined_methods and method_name not in all_defined_methods:
            undefined_methods.append(call)
            
            # Agrupar por método para resumo
            if full_call not in method_summary:
                method_summary[full_call] = []
            method_summary[full_call].append({
                'file': call['file'],
                'line': call['line']
            })
    
    return {
        'files_analyzed': files_analyzed,
        'total_method_calls': len(all_method_calls),
        'total_defined_methods': len(all_defined_methods),
        'undefined_methods': undefined_methods,
        'method_summary': method_summary,
        'timestamp': datetime.now().isoformat()
    }

def generate_report(results: Dict[str, any]) -> str:
    """Gera relatório formatado dos resultados"""
    
    report = []
    report.append("# 🔍 RELATÓRIO DE MÉTODOS INEXISTENTES\n")
    report.append(f"**Data**: {results['timestamp']}")
    report.append(f"**Arquivos analisados**: {results['files_analyzed']}")
    report.append(f"**Total de chamadas**: {results['total_method_calls']}")
    report.append(f"**Métodos definidos**: {results['total_defined_methods']}")
    report.append(f"**Métodos suspeitos**: {len(results['undefined_methods'])}\n")
    
    if results['method_summary']:
        report.append("## 📋 MÉTODOS POTENCIALMENTE INEXISTENTES\n")
        
        # Ordenar por frequência
        sorted_methods = sorted(
            results['method_summary'].items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for method, locations in sorted_methods:
            report.append(f"### `{method}` ({len(locations)} ocorrências)")
            report.append("```")
            for loc in locations[:5]:  # Mostrar até 5 localizações
                file_path = loc['file'].replace('\\', '/')
                report.append(f"  {file_path}:{loc['line']}")
            if len(locations) > 5:
                report.append(f"  ... e mais {len(locations) - 5} ocorrências")
            report.append("```\n")
    else:
        report.append("✅ **Nenhum método suspeito encontrado!**")
    
    return '\n'.join(report)

def main():
    """Função principal"""
    
    print("🔍 MAPEANDO MÉTODOS INEXISTENTES")
    print("=" * 50)
    
    # Diretório base
    base_dir = Path(__file__).parent
    
    # Executar análise
    results = find_undefined_methods(base_dir)
    
    # Salvar resultados JSON
    with open('metodos_inexistentes.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Gerar e salvar relatório
    report = generate_report(results)
    with open('RELATORIO_METODOS_INEXISTENTES.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Imprimir resumo
    print(f"\n📊 RESUMO:")
    print(f"- Arquivos analisados: {results['files_analyzed']}")
    print(f"- Métodos suspeitos: {len(results['undefined_methods'])}")
    
    if results['method_summary']:
        print(f"\n🔍 TOP 5 MÉTODOS MAIS FREQUENTES:")
        sorted_methods = sorted(
            results['method_summary'].items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]
        
        for method, locations in sorted_methods:
            print(f"  - {method}: {len(locations)} ocorrências")
    
    print(f"\n📄 Relatório salvo em: RELATORIO_METODOS_INEXISTENTES.md")
    print(f"📄 Dados JSON salvos em: metodos_inexistentes.json")

if __name__ == "__main__":
    main() 