#!/usr/bin/env python3
"""
🧪 TESTE DA CORREÇÃO DO CAMPO DESTINO
=====================================

Testa se a correção do campo destino no DataProvider resolveu o problema.
"""

import os
import sys
import logging

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def testar_data_provider():
    """Testa o DataProvider com a correção do campo destino"""
    try:
        from app.claude_ai_novo.providers.data_provider import get_data_provider
        
        logger.info("📊 Testando DataProvider...")
        
        # Obter instância
        data_provider = get_data_provider()
        
        # Testar busca de entregas
        logger.info("\n🚚 Testando busca de entregas...")
        filters = {
            "cliente": "Atacadão",
            "data_inicio": "2025-06-01",
            "data_fim": "2025-07-14"
        }
        
        result = data_provider.get_data_by_domain("entregas", filters)
        
        if "error" in result:
            logger.error(f"❌ Erro ao buscar entregas: {result['error']}")
            return False
        
        logger.info(f"✅ Entregas encontradas: {result.get('total', 0)}")
        
        # Mostrar amostra dos dados
        if result.get('data'):
            logger.info("\n📋 Amostra dos dados (primeira entrega):")
            primeira_entrega = result['data'][0]
            for campo, valor in primeira_entrega.items():
                logger.info(f"  - {campo}: {valor}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_orchestrator():
    """Testa o Orchestrator com workflow completo"""
    try:
        from app.claude_ai_novo.orchestrators import get_orchestrator_manager
        
        logger.info("\n🎭 Testando Orchestrator...")
        
        # Obter instância
        orchestrator = get_orchestrator_manager()
        
        # Testar query
        data = {
            "query": "Como estão as entregas do Atacadão?",
            "context": {"user_id": "test"},
            "session_id": "test_session"
        }
        
        result = orchestrator.orchestrate(
            operation_type="intelligent_query",
            data=data
        )
        
        if result.get('success'):
            logger.info("✅ Orchestrator executado com sucesso")
            logger.info(f"📝 Resposta: {result.get('response', 'N/A')[:200]}...")
        else:
            logger.error(f"❌ Erro no Orchestrator: {result.get('error', 'Unknown')}")
            
        return result.get('success', False)
        
    except Exception as e:
        logger.error(f"❌ Erro no teste do Orchestrator: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa os testes"""
    logger.info("🧪 TESTANDO CORREÇÃO DO CAMPO DESTINO")
    logger.info("=" * 50)
    
    # Teste 1: DataProvider
    if testar_data_provider():
        logger.info("\n✅ DataProvider funcionando corretamente!")
    else:
        logger.error("\n❌ DataProvider com problemas!")
        return
    
    # Teste 2: Orchestrator
    if testar_orchestrator():
        logger.info("\n✅ Sistema completo funcionando!")
    else:
        logger.error("\n❌ Sistema ainda com problemas!")

if __name__ == "__main__":
    main() 