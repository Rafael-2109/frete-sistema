#!/usr/bin/env python3
"""
🔥 VALIDADOR SISTEMA REAL - Versão de Produção
==================================================

Este validador roda no ambiente REAL da aplicação, não tem problemas
de import e testa os mesmos erros que estão aparecendo nos logs.

Criado após descoberta de que validadores anteriores eram inúteis.
"""

import sys
import os
import traceback
import importlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import json

# Adicionar o diretório raiz do projeto ao path ANTES de qualquer import
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

class ValidadorSistemaReal:
    """Validador que roda no ambiente real de produção"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'validator': 'ValidadorSistemaReal v1.0',
            'environment': 'REAL',
            'tests': {},
            'summary': {},
            'critical_errors': [],
            'production_issues': []
        }
        
    def log(self, message: str, level: str = "INFO"):
        """Log estruturado"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def test_basic_imports(self) -> bool:
        """Testa imports básicos que estão falhando nos logs"""
        self.log("🔍 Testando imports básicos...")
        
        tests = {
            'flask_app': self._test_flask_app_import,
            'anthropic_config': self._test_anthropic_config,
            'specialist_agents': self._test_specialist_agents,
            'domain_agents': self._test_domain_agents,
            'query_processor': self._test_query_processor,
            'response_processor': self._test_response_processor
        }
        
        passed = 0
        for test_name, test_func in tests.items():
            try:
                result = test_func()
                self.results['tests'][f'import_{test_name}'] = {
                    'status': 'PASS' if result else 'FAIL',
                    'details': f'Import test for {test_name}'
                }
                if result:
                    passed += 1
                    self.log(f"✅ {test_name}: OK")
                else:
                    self.log(f"❌ {test_name}: FALHOU")
            except Exception as e:
                self.results['tests'][f'import_{test_name}'] = {
                    'status': 'ERROR',
                    'details': str(e)
                }
                self.results['critical_errors'].append({
                    'test': f'import_{test_name}',
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
                self.log(f"💥 {test_name}: ERRO - {e}")
                
        return passed == len(tests)
    
    def _test_flask_app_import(self) -> bool:
        """Testa se consegue importar o app Flask básico"""
        try:
            from app import create_app
            app = create_app()
            return app is not None
        except Exception as e:
            self.results['production_issues'].append({
                'issue': 'flask_app_import',
                'error': str(e),
                'impact': 'CRITICAL - Sistema não pode inicializar'
            })
            return False
            
    def _test_anthropic_config(self) -> bool:
        """Testa o erro específico: 'ClaudeAIConfig' object has no attribute 'get_anthropic_api_key'"""
        try:
            # Tentar importar configuração do Claude
            from app.claude_ai_novo.config.advanced_config import ClaudeAIConfig
            config = ClaudeAIConfig()
            
            # Testar se o método existe
            if hasattr(config, 'get_anthropic_api_key'):
                api_key = config.get_anthropic_api_key()
                return api_key is not None
            else:
                self.results['production_issues'].append({
                    'issue': 'missing_get_anthropic_api_key',
                    'error': 'ClaudeAIConfig missing get_anthropic_api_key method',
                    'impact': 'HIGH - Claude API não pode ser inicializada',
                    'log_evidence': "'ClaudeAIConfig' object has no attribute 'get_anthropic_api_key'"
                })
                return False
        except Exception as e:
            self.results['production_issues'].append({
                'issue': 'anthropic_config_import',
                'error': str(e),
                'impact': 'HIGH - Configuração Claude não disponível'
            })
            return False
    
    def _test_specialist_agents(self) -> bool:
        """Testa o erro específico: cannot import name 'SpecialistAgent'"""
        try:
            from app.claude_ai_novo.coordinators.specialist_agents import SpecialistAgent
            agents = SpecialistAgent()
            return agents is not None
        except ImportError as e:
            self.results['production_issues'].append({
                'issue': 'missing_specialist_agents',
                'error': str(e),
                'impact': 'MEDIUM - Agentes especializados não disponíveis',
                'log_evidence': "cannot import name 'SpecialistAgent'"
            })
            return False
        except Exception as e:
            self.results['production_issues'].append({
                'issue': 'specialist_agents_error',
                'error': str(e),
                'impact': 'MEDIUM - Erro na inicialização de agentes'
            })
            return False
            
    def _test_domain_agents(self) -> bool:
        """Testa o erro específico: 'EmbarquesAgent' object has no attribute 'agent_type'"""
        try:
            from app.claude_ai_novo.coordinators.domain_agents.embarques_agent import EmbarquesAgent
            agent = EmbarquesAgent()
            
            if hasattr(agent, 'agent_type'):
                return agent.agent_type is not None
            else:
                self.results['production_issues'].append({
                    'issue': 'missing_agent_type_embarques',
                    'error': 'EmbarquesAgent missing agent_type attribute',
                    'impact': 'MEDIUM - Agente de embarques mal configurado',
                    'log_evidence': "'EmbarquesAgent' object has no attribute 'agent_type'"
                })
                return False
        except Exception as e:
            self.results['production_issues'].append({
                'issue': 'domain_agents_error',
                'error': str(e),
                'impact': 'MEDIUM - Erro nos agentes de domínio'
            })
            return False
            
    def _test_query_processor(self) -> bool:
        """Testa o erro específico: QueryProcessor.__init__() missing arguments"""
        try:
            from app.claude_ai_novo.processors.query_processor import QueryProcessor
            
            # Tentar instanciar com argumentos mínimos
            processor = QueryProcessor(
                claude_client=None,  # Mock
                context_manager=None,  # Mock  
                learning_system=None  # Mock
            )
            return processor is not None
        except TypeError as e:
            if "missing" in str(e) and "required positional arguments" in str(e):
                self.results['production_issues'].append({
                    'issue': 'query_processor_signature',
                    'error': str(e),
                    'impact': 'HIGH - QueryProcessor não pode ser instanciado',
                    'log_evidence': "QueryProcessor.__init__() missing 3 required positional arguments"
                })
            return False
        except Exception as e:
            self.results['production_issues'].append({
                'issue': 'query_processor_error',
                'error': str(e),
                'impact': 'HIGH - Erro no processador de queries'
            })
            return False
            
    def _test_response_processor(self) -> bool:
        """Testa o erro específico: ResponseProcessor com Anthropic"""
        try:
            from app.claude_ai_novo.processors.response_processor import ResponseProcessor
            processor = ResponseProcessor()
            
            # Verificar se consegue inicializar cliente Anthropic
            if hasattr(processor, 'claude_client') and processor.claude_client is not None:
                return True
            else:
                self.results['production_issues'].append({
                    'issue': 'response_processor_anthropic',
                    'error': 'ResponseProcessor cannot initialize Anthropic client',
                    'impact': 'HIGH - Processamento de respostas falha',
                    'log_evidence': "Erro ao inicializar cliente Anthropic"
                })
                return False
        except Exception as e:
            self.results['production_issues'].append({
                'issue': 'response_processor_error',
                'error': str(e),
                'impact': 'HIGH - ResponseProcessor não funciona'
            })
            return False
    
    def test_async_issues(self) -> bool:
        """Testa problemas de async/await encontrados nos logs"""
        self.log("🔍 Testando problemas async/await...")
        
        try:
            # Verificar se há problemas de async mal implementados
            from app.claude_ai_novo.integration.integration_manager import IntegrationManager
            manager = IntegrationManager()
            
            # Tentar operação que falha nos logs
            # Não executar await em método síncrono
            if hasattr(manager, 'process_query'):
                # Verificar se método está marcado como async corretamente
                import inspect
                is_async = inspect.iscoroutinefunction(manager.process_query)
                
                if is_async:
                    self.results['production_issues'].append({
                        'issue': 'async_await_mismatch',
                        'error': 'Método async sendo chamado sincronamente',
                        'impact': 'HIGH - Causa erro object dict cannot be used in await',
                        'log_evidence': "object dict can't be used in 'await' expression"
                    })
                    return False
                    
            return True
        except Exception as e:
            self.results['production_issues'].append({
                'issue': 'async_testing_error',
                'error': str(e),
                'impact': 'MEDIUM - Não foi possível testar async'
            })
            return False
    
    def test_production_health(self) -> bool:
        """Testa se o sistema consegue responder adequadamente"""
        self.log("🔍 Testando saúde do sistema...")
        
        try:
            # Testar se consegue acessar componentes básicos
            from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager
            manager = OrchestratorManager()
            
            # Verificar se consegue processar uma query simples
            if hasattr(manager, 'process_query'):
                # Tentar processamento básico
                result = manager.process_query("teste de saúde", {})
                return result is not None
            else:
                self.results['production_issues'].append({
                    'issue': 'missing_process_query',
                    'error': 'OrchestratorManager missing process_query method',
                    'impact': 'CRITICAL - Sistema não pode processar queries'
                })
                return False
        except Exception as e:
            self.results['production_issues'].append({
                'issue': 'production_health_error',
                'error': str(e),
                'impact': 'CRITICAL - Sistema não está saudável'
            })
            return False
            
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Executa validação completa no ambiente real"""
        self.log("🔥 INICIANDO VALIDAÇÃO SISTEMA REAL")
        self.log("=" * 50)
        
        # Executar testes
        tests = [
            ('basic_imports', self.test_basic_imports),
            ('async_issues', self.test_async_issues),
            ('production_health', self.test_production_health)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            self.log(f"\n🧪 Executando: {test_name}")
            try:
                result = test_func()
                self.results['tests'][test_name] = {
                    'status': 'PASS' if result else 'FAIL',
                    'timestamp': datetime.now().isoformat()
                }
                if result:
                    passed += 1
                    self.log(f"✅ {test_name}: PASSOU")
                else:
                    self.log(f"❌ {test_name}: FALHOU")
            except Exception as e:
                self.results['tests'][test_name] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
                self.log(f"💥 {test_name}: ERRO - {e}")
        
        # Calcular score
        score = (passed / total) * 100 if total > 0 else 0
        
        # Resumo
        self.results['summary'] = {
            'total_tests': total,
            'total': total,  # Fix: adicionar 'total' para compatibilidade
            'passed': passed,
            'failed': total - passed,
            'score': score,
            'classification': self._get_classification(score),
            'critical_issues': len(self.results['production_issues']),
            'health_status': 'CRITICAL' if score < 50 else 'WARNING' if score < 80 else 'GOOD'
        }
        
        self._print_summary()
        self._save_results()
        
        return self.results
    
    def _get_classification(self, score: float) -> str:
        """Classificação baseada no score"""
        if score >= 90:
            return "🎉 EXCELENTE"
        elif score >= 80:
            return "✅ BOM"
        elif score >= 60:
            return "⚠️ ACEITÁVEL"
        elif score >= 40:
            return "🔶 RUIM"
        else:
            return "🚨 CRÍTICO"
    
    def _print_summary(self):
        """Imprime resumo da validação"""
        summary = self.results['summary']
        
        self.log("\n" + "=" * 50)
        self.log("📊 RESUMO DA VALIDAÇÃO REAL")
        self.log("=" * 50)
        self.log(f"🎯 Score: {summary['score']:.1f}%")
        self.log(f"📋 Testes: {summary['passed']}/{summary['total']}")
        self.log(f"🏆 Classificação: {summary['classification']}")
        self.log(f"🔥 Issues Críticos: {summary['critical_issues']}")
        self.log(f"💗 Status Saúde: {summary['health_status']}")
        
        if self.results['production_issues']:
            self.log("\n🚨 PROBLEMAS ENCONTRADOS EM PRODUÇÃO:")
            for i, issue in enumerate(self.results['production_issues'], 1):
                self.log(f"  {i}. {issue['issue']}: {issue['error']}")
                self.log(f"     Impacto: {issue['impact']}")
                if 'log_evidence' in issue:
                    self.log(f"     Evidência: {issue['log_evidence']}")
                    
    def _save_results(self):
        """Salva resultados em arquivo"""
        filename = f"validacao_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(__file__).parent / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
            
        self.log(f"\n💾 Resultados salvos em: {filename}")

def main():
    """Função principal"""
    try:
        validator = ValidadorSistemaReal()
        results = validator.run_comprehensive_validation()
        
        # Exit code baseado no resultado
        if results['summary']['score'] < 50:
            exit(2)  # Crítico
        elif results['summary']['score'] < 80:
            exit(1)  # Warning
        else:
            exit(0)  # OK
            
    except Exception as e:
        print(f"💥 ERRO FATAL no validador: {e}")
        traceback.print_exc()
        exit(3)

if __name__ == "__main__":
    main() 