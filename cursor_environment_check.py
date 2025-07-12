#!/usr/bin/env python3
"""
🔍 CURSOR ENVIRONMENT CHECK - Verificação do Ambiente Real
=========================================================

Script para coletar informações REAIS do ambiente antes de configurar
a integração com Cursor. Evita suposições incorretas.

USAGE:
    python cursor_environment_check.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

class EnvironmentChecker:
    """Coleta informações reais do ambiente para configuração correta"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.info = {}
        
        print("🔍 VERIFICAÇÃO DO AMBIENTE REAL")
        print("=" * 50)
        print("Coletando informações para configuração correta do Cursor...")
        print("=" * 50)
    
    def check_python_setup(self) -> Dict[str, Any]:
        """Verifica configuração real do Python"""
        python_info = {
            'current_python': sys.executable,
            'python_version': sys.version,
            'virtual_env': None,
            'venv_locations': []
        }
        
        # Verificar virtual environments possíveis
        possible_venv_paths = [
            self.project_root / "venv",
            self.project_root / ".venv", 
            self.project_root / "env",
            self.project_root / ".env"
        ]
        
        for venv_path in possible_venv_paths:
            if venv_path.exists():
                # Windows
                python_exe = venv_path / "Scripts" / "python.exe"
                if python_exe.exists():
                    python_info['venv_locations'].append({
                        'path': str(venv_path),
                        'type': 'windows',
                        'python_exe': str(python_exe)
                    })
                
                # Linux/Mac
                python_exe = venv_path / "bin" / "python"
                if python_exe.exists():
                    python_info['venv_locations'].append({
                        'path': str(venv_path),
                        'type': 'unix',
                        'python_exe': str(python_exe)
                    })
        
        # Detectar se já está em venv
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            python_info['currently_in_venv'] = True
            python_info['venv_path'] = sys.prefix
        else:
            python_info['currently_in_venv'] = False
        
        return python_info
    
    def check_project_structure(self) -> Dict[str, Any]:
        """Verifica estrutura real do projeto"""
        structure = {
            'root_files': [],
            'app_structure': {},
            'claude_ai_novo_structure': {},
            'key_files_found': {}
        }
        
        # Arquivos na raiz
        for item in self.project_root.iterdir():
            if item.is_file():
                structure['root_files'].append(item.name)
        
        # Estrutura app/
        app_dir = self.project_root / "app"
        if app_dir.exists():
            structure['app_structure'] = {
                'exists': True,
                'modules': [d.name for d in app_dir.iterdir() if d.is_dir()]
            }
        
        # Estrutura claude_ai_novo/
        claude_dir = app_dir / "claude_ai_novo" if app_dir.exists() else None
        if claude_dir and claude_dir.exists():
            structure['claude_ai_novo_structure'] = {
                'exists': True,
                'subdirs': [d.name for d in claude_dir.iterdir() if d.is_dir()],
                'key_files': [f.name for f in claude_dir.iterdir() if f.is_file() and f.suffix == '.py']
            }
        
        # Verificar arquivos-chave
        key_files = {
            'run.py': self.project_root / "run.py",
            'requirements.txt': self.project_root / "requirements.txt",
            'config.py': self.project_root / "config.py",
            'validador_sistema_real.py': self.project_root / "app" / "claude_ai_novo" / "validador_sistema_real.py",
            'check_status.py': self.project_root / "app" / "claude_ai_novo" / "check_status.py"
        }
        
        for name, path in key_files.items():
            structure['key_files_found'][name] = path.exists()
        
        return structure
    
    def check_flask_configuration(self) -> Dict[str, Any]:
        """Verifica configuração real do Flask"""
        flask_info = {
            'flask_app_file': None,
            'possible_entry_points': [],
            'environment_vars': {},
            'config_files': []
        }
        
        # Procurar possíveis entry points
        possible_entries = ['run.py', 'app.py', 'main.py', 'wsgi.py']
        for entry in possible_entries:
            entry_path = self.project_root / entry
            if entry_path.exists():
                flask_info['possible_entry_points'].append(entry)
                if entry == 'run.py':
                    flask_info['flask_app_file'] = entry
        
        # Verificar variáveis de ambiente relacionadas ao Flask
        flask_env_vars = ['FLASK_APP', 'FLASK_ENV', 'FLASK_DEBUG', 'DATABASE_URL', 'SECRET_KEY']
        for var in flask_env_vars:
            value = os.environ.get(var)
            if value:
                flask_info['environment_vars'][var] = value[:50] + "..." if len(value) > 50 else value
        
        # Procurar arquivos de configuração
        config_files = ['config.py', '.env', '.flaskenv', 'app/config.py']
        for config_file in config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                flask_info['config_files'].append(config_file)
        
        return flask_info
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Verifica dependências instaladas"""
        deps_info = {
            'requirements_file': None,
            'installed_packages': {},
            'missing_critical': []
        }
        
        # Verificar requirements.txt
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            deps_info['requirements_file'] = str(req_file)
        
        # Verificar pacotes críticos instalados
        critical_packages = ['flask', 'requests', 'anthropic', 'sqlalchemy', 'psycopg2', 'redis']
        
        for package in critical_packages:
            try:
                __import__(package)
                deps_info['installed_packages'][package] = "✅ Instalado"
            except ImportError:
                deps_info['installed_packages'][package] = "❌ Não encontrado"
                deps_info['missing_critical'].append(package)
        
        return deps_info
    
    def check_api_endpoints(self) -> Dict[str, Any]:
        """Verifica quais endpoints da API realmente existem"""
        api_info = {
            'flask_running': False,
            'base_url': None,
            'available_endpoints': [],
            'test_urls': {}
        }
        
        # Verificar se Flask está rodando localmente
        test_urls = [
            'http://localhost:5000',
            'http://127.0.0.1:5000',
            'http://localhost:8000'
        ]
        
        import requests
        for url in test_urls:
            try:
                response = requests.get(f"{url}/health", timeout=2)
                if response.status_code == 200:
                    api_info['flask_running'] = True
                    api_info['base_url'] = url
                    break
            except:
                continue
        
        # Se Flask estiver rodando, testar endpoints
        if api_info['flask_running']:
            test_endpoints = [
                '/health',
                '/api/claude-ai-novo/status',
                '/api/system/info',
                '/claude-ai/query',
                '/api/pedidos/pendentes'
            ]
            
            for endpoint in test_endpoints:
                try:
                    response = requests.get(f"{api_info['base_url']}{endpoint}", timeout=2)
                    api_info['test_urls'][endpoint] = {
                        'status': response.status_code,
                        'available': response.status_code < 500
                    }
                    if response.status_code < 500:
                        api_info['available_endpoints'].append(endpoint)
                except Exception as e:
                    api_info['test_urls'][endpoint] = {
                        'status': 'error',
                        'error': str(e),
                        'available': False
                    }
        
        return api_info
    
    def check_database_config(self) -> Dict[str, Any]:
        """Verifica configuração do banco de dados"""
        db_info = {
            'database_url': None,
            'db_type': None,
            'connection_test': False
        }
        
        # Verificar DATABASE_URL
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            db_info['database_url'] = db_url[:50] + "..." if len(db_url) > 50 else db_url
            
            # Detectar tipo de banco
            if 'postgresql' in db_url or 'postgres' in db_url:
                db_info['db_type'] = 'PostgreSQL'
            elif 'sqlite' in db_url:
                db_info['db_type'] = 'SQLite'
            elif 'mysql' in db_url:
                db_info['db_type'] = 'MySQL'
        
        # Tentar testar conexão se SQLAlchemy estiver disponível
        try:
            from sqlalchemy import create_engine
            if db_url:
                engine = create_engine(db_url)
                with engine.connect() as conn:
                    db_info['connection_test'] = True
        except Exception as e:
            db_info['connection_error'] = str(e)
        
        return db_info
    
    def generate_recommendations(self) -> List[str]:
        """Gera recomendações baseadas no ambiente detectado"""
        recommendations = []
        
        # Recomendações sobre Python
        python_info = self.info.get('python', {})
        if not python_info.get('venv_locations'):
            recommendations.append("⚠️ Nenhum virtual environment detectado. Considere criar com: python -m venv venv")
        
        # Recomendações sobre Flask
        flask_info = self.info.get('flask', {})
        if not flask_info.get('flask_app_file'):
            recommendations.append("⚠️ Arquivo principal do Flask não detectado claramente")
        
        # Recomendações sobre API
        api_info = self.info.get('api', {})
        if not api_info.get('flask_running'):
            recommendations.append("💡 Flask não está rodando. Inicie com: python run.py")
        
        # Recomendações sobre dependências
        deps_info = self.info.get('dependencies', {})
        if deps_info.get('missing_critical'):
            recommendations.append(f"📦 Instalar dependências: pip install {' '.join(deps_info['missing_critical'])}")
        
        return recommendations
    
    def run_full_check(self) -> Dict[str, Any]:
        """Executa verificação completa do ambiente"""
        print("🔍 Verificando configuração Python...")
        self.info['python'] = self.check_python_setup()
        
        print("🔍 Verificando estrutura do projeto...")
        self.info['project'] = self.check_project_structure()
        
        print("🔍 Verificando configuração Flask...")
        self.info['flask'] = self.check_flask_configuration()
        
        print("🔍 Verificando dependências...")
        self.info['dependencies'] = self.check_dependencies()
        
        print("🔍 Verificando APIs disponíveis...")
        self.info['api'] = self.check_api_endpoints()
        
        print("🔍 Verificando configuração do banco...")
        self.info['database'] = self.check_database_config()
        
        print("🔍 Gerando recomendações...")
        self.info['recommendations'] = self.generate_recommendations()
        
        return self.info
    
    def print_summary_report(self):
        """Imprime relatório resumido"""
        print("\n" + "=" * 60)
        print("📊 RELATÓRIO DO AMBIENTE")
        print("=" * 60)
        
        # Python
        python_info = self.info['python']
        print(f"\n🐍 PYTHON:")
        print(f"   Versão: {python_info['python_version'].split()[0]}")
        print(f"   Executável: {python_info['current_python']}")
        print(f"   Virtual Envs encontrados: {len(python_info['venv_locations'])}")
        
        # Projeto
        project_info = self.info['project']
        print(f"\n📁 PROJETO:")
        print(f"   Claude AI Novo existe: {'✅' if project_info['claude_ai_novo_structure'].get('exists') else '❌'}")
        print(f"   Validador encontrado: {'✅' if project_info['key_files_found'].get('validador_sistema_real.py') else '❌'}")
        print(f"   run.py encontrado: {'✅' if project_info['key_files_found'].get('run.py') else '❌'}")
        
        # Flask
        flask_info = self.info['flask']
        print(f"\n🌐 FLASK:")
        print(f"   Entry point: {flask_info.get('flask_app_file', 'Não detectado')}")
        print(f"   Variáveis ambiente: {len(flask_info['environment_vars'])}")
        
        # API
        api_info = self.info['api']
        print(f"\n🔌 API:")
        print(f"   Flask rodando: {'✅' if api_info['flask_running'] else '❌'}")
        if api_info['flask_running']:
            print(f"   Base URL: {api_info['base_url']}")
            print(f"   Endpoints disponíveis: {len(api_info['available_endpoints'])}")
        
        # Dependências
        deps_info = self.info['dependencies']
        print(f"\n📦 DEPENDÊNCIAS:")
        for package, status in deps_info['installed_packages'].items():
            print(f"   {package}: {status}")
        
        # Recomendações
        if self.info['recommendations']:
            print(f"\n💡 RECOMENDAÇÕES:")
            for rec in self.info['recommendations']:
                print(f"   {rec}")
        
        print("\n" + "=" * 60)
    
    def save_detailed_report(self):
        """Salva relatório detalhado em JSON"""
        report_file = self.project_root / "cursor_environment_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.info, f, indent=2, default=str)
        
        print(f"📄 Relatório detalhado salvo em: {report_file}")

def main():
    """Função principal"""
    try:
        checker = EnvironmentChecker()
        
        # Executar verificação completa
        checker.run_full_check()
        
        # Mostrar relatório
        checker.print_summary_report()
        
        # Salvar relatório detalhado
        checker.save_detailed_report()
        
        print("\n✅ Verificação completa!")
        print("Use essas informações para configurar o Cursor corretamente.")
        
    except Exception as e:
        print(f"\n❌ Erro durante verificação: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 