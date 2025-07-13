#!/usr/bin/env python3
"""
Testa se a correção do singleton DataProvider funciona
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configurar variável de ambiente
os.environ['SKIP_DB_CREATE'] = 'true'

def testar_singleton():
    print("=" * 60)
    print("🧪 TESTE DA CORREÇÃO DO SINGLETON")
    print("=" * 60)
    
    try:
        # 1. Testar get_data_provider() ANTES de criar LoaderManager
        print("\n1️⃣ Testando get_data_provider() primeiro...")
        from app.claude_ai_novo.providers import get_data_provider
        
        provider1 = get_data_provider()
        print(f"✅ DataProvider criado: {provider1}")
        
        # Verificar se tem loader
        if hasattr(provider1, 'loader') and provider1.loader:
            print(f"✅ LoaderManager configurado automaticamente: {provider1.loader}")
            print(f"   - Tipo: {type(provider1.loader).__name__}")
            print(f"   - Inicializado: {getattr(provider1.loader, 'initialized', 'N/A')}")
        else:
            print("❌ LoaderManager NÃO foi configurado automaticamente")
        
        # 2. Verificar se é singleton
        print("\n2️⃣ Verificando padrão singleton...")
        provider2 = get_data_provider()
        if provider1 is provider2:
            print("✅ Singleton funcionando (mesma instância)")
        else:
            print("❌ Singleton quebrado (instâncias diferentes)")
        
        # 3. Testar ProviderManager
        print("\n3️⃣ Testando ProviderManager...")
        from app.claude_ai_novo.providers import get_provider_manager
        
        manager = get_provider_manager()
        print(f"✅ ProviderManager criado: {manager}")
        
        if hasattr(manager, 'data_provider') and manager.data_provider:
            print(f"✅ DataProvider no manager: {manager.data_provider}")
            
            # Verificar se é a mesma instância
            if manager.data_provider is provider1:
                print("✅ Mesma instância do singleton!")
            else:
                print("❌ Instância diferente (não deveria)")
                
            # Verificar loader no data_provider do manager
            if hasattr(manager.data_provider, 'loader') and manager.data_provider.loader:
                print(f"✅ LoaderManager presente no DataProvider do manager")
            else:
                print("❌ LoaderManager ausente no DataProvider do manager")
        
        # 4. Testar funcionalidade
        print("\n4️⃣ Testando funcionalidade...")
        resultado = provider1.get_data_by_domain('entregas', {
            'periodo_dias': 30,
            'cliente_especifico': 'Atacadão'
        })
        
        print(f"\nResultado:")
        print(f"- Source: {resultado.get('source', 'unknown')}")
        print(f"- Optimized: {resultado.get('optimized', False)}")
        print(f"- Total registros: {resultado.get('total_registros', resultado.get('total', 0))}")
        print(f"- Erro: {resultado.get('erro', resultado.get('error', 'Nenhum'))}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    testar_singleton() 