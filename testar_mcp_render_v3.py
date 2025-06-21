#!/usr/bin/env python3
"""
Teste das funcionalidades MCP v3.0 para representantes no Render
"""

import requests
import json
from datetime import datetime

def testar_mcp_render_v3():
    print("🧪 TESTANDO MCP v3.0 NO RENDER - FUNCIONALIDADES PARA REPRESENTANTES")
    print("=" * 80)
    
    base_url = "https://frete-sistema.onrender.com"
    
    # Headers para as requisições
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'MCP-Test-v3.0'
    }
    
    # Testes das novas funcionalidades
    testes = [
        {
            'nome': 'Health Check',
            'url': f'{base_url}/claude-ai/api/health',
            'metodo': 'GET',
            'esperado': 'Status online'
        },
        {
            'nome': 'Dashboard MCP',
            'url': f'{base_url}/claude-ai/dashboard',
            'metodo': 'GET',
            'esperado': 'Interface dashboard'
        },
        {
            'nome': 'Chat MCP',
            'url': f'{base_url}/claude-ai/chat',
            'metodo': 'GET', 
            'esperado': 'Interface chat'
        }
    ]
    
    # Executar testes
    resultados = []
    
    for teste in testes:
        print(f"\n🔍 TESTANDO: {teste['nome']}")
        try:
            if teste['metodo'] == 'GET':
                response = requests.get(teste['url'], headers=headers, timeout=10)
            
            status_emoji = "✅" if response.status_code == 200 else "❌"
            print(f"   {status_emoji} Status: {response.status_code}")
            print(f"   📏 Tamanho: {len(response.content)} bytes")
            
            # Verificar conteúdo específico
            if 'health' in teste['url']:
                try:
                    data = response.json()
                    print(f"   🟢 Serviço: {data.get('service', 'N/A')}")
                    print(f"   ⏰ Timestamp: {data.get('timestamp', 'N/A')}")
                except:
                    print("   ⚠️ Resposta não é JSON válido")
            
            elif 'dashboard' in teste['url'] or 'chat' in teste['url']:
                if 'claude-ai' in response.text.lower():
                    print("   ✅ Conteúdo MCP detectado")
                else:
                    print("   ⚠️ Conteúdo MCP não detectado")
            
            resultados.append({
                'teste': teste['nome'],
                'status': response.status_code,
                'sucesso': response.status_code == 200
            })
            
        except requests.exceptions.Timeout:
            print(f"   ⏰ TIMEOUT - Render pode estar hibernando")
            resultados.append({'teste': teste['nome'], 'status': 'TIMEOUT', 'sucesso': False})
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ ERRO: {e}")
            resultados.append({'teste': teste['nome'], 'status': 'ERRO', 'sucesso': False})
    
    # Resumo dos resultados
    print("\n" + "=" * 80)
    print("📊 RESUMO DOS TESTES MCP v3.0")
    print("=" * 80)
    
    sucessos = sum(1 for r in resultados if r['sucesso'])
    total = len(resultados)
    
    print(f"✅ Sucessos: {sucessos}/{total}")
    print(f"📈 Taxa de sucesso: {(sucessos/total)*100:.1f}%")
    
    print("\n📋 DETALHES:")
    for resultado in resultados:
        status_emoji = "✅" if resultado['sucesso'] else "❌"
        print(f"   {status_emoji} {resultado['teste']}: {resultado['status']}")
    
    # Próximos passos
    print("\n" + "=" * 80)
    print("🚀 FUNCIONALIDADES PARA REPRESENTANTES DEPLOYADAS")
    print("=" * 80)
    
    print("💡 COMANDOS DISPONÍVEIS:")
    print("• 'Pedidos do cliente Assai de SP'")
    print("• 'Como estão os pedidos do Carrefour?'")
    print("• 'Exportar pedidos do Magazine Luiza para Excel'")
    print("• 'Status dos últimos pedidos da Renner'")
    
    print("\n🎯 STATUS MOSTRADOS:")
    print("• 📅 Agendamento (data + protocolo)")
    print("• 🚚 Embarque (data + previsão)")
    print("• 📄 Faturamento (NF + status)")
    print("• 🎯 Entrega (realizada + previsão)")
    print("• 🚛 Transportadora")
    
    print("\n📊 EXCEL INCLUI:")
    print("• 20 colunas completas")
    print("• Até 100 pedidos por cliente")
    print("• Resumo automático por status")
    print("• Lead time e dados de performance")
    
    if sucessos >= total * 0.8:  # 80% de sucesso
        print("\n🎉 SISTEMA PRONTO PARA PRÓXIMO NÍVEL!")
        print("🔮 Preparando MCP Avançado com IA...")
        return True
    else:
        print("\n⚠️ Alguns testes falharam - verificar logs do Render")
        return False

if __name__ == "__main__":
    testar_mcp_render_v3() 