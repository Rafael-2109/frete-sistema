#!/usr/bin/env python3
"""
🔍 CURSOR MONITOR - Monitoramento em Tempo Real
===============================================

Sistema de monitoramento integrado para usar no Cursor durante desenvolvimento.
Monitora logs, APIs, sistema e Claude AI Novo em tempo real.

USAGE no Cursor:
1. Terminal integrado: python app/claude_ai_novo/monitoring/cursor_monitor.py
2. Ou use a task: Ctrl+Shift+P > "Tasks: Run Task" > "Monitor System"
"""

import asyncio
import json
import time
import requests
import subprocess
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import threading
import signal

# Adicionar path do projeto
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class MonitorStatus:
    """Status do monitoramento"""
    system_health: str = "unknown"
    api_status: str = "unknown"
    claude_ai_status: str = "unknown"
    last_error: Optional[str] = None
    uptime: float = 0
    total_requests: int = 0
    errors_count: int = 0

class CursorMonitor:
    """Monitor integrado para desenvolvimento no Cursor"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.status = MonitorStatus()
        self.start_time = time.time()
        self.running = False
        self.check_interval = 5  # segundos
        
        # Configurar URLs
        self.urls = {
            'health': f"{base_url}/health",
            'claude_status': f"{base_url}/api/claude-ai-novo/status",
            'system_info': f"{base_url}/api/system/info",
            'metrics': f"{base_url}/api/metrics/performance"
        }
        
        print("🔍 CURSOR MONITOR INICIADO")
        print("=" * 50)
        print(f"📡 Base URL: {base_url}")
        print(f"⏱️ Intervalo: {self.check_interval}s")
        print(f"🎯 Monitorando: Sistema + Claude AI + APIs")
        print("=" * 50)
    
    def clear_screen(self):
        """Limpa tela do terminal"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def format_uptime(self, seconds: float) -> str:
        """Formata tempo de execução"""
        td = timedelta(seconds=int(seconds))
        return str(td)
    
    def format_timestamp(self) -> str:
        """Timestamp formatado"""
        return datetime.now().strftime("%H:%M:%S")
    
    def check_url(self, name: str, url: str) -> Dict[str, Any]:
        """Verifica status de uma URL"""
        try:
            start_time = time.time()
            response = requests.get(url, timeout=3)
            response_time = (time.time() - start_time) * 1000
            
            return {
                'name': name,
                'status': 'ok' if response.status_code == 200 else 'error',
                'status_code': response.status_code,
                'response_time': response_time,
                'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            }
        except requests.exceptions.ConnectionError:
            return {
                'name': name,
                'status': 'offline',
                'error': 'Conexão recusada - servidor pode estar offline'
            }
        except requests.exceptions.Timeout:
            return {
                'name': name,
                'status': 'timeout',
                'error': 'Timeout na requisição'
            }
        except Exception as e:
            return {
                'name': name,
                'status': 'error',
                'error': str(e)
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do sistema"""
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
                'boot_time': psutil.boot_time()
            }
        except ImportError:
            return {'error': 'psutil não disponível'}
    
    def check_flask_process(self) -> Dict[str, Any]:
        """Verifica se processo Flask está rodando"""
        try:
            # Procurar por processos Python rodando run.py ou flask
            if os.name == 'nt':
                cmd = 'tasklist /FI "IMAGENAME eq python.exe" /FO CSV'
            else:
                cmd = 'ps aux | grep -E "(run.py|flask)" | grep -v grep'
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                return {'status': 'running', 'processes': len(result.stdout.split('\n')) - 1}
            else:
                return {'status': 'not_running', 'processes': 0}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def run_validator(self) -> Dict[str, Any]:
        """Executa validador rápido do sistema"""
        try:
            validator_path = project_root / "app" / "claude_ai_novo" / "check_status.py"
            
            if not validator_path.exists():
                return {'status': 'error', 'error': 'Validador não encontrado'}
            
            result = subprocess.run(
                [sys.executable, str(validator_path)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(project_root)
            )
            
            if result.returncode == 0:
                # Tentar extrair informações do output
                output_lines = result.stdout.split('\n')
                score_line = [line for line in output_lines if 'Score:' in line]
                
                if score_line:
                    score = score_line[0].split('Score:')[1].strip().split('%')[0]
                    return {
                        'status': 'ok',
                        'score': float(score),
                        'classification': 'excellent' if float(score) > 90 else 'good' if float(score) > 70 else 'warning'
                    }
                
                return {'status': 'ok', 'output': result.stdout[:200]}
            else:
                return {'status': 'error', 'error': result.stderr[:200]}
                
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'error': 'Validador demorou mais que 10s'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def display_status(self, results: Dict[str, Any]):
        """Exibe status formatado no terminal"""
        self.clear_screen()
        
        timestamp = self.format_timestamp()
        uptime = self.format_uptime(time.time() - self.start_time)
        
        print("🔍 CURSOR MONITOR - SISTEMA FRETES")
        print("=" * 60)
        print(f"🕐 {timestamp} | ⏱️ Uptime: {uptime}")
        print()
        
        # STATUS GERAL
        print("📊 STATUS GERAL")
        print("-" * 30)
        
        # Flask Process
        flask_status = results.get('flask_process', {})
        flask_icon = "🟢" if flask_status.get('status') == 'running' else "🔴"
        print(f"{flask_icon} Flask Server: {flask_status.get('status', 'unknown').upper()}")
        
        # System Stats
        sys_stats = results.get('system_stats', {})
        if 'cpu_percent' in sys_stats:
            cpu_icon = "🟢" if sys_stats['cpu_percent'] < 70 else "🟡" if sys_stats['cpu_percent'] < 90 else "🔴"
            mem_icon = "🟢" if sys_stats['memory_percent'] < 70 else "🟡" if sys_stats['memory_percent'] < 90 else "🔴"
            print(f"{cpu_icon} CPU: {sys_stats['cpu_percent']:.1f}%")
            print(f"{mem_icon} Memória: {sys_stats['memory_percent']:.1f}%")
        
        print()
        
        # APIS STATUS
        print("🌐 APIS STATUS")
        print("-" * 30)
        
        for check_name, result in results.get('api_checks', {}).items():
            if result['status'] == 'ok':
                icon = "🟢"
                details = f"({result['response_time']:.0f}ms)"
            elif result['status'] == 'offline':
                icon = "🔴"
                details = "(OFFLINE)"
            elif result['status'] == 'timeout':
                icon = "🟡"
                details = "(TIMEOUT)"
            else:
                icon = "🔴"
                details = f"(ERROR: {result.get('error', 'unknown')[:30]})"
            
            print(f"{icon} {check_name.upper()}: {details}")
        
        print()
        
        # CLAUDE AI STATUS
        print("🤖 CLAUDE AI NOVO")
        print("-" * 30)
        
        claude_data = results.get('api_checks', {}).get('claude_status', {}).get('data')
        if claude_data:
            components = claude_data.get('components', {})
            for component, status in components.items():
                icon = "🟢" if status else "🔴"
                print(f"{icon} {component}: {'OK' if status else 'ERRO'}")
        
        # VALIDATOR STATUS
        validator_result = results.get('validator', {})
        if validator_result.get('status') == 'ok' and 'score' in validator_result:
            score = validator_result['score']
            classification = validator_result['classification']
            
            if classification == 'excellent':
                icon = "🟢"
            elif classification == 'good':
                icon = "🟡"
            else:
                icon = "🔴"
            
            print(f"{icon} Validação Sistema: {score}% ({classification.upper()})")
        
        print()
        
        # ESTATÍSTICAS
        print("📈 ESTATÍSTICAS")
        print("-" * 30)
        print(f"📊 Total Checks: {self.status.total_requests}")
        print(f"❌ Erros: {self.status.errors_count}")
        print(f"✅ Taxa Sucesso: {((self.status.total_requests - self.status.errors_count) / max(self.status.total_requests, 1) * 100):.1f}%")
        
        if self.status.last_error:
            print(f"⚠️ Último Erro: {self.status.last_error[:50]}...")
        
        print()
        print("💡 Pressione Ctrl+C para parar o monitor")
        print("🔄 Próxima verificação em 5 segundos...")
    
    async def monitor_loop(self):
        """Loop principal de monitoramento"""
        self.running = True
        
        while self.running:
            try:
                # Inicializar resultados
                results = {
                    'timestamp': time.time(),
                    'api_checks': {},
                    'system_stats': {},
                    'flask_process': {},
                    'validator': {}
                }
                
                # Verificar APIs em paralelo
                api_tasks = []
                for name, url in self.urls.items():
                    task = asyncio.create_task(
                        asyncio.to_thread(self.check_url, name, url)
                    )
                    api_tasks.append(task)
                
                api_results = await asyncio.gather(*api_tasks)
                
                for result in api_results:
                    results['api_checks'][result['name']] = result
                    
                    if result['status'] != 'ok':
                        self.status.errors_count += 1
                        self.status.last_error = result.get('error', 'Unknown error')
                
                # Verificar sistema
                results['system_stats'] = await asyncio.to_thread(self.get_system_stats)
                results['flask_process'] = await asyncio.to_thread(self.check_flask_process)
                
                # Executar validador (menos frequente)
                if self.status.total_requests % 6 == 0:  # A cada 30 segundos
                    results['validator'] = await asyncio.to_thread(self.run_validator)
                
                # Atualizar estatísticas
                self.status.total_requests += 1
                self.status.uptime = time.time() - self.start_time
                
                # Exibir status
                self.display_status(results)
                
                # Aguardar próximo ciclo
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.status.errors_count += 1
                self.status.last_error = str(e)
                print(f"❌ Erro no monitor: {e}")
                await asyncio.sleep(self.check_interval)
        
        print("\n🛑 Monitor parado.")
    
    def start(self):
        """Inicia o monitor"""
        try:
            # Configurar handler para Ctrl+C
            def signal_handler(sig, frame):
                print("\n🛑 Parando monitor...")
                self.running = False
            
            signal.signal(signal.SIGINT, signal_handler)
            
            # Executar loop assíncrono
            asyncio.run(self.monitor_loop())
            
        except KeyboardInterrupt:
            print("\n🛑 Monitor interrompido pelo usuário.")
        except Exception as e:
            print(f"❌ Erro fatal no monitor: {e}")

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor em tempo real para desenvolvimento no Cursor")
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL do sistema')
    parser.add_argument('--interval', type=int, default=5, help='Intervalo entre checks (segundos)')
    
    args = parser.parse_args()
    
    monitor = CursorMonitor(base_url=args.url)
    monitor.check_interval = args.interval
    
    monitor.start()

if __name__ == "__main__":
    main() 