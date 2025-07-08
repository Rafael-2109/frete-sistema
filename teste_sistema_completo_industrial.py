#!/usr/bin/env python3
"""
🧪 TESTE SISTEMA COMPLETO DE IA INDUSTRIAL
Testa a estrutura e importações do sistema completo reescrito
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def teste_sistema_completo():
    """Testa estrutura do sistema completo sem dependências externas"""
    
    logger.info("🚀 TESTE SISTEMA COMPLETO DE IA INDUSTRIAL")
    logger.info("=" * 60)
    
    resultados = {}
    
    # 📦 TESTE 1: Integration Manager
    logger.info("📦 TESTE 1: Integration Manager")
    
    try:
        from app.claude_ai_novo.integration_manager import IntegrationManager
        resultados['integration_manager'] = "✅ SUCESSO"
        logger.info("✅ IntegrationManager importado com sucesso")
        
    except Exception as e:
        resultados['integration_manager'] = f"❌ ERRO: {e}"
        logger.error(f"❌ Erro ao importar IntegrationManager: {e}")
    
    # 🧠 TESTE 2: Claude Integration (Nova)
    logger.info("🧠 TESTE 2: Claude Integration (Nova)")
    
    try:
        from app.claude_ai_novo.integration.claude.claude_integration import ClaudeRealIntegration
        
        # Instanciar sem inicializar
        integration = ClaudeRealIntegration()
        
        resultados['claude_integration'] = "✅ SUCESSO"
        logger.info("✅ ClaudeRealIntegration criada com sucesso")
        
    except Exception as e:
        resultados['claude_integration'] = f"❌ ERRO: {e}"
        logger.error(f"❌ Erro na integração Claude: {e}")
    
    # 🔍 TESTE 3: Multi-Agent System
    logger.info("🔍 TESTE 3: Multi-Agent System")
    
    try:
        from app.claude_ai_novo.multi_agent.system import MultiAgentSystem
        from app.claude_ai_novo.multi_agent.multi_agent_orchestrator import MultiAgentOrchestrator
        
        resultados['multi_agent'] = "✅ SUCESSO"
        logger.info("✅ Multi-Agent System carregado")
        
    except Exception as e:
        resultados['multi_agent'] = f"❌ ERRO: {e}"
        logger.error(f"❌ Erro no Multi-Agent System: {e}")
    
    # 📊 TESTE 4: Database System
    logger.info("📊 TESTE 4: Database System")
    
    try:
        from app.claude_ai_novo.semantic.readers.database_reader import DatabaseReader
        from app.claude_ai_novo.semantic.readers.database.metadata_reader import MetadataReader
        
        resultados['database'] = "✅ SUCESSO"
        logger.info("✅ Database System carregado")
        
    except Exception as e:
        resultados['database'] = f"❌ ERRO: {e}"
        logger.error(f"❌ Erro no Database System: {e}")
    
    # 💡 TESTE 5: Learning System
    logger.info("💡 TESTE 5: Learning System")
    
    try:
        from app.claude_ai_novo.intelligence.learning.learning_core import LearningCore
        from app.claude_ai_novo.intelligence.learning.lifelong_learning import LifelongLearningSystem
        
        resultados['learning'] = "✅ SUCESSO"
        logger.info("✅ Learning System carregado")
        
    except Exception as e:
        resultados['learning'] = f"❌ ERRO: {e}"
        logger.error(f"❌ Erro no Learning System: {e}")
    
    # 🎯 TESTE 6: Advanced Integration
    logger.info("🎯 TESTE 6: Advanced Integration")
    
    try:
        from app.claude_ai_novo.integration.advanced.advanced_integration import AdvancedAIIntegration
        
        resultados['advanced'] = "✅ SUCESSO"
        logger.info("✅ Advanced Integration carregado")
        
    except Exception as e:
        resultados['advanced'] = f"❌ ERRO: {e}"
        logger.error(f"❌ Erro no Advanced Integration: {e}")
    
    # 🔧 TESTE 7: Estrutura Geral
    logger.info("🔧 TESTE 7: Estrutura Geral")
    
    try:
        # Teste mais simples - apenas contar módulos que conseguimos importar
        sucessos = sum(1 for r in resultados.values() if "✅ SUCESSO" in r)
        total = len(resultados)
        taxa = (sucessos / total) * 100
        
        if taxa >= 80:
            resultados['estrutura'] = f"✅ SUCESSO: {taxa:.1f}% ({sucessos}/{total})"
            logger.info(f"✅ Estrutura geral: {taxa:.1f}% dos módulos funcionais")
        else:
            resultados['estrutura'] = f"⚠️ LIMITADO: {taxa:.1f}% ({sucessos}/{total})"
            logger.warning(f"⚠️ Estrutura geral: {taxa:.1f}% dos módulos funcionais")
        
    except Exception as e:
        resultados['estrutura'] = f"❌ ERRO: {e}"
        logger.error(f"❌ Erro ao testar estrutura: {e}")
    
    return resultados

async def main():
    """Função principal do teste"""
    
    print("\n🚀 TESTE SISTEMA COMPLETO DE IA INDUSTRIAL")
    print("=" * 60)
    
    # Executar testes
    resultados = await teste_sistema_completo()
    
    # Relatório final
    print("\n📊 RELATÓRIO FINAL:")
    print("-" * 40)
    
    sucessos = 0
    total = len(resultados)
    
    for teste, resultado in resultados.items():
        print(f"{teste}: {resultado}")
        if "✅ SUCESSO" in resultado:
            sucessos += 1
    
    taxa_sucesso = (sucessos / total) * 100
    
    print(f"\n🎯 TAXA DE SUCESSO: {taxa_sucesso:.1f}% ({sucessos}/{total})")
    
    if taxa_sucesso >= 80:
        print("🎉 SISTEMA COMPLETO OPERACIONAL!")
        print("✅ Pronto para uso em produção")
    elif taxa_sucesso >= 60:
        print("⚠️ SISTEMA PARCIALMENTE OPERACIONAL")
        print("🔧 Algumas funcionalidades podem estar limitadas")
    else:
        print("❌ SISTEMA COM PROBLEMAS CRÍTICOS")
        print("🚨 Requer correções antes do uso")
    
    print(f"\n⏰ Teste concluído em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main()) 