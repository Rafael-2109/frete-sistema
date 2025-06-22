#!/usr/bin/env python3
"""
Teste direto MCP v4.0 - Investigação
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
import traceback

def teste_direto():
    """Teste direto das funcionalidades"""
    
    print("🔍 TESTE DIRETO MCP v4.0")
    print("=" * 40)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Teste 1: Importar servidor
            print("\n1️⃣ Importando servidor MCP...")
            from app.claude_ai.mcp_v4_server import MCPv4Server
            print("✅ Servidor importado com sucesso")
            
            # Teste 2: Criar instância
            print("\n2️⃣ Criando instância...")
            server = MCPv4Server()
            print("✅ Instância criada com sucesso")
            
            # Teste 3: Teste de método direto
            print("\n3️⃣ Testando método direto...")
            result = server._status_sistema({})
            print("✅ Método _status_sistema funcionou")
            print(f"Primeiras linhas: {result[:200]}...")
            
            # Teste 4: Teste via query_intelligent
            print("\n4️⃣ Testando query_intelligent...")
            try:
                result = server.query_intelligent("Status do sistema")
                print(f"Resultado: {result}")
                
                if result and 'content' in result:
                    content = result['content']
                    if content and len(content) > 0:
                        text = content[0].get('text', 'Sem texto')
                        print(f"✅ SUCESSO! Resposta: {text[:100]}...")
                    else:
                        print("❌ Content vazio")
                else:
                    print("❌ Resultado inválido")
                    
            except Exception as e:
                print(f"❌ Erro em query_intelligent: {e}")
                traceback.print_exc()
            
            # Teste 5: Teste ML models
            print("\n5️⃣ Testando ML models...")
            try:
                from app.utils.ml_models_real import get_embarques_ativos
                embarques = get_embarques_ativos()
                print(f"✅ ML models funcionando - {len(embarques)} embarques")
            except Exception as e:
                print(f"❌ Erro ML models: {e}")
            
            # Teste 6: Teste NLP
            print("\n6️⃣ Testando NLP...")
            try:
                intent = server.nlp_processor.classify_intent("Status do sistema")
                entities = server.nlp_processor.extract_entities("Status do sistema")
                print(f"✅ NLP funcionando - Intent: {intent}, Entidades: {entities}")
            except Exception as e:
                print(f"❌ Erro NLP: {e}")
                
        except Exception as e:
            print(f"❌ ERRO GERAL: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    teste_direto() 