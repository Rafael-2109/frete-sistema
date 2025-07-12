#!/usr/bin/env python3
"""
🔍 MAPEADOR DE DEPENDÊNCIAS AUSENTES
====================================

Detecta problemas com dependências:
- Modelos SQLAlchemy não disponíveis
- Redis opcional mas código assume disponível
- Imports condicionais mal gerenciados
- Fallbacks incompletos
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import json
from datetime import datetime

class DependencyAnalyzer(ast.NodeVisitor):
    """Analisador de dependências e imports condicionais"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.imports = []
        self.try_imports = []
        self.conditional_imports = []
        self.redis_usage = []
        self.db_usage = []
        self.model_usage = []
        self.fallback_patterns = []
        self.current_try_block = False
        self.in_function = None
        
    def visit_Import(self, node):
        """Registra imports diretos"""
        for alias in node.names:
            import_info = {
                'type': 'direct',
                'module': alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'in_try': self.current_try_block
            }
            if self.current_try_block:
                self.try_imports.append(import_info)
            else:
                self.imports.append(import_info)
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        """Registra imports from"""
        module = node.module or ''
        for alias in node.names:
            import_info = {
                'type': 'from',
                'module': module,
                'name': alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'in_try': self.current_try_block
            }
            if self.current_try_block:
                self.try_imports.append(import_info)
            else:
                self.imports.append(import_info)
        self.generic_visit(node)
        
    def visit_Try(self, node):
        """Detecta blocos try/except com imports"""
        old_try = self.current_try_block
        self.current_try_block = True
        
        # Visitar o bloco try
        for stmt in node.body:
            self.visit(stmt)
            
        # Verificar se há fallback no except
        has_fallback = False
        for handler in node.handlers:
            if handler.body:
                has_fallback = True
                # Analisar o que está no except
                for stmt in handler.body:
                    if isinstance(stmt, ast.Assign):
                        # Detecta padrões como redis_cache = None
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                self.fallback_patterns.append({
                                    'variable': target.id,
                                    'value': ast.unparse(stmt.value) if hasattr(ast, 'unparse') else str(stmt.value),
                                    'line': stmt.lineno,
                                    'type': 'assignment'
                                })
                    self.visit(stmt)
        
        self.current_try_block = old_try
        
        # Se não tem fallback, registrar
        if not has_fallback and self.try_imports:
            self.conditional_imports.append({
                'line': node.lineno,
                'imports': self.try_imports[-len(node.body):],
                'has_fallback': False
            })
            
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        """Detecta uso de atributos (redis, db, models)"""
        if isinstance(node.value, ast.Name):
            name = node.value.id
            attr = node.attr
            
            # Detectar uso de Redis
            if 'redis' in name.lower() or 'cache' in name.lower():
                self.redis_usage.append({
                    'object': name,
                    'attribute': attr,
                    'line': node.lineno,
                    'in_function': self.in_function
                })
                
            # Detectar uso de DB
            elif name == 'db' or 'session' in name.lower():
                self.db_usage.append({
                    'object': name,
                    'attribute': attr,
                    'line': node.lineno,
                    'in_function': self.in_function
                })
                
            # Detectar uso de modelos
            elif name[0].isupper() and attr in ['query', 'filter', 'filter_by', 'get', 'all']:
                self.model_usage.append({
                    'model': name,
                    'method': attr,
                    'line': node.lineno,
                    'in_function': self.in_function
                })
                
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        """Rastreia em qual função estamos"""
        old_function = self.in_function
        self.in_function = node.name
        self.generic_visit(node)
        self.in_function = old_function

def analisar_arquivo(filepath: Path) -> Dict[str, any]:
    """Analisa um arquivo Python em busca de problemas de dependências"""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        analyzer = DependencyAnalyzer(str(filepath))
        analyzer.visit(tree)
        
        # Analisar problemas
        problemas = []
        
        # 1. Imports condicionais sem fallback adequado
        for cond_import in analyzer.conditional_imports:
            if not cond_import['has_fallback']:
                problemas.append({
                    'tipo': 'import_sem_fallback',
                    'linha': cond_import['line'],
                    'descricao': 'Import condicional sem fallback adequado'
                })
                
        # 2. Uso de Redis sem verificação
        redis_checks = []
        for line in content.split('\n'):
            if 'if redis' in line or 'if cache' in line:
                redis_checks.append(line)
                
        for redis_use in analyzer.redis_usage:
            # Verificar se há checagem antes do uso
            has_check = False
            for check in redis_checks:
                if check:  # Simplificado - deveria verificar escopo
                    has_check = True
                    break
                    
            if not has_check:
                problemas.append({
                    'tipo': 'redis_sem_verificacao',
                    'linha': redis_use['line'],
                    'objeto': redis_use['object'],
                    'descricao': f"Uso de {redis_use['object']}.{redis_use['attribute']} sem verificar disponibilidade"
                })
                
        # 3. Uso de modelos sem verificação de contexto Flask
        for model_use in analyzer.model_usage:
            # Verificar se está em contexto apropriado
            if model_use['in_function'] and 'route' not in str(model_use['in_function']):
                problemas.append({
                    'tipo': 'modelo_sem_contexto',
                    'linha': model_use['line'],
                    'modelo': model_use['model'],
                    'descricao': f"Uso de {model_use['model']}.{model_use['method']} pode falhar sem contexto Flask"
                })
                
        # 4. Fallbacks incompletos
        fallback_vars = {f['variable'] for f in analyzer.fallback_patterns}
        imported_vars = {imp['name'] for imp in analyzer.try_imports if 'name' in imp}
        
        missing_fallbacks = imported_vars - fallback_vars
        if missing_fallbacks:
            problemas.append({
                'tipo': 'fallback_incompleto',
                'variaveis': list(missing_fallbacks),
                'descricao': f"Variáveis importadas sem fallback: {', '.join(missing_fallbacks)}"
            })
        
        return {
            'arquivo': str(filepath),
            'problemas': problemas,
            'estatisticas': {
                'total_imports': len(analyzer.imports),
                'imports_condicionais': len(analyzer.try_imports),
                'uso_redis': len(analyzer.redis_usage),
                'uso_db': len(analyzer.db_usage),
                'uso_modelos': len(analyzer.model_usage),
                'fallbacks': len(analyzer.fallback_patterns)
            }
        }
        
    except Exception as e:
        return {
            'arquivo': str(filepath),
            'erro': str(e),
            'problemas': []
        }

def main():
    """Função principal"""
    print("🔍 MAPEANDO DEPENDÊNCIAS AUSENTES")
    print("=" * 50)
    
    base_dir = Path(__file__).parent
    problemas_por_tipo = {}
    total_problemas = 0
    arquivos_analisados = 0
    
    # Analisar todos os arquivos Python
    for arquivo in base_dir.rglob("*.py"):
        # Pular arquivos de teste e ferramentas
        if any(x in str(arquivo) for x in ['test_', 'mapear_', 'verificar_', '__pycache__']):
            continue
            
        resultado = analisar_arquivo(arquivo)
        arquivos_analisados += 1
        
        if resultado['problemas']:
            for problema in resultado['problemas']:
                tipo = problema['tipo']
                if tipo not in problemas_por_tipo:
                    problemas_por_tipo[tipo] = []
                    
                problemas_por_tipo[tipo].append({
                    'arquivo': resultado['arquivo'],
                    'linha': problema.get('linha', 0),
                    'descricao': problema['descricao'],
                    'detalhes': problema
                })
                total_problemas += 1
    
    # Gerar relatório
    relatorio = {
        'timestamp': datetime.now().isoformat(),
        'arquivos_analisados': arquivos_analisados,
        'total_problemas': total_problemas,
        'problemas_por_tipo': problemas_por_tipo
    }
    
    # Salvar JSON
    with open('dependencias_ausentes.json', 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    # Gerar relatório Markdown
    with open('RELATORIO_DEPENDENCIAS_AUSENTES.md', 'w', encoding='utf-8') as f:
        f.write("# 🔍 RELATÓRIO DE DEPENDÊNCIAS AUSENTES\n\n")
        f.write(f"**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Arquivos analisados**: {arquivos_analisados}\n\n")
        f.write(f"**Total de problemas**: {total_problemas}\n\n")
        
        if problemas_por_tipo:
            f.write("## 📊 PROBLEMAS POR TIPO\n\n")
            
            for tipo, problemas in sorted(problemas_por_tipo.items()):
                f.write(f"### {tipo.upper().replace('_', ' ')} ({len(problemas)} ocorrências)\n\n")
                
                for p in sorted(problemas, key=lambda x: x['arquivo']):
                    f.write(f"- **{p['arquivo']}:{p['linha']}**\n")
                    f.write(f"  - {p['descricao']}\n")
                    if 'detalhes' in p and 'variaveis' in p['detalhes']:
                        f.write(f"  - Variáveis: {', '.join(p['detalhes']['variaveis'])}\n")
                    f.write("\n")
                    
        f.write("\n## 🔧 RECOMENDAÇÕES\n\n")
        f.write("1. **Imports condicionais**: Sempre adicionar fallback no bloco except\n")
        f.write("2. **Redis/Cache**: Verificar disponibilidade antes de usar\n")
        f.write("3. **Modelos SQLAlchemy**: Garantir contexto Flask ou usar with app.app_context()\n")
        f.write("4. **Fallbacks**: Definir valores padrão para todas as dependências opcionais\n")
    
    print(f"\n✅ Análise completa!")
    print(f"📊 Total de problemas: {total_problemas}")
    print(f"📋 Tipos de problemas: {len(problemas_por_tipo)}")
    print(f"📄 Relatório salvo em: {Path('RELATORIO_DEPENDENCIAS_AUSENTES.md').absolute()}")

if __name__ == "__main__":
    main() 