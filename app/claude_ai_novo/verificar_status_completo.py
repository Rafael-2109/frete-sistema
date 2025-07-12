#!/usr/bin/env python3
"""
Verifica status completo do sistema Claude AI Novo
"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def verificar_status():
    """Verifica status de todos os componentes"""
    print("\n🔍 VERIFICANDO STATUS DO SISTEMA CLAUDE AI NOVO\n")
    
    # 1. Variáveis de ambiente
    print("1️⃣ VARIÁVEIS DE AMBIENTE:")
    print(f"   DATABASE_URL: {'✅ Configurada' if os.getenv('DATABASE_URL') else '❌ Não configurada'}")
    print(f"   ANTHROPIC_API_KEY: {'✅ Configurada' if os.getenv('ANTHROPIC_API_KEY') else '❌ Não configurada'}")
    print(f"   REDIS_URL: {'✅ Configurada' if os.getenv('REDIS_URL') else '❌ Não configurada'}")
    
    # 2. IntegrationManager
    print("\n2️⃣ INTEGRATION MANAGER:")
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        manager = get_integration_manager()
        status = manager.get_integration_status()
        print(f"   Orchestrator ativo: {status.get('orchestrator_active', False)}")
        print(f"   Dados disponíveis: {status.get('data_provider_available', False)}")
        print(f"   Claude disponível: {status.get('claude_integration_available', False)}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 3. SessionOrchestrator
    print("\n3️⃣ SESSION ORCHESTRATOR:")
    try:
        from app.claude_ai_novo.orchestrators.session_orchestrator import SessionOrchestrator
        session_orch = SessionOrchestrator()
        print(f"   IntegrationManager conectado: {hasattr(session_orch, 'integration_manager') and session_orch.integration_manager is not None}")
        print(f"   LearningCore disponível: {session_orch.learning_core is not None}")
        print(f"   SecurityGuard disponível: {session_orch.security_guard is not None}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 4. Loaders
    print("\n4️⃣ DATA LOADERS:")
    try:
        from app.claude_ai_novo.loaders.domain import (
            get_pedidos_loader, get_fretes_loader, get_entregas_loader
        )
        pedidos_loader = get_pedidos_loader()
        print(f"   PedidosLoader: {'✅ Real' if not getattr(pedidos_loader, 'mock_mode', True) else '❌ Mock'}")
        
        fretes_loader = get_fretes_loader()
        print(f"   FretesLoader: {'✅ Real' if not getattr(fretes_loader, 'mock_mode', True) else '❌ Mock'}")
        
        entregas_loader = get_entregas_loader()
        print(f"   EntregasLoader: {'✅ Real' if not getattr(entregas_loader, 'mock_mode', True) else '❌ Mock'}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print("\n✅ Verificação concluída!\n")

if __name__ == "__main__":
    verificar_status()
