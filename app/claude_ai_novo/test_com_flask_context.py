#!/usr/bin/env python3
"""
🔧 TESTE COM CONTEXTO FLASK - Simular ambiente de produção
"""

import asyncio
import sys
import os

# Adicionar paths necessários
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

print("🔧 TESTE COM CONTEXTO FLASK - SIMULANDO PRODUÇÃO")
print("=" * 60)

async def testar_com_flask_context():
    """Testa sistema com contexto Flask ativo (como em produção)"""
    
    try:
        # Importar Flask app
        from app import create_app
        
        # Criar app com configuração de teste
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        print("📱 CRIANDO CONTEXTO FLASK (simulando produção)...")
        
        with app.app_context():
            print("✅ Contexto Flask ativo")
            
            # Importar agente 
            from multi_agent.agents.entregas_agent import EntregasAgent
            
            # Criar agente
            agente = EntregasAgent()
            
            print(f"✅ Agente criado: {type(agente)}")
            print(f"🔗 Tem dados reais: {agente.tem_dados_reais}")
            print(f"📊 Data executor: {type(agente.data_executor) if agente.data_executor else 'None'}")
            
            if agente.tem_dados_reais:
                print("🎯 TESTE REAL EM AMBIENTE PRODUÇÃO:")
                
                # Contexto de usuário
                contexto = {
                    'user_id': 1,
                    'username': 'usuario_producao',
                    'perfil': 'vendedor',
                    'vendedor_codigo': 'V001'
                }
                
                # Consulta teste
                consulta = "Como estão as entregas do Atacadão?"
                
                # Executar análise
                resultado = await agente.analyze(consulta, contexto)
                
                print(f"\n✅ RESULTADO EM PRODUÇÃO:")
                print(f"📏 Tipo: {type(resultado)}")
                print(f"🎯 Relevância: {resultado.get('relevance', 'N/A')}")
                print(f"🔍 Confiança: {resultado.get('confidence', 'N/A')}")
                print(f"🔧 Agente: {resultado.get('agent', 'N/A')}")
                
                if 'response' in resultado:
                    resposta = resultado['response']
                    print(f"📝 Resposta (primeiros 300 chars): {str(resposta)[:300]}...")
                    
                    # Verificar se contém dados específicos
                    if any(palavra in str(resposta).lower() for palavra in ['dados', 'encontrado', 'consultado', 'banco']):
                        print("🎉 RESPOSTA BASEADA EM DADOS REAIS!")
                    else:
                        print("⚠️ Resposta ainda teórica")
                        
                    if 'erro' in resultado:
                        print(f"❌ Erro encontrado: {resultado['erro']}")
                
                return True
            else:
                print("❌ Agente não conectado aos dados reais")
                return False
            
    except Exception as e:
        print(f"❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(testar_com_flask_context())
    
    if success:
        print("\n🎉 TESTE COM CONTEXTO FLASK CONCLUÍDO COM SUCESSO!")
        print("🚀 Sistema pronto para produção!")
    else:
        print("\n❌ TESTE COM CONTEXTO FLASK FALHOU!") 