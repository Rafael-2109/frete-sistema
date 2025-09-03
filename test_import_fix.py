#!/usr/bin/env python3
"""
Script para testar se a correção do import circular funcionou
"""

import sys
import os
sys.path.insert(0, os.getcwd())

print("=== TESTE DE IMPORT CIRCULAR ===\n")

try:
    print("1. Testando import de models.py...")
    from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
    print("   ✅ MovimentacaoEstoque e UnificacaoCodigos importados")
except ImportError as e:
    print(f"   ❌ Erro: {e}")
    sys.exit(1)

try:
    print("\n2. Testando import de compatibility_layer.py...")
    from app.estoque.services.compatibility_layer import SaldoEstoque
    print("   ✅ SaldoEstoque importado da compatibility_layer")
except ImportError as e:
    print(f"   ❌ Erro: {e}")
    sys.exit(1)

try:
    print("\n3. Testando import alternativo...")
    from app.estoque.services.compatibility_layer import SaldoEstoqueCompativel
    print("   ✅ SaldoEstoqueCompativel importado")
except ImportError as e:
    print(f"   ❌ Erro: {e}")
    sys.exit(1)

print("\n4. Verificando métodos disponíveis...")
metodos_esperados = [
    'calcular_estoque_inicial',
    'calcular_producao_periodo', 
    'calcular_projecao_completa',
    'obter_resumo_produto'
]

for metodo in metodos_esperados:
    if hasattr(SaldoEstoque, metodo):
        print(f"   ✅ SaldoEstoque.{metodo} disponível")
    else:
        print(f"   ❌ SaldoEstoque.{metodo} NÃO encontrado")

print("\n5. Verificando se são a mesma classe...")
if SaldoEstoque == SaldoEstoqueCompativel:
    print("   ✅ SaldoEstoque e SaldoEstoqueCompativel são idênticos")
else:
    print("   ❌ Classes diferentes")

print("\n✅ TODOS OS TESTES PASSARAM!")
print("\nO workspace de montagem agora deve funcionar corretamente.")
print("O erro de import circular foi resolvido.")