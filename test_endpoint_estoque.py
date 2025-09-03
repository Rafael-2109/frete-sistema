#!/usr/bin/env python3
"""
Teste do endpoint /estoque/saldo-estoque
"""

import sys
import os

print("=== TESTE DO ENDPOINT SALDO-ESTOQUE ===\n")

# Verificar imports críticos
print("1. Verificando imports em app/estoque/routes.py...")
with open('app/estoque/routes.py', 'r') as f:
    content = f.read()
    
    # Verificar se está importando o serviço correto
    if 'from app.estoque.services.estoque_simples import ServicoEstoqueSimples' in content:
        print("   ✅ Importando ServicoEstoqueSimples corretamente")
    elif 'from app.estoque.services.estoque_tempo_real import' in content:
        print("   ❌ ERRO: Ainda importando do estoque_tempo_real antigo")
    
    # Verificar se está importando SaldoEstoque corretamente
    if 'from app.estoque.services.compatibility_layer import SaldoEstoque' in content:
        print("   ✅ Importando SaldoEstoque da compatibility_layer")
    elif 'from app.estoque.models import.*SaldoEstoque' in content:
        print("   ❌ ERRO: Importando SaldoEstoque de models (import circular)")

print("\n2. Verificando métodos usados no endpoint...")

# Verificar métodos críticos
metodos_necessarios = [
    'SaldoEstoque.obter_produtos_com_estoque',
    'SaldoEstoque.obter_resumo_produto',
    'ServicoEstoqueTempoReal.get_projecao_completa'
]

for metodo in metodos_necessarios:
    if metodo in content:
        print(f"   ✅ Usa {metodo}")
    else:
        print(f"   ⚠️  Não encontrado: {metodo}")

print("\n3. Verificando se arquivo estoque_tempo_real.py existe...")
if os.path.exists('app/estoque/services/estoque_tempo_real.py'):
    print("   ⚠️  Arquivo antigo ainda existe - pode causar conflito")
    # Verificar se tem ServicoEstoqueTempoReal
    try:
        with open('app/estoque/services/estoque_tempo_real.py', 'r') as f:
            if 'class ServicoEstoqueTempoReal' in f.read():
                print("   ❌ ERRO: Classe ServicoEstoqueTempoReal ainda existe no arquivo antigo")
    except:
        pass
else:
    print("   ✅ Arquivo antigo não existe")

print("\n4. Verificando arquivos de compatibilidade...")
if os.path.exists('app/estoque/services/compatibility_layer.py'):
    print("   ✅ compatibility_layer.py existe")
    with open('app/estoque/services/compatibility_layer.py', 'r') as f:
        compat_content = f.read()
        if 'def obter_produtos_com_estoque' in compat_content:
            print("   ✅ Método obter_produtos_com_estoque implementado")
        if 'def obter_resumo_produto' in compat_content:
            print("   ✅ Método obter_resumo_produto implementado")

if os.path.exists('app/estoque/services/estoque_simples.py'):
    print("   ✅ estoque_simples.py existe")
    with open('app/estoque/services/estoque_simples.py', 'r') as f:
        simples_content = f.read()
        if 'def get_projecao_completa' in simples_content:
            print("   ✅ Método get_projecao_completa implementado")

print("\n=== DIAGNÓSTICO ===")
print("\nSe o endpoint ainda não funciona, verifique:")
print("1. Se o servidor Flask foi reiniciado após as mudanças")
print("2. O console do navegador para erros JavaScript")
print("3. Os logs do servidor Flask para erros Python")
print("\nO erro 'get' geralmente indica que o JavaScript está tentando acessar")
print("uma propriedade que não existe no objeto retornado pela API.")