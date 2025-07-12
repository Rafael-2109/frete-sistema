#!/usr/bin/env python3
"""
Filtrador de Imports Reais - Remove Falsos Positivos
Identifica apenas imports que são REALMENTE problemáticos
"""

import json
import os
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class ImportFilterer:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Padrões de falsos positivos
        self.false_positive_patterns = {
            # Imports opcionais/condicionais
            'optional_imports': [
                r'redis',
                r'numpy',
                r'pandas',
                r'torch',
                r'transformers',
                r'spacy',
                r'nltk',
                r'sklearn',
                r'matplotlib',
                r'plotly',
                r'seaborn',
                r'requests',
                r'aiohttp',
                r'asyncio',
                r'concurrent\.futures',
            ],
            
            # Imports de desenvolvimento
            'dev_imports': [
                r'pytest',
                r'unittest',
                r'mock',
                r'faker',
                r'factory',
                r'debug',
                r'ipdb',
                r'pdb',
                r'coverage',
                r'black',
                r'flake8',
                r'mypy',
                r'pylint',
            ],
            
            # Imports específicos do sistema antigo
            'old_system': [
                r'app\.claude_ai\.',
                r'app\.mcp\.',
                r'app\.intelligence\.',
                r'app\.multi_agent\.',
                r'app\.learning\.',
                r'app\.ai_',
            ],
            
            # Imports que são placeholders conhecidos
            'known_placeholders': [
                r'Mock',
                r'MagicMock',
                r'DummyClass',
                r'PlaceholderClass',
                r'FallbackClass',
                r'DefaultClass',
            ],
            
            # Imports de módulos externos opcionais
            'external_optional': [
                r'anthropic',
                r'openai',
                r'langchain',
                r'chromadb',
                r'pinecone',
                r'weaviate',
                r'qdrant',
                r'elasticsearch',
                r'faiss',
            ]
        }
        
        # Contextos que indicam falso positivo
        self.safe_contexts = [
            'try:',
            'except',
            'if ',
            'else:',
            'elif ',
            'def fallback',
            'def get_fallback',
            'def create_mock',
            '# Optional',
            '# Fallback',
            '# Development',
            '# Debug',
            '# Test',
            'IS_PRODUCTION',
            'DEBUG',
            'TESTING',
        ]
        
    def is_false_positive(self, import_info: Dict) -> Tuple[bool, str]:
        """Verifica se é um falso positivo e retorna o motivo"""
        
        # 1. Verifica se está em contexto seguro (try/except, if/else)
        context = import_info.get('context', '')
        for safe in self.safe_contexts:
            if safe.lower() in context.lower():
                return True, f"Em contexto seguro: {safe}"
        
        # 2. Verifica se é import opcional conhecido
        module = import_info.get('module', '')
        for pattern in self.false_positive_patterns['optional_imports']:
            if re.search(pattern, module, re.IGNORECASE):
                return True, f"Import opcional: {pattern}"
        
        # 3. Verifica se é import de desenvolvimento
        for pattern in self.false_positive_patterns['dev_imports']:
            if re.search(pattern, module, re.IGNORECASE):
                return True, f"Import de desenvolvimento: {pattern}"
        
        # 4. Verifica se é do sistema antigo
        for pattern in self.false_positive_patterns['old_system']:
            if re.search(pattern, module, re.IGNORECASE):
                return True, f"Sistema antigo: {pattern}"
        
        # 5. Verifica se é placeholder conhecido
        items = import_info.get('items', [])
        if items:
            for item in items:
                for pattern in self.false_positive_patterns['known_placeholders']:
                    if re.search(pattern, item, re.IGNORECASE):
                        return True, f"Placeholder conhecido: {pattern}"
        
        # 6. Verifica se é módulo externo opcional
        for pattern in self.false_positive_patterns['external_optional']:
            if re.search(pattern, module, re.IGNORECASE):
                return True, f"Módulo externo opcional: {pattern}"
        
        # 7. Verifica se tem fallback definido
        if 'fallback' in import_info:
            return True, "Tem fallback definido"
        
        # 8. Verifica se está em função de teste/debug
        function = import_info.get('function', '')
        if any(word in function.lower() for word in ['test', 'debug', 'mock', 'dummy', 'example']):
            return True, f"Em função de teste/debug: {function}"
        
        return False, ""
    
    def analyze_real_problems(self, imports_file: str = 'imports_profundos.json'):
        """Analisa apenas problemas reais, excluindo falsos positivos"""
        
        # Carrega dados da análise profunda
        with open(os.path.join(self.base_dir, imports_file), 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        real_problems = defaultdict(list)
        false_positives = defaultdict(list)
        stats = {
            'total_broken': 0,
            'real_problems': 0,
            'false_positives': 0,
            'by_category': defaultdict(int)
        }
        
        # Analisa os imports quebrados
        imports_quebrados = data.get('detalhes', {}).get('imports_quebrados', [])
        
        for import_info in imports_quebrados:
            file_path = import_info.get('arquivo', 'unknown')
            stats['total_broken'] += 1
            
            is_fp, reason = self.is_false_positive(import_info)
            
            if is_fp:
                stats['false_positives'] += 1
                stats['by_category'][reason] += 1
                false_positives[file_path].append({
                    **import_info,
                    'reason': reason
                })
            else:
                stats['real_problems'] += 1
                real_problems[file_path].append(import_info)
        
        return {
            'real_problems': dict(real_problems),
            'false_positives': dict(false_positives),
            'stats': stats
        }
    
    def generate_report(self, analysis: Dict):
        """Gera relatório apenas com problemas reais"""
        
        report = []
        report.append("# 🎯 IMPORTS REALMENTE PROBLEMÁTICOS - CLAUDE AI NOVO")
        report.append("## Análise Filtrada - Apenas Problemas Reais\n")
        
        stats = analysis['stats']
        report.append("## 📊 ESTATÍSTICAS")
        report.append(f"- **Total de imports quebrados**: {stats['total_broken']}")
        report.append(f"- **Problemas REAIS**: {stats['real_problems']} ({stats['real_problems']/max(stats['total_broken'],1)*100:.1f}%)")
        report.append(f"- **Falsos positivos**: {stats['false_positives']} ({stats['false_positives']/max(stats['total_broken'],1)*100:.1f}%)")
        report.append("")
        
        # Categorias de falsos positivos
        if stats['by_category']:
            report.append("### 📋 Categorias de Falsos Positivos")
            for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
                report.append(f"- {category}: {count}")
            report.append("")
        
        # Problemas reais por arquivo
        real_problems = analysis['real_problems']
        if real_problems:
            report.append("## 🚨 PROBLEMAS REAIS ENCONTRADOS\n")
            
            # Agrupa por tipo de problema
            by_module = defaultdict(list)
            for file_path, problems in real_problems.items():
                for problem in problems:
                    module = problem.get('module', 'Unknown')
                    by_module[module].append({
                        'file': file_path,
                        'line': problem.get('line', 0),
                        'type': problem.get('type', 'unknown'),
                        'items': problem.get('items', []),
                        'context': problem.get('context', '')
                    })
            
            # Lista problemas agrupados
            for module, occurrences in sorted(by_module.items()):
                report.append(f"### ❌ `{module}`")
                report.append(f"**Ocorrências**: {len(occurrences)}\n")
                
                # Primeiras 3 ocorrências como exemplo
                for i, occ in enumerate(occurrences[:3]):
                    report.append(f"**Arquivo**: `{occ['file']}`")
                    report.append(f"**Linha**: {occ['line']}")
                    if occ['items']:
                        report.append(f"**Items**: {', '.join(occ['items'])}")
                    report.append("")
                
                if len(occurrences) > 3:
                    report.append(f"... e mais {len(occurrences) - 3} ocorrências\n")
                
                report.append("---\n")
        else:
            report.append("## ✅ NENHUM PROBLEMA REAL ENCONTRADO!")
            report.append("Todos os imports quebrados são falsos positivos (opcionais, condicionais, etc.)")
        
        # Salva relatório
        report_path = os.path.join(self.base_dir, 'IMPORTS_REAIS_PROBLEMATICOS.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        # Salva JSON com problemas reais
        json_path = os.path.join(self.base_dir, 'imports_reais_problematicos.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        return report_path, json_path

def main():
    print("🔍 Filtrando Imports Reais (removendo falsos positivos)...")
    print("=" * 60)
    
    filterer = ImportFilterer()
    
    # Analisa e filtra
    print("\n📊 Analisando imports...")
    analysis = filterer.analyze_real_problems()
    
    # Gera relatório
    print("\n📝 Gerando relatório filtrado...")
    report_path, json_path = filterer.generate_report(analysis)
    
    # Mostra resumo
    stats = analysis['stats']
    print(f"\n✅ Análise concluída!")
    print(f"\n📊 Resumo:")
    print(f"  - Total analisado: {stats['total_broken']} imports")
    print(f"  - Problemas REAIS: {stats['real_problems']} ({stats['real_problems']/max(stats['total_broken'],1)*100:.1f}%)")
    print(f"  - Falsos positivos: {stats['false_positives']} ({stats['false_positives']/max(stats['total_broken'],1)*100:.1f}%)")
    
    print(f"\n📄 Relatório salvo em: {report_path}")
    print(f"📄 JSON salvo em: {json_path}")
    
    # Mostra top 5 problemas reais
    real_problems = analysis['real_problems']
    if real_problems:
        print("\n🚨 Top 5 arquivos com problemas REAIS:")
        sorted_files = sorted(real_problems.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        for file_path, problems in sorted_files:
            print(f"  - {file_path}: {len(problems)} problemas")

if __name__ == "__main__":
    main() 