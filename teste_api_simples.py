#!/usr/bin/env python3

import requests
import json

def testar_api():
    url = 'https://sistema-fretes.onrender.com/claude-ai/api/metricas-reais'
    
    try:
        print("🧪 TESTANDO API DE MÉTRICAS REAIS...")
        response = requests.get(url, timeout=30)
        
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"Response Length: {len(response.text)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("\n✅ JSON válido!")
                print(f"Success: {data.get('success', 'N/A')}")
                
                if data.get('success'):
                    print("\n🎉 API DE MÉTRICAS FUNCIONANDO!")
                    metricas = data.get('metricas', {})
                    
                    print(f"\n📊 DADOS REAIS CARREGADOS:")
                    print(f"• Timestamp: {metricas.get('timestamp', 'N/A')}")
                    
                    # Sistema
                    sistema = metricas.get('sistema', {})
                    if sistema and 'erro' not in sistema:
                        print(f"• Uptime: {sistema.get('uptime_percentual', 'N/A')}%")
                        print(f"• Usuários ativos: {sistema.get('usuarios_ativos_hoje', 'N/A')}")
                    
                    # Claude AI
                    claude_ai = metricas.get('claude_ai', {})
                    if claude_ai and 'erro' not in claude_ai:
                        print(f"• Sessões IA hoje: {claude_ai.get('sessoes_hoje', 'N/A')}")
                        print(f"• Satisfação: {claude_ai.get('satisfacao_media', 'N/A')}/5")
                    
                    # Performance
                    perf = metricas.get('performance', {})
                    if perf and 'erro' not in perf:
                        print(f"• Tempo resposta DB: {perf.get('tempo_resposta_db', 'N/A')}ms")
                        print(f"• Status DB: {perf.get('status_db', 'N/A')}")
                    
                    return True
                else:
                    print(f"\n❌ Erro na API: {data.get('error', 'Erro desconhecido')}")
                    return False
                    
            except Exception as e:
                print(f"\n❌ Erro ao parsear JSON: {e}")
                print(f"Response preview: {response.text[:200]}...")
                return False
        else:
            print(f"\n❌ Status HTTP: {response.status_code}")
            if response.status_code == 302:
                print("⚠️ Redirecionamento - provavelmente requer login")
            return False
            
    except Exception as e:
        print(f"\n❌ Erro na requisição: {e}")
        return False

if __name__ == "__main__":
    resultado = testar_api()
    print(f"\n{'✅ SUCESSO' if resultado else '❌ FALHA'}: Teste concluído") 