#!/usr/bin/env python3
"""
Script de Teste de Performance - API de Ruptura Otimizada
Autor: Claude AI
Data: 2025-01-04

Executa testes de performance comparando as diferentes versões da API
"""

import requests
import time
import json
from datetime import datetime
import sys
import os

# Adicionar diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuração
BASE_URL = "http://localhost:5000"  # Ajustar se necessário
HEADERS = {"Content-Type": "application/json"}

def testar_api_individual(num_pedido):
    """Testa API individual"""
    print(f"\n🔍 Testando pedido individual: {num_pedido}")
    
    # Versão antiga (sem cache)
    print("\n1. API Sem Cache (original):")
    inicio = time.time()
    try:
        response = requests.get(f"{BASE_URL}/carteira/api/ruptura/sem-cache/analisar-pedido/{num_pedido}")
        tempo_sem_cache = (time.time() - inicio) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Sucesso em {tempo_sem_cache:.2f}ms")
            print(f"   - Pedido OK: {data.get('pedido_ok')}")
            print(f"   - Disponibilidade: {data.get('percentual_disponibilidade')}%")
        else:
            print(f"   ❌ Erro: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        tempo_sem_cache = None
    
    # Versão nova (batch otimizada)
    print("\n2. API Batch Otimizada (nova):")
    inicio = time.time()
    try:
        response = requests.get(f"{BASE_URL}/carteira/api/ruptura/batch/analisar-pedido/{num_pedido}")
        tempo_batch = (time.time() - inicio) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Sucesso em {tempo_batch:.2f}ms")
            print(f"   - Pedido OK: {data.get('pedido_ok')}")
            print(f"   - Disponibilidade: {data.get('percentual_disponibilidade')}%")
        else:
            print(f"   ❌ Erro: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        tempo_batch = None
    
    # Comparação
    if tempo_sem_cache and tempo_batch:
        melhoria = ((tempo_sem_cache - tempo_batch) / tempo_sem_cache) * 100
        print(f"\n📊 Comparação:")
        print(f"   - Sem Cache: {tempo_sem_cache:.2f}ms")
        print(f"   - Batch Otimizada: {tempo_batch:.2f}ms")
        print(f"   - Melhoria: {melhoria:.1f}%")
        if tempo_batch < tempo_sem_cache:
            print(f"   🚀 Nova API é {tempo_sem_cache/tempo_batch:.1f}x mais rápida!")

def testar_api_batch(pedidos):
    """Testa API batch com múltiplos pedidos"""
    print(f"\n🔍 Testando batch com {len(pedidos)} pedidos")
    
    inicio = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/carteira/api/ruptura/batch/multiple",
            json={"pedidos": pedidos},
            headers=HEADERS
        )
        tempo_total = (time.time() - inicio) * 1000
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('estatisticas', {})
            perf = data.get('performance', {})
            
            print(f"\n✅ Batch concluído em {tempo_total:.2f}ms")
            print(f"\n📊 Estatísticas:")
            print(f"   - Total pedidos: {stats.get('total_pedidos')}")
            print(f"   - Pedidos OK: {stats.get('pedidos_ok')}")
            print(f"   - Com ruptura: {stats.get('pedidos_com_ruptura')}")
            print(f"   - % OK: {stats.get('percentual_ok')}%")
            print(f"\n⚡ Performance:")
            print(f"   - Tempo total: {perf.get('tempo_total_ms')}ms")
            print(f"   - Tempo médio: {perf.get('tempo_medio_ms')}ms/pedido")
            print(f"   - Taxa: {perf.get('pedidos_por_segundo')} pedidos/segundo")
            
            return data
        else:
            print(f"❌ Erro: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    return None

def buscar_pedidos_ativos(limite=10):
    """Busca pedidos ativos para teste"""
    print("\n🔍 Buscando pedidos ativos...")
    
    try:
        # Usar a própria API de todos ativos com limite
        response = requests.get(f"{BASE_URL}/carteira/api/ruptura/batch/todos-ativos?limite={limite}")
        
        if response.status_code == 200:
            data = response.json()
            if 'resultados_completos' in data:
                pedidos = list(data['resultados_completos'].keys())
                print(f"   ✅ Encontrados {len(pedidos)} pedidos ativos")
                return pedidos[:limite]
        
        print("   ⚠️ Usando pedidos de exemplo")
        return ["P001", "P002", "P003"]  # Fallback
        
    except Exception as e:
        print(f"   ❌ Erro ao buscar pedidos: {e}")
        return ["P001", "P002", "P003"]  # Fallback

def main():
    """Função principal"""
    print("=" * 60)
    print("🚀 TESTE DE PERFORMANCE - API DE RUPTURA OTIMIZADA")
    print("=" * 60)
    print(f"Servidor: {BASE_URL}")
    print(f"Horário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Buscar pedidos para teste
    pedidos = buscar_pedidos_ativos(20)
    
    if not pedidos:
        print("\n❌ Nenhum pedido encontrado para teste")
        return
    
    # Teste 1: Individual
    print("\n" + "=" * 60)
    print("TESTE 1: PEDIDO INDIVIDUAL")
    print("=" * 60)
    if pedidos:
        testar_api_individual(pedidos[0])
    
    # Teste 2: Batch pequeno
    print("\n" + "=" * 60)
    print("TESTE 2: BATCH PEQUENO (5 pedidos)")
    print("=" * 60)
    if len(pedidos) >= 5:
        testar_api_batch(pedidos[:5])
    
    # Teste 3: Batch médio
    print("\n" + "=" * 60)
    print("TESTE 3: BATCH MÉDIO (20 pedidos)")
    print("=" * 60)
    if len(pedidos) >= 20:
        testar_api_batch(pedidos[:20])
    
    # Teste 4: Todos ativos
    print("\n" + "=" * 60)
    print("TESTE 4: TODOS PEDIDOS ATIVOS")
    print("=" * 60)
    
    inicio = time.time()
    try:
        response = requests.get(f"{BASE_URL}/carteira/api/ruptura/batch/todos-ativos?limite=100")
        tempo_total = (time.time() - inicio) * 1000
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('estatisticas', {})
            perf = data.get('performance', {})
            
            print(f"\n✅ Análise completa em {tempo_total:.2f}ms")
            print(f"\n📊 Resultado:")
            print(f"   - Total analisados: {stats.get('total_pedidos')}")
            print(f"   - Tempo total: {perf.get('tempo_total_segundos')}s")
            print(f"   - Taxa: {perf.get('pedidos_por_segundo')} pedidos/segundo")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⛔ Testes interrompidos pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()