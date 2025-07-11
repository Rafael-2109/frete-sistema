#!/usr/bin/env python3
"""
Teste específico dos carregadores
"""

def testar_carregadores():
    """Testa especificamente os carregadores"""
    
    print("🧪 TESTE ESPECÍFICO DOS CARREGADORES")
    print("=" * 50)
    
    # Teste 1: ContextLoader
    print("\n1️⃣ TESTE CONTEXT LOADER")
    try:
        from loaders import get_contextloader
        loader = get_contextloader()
        print("✅ ContextLoader importado e instanciado com sucesso")
    except Exception as e:
        print(f"❌ Erro no ContextLoader: {e}")
        return False
    
    # Teste 2: DatabaseLoader
    print("\n2️⃣ TESTE DATABASE LOADER")
    try:
        from loaders import get_database_loader
        db_loader = get_database_loader()
        print("✅ DatabaseLoader importado e instanciado com sucesso")
    except Exception as e:
        print(f"❌ Erro no DatabaseLoader: {e}")
    
    # Teste 3: DataManager
    print("\n3️⃣ TESTE DATA MANAGER")
    try:
        from loaders import get_data_manager
        data_manager = get_data_manager()
        print("✅ DataManager importado e instanciado com sucesso")
    except Exception as e:
        print(f"❌ Erro no DataManager: {e}")
    
    # Teste 4: Funções auxiliares
    print("\n4️⃣ TESTE FUNÇÕES AUXILIARES")
    try:
        from loaders.context_loader import (
            _carregar_dados_pedidos,
            _carregar_dados_fretes,
            _carregar_dados_transportadoras
        )
        print("✅ Funções auxiliares importadas com sucesso")
        
        # Teste básico das funções
        analise = {"cliente_especifico": "teste", "periodo_dias": 30}
        filtros = {"is_vendedor": False}
        from datetime import datetime, timedelta
        data_limite = datetime.now() - timedelta(days=30)
        
        resultado = _carregar_dados_pedidos(analise, filtros, data_limite)
        print(f"✅ _carregar_dados_pedidos funcionando: {type(resultado)}")
        
    except Exception as e:
        print(f"❌ Erro nas funções auxiliares: {e}")
    
    print("\n🎯 RESUMO")
    print("=" * 50)
    print("✅ Teste de carregadores concluído!")
    return True

if __name__ == "__main__":
    testar_carregadores() 