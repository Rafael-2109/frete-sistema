#!/usr/bin/env python3
"""
Verificador de Configuração e Inicialização - Claude AI Novo
Analisa ordem de inicialização, configurações e variáveis de ambiente
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import json
import importlib
import traceback

class ConfigurationChecker:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.project_root = self.base_dir.parent.parent
        
        self.issues = []
        self.warnings = []
        self.config_status = {}
        
    def check_environment_variables(self) -> Dict[str, Any]:
        """Verifica variáveis de ambiente necessárias"""
        print("\n🔍 Verificando Variáveis de Ambiente...")
        print("=" * 60)
        
        required_vars = {
            'ANTHROPIC_API_KEY': {
                'description': 'Chave API do Claude',
                'critical': True,
                'fallback': None
            },
            'DATABASE_URL': {
                'description': 'URL de conexão com banco de dados',
                'critical': True,
                'fallback': 'sqlite:///instance/sistema_fretes.db'
            },
            'SECRET_KEY': {
                'description': 'Chave secreta do Flask',
                'critical': True,
                'fallback': 'dev-secret-key'
            },
            'REDIS_URL': {
                'description': 'URL do Redis',
                'critical': False,
                'fallback': 'redis://localhost:6379'
            },
            'FLASK_ENV': {
                'description': 'Ambiente Flask',
                'critical': False,
                'fallback': 'development'
            }
        }
        
        env_status = {}
        
        for var_name, config in required_vars.items():
            value = os.environ.get(var_name)
            
            if value:
                # Mascarar valores sensíveis
                if 'KEY' in var_name or 'SECRET' in var_name:
                    masked_value = value[:4] + '***' + value[-4:] if len(value) > 8 else '***'
                else:
                    masked_value = value
                    
                env_status[var_name] = {
                    'status': 'OK',
                    'value': masked_value,
                    'using_fallback': False
                }
                print(f"✅ {var_name}: {masked_value}")
            else:
                if config['critical']:
                    self.issues.append({
                        'type': 'missing_env_var',
                        'var': var_name,
                        'description': config['description']
                    })
                    print(f"❌ {var_name}: NÃO CONFIGURADA (CRÍTICO)")
                else:
                    print(f"⚠️  {var_name}: Não configurada (usando fallback)")
                    
                env_status[var_name] = {
                    'status': 'MISSING',
                    'fallback': config['fallback'],
                    'using_fallback': True
                }
                
        return env_status
        
    def check_config_files(self) -> Dict[str, Any]:
        """Verifica arquivos de configuração"""
        print("\n\n📄 Verificando Arquivos de Configuração...")
        print("=" * 60)
        
        config_files = {
            'config/__init__.py': 'Configuração principal',
            'config/basic_config.py': 'Configuração básica',
            'config/advanced_config.py': 'Configuração avançada',
            'config/config_paths.json': 'Paths de configuração',
            'config/semantic_mapping.json': 'Mapeamento semântico'
        }
        
        file_status = {}
        
        for file_path, description in config_files.items():
            full_path = self.base_dir / file_path
            
            if full_path.exists():
                # Verificar se é importável (para .py)
                if file_path.endswith('.py'):
                    module_path = file_path.replace('/', '.').replace('.py', '')
                    try:
                        module = importlib.import_module(f'app.claude_ai_novo.{module_path}')
                        file_status[file_path] = {
                            'exists': True,
                            'importable': True,
                            'size': full_path.stat().st_size
                        }
                        print(f"✅ {file_path}: OK ({full_path.stat().st_size} bytes)")
                    except Exception as e:
                        file_status[file_path] = {
                            'exists': True,
                            'importable': False,
                            'error': str(e)
                        }
                        print(f"⚠️  {file_path}: Existe mas não importável - {str(e)}")
                        self.warnings.append({
                            'type': 'config_import_error',
                            'file': file_path,
                            'error': str(e)
                        })
                else:
                    # Arquivo JSON
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            json.load(f)
                        file_status[file_path] = {
                            'exists': True,
                            'valid_json': True,
                            'size': full_path.stat().st_size
                        }
                        print(f"✅ {file_path}: JSON válido ({full_path.stat().st_size} bytes)")
                    except json.JSONDecodeError as e:
                        file_status[file_path] = {
                            'exists': True,
                            'valid_json': False,
                            'error': str(e)
                        }
                        print(f"❌ {file_path}: JSON inválido - {str(e)}")
                        self.issues.append({
                            'type': 'invalid_json',
                            'file': file_path,
                            'error': str(e)
                        })
            else:
                file_status[file_path] = {'exists': False}
                print(f"❌ {file_path}: NÃO ENCONTRADO")
                self.issues.append({
                    'type': 'missing_config_file',
                    'file': file_path,
                    'description': description
                })
                
        return file_status
        
    def check_initialization_order(self) -> Dict[str, Any]:
        """Verifica ordem de inicialização"""
        print("\n\n🔄 Verificando Ordem de Inicialização...")
        print("=" * 60)
        
        initialization_steps = []
        
        # 1. Verificar __init__.py principal
        try:
            # Simular importação para verificar ordem
            init_file = self.base_dir / '__init__.py'
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Analisar ordem de imports
            import_lines = []
            for i, line in enumerate(content.split('\n')):
                if line.strip().startswith('from ') or line.strip().startswith('import '):
                    import_lines.append((i + 1, line.strip()))
                    
            initialization_steps.append({
                'step': '__init__.py imports',
                'status': 'OK',
                'imports_count': len(import_lines)
            })
            print(f"✅ __init__.py: {len(import_lines)} imports")
            
            # Verificar se há imports circulares potenciais
            if 'from app.claude_ai_novo' in content:
                circular_count = content.count('from app.claude_ai_novo')
                if circular_count > 5:
                    self.warnings.append({
                        'type': 'potential_circular_imports',
                        'count': circular_count
                    })
                    print(f"⚠️  Potenciais imports circulares: {circular_count}")
                    
        except Exception as e:
            initialization_steps.append({
                'step': '__init__.py analysis',
                'status': 'ERROR',
                'error': str(e)
            })
            print(f"❌ Erro ao analisar __init__.py: {e}")
            
        # 2. Verificar função get_claude_ai_instance
        try:
            from app.claude_ai_novo import get_claude_ai_instance
            
            # Tentar criar instância (sem realmente executar)
            initialization_steps.append({
                'step': 'get_claude_ai_instance',
                'status': 'AVAILABLE',
                'callable': callable(get_claude_ai_instance)
            })
            print("✅ get_claude_ai_instance: Disponível")
            
        except ImportError as e:
            initialization_steps.append({
                'step': 'get_claude_ai_instance',
                'status': 'MISSING',
                'error': str(e)
            })
            print(f"❌ get_claude_ai_instance: Não disponível - {e}")
            self.issues.append({
                'type': 'missing_main_function',
                'function': 'get_claude_ai_instance'
            })
            
        # 3. Verificar contexto Flask
        try:
            from flask import current_app
            # Tentar acessar current_app (vai falhar fora do contexto)
            _ = current_app.config
            initialization_steps.append({
                'step': 'flask_context',
                'status': 'ACTIVE'
            })
            print("✅ Contexto Flask: Ativo")
        except:
            initialization_steps.append({
                'step': 'flask_context',
                'status': 'INACTIVE'
            })
            print("⚠️  Contexto Flask: Inativo (normal fora da aplicação)")
            
        return {
            'steps': initialization_steps,
            'total_steps': len(initialization_steps),
            'successful_steps': len([s for s in initialization_steps if s.get('status') in ['OK', 'AVAILABLE', 'ACTIVE']])
        }
        
    def check_module_loading_order(self) -> List[Dict[str, Any]]:
        """Verifica ordem de carregamento dos módulos"""
        print("\n\n📦 Verificando Carregamento de Módulos...")
        print("=" * 60)
        
        # Módulos na ordem que devem ser carregados
        module_order = [
            ('config', 'Configurações'),
            ('utils', 'Utilitários'),
            ('scanning', 'Scanners'),
            ('mappers', 'Mapeadores'),
            ('loaders', 'Carregadores'),
            ('validators', 'Validadores'),
            ('analyzers', 'Analisadores'),
            ('processors', 'Processadores'),
            ('enrichers', 'Enriquecedores'),
            ('memorizers', 'Memorizadores'),
            ('learners', 'Aprendizes'),
            ('conversers', 'Conversadores'),
            ('coordinators', 'Coordenadores'),
            ('orchestrators', 'Orquestradores'),
            ('integration', 'Integração'),
            ('commands', 'Comandos'),
            ('tools', 'Ferramentas'),
            ('suggestions', 'Sugestões')
        ]
        
        loading_status = []
        
        for module_name, description in module_order:
            module_path = self.base_dir / module_name
            
            if module_path.exists() and module_path.is_dir():
                init_file = module_path / '__init__.py'
                
                if init_file.exists():
                    try:
                        # Verificar se tem manager
                        with open(init_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        has_manager = 'Manager' in content
                        has_get_function = f'get_{module_name}_manager' in content or f'get_{module_name}' in content
                        
                        loading_status.append({
                            'module': module_name,
                            'description': description,
                            'status': 'OK',
                            'has_manager': has_manager,
                            'has_get_function': has_get_function
                        })
                        
                        status_symbol = "✅" if has_manager else "⚠️"
                        print(f"{status_symbol} {module_name}: {'Manager OK' if has_manager else 'Sem Manager'}")
                        
                    except Exception as e:
                        loading_status.append({
                            'module': module_name,
                            'description': description,
                            'status': 'ERROR',
                            'error': str(e)
                        })
                        print(f"❌ {module_name}: Erro - {e}")
                else:
                    loading_status.append({
                        'module': module_name,
                        'description': description,
                        'status': 'NO_INIT'
                    })
                    print(f"⚠️  {module_name}: Sem __init__.py")
            else:
                loading_status.append({
                    'module': module_name,
                    'description': description,
                    'status': 'MISSING'
                })
                print(f"❌ {module_name}: Pasta não existe")
                
        return loading_status
        
    def generate_report(self):
        """Gera relatório de configuração"""
        report = {
            'summary': {
                'total_issues': len(self.issues),
                'total_warnings': len(self.warnings),
                'critical_issues': len([i for i in self.issues if i.get('type') in ['missing_env_var', 'missing_main_function']]),
                'configuration_score': 0
            },
            'issues': self.issues,
            'warnings': self.warnings,
            'details': self.config_status
        }
        
        # Calcular score
        total_checks = 20  # Aproximado
        issues_weight = len(self.issues) * 5
        warnings_weight = len(self.warnings) * 2
        score = max(0, 100 - issues_weight - warnings_weight)
        report['summary']['configuration_score'] = score
        
        # Salvar relatório
        with open(self.base_dir / 'configuracao_sistema.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # Criar relatório Markdown
        self._create_markdown_report(report)
        
        return report
        
    def _create_markdown_report(self, report):
        """Cria relatório em Markdown"""
        md = ["# 📊 RELATÓRIO DE CONFIGURAÇÃO - Claude AI Novo\n"]
        md.append(f"**Data**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Resumo
        md.append("## 📈 Resumo Executivo\n")
        s = report['summary']
        md.append(f"- **Score de Configuração**: {s['configuration_score']}%")
        md.append(f"- **Issues Críticos**: {s['critical_issues']} 🚨")
        md.append(f"- **Issues Totais**: {s['total_issues']} ❌")
        md.append(f"- **Warnings**: {s['total_warnings']} ⚠️\n")
        
        # Issues críticos
        if s['critical_issues'] > 0:
            md.append("## 🚨 ISSUES CRÍTICOS\n")
            for issue in report['issues']:
                if issue.get('type') in ['missing_env_var', 'missing_main_function']:
                    md.append(f"- **{issue['type']}**: {issue.get('var', issue.get('function', 'N/A'))}")
            md.append("")
            
        # Outros issues
        other_issues = [i for i in report['issues'] if i.get('type') not in ['missing_env_var', 'missing_main_function']]
        if other_issues:
            md.append("## ❌ Outros Issues\n")
            for issue in other_issues:
                md.append(f"- **{issue['type']}**: {issue.get('file', issue.get('description', 'N/A'))}")
            md.append("")
            
        # Warnings
        if report['warnings']:
            md.append("## ⚠️ Warnings\n")
            for warning in report['warnings']:
                md.append(f"- **{warning['type']}**: {warning.get('file', warning.get('count', 'N/A'))}")
            md.append("")
            
        # Salvar
        with open(self.base_dir / 'RELATORIO_CONFIGURACAO.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(md))
            
    def run(self):
        """Executa verificação completa"""
        print("🔧 Verificando Configuração e Inicialização do Sistema...\n")
        
        # 1. Variáveis de ambiente
        env_status = self.check_environment_variables()
        self.config_status['environment'] = env_status
        
        # 2. Arquivos de configuração
        config_files = self.check_config_files()
        self.config_status['config_files'] = config_files
        
        # 3. Ordem de inicialização
        init_order = self.check_initialization_order()
        self.config_status['initialization'] = init_order
        
        # 4. Carregamento de módulos
        module_loading = self.check_module_loading_order()
        self.config_status['module_loading'] = module_loading
        
        # Gerar relatório
        report = self.generate_report()
        
        print("\n\n📊 RESUMO FINAL:")
        print("=" * 60)
        s = report['summary']
        print(f"Score: {s['configuration_score']}% | Issues: {s['total_issues']} | Warnings: {s['total_warnings']}")
        
        if s['critical_issues'] > 0:
            print("\n🚨 ATENÇÃO: Existem issues críticos de configuração!")
        elif s['total_issues'] > 0:
            print("\n⚠️  AVISO: Alguns problemas de configuração encontrados")
        else:
            print("\n✅ Configuração está correta!")
            
        print(f"\n📄 Relatório salvo em: RELATORIO_CONFIGURACAO.md")

if __name__ == "__main__":
    checker = ConfigurationChecker()
    checker.run() 