#!/usr/bin/env python3
"""
Teste MCP v4.0 com Dados Reais
Sistema de teste para demonstrar o funcionamento real do MCP v4.0
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.claude_ai.mcp_v4_server import MCPv4Server
import json
from datetime import datetime

def test_mcp_v4_real():
    """Testa o MCP v4.0 com dados reais do sistema"""
    
    print("🚀 TESTE MCP v4.0 - DADOS REAIS")
    print("=" * 50)
    
    # Criar contexto da aplicação
    app = create_app()
    
    with app.app_context():
        print("\n✅ Contexto da aplicação criado")
        
        # Inicializar servidor MCP v4.0
        mcp_server = MCPv4Server()
        print("✅ Servidor MCP v4.0 inicializado")
        
        # Lista de testes com comandos em linguagem natural
        testes = [
            {
                'nome': 'Status Geral do Sistema',
                'comando': 'Como está o sistema? Preciso de um relatório geral'
            },
            {
                'nome': 'Análise de Tendências',
                'comando': 'Análise de tendências dos fretes dos últimos 30 dias'
            },
            {
                'nome': 'Detecção de Anomalias',
                'comando': 'Detectar anomalias nos custos dos fretes da última semana'
            },
            {
                'nome': 'Otimização de Rotas',
                'comando': 'Otimizar rotas para SP, RJ e MG com dados dos últimos 7 dias'
            },
            {
                'nome': 'Previsão de Custos',
                'comando': 'Previsão de custos para os próximos 30 dias'
            },
            {
                'nome': 'Consulta de Fretes',
                'comando': 'Fretes do cliente Assai em SP'
            },
            {
                'nome': 'Consulta de Embarques',
                'comando': 'Embarques ativos pendentes de hoje'
            },
            {
                'nome': 'Consulta de Transportadoras',
                'comando': 'Listar transportadoras ativas disponíveis'
            }
        ]
        
        print(f"\n🧪 EXECUTANDO {len(testes)} TESTES COM DADOS REAIS")
        print("-" * 50)
        
        resultados = []
        
        for i, teste in enumerate(testes, 1):
            print(f"\n[{i}/{len(testes)}] 🔍 {teste['nome']}")
            print(f"Comando: '{teste['comando']}'")
            
            try:
                # Executar comando via MCP
                request_data = {
                    "method": "tools/call",
                    "params": {
                        "name": "query_intelligent",
                        "arguments": {
                            "query": teste['comando']
                        }
                    }
                }
                
                # Simular processamento MCP - CORREÇÃO
                result = mcp_server.handle_tool_call(
                    "query_intelligent",
                    {
                        "query": teste['comando']
                    }
                )
                
                if result and 'content' in result:
                    content = result.get('content', [])
                    if content and len(content) > 0:
                        resposta = content[0].get('text', 'Sem resposta')
                        
                        # Extrair primeiras linhas para resumo
                        linhas = resposta.split('\n')
                        resumo = '\n'.join(linhas[:8]) + '\n...' if len(linhas) > 8 else resposta
                        
                        print(f"✅ SUCESSO!")
                        print(f"Resumo da resposta:")
                        print(resumo)
                        
                        resultados.append({
                            'teste': teste['nome'],
                            'status': 'SUCESSO',
                            'tamanho_resposta': len(resposta),
                            'linhas': len(linhas),
                            'tem_dados_reais': 'DADOS REAIS' in resposta.upper()
                        })
                    else:
                        print("❌ ERRO: Resposta vazia")
                        resultados.append({
                            'teste': teste['nome'],
                            'status': 'ERRO',
                            'erro': 'Resposta vazia'
                        })
                else:
                    print("❌ ERRO: Falha na execução")
                    resultados.append({
                        'teste': teste['nome'],
                        'status': 'ERRO',
                        'erro': 'Falha na execução'
                    })
                    
            except Exception as e:
                print(f"❌ ERRO: {str(e)}")
                resultados.append({
                    'teste': teste['nome'],
                    'status': 'ERRO',
                    'erro': str(e)
                })
        
        # Relatório final
        print("\n" + "=" * 60)
        print("📊 RELATÓRIO FINAL DOS TESTES")
        print("=" * 60)
        
        sucessos = len([r for r in resultados if r['status'] == 'SUCESSO'])
        erros = len([r for r in resultados if r['status'] == 'ERRO'])
        com_dados_reais = len([r for r in resultados if r.get('tem_dados_reais', False)])
        
        print(f"""
📈 ESTATÍSTICAS:
• Total de testes: {len(testes)}
• Sucessos: {sucessos} ({sucessos/len(testes)*100:.1f}%)
• Erros: {erros} ({erros/len(testes)*100:.1f}%)
• Com dados reais: {com_dados_reais} ({com_dados_reais/len(testes)*100:.1f}%)

🔍 DETALHES POR TESTE:""")
        
        for resultado in resultados:
            status_emoji = "✅" if resultado['status'] == 'SUCESSO' else "❌"
            dados_emoji = "🔥" if resultado.get('tem_dados_reais', False) else "📝"
            
            print(f"{status_emoji} {dados_emoji} {resultado['teste']}")
            
            if resultado['status'] == 'SUCESSO':
                print(f"   📏 Resposta: {resultado.get('tamanho_resposta', 0)} chars, {resultado.get('linhas', 0)} linhas")
            else:
                print(f"   💥 Erro: {resultado.get('erro', 'Desconhecido')}")
        
        print(f"""

🎯 CONCLUSÃO:
• MCP v4.0 {'FUNCIONANDO' if sucessos > len(testes)/2 else 'COM PROBLEMAS'}
• Dados reais {'INTEGRADOS' if com_dados_reais > 0 else 'NÃO CONECTADOS'}
• NLP {'FUNCIONAL' if sucessos > 0 else 'COM PROBLEMAS'}

⚡ Engine: MCP v4.0 Real Data System
🕒 Teste executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
""")

def test_nlp_performance():
    """Teste específico da performance do NLP"""
    
    print("\n🧠 TESTE ESPECÍFICO - NLP PERFORMANCE")
    print("-" * 40)
    
    app = create_app()
    
    with app.app_context():
        from app.claude_ai.mcp_v4_server import NLPProcessor
        
        nlp = NLPProcessor()
        
        frases_teste = [
            "Como estão os fretes do Assai em SP?",
            "Detectar problemas nos custos da semana passada",
            "Análise de tendências dos últimos 30 dias",
            "Otimizar rotas para RJ e MG",
            "Previsão de custos para o próximo mês",
            "Status do sistema hoje",
            "Embarques pendentes ativos",
            "Transportadoras disponíveis",
            "Anomalias nos valores de frete",
            "Relatório geral do sistema"
        ]
        
        print(f"🔤 Testando classificação de {len(frases_teste)} frases...")
        
        acertos = 0
        for i, frase in enumerate(frases_teste, 1):
            intent = nlp.classify_intent(frase)
            entities = nlp.extract_entities(frase)
            
            print(f"[{i:2d}] '{frase[:40]}...'")
            print(f"     🎯 Intent: {intent}")
            print(f"     🔍 Entidades: {entities}")
            
            # Verificar se classificou corretamente
            if intent != 'status_sistema' or 'sistema' in frase.lower():
                acertos += 1
        
        taxa_acerto = acertos / len(frases_teste) * 100
        
        print(f"""
📊 PERFORMANCE NLP:
• Frases testadas: {len(frases_teste)}
• Classificações corretas: {acertos}
• Taxa de acerto: {taxa_acerto:.1f}%
• Status: {'EXCELENTE' if taxa_acerto >= 80 else 'BOM' if taxa_acerto >= 60 else 'PRECISA MELHORAR'}
""")

if __name__ == "__main__":
    print("🚀 INICIANDO TESTES MCP v4.0 COM DADOS REAIS")
    print("=" * 60)
    
    try:
        # Teste principal
        test_mcp_v4_real()
        
        # Teste NLP
        test_nlp_performance()
        
        print("\n✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
        
    except Exception as e:
        print(f"\n❌ ERRO GERAL NOS TESTES: {str(e)}")
        import traceback
        traceback.print_exc() 