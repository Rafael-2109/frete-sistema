"""
Simulador de Produção - Reproduz comportamento real para detectar loops
Permite testar cenários problemáticos ANTES do commit
"""

import sys
import os
import time
import json
import threading
from datetime import datetime
import traceback

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importa os módulos principais
from app.claude_ai_novo.integration.integration_manager import IntegrationManager
from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager


class ProductionSimulator:
    """Simula comportamento de produção para detectar problemas"""
    
    def __init__(self):
        self.integration_manager = IntegrationManager()
        self.orchestrator_manager = OrchestratorManager()
        self.call_stack = []
        self.max_depth = 5
        self.timeout_seconds = 10
        
    def track_call(self, module, method, args):
        """Rastreia chamadas para detectar loops"""
        call_info = {
            'module': module,
            'method': method,
            'args': str(args)[:100],  # Limita tamanho
            'timestamp': time.time()
        }
        
        self.call_stack.append(call_info)
        
        # Detecta loops
        if len(self.call_stack) > self.max_depth:
            print("\n❌ LOOP DETECTADO!")
            print("Call Stack:")
            for i, call in enumerate(self.call_stack[-10:]):
                print(f"  {i}: {call['module']}.{call['method']}")
            return True
        
        # Detecta padrões repetitivos
        if len(self.call_stack) >= 4:
            recent_calls = [f"{c['module']}.{c['method']}" for c in self.call_stack[-4:]]
            if recent_calls[0] == recent_calls[2] and recent_calls[1] == recent_calls[3]:
                print("\n❌ PADRÃO DE LOOP DETECTADO!")
                print(f"   Repetição: {recent_calls[0]} -> {recent_calls[1]} -> {recent_calls[0]} -> {recent_calls[1]}")
                return True
                
        return False
    
    def simulate_query(self, query, context=None):
        """Simula uma query como em produção"""
        print(f"\n🔍 Simulando query: '{query}'")
        print("="*60)
        
        if context is None:
            context = {
                "user_id": "vendedor123",
                "session_id": f"sess_{int(time.time())}",
                "user_profile": "vendedor",
                "vendedor_codigo": "V001"
            }
        
        # Reseta rastreamento
        self.call_stack = []
        start_time = time.time()
        result = None
        error = None
        
        # Intercepta chamadas principais
        original_integration = self.integration_manager.process_unified_query
        original_orchestrator = self.orchestrator_manager.process_query
        
        def tracked_integration(*args, **kwargs):
            if self.track_call('IntegrationManager', 'process_unified_query', args):
                return {'error': 'Loop detectado', 'response': 'Sistema interrompido por segurança'}
            return original_integration(*args, **kwargs)
        
        def tracked_orchestrator(*args, **kwargs):
            if self.track_call('OrchestratorManager', 'process_query', args):
                return {'error': 'Loop detectado', 'response': 'Sistema interrompido por segurança'}
            return original_orchestrator(*args, **kwargs)
        
        # Aplica interceptadores
        self.integration_manager.process_unified_query = tracked_integration
        self.orchestrator_manager.process_query = tracked_orchestrator
        
        # Thread para timeout
        timeout_reached = False
        
        def run_query():
            nonlocal result, error
            try:
                result = self.integration_manager.process_unified_query(query, context)
            except Exception as e:
                error = e
                traceback.print_exc()
        
        # Executa em thread separada
        thread = threading.Thread(target=run_query)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout_seconds)
        
        if thread.is_alive():
            timeout_reached = True
            print(f"\n⏱️ TIMEOUT! Query travou por mais de {self.timeout_seconds} segundos")
        
        # Restaura originais
        self.integration_manager.process_unified_query = original_integration
        self.orchestrator_manager.process_query = original_orchestrator
        
        # Análise de resultado
        elapsed_time = time.time() - start_time
        
        print(f"\n📊 Resultado da Simulação:")
        print(f"   - Tempo: {elapsed_time:.2f}s")
        print(f"   - Chamadas rastreadas: {len(self.call_stack)}")
        print(f"   - Timeout: {'SIM' if timeout_reached else 'NÃO'}")
        print(f"   - Erro: {'SIM' if error else 'NÃO'}")
        
        if result:
            print(f"   - Resposta: {str(result)[:200]}...")
        
        # Retorna análise
        return {
            'success': not (timeout_reached or error or len(self.call_stack) > self.max_depth),
            'elapsed_time': elapsed_time,
            'call_count': len(self.call_stack),
            'timeout': timeout_reached,
            'error': str(error) if error else None,
            'response': result
        }
    
    def run_production_tests(self):
        """Executa bateria de testes de produção"""
        print("\n" + "="*80)
        print("🏭 SIMULADOR DE PRODUÇÃO - DETECÇÃO DE LOOPS")
        print("="*80)
        
        # Queries problemáticas conhecidas
        test_queries = [
            # Queries que causaram problemas
            ("Como estão as entregas do Atacadão?", {"_problema": "loop_historico"}),
            ("Mostre os fretes pendentes", {}),
            ("Status das entregas de hoje", {}),
            ("Relatório de pedidos em atraso", {}),
            
            # Queries complexas
            ("Análise completa do cliente Assai com gráficos", {}),
            ("Comparativo de performance entre transportadoras", {}),
            
            # Queries com contexto especial
            ("Continue a análise anterior", {"_from_conversation": True}),
            ("Detalhe mais sobre isso", {"_continuation": True}),
        ]
        
        results = []
        
        for query, extra_context in test_queries:
            context = {
                "user_id": "test_user",
                "session_id": f"test_{int(time.time())}",
                **extra_context
            }
            
            result = self.simulate_query(query, context)
            results.append({
                'query': query,
                'result': result
            })
            
            # Pausa entre testes
            time.sleep(0.5)
        
        # Resumo
        print("\n" + "="*80)
        print("📊 RESUMO DOS TESTES")
        print("="*80)
        
        total = len(results)
        successful = sum(1 for r in results if r['result']['success'])
        
        print(f"\nTotal de testes: {total}")
        print(f"Sucessos: {successful}")
        print(f"Falhas: {total - successful}")
        
        if successful < total:
            print("\n❌ PROBLEMAS DETECTADOS:")
            for r in results:
                if not r['result']['success']:
                    print(f"\n   Query: '{r['query']}'")
                    if r['result']['timeout']:
                        print(f"   - TIMEOUT após {self.timeout_seconds}s")
                    if r['result']['error']:
                        print(f"   - Erro: {r['result']['error']}")
                    if r['result']['call_count'] > self.max_depth:
                        print(f"   - Loop detectado: {r['result']['call_count']} chamadas")
        else:
            print("\n✅ TODOS OS TESTES PASSARAM!")
        
        return successful == total
    
    def test_specific_scenario(self, scenario_name):
        """Testa cenário específico de produção"""
        scenarios = {
            'loop_atacadao': {
                'query': 'Como estão as entregas do Atacadão?',
                'context': {
                    'user_id': 'vendedor123',
                    'vendedor_codigo': 'V001',
                    '_debug': True
                },
                'description': 'Query que causou loop infinito em produção'
            },
            'circular_reference': {
                'query': 'Análise integrada com todos os módulos',
                'context': {
                    '_force_integration': True,
                    '_force_orchestration': True
                },
                'description': 'Força uso de integração e orquestração simultaneamente'
            },
            'stress_test': {
                'query': 'Relatório completo de todos os clientes com gráficos e análises',
                'context': {
                    '_max_complexity': True
                },
                'description': 'Query complexa que estressa o sistema'
            }
        }
        
        if scenario_name not in scenarios:
            print(f"❌ Cenário '{scenario_name}' não encontrado")
            print(f"   Cenários disponíveis: {list(scenarios.keys())}")
            return False
        
        scenario = scenarios[scenario_name]
        print(f"\n🎯 Testando cenário: {scenario_name}")
        print(f"   Descrição: {scenario['description']}")
        
        result = self.simulate_query(scenario['query'], scenario['context'])
        
        if result['success']:
            print("\n✅ Cenário passou no teste!")
        else:
            print("\n❌ Cenário falhou!")
            
        return result['success']


def main():
    """Função principal"""
    simulator = ProductionSimulator()
    
    # Menu interativo
    while True:
        print("\n" + "="*60)
        print("🏭 SIMULADOR DE PRODUÇÃO - CLAUDE AI NOVO")
        print("="*60)
        print("\n1. Executar todos os testes")
        print("2. Testar query específica")
        print("3. Testar cenário conhecido")
        print("4. Configurar parâmetros")
        print("5. Sair")
        
        choice = input("\nEscolha uma opção: ").strip()
        
        if choice == '1':
            simulator.run_production_tests()
            
        elif choice == '2':
            query = input("\nDigite a query para testar: ").strip()
            if query:
                simulator.simulate_query(query)
                
        elif choice == '3':
            print("\nCenários disponíveis:")
            print("- loop_atacadao")
            print("- circular_reference")
            print("- stress_test")
            scenario = input("\nEscolha o cenário: ").strip()
            simulator.test_specific_scenario(scenario)
            
        elif choice == '4':
            print(f"\nParâmetros atuais:")
            print(f"- Max depth: {simulator.max_depth}")
            print(f"- Timeout: {simulator.timeout_seconds}s")
            
            try:
                new_depth = input("\nNovo max depth (Enter para manter): ").strip()
                if new_depth:
                    simulator.max_depth = int(new_depth)
                    
                new_timeout = input("Novo timeout em segundos (Enter para manter): ").strip()
                if new_timeout:
                    simulator.timeout_seconds = int(new_timeout)
                    
                print("\n✅ Parâmetros atualizados!")
            except ValueError:
                print("\n❌ Valor inválido!")
                
        elif choice == '5':
            print("\n👋 Saindo...")
            break
        
        input("\nPressione Enter para continuar...")


if __name__ == '__main__':
    # Se executado com argumentos, roda teste específico
    if len(sys.argv) > 1:
        simulator = ProductionSimulator()
        
        if sys.argv[1] == '--all':
            # Executa todos os testes
            success = simulator.run_production_tests()
            sys.exit(0 if success else 1)
            
        elif sys.argv[1] == '--query':
            # Testa query específica
            if len(sys.argv) > 2:
                query = ' '.join(sys.argv[2:])
                result = simulator.simulate_query(query)
                sys.exit(0 if result['success'] else 1)
            else:
                print("❌ Especifique a query após --query")
                sys.exit(1)
                
        elif sys.argv[1] == '--scenario':
            # Testa cenário específico
            if len(sys.argv) > 2:
                success = simulator.test_specific_scenario(sys.argv[2])
                sys.exit(0 if success else 1)
            else:
                print("❌ Especifique o cenário após --scenario")
                sys.exit(1)
    else:
        # Modo interativo
        main() 