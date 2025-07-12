"""
Testes para prevenir loops infinitos no sistema Claude AI Novo
Simula comportamento real de produção para detectar loops ANTES do commit
"""

import unittest
import sys
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import json

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.claude_ai_novo.integration.integration_manager import IntegrationManager
from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager


class TestLoopPrevention(unittest.TestCase):
    """Testes para detectar e prevenir loops infinitos"""
    
    def setUp(self):
        """Configuração inicial dos testes"""
        self.integration_manager = IntegrationManager()
        self.orchestrator_manager = OrchestratorManager()
        
        # Contador de chamadas para detectar loops
        self.call_count = {
            'integration': 0,
            'orchestrator': 0
        }
        
        # Flag para timeout
        self.timeout_reached = False
        
    def test_direct_loop_detection(self):
        """Testa detecção direta de loop entre Integration e Orchestrator"""
        print("\n🔍 Testando detecção direta de loop...")
        
        # Simula query que causaria loop
        query = "Como estão as entregas do Atacadão?"
        context = {"user_id": "test", "session_id": "test123"}
        
        # Intercepta chamadas para contar
        original_integration = self.integration_manager.process_unified_query
        original_orchestrator = self.orchestrator_manager.process_query
        
        def count_integration_calls(*args, **kwargs):
            self.call_count['integration'] += 1
            if self.call_count['integration'] > 2:
                self.fail("Loop detectado: IntegrationManager chamado mais de 2 vezes!")
            return original_integration(*args, **kwargs)
            
        def count_orchestrator_calls(*args, **kwargs):
            self.call_count['orchestrator'] += 1
            if self.call_count['orchestrator'] > 2:
                self.fail("Loop detectado: OrchestratorManager chamado mais de 2 vezes!")
            return original_orchestrator(*args, **kwargs)
        
        # Aplica interceptadores
        self.integration_manager.process_unified_query = count_integration_calls
        self.orchestrator_manager.process_query = count_orchestrator_calls
        
        # Executa query
        try:
            response = self.integration_manager.process_unified_query(query, context)
            
            # Verifica se não houve loop
            self.assertLessEqual(self.call_count['integration'], 2, 
                               "IntegrationManager foi chamado muitas vezes")
            self.assertLessEqual(self.call_count['orchestrator'], 2,
                               "OrchestratorManager foi chamado muitas vezes")
            
            # Verifica se resposta é válida
            self.assertIsNotNone(response)
            self.assertIn('response', response)
            
            print(f"✅ Loop prevenido com sucesso!")
            print(f"   - Chamadas Integration: {self.call_count['integration']}")
            print(f"   - Chamadas Orchestrator: {self.call_count['orchestrator']}")
            
        except Exception as e:
            self.fail(f"Erro durante teste: {str(e)}")
    
    def test_timeout_protection(self):
        """Testa proteção contra travamento com timeout"""
        print("\n⏱️ Testando proteção de timeout...")
        
        def run_with_timeout():
            """Executa query com timeout"""
            try:
                query = "Status do sistema"
                context = {"user_id": "test"}
                
                # Simula processamento
                response = self.integration_manager.process_unified_query(query, context)
                
                # Se chegou aqui, não travou
                self.assertIsNotNone(response)
                
            except Exception as e:
                # Qualquer erro é melhor que travar
                pass
        
        # Cria thread com timeout
        thread = threading.Thread(target=run_with_timeout)
        thread.daemon = True
        thread.start()
        
        # Aguarda no máximo 5 segundos
        thread.join(timeout=5.0)
        
        if thread.is_alive():
            self.fail("Sistema travou! Timeout de 5 segundos excedido")
        else:
            print("✅ Sistema respondeu dentro do timeout")
    
    def test_circular_reference_detection(self):
        """Testa detecção de referências circulares"""
        print("\n🔄 Testando detecção de referências circulares...")
        
        # Mock para simular comportamento problemático
        with patch.object(self.orchestrator_manager, '_execute_integration_operation') as mock_exec:
            # Simula tentativa de chamar integration_manager de volta
            mock_exec.side_effect = lambda *args, **kwargs: {
                'error': 'Referência circular detectada',
                'response': 'Operação bloqueada por segurança'
            }
            
            query = "Análise complexa que requer integração"
            response = self.orchestrator_manager.process_query(query, {})
            
            # Verifica se não causou loop
            self.assertIsNotNone(response)
            print("✅ Referência circular prevenida com sucesso")
    
    def test_real_production_scenario(self):
        """Simula cenário real de produção com dados reais"""
        print("\n🏭 Simulando cenário de produção...")
        
        # Queries reais que causaram problemas
        problematic_queries = [
            "Como estão as entregas do Atacadão?",
            "Mostre os fretes pendentes",
            "Status das entregas de hoje",
            "Relatório de pedidos em atraso"
        ]
        
        for query in problematic_queries:
            print(f"\n   Testando: '{query}'")
            
            # Reset contador
            self.call_count = {'integration': 0, 'orchestrator': 0}
            
            # Simula contexto real
            context = {
                "user_id": "vendedor123",
                "session_id": "sess_" + str(int(time.time())),
                "user_profile": "vendedor",
                "vendedor_codigo": "V001"
            }
            
            # Monitora chamadas
            start_time = time.time()
            
            try:
                response = self.integration_manager.process_unified_query(query, context)
                
                elapsed_time = time.time() - start_time
                
                # Validações
                self.assertLess(elapsed_time, 3.0, 
                              f"Query demorou muito: {elapsed_time:.2f}s")
                self.assertIsNotNone(response)
                self.assertIn('response', response)
                
                print(f"   ✅ OK - Tempo: {elapsed_time:.2f}s")
                
            except Exception as e:
                self.fail(f"Erro na query '{query}': {str(e)}")
    
    def test_stress_concurrent_requests(self):
        """Testa múltiplas requisições concorrentes"""
        print("\n🔥 Testando requisições concorrentes...")
        
        results = []
        errors = []
        
        def make_request(idx):
            """Faz uma requisição"""
            try:
                query = f"Status do pedido {idx}"
                response = self.integration_manager.process_unified_query(
                    query, 
                    {"user_id": f"user_{idx}"}
                )
                results.append(response)
            except Exception as e:
                errors.append(str(e))
        
        # Cria 10 threads concorrentes
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()
        
        # Aguarda todas terminarem
        for t in threads:
            t.join(timeout=5.0)
        
        # Verifica resultados
        self.assertEqual(len(errors), 0, f"Erros encontrados: {errors}")
        self.assertEqual(len(results), 10, "Nem todas as requisições completaram")
        
        print(f"✅ {len(results)} requisições concorrentes processadas sem loops")
    
    def test_anti_loop_response_quality(self):
        """Testa qualidade das respostas anti-loop"""
        print("\n📝 Testando qualidade das respostas anti-loop...")
        
        # Força situação de loop
        query = "Como estão as entregas do Atacadão?"
        context = {"_from_orchestrator": True}  # Simula flag de loop
        
        response = self.integration_manager.process_unified_query(query, context)
        
        # Verifica qualidade da resposta
        self.assertIsNotNone(response)
        self.assertIn('response', response)
        
        response_text = response['response']
        
        # Verifica se tem informações úteis
        self.assertIn('Atacadão', response_text, "Resposta deve mencionar o cliente")
        self.assertTrue(
            any(word in response_text.lower() for word in ['entrega', 'pedido', 'status']),
            "Resposta deve ter contexto relevante"
        )
        
        print("✅ Resposta anti-loop tem qualidade adequada")
        print(f"   Resposta: {response_text[:100]}...")


def run_pre_commit_tests():
    """Executa todos os testes antes do commit"""
    print("\n" + "="*60)
    print("🚀 EXECUTANDO TESTES PRÉ-COMMIT")
    print("="*60)
    
    # Cria suite de testes
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLoopPrevention)
    
    # Executa testes
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Resumo
    print("\n" + "="*60)
    if result.wasSuccessful():
        print("✅ TODOS OS TESTES PASSARAM!")
        print("   Sistema seguro para commit")
        return True
    else:
        print("❌ TESTES FALHARAM!")
        print(f"   Erros: {len(result.errors)}")
        print(f"   Falhas: {len(result.failures)}")
        print("\n⚠️  NÃO FAÇA COMMIT! Corrija os problemas primeiro.")
        return False


if __name__ == '__main__':
    # Executa testes pré-commit
    success = run_pre_commit_tests()
    
    # Retorna código de saída apropriado
    sys.exit(0 if success else 1) 