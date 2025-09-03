#!/usr/bin/env python3
"""
Script de teste para validar as APIs de cardex
Verifica se produção e saídas estão sendo retornadas corretamente
"""

import json
import requests
from datetime import date, timedelta
import sys

# Configurações
BASE_URL = "http://localhost:5000"  # Ajuste conforme necessário
COD_PRODUTO_TESTE = "52010"  # Substitua por um produto válido no seu sistema

def test_cardex_api():
    """Testa a API principal de cardex"""
    print("\n=== Testando API /api/produto/<cod_produto>/cardex ===")
    
    url = f"{BASE_URL}/carteira/api/produto/{COD_PRODUTO_TESTE}/cardex"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print(f"✅ API respondeu com sucesso")
                print(f"📦 Produto: {data.get('cod_produto')}")
                print(f"📊 Estoque Atual: {data.get('estoque_atual', 0):.0f}")
                print(f"📈 Total Produção (28 dias): {data.get('total_producao', 0):.0f}")
                print(f"📉 Total Saídas (28 dias): {data.get('total_saidas', 0):.0f}")
                
                # Verificar se cardex tem dados
                cardex = data.get('cardex', [])
                if cardex:
                    print(f"\n📋 Primeiros 3 dias do cardex:")
                    for dia in cardex[:3]:
                        print(f"  D+{dia.get('dia', 0)}:")
                        print(f"    Est. Inicial: {dia.get('estoque_inicial', 0):.0f}")
                        print(f"    Saídas: {dia.get('saidas', 0):.0f}")
                        print(f"    Saldo: {dia.get('saldo', 0):.0f}")
                        print(f"    Produção: {dia.get('producao', 0):.0f}")
                        print(f"    Est. Final: {dia.get('estoque_final', 0):.0f}")
                        
                        # Validar cálculo do saldo
                        saldo_calculado = dia.get('estoque_inicial', 0) - dia.get('saidas', 0)
                        saldo_api = dia.get('saldo', 0)
                        if abs(saldo_calculado - saldo_api) > 0.01:
                            print(f"    ⚠️ AVISO: Saldo incorreto! Esperado: {saldo_calculado:.0f}, Recebido: {saldo_api:.0f}")
                    
                    # Verificar se produção e saídas estão sendo somadas
                    if data.get('total_producao', 0) == 0 and data.get('total_saidas', 0) == 0:
                        print("\n⚠️ PROBLEMA: Total de produção e saídas estão zerados!")
                    
                else:
                    print("❌ Cardex vazio")
                    
                return True
            else:
                print(f"❌ API retornou erro: {data.get('error')}")
                return False
                
        else:
            print(f"❌ Status HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao chamar API: {e}")
        return False


def test_cardex_detalhado_api():
    """Testa a API de cardex detalhado"""
    print("\n=== Testando API /api/produto/<cod_produto>/cardex-detalhado ===")
    
    url = f"{BASE_URL}/carteira/api/produto/{COD_PRODUTO_TESTE}/cardex-detalhado"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print(f"✅ API respondeu com sucesso")
                print(f"📦 Produto: {data.get('cod_produto')}")
                print(f"📊 Estoque Atual: {data.get('estoque_atual', 0):.0f}")
                
                # Verificar projeção resumo
                projecao = data.get('projecao_resumo', [])
                if projecao:
                    print(f"\n📋 Primeiros 3 dias da projeção:")
                    for dia in projecao[:3]:
                        print(f"  D+{dia.get('dia', 0)}:")
                        print(f"    Saldo Inicial: {dia.get('saldo_inicial', 0):.0f}")
                        print(f"    Saída: {dia.get('saida', 0):.0f}")
                        print(f"    Saldo: {dia.get('saldo', 0):.0f}")
                        print(f"    Entrada/Produção: {dia.get('entrada', 0):.0f}")
                        print(f"    Saldo Final: {dia.get('saldo_final', 0):.0f}")
                
                # Verificar pedidos por data
                pedidos_por_data = data.get('pedidos_por_data', {})
                print(f"\n📅 Total de datas com pedidos: {len(pedidos_por_data)}")
                
                for data_key, pedidos in list(pedidos_por_data.items())[:3]:
                    total_qtd = sum(p.get('qtd', 0) for p in pedidos)
                    print(f"  {data_key}: {len(pedidos)} pedidos, Total: {total_qtd:.0f}")
                
                return True
            else:
                print(f"❌ API retornou erro: {data.get('error')}")
                return False
                
        else:
            print(f"❌ Status HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao chamar API: {e}")
        return False


def main():
    print("=" * 60)
    print("TESTE DAS APIs DE CARDEX")
    print("=" * 60)
    
    # Testar ambas as APIs
    resultado1 = test_cardex_api()
    resultado2 = test_cardex_detalhado_api()
    
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    
    if resultado1 and resultado2:
        print("✅ Todos os testes passaram!")
        print("\n📝 VERIFICAÇÕES IMPORTANTES:")
        print("1. Verifique se 'Total Produção' e 'Total Saídas' têm valores > 0")
        print("2. Verifique se o cálculo do Saldo está correto (Est. Inicial - Saídas)")
        print("3. Verifique se a coluna 'Produção' aparece com valores no frontend")
        return 0
    else:
        print("❌ Alguns testes falharam")
        print("\n📝 POSSÍVEIS PROBLEMAS:")
        print("1. Servidor Flask não está rodando")
        print("2. Produto de teste não existe")
        print("3. Erro de autenticação (precisa estar logado)")
        return 1


if __name__ == "__main__":
    sys.exit(main())