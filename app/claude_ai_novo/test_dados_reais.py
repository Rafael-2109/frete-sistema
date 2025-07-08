#!/usr/bin/env python3
"""
🔧 TESTE DADOS REAIS - Verificar se agente está conectado aos dados
"""

import asyncio
import sys
import os

# Adicionar paths necessários
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

print("🔧 TESTE DADOS REAIS - AGENTE CONECTADO")
print("=" * 60)

async def testar_dados_reais():
    """Testa se o agente está conectado aos dados reais"""
    
    try:
        from multi_agent.agents.entregas_agent import EntregasAgent
        
        print("\n📱 TESTANDO AGENTE COM DADOS REAIS:")
        
        # Criar agente de entregas
        agente = EntregasAgent()
        
        # Verificar se tem executor de dados
        print(f"✅ Agente criado: {type(agente)}")
        print(f"🔗 Tem dados reais: {agente.tem_dados_reais}")
        print(f"📊 Data executor: {type(agente.data_executor) if agente.data_executor else 'None'}")
        
        # Teste de consulta
        consulta = "Como estão as entregas do Atacadão?"
        contexto = {
            'user_id': 1,
            'username': 'teste_user',
            'perfil': 'vendedor',
            'vendedor_codigo': 'V001'
        }
        
        print(f"\n📝 Testando consulta: {consulta}")
        
        # Processar consulta usando método correto
        resultado = await agente.analyze(consulta, contexto)
        
        print(f"\n✅ RESULTADO:")
        print(f"📏 Tipo: {type(resultado)}")
        print(f"🎯 Relevância: {resultado.get('relevance', 'N/A')}")
        print(f"🔍 Confiança: {resultado.get('confidence', 'N/A')}")
        print(f"📊 Dados reais: {resultado.get('dados_reais', False)}")
        
        if 'response' in resultado:
            resposta = resultado['response']
            print(f"📝 Resposta: {str(resposta)[:200]}...")
            
            # Verificar se resposta contém dados específicos
            if any(palavra in str(resposta).lower() for palavra in ['dados', 'encontrado', 'sistema', 'registro']):
                print("✅ RESPOSTA PARECE BASEADA EM DADOS!")
            else:
                print("⚠️ RESPOSTA AINDA PARECE TEÓRICA")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(testar_dados_reais())
    
    if success:
        print("\n🎉 TESTE DE DADOS REAIS CONCLUÍDO!")
    else:
        print("\n❌ TESTE DE DADOS REAIS FALHOU!") 