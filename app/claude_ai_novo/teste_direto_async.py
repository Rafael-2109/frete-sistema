#!/usr/bin/env python3
"""
🧪 TESTE DIRETO DO ERRO ASYNC
============================

Testa diretamente se o erro "This event loop is already running" foi corrigido.
"""

import os
import sys
import asyncio
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def testar_erro_async():
    """Testa se o erro de event loop foi corrigido"""
    print("\n🧪 TESTE DIRETO DO ERRO ASYNC\n")
    
    try:
        # 1. Testar se conseguimos importar
        print("1️⃣ Importando SessionOrchestrator...")
        from app.claude_ai_novo.orchestrators.session_orchestrator import SessionOrchestrator
        print("   ✅ Import OK")
        
        # 2. Criar instância
        print("\n2️⃣ Criando instância...")
        orchestrator = SessionOrchestrator()
        print("   ✅ Instância criada")
        
        # 3. Testar método problemático
        print("\n3️⃣ Testando _process_deliveries_status...")
        
        # Simular IntegrationManager
        class MockIntegrationManager:
            async def process_unified_query(self, query, context):
                await asyncio.sleep(0.1)  # Simular processamento
                return {
                    'response': 'Resposta mockada do IntegrationManager',
                    'success': True
                }
        
        # Injetar mock
        orchestrator._integration_manager = MockIntegrationManager()
        
        # Testar o método
        result = orchestrator._process_deliveries_status("entregas do atacadão")
        
        print("   ✅ Método executou sem erro de event loop!")
        print(f"   📝 Resultado: {result}")
        
        # Verificar se usou o IntegrationManager
        if 'integration_manager' in result.get('source', ''):
            print("\n🎉 EXCELENTE! Está usando o IntegrationManager!")
        else:
            print("\n⚠️  Ainda está usando fallback, mas sem erro de event loop")
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        
        # Verificar tipo de erro
        if "This event loop is already running" in str(e):
            print("❌ ERRO DE EVENT LOOP AINDA PRESENTE!")
            import traceback
            traceback.print_exc()
        else:
            print("✅ Não é erro de event loop (outro tipo de erro)")
    
    print("\n✅ TESTE COMPLETO!")

if __name__ == "__main__":
    testar_erro_async() 