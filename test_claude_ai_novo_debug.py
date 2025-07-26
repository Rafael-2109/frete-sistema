#!/usr/bin/env python3
"""
Script de teste para debug do Claude AI Novo
Verifica problemas de integração e funcionamento
"""

import os
import sys
import asyncio
import logging
import traceback
from pathlib import Path

# Configurar path
sys.path.append(str(Path(__file__).parent))

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_integration_manager():
    """Testa o IntegrationManager diretamente"""
    logger.info("🔍 TESTE 1: IntegrationManager")
    
    try:
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        
        # Criar instância sem dependências externas
        im = IntegrationManager()
        
        # Testar processamento
        result = await im.process_unified_query("teste de integração")
        
        logger.info(f"✅ IntegrationManager OK: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ IntegrationManager ERRO: {e}")
        traceback.print_exc()
        return False

async def test_orchestrator_manager():
    """Testa o OrchestratorManager diretamente"""
    logger.info("🔍 TESTE 2: OrchestratorManager")
    
    try:
        from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager
        
        # Criar instância
        om = OrchestratorManager()
        
        # Testar processamento
        result = await om.process_query("teste de orchestrator")
        
        logger.info(f"✅ OrchestratorManager OK: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ OrchestratorManager ERRO: {e}")
        traceback.print_exc()
        return False

async def test_claude_ai_novo():
    """Testa o ClaudeAINovo completo"""
    logger.info("🔍 TESTE 3: ClaudeAINovo")
    
    try:
        from app.claude_ai_novo import ClaudeAINovo
        
        # Criar instância sem dependências
        claude = ClaudeAINovo()
        
        # Inicializar sistema
        init_result = await claude.initialize_system()
        logger.info(f"Inicialização: {init_result}")
        
        # Testar processamento
        result = await claude.process_query("teste de sistema completo")
        
        logger.info(f"✅ ClaudeAINovo OK: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ ClaudeAINovo ERRO: {e}")
        traceback.print_exc()
        return False

async def test_transition_manager():
    """Testa o ClaudeTransitionManager"""
    logger.info("🔍 TESTE 4: ClaudeTransitionManager")
    
    try:
        # Forçar uso do sistema novo
        os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'
        
        from app.claude_transition import ClaudeTransitionManager
        
        # Criar instância
        manager = ClaudeTransitionManager()
        
        # Verificar sistema ativo
        logger.info(f"Sistema ativo: {manager.sistema_ativo}")
        
        # Testar processamento
        result = await manager.processar_consulta("teste do transition manager")
        
        logger.info(f"✅ TransitionManager OK: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ TransitionManager ERRO: {e}")
        traceback.print_exc()
        return False

async def test_specific_query():
    """Testa uma query específica que está falhando"""
    logger.info("🔍 TESTE 5: Query Específica")
    
    try:
        from app.claude_transition import processar_consulta_transicao
        
        # Queries de teste
        queries = [
            "Como estão as entregas?",
            "Listar entregas do Atacadão",
            "Status das entregas de hoje",
            "Relatório de fretes"
        ]
        
        for query in queries:
            logger.info(f"\n📝 Testando: '{query}'")
            
            # Processar de forma síncrona
            try:
                # Criar novo event loop para evitar conflitos
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Executar query
                result = processar_consulta_transicao(query)
                
                logger.info(f"✅ Resultado: {type(result)} - {str(result)[:200]}...")
                
            except Exception as e:
                logger.error(f"❌ Erro na query '{query}': {e}")
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro geral no teste de queries: {e}")
        traceback.print_exc()
        return False

async def test_import_chain():
    """Testa a cadeia de imports para identificar problemas"""
    logger.info("🔍 TESTE 6: Cadeia de Imports")
    
    modules_to_test = [
        "app.claude_ai_novo",
        "app.claude_ai_novo.integration.integration_manager",
        "app.claude_ai_novo.orchestrators.orchestrator_manager",
        "app.claude_ai_novo.orchestrators.main_orchestrator",
        "app.claude_ai_novo.orchestrators.session_orchestrator",
        "app.claude_ai_novo.orchestrators.workflow_orchestrator",
        "app.claude_transition"
    ]
    
    for module in modules_to_test:
        try:
            logger.info(f"📦 Importando: {module}")
            __import__(module)
            logger.info(f"✅ {module} OK")
        except Exception as e:
            logger.error(f"❌ {module} ERRO: {e}")
            traceback.print_exc()
    
    return True

async def test_database_connection():
    """Testa conexão com banco de dados"""
    logger.info("🔍 TESTE 7: Conexão com Banco de Dados")
    
    try:
        # Verificar variáveis de ambiente
        db_url = os.getenv('DATABASE_URL')
        logger.info(f"DATABASE_URL configurada: {'SIM' if db_url else 'NÃO'}")
        
        if db_url:
            # Tentar conectar
            from sqlalchemy import create_engine, text
            
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("✅ Conexão com banco OK")
                return True
        else:
            logger.warning("⚠️ DATABASE_URL não configurada")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na conexão com banco: {e}")
        traceback.print_exc()
        return False

async def main():
    """Executa todos os testes"""
    logger.info("🚀 INICIANDO TESTES DE DEBUG DO CLAUDE AI NOVO")
    logger.info("=" * 60)
    
    # Verificar ambiente
    logger.info("📋 AMBIENTE:")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Path: {sys.path[0]}")
    logger.info(f"USE_NEW_CLAUDE_SYSTEM: {os.getenv('USE_NEW_CLAUDE_SYSTEM', 'não definido')}")
    logger.info("=" * 60)
    
    # Executar testes
    tests = [
        test_import_chain,
        test_database_connection,
        test_integration_manager,
        test_orchestrator_manager,
        test_claude_ai_novo,
        test_transition_manager,
        test_specific_query
    ]
    
    results = []
    for test in tests:
        logger.info(f"\n{'=' * 60}")
        result = await test()
        results.append((test.__name__, result))
        logger.info(f"{'=' * 60}\n")
    
    # Resumo
    logger.info("📊 RESUMO DOS TESTES:")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} testes passaram")
    logger.info("=" * 60)
    
    # Diagnóstico final
    if passed < total:
        logger.error("\n🔴 PROBLEMAS IDENTIFICADOS:")
        logger.error("1. Verifique os logs acima para erros específicos")
        logger.error("2. Confirme que todas as dependências estão instaladas")
        logger.error("3. Verifique as variáveis de ambiente")
        logger.error("4. Revise a estrutura de imports")
    else:
        logger.info("\n🟢 TODOS OS TESTES PASSARAM!")

if __name__ == "__main__":
    # Executar testes
    asyncio.run(main())