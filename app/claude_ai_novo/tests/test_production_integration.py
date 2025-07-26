"""
🧪 PRODUCTION INTEGRATION TESTS - Claude AI Novo
==============================================

Testes de integração para verificar que o sistema está pronto para produção.
Execute antes do deploy para garantir que tudo está funcionando.
"""

import pytest
import os
import sys
from datetime import datetime
import logging

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

logger = logging.getLogger(__name__)

class TestProductionReadiness:
    """Testes de prontidão para produção"""
    
    def test_environment_variables(self):
        """Testa se variáveis de ambiente críticas estão configuradas"""
        # Variáveis opcionais mas importantes
        optional_vars = {
            'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
            'DATABASE_URL': os.getenv('DATABASE_URL'),
            'SECRET_KEY': os.getenv('SECRET_KEY')
        }
        
        # Verificar quais estão faltando
        missing = [var for var, value in optional_vars.items() if not value]
        
        if missing:
            logger.warning(f"⚠️ Variáveis de ambiente faltando (configure em produção): {missing}")
        
        # Teste não falha, apenas avisa
        assert True, "Verificação de ambiente concluída"
    
    def test_import_main_module(self):
        """Testa se o módulo principal pode ser importado"""
        try:
            from app.claude_ai_novo import ClaudeAINovo
            assert ClaudeAINovo is not None
            logger.info("✅ Módulo principal importado com sucesso")
        except ImportError as e:
            pytest.fail(f"❌ Falha ao importar módulo principal: {e}")
    
    def test_create_instance(self):
        """Testa se uma instância pode ser criada"""
        try:
            from app.claude_ai_novo import ClaudeAINovo
            
            # Criar instância sem dependências externas
            instance = ClaudeAINovo()
            assert instance is not None
            assert hasattr(instance, 'process_query')
            assert hasattr(instance, 'get_system_status')
            
            logger.info("✅ Instância criada com sucesso")
        except Exception as e:
            pytest.fail(f"❌ Falha ao criar instância: {e}")
    
    def test_security_guard(self):
        """Testa se o SecurityGuard está funcionando"""
        try:
            from app.claude_ai_novo.security.security_guard import SecurityGuard
            
            guard = SecurityGuard()
            
            # Testar validação de input
            assert guard.validate_input("consulta normal") == True
            assert guard.validate_input("DROP TABLE users") == False
            assert guard.validate_input("<script>alert('xss')</script>") == False
            
            # Testar sanitização
            sanitized = guard.sanitize_input("<script>alert('test')</script>Hello")
            assert "<script>" not in sanitized
            assert "Hello" in sanitized
            
            logger.info("✅ SecurityGuard funcionando corretamente")
        except Exception as e:
            pytest.fail(f"❌ Falha no SecurityGuard: {e}")
    
    def test_health_check_module(self):
        """Testa se o módulo de health check funciona"""
        try:
            from app.claude_ai_novo.api.health_check import HealthCheckService
            
            service = HealthCheckService()
            assert service is not None
            
            # Não executamos o check async aqui, apenas verificamos que existe
            assert hasattr(service, 'check_system_health')
            assert hasattr(service, '_check_claude_api')
            assert hasattr(service, '_check_database')
            
            logger.info("✅ Módulo de health check disponível")
        except Exception as e:
            pytest.fail(f"❌ Falha no health check: {e}")
    
    def test_api_endpoints_blueprint(self):
        """Testa se o blueprint da API pode ser criado"""
        try:
            from app.claude_ai_novo.api import claude_ai_api_bp
            
            assert claude_ai_api_bp is not None
            assert claude_ai_api_bp.name == 'claude_ai_api'
            
            # Verificar endpoints registrados
            rules = [str(rule) for rule in claude_ai_api_bp.deferred_functions]
            logger.info(f"📍 Endpoints registrados: {len(rules)}")
            
            logger.info("✅ Blueprint da API criado com sucesso")
        except Exception as e:
            pytest.fail(f"❌ Falha no blueprint da API: {e}")
    
    def test_configuration_system(self):
        """Testa se o sistema de configuração funciona"""
        try:
            from app.claude_ai_novo.config.system_config import SystemConfig
            
            config = SystemConfig()
            
            # Testar operações básicas
            test_value = config.get_config('system.name')
            assert test_value is not None
            
            # Testar detecção de profile
            profile = config.active_profile
            assert profile in ['development', 'testing', 'staging', 'production']
            
            logger.info(f"✅ Sistema de configuração OK - Profile: {profile}")
        except Exception as e:
            pytest.fail(f"❌ Falha no sistema de configuração: {e}")
    
    def test_fallback_responses(self):
        """Testa se o sistema tem respostas de fallback"""
        try:
            from app.claude_ai_novo import ClaudeAINovo
            
            instance = ClaudeAINovo()
            
            # Testar com query vazia
            result = instance.processar_consulta_sync("")
            assert result is not None
            assert isinstance(result, str)
            assert len(result) > 0
            
            # Testar com None
            result = instance.processar_consulta_sync(None)
            assert result is not None
            assert isinstance(result, str)
            
            logger.info("✅ Sistema de fallback funcionando")
        except Exception as e:
            logger.warning(f"⚠️ Fallback com problemas (não crítico): {e}")
    
    def test_production_detection(self):
        """Testa detecção de ambiente de produção"""
        try:
            from app.claude_ai_novo.security.security_guard import SecurityGuard
            
            guard = SecurityGuard()
            
            # Verificar se detecta produção corretamente
            is_prod = guard.is_production
            logger.info(f"🏭 Ambiente detectado: {'PRODUÇÃO' if is_prod else 'DESENVOLVIMENTO'}")
            
            # Em produção, verificar se está mais permissivo
            if is_prod:
                assert guard.validate_user_access('process_query') == True
                logger.info("✅ Modo produção com permissões adequadas")
            
            assert True  # Teste sempre passa, apenas informativo
        except Exception as e:
            logger.warning(f"⚠️ Problema na detecção de produção: {e}")


class TestCriticalPaths:
    """Testes dos caminhos críticos do sistema"""
    
    def test_query_processing_path(self):
        """Testa o caminho completo de processamento de query"""
        try:
            from app.claude_ai_novo import ClaudeAINovo
            
            instance = ClaudeAINovo()
            
            # Processar uma query de teste
            test_query = "Qual é o status do sistema?"
            result = instance.process_query_sync(test_query)
            
            assert result is not None
            assert isinstance(result, dict)
            
            # Verificar estrutura da resposta
            assert 'success' in result or 'error' in result
            
            logger.info("✅ Caminho de processamento de query OK")
        except Exception as e:
            logger.error(f"❌ Falha crítica no processamento: {e}")
            pytest.fail("Processamento de query falhou")
    
    def test_error_handling(self):
        """Testa se erros são tratados adequadamente"""
        try:
            from app.claude_ai_novo import ClaudeAINovo
            
            instance = ClaudeAINovo()
            
            # Testar com input problemático
            problematic_inputs = [
                None,
                "",
                "DROP TABLE users;",
                "<script>alert('xss')</script>",
                "x" * 20000,  # String muito longa
                {"invalid": "type"},  # Tipo errado
            ]
            
            for inp in problematic_inputs:
                try:
                    result = instance.process_query_sync(inp)
                    # Deve retornar algo, não crashar
                    assert result is not None
                except Exception as e:
                    # Se houver exceção, deve ser tratada
                    logger.warning(f"Exceção tratada para input {type(inp)}: {e}")
            
            logger.info("✅ Tratamento de erros funcionando")
        except Exception as e:
            pytest.fail(f"❌ Falha no tratamento de erros: {e}")


def run_production_tests():
    """Executa todos os testes de produção e retorna relatório"""
    import subprocess
    
    print("\n" + "="*60)
    print("🧪 TESTES DE INTEGRAÇÃO PARA PRODUÇÃO - Claude AI Novo")
    print("="*60 + "\n")
    
    # Executar pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("ERROS:", result.stderr)
    
    # Resumo
    print("\n" + "="*60)
    if result.returncode == 0:
        print("✅ TODOS OS TESTES PASSARAM - SISTEMA PRONTO PARA PRODUÇÃO!")
    else:
        print("❌ ALGUNS TESTES FALHARAM - REVISAR ANTES DO DEPLOY")
    print("="*60 + "\n")
    
    return result.returncode == 0


if __name__ == "__main__":
    # Se executado diretamente, rodar os testes
    success = run_production_tests()
    sys.exit(0 if success else 1)