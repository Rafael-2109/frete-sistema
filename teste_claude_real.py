#!/usr/bin/env python3
"""
Teste rápido do Claude REAL após configuração
"""

import requests
import json
from datetime import datetime

def testar_claude_real():
    """Testa Claude real via API do sistema"""
    
    print("🧠 TESTANDO CLAUDE REAL INTEGRATION")
    print("=" * 50)
    
    # URL do sistema (altere se necessário)
    base_url = "https://frete-sistema.onrender.com"
    
    # Teste 1: Verificar status
    print("\n1️⃣ VERIFICANDO STATUS...")
    try:
        response = requests.get(f"{base_url}/claude-ai/real/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status obtido:")
            print(f"   Modo Real: {data.get('modo_real', False)}")
            print(f"   API Key Configurada: {data.get('api_key_configurada', False)}")
            print(f"   Client Conectado: {data.get('client_conectado', False)}")
            
            if data.get('modo_real') and data.get('client_conectado'):
                print("🎉 CLAUDE REAL ESTÁ ATIVO!")
            else:
                print("⚠️ Claude Real ainda não está ativo (aguarde deploy)")
        else:
            print(f"❌ Erro no status: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
    
    # Teste 2: Consulta simples (só se ativo)
    print("\n2️⃣ TESTANDO CONSULTA...")
    try:
        test_query = {
            "query": "Analise rapidamente o status atual do sistema de fretes e dê 2 insights principais."
        }
        
        response = requests.post(
            f"{base_url}/claude-ai/real", 
            json=test_query,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print("✅ CONSULTA FUNCIONOU!")
                print("📝 Resposta:")
                print(data.get('response', '')[:200] + "...")
            else:
                print(f"⚠️ Erro na consulta: {data.get('error', 'Erro desconhecido')}")
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro na consulta: {e}")
    
    print("\n" + "=" * 50)
    print("🔗 URLS PARA TESTAR NO NAVEGADOR:")
    print(f"📊 Dashboard: {base_url}/")
    print(f"🧠 Claude Real: {base_url}/claude-ai/real")
    print(f"📈 Dashboard v4.0: {base_url}/claude-ai/v4/dashboard")

if __name__ == "__main__":
    testar_claude_real() 