#!/usr/bin/env python3
"""
🔍 DIAGNÓSTICO: Conexão Loader → Provider
========================================
"""

import logging
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Diagnostica problemas na conexão Loader → Provider"""
    print("\n" + "="*60)
    print("🔍 DIAGNÓSTICO: Conexão Loader → Provider")
    print("="*60 + "\n")
    
    try:
        # 1. Verificar se os módulos podem ser importados
        print("1️⃣ Importando módulos...")
        
        try:
            from app.claude_ai_novo.loaders import LoaderManager
            print("✅ LoaderManager importado com sucesso")
        except Exception as e:
            print(f"❌ Erro ao importar LoaderManager: {e}")
            return
            
        try:
            from app.claude_ai_novo.providers import DataProvider, ProviderManager, get_provider_manager
            print("✅ Providers importados com sucesso")
        except Exception as e:
            print(f"❌ Erro ao importar Providers: {e}")
            return
            
        # 2. Verificar estrutura do ProviderManager
        print("\n2️⃣ Analisando ProviderManager...")
        
        provider_manager = get_provider_manager()
        print(f"   Tipo: {type(provider_manager)}")
        print(f"   Atributos: {[attr for attr in dir(provider_manager) if not attr.startswith('_')]}")
        
        # Verificar se tem DataProvider
        if hasattr(provider_manager, 'data_provider'):
            print(f"✅ ProviderManager tem data_provider: {type(provider_manager.data_provider)}")
            
            # Verificar se DataProvider tem set_loader
            if hasattr(provider_manager.data_provider, 'set_loader'):
                print("✅ DataProvider tem método set_loader")
            else:
                print("❌ DataProvider NÃO tem método set_loader")
        else:
            print("❌ ProviderManager NÃO tem data_provider")
            
        # 3. Testar conexão direta
        print("\n3️⃣ Testando conexão direta...")
        
        loader = LoaderManager()
        data_provider = DataProvider()
        
        # Verificar estado inicial
        print(f"   Loader inicial no DataProvider: {getattr(data_provider, 'loader', 'NÃO EXISTE')}")
        
        # Fazer conexão
        data_provider.set_loader(loader)
        print("✅ set_loader() executado")
        
        # Verificar estado após conexão
        print(f"   Loader após conexão: {getattr(data_provider, 'loader', 'NÃO EXISTE')}")
        
        # 4. Verificar como o orchestrator vê os componentes
        print("\n4️⃣ Verificando componentes no Orchestrator...")
        
        from app.claude_ai_novo.orchestrators import get_main_orchestrator
        orchestrator = get_main_orchestrator()
        
        print(f"   Componentes registrados: {list(orchestrator.components.keys())}")
        
        if 'providers' in orchestrator.components:
            provider_component = orchestrator.components['providers']
            print(f"   Tipo do provider: {type(provider_component)}")
            print(f"   É ProviderManager? {isinstance(provider_component, ProviderManager)}")
            
            # Se for ProviderManager, precisamos acessar o DataProvider dentro dele
            if hasattr(provider_component, 'data_provider'):
                print("   ✅ Provider tem data_provider interno")
                data_provider_interno = provider_component.data_provider
                
                if hasattr(data_provider_interno, 'set_loader'):
                    print("   ✅ DataProvider interno tem set_loader")
                else:
                    print("   ❌ DataProvider interno NÃO tem set_loader")
            else:
                print("   ❌ Provider NÃO tem data_provider interno")
                
        # 5. Propor solução
        print("\n5️⃣ DIAGNÓSTICO FINAL:")
        print("-" * 40)
        
        if isinstance(orchestrator.components.get('providers'), ProviderManager):
            print("❗ PROBLEMA IDENTIFICADO:")
            print("   O Orchestrator registra ProviderManager, não DataProvider diretamente.")
            print("   A conexão deveria ser: loader → provider_manager.data_provider")
            print("\n📝 SOLUÇÃO PROPOSTA:")
            print("   Modificar _connect_modules() para:")
            print("   1. Verificar se provider é ProviderManager")
            print("   2. Acessar provider.data_provider")
            print("   3. Chamar data_provider.set_loader()")
        else:
            print("✅ Estrutura parece correta, verificar outros problemas")
            
    except Exception as e:
        logger.error(f"❌ Erro durante diagnóstico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 