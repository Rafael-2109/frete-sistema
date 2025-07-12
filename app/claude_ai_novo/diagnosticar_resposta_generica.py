#!/usr/bin/env python3
"""
Diagnóstico de Respostas Genéricas - Claude AI Novo
Identifica porque o sistema está dando respostas padrão em vez de dados reais
"""

import os
import sys
from pathlib import Path
import json
import ast
from typing import Dict, List, Any

class GenericResponseDiagnostic:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.issues = []
        self.findings = []
        
    def check_response_processor(self):
        """Verifica o ResponseProcessor que gera as respostas"""
        print("\n🔍 Analisando ResponseProcessor...")
        print("=" * 60)
        
        response_processor_path = self.base_dir / 'utils' / 'base_classes.py'
        
        if response_processor_path.exists():
            with open(response_processor_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verificar se está usando dados reais
            if 'dados reais' in content.lower() or 'real_data' in content.lower():
                print("✅ ResponseProcessor menciona dados reais")
                self.findings.append("ResponseProcessor tem referência a dados reais")
            else:
                print("⚠️  ResponseProcessor não menciona dados reais explicitamente")
                
            # Verificar se está chamando providers
            if 'provider' in content.lower():
                print("✅ ResponseProcessor usa providers")
                self.findings.append("ResponseProcessor integra com providers")
            else:
                print("❌ ResponseProcessor não parece usar providers")
                self.issues.append({
                    'type': 'missing_provider_integration',
                    'file': 'utils/base_classes.py',
                    'severity': 'high'
                })
                
            # Verificar templates de resposta
            if 'template' in content or 'Como assistente' in content:
                print("⚠️  ResponseProcessor pode estar usando templates fixos")
                self.issues.append({
                    'type': 'fixed_templates',
                    'file': 'utils/base_classes.py',
                    'severity': 'medium'
                })
                
    def check_data_flow(self):
        """Verifica o fluxo de dados do sistema"""
        print("\n\n🔄 Analisando Fluxo de Dados...")
        print("=" * 60)
        
        # Verificar DataProvider
        data_provider_path = self.base_dir / 'providers' / 'data_provider.py'
        
        if data_provider_path.exists():
            with open(data_provider_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verificar se está acessando banco
            if 'db.session' in content or 'query' in content:
                print("✅ DataProvider acessa banco de dados")
                self.findings.append("DataProvider tem queries ao banco")
            else:
                print("❌ DataProvider não parece acessar banco")
                self.issues.append({
                    'type': 'no_database_access',
                    'file': 'providers/data_provider.py',
                    'severity': 'critical'
                })
                
            # Verificar métodos específicos
            if 'obter_entregas' in content or 'get_deliveries' in content:
                print("✅ DataProvider tem método para entregas")
            else:
                print("⚠️  DataProvider não tem método específico para entregas")
                
    def check_orchestrator_flow(self):
        """Verifica como os orchestrators processam as queries"""
        print("\n\n🎭 Analisando Orchestrators...")
        print("=" * 60)
        
        orchestrator_path = self.base_dir / 'orchestrators' / 'orchestrator_manager.py'
        
        if orchestrator_path.exists():
            with open(orchestrator_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verificar se usa workflow de dados reais
            if 'data_provider' in content.lower() or 'real_data' in content.lower():
                print("✅ Orchestrator integra com dados reais")
            else:
                print("❌ Orchestrator não menciona integração com dados")
                self.issues.append({
                    'type': 'orchestrator_no_data_integration',
                    'file': 'orchestrators/orchestrator_manager.py',
                    'severity': 'high'
                })
                
    def check_analyzer_integration(self):
        """Verifica se analyzers estão processando corretamente"""
        print("\n\n🧠 Analisando Analyzers...")
        print("=" * 60)
        
        analyzer_path = self.base_dir / 'analyzers' / 'intention_analyzer.py'
        
        if analyzer_path.exists():
            with open(analyzer_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verificar detecção de intenção
            if 'entregas' in content.lower() or 'delivery' in content.lower():
                print("✅ Analyzer reconhece queries de entregas")
            else:
                print("⚠️  Analyzer pode não reconhecer queries de entregas")
                
    def check_config_loading(self):
        """Verifica se configurações estão sendo carregadas"""
        print("\n\n⚙️ Verificando Carregamento de Configurações...")
        print("=" * 60)
        
        # Verificar se semantic_mapping.json está sendo usado
        semantic_used = False
        
        for root, dirs, files in os.walk(self.base_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        if 'semantic_mapping.json' in content:
                            semantic_used = True
                            print(f"✅ semantic_mapping.json usado em: {file_path.relative_to(self.base_dir)}")
                            break
                    except:
                        pass
                        
        if not semantic_used:
            print("❌ semantic_mapping.json não está sendo carregado!")
            self.issues.append({
                'type': 'config_not_loaded',
                'file': 'config/semantic_mapping.json',
                'severity': 'high'
            })
            
    def analyze_response_generation(self):
        """Analisa como as respostas são geradas"""
        print("\n\n📝 Analisando Geração de Respostas...")
        print("=" * 60)
        
        # Buscar onde as respostas genéricas são criadas
        generic_patterns = [
            "Como assistente",
            "preciso informar",
            "não tenho acesso",
            "dados específicos",
            "seria necessário"
        ]
        
        files_with_generic = []
        
        for root, dirs, files in os.walk(self.base_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        for pattern in generic_patterns:
                            if pattern in content:
                                files_with_generic.append({
                                    'file': str(file_path.relative_to(self.base_dir)),
                                    'pattern': pattern
                                })
                                break
                    except:
                        pass
                        
        if files_with_generic:
            print(f"⚠️  Encontrados {len(files_with_generic)} arquivos com padrões genéricos:")
            for item in files_with_generic[:5]:  # Mostrar apenas os 5 primeiros
                print(f"   - {item['file']}: '{item['pattern']}'")
                
    def generate_report(self):
        """Gera relatório de diagnóstico"""
        report = {
            'summary': {
                'total_issues': len(self.issues),
                'critical_issues': len([i for i in self.issues if i['severity'] == 'critical']),
                'findings': len(self.findings)
            },
            'issues': self.issues,
            'findings': self.findings,
            'recommendations': []
        }
        
        # Gerar recomendações baseadas nos issues
        if any(i['type'] == 'no_database_access' for i in self.issues):
            report['recommendations'].append({
                'priority': 'HIGH',
                'action': 'Verificar integração do DataProvider com banco de dados',
                'description': 'O DataProvider não está acessando o banco para buscar dados reais'
            })
            
        if any(i['type'] == 'orchestrator_no_data_integration' for i in self.issues):
            report['recommendations'].append({
                'priority': 'HIGH',
                'action': 'Integrar Orchestrator com DataProvider',
                'description': 'O Orchestrator precisa chamar o DataProvider para obter dados reais'
            })
            
        if any(i['type'] == 'config_not_loaded' for i in self.issues):
            report['recommendations'].append({
                'priority': 'MEDIUM',
                'action': 'Carregar configurações semânticas',
                'description': 'O arquivo semantic_mapping.json não está sendo utilizado'
            })
            
        # Salvar relatório
        with open(self.base_dir / 'diagnostico_resposta_generica.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # Criar relatório Markdown
        self._create_markdown_report(report)
        
        return report
        
    def _create_markdown_report(self, report):
        """Cria relatório em Markdown"""
        md = ["# 🔍 DIAGNÓSTICO: Respostas Genéricas\n"]
        md.append(f"**Data**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Resumo
        md.append("## 📊 Resumo\n")
        s = report['summary']
        md.append(f"- **Issues Encontrados**: {s['total_issues']}")
        md.append(f"- **Issues Críticos**: {s['critical_issues']} 🚨")
        md.append(f"- **Descobertas Positivas**: {s['findings']}\n")
        
        # Issues críticos
        critical = [i for i in report['issues'] if i['severity'] == 'critical']
        if critical:
            md.append("## 🚨 ISSUES CRÍTICOS\n")
            for issue in critical:
                md.append(f"- **{issue['type']}**: {issue.get('file', 'N/A')}")
            md.append("")
            
        # Recomendações
        if report['recommendations']:
            md.append("## 💡 RECOMENDAÇÕES\n")
            for rec in sorted(report['recommendations'], key=lambda x: x['priority']):
                md.append(f"### {rec['priority']}: {rec['action']}")
                md.append(f"{rec['description']}\n")
                
        # Descobertas
        if report['findings']:
            md.append("## ✅ Descobertas Positivas\n")
            for finding in report['findings']:
                md.append(f"- {finding}")
                
        # Salvar
        with open(self.base_dir / 'DIAGNOSTICO_RESPOSTA_GENERICA.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(md))
            
    def run(self):
        """Executa diagnóstico completo"""
        print("🔍 Diagnosticando Respostas Genéricas...\n")
        
        self.check_response_processor()
        self.check_data_flow()
        self.check_orchestrator_flow()
        self.check_analyzer_integration()
        self.check_config_loading()
        self.analyze_response_generation()
        
        report = self.generate_report()
        
        print("\n\n📊 DIAGNÓSTICO FINAL:")
        print("=" * 60)
        s = report['summary']
        print(f"Issues: {s['total_issues']} (Críticos: {s['critical_issues']})")
        
        if s['critical_issues'] > 0:
            print("\n🚨 PROBLEMA IDENTIFICADO: O sistema não está integrando com dados reais!")
            print("\nPRINCIPAIS CAUSAS:")
            for issue in report['issues']:
                if issue['severity'] == 'critical':
                    print(f"- {issue['type']}")
        else:
            print("\n✅ Sistema parece estar configurado corretamente")
            
        print(f"\n📄 Relatório salvo em: DIAGNOSTICO_RESPOSTA_GENERICA.md")

if __name__ == "__main__":
    diagnostic = GenericResponseDiagnostic()
    diagnostic.run() 