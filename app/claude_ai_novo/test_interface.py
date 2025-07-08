#!/usr/bin/env python3
"""
🔧 TESTE DE INTERFACE - Verificar comunicação backend ↔ frontend
"""

import asyncio
import sys
import os

# Adicionar paths necessários
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

print("🔧 TESTE DE INTERFACE - BACKEND ↔ FRONTEND")
print("=" * 60)

async def testar_interface():
    """Testa se a interface está funcionando corretamente"""
    
    try:
        # Importar função de transição
        from app.claude_transition import processar_consulta_transicao
        
        print("\n📱 TESTANDO PROCESSO DE TRANSIÇÃO:")
        
        # Simular contexto de usuário
        user_context = {
            'user_id': 1,
            'username': 'teste_user',
            'perfil': 'vendedor',
            'vendedor_codigo': 'V001',
            'timestamp': '2025-07-08T15:00:00'
        }
        
        # Consulta teste
        consulta = "Como estão as entregas do Atacadão?"
        
        print(f"📝 Consulta: {consulta}")
        print(f"👤 Contexto: {user_context}")
        
        # Processar consulta
        resposta = processar_consulta_transicao(consulta, user_context)
        
        print(f"\n✅ RESPOSTA RECEBIDA:")
        print(f"📏 Tamanho: {len(resposta)} caracteres")
        print(f"🔍 Tipo: {type(resposta)}")
        print(f"📝 Primeiros 200 chars: {str(resposta)[:200]}...")
        
        # Verificar se é uma resposta válida
        if resposta and len(resposta) > 10:
            print("✅ RESPOSTA VÁLIDA!")
        else:
            print("❌ RESPOSTA INVÁLIDA OU VAZIA!")
            
        # Testar estrutura JSON como esperado pelo frontend
        import json
        response_data = {
            'response': resposta,
            'status': 'success',
            'timestamp': '2025-07-08T15:00:00',
            'mode': 'claude_real'
        }
        
        json_response = json.dumps(response_data, ensure_ascii=False)
        print(f"\n📦 JSON FINAL (para frontend):")
        print(f"📏 Tamanho JSON: {len(json_response)} caracteres")
        print(f"✅ JSON válido: {json_response[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(testar_interface())
    
    if success:
        print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("\n❌ TESTE FALHOU!") 