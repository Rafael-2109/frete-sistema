#!/usr/bin/env python3
"""
DIAGNÓSTICO COMPLETO MCP v4.0
Script para identificar exatamente onde está o problema
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
import traceback

def diagnóstico_mcp_v4():
    """Diagnóstico completo do MCP v4.0"""
    
    print("🔍 DIAGNÓSTICO COMPLETO MCP v4.0")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # 1. TESTE DE IMPORTAÇÃO
            print("\n1️⃣ TESTE DE IMPORTAÇÃO:")
            try:
                from app.claude_ai.mcp_v4_server import MCPv4Server, process_query
                print("✅ Importação MCPv4Server: OK")
                print("✅ Importação process_query: OK")
            except Exception as e:
                print(f"❌ Erro na importação: {e}")
                return
            
            # 2. TESTE DE INSTÂNCIA
            print("\n2️⃣ TESTE DE CRIAÇÃO DA INSTÂNCIA:")
            try:
                server = MCPv4Server()
                print("✅ MCPv4Server criado com sucesso")
                print(f"✅ Total de ferramentas: {len(server.tools)}")
                print(f"✅ Ferramentas disponíveis: {list(server.tools.keys())}")
            except Exception as e:
                print(f"❌ Erro na criação: {e}")
                traceback.print_exc()
                return
            
            # 3. TESTE NLP DIRETO
            print("\n3️⃣ TESTE NLP DIRETO:")
            consultas_teste = [
                "Status do sistema",
                "Como estão os fretes do Assai?", 
                "Transportadoras cadastradas",
                "Embarques ativos",
                "Análise de tendências"
            ]
            
            for consulta in consultas_teste:
                try:
                    intent = server.nlp_processor.classify_intent(consulta)
                    entities = server.nlp_processor.extract_entities(consulta)
                    
                    print(f"\n📝 Query: '{consulta}'")
                    print(f"🎯 Intent: {intent}")
                    print(f"🔍 Entities: {entities}")
                    
                    # Verificar se intent está no mapeamento
                    if intent in ['consulta_fretes', 'consulta_embarques', 'consulta_transportadoras', 'status_sistema', 
                                 'analise_tendencias', 'detectar_anomalias', 'otimizar_rotas', 'previsao_custos']:
                        print(f"✅ Intent mapeado corretamente")
                    else:
                        print(f"⚠️ Intent '{intent}' NÃO está no mapeamento!")
                        
                except Exception as e:
                    print(f"❌ Erro no NLP para '{consulta}': {e}")
            
            # 4. TESTE DE EXECUÇÃO DIRETA DAS FERRAMENTAS
            print("\n4️⃣ TESTE EXECUÇÃO DIRETA DAS FERRAMENTAS:")
            
            ferramentas_teste = {
                'status_sistema': {},
                'consultar_fretes': {'cliente': 'Assai'},
                'consultar_transportadoras': {},
                'consultar_embarques': {}
            }
            
            for ferramenta, args in ferramentas_teste.items():
                try:
                    if ferramenta in server.tools:
                        resultado = server.tools[ferramenta](args)
                        # Mostrar apenas primeiras linhas
                        linhas = resultado.split('\n')[:5]
                        preview = '\n'.join(linhas)
                        print(f"\n🔧 {ferramenta}: ✅ FUNCIONOU")
                        print(f"📄 Preview: {preview}...")
                    else:
                        print(f"\n🔧 {ferramenta}: ❌ NÃO ENCONTRADA")
                except Exception as e:
                    print(f"\n🔧 {ferramenta}: ❌ ERRO: {e}")
            
            # 5. TESTE DA FUNÇÃO query_intelligent
            print("\n5️⃣ TESTE query_intelligent:")
            
            try:
                resultado = server._query_intelligent({"query": "Como estão os fretes do Assai?"})
                linhas = resultado.split('\n')[:10]
                preview = '\n'.join(linhas)
                print(f"✅ query_intelligent funcionou!")
                print(f"📄 Preview resultado:\n{preview}...")
                
                # Verificar se sempre retorna status
                if "STATUS AVANÇADO" in resultado:
                    print(f"⚠️ PROBLEMA IDENTIFICADO: Sempre retorna status do sistema!")
                else:
                    print(f"✅ Resultado específico para a consulta")
                    
            except Exception as e:
                print(f"❌ Erro em query_intelligent: {e}")
                traceback.print_exc()
            
            # 6. TESTE process_query (função pública)
            print("\n6️⃣ TESTE process_query (função principal):")
            
            try:
                resultado = process_query("Transportadoras cadastradas")
                linhas = resultado.split('\n')[:10]
                preview = '\n'.join(linhas)
                print(f"✅ process_query funcionou!")
                print(f"📄 Preview resultado:\n{preview}...")
                
                # Verificar se sempre retorna status
                if "STATUS AVANÇADO" in resultado:
                    print(f"🔴 PROBLEMA CONFIRMADO: process_query sempre retorna status!")
                else:
                    print(f"✅ process_query funcionando corretamente")
                    
            except Exception as e:
                print(f"❌ Erro em process_query: {e}")
                traceback.print_exc()
            
            # 7. TESTE COMPLETO SIMULANDO API
            print("\n7️⃣ TESTE SIMULANDO CHAMADA API:")
            
            try:
                # Simular requisição como na API
                requisicao = {
                    "method": "tools/call",
                    "params": {
                        "name": "query_intelligent",
                        "arguments": {"query": "Transportadoras cadastradas"}
                    },
                    "id": 1
                }
                
                resposta = server.processar_requisicao(requisicao)
                
                if "result" in resposta:
                    texto = resposta["result"][0]["text"]
                    linhas = texto.split('\n')[:10]
                    preview = '\n'.join(linhas)
                    print(f"✅ Chamada API simulada funcionou!")
                    print(f"📄 Preview resposta:\n{preview}...")
                    
                    if "STATUS AVANÇADO" in texto:
                        print(f"🔴 CONFIRMADO: API sempre retorna status do sistema")
                    else:
                        print(f"✅ API funcionando corretamente")
                else:
                    print(f"❌ Resposta inválida da API: {resposta}")
                    
            except Exception as e:
                print(f"❌ Erro na simulação API: {e}")
                traceback.print_exc()
            
            print("\n" + "=" * 60)
            print("🏁 DIAGNÓSTICO CONCLUÍDO")
            
        except Exception as e:
            print(f"❌ Erro fatal no diagnóstico: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    diagnóstico_mcp_v4() 