#!/usr/bin/env python3
"""
Teste direto dos imports sem Flask
"""

import sys
import os
sys.path.insert(0, os.getcwd())

print("=== TESTE DIRETO DE IMPORTS ===\n")

# Configurar variáveis mínimas
os.environ.setdefault('DATABASE_URL', 'postgresql://test')
os.environ.setdefault('SECRET_KEY', 'test')

try:
    print("1. Testando import de estoque_simples...")
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    print("   ✅ ServicoEstoqueSimples importado")
    
    # Verificar se tem o método
    if hasattr(ServicoEstoqueSimples, 'get_projecao_completa'):
        print("   ✅ Método get_projecao_completa existe")
    
    # Testar com alias
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples as ServicoEstoqueTempoReal
    print("   ✅ Alias ServicoEstoqueTempoReal funcionando")
    
except ImportError as e:
    print(f"   ❌ Erro de import: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n2. Testando import de compatibility_layer...")
    from app.estoque.services.compatibility_layer import SaldoEstoque
    print("   ✅ SaldoEstoque importado")
    
    # Verificar métodos
    if hasattr(SaldoEstoque, 'obter_produtos_com_estoque'):
        print("   ✅ Método obter_produtos_com_estoque existe")
    if hasattr(SaldoEstoque, 'obter_resumo_produto'):
        print("   ✅ Método obter_resumo_produto existe")
        
except ImportError as e:
    print(f"   ❌ Erro de import: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ Se todos os imports funcionaram, o problema pode ser:")
print("1. Servidor Flask não foi reiniciado")
print("2. Cache do navegador")
print("3. Erro no JavaScript do frontend")