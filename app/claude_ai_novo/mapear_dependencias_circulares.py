#!/usr/bin/env python3
"""
Mapeador de Dependências Circulares - Claude AI Novo
Detecta loops e dependências circulares entre módulos
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import json

class CircularDependencyMapper:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.dependencies = defaultdict(set)  # arquivo -> conjunto de dependências
        self.circular_deps = []  # lista de ciclos encontrados
        self.import_graph = defaultdict(list)  # grafo de imports
        
    def extract_imports(self, file_path: Path) -> Set[str]:
        """Extrai todos os imports de um arquivo Python"""
        imports = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            # Visitar apenas imports no nível do módulo (não dentro de funções)
            for node in tree.body:
                # Import direto: import module
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                
                # Import from: from module import ...
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Converte imports relativos
                        if node.level > 0:  # Import relativo
                            parts = file_path.parts
                            # Encontra índice de 'claude_ai_novo'
                            try:
                                idx = parts.index('claude_ai_novo')
                                base_parts = list(parts[idx:len(parts)-1])  # Remove filename
                                
                                # Volta níveis conforme node.level
                                for _ in range(node.level):
                                    if base_parts:
                                        base_parts.pop()
                                
                                # Adiciona o módulo
                                if node.module:
                                    base_parts.extend(node.module.split('.'))
                                
                                module = 'app.claude_ai_novo.' + '.'.join(base_parts)
                                imports.add(module)
                            except ValueError:
                                # Não está em claude_ai_novo
                                if node.module:
                                    imports.add(node.module)
                        else:
                            imports.add(node.module)
                            
        except Exception as e:
            print(f"❌ Erro ao processar {file_path}: {e}")
            
        return imports
    
    def normalize_module_path(self, module: str, from_file: Path) -> str:
        """Normaliza um caminho de módulo para comparação"""
        # Se é um módulo do claude_ai_novo
        if module.startswith('app.claude_ai_novo.'):
            return module
            
        # Se é relativo ao claude_ai_novo
        if not module.startswith('app.'):
            # Tenta como módulo interno
            test_module = f'app.claude_ai_novo.{module}'
            # Verifica se existe
            test_path = module.replace('.', '/') + '.py'
            if (self.base_dir / test_path).exists():
                return test_module
                
        return module
    
    def build_dependency_graph(self):
        """Constrói o grafo de dependências"""
        print("🔍 Construindo grafo de dependências...")
        
        # Mapeia todos os arquivos Python
        py_files = []
        for path in self.base_dir.rglob("*.py"):
            if "__pycache__" not in str(path):
                py_files.append(path)
        
        print(f"📊 Analisando {len(py_files)} arquivos Python...")
        
        # Para cada arquivo, extrai suas dependências
        for file_path in py_files:
            # Converte path para módulo
            rel_path = file_path.relative_to(self.base_dir.parent.parent)
            module_name = str(rel_path).replace('\\', '.').replace('/', '.')[:-3]  # Remove .py
            
            # Extrai imports
            imports = self.extract_imports(file_path)
            
            # Filtra apenas imports internos do claude_ai_novo
            internal_imports = set()
            for imp in imports:
                normalized = self.normalize_module_path(imp, file_path)
                if 'claude_ai_novo' in normalized:
                    internal_imports.add(normalized)
            
            if internal_imports:
                self.dependencies[module_name] = internal_imports
                for imp in internal_imports:
                    self.import_graph[module_name].append(imp)
    
    def find_cycles_dfs(self) -> List[List[str]]:
        """Encontra ciclos usando DFS"""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str, start: str):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.import_graph.get(node, []):
                if neighbor == start and len(path) > 1:
                    # Encontrou ciclo
                    cycle = path[:]
                    cycles.append(cycle)
                elif neighbor not in visited:
                    dfs(neighbor, start)
                elif neighbor in rec_stack:
                    # Ciclo detectado
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:]
                    if cycle not in cycles:
                        cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(node)
        
        # Tenta começar de cada nó
        for node in self.import_graph:
            if node not in visited:
                dfs(node, node)
        
        return cycles
    
    def analyze_circular_dependencies(self):
        """Analisa e detecta dependências circulares"""
        # Constrói grafo
        self.build_dependency_graph()
        
        # Encontra ciclos
        print("\n🔄 Procurando dependências circulares...")
        cycles = self.find_cycles_dfs()
        
        # Remove ciclos duplicados e triviais
        unique_cycles = []
        seen = set()
        
        for cycle in cycles:
            # Normaliza ciclo (menor elemento primeiro)
            if len(cycle) > 1:
                min_idx = cycle.index(min(cycle))
                normalized = tuple(cycle[min_idx:] + cycle[:min_idx])
                
                if normalized not in seen:
                    seen.add(normalized)
                    unique_cycles.append(list(normalized))
        
        self.circular_deps = unique_cycles
        
        return {
            'total_modules': len(self.dependencies),
            'modules_with_deps': len([m for m, deps in self.dependencies.items() if deps]),
            'total_dependencies': sum(len(deps) for deps in self.dependencies.values()),
            'circular_dependencies': len(self.circular_deps),
            'cycles': self.circular_deps
        }
    
    def generate_report(self, analysis: Dict):
        """Gera relatório de dependências circulares"""
        report = []
        report.append("# 🔄 ANÁLISE DE DEPENDÊNCIAS CIRCULARES - CLAUDE AI NOVO")
        report.append(f"\n**Data**: {Path(__file__).stat().st_mtime}")
        report.append("")
        
        # Estatísticas
        report.append("## 📊 ESTATÍSTICAS")
        report.append(f"- **Total de módulos**: {analysis['total_modules']}")
        report.append(f"- **Módulos com dependências**: {analysis['modules_with_deps']}")
        report.append(f"- **Total de dependências**: {analysis['total_dependencies']}")
        report.append(f"- **Dependências circulares**: {analysis['circular_dependencies']}")
        report.append("")
        
        # Ciclos encontrados
        if analysis['cycles']:
            report.append("## 🚨 DEPENDÊNCIAS CIRCULARES ENCONTRADAS\n")
            
            for i, cycle in enumerate(analysis['cycles'], 1):
                report.append(f"### Ciclo {i}")
                report.append("```")
                for j, module in enumerate(cycle):
                    next_module = cycle[(j + 1) % len(cycle)]
                    report.append(f"{module}")
                    report.append(f"  ↓ importa")
                report.append(f"{cycle[0]} (volta ao início)")
                report.append("```")
                
                # Análise do impacto
                report.append("\n**Módulos envolvidos**:")
                for module in cycle:
                    short_name = module.split('.')[-1]
                    report.append(f"- `{short_name}`")
                
                report.append("")
        else:
            report.append("## ✅ NENHUMA DEPENDÊNCIA CIRCULAR ENCONTRADA!")
            report.append("\nO sistema está livre de imports circulares.")
        
        # Módulos mais conectados
        report.append("\n## 📈 MÓDULOS MAIS CONECTADOS")
        connected = [(m, len(deps)) for m, deps in self.dependencies.items() if deps]
        connected.sort(key=lambda x: x[1], reverse=True)
        
        for module, count in connected[:10]:
            short_name = module.split('.')[-1]
            report.append(f"- **{short_name}**: {count} dependências")
        
        # Recomendações
        if analysis['cycles']:
            report.append("\n## 💡 RECOMENDAÇÕES")
            report.append("\n1. **Usar imports lazy** - Importar dentro de funções quando necessário")
            report.append("2. **Dependency Injection** - Passar dependências como parâmetros")
            report.append("3. **Interfaces/Protocolos** - Usar abstrações ao invés de implementações")
            report.append("4. **Reestruturar módulos** - Separar responsabilidades")
            report.append("5. **Event-driven** - Usar eventos ao invés de chamadas diretas")
        
        # Salva relatório
        report_path = self.base_dir / 'RELATORIO_DEPENDENCIAS_CIRCULARES.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        # Salva JSON
        json_path = self.base_dir / 'dependencias_circulares.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        return report_path, json_path

def main():
    print("🔄 Mapeador de Dependências Circulares")
    print("=" * 60)
    
    mapper = CircularDependencyMapper()
    
    # Analisa
    print("\n📊 Analisando dependências...")
    analysis = mapper.analyze_circular_dependencies()
    
    # Gera relatório
    print("\n📝 Gerando relatório...")
    report_path, json_path = mapper.generate_report(analysis)
    
    # Mostra resumo
    print(f"\n✅ Análise concluída!")
    print(f"\n📊 Resumo:")
    print(f"  - Módulos analisados: {analysis['total_modules']}")
    print(f"  - Dependências circulares: {analysis['circular_dependencies']}")
    
    if analysis['cycles']:
        print(f"\n🚨 ATENÇÃO: {len(analysis['cycles'])} ciclos encontrados!")
        for i, cycle in enumerate(analysis['cycles'][:3], 1):
            print(f"\n  Ciclo {i}: {' → '.join(c.split('.')[-1] for c in cycle[:3])}...")
    else:
        print("\n✅ Nenhuma dependência circular encontrada!")
    
    print(f"\n📄 Relatório: {report_path}")
    print(f"📄 JSON: {json_path}")

if __name__ == "__main__":
    main() 