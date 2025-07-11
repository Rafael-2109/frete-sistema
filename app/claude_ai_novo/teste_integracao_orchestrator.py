#!/usr/bin/env python3
"""
🧪 TESTE DA NOVA INTEGRAÇÃO ORCHESTRATOR
=========================================

Testa se a nova versão do integration_manager usando orchestrators está funcionando.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
import traceback

def teste_importacao():
    """Testa se a importação está funcionando"""
    print("🔍 Testando importação do IntegrationManager...")
    
    try:
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        print("✅ IntegrationManager importado com sucesso")
        
        # Testar instanciação
        manager = IntegrationManager()
        print("✅ IntegrationManager instanciado com sucesso")
        
        return manager
        
    except Exception as e:
        print(f"❌ Erro na importação: {e}")
        traceback.print_exc()
        return None

def teste_orchestrator_import():
    """Testa se o orchestrator pode ser importado"""
    print("\n🔍 Testando importação do orchestrator...")
    
    try:
        from app.claude_ai_novo.orchestrators import get_orchestrator_manager
        print("✅ get_orchestrator_manager importado com sucesso")
        
        # Testar chamada da função
        orchestrator = get_orchestrator_manager()
        print(f"✅ get_orchestrator_manager executado: {orchestrator is not None}")
        
        return orchestrator
        
    except Exception as e:
        print(f"❌ Erro na importação do orchestrator: {e}")
        traceback.print_exc()
        return None

async def teste_inicializacao(manager):
    """Testa se a inicialização está funcionando"""
    print("\n🔍 Testando inicialização do sistema...")
    
    try:
        # Testar inicialização
        start_time = datetime.now()
        result = await manager.initialize_all_modules()
        end_time = datetime.now()
        
        print(f"✅ Inicialização concluída em {(end_time - start_time).total_seconds():.2f}s")
        print(f"📊 Resultado: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
        traceback.print_exc()
        return None

async def teste_consulta(manager):
    """Testa se o processamento de consulta está funcionando"""
    print("\n🔍 Testando processamento de consulta...")
    
    try:
        # Testar consulta simples
        result = await manager.process_unified_query("Como estão as entregas?")
        print(f"✅ Consulta processada: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Erro na consulta: {e}")
        traceback.print_exc()
        return None

def teste_status(manager):
    """Testa se o status do sistema está funcionando"""
    print("\n🔍 Testando status do sistema...")
    
    try:
        # Testar status
        status = manager.get_system_status()
        print(f"✅ Status obtido: {status}")
        
        return status
        
    except Exception as e:
        print(f"❌ Erro ao obter status: {e}")
        traceback.print_exc()
        return None

async def main():
    """Função principal de teste"""
    print("🚀 INICIANDO TESTE DA INTEGRAÇÃO ORCHESTRATOR")
    print("=" * 60)
    
    # Teste 1: Importação
    manager = teste_importacao()
    if not manager:
        print("❌ Falha na importação - parando testes")
        return
    
    # Teste 2: Orchestrator
    orchestrator = teste_orchestrator_import()
    
    # Teste 3: Inicialização
    init_result = await teste_inicializacao(manager)
    
    # Teste 4: Consulta
    query_result = await teste_consulta(manager)
    
    # Teste 5: Status
    status_result = teste_status(manager)
    
    # Sumário final
    print("\n" + "=" * 60)
    print("📊 SUMÁRIO DOS TESTES:")
    print(f"✅ Importação: {'OK' if manager else 'FALHA'}")
    print(f"✅ Orchestrator: {'OK' if orchestrator else 'FALHA'}")
    print(f"✅ Inicialização: {'OK' if init_result else 'FALHA'}")
    print(f"✅ Consulta: {'OK' if query_result else 'FALHA'}")
    print(f"✅ Status: {'OK' if status_result else 'FALHA'}")
    
    # Análise dos resultados
    if init_result and init_result.get('success'):
        score = init_result.get('score', 0)
        modules_active = init_result.get('modules_active', 0)
        modules_loaded = init_result.get('modules_loaded', 0)
        
        print(f"\n🎯 SCORE DE INTEGRAÇÃO: {score * 100:.1f}%")
        print(f"📊 MÓDULOS ATIVOS: {modules_active}/{modules_loaded}")
        
        if score >= 1.0:
            print("🎉 INTEGRAÇÃO PERFEITA!")
        elif score >= 0.8:
            print("✅ INTEGRAÇÃO BOA")
        else:
            print("⚠️ INTEGRAÇÃO PARCIAL")
    
    print("\n🏁 TESTE CONCLUÍDO")

if __name__ == "__main__":
    asyncio.run(main()) 