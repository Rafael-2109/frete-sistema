#!/usr/bin/env python3
"""
🔧 TESTE COM CONTEXTO FLASK - Verificar se o problema é de contexto
"""

import asyncio
import sys
import os

# Adicionar paths necessários
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

print("🔧 TESTE COM CONTEXTO FLASK")
print("=" * 60)

async def testar_com_contexto():
    """Testa com contexto Flask correto"""
    
    try:
        # Importar Flask app
        from app import create_app
        app = create_app()
        
        print("📱 CRIANDO CONTEXTO FLASK...")
        
        with app.app_context():
            print("✅ Contexto Flask ativo")
            
            # Importar função de transição
            from app.claude_transition import processar_consulta_transicao
            
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
            
            # Processar consulta com contexto Flask
            resposta = processar_consulta_transicao(consulta, user_context)
            
            print(f"\n✅ RESPOSTA COM CONTEXTO FLASK:")
            print(f"📏 Tamanho: {len(resposta)} caracteres")
            print(f"🔍 Tipo: {type(resposta)}")
            
            # Verificar se é resposta real ou fallback
            if "MODO FALLBACK" in str(resposta):
                print("⚠️ AINDA EM MODO FALLBACK")
                print("🔍 Verificando possíveis causas...")
                
                # Verificar ANTHROPIC_API_KEY
                anthropic_key = os.getenv('ANTHROPIC_API_KEY')
                if anthropic_key:
                    print(f"✅ ANTHROPIC_API_KEY configurada: {anthropic_key[:20]}...")
                else:
                    print("❌ ANTHROPIC_API_KEY não encontrada")
                
                # Verificar se sistema novo está ativo
                try:
                    from app.claude_ai_novo.integration.claude import get_claude_integration
                    claude = get_claude_integration()
                    print(f"✅ Sistema novo disponível: {type(claude)}")
                except Exception as e:
                    print(f"❌ Sistema novo não disponível: {e}")
                    
            else:
                print("✅ RESPOSTA REAL DO SISTEMA!")
                
            print(f"\n📋 RESPOSTA COMPLETA:")
            print(f"{str(resposta)[:500]}...")
            
            return True
            
    except Exception as e:
        print(f"❌ ERRO NO TESTE COM CONTEXTO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(testar_com_contexto())
    
    if success:
        print("\n🎉 TESTE COM CONTEXTO CONCLUÍDO!")
    else:
        print("\n❌ TESTE COM CONTEXTO FALHOU!") 