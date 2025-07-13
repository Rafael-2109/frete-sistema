#!/usr/bin/env python3
"""
🧪 TESTE DE CONEXÕES DO ORCHESTRATOR
====================================

Verifica se todas as conexões entre módulos estão funcionando corretamente.
"""

import os
import sys
import logging
from typing import Dict, Any

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def testar_conexoes_basicas():
    """Testa se os módulos básicos foram modificados corretamente"""
    logger.info("\n🔍 TESTANDO MODIFICAÇÕES BÁSICAS")
    logger.info("=" * 60)
    
    resultados = {
        'loader_aceita_injecao': False,
        'provider_aceita_injecao': False,
        'orchestrator_tem_connect': False
    }
    
    try:
        # 1. Testar LoaderManager
        logger.info("\n📊 Testando LoaderManager...")
        from app.claude_ai_novo.loaders.loader_manager import LoaderManager
        
        # Verificar se aceita parâmetros
        try:
            loader = LoaderManager(scanner=None, mapper=None)
            resultados['loader_aceita_injecao'] = True
            logger.info("✅ LoaderManager aceita scanner e mapper via injeção")
        except TypeError as e:
            logger.error(f"❌ LoaderManager não aceita injeção: {e}")
            
        # Verificar métodos de configuração
        if hasattr(loader, 'configure_with_scanner'):
            logger.info("✅ LoaderManager tem método configure_with_scanner")
        else:
            logger.warning("❌ LoaderManager não tem método configure_with_scanner")
            
        if hasattr(loader, 'configure_with_mapper'):
            logger.info("✅ LoaderManager tem método configure_with_mapper")
        else:
            logger.warning("❌ LoaderManager não tem método configure_with_mapper")
            
    except Exception as e:
        logger.error(f"❌ Erro ao testar LoaderManager: {e}")
        
    try:
        # 2. Testar DataProvider
        logger.info("\n📊 Testando DataProvider...")
        from app.claude_ai_novo.providers.data_provider import DataProvider
        
        # Verificar se aceita loader
        try:
            provider = DataProvider(loader=None)
            resultados['provider_aceita_injecao'] = True
            logger.info("✅ DataProvider aceita loader via injeção")
        except TypeError as e:
            logger.error(f"❌ DataProvider não aceita injeção: {e}")
            
        # Verificar método set_loader
        if hasattr(provider, 'set_loader'):
            logger.info("✅ DataProvider tem método set_loader")
        else:
            logger.warning("❌ DataProvider não tem método set_loader")
            
    except Exception as e:
        logger.error(f"❌ Erro ao testar DataProvider: {e}")
        
    try:
        # 3. Testar MainOrchestrator
        logger.info("\n📊 Testando MainOrchestrator...")
        from app.claude_ai_novo.orchestrators.main_orchestrator import MainOrchestrator
        
        orchestrator = MainOrchestrator()
        
        # Verificar se tem _connect_modules
        if hasattr(orchestrator, '_connect_modules'):
            resultados['orchestrator_tem_connect'] = True
            logger.info("✅ MainOrchestrator tem método _connect_modules")
        else:
            logger.error("❌ MainOrchestrator não tem método _connect_modules")
            
    except Exception as e:
        logger.error(f"❌ Erro ao testar MainOrchestrator: {e}")
        
    return resultados

def testar_conexoes_orchestrator():
    """Testa as conexões estabelecidas pelo Orchestrator"""
    logger.info("\n🔗 TESTANDO CONEXÕES DO ORCHESTRATOR")
    logger.info("=" * 60)
    
    conexoes = {
        'scanner_loader': False,
        'loader_provider': False,
        'memorizer_processor': False,
        'learner_analyzer': False
    }
    
    try:
        from app.claude_ai_novo.orchestrators import get_orchestrator_manager
        
        logger.info("📊 Criando OrchestratorManager...")
        orchestrator_manager = get_orchestrator_manager()
        
        if hasattr(orchestrator_manager, 'main_orchestrator'):
            main_orch = orchestrator_manager.main_orchestrator
            
            # Verificar componentes carregados
            if hasattr(main_orch, 'components'):
                componentes = list(main_orch.components.keys())
                logger.info(f"\n✅ Componentes carregados: {componentes}")
                logger.info(f"   Total: {len(componentes)} componentes")
                
                # Testar conexão Scanner → Loader
                if 'loaders' in main_orch.components and 'scanners' in main_orch.components:
                    loader = main_orch.components['loaders']
                    if hasattr(loader, 'scanner') and loader.scanner is not None:
                        conexoes['scanner_loader'] = True
                        logger.info("\n✅ Scanner → Loader: CONECTADO")
                        
                        # Verificar se scanner tem info do banco
                        if hasattr(loader, 'db_info') and loader.db_info:
                            logger.info("   └─ LoaderManager tem acesso a db_info do Scanner")
                    else:
                        logger.warning("\n❌ Scanner → Loader: NÃO conectado")
                        if hasattr(loader, 'scanner'):
                            logger.info("   └─ Loader tem atributo scanner mas está None")
                
                # Testar conexão Loader → Provider
                if 'providers' in main_orch.components and 'loaders' in main_orch.components:
                    provider = main_orch.components['providers']
                    if hasattr(provider, 'loader') and provider.loader is not None:
                        conexoes['loader_provider'] = True
                        logger.info("\n✅ Loader → Provider: CONECTADO")
                    else:
                        logger.warning("\n❌ Loader → Provider: NÃO conectado")
                        if hasattr(provider, 'loader'):
                            logger.info("   └─ Provider tem atributo loader mas está None")
                
                # Testar conexão Memorizer → Processor
                if 'processors' in main_orch.components and 'memorizers' in main_orch.components:
                    processor = main_orch.components['processors']
                    if hasattr(processor, 'memory') and processor.memory is not None:
                        conexoes['memorizer_processor'] = True
                        logger.info("\n✅ Memorizer → Processor: CONECTADO")
                    else:
                        logger.warning("\n❌ Memorizer → Processor: NÃO conectado")
                        logger.info("   └─ Processor não tem memory configurado")
                
                # Testar conexão Learner → Analyzer
                if 'analyzers' in main_orch.components and 'learners' in main_orch.components:
                    analyzer = main_orch.components['analyzers']
                    if hasattr(analyzer, 'learner') and analyzer.learner is not None:
                        conexoes['learner_analyzer'] = True
                        logger.info("\n✅ Learner → Analyzer: CONECTADO")
                    else:
                        logger.warning("\n❌ Learner → Analyzer: NÃO conectado")
                        logger.info("   └─ Analyzer não tem learner configurado")
                        
            else:
                logger.error("❌ MainOrchestrator não tem componentes")
        else:
            logger.error("❌ OrchestratorManager não tem main_orchestrator")
            
    except Exception as e:
        logger.error(f"❌ Erro ao testar conexões: {e}")
        import traceback
        traceback.print_exc()
        
    return conexoes

def testar_fluxo_query():
    """Testa um fluxo completo de query"""
    logger.info("\n🔄 TESTANDO FLUXO DE QUERY")
    logger.info("=" * 60)
    
    try:
        from app.claude_ai_novo.orchestrators import get_orchestrator_manager
        
        orchestrator = get_orchestrator_manager()
        
        # Tentar executar uma query simples
        logger.info("\n📝 Executando query de teste...")
        result = orchestrator.process_query(
            query="teste de conexão",
            context={"test": True}
        )
        
        if result:
            logger.info("✅ Query executada com sucesso")
            
            # Verificar metadados
            if 'metadata' in result:
                logger.info("\n📊 Metadados da execução:")
                for key, value in result['metadata'].items():
                    logger.info(f"   - {key}: {value}")
                    
            # Verificar se usou loader otimizado
            if result.get('metadata', {}).get('source') == 'loader_manager':
                logger.info("\n✅ DataProvider usou LoaderManager (otimizado)")
            else:
                logger.warning("\n⚠️ DataProvider não usou LoaderManager")
                
        else:
            logger.warning("⚠️ Query retornou resultado vazio")
            
    except Exception as e:
        logger.error(f"❌ Erro ao testar fluxo: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Executa todos os testes de conexão"""
    logger.info("🧪 TESTE COMPLETO DE CONEXÕES DO ORCHESTRATOR")
    logger.info("=" * 60)
    
    # 1. Testar modificações básicas
    resultados_basicos = testar_conexoes_basicas()
    
    # 2. Testar conexões do orchestrator
    conexoes = testar_conexoes_orchestrator()
    
    # 3. Testar fluxo de query
    testar_fluxo_query()
    
    # Resumo final
    logger.info("\n" + "=" * 60)
    logger.info("📊 RESUMO DOS TESTES")
    logger.info("=" * 60)
    
    logger.info("\n🔧 Modificações Básicas:")
    for teste, resultado in resultados_basicos.items():
        status = "✅" if resultado else "❌"
        logger.info(f"   {status} {teste}")
        
    logger.info("\n🔗 Conexões Estabelecidas:")
    for conexao, resultado in conexoes.items():
        status = "✅" if resultado else "❌"
        logger.info(f"   {status} {conexao}")
        
    # Contagem final
    total_basicos = sum(resultados_basicos.values())
    total_conexoes = sum(conexoes.values())
    
    logger.info(f"\n📈 Resultado Final:")
    logger.info(f"   - Modificações básicas: {total_basicos}/{len(resultados_basicos)}")
    logger.info(f"   - Conexões funcionando: {total_conexoes}/{len(conexoes)}")
    
    if total_basicos == len(resultados_basicos) and total_conexoes > 0:
        logger.info("\n✅ Sistema está no caminho certo!")
        logger.info("   Próximo passo: Implementar métodos faltantes nos módulos")
    else:
        logger.warning("\n⚠️ Algumas conexões ainda precisam ser implementadas")
        logger.info("   Verifique os métodos faltantes nos módulos")

if __name__ == "__main__":
    main() 