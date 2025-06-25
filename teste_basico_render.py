#!/usr/bin/env python3
"""
Teste básico para verificar se as rotas do sistema avançado estão registradas
"""

import requests
from datetime import datetime

def testar_rotas_basico():
    """Testa se as rotas respondem (mesmo que seja redirect)"""
    print("🧪 TESTE BÁSICO - VERIFICAR SE ROTAS ESTÃO REGISTRADAS")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    base_url = "https://sistema-fretes.onrender.com"
    
    # Rotas para testar (esperamos 302 redirect para login OU 200 se não precisar login)
    rotas_testar = [
        "/claude-ai/advanced-dashboard",
        "/claude-ai/advanced-feedback-interface",
        "/claude-ai/api/advanced-analytics", 
        "/claude-ai/api/system-health-advanced",
        "/claude-ai/real",  # Esta deve funcionar
        "/claude-ai/dashboard"  # Esta também
    ]
    
    resultados = {}
    rotas_ok = 0
    
    print("\n🚀 TESTANDO ROTAS...")
    
    for rota in rotas_testar:
        try:
            response = requests.get(f"{base_url}{rota}", timeout=10, allow_redirects=False)
            
            if response.status_code in [200, 302]:  # 200 = OK, 302 = redirect para login
                status = "✅ REGISTRADA"
                rotas_ok += 1
            elif response.status_code == 404:
                status = "❌ NÃO ENCONTRADA"
            else:
                status = f"⚠️ HTTP {response.status_code}"
            
            resultados[rota] = status
            print(f"  {status} {rota}")
            
        except Exception as e:
            resultados[rota] = f"❌ ERRO: {str(e)[:30]}..."
            print(f"  ❌ ERRO {rota}: {str(e)[:50]}...")
    
    # Resumo
    print("\n" + "=" * 60)
    print("📋 RESUMO DOS TESTES")
    print("=" * 60)
    
    print(f"\n🎯 RESULTADO: {rotas_ok}/{len(rotas_testar)} rotas registradas")
    
    if rotas_ok >= 4:  # Pelo menos 4 das 6 rotas
        print("🎉 SISTEMA AVANÇADO REGISTRADO COM SUCESSO!")
        print("\n✅ ROTAS PRINCIPAIS FUNCIONANDO:")
        for rota, status in resultados.items():
            if "REGISTRADA" in status:
                print(f"  ✅ {rota}")
        
        print("\n🚀 PRÓXIMOS PASSOS:")
        print("1. Acesse https://sistema-fretes.onrender.com/claude-ai/advanced-dashboard")
        print("2. Faça login no sistema")
        print("3. Teste o dashboard avançado")
        print("4. Use o Claude AI com funcionalidades avançadas")
        
    else:
        print("⚠️ Algumas rotas não foram registradas")
        print("\n🔧 ROTAS COM PROBLEMA:")
        for rota, status in resultados.items():
            if "NÃO ENCONTRADA" in status:
                print(f"  ❌ {rota}")
    
    return rotas_ok >= 4

if __name__ == "__main__":
    testar_rotas_basico() 