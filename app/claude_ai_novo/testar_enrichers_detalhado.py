#!/usr/bin/env python3
"""
Script para testar detalhadamente o EnricherManager
"""

import logging
import json
from datetime import datetime
import sys
import os

# Adicionar o diretório pai ao path para imports funcionarem
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def testar_criacao_enricher_manager():
    """Testa a criação do EnricherManager"""
    print("\n🔍 TESTE 1: Criação do EnricherManager")
    print("=" * 50)
    
    try:
        from claude_ai_novo.enrichers.enricher_manager import EnricherManager, get_enricher_manager
        
        # Teste 1: Criar instância direta
        manager = EnricherManager()
        print("✅ EnricherManager criado diretamente")
        
        # Teste 2: Usar função de conveniência
        manager2 = get_enricher_manager()
        print("✅ EnricherManager criado via get_enricher_manager()")
        
        # Verificar se tem os métodos esperados
        metodos_esperados = ['enrich_context', 'enrich_response', '_enrich_by_domain']
        for metodo in metodos_esperados:
            if hasattr(manager, metodo):
                print(f"✅ Método '{metodo}' encontrado")
            else:
                print(f"❌ Método '{metodo}' NÃO encontrado")
        
        return manager
        
    except Exception as e:
        print(f"❌ Erro ao criar EnricherManager: {e}")
        import traceback
        traceback.print_exc()
        return None

def testar_enriquecimento_basico(manager):
    """Testa enriquecimento básico de dados"""
    print("\n🔍 TESTE 2: Enriquecimento Básico")
    print("=" * 50)
    
    if not manager:
        print("❌ Manager não disponível")
        return False
    
    try:
        # Dados de teste simples
        dados_teste = {
            'teste': 'dados simples',
            'numero': 123
        }
        
        resultado = manager.enrich_context(
            data=dados_teste,
            query="Teste simples",
            domain="teste"
        )
        
        print(f"✅ Dados originais: {len(dados_teste)} campos")
        print(f"✅ Dados enriquecidos: {len(resultado)} campos")
        
        # Verificar campos adicionados
        campos_novos = [k for k in resultado.keys() if k not in dados_teste]
        print(f"✅ Campos adicionados: {campos_novos}")
        
        # Verificar metadados
        if 'metadata' in resultado:
            print("✅ Metadados adicionados:")
            for k, v in resultado['metadata'].items():
                print(f"   - {k}: {v}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no enriquecimento básico: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_enriquecimento_entregas(manager):
    """Testa enriquecimento específico de entregas"""
    print("\n🔍 TESTE 3: Enriquecimento de Entregas")
    print("=" * 50)
    
    if not manager:
        print("❌ Manager não disponível")
        return False
    
    try:
        # Dados de teste de entregas
        dados_teste = {
            'entregas': [
                {'status': 'entregue', 'no_prazo': True, 'cliente': 'Cliente A'},
                {'status': 'entregue', 'no_prazo': False, 'cliente': 'Cliente B'},
                {'status': 'pendente', 'no_prazo': None, 'cliente': 'Cliente C'},
                {'status': 'entregue', 'no_prazo': True, 'cliente': 'Cliente D'},
                {'status': 'cancelada', 'no_prazo': None, 'cliente': 'Cliente E'}
            ]
        }
        
        resultado = manager.enrich_context(
            data=dados_teste,
            query="Como estão as entregas?",
            domain="entregas"
        )
        
        print(f"✅ Total de entregas: {len(dados_teste['entregas'])}")
        
        # Verificar análise de entregas
        if 'analise_entregas' in resultado:
            analise = resultado['analise_entregas']
            print("\n📊 Análise de Entregas:")
            print(f"   - Total: {analise.get('total_entregas', 0)}")
            print(f"   - No prazo: {analise.get('entregas_no_prazo', 0)}")
            print(f"   - Atrasadas: {analise.get('entregas_atrasadas', 0)}")
            print(f"   - Taxa de sucesso: {analise.get('taxa_sucesso', 0):.1f}%")
        else:
            print("❌ Análise de entregas não encontrada")
        
        # Verificar outros enriquecimentos
        if 'historico' in resultado:
            print("✅ Histórico adicionado")
        
        if 'tendencias' in resultado:
            print("✅ Tendências calculadas")
        
        if 'comparacoes' in resultado:
            print("✅ Comparações adicionadas")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no enriquecimento de entregas: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_enriquecimento_pedidos(manager):
    """Testa enriquecimento específico de pedidos"""
    print("\n🔍 TESTE 4: Enriquecimento de Pedidos")
    print("=" * 50)
    
    if not manager:
        print("❌ Manager não disponível")
        return False
    
    try:
        # Dados de teste de pedidos
        dados_teste = {
            'pedidos': [
                {'status': 'pendente', 'valor_total': 1000.00},
                {'status': 'faturado', 'valor_total': 2500.50},
                {'status': 'faturado', 'valor_total': 1750.00},
                {'status': 'pendente', 'valor_total': 500.00},
                {'status': 'cancelado', 'valor_total': 0}
            ]
        }
        
        resultado = manager.enrich_context(
            data=dados_teste,
            query="Análise dos pedidos",
            domain="pedidos"
        )
        
        # Verificar análise de pedidos
        if 'analise_pedidos' in resultado:
            analise = resultado['analise_pedidos']
            print("\n📊 Análise de Pedidos:")
            print(f"   - Total: {analise.get('total_pedidos', 0)}")
            print(f"   - Pendentes: {analise.get('pedidos_pendentes', 0)}")
            print(f"   - Faturados: {analise.get('pedidos_faturados', 0)}")
            print(f"   - Valor total: R$ {analise.get('valor_total', 0):,.2f}")
            print(f"   - Ticket médio: R$ {analise.get('ticket_medio', 0):,.2f}")
            
            # Validar cálculos
            valor_esperado = sum(p['valor_total'] for p in dados_teste['pedidos'])
            if abs(analise.get('valor_total', 0) - valor_esperado) < 0.01:
                print("✅ Cálculo de valor total correto")
            else:
                print("❌ Cálculo de valor total incorreto")
        else:
            print("❌ Análise de pedidos não encontrada")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no enriquecimento de pedidos: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_enriquecimento_resposta(manager):
    """Testa enriquecimento de resposta"""
    print("\n🔍 TESTE 5: Enriquecimento de Resposta")
    print("=" * 50)
    
    if not manager:
        print("❌ Manager não disponível")
        return False
    
    try:
        # Primeiro enriquecer dados
        dados_teste = {
            'entregas': [
                {'status': 'entregue', 'no_prazo': True},
                {'status': 'entregue', 'no_prazo': False},
                {'status': 'entregue', 'no_prazo': True}
            ],
            'pedidos': [
                {'status': 'faturado', 'valor_total': 1000},
                {'status': 'faturado', 'valor_total': 2000}
            ]
        }
        
        # Enriquecer contexto primeiro
        dados_enriquecidos = manager.enrich_context(
            data=dados_teste,
            query="Status geral",
            domain="entregas"
        )
        
        # Resposta original
        resposta_original = "Aqui está o status das entregas."
        
        # Enriquecer resposta
        resposta_enriquecida = manager.enrich_response(
            response=resposta_original,
            enrichment_data=dados_enriquecidos
        )
        
        print(f"✅ Resposta original: {len(resposta_original)} caracteres")
        print(f"✅ Resposta enriquecida: {len(resposta_enriquecida)} caracteres")
        
        # Verificar se insights foram adicionados
        if "Insights Adicionais:" in resposta_enriquecida:
            print("✅ Insights adicionados à resposta")
            
            # Extrair insights
            insights_parte = resposta_enriquecida.split("Insights Adicionais:")[1]
            insights = [l.strip() for l in insights_parte.split('\n') if l.strip().startswith('-')]
            print(f"✅ {len(insights)} insights encontrados:")
            for insight in insights:
                print(f"   {insight}")
        else:
            print("❌ Nenhum insight adicionado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no enriquecimento de resposta: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_enrichers_individuais(manager):
    """Testa os enrichers individuais dentro do manager"""
    print("\n🔍 TESTE 6: Enrichers Individuais")
    print("=" * 50)
    
    if not manager:
        print("❌ Manager não disponível")
        return False
    
    try:
        # Verificar enrichers carregados
        print("Verificando enrichers disponíveis:")
        
        if hasattr(manager, 'enrichers'):
            print(f"✅ {len(manager.enrichers)} enrichers registrados")
            
            for nome, enricher in manager.enrichers.items():
                if enricher:
                    print(f"✅ {nome}: {type(enricher).__name__}")
                else:
                    print(f"❌ {nome}: None")
        else:
            print("❌ Atributo 'enrichers' não encontrado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar enrichers individuais: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 TESTE DETALHADO DO ENRICHERMANAGER")
    print("=" * 70)
    
    # Teste 1: Criar manager
    manager = testar_criacao_enricher_manager()
    
    if not manager:
        print("\n❌ Não foi possível criar o EnricherManager. Abortando testes.")
        return
    
    # Executar testes
    resultados = {
        'criacao': manager is not None,
        'basico': testar_enriquecimento_basico(manager),
        'entregas': testar_enriquecimento_entregas(manager),
        'pedidos': testar_enriquecimento_pedidos(manager),
        'resposta': testar_enriquecimento_resposta(manager),
        'individuais': testar_enrichers_individuais(manager)
    }
    
    # Resumo
    print("\n📊 RESUMO DOS TESTES")
    print("=" * 50)
    
    total = len(resultados)
    sucesso = sum(1 for v in resultados.values() if v)
    
    for teste, resultado in resultados.items():
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{teste}: {status}")
    
    print(f"\nTotal: {sucesso}/{total} testes passaram ({sucesso/total*100:.0f}%)")
    
    if sucesso == total:
        print("\n🎉 TODOS OS TESTES PASSARAM! EnricherManager funcionando perfeitamente.")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os logs acima.")

if __name__ == "__main__":
    main() 