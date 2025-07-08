#!/usr/bin/env python3
"""
🧪 TESTE TODOS OS AGENTES SMART BASE

Script para testar TODOS os agentes atualizados para SmartBaseAgent
e validar que possuem TODAS as capacidades avançadas.

CAPACIDADES TESTADAS:
✅ Dados reais do banco PostgreSQL
✅ Claude 4 Sonnet real (não simulado)
✅ Cache Redis para performance
✅ Sistema de contexto conversacional
✅ Mapeamento semântico inteligente
✅ ML Models para predições
✅ Sistema de logs estruturados
✅ Análise de tendências temporais
✅ Sistema de validação e confiança
✅ Sugestões inteligentes contextuais
✅ Alertas operacionais automáticos
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# Adicionar caminho para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Simular contexto Flask para testes
class MockFlaskContext:
    def __init__(self):
        self.username = "teste_usuario"
        self.user_id = "123"
        self.profile = "admin"

# Configurar contexto mock
mock_context = MockFlaskContext()

def testar_import_agentes():
    """Testa se todos os agentes podem ser importados corretamente"""
    print("📦 Testando imports dos agentes...")
    
    resultados = {}
    
    # Testar importação de cada agente
    agentes_para_testar = [
        ('EntregasAgent', 'multi_agent.agents.entregas_agent'),
        ('EmbarquesAgent', 'multi_agent.agents.embarques_agent'),
        ('FinanceiroAgent', 'multi_agent.agents.financeiro_agent'),
        ('PedidosAgent', 'multi_agent.agents.pedidos_agent'),
        ('FretesAgent', 'multi_agent.agents.fretes_agent'),
        ('SmartBaseAgent', 'multi_agent.agents.smart_base_agent')
    ]
    
    for nome_agente, modulo in agentes_para_testar:
        try:
            # Import dinâmico
            from importlib import import_module
            modulo_importado = import_module(modulo)
            classe_agente = getattr(modulo_importado, nome_agente)
            
            resultados[nome_agente] = {
                'importado': True,
                'classe': classe_agente,
                'erro': None
            }
            print(f"✅ {nome_agente}: Importado com sucesso")
            
        except Exception as e:
            resultados[nome_agente] = {
                'importado': False,
                'classe': None,
                'erro': str(e)
            }
            print(f"❌ {nome_agente}: Erro no import - {e}")
    
    return resultados

def testar_inicializacao_agentes(resultados_import: Dict[str, Any]):
    """Testa se todos os agentes podem ser inicializados"""
    print("\n🔧 Testando inicialização dos agentes...")
    
    resultados = {}
    
    agentes_especializados = [
        'EntregasAgent',
        'EmbarquesAgent', 
        'FinanceiroAgent',
        'PedidosAgent',
        'FretesAgent'
    ]
    
    for nome_agente in agentes_especializados:
        if not resultados_import[nome_agente]['importado']:
            print(f"⏭️ {nome_agente}: Pulando (erro no import)")
            continue
            
        try:
            # Inicializar agente
            classe_agente = resultados_import[nome_agente]['classe']
            agente = classe_agente()
            
            resultados[nome_agente] = {
                'inicializado': True,
                'agente': agente,
                'erro': None
            }
            print(f"✅ {nome_agente}: Inicializado com sucesso")
            
        except Exception as e:
            resultados[nome_agente] = {
                'inicializado': False,
                'agente': None,
                'erro': str(e)
            }
            print(f"❌ {nome_agente}: Erro na inicialização - {e}")
    
    return resultados

def testar_capacidades_agentes(resultados_init: Dict[str, Any]):
    """Testa se todos os agentes têm as capacidades SmartBaseAgent"""
    print("\n🧠 Testando capacidades dos agentes...")
    
    resultados = {}
    
    # Capacidades esperadas
    capacidades_esperadas = [
        'tem_dados_reais',
        'tem_claude_real',
        'tem_cache',
        'tem_contexto',
        'tem_mapeamento',
        'tem_ml_models',
        'tem_logs_estruturados',
        'tem_trend_analyzer',
        'tem_validation',
        'tem_suggestions',
        'tem_alerts'
    ]
    
    for nome_agente, info in resultados_init.items():
        if not info['inicializado']:
            print(f"⏭️ {nome_agente}: Pulando (erro na inicialização)")
            continue
            
        try:
            agente = info['agente']
            
            # Verificar se é SmartBaseAgent
            from multi_agent.agents.smart_base_agent import SmartBaseAgent
            is_smart_agent = isinstance(agente, SmartBaseAgent)
            
            # Verificar capacidades
            capacidades_encontradas = []
            for capacidade in capacidades_esperadas:
                if hasattr(agente, capacidade):
                    status = getattr(agente, capacidade)
                    capacidades_encontradas.append({
                        'nome': capacidade,
                        'status': status,
                        'tipo': type(status).__name__
                    })
            
            # Verificar método get_agent_status
            status_completo = None
            if hasattr(agente, 'get_agent_status'):
                status_completo = agente.get_agent_status()
            
            resultados[nome_agente] = {
                'is_smart_agent': is_smart_agent,
                'capacidades_encontradas': capacidades_encontradas,
                'total_capacidades': len(capacidades_encontradas),
                'status_completo': status_completo,
                'erro': None
            }
            
            print(f"✅ {nome_agente}: SmartBaseAgent={is_smart_agent}, Capacidades={len(capacidades_encontradas)}/11")
            
        except Exception as e:
            resultados[nome_agente] = {
                'is_smart_agent': False,
                'capacidades_encontradas': [],
                'total_capacidades': 0,
                'status_completo': None,
                'erro': str(e)
            }
            print(f"❌ {nome_agente}: Erro ao testar capacidades - {e}")
    
    return resultados

async def testar_consultas_agentes(resultados_capacidades: Dict[str, Any]):
    """Testa se os agentes conseguem processar consultas"""
    print("\n🔍 Testando consultas dos agentes...")
    
    resultados = {}
    
    # Consultas de teste por agente
    consultas_teste = {
        'EntregasAgent': "Quantas entregas foram realizadas hoje?",
        'EmbarquesAgent': "Quais embarques estão pendentes?",
        'FinanceiroAgent': "Qual o faturamento do mês?",
        'PedidosAgent': "Quantos pedidos estão em aberto?",
        'FretesAgent': "Qual o custo médio dos fretes?"
    }
    
    for nome_agente, consulta in consultas_teste.items():
        if nome_agente not in resultados_capacidades:
            print(f"⏭️ {nome_agente}: Pulando (não disponível)")
            continue
            
        try:
            # Buscar agente inicializado
            agente = None
            for resultado in resultados_capacidades.values():
                if resultado.get('agente') and resultado['agente'].__class__.__name__ == nome_agente:
                    agente = resultado['agente']
                    break
            
            if not agente:
                print(f"⏭️ {nome_agente}: Agente não encontrado")
                continue
            
            # Contexto de teste
            contexto = {
                'username': mock_context.username,
                'user_id': mock_context.user_id,
                'profile': mock_context.profile,
                'timestamp': datetime.now().isoformat()
            }
            
            # Processar consulta
            resposta = await agente.analyze(consulta, contexto)
            
            resultados[nome_agente] = {
                'consulta': consulta,
                'processou': True,
                'resposta': resposta,
                'erro': None
            }
            
            print(f"✅ {nome_agente}: Consulta processada - Confiança: {resposta.get('confidence', 'N/A')}")
            
        except Exception as e:
            resultados[nome_agente] = {
                'consulta': consulta,
                'processou': False,
                'resposta': None,
                'erro': str(e)
            }
            print(f"❌ {nome_agente}: Erro na consulta - {e}")
    
    return resultados

def gerar_relatorio_completo(resultados_todos: Dict[str, Any]):
    """Gera relatório completo dos testes"""
    print("\n📋 RELATÓRIO COMPLETO DOS TESTES")
    print("=" * 60)
    
    # Estatísticas gerais
    total_agentes = 5
    agentes_importados = sum(1 for r in resultados_todos['imports'].values() if r['importado'])
    agentes_inicializados = sum(1 for r in resultados_todos['inicializacao'].values() if r['inicializado'])
    agentes_smart = sum(1 for r in resultados_todos['capacidades'].values() if r['is_smart_agent'])
    agentes_consultando = sum(1 for r in resultados_todos['consultas'].values() if r['processou'])
    
    print(f"📊 ESTATÍSTICAS GERAIS:")
    print(f"• Total de agentes: {total_agentes}")
    print(f"• Agentes importados: {agentes_importados}/{total_agentes} ({agentes_importados/total_agentes*100:.1f}%)")
    print(f"• Agentes inicializados: {agentes_inicializados}/{total_agentes} ({agentes_inicializados/total_agentes*100:.1f}%)")
    print(f"• Agentes SmartBaseAgent: {agentes_smart}/{total_agentes} ({agentes_smart/total_agentes*100:.1f}%)")
    print(f"• Agentes processando consultas: {agentes_consultando}/{total_agentes} ({agentes_consultando/total_agentes*100:.1f}%)")
    
    # Detalhes por agente
    print(f"\n📋 DETALHES POR AGENTE:")
    
    agentes = ['EntregasAgent', 'EmbarquesAgent', 'FinanceiroAgent', 'PedidosAgent', 'FretesAgent']
    
    for agente in agentes:
        print(f"\n🤖 {agente}:")
        
        # Import
        import_ok = resultados_todos['imports'].get(agente, {}).get('importado', False)
        print(f"  • Import: {'✅' if import_ok else '❌'}")
        
        # Inicialização
        init_ok = resultados_todos['inicializacao'].get(agente, {}).get('inicializado', False)
        print(f"  • Inicialização: {'✅' if init_ok else '❌'}")
        
        # SmartBaseAgent
        smart_ok = resultados_todos['capacidades'].get(agente, {}).get('is_smart_agent', False)
        print(f"  • SmartBaseAgent: {'✅' if smart_ok else '❌'}")
        
        # Capacidades
        capacidades = resultados_todos['capacidades'].get(agente, {}).get('total_capacidades', 0)
        print(f"  • Capacidades: {capacidades}/11")
        
        # Consultas
        consulta_ok = resultados_todos['consultas'].get(agente, {}).get('processou', False)
        print(f"  • Consultas: {'✅' if consulta_ok else '❌'}")
    
    # Capacidades detalhadas
    print(f"\n🧠 CAPACIDADES DETALHADAS:")
    
    capacidades_nomes = {
        'tem_dados_reais': 'Dados Reais PostgreSQL',
        'tem_claude_real': 'Claude 4 Sonnet Real',
        'tem_cache': 'Cache Redis',
        'tem_contexto': 'Contexto Conversacional',
        'tem_mapeamento': 'Mapeamento Semântico',
        'tem_ml_models': 'ML Models',
        'tem_logs_estruturados': 'Logs Estruturados',
        'tem_trend_analyzer': 'Análise Tendências',
        'tem_validation': 'Sistema Validação',
        'tem_suggestions': 'Sugestões Inteligentes',
        'tem_alerts': 'Sistema Alertas'
    }
    
    for cap_key, cap_nome in capacidades_nomes.items():
        agentes_com_cap = 0
        for agente in agentes:
            caps = resultados_todos['capacidades'].get(agente, {}).get('capacidades_encontradas', [])
            tem_cap = any(c['nome'] == cap_key for c in caps)
            if tem_cap:
                agentes_com_cap += 1
        
        print(f"  • {cap_nome}: {agentes_com_cap}/{len(agentes)} agentes")
    
    # Resumo final
    print(f"\n🎯 RESUMO FINAL:")
    
    if agentes_smart == total_agentes:
        print("✅ SUCESSO TOTAL: Todos os agentes são SmartBaseAgent!")
    elif agentes_smart > 0:
        print(f"⚠️ SUCESSO PARCIAL: {agentes_smart}/{total_agentes} agentes são SmartBaseAgent")
    else:
        print("❌ FALHA: Nenhum agente é SmartBaseAgent")
    
    if agentes_consultando == total_agentes:
        print("✅ FUNCIONALIDADE TOTAL: Todos os agentes processam consultas!")
    elif agentes_consultando > 0:
        print(f"⚠️ FUNCIONALIDADE PARCIAL: {agentes_consultando}/{total_agentes} agentes processam consultas")
    else:
        print("❌ FUNCIONALIDADE FALHA: Nenhum agente processa consultas")
    
    # Calcular score geral
    score_geral = (agentes_smart + agentes_consultando) / (total_agentes * 2) * 100
    print(f"\n📊 SCORE GERAL: {score_geral:.1f}%")
    
    if score_geral >= 80:
        print("🎉 EXCELENTE: Sistema pronto para produção!")
    elif score_geral >= 60:
        print("👍 BOM: Sistema funcional com algumas limitações")
    elif score_geral >= 40:
        print("⚠️ REGULAR: Sistema precisa de ajustes")
    else:
        print("❌ CRÍTICO: Sistema precisa de correções importantes")

async def main():
    """Função principal dos testes"""
    print("🚀 INICIANDO TESTES COMPLETOS DOS AGENTES SMART BASE")
    print("=" * 70)
    
    resultados_todos = {}
    
    # Teste 1: Imports
    resultados_todos['imports'] = testar_import_agentes()
    
    # Teste 2: Inicialização
    resultados_todos['inicializacao'] = testar_inicializacao_agentes(resultados_todos['imports'])
    
    # Teste 3: Capacidades
    resultados_todos['capacidades'] = testar_capacidades_agentes(resultados_todos['inicializacao'])
    
    # Teste 4: Consultas
    resultados_todos['consultas'] = await testar_consultas_agentes(resultados_todos['capacidades'])
    
    # Relatório final
    gerar_relatorio_completo(resultados_todos)
    
    print("\n🏁 TESTES CONCLUÍDOS!")

if __name__ == "__main__":
    asyncio.run(main()) 