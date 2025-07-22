#!/usr/bin/env python3
"""
Script de teste para verificar o funcionamento do Claude AI Novo
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

def test_claude_ai_novo():
    """Teste completo do sistema Claude AI Novo"""
    
    print("🚀 Iniciando teste do Claude AI Novo...")
    
    # Criar contexto da aplicação
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Testar importação do sistema
            print("\n1️⃣ Testando importação...")
            from app.claude_ai_novo import get_claude_ai_instance
            print("   ✅ Importação bem-sucedida")
            
            # 2. Obter instância
            print("\n2️⃣ Obtendo instância...")
            instance = get_claude_ai_instance()
            print(f"   ✅ Instância criada: {type(instance)}")
            
            # 3. Verificar configuração API
            print("\n3️⃣ Verificando configuração...")
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                print(f"   ✅ API Key configurada: {api_key[:10]}...")
            else:
                print("   ⚠️ API Key não configurada - usando fallback")
            
            # 4. Teste de consultas
            print("\n4️⃣ Testando consultas...")
            
            consultas_teste = [
                "Como estão as entregas do Atacadão?",
                "Quais os fretes para São Paulo?",
                "Relatório de hoje",
                "Status dos pedidos",
                "Teste genérico"
            ]
            
            for i, consulta in enumerate(consultas_teste, 1):
                print(f"\n   🔍 Teste {i}: {consulta}")
                try:
                    resultado = instance.processar_consulta_sync(consulta)
                    
                    if isinstance(resultado, dict):
                        if resultado.get('success'):
                            resposta = resultado.get('response', 'Sem resposta')
                            print(f"   ✅ Sucesso: {len(resposta)} caracteres")
                            print(f"      📝 Início: {resposta[:100]}...")
                        else:
                            print(f"   ❌ Erro: {resultado.get('response', 'Erro desconhecido')}")
                    else:
                        print(f"   📝 Resposta direta: {len(str(resultado))} caracteres")
                        
                except Exception as e:
                    print(f"   ❌ Erro na consulta: {e}")
            
            print("\n🎉 Teste concluído!")
            
        except Exception as e:
            print(f"❌ Erro no teste: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_claude_ai_novo()