#!/usr/bin/env python3
"""
🎯 MAPEADOR DE PROBLEMAS REAIS
==============================

Detecta apenas problemas CONFIRMADOS, não suspeitos.
Ignora métodos comuns como logger, get, set, etc.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import json
from datetime import datetime

# Métodos/atributos que sabemos que existem
KNOWN_VALID = {
    # Logging
    'logger', 'info', 'debug', 'error', 'warning', 'critical',
    
    # Python built-ins
    'get', 'set', 'items', 'keys', 'values', 'append', 'extend',
    'strip', 'split', 'join', 'format', 'lower', 'upper', 'replace',
    'startswith', 'endswith', 'find', 'encode', 'decode',
    
    # SQLAlchemy
    'query', 'filter', 'filter_by', 'first', 'all', 'count',
    'order_by', 'limit', 'offset', 'delete', 'update',
    'add', 'commit', 'rollback', 'flush',
    
    # Flask
    'route', 'before_request', 'after_request', 'errorhandler',
    'json', 'args', 'form', 'files', 'method', 'headers',
    
    # Common
    'id', 'name', 'value', 'data', 'result', 'response',
    'status', 'message', 'error', 'success', 'config'
}

# Objetos que sabemos que existem
KNOWN_OBJECTS = {
    'self', 'cls', 'db', 'app', 'request', 'session', 'g',
    'current_user', 'login_user', 'logout_user',
    'json', 'os', 'sys', 'datetime', 'time', 're'
}

# Padrões de problemas CONFIRMADOS que queremos encontrar
REAL_PROBLEMS = {
    'methods': {
        # REMOVIDOS - esses métodos existem, o problema é que o objeto pode ser None
        # 'obter_readers': 'Método não existe no orchestrator',
        # 'verificar_saude_sistema': 'Método não existe no orchestrator',
        # 'validar_estrutura_readme': 'Método não existe em readme_reader',
        # 'obter_estatisticas_gerais': 'Método não existe em database_reader',
        'capture_interaction': 'Método correto é capture_feedback',
        'analisar_intencao': 'Método correto é _detectar_intencao_refinada'
    },
    'attributes': {
        'semantic_manager': 'Deve usar get_semantic_mapper()',
        # REMOVIDOS - esses são problemas de verificação de None, não de existência
        # 'readers': 'Atributo não existe no orchestrator',
        # 'readme_reader': 'Pode não estar inicializado',
        # 'database_reader': 'Pode não estar inicializado'
    }
}

class RealProblemFinder(ast.NodeVisitor):
    """Encontra apenas problemas REAIS, não suspeitos"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.problems = []
        self.current_class = None
        self.current_function = None
        self.in_try_block = False
        
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func
        
    def visit_Try(self, node):
        old_try = self.in_try_block
        self.in_try_block = True
        self.generic_visit(node)
        self.in_try_block = old_try
        
    def visit_Attribute(self, node):
        """Verifica acessos a atributos"""
        if isinstance(node.value, ast.Name):
            obj_name = node.value.id
            attr_name = node.attr
            
            # Verificar se é um problema conhecido
            if attr_name in REAL_PROBLEMS['methods']:
                self.problems.append({
                    'file': self.filename,
                    'line': node.lineno,
                    'type': 'method',
                    'object': obj_name,
                    'attribute': attr_name,
                    'problem': REAL_PROBLEMS['methods'][attr_name],
                    'context': f"{self.current_class}.{self.current_function}" if self.current_class else self.current_function,
                    'in_try': self.in_try_block
                })
            elif obj_name in REAL_PROBLEMS['attributes']:
                self.problems.append({
                    'file': self.filename,
                    'line': node.lineno,
                    'type': 'attribute',
                    'object': obj_name,
                    'attribute': attr_name,
                    'problem': REAL_PROBLEMS['attributes'][obj_name],
                    'context': f"{self.current_class}.{self.current_function}" if self.current_class else self.current_function,
                    'in_try': self.in_try_block
                })
                
        self.generic_visit(node)
        
    def visit_Name(self, node):
        """Verifica uso de variáveis"""
        if isinstance(node.ctx, ast.Load):
            var_name = node.id
            
            # Verificar se é uma variável problemática conhecida
            if var_name in REAL_PROBLEMS['attributes'] and var_name not in KNOWN_OBJECTS:
                self.problems.append({
                    'file': self.filename,
                    'line': node.lineno,
                    'type': 'variable',
                    'name': var_name,
                    'problem': REAL_PROBLEMS['attributes'][var_name],
                    'context': f"{self.current_class}.{self.current_function}" if self.current_class else self.current_function,
                    'in_try': self.in_try_block
                })
                
        self.generic_visit(node)

def find_real_problems():
    """Encontra apenas problemas REAIS no código"""
    
    print("🎯 PROCURANDO APENAS PROBLEMAS REAIS")
    print("=" * 50)
    
    base_dir = Path(__file__).parent
    all_problems = []
    
    # Percorrer arquivos Python
    for root, dirs, files in os.walk(base_dir):
        # Ignorar diretórios
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                filepath = Path(root) / file
                relpath = filepath.relative_to(base_dir)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content)
                    finder = RealProblemFinder(str(relpath))
                    finder.visit(tree)
                    
                    if finder.problems:
                        all_problems.extend(finder.problems)
                        
                except Exception as e:
                    print(f"❌ Erro ao analisar {relpath}: {e}")
    
    # Agrupar por tipo de problema
    problems_by_type = {}
    for problem in all_problems:
        key = f"{problem['type']}:{problem.get('attribute', problem.get('name', ''))}"
        if key not in problems_by_type:
            problems_by_type[key] = []
        problems_by_type[key].append(problem)
    
    # Gerar relatório
    report = ["# 🎯 PROBLEMAS REAIS CONFIRMADOS\n"]
    report.append(f"**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**Total de problemas**: {len(all_problems)}\n")
    report.append(f"**Tipos únicos**: {len(problems_by_type)}\n")
    report.append("\n---\n")
    
    # Problemas por tipo
    for problem_key, instances in sorted(problems_by_type.items()):
        problem_type, problem_name = problem_key.split(':', 1)
        
        report.append(f"\n## {problem_type.upper()}: `{problem_name}`\n")
        report.append(f"**Problema**: {instances[0]['problem']}\n")
        report.append(f"**Ocorrências**: {len(instances)}\n")
        report.append("\n### Localizações:\n")
        
        for inst in instances[:10]:  # Máximo 10 exemplos
            report.append(f"- `{inst['file']}:{inst['line']}` - {inst['context'] or 'módulo'}")
            if inst.get('in_try'):
                report.append(" ⚠️ (em try/except)")
            report.append("\n")
            
        if len(instances) > 10:
            report.append(f"- ... e mais {len(instances) - 10} ocorrências\n")
    
    # Sugestões de correção
    report.append("\n---\n\n## 🔧 CORREÇÕES SUGERIDAS\n")
    
    corrections = {
        'obter_readers': """
```python
# Em orchestrators/main_orchestrator.py ou session_orchestrator.py
def obter_readers(self):
    \"\"\"Obtém os readers disponíveis\"\"\"
    from ..scanning import get_scanning_manager
    scanning_manager = get_scanning_manager()
    return {
        'readme': scanning_manager.get_readme_scanner(),
        'database': scanning_manager.get_database_scanner()
    }
```""",
        'verificar_saude_sistema': """
```python
# Em orchestrators/main_orchestrator.py
def verificar_saude_sistema(self) -> Dict[str, Any]:
    \"\"\"Verifica a saúde do sistema\"\"\"
    return {
        'status': 'healthy',
        'components': self._verificar_componentes(),
        'timestamp': datetime.now().isoformat()
    }
```""",
        'semantic_manager': """
```python
# Substituir semantic_manager por:
from ..mappers import get_semantic_mapper
semantic_mapper = get_semantic_mapper()
```"""
    }
    
    for problem_name, correction in corrections.items():
        if any(problem_name in key for key in problems_by_type):
            report.append(f"\n### Correção para `{problem_name}`:\n")
            report.append(correction)
            report.append("\n")
    
    # Salvar relatório
    report_path = base_dir / "PROBLEMAS_REAIS_CONFIRMADOS.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    # Salvar JSON
    json_path = base_dir / "problemas_reais.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'problems': all_problems,
            'summary': {
                'total': len(all_problems),
                'by_type': {k: len(v) for k, v in problems_by_type.items()}
            },
            'timestamp': datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    # Resumo no console
    print(f"\n✅ Análise completa!")
    print(f"📊 Total de problemas REAIS: {len(all_problems)}")
    print(f"📋 Tipos únicos: {len(problems_by_type)}")
    print(f"📄 Relatório salvo em: {report_path}")
    print(f"📄 JSON salvo em: {json_path}")
    
    # Mostrar resumo
    print("\n🎯 PROBLEMAS ENCONTRADOS:")
    for problem_key, instances in sorted(problems_by_type.items()):
        problem_type, problem_name = problem_key.split(':', 1)
        print(f"  - {problem_type}: {problem_name} ({len(instances)} ocorrências)")

if __name__ == "__main__":
    find_real_problems() 