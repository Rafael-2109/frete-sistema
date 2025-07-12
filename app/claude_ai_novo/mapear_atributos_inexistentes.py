#!/usr/bin/env python3
"""
🔍 MAPEADOR DE ATRIBUTOS INEXISTENTES
=====================================

Detecta acessos a atributos/métodos que não existem nos objetos.
Mostra exatamente onde cada problema foi encontrado.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import json
from datetime import datetime

class AttributeAccessVisitor(ast.NodeVisitor):
    """Visitor que detecta acessos a atributos"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.attribute_accesses = []
        self.class_definitions = {}
        self.variable_types = {}
        self.current_class = None
        self.current_function = None
        
    def visit_ClassDef(self, node):
        """Registra definições de classes e seus atributos"""
        old_class = self.current_class
        self.current_class = node.name
        
        # Inicializar registro da classe
        if node.name not in self.class_definitions:
            self.class_definitions[node.name] = {
                'methods': set(),
                'attributes': set(),
                'base_classes': [base.id for base in node.bases if isinstance(base, ast.Name)]
            }
        
        # Registrar métodos e atributos
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.class_definitions[node.name]['methods'].add(item.name)
                
                # Se é __init__, procurar self.atributos
                if item.name == '__init__':
                    for stmt in ast.walk(item):
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Attribute) and \
                                   isinstance(target.value, ast.Name) and \
                                   target.value.id == 'self':
                                    self.class_definitions[node.name]['attributes'].add(target.attr)
        
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        """Registra contexto de função"""
        old_function = self.current_function
        self.current_function = node.name
        
        # Analisar tipo de retorno se houver
        if node.returns:
            # Simplificado - apenas para tipos básicos
            pass
            
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_Assign(self, node):
        """Tenta inferir tipos de variáveis"""
        # Simplificado - apenas casos básicos
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Tentar inferir tipo básico
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        self.variable_types[target.id] = node.value.func.id
                        
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        """Detecta acessos a atributos"""
        if isinstance(node.ctx, ast.Load):
            obj_info = self._get_object_info(node.value)
            if obj_info:
                self.attribute_accesses.append({
                    'object': obj_info['name'],
                    'object_type': obj_info.get('type', 'unknown'),
                    'attribute': node.attr,
                    'line': node.lineno,
                    'file': self.filename,
                    'context': f"{self.current_class or 'module'}.{self.current_function or 'top-level'}",
                    'full_access': f"{obj_info['name']}.{node.attr}"
                })
        self.generic_visit(node)
        
    def _get_object_info(self, node) -> Optional[Dict[str, str]]:
        """Extrai informações sobre o objeto"""
        if isinstance(node, ast.Name):
            obj_type = self.variable_types.get(node.id, 'unknown')
            return {'name': node.id, 'type': obj_type}
        elif isinstance(node, ast.Attribute):
            base = self._get_object_info(node.value)
            if base:
                return {'name': f"{base['name']}.{node.attr}", 'type': 'chained'}
        elif isinstance(node, ast.Call):
            func_info = self._get_object_info(node.func)
            if func_info:
                return {'name': f"{func_info['name']}()", 'type': 'call_result'}
        return None

def analyze_file(filepath: Path) -> Dict[str, any]:
    """Analisa um arquivo Python em busca de atributos inexistentes"""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        visitor = AttributeAccessVisitor(str(filepath))
        visitor.visit(tree)
        
        return {
            'file': str(filepath),
            'attribute_accesses': visitor.attribute_accesses,
            'class_definitions': visitor.class_definitions,
            'variable_types': visitor.variable_types
        }
    except Exception as e:
        return {
            'file': str(filepath),
            'error': str(e),
            'attribute_accesses': [],
            'class_definitions': {},
            'variable_types': {}
        }

def find_undefined_attributes(base_dir: Path) -> Dict[str, any]:
    """Encontra atributos não definidos em todo o projeto"""
    
    all_attribute_accesses = []
    all_class_definitions = {}
    files_analyzed = 0
    
    # Atributos conhecidos por tipo
    known_attributes = {
        'self': {'__init__', '__str__', '__repr__', '__class__', '__dict__'},
        'logger': {'info', 'debug', 'warning', 'error', 'critical', 'exception'},
        'request': {'json', 'form', 'args', 'method', 'headers', 'cookies'},
        'response': {'status_code', 'headers', 'data', 'json'},
        'db': {'session', 'Model', 'Column', 'Integer', 'String', 'commit', 'rollback'},
        'datetime': {'now', 'today', 'year', 'month', 'day', 'hour', 'minute'},
        'Path': {'exists', 'is_file', 'is_dir', 'parent', 'name', 'suffix'},
        'dict': {'get', 'keys', 'values', 'items', 'update', 'pop'},
        'list': {'append', 'extend', 'insert', 'remove', 'pop', 'clear'},
        'str': {'split', 'strip', 'lower', 'upper', 'replace', 'format'},
    }
    
    # Padrões suspeitos específicos
    suspicious_patterns = [
        ('semantic_manager', '*'),  # Qualquer acesso a semantic_manager
        ('orchestrator', ['obter_readers', 'verificar_saude_sistema']),
        ('readme_reader', ['validar_estrutura_readme']),
        ('database_reader', ['obter_estatisticas_gerais']),
        ('readers', '*'),  # Variável readers sendo acessada
    ]
    
    # Analisar todos os arquivos Python
    for py_file in base_dir.rglob("*.py"):
        if '__pycache__' in str(py_file) or 'mapear_atributos' in str(py_file):
            continue
            
        result = analyze_file(py_file)
        files_analyzed += 1
        
        if 'error' not in result:
            all_attribute_accesses.extend(result['attribute_accesses'])
            all_class_definitions.update(result['class_definitions'])
    
    # Filtrar atributos suspeitos
    undefined_attributes = []
    attribute_summary = {}  # Para agrupar por atributo
    
    for access in all_attribute_accesses:
        obj_name = access['object']
        attr_name = access['attribute']
        full_access = access['full_access']
        
        # Verificar padrões suspeitos específicos
        is_suspicious = False
        for pattern_obj, pattern_attrs in suspicious_patterns:
            if obj_name == pattern_obj:
                if pattern_attrs == '*' or attr_name in pattern_attrs:
                    is_suspicious = True
                    break
        
        # Verificar se é conhecido
        if not is_suspicious and obj_name in known_attributes:
            if attr_name in known_attributes[obj_name]:
                continue
        
        # Se é suspeito ou não está em atributos conhecidos
        if is_suspicious or obj_name not in known_attributes:
            undefined_attributes.append(access)
            
            # Agrupar por acesso completo
            if full_access not in attribute_summary:
                attribute_summary[full_access] = []
            attribute_summary[full_access].append({
                'file': access['file'],
                'line': access['line'],
                'context': access['context']
            })
    
    return {
        'files_analyzed': files_analyzed,
        'total_attribute_accesses': len(all_attribute_accesses),
        'total_class_definitions': len(all_class_definitions),
        'undefined_attributes': undefined_attributes,
        'attribute_summary': attribute_summary,
        'timestamp': datetime.now().isoformat()
    }

def generate_report(results: Dict[str, any]) -> str:
    """Gera relatório formatado dos resultados"""
    
    report = []
    report.append("# 🔍 RELATÓRIO DE ATRIBUTOS INEXISTENTES\n")
    report.append(f"**Data**: {results['timestamp']}")
    report.append(f"**Arquivos analisados**: {results['files_analyzed']}")
    report.append(f"**Total de acessos**: {results['total_attribute_accesses']}")
    report.append(f"**Classes definidas**: {results['total_class_definitions']}")
    report.append(f"**Atributos suspeitos**: {len(results['undefined_attributes'])}\n")
    
    if results['attribute_summary']:
        report.append("## 📋 ATRIBUTOS POTENCIALMENTE INEXISTENTES\n")
        
        # Ordenar por frequência
        sorted_attrs = sorted(
            results['attribute_summary'].items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        # Agrupar por objeto para melhor organização
        by_object = {}
        for attr, locations in sorted_attrs:
            obj = attr.split('.')[0]
            if obj not in by_object:
                by_object[obj] = []
            by_object[obj].append((attr, locations))
        
        # Mostrar por objeto
        for obj in sorted(by_object.keys()):
            report.append(f"### 🔍 Objeto: `{obj}`\n")
            
            for attr, locations in by_object[obj]:
                report.append(f"#### `{attr}` ({len(locations)} ocorrências)")
                report.append("```")
                for loc in locations[:5]:  # Mostrar até 5 localizações
                    file_path = loc['file'].replace('\\', '/')
                    context = loc['context']
                    report.append(f"  {file_path}:{loc['line']} (em {context})")
                if len(locations) > 5:
                    report.append(f"  ... e mais {len(locations) - 5} ocorrências")
                report.append("```\n")
    else:
        report.append("✅ **Nenhum atributo suspeito encontrado!**")
    
    # Adicionar seção de problemas conhecidos
    report.append("\n## 🎯 PROBLEMAS CONHECIDOS IDENTIFICADOS\n")
    
    known_issues = {
        'semantic_manager': 'Use get_semantic_mapper() de mappers/',
        'orchestrator.obter_readers': 'Método não existe - verificar implementação',
        'orchestrator.verificar_saude_sistema': 'Método não existe - verificar implementação',
        'readme_reader': 'Objeto pode não existir - adicionar verificação',
        'database_reader': 'Objeto pode não existir - adicionar verificação'
    }
    
    for issue, solution in known_issues.items():
        if any(issue in attr for attr in results['attribute_summary'].keys()):
            report.append(f"- **{issue}**: {solution}")
    
    return '\n'.join(report)

def main():
    """Função principal"""
    
    print("🔍 MAPEANDO ATRIBUTOS INEXISTENTES")
    print("=" * 50)
    
    # Diretório base
    base_dir = Path(__file__).parent
    
    # Executar análise
    results = find_undefined_attributes(base_dir)
    
    # Salvar resultados JSON
    with open('atributos_inexistentes.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Gerar e salvar relatório
    report = generate_report(results)
    with open('RELATORIO_ATRIBUTOS_INEXISTENTES.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Imprimir resumo
    print(f"\n📊 RESUMO:")
    print(f"- Arquivos analisados: {results['files_analyzed']}")
    print(f"- Atributos suspeitos: {len(results['undefined_attributes'])}")
    
    if results['attribute_summary']:
        print(f"\n🔍 TOP 5 ATRIBUTOS MAIS FREQUENTES:")
        sorted_attrs = sorted(
            results['attribute_summary'].items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]
        
        for attr, locations in sorted_attrs:
            print(f"  - {attr}: {len(locations)} ocorrências")
    
    print(f"\n📄 Relatório salvo em: RELATORIO_ATRIBUTOS_INEXISTENTES.md")
    print(f"📄 Dados JSON salvos em: atributos_inexistentes.json")

if __name__ == "__main__":
    main() 