#!/usr/bin/env python3
"""
Análise Completa de Integração de Módulos - Claude AI Novo
==========================================================

Mapeia como todos os módulos se integram, detecta:
- Módulos órfãos (não usados)
- Redundâncias ocultas
- Dependências circulares
- Pontos de integração críticos
- Eficiência da arquitetura
"""

import os
import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict, Counter
import json

# Adicionar paths necessários
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))

class ModuleIntegrationAnalyzer:
    """Analisador de integração de módulos"""
    
    def __init__(self):
        self.claude_ai_path = Path(__file__).parent
        self.modules_info = {}
        self.imports_map = defaultdict(set)
        self.usage_map = defaultdict(int)
        self.circular_deps = []
        self.orphan_modules = set()
        self.redundant_modules = {}
        self.integration_points = {}
        
    def analyze_all_modules(self) -> Dict[str, Any]:
        """Análise completa de todos os módulos"""
        print("🔍 ANÁLISE COMPLETA DE INTEGRAÇÃO DE MÓDULOS")
        print("=" * 80)
        
        # 1. Escanear todos os módulos
        self._scan_all_modules()
        
        # 2. Analisar imports e dependências
        self._analyze_imports()
        
        # 3. Detectar dependências circulares
        self._detect_circular_dependencies()
        
        # 4. Identificar módulos órfãos
        self._identify_orphan_modules()
        
        # 5. Detectar redundâncias
        self._detect_redundancies()
        
        # 6. Analisar pontos de integração
        self._analyze_integration_points()
        
        # 7. Calcular métricas de arquitetura
        metrics = self._calculate_architecture_metrics()
        
        # 8. Gerar relatório completo
        return self._generate_comprehensive_report(metrics)
    
    def _scan_all_modules(self):
        """Escaneia todos os módulos Python"""
        print("📁 Escaneando todos os módulos...")
        
        for root, dirs, files in os.walk(self.claude_ai_path):
            # Pular __pycache__ e outras pastas desnecessárias
            dirs[:] = [d for d in dirs if not d.startswith('__pycache__') and not d.startswith('.')]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.claude_ai_path)
                    
                    try:
                        module_info = self._analyze_module_file(file_path, relative_path)
                        self.modules_info[str(relative_path)] = module_info
                    except Exception as e:
                        print(f"⚠️ Erro ao analisar {relative_path}: {e}")
        
        print(f"✅ {len(self.modules_info)} módulos escaneados")
    
    def _analyze_module_file(self, file_path: Path, relative_path: Path) -> Dict[str, Any]:
        """Analisa um arquivo de módulo específico"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Analisar AST para imports
        try:
            tree = ast.parse(content)
        except SyntaxError:
            tree = None
        
        # Informações básicas
        info = {
            'path': str(relative_path),
            'size_lines': len(content.split('\n')),
            'size_bytes': len(content.encode('utf-8')),
            'imports': self._extract_imports(tree) if tree else [],
            'classes': self._extract_classes(tree) if tree else [],
            'functions': self._extract_functions(tree) if tree else [],
            'has_main': '__main__' in content,
            'has_init': relative_path.name == '__init__.py',
            'category': self._determine_category(relative_path),
            'docstring': self._extract_docstring(tree) if tree else None,
            'complexity_score': self._calculate_complexity(content),
            'integration_patterns': self._detect_integration_patterns(content)
        }
        
        return info
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, str]]:
        """Extrai todos os imports do AST"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append({
                        'type': 'from_import',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'level': node.level
                    })
        
        return imports
    
    def _extract_classes(self, tree: ast.AST) -> List[str]:
        """Extrai nomes de classes"""
        return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    
    def _extract_functions(self, tree: ast.AST) -> List[str]:
        """Extrai nomes de funções"""
        return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    
    def _extract_docstring(self, tree: ast.AST) -> str:
        """Extrai docstring do módulo"""
        if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Str):
            return tree.body[0].value.s
        return None
    
    def _determine_category(self, path: Path) -> str:
        """Determina categoria do módulo baseado no path"""
        parts = path.parts
        if len(parts) > 1:
            return parts[0]  # Primeira pasta
        return 'root'
    
    def _calculate_complexity(self, content: str) -> int:
        """Calcula score de complexidade simples"""
        lines = content.split('\n')
        complexity = 0
        
        # Contar diferentes tipos de construtos
        for line in lines:
            line = line.strip()
            if line.startswith('def '):
                complexity += 2
            elif line.startswith('class '):
                complexity += 3
            elif 'if ' in line or 'elif ' in line:
                complexity += 1
            elif 'for ' in line or 'while ' in line:
                complexity += 1
            elif 'try:' in line or 'except' in line:
                complexity += 1
        
        return complexity
    
    def _detect_integration_patterns(self, content: str) -> List[str]:
        """Detecta padrões de integração no código"""
        patterns = []
        
        # Padrões comuns
        if 'get_' in content and '_manager' in content:
            patterns.append('manager_pattern')
        if 'register_' in content:
            patterns.append('registry_pattern')
        if 'singleton' in content.lower() or '_instance' in content:
            patterns.append('singleton_pattern')
        if 'coordinator' in content.lower():
            patterns.append('coordinator_pattern')
        if 'from typing import' in content and ('Protocol' in content or 'ABC' in content):
            patterns.append('interface_pattern')
        if '__all__' in content:
            patterns.append('explicit_exports')
        if 'fallback' in content.lower():
            patterns.append('fallback_pattern')
        if 'logger' in content and 'logging' in content:
            patterns.append('logging_pattern')
        
        return patterns
    
    def _analyze_imports(self):
        """Analisa todas as dependências de import"""
        print("🔗 Analisando dependências...")
        
        for module_path, module_info in self.modules_info.items():
            for import_info in module_info['imports']:
                imported_module = import_info['module']
                
                # Mapear import interno do claude_ai_novo
                if self._is_internal_import(imported_module):
                    self.imports_map[module_path].add(imported_module)
                    self.usage_map[imported_module] += 1
    
    def _is_internal_import(self, module_name: str) -> bool:
        """Verifica se é import interno do claude_ai_novo"""
        return (
            module_name.startswith('app.claude_ai_novo') or
            module_name.startswith('.') or
            any(module_name in str(path) for path in self.modules_info.keys())
        )
    
    def _detect_circular_dependencies(self):
        """Detecta dependências circulares"""
        print("🔄 Detectando dependências circulares...")
        
        def dfs(node, path, visited):
            if node in path:
                # Encontrou ciclo
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                self.circular_deps.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for dependency in self.imports_map.get(node, []):
                dfs(dependency, path.copy(), visited)
        
        visited = set()
        for module in self.modules_info.keys():
            if module not in visited:
                dfs(module, [], visited)
        
        # Remover duplicatas
        unique_cycles = []
        for cycle in self.circular_deps:
            cycle_set = set(cycle)
            if not any(cycle_set.issubset(set(existing)) for existing in unique_cycles):
                unique_cycles.append(cycle)
        
        self.circular_deps = unique_cycles
    
    def _identify_orphan_modules(self):
        """Identifica módulos órfãos (não importados por ninguém)"""
        print("👻 Identificando módulos órfãos...")
        
        all_modules = set(self.modules_info.keys())
        imported_modules = set()
        
        # Coletar todos os módulos importados
        for imports in self.imports_map.values():
            imported_modules.update(imports)
        
        # Módulos órfãos = não importados + não são __init__ + não são main
        for module_path in all_modules:
            module_info = self.modules_info[module_path]
            
            is_imported = any(module_path in str(imp) for imp in imported_modules)
            is_init = module_info['has_init']
            is_main = module_info['has_main']
            is_test = 'test' in module_path.lower()
            
            if not is_imported and not is_init and not is_main and not is_test:
                self.orphan_modules.add(module_path)
    
    def _detect_redundancies(self):
        """Detecta módulos redundantes"""
        print("🔍 Detectando redundâncias...")
        
        # Agrupar por funcionalidade similar
        functionality_groups = defaultdict(list)
        
        for module_path, module_info in self.modules_info.items():
            # Baseado no nome do arquivo
            base_name = Path(module_path).stem
            
            # Padrões de redundância
            key_words = []
            if 'manager' in base_name:
                key_words.append('manager')
            if 'loader' in base_name:
                key_words.append('loader')
            if 'processor' in base_name:
                key_words.append('processor')
            if 'analyzer' in base_name:
                key_words.append('analyzer')
            if 'coordinator' in base_name:
                key_words.append('coordinator')
            
            for word in key_words:
                functionality_groups[f"{module_info['category']}_{word}"].append(module_path)
        
        # Identificar grupos com múltiplos módulos
        for group_name, modules in functionality_groups.items():
            if len(modules) > 1:
                # Analisar se são realmente redundantes
                redundancy_score = self._calculate_redundancy_score(modules)
                if redundancy_score > 0.7:  # 70% de similaridade
                    self.redundant_modules[group_name] = {
                        'modules': modules,
                        'redundancy_score': redundancy_score,
                        'recommendation': self._suggest_redundancy_resolution(modules)
                    }
    
    def _calculate_redundancy_score(self, modules: List[str]) -> float:
        """Calcula score de redundância entre módulos"""
        if len(modules) < 2:
            return 0.0
        
        total_similarity = 0
        pairs = 0
        
        for i in range(len(modules)):
            for j in range(i + 1, len(modules)):
                similarity = self._calculate_module_similarity(modules[i], modules[j])
                total_similarity += similarity
                pairs += 1
        
        return total_similarity / pairs if pairs > 0 else 0.0
    
    def _calculate_module_similarity(self, module1: str, module2: str) -> float:
        """Calcula similaridade entre dois módulos"""
        info1 = self.modules_info[module1]
        info2 = self.modules_info[module2]
        
        similarity_factors = []
        
        # Similaridade de classes
        classes1 = set(info1['classes'])
        classes2 = set(info2['classes'])
        if classes1 or classes2:
            class_similarity = len(classes1 & classes2) / len(classes1 | classes2)
            similarity_factors.append(class_similarity)
        
        # Similaridade de funções
        funcs1 = set(info1['functions'])
        funcs2 = set(info2['functions'])
        if funcs1 or funcs2:
            func_similarity = len(funcs1 & funcs2) / len(funcs1 | funcs2)
            similarity_factors.append(func_similarity)
        
        # Similaridade de imports
        imports1 = set(imp['module'] for imp in info1['imports'])
        imports2 = set(imp['module'] for imp in info2['imports'])
        if imports1 or imports2:
            import_similarity = len(imports1 & imports2) / len(imports1 | imports2)
            similarity_factors.append(import_similarity)
        
        # Similaridade de padrões
        patterns1 = set(info1['integration_patterns'])
        patterns2 = set(info2['integration_patterns'])
        if patterns1 or patterns2:
            pattern_similarity = len(patterns1 & patterns2) / len(patterns1 | patterns2)
            similarity_factors.append(pattern_similarity)
        
        return sum(similarity_factors) / len(similarity_factors) if similarity_factors else 0.0
    
    def _suggest_redundancy_resolution(self, modules: List[str]) -> str:
        """Sugere como resolver redundância"""
        if len(modules) == 2:
            # Comparar complexidade e uso
            info1 = self.modules_info[modules[0]]
            info2 = self.modules_info[modules[1]]
            
            if info1['complexity_score'] > info2['complexity_score']:
                return f"Manter {modules[0]}, avaliar remoção de {modules[1]}"
            else:
                return f"Manter {modules[1]}, avaliar remoção de {modules[0]}"
        else:
            return f"Consolidar {len(modules)} módulos em um único módulo principal"
    
    def _analyze_integration_points(self):
        """Analisa pontos críticos de integração"""
        print("🔗 Analisando pontos de integração...")
        
        # Módulos mais importados (hubs)
        import_counts = Counter(self.usage_map)
        top_imported = import_counts.most_common(10)
        
        # Módulos que mais importam (dependents)
        dependent_counts = Counter()
        for module, imports in self.imports_map.items():
            dependent_counts[module] = len(imports)
        top_dependents = dependent_counts.most_common(10)
        
        # Modules managers/coordinators
        managers = []
        for module_path, module_info in self.modules_info.items():
            base_name = Path(module_path).stem.lower()
            if 'manager' in base_name or 'coordinator' in base_name:
                managers.append(module_path)
        
        self.integration_points = {
            'top_imported': top_imported,
            'top_dependents': top_dependents,
            'managers': managers,
            'critical_modules': self._identify_critical_modules()
        }
    
    def _identify_critical_modules(self) -> List[str]:
        """Identifica módulos críticos para o sistema"""
        critical = []
        
        for module_path, module_info in self.modules_info.items():
            # Critérios de criticidade
            is_manager = 'manager' in Path(module_path).stem.lower()
            is_coordinator = 'coordinator' in Path(module_path).stem.lower()
            is_init = module_info['has_init']
            has_many_classes = len(module_info['classes']) > 3
            has_many_functions = len(module_info['functions']) > 5
            is_highly_imported = self.usage_map.get(module_path, 0) > 2
            
            if any([is_manager, is_coordinator, is_init, has_many_classes, has_many_functions, is_highly_imported]):
                critical.append(module_path)
        
        return critical
    
    def _calculate_architecture_metrics(self) -> Dict[str, Any]:
        """Calcula métricas da arquitetura"""
        total_modules = len(self.modules_info)
        total_lines = sum(info['size_lines'] for info in self.modules_info.values())
        
        # Distribuição por categoria
        category_distribution = Counter()
        for module_info in self.modules_info.values():
            category_distribution[module_info['category']] += 1
        
        # Métricas de complexidade
        complexity_scores = [info['complexity_score'] for info in self.modules_info.values()]
        avg_complexity = sum(complexity_scores) / len(complexity_scores)
        
        # Métricas de integração
        total_imports = sum(len(imports) for imports in self.imports_map.values())
        avg_imports_per_module = total_imports / total_modules
        
        return {
            'total_modules': total_modules,
            'total_lines': total_lines,
            'average_lines_per_module': total_lines / total_modules,
            'category_distribution': dict(category_distribution),
            'average_complexity': avg_complexity,
            'total_imports': total_imports,
            'average_imports_per_module': avg_imports_per_module,
            'circular_dependencies_count': len(self.circular_deps),
            'orphan_modules_count': len(self.orphan_modules),
            'redundant_groups_count': len(self.redundant_modules),
            'integration_health_score': self._calculate_integration_health()
        }
    
    def _calculate_integration_health(self) -> float:
        """Calcula score de saúde da integração (0-1)"""
        total_modules = len(self.modules_info)
        
        # Penalidades
        circular_penalty = len(self.circular_deps) * 0.1
        orphan_penalty = len(self.orphan_modules) * 0.05
        redundancy_penalty = len(self.redundant_modules) * 0.1
        
        # Score base
        base_score = 1.0
        
        # Aplicar penalidades
        health_score = base_score - circular_penalty - orphan_penalty - redundancy_penalty
        
        return max(0.0, min(1.0, health_score))
    
    def _generate_comprehensive_report(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Gera relatório completo"""
        print("\n" + "=" * 80)
        print("📊 RELATÓRIO COMPLETO DE INTEGRAÇÃO")
        print("=" * 80)
        
        # Estatísticas gerais
        print(f"\n📈 ESTATÍSTICAS GERAIS:")
        print(f"   • Total de Módulos: {metrics['total_modules']}")
        print(f"   • Total de Linhas: {metrics['total_lines']:,}")
        print(f"   • Média Linhas/Módulo: {metrics['average_lines_per_module']:.1f}")
        print(f"   • Complexidade Média: {metrics['average_complexity']:.1f}")
        print(f"   • Imports Totais: {metrics['total_imports']}")
        print(f"   • Média Imports/Módulo: {metrics['average_imports_per_module']:.1f}")
        
        # Distribuição por categoria
        print(f"\n📁 DISTRIBUIÇÃO POR CATEGORIA:")
        for category, count in sorted(metrics['category_distribution'].items()):
            percentage = (count / metrics['total_modules']) * 100
            print(f"   • {category}: {count} módulos ({percentage:.1f}%)")
        
        # Problemas detectados
        print(f"\n🚨 PROBLEMAS DETECTADOS:")
        print(f"   • Dependências Circulares: {metrics['circular_dependencies_count']}")
        print(f"   • Módulos Órfãos: {metrics['orphan_modules_count']}")
        print(f"   • Grupos Redundantes: {metrics['redundant_groups_count']}")
        
        # Score de saúde
        health_score = metrics['integration_health_score']
        health_emoji = "🟢" if health_score > 0.8 else "🟡" if health_score > 0.6 else "🔴"
        print(f"\n{health_emoji} SCORE DE SAÚDE DA INTEGRAÇÃO: {health_score:.2f}")
        
        # Detalhes dos problemas
        if self.circular_deps:
            print(f"\n🔄 DEPENDÊNCIAS CIRCULARES DETECTADAS:")
            for i, cycle in enumerate(self.circular_deps, 1):
                print(f"   {i}. {' → '.join(cycle)}")
        
        if self.orphan_modules:
            print(f"\n👻 MÓDULOS ÓRFÃOS (NÃO USADOS):")
            for module in sorted(self.orphan_modules):
                print(f"   • {module}")
        
        if self.redundant_modules:
            print(f"\n🔍 GRUPOS REDUNDANTES:")
            for group, info in self.redundant_modules.items():
                print(f"   • {group} (score: {info['redundancy_score']:.2f}):")
                for module in info['modules']:
                    print(f"     - {module}")
                print(f"     → {info['recommendation']}")
        
        # Pontos de integração críticos
        print(f"\n🔗 PONTOS DE INTEGRAÇÃO CRÍTICOS:")
        print(f"   • Módulos Mais Importados:")
        for module, count in self.integration_points['top_imported'][:5]:
            print(f"     - {module}: {count} imports")
        
        print(f"   • Módulos Mais Dependentes:")
        for module, count in self.integration_points['top_dependents'][:5]:
            print(f"     - {module}: {count} dependências")
        
        # Recomendações
        print(f"\n💡 RECOMENDAÇÕES:")
        recommendations = self._generate_recommendations(metrics)
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        return {
            'metrics': metrics,
            'circular_dependencies': self.circular_deps,
            'orphan_modules': list(self.orphan_modules),
            'redundant_modules': self.redundant_modules,
            'integration_points': self.integration_points,
            'recommendations': recommendations,
            'detailed_modules': self.modules_info
        }
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        # Baseado no score de saúde
        health_score = metrics['integration_health_score']
        
        if health_score < 0.6:
            recommendations.append("🚨 CRÍTICO: Reestruturação arquitetural necessária")
        
        if self.circular_deps:
            recommendations.append(f"🔄 Resolver {len(self.circular_deps)} dependência(s) circular(es)")
        
        if len(self.orphan_modules) > 5:
            recommendations.append(f"🧹 Limpar {len(self.orphan_modules)} módulo(s) órfão(s)")
        
        if self.redundant_modules:
            recommendations.append(f"🔧 Consolidar {len(self.redundant_modules)} grupo(s) redundante(s)")
        
        if metrics['average_complexity'] > 20:
            recommendations.append("📉 Reduzir complexidade média dos módulos")
        
        if metrics['average_imports_per_module'] > 10:
            recommendations.append("🔗 Simplificar dependências entre módulos")
        
        # Recomendações específicas de arquitetura
        if metrics['total_modules'] > 50:
            recommendations.append("📦 Considerar agrupamento em sub-pacotes")
        
        recommendations.append("📚 Documentar arquitetura e padrões de integração")
        recommendations.append("🧪 Implementar testes de integração automatizados")
        
        return recommendations


def main():
    """Executa análise completa"""
    analyzer = ModuleIntegrationAnalyzer()
    report = analyzer.analyze_all_modules()
    
    # Salvar relatório detalhado
    report_file = Path(__file__).parent / "RELATORIO_INTEGRACAO_COMPLETO.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Relatório detalhado salvo em: {report_file}")
    print("\n" + "=" * 80)
    print("ANÁLISE CONCLUÍDA")
    print("=" * 80)
    
    return report


if __name__ == "__main__":
    main() 