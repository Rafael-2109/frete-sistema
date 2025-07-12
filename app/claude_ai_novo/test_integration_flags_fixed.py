#!/usr/bin/env python3
"""
🧪 TESTE DAS FLAGS CORRIGIDAS
============================

Verifica se o IntegrationManager agora detecta corretamente
as variáveis de ambiente e se o SmartBaseAgent recebe as flags corretas.
"""

import os
import sys
import asyncio
from pathlib import Path

# Adicionar o diretório raiz ao path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Simular variáveis de ambiente (como no Render)
os.environ['DATABASE_URL'] = 'postgresql://user:pass@host/db'
os.environ['ANTHROPIC_API_KEY'] = 'sk-test-key'
os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'


async def test_integration_flags():
    """Testa se as flags estão sendo detectadas corretamente"""
    
    print("🧪 TESTANDO FLAGS DO INTEGRATION MANAGER")
    print("=" * 60)
    
    # 1. Testar IntegrationManager
    print("\n1️⃣ Testando IntegrationManager...")
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        
        manager = get_integration_manager()
        status = manager.get_system_status()
        
        print(f"✅ IntegrationManager carregado")
        print(f"📊 data_provider_available: {status.get('data_provider_available', False)}")
        print(f"🤖 claude_integration_available: {status.get('claude_integration_available', False)}")
        
        # Verificar se as flags estão corretas
        assert status.get('data_provider_available') == True, "DATABASE_URL não detectada!"
        assert status.get('claude_integration_available') == True, "ANTHROPIC_API_KEY não detectada!"
        
        print("✅ Flags detectadas corretamente!")
        
    except Exception as e:
        print(f"❌ Erro no IntegrationManager: {e}")
        return False
    
    # 2. Testar SmartBaseAgent
    print("\n2️⃣ Testando SmartBaseAgent...")
    try:
        from app.claude_ai_novo.coordinators.domain_agents.smart_base_agent import SmartBaseAgent
        from app.claude_ai_novo.utils.agent_types import AgentType
        
        # Criar um agente de teste
        agent = SmartBaseAgent(AgentType.ENTREGAS)
        
        print(f"✅ SmartBaseAgent criado")
        print(f"📊 tem_dados_reais: {agent.tem_dados_reais}")
        print(f"🤖 tem_claude_real: {agent.tem_claude_real}")
        print(f"🔧 tem_integration_manager: {agent.tem_integration_manager}")
        
        # Verificar se as flags foram propagadas
        assert agent.tem_dados_reais == True, "Dados reais não detectados no agent!"
        assert agent.tem_claude_real == True, "Claude real não detectado no agent!"
        
        print("✅ Flags propagadas corretamente para o agent!")
        
        # Testar status completo
        print("\n3️⃣ Status completo do agent:")
        agent_status = agent.get_agent_status()
        print(f"   Mode: {agent_status['mode']}")
        print(f"   Integration disponível: {agent_status['integration_manager_available']}")
        print(f"   Dados disponíveis: {agent_status['data_available']}")
        print(f"   Claude disponível: {agent_status['claude_available']}")
        
    except Exception as e:
        print(f"❌ Erro no SmartBaseAgent: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. Testar processamento real
    print("\n4️⃣ Testando processamento com dados reais...")
    try:
        # Testar uma consulta
        result = await agent.analyze(
            "Quantas entregas temos hoje?",
            {'username': 'teste', 'user_id': 1}
        )
        
        print(f"✅ Consulta processada!")
        print(f"   Tipo de resposta: {type(result)}")
        print(f"   Chaves da resposta: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        
        # Verificar se não é resposta genérica
        if isinstance(result, dict) and 'response' in result:
            response_text = result['response']
            is_generic = "Modo Básico" in response_text or "Sistema IntegrationManager não disponível" in response_text
            
            if is_generic:
                print("⚠️ AVISO: Resposta ainda é genérica!")
            else:
                print("✅ Resposta não é genérica - sistema usando recursos reais!")
        
    except Exception as e:
        print(f"❌ Erro no processamento: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ TESTE CONCLUÍDO!")
    
    # Limpar variáveis de teste
    del os.environ['DATABASE_URL']
    del os.environ['ANTHROPIC_API_KEY']
    

if __name__ == "__main__":
    asyncio.run(test_integration_flags()) 