#!/usr/bin/env python3
"""
Script de debug para testar o sistema claude_ai_novo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import json
from datetime import datetime

async def test_system():
    """Testa o sistema com uma query real"""
    
    # Criar contexto Flask
    from app import create_app
    app = create_app()
    
    with app.app_context():
        # Importar e testar o sistema
        from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager
        
        orchestrator = OrchestratorManager()
        
        # Query de teste
        query = "Como estão as entregas do Atacadão?"
        context = {
            "user_id": "test_user",
            "timestamp": datetime.now().isoformat()
        }
        
        print("🔍 Testando sistema com query:", query)
        print("-" * 60)
        
        # Verificar SecurityGuard
        from app.claude_ai_novo.security.security_guard import get_security_guard
        sg = get_security_guard()
        print(f"\n🔐 SecurityGuard Status:")
        print(f"  - Em produção: {sg.is_production}")
        print(f"  - Sistema novo ativo: {sg.new_system_active}")
        print(f"  - Validate access: {sg.validate_user_access('intelligent_query')}")
        
        # Processar query
        result = await orchestrator.process_query(query, context)
        
        # Mostrar resultado completo
        print("\n📊 RESULTADO COMPLETO:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Extrair resposta
        print("\n🎯 TENTANDO EXTRAIR RESPOSTA:")
        
        if isinstance(result, dict):
            # Verificar campos comuns
            campos = ['result', 'response', 'text', 'message', 'response_result']
            
            for campo in campos:
                if campo in result:
                    print(f"  - Campo '{campo}' encontrado:", type(result[campo]))
                    if isinstance(result[campo], dict):
                        print(f"    Sub-campos: {list(result[campo].keys())}")
                        
                        # Procurar mais profundo
                        for subcampo in ['response', 'text', 'result', 'message']:
                            if subcampo in result[campo]:
                                print(f"      - '{subcampo}': {str(result[campo][subcampo])[:100]}...")
        
        print("\n✅ Teste concluído!")

if __name__ == "__main__":
    asyncio.run(test_system())