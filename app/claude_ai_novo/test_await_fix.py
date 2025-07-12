"""
🔧 TESTE DE CORREÇÃO DE AWAIT - Verificação das Correções
========================================================

Script para testar se o erro "object dict can't be used in 'await' expression"
foi corrigido com sucesso.
"""

import logging
import asyncio
from typing import Dict, Any
import sys
import traceback

logger = logging.getLogger(__name__)

class AwaitFixTester:
    """
    Testa se as correções de await foram aplicadas corretamente.
    """
    
    def __init__(self):
        self.test_results = []
        
    def test_integration_manager_orchestrator(self) -> Dict[str, Any]:
        """
        Testa o IntegrationManagerOrchestrator.
        
        Returns:
            Resultado do teste
        """
        try:
            from app.claude_ai_novo.integration.integration_manager_orchestrator import IntegrationManagerOrchestrator
            
            # Criar instância
            manager = IntegrationManagerOrchestrator()
            
            # Testar processo unified query
            result = asyncio.run(manager.process_unified_query("teste"))
            
            return {
                'test': 'integration_manager_orchestrator',
                'success': True,
                'result': result,
                'error': None
            }
            
        except Exception as e:
            return {
                'test': 'integration_manager_orchestrator',
                'success': False,
                'result': None,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def test_orchestrator_manager(self) -> Dict[str, Any]:
        """
        Testa o OrchestratorManager.
        
        Returns:
            Resultado do teste
        """
        try:
            from app.claude_ai_novo.orchestrators import get_orchestrator_manager
            
            # Criar instância
            manager = get_orchestrator_manager()
            
            # Testar process_query (não async)
            result = manager.process_query("teste")
            
            return {
                'test': 'orchestrator_manager',
                'success': True,
                'result': result,
                'error': None
            }
            
        except Exception as e:
            return {
                'test': 'orchestrator_manager',
                'success': False,
                'result': None,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def test_integration_manager_main(self) -> Dict[str, Any]:
        """
        Testa o IntegrationManager principal.
        
        Returns:
            Resultado do teste
        """
        try:
            from app.claude_ai_novo.integration.integration_manager import IntegrationManager
            
            # Criar instância
            manager = IntegrationManager()
            
            # Testar process_unified_query (agora com await correto)
            result = asyncio.run(manager.process_unified_query("teste"))
            
            return {
                'test': 'integration_manager_main',
                'success': True,
                'result': result,
                'error': None
            }
            
        except Exception as e:
            return {
                'test': 'integration_manager_main',
                'success': False,
                'result': None,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def test_full_integration_flow(self) -> Dict[str, Any]:
        """
        Testa o fluxo completo de integração.
        
        Returns:
            Resultado do teste
        """
        try:
            from app.claude_ai_novo.integration.integration_manager import IntegrationManager
            
            # Criar instância
            manager = IntegrationManager()
            
            # Testar inicialização completa
            result = asyncio.run(manager.initialize_all_modules())
            
            return {
                'test': 'full_integration_flow',
                'success': True,
                'result': result,
                'error': None
            }
            
        except Exception as e:
            return {
                'test': 'full_integration_flow',
                'success': False,
                'result': None,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Executa todos os testes.
        
        Returns:
            Relatório completo dos testes
        """
        logger.info("🧪 Iniciando testes de correção de await...")
        
        tests = [
            self.test_orchestrator_manager,
            self.test_integration_manager_main,
            self.test_integration_manager_orchestrator,
            self.test_full_integration_flow
        ]
        
        results = []
        
        for test_func in tests:
            try:
                result = test_func()
                results.append(result)
                
                if result['success']:
                    logger.info(f"✅ {result['test']}: PASSOU")
                else:
                    logger.error(f"❌ {result['test']}: FALHOU - {result['error']}")
                    
            except Exception as e:
                logger.error(f"💥 Erro crítico no teste {test_func.__name__}: {e}")
                results.append({
                    'test': test_func.__name__,
                    'success': False,
                    'error': str(e),
                    'critical': True
                })
        
        # Calcular estatísticas
        total_tests = len(results)
        passed_tests = len([r for r in results if r['success']])
        failed_tests = total_tests - passed_tests
        
        # Verificar se o erro específico foi corrigido
        await_error_fixed = not any(
            'await' in str(r.get('error', '')) and 'dict' in str(r.get('error', ''))
            for r in results if not r['success']
        )
        
        report = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            'await_error_fixed': await_error_fixed,
            'results': results
        }
        
        logger.info(f"🎯 Relatório Final: {passed_tests}/{total_tests} testes passaram ({report['success_rate']:.1f}%)")
        
        return report


def main():
    """Função principal para executar os testes."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 TESTE DE CORREÇÃO DE AWAIT")
    print("="*50)
    
    tester = AwaitFixTester()
    report = tester.run_all_tests()
    
    print("\n" + "="*50)
    print("📊 RELATÓRIO DE TESTES")
    print("="*50)
    print(f"Total de testes: {report['total_tests']}")
    print(f"Testes que passaram: {report['passed_tests']}")
    print(f"Testes que falharam: {report['failed_tests']}")
    print(f"Taxa de sucesso: {report['success_rate']:.1f}%")
    
    if report['await_error_fixed']:
        print("\n✅ ERRO DE AWAIT CORRIGIDO!")
    else:
        print("\n❌ ERRO DE AWAIT AINDA PRESENTE!")
    
    print("\n📋 DETALHES DOS TESTES:")
    for result in report['results']:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"  {status} - {result['test']}")
        if not result['success']:
            print(f"    Erro: {result['error']}")
    
    # Retornar código de saída apropriado
    return 0 if report['success_rate'] >= 75 else 1


if __name__ == "__main__":
    sys.exit(main()) 