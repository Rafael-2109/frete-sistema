#!/usr/bin/env python3
"""
Verificador de Dependências do Sistema Claude AI Novo
Analisa disponibilidade de dependências e qualidade dos fallbacks
"""

import importlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json
import subprocess

class DependencyChecker:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.project_root = self.base_dir.parent.parent
        
        # Dependências categorizadas
        self.dependencies = {
            'core': {
                'flask': 'Flask framework',
                'sqlalchemy': 'ORM para banco de dados',
                'anthropic': 'Claude API client',
                'flask_login': 'Autenticação Flask',
                'flask_wtf': 'Formulários Flask',
                'flask_sqlalchemy': 'SQLAlchemy para Flask'
            },
            'optional': {
                'redis': 'Cache distribuído',
                'numpy': 'Computação numérica',
                'pandas': 'Análise de dados',
                'openpyxl': 'Manipulação de Excel',
                'psutil': 'Informações do sistema',
                'fuzzywuzzy': 'Fuzzy string matching',
                'python-Levenshtein': 'Otimização para fuzzywuzzy'
            },
            'ai_ml': {
                'torch': 'PyTorch para ML',
                'transformers': 'Modelos de linguagem',
                'spacy': 'NLP avançado',
                'nltk': 'Natural Language Toolkit',
                'sklearn': 'Machine Learning'
            },
            'dev': {
                'pytest': 'Framework de testes',
                'black': 'Formatador de código',
                'pylint': 'Linter Python',
                'mypy': 'Type checking'
            }
        }
        
        self.results = {
            'installed': {},
            'missing': {},
            'fallbacks': {},
            'issues': []
        }
        
    def check_module(self, module_name: str) -> Tuple[bool, str]:
        """Verifica se um módulo está disponível"""
        try:
            importlib.import_module(module_name)
            return True, "OK"
        except ImportError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Error: {str(e)}"
            
    def check_pip_package(self, package_name: str) -> Dict[str, Any]:
        """Verifica informações de um pacote pip"""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', package_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                info = {}
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
                return {
                    'installed': True,
                    'version': info.get('Version', 'unknown'),
                    'location': info.get('Location', 'unknown')
                }
            else:
                return {'installed': False, 'error': result.stderr}
                
        except Exception as e:
            return {'installed': False, 'error': str(e)}
            
    def check_fallback_quality(self, module_name: str) -> Dict[str, Any]:
        """Analisa a qualidade do fallback para um módulo"""
        fallback_patterns = [
            # Pattern 1: try/except com fallback
            f"try:.*import.*{module_name}.*except.*:",
            # Pattern 2: verificação de disponibilidade
            f"{module_name}_available.*=.*",
            # Pattern 3: mock/stub
            f"Mock.*{module_name}|{module_name}.*Mock",
            # Pattern 4: if/else import
            f"if.*{module_name}.*else.*:"
        ]
        
        fallback_info = {
            'has_fallback': False,
            'fallback_type': None,
            'files_with_fallback': [],
            'quality_score': 0
        }
        
        # Buscar por fallbacks no código
        for root, dirs, files in os.walk(self.base_dir):
            # Pular diretórios desnecessários
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Verificar cada padrão
                        for pattern in fallback_patterns:
                            import re
                            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                                fallback_info['has_fallback'] = True
                                fallback_info['files_with_fallback'].append(
                                    str(file_path.relative_to(self.project_root))
                                )
                                
                                # Determinar tipo de fallback
                                if 'try' in pattern:
                                    fallback_info['fallback_type'] = 'try/except'
                                elif 'available' in pattern:
                                    fallback_info['fallback_type'] = 'availability_check'
                                elif 'Mock' in pattern:
                                    fallback_info['fallback_type'] = 'mock_object'
                                elif 'if' in pattern:
                                    fallback_info['fallback_type'] = 'conditional_import'
                                    
                                break
                                
                    except Exception:
                        pass
                        
        # Calcular score de qualidade
        if fallback_info['has_fallback']:
            fallback_info['quality_score'] = min(100, len(fallback_info['files_with_fallback']) * 20)
            
        return fallback_info
        
    def analyze_dependencies(self):
        """Analisa todas as dependências do sistema"""
        print("🔍 Analisando dependências do sistema Claude AI Novo...\n")
        
        for category, deps in self.dependencies.items():
            print(f"\n📦 {category.upper()} Dependencies:")
            print("=" * 60)
            
            for module, description in deps.items():
                # Verificar se está instalado
                is_available, error = self.check_module(module)
                pip_info = self.check_pip_package(module)
                
                if is_available:
                    self.results['installed'][module] = {
                        'category': category,
                        'description': description,
                        'version': pip_info.get('version', 'unknown'),
                        'import_ok': True
                    }
                    print(f"✅ {module:<20} v{pip_info.get('version', '?'):<10} - {description}")
                else:
                    # Verificar fallback
                    fallback = self.check_fallback_quality(module)
                    
                    self.results['missing'][module] = {
                        'category': category,
                        'description': description,
                        'error': error,
                        'has_fallback': fallback['has_fallback']
                    }
                    
                    if fallback['has_fallback']:
                        self.results['fallbacks'][module] = fallback
                        print(f"⚠️  {module:<20} {'MISSING':<10} - {description}")
                        print(f"    └─ Fallback: {fallback['fallback_type']} em {len(fallback['files_with_fallback'])} arquivo(s)")
                    else:
                        print(f"❌ {module:<20} {'MISSING':<10} - {description}")
                        print(f"    └─ SEM FALLBACK!")
                        self.results['issues'].append({
                            'type': 'missing_fallback',
                            'module': module,
                            'category': category,
                            'severity': 'high' if category == 'core' else 'medium'
                        })
                        
    def check_database_connection(self):
        """Verifica conexão com banco de dados"""
        print("\n\n🗄️ DATABASE Connection:")
        print("=" * 60)
        
        try:
            # Tentar importar e verificar configuração
            from app import db
            from flask import current_app
            
            # Verificar se estamos em contexto Flask
            try:
                db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')
                print(f"✅ Database URI configurada")
                print(f"   └─ Engine: {db_uri.split('://')[0] if '://' in db_uri else 'unknown'}")
            except:
                print("⚠️  Fora do contexto Flask - não é possível verificar configuração")
                
        except ImportError:
            print("❌ SQLAlchemy não disponível")
            self.results['issues'].append({
                'type': 'database_unavailable',
                'severity': 'critical'
            })
            
    def check_redis_connection(self):
        """Verifica conexão com Redis"""
        print("\n\n💾 REDIS Connection:")
        print("=" * 60)
        
        try:
            import redis
            
            # Tentar conectar
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            print("✅ Redis disponível e conectado")
            
        except ImportError:
            print("⚠️  Redis não instalado - usando fallback em memória")
            
            # Verificar se há fallback
            fallback = self.check_fallback_quality('redis')
            if fallback['has_fallback']:
                print(f"   └─ Fallback implementado em {len(fallback['files_with_fallback'])} arquivo(s)")
            else:
                print("   └─ ❌ SEM FALLBACK!")
                
        except Exception as e:
            print(f"⚠️  Redis instalado mas não conectado: {str(e)}")
            print("   └─ Sistema usará fallback em memória")
            
    def generate_report(self):
        """Gera relatório detalhado"""
        report = {
            'summary': {
                'total_dependencies': sum(len(deps) for deps in self.dependencies.values()),
                'installed': len(self.results['installed']),
                'missing': len(self.results['missing']),
                'with_fallback': len(self.results['fallbacks']),
                'critical_issues': len([i for i in self.results['issues'] if i.get('severity') == 'critical']),
                'warnings': len([i for i in self.results['issues'] if i.get('severity') != 'critical'])
            },
            'details': self.results
        }
        
        # Salvar JSON
        with open(self.base_dir / 'dependencias_sistema.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # Criar relatório Markdown
        self._create_markdown_report(report)
        
        return report
        
    def _create_markdown_report(self, report):
        """Cria relatório em Markdown"""
        md = ["# 📊 RELATÓRIO DE DEPENDÊNCIAS - Claude AI Novo\n"]
        md.append(f"**Data**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Resumo
        md.append("## 📈 Resumo Executivo\n")
        s = report['summary']
        md.append(f"- **Total de Dependências**: {s['total_dependencies']}")
        md.append(f"- **Instaladas**: {s['installed']} ✅")
        md.append(f"- **Faltando**: {s['missing']} ❌")
        md.append(f"- **Com Fallback**: {s['with_fallback']} ⚠️")
        md.append(f"- **Issues Críticos**: {s['critical_issues']} 🚨")
        md.append(f"- **Warnings**: {s['warnings']} ⚠️\n")
        
        # Dependências faltando sem fallback
        missing_no_fallback = [
            m for m, info in self.results['missing'].items() 
            if not info['has_fallback']
        ]
        
        if missing_no_fallback:
            md.append("## 🚨 AÇÃO NECESSÁRIA\n")
            md.append("### Dependências sem Fallback:\n")
            for module in missing_no_fallback:
                info = self.results['missing'][module]
                md.append(f"- **{module}** ({info['category']}): {info['description']}")
            md.append("")
            
        # Dependências com fallback
        if self.results['fallbacks']:
            md.append("## ⚠️ Dependências com Fallback\n")
            for module, fallback in self.results['fallbacks'].items():
                md.append(f"### {module}")
                md.append(f"- **Tipo**: {fallback['fallback_type']}")
                md.append(f"- **Qualidade**: {fallback['quality_score']}%")
                md.append(f"- **Arquivos**: {len(fallback['files_with_fallback'])}")
                md.append("")
                
        # Salvar relatório
        with open(self.base_dir / 'RELATORIO_DEPENDENCIAS.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(md))
            
    def run(self):
        """Executa análise completa"""
        self.analyze_dependencies()
        self.check_database_connection()
        self.check_redis_connection()
        
        report = self.generate_report()
        
        print("\n\n📊 RESUMO FINAL:")
        print("=" * 60)
        s = report['summary']
        print(f"Total: {s['total_dependencies']} | Instaladas: {s['installed']} | Faltando: {s['missing']}")
        print(f"Com Fallback: {s['with_fallback']} | Issues: {s['critical_issues'] + s['warnings']}")
        
        if s['critical_issues'] > 0:
            print("\n🚨 ATENÇÃO: Existem issues críticos que precisam ser resolvidos!")
        elif s['missing'] > s['with_fallback']:
            print("\n⚠️  AVISO: Algumas dependências não têm fallback adequado")
        else:
            print("\n✅ Sistema tem fallbacks para todas as dependências opcionais!")
            
        print(f"\n📄 Relatório salvo em: RELATORIO_DEPENDENCIAS.md")

if __name__ == "__main__":
    checker = DependencyChecker()
    checker.run() 