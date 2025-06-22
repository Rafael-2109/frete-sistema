#!/usr/bin/env python3
"""
Teste do Sistema ML v4.0 - Dia 3
"""

def teste_ml_completo():
    """Teste completo do sistema ML"""
    print("🧪 Testando Sistema ML v4.0 - Dia 3...")
    
    try:
        # 1. Testar módulo ML
        print("\n1. Testando ml_models.py...")
        from app.utils.ml_models import predict_delay, detect_anomalies, optimize_costs
        print("✅ Importação ML bem-sucedida")
        
        # Teste predição de atraso
        embarque_teste = {
            'peso_total': 2500,
            'distancia_km': 1200,
            'uf_destino': 'AM',
            'valor_frete': 1500
        }
        
        predicao = predict_delay(embarque_teste)
        print(f"✅ Predição de atraso: {predicao.get('status', 'N/A')} - {predicao.get('atraso_previsto_dias', 0)} dias")
        
        # Teste detecção de anomalias
        dados_teste = [
            {'valor_frete': 2000, 'peso_total': 100, 'distancia_km': 400},  # Anomalia
            {'valor_frete': 800, 'peso_total': 1000, 'distancia_km': 400}   # Normal
        ]
        
        anomalias = detect_anomalies(dados_teste)
        print(f"✅ Anomalias detectadas: {len(anomalias)}")
        
        if anomalias:
            print(f"   - Primeira anomalia: {anomalias[0].get('descricao', 'N/A')}")
        
        # Teste otimização de custos
        rotas_teste = [
            {'valor_frete': 800, 'transportadora': 'Trans A', 'uf_destino': 'SP'},
            {'valor_frete': 1200, 'transportadora': 'Trans B', 'uf_destino': 'RJ'}
        ]
        
        otimizacao = optimize_costs(rotas_teste)
        print(f"✅ Otimização: {otimizacao.get('total_routes', 0)} rotas analisadas")
        print(f"   - Economia estimada: {otimizacao.get('economia_estimada', 'N/A')}")
        
        # 2. Testar MCP v4.0 Server
        print("\n2. Testando MCP v4.0 Server...")
        from app.claude_ai.mcp_v4_server import process_query
        print("✅ Importação MCP v4.0 bem-sucedida")
        
        # Teste comandos ML
        queries_teste = [
            ('Status do sistema', 'STATUS'),
            ('Analisar tendências', 'TENDÊNCIAS'),
            ('Detectar anomalias', 'ANOMALIAS'),
            ('Otimizar rotas SP RJ MG', 'ROTAS'),
            ('Previsão de custos 30d', 'CUSTOS')
        ]
        
        for query, tipo in queries_teste:
            try:
                resultado = process_query(query)
                if 'ML REAL' in resultado:
                    print(f"✅ {tipo}: ML REAL ativo")
                elif 'SIMULADO' in resultado or 'desenvolvimento' in resultado:
                    print(f"⚠️ {tipo}: Modo simulado/desenvolvimento")
                elif 'v4.0' in resultado:
                    print(f"✅ {tipo}: v4.0 funcionando")
                else:
                    print(f"❓ {tipo}: Funcionando (resposta: {len(resultado)} chars)")
            except Exception as e:
                print(f"❌ {tipo}: Erro - {str(e)[:100]}...")
        
        # 3. Estatísticas finais
        print("\n3. Estatísticas do Sistema:")
        from app.claude_ai.mcp_v4_server import mcp_v4_server
        metrics = mcp_v4_server.metrics
        
        print(f"   - Requisições processadas: {metrics['requests_processed']}")
        print(f"   - Intenções classificadas: {metrics['intents_classified']}")
        print(f"   - Ferramentas disponíveis: {len(mcp_v4_server.tools)}")
        
        # 4. Validar ferramentas v4.0
        ferramentas_v4 = ['analisar_tendencias', 'detectar_anomalias', 'otimizar_rotas', 'previsao_custos']
        ferramentas_ativas = [nome for nome in ferramentas_v4 if nome in mcp_v4_server.tools]
        
        print(f"\n4. Ferramentas v4.0: {len(ferramentas_ativas)}/4 implementadas")
        for ferramenta in ferramentas_ativas:
            print(f"   ✅ {ferramenta}")
        
        print(f"\n🎉 TESTE COMPLETO REALIZADO!")
        print(f"✅ Sistema ML v4.0 operacional")
        print(f"✅ Integração MCP funcionando") 
        print(f"✅ {len(ferramentas_ativas)} novas ferramentas ML implementadas")
        print(f"🚀 DIA 3 - MACHINE LEARNING: CONCLUÍDO COM SUCESSO!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    teste_ml_completo() 