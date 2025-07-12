#!/usr/bin/env python3
"""
Analisador de Imports Prioritários
Agrupa e prioriza os imports problemáticos para correção eficiente
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple

class ImportPriorityAnalyzer:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Categorias de imports por prioridade
        self.categories = {
            'python_stdlib': {
                'priority': 1,
                'description': 'Biblioteca padrão Python',
                'modules': ['abc', 'argparse', 'dataclasses', 'datetime', 'json', 'os', 
                           'random', 'signal', 'statistics', 'subprocess', 'tempfile', 
                           'threading', 'time', 'traceback', 'uuid', 'weakref']
            },
            'internal_components': {
                'priority': 2,
                'description': 'Componentes internos do sistema',
                'patterns': ['_manager', '_scanner', '_loader', '_processor', '_analyzer',
                            '_validator', '_mapper', '_memory', '_provider', '_enricher']
            },
            'base_classes': {
                'priority': 3,
                'description': 'Classes base e utilitários',
                'patterns': ['base_', 'base', 'utils', 'types', 'config']
            },
            'domain_specific': {
                'priority': 4,
                'description': 'Componentes específicos de domínio',
                'patterns': ['embarques_', 'faturamento_', 'pedidos_', 'monitoramento_',
                            'transportadoras_', 'agendamentos_']
            },
            'external_integration': {
                'priority': 5,
                'description': 'Integrações externas',
                'patterns': ['claude', 'integration', 'api', 'web_']
            }
        }
    
    def categorize_import(self, module: str) -> Tuple[str, int]:
        """Categoriza um import e retorna categoria e prioridade"""
        
        # Verifica biblioteca padrão
        if module in self.categories['python_stdlib']['modules']:
            return 'python_stdlib', self.categories['python_stdlib']['priority']
        
        # Verifica padrões
        for category, info in self.categories.items():
            if 'patterns' in info:
                for pattern in info['patterns']:
                    if pattern in module.lower():
                        return category, info['priority']
        
        # Categoria padrão
        return 'other', 6
    
    def analyze_priorities(self, imports_file: str = 'imports_reais_problematicos.json'):
        """Analisa e prioriza os imports problemáticos"""
        
        # Carrega dados
        with open(os.path.join(self.base_dir, imports_file), 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Agrupa por categoria e arquivo
        by_category = defaultdict(lambda: defaultdict(list))
        by_file = defaultdict(lambda: defaultdict(int))
        module_occurrences = defaultdict(int)
        
        for file_path, problems in data['real_problems'].items():
            for problem in problems:
                module = problem.get('module', 'unknown')
                category, priority = self.categorize_import(module)
                
                by_category[category][module].append({
                    'file': file_path,
                    'line': problem.get('line', 0),
                    'context': problem.get('context', '')
                })
                
                by_file[file_path][category] += 1
                module_occurrences[module] += 1
        
        # Identifica arquivos críticos (muitos problemas)
        critical_files = []
        for file_path, categories in by_file.items():
            total = sum(categories.values())
            if total > 10:
                critical_files.append((file_path, total, categories))
        
        critical_files.sort(key=lambda x: x[1], reverse=True)
        
        # Identifica imports mais problemáticos
        top_modules = sorted(module_occurrences.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            'by_category': dict(by_category),
            'critical_files': critical_files,
            'top_modules': top_modules,
            'stats': data['stats']
        }
    
    def generate_action_plan(self, analysis: Dict):
        """Gera plano de ação prioritizado"""
        
        report = []
        report.append("# 🎯 PLANO DE AÇÃO - CORREÇÃO DE IMPORTS")
        report.append("## Análise Prioritizada para Correção Eficiente\n")
        
        # Estatísticas gerais
        stats = analysis['stats']
        report.append("## 📊 RESUMO EXECUTIVO")
        report.append(f"- **Total de problemas REAIS**: {stats['real_problems']}")
        report.append(f"- **Arquivos afetados**: {len(analysis['critical_files'])}")
        report.append("")
        
        # Top 10 módulos problemáticos
        report.append("## 🚨 TOP 10 IMPORTS MAIS PROBLEMÁTICOS")
        report.append("*(Foque nestes primeiro para máximo impacto)*\n")
        
        for module, count in analysis['top_modules'][:10]:
            category, _ = self.categorize_import(module)
            report.append(f"1. **`{module}`** - {count} ocorrências ({category})")
        report.append("")
        
        # Arquivos críticos
        report.append("## 📁 ARQUIVOS CRÍTICOS")
        report.append("*(Arquivos com mais de 10 problemas)*\n")
        
        for file_path, total, categories in analysis['critical_files'][:10]:
            report.append(f"### `{file_path}` ({total} problemas)")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                report.append(f"  - {cat}: {count}")
            report.append("")
        
        # Ações por categoria
        report.append("## 📋 AÇÕES POR CATEGORIA\n")
        
        for category, info in sorted(self.categories.items(), key=lambda x: x[1]['priority']):
            if category in analysis['by_category']:
                modules = analysis['by_category'][category]
                report.append(f"### {info['priority']}. {info['description'].upper()}")
                report.append(f"*{len(modules)} módulos afetados*\n")
                
                if category == 'python_stdlib':
                    report.append("**AÇÃO**: Verificar se estão instalados no ambiente Python")
                    report.append("```python")
                    report.append("# Estes são módulos padrão que deveriam estar disponíveis")
                    for module in list(modules.keys())[:5]:
                        report.append(f"import {module}")
                    report.append("```")
                
                elif category == 'internal_components':
                    report.append("**AÇÃO**: Verificar se arquivos existem e imports estão corretos")
                    report.append("```python")
                    report.append("# Exemplo de correções comuns:")
                    report.append("# from .analyzer_manager import AnalyzerManager")
                    report.append("# from ..utils.base_classes import BaseComponent")
                    report.append("```")
                
                elif category == 'base_classes':
                    report.append("**AÇÃO**: Criar/verificar classes base em utils/")
                    
                elif category == 'external_integration':
                    report.append("**AÇÃO**: Verificar configuração de integrações externas")
                
                # Lista alguns exemplos
                examples = list(modules.items())[:3]
                for module, occurrences in examples:
                    report.append(f"\n- `{module}` ({len(occurrences)} ocorrências)")
                
                if len(modules) > 3:
                    report.append(f"- ... e mais {len(modules) - 3} módulos")
                
                report.append("")
        
        # Correções sugeridas
        report.append("## 🔧 CORREÇÕES SUGERIDAS\n")
        
        report.append("### 1. IMPORTS DA BIBLIOTECA PADRÃO")
        report.append("```python")
        report.append("# Adicione no início dos arquivos afetados:")
        stdlib_modules = [m for m, _ in analysis['top_modules'] 
                         if m in self.categories['python_stdlib']['modules']][:5]
        for module in stdlib_modules:
            report.append(f"import {module}")
        report.append("```\n")
        
        report.append("### 2. PADRÃO DE IMPORTS INTERNOS")
        report.append("```python")
        report.append("# Use imports relativos para componentes internos:")
        report.append("from .manager import ComponentManager")
        report.append("from ..utils.base_classes import BaseClass")
        report.append("from ...config import system_config")
        report.append("```\n")
        
        report.append("### 3. VERIFICAÇÃO RÁPIDA")
        report.append("```bash")
        report.append("# Execute para verificar correções:")
        report.append("python -m app.claude_ai_novo.verificar_imports_quebrados")
        report.append("```")
        
        # Salva relatório
        report_path = os.path.join(self.base_dir, 'PLANO_ACAO_IMPORTS.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        return report_path

def main():
    print("📊 Analisando prioridades de correção de imports...")
    print("=" * 60)
    
    analyzer = ImportPriorityAnalyzer()
    
    # Analisa
    print("\n🔍 Analisando imports problemáticos...")
    analysis = analyzer.analyze_priorities()
    
    # Gera plano
    print("\n📝 Gerando plano de ação...")
    report_path = analyzer.generate_action_plan(analysis)
    
    # Mostra resumo
    print(f"\n✅ Análise concluída!")
    print(f"\n📊 Resumo:")
    print(f"  - Problemas reais: {analysis['stats']['real_problems']}")
    print(f"  - Arquivos críticos: {len(analysis['critical_files'])}")
    print(f"  - Top módulo: {analysis['top_modules'][0][0]} ({analysis['top_modules'][0][1]} ocorrências)")
    
    print(f"\n📄 Plano de ação salvo em: {report_path}")
    
    # Mostra ações imediatas
    print("\n🚀 AÇÕES IMEDIATAS:")
    print("1. Corrija os imports da biblioteca padrão (abc, dataclasses, etc.)")
    print("2. Verifique os arquivos __init__.py com muitos problemas")
    print("3. Use a ferramenta corrigir_imports_automatico.py para correções conhecidas")

if __name__ == "__main__":
    main() 