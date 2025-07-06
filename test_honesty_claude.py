#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🧪 TESTE DE HONESTIDADE DO CLAUDE AI
Verifica se o Claude é transparente sobre suas capacidades reais
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

print("=== TESTE DE HONESTIDADE DO CLAUDE AI ===\n")

# 1. Verificar system prompt
print("1. Testando novo system prompt...")
try:
    from app.claude_ai.claude_real_integration import claude_real_integration
    
    print("System prompt atual:")
    print("-" * 60)
    print(claude_real_integration.system_prompt)
    print("-" * 60)
    
    # Verificar palavras-chave importantes
    keywords = [
        "NÃO tenho acesso direto aos arquivos",
        "HONESTO",
        "capacidades REAIS",
        "peça ao usuário para compartilhar"
    ]
    
    for keyword in keywords:
        if keyword in claude_real_integration.system_prompt:
            print(f"✅ Contém: '{keyword}'")
        else:
            print(f"❌ Faltando: '{keyword}'")
            
except Exception as e:
    print(f"❌ Erro: {e}")

# 2. Simular pergunta sobre código
print("\n\n2. Simulando pergunta sobre código...")
test_queries = [
    ("Pode verificar o conteudo de carteira/routes.py por favor", "arquivo"),
    ("Qual o código da função gerar_separacao?", "função"),
    ("Mostre o modelo CarteiraPrincipal", "modelo"),
    ("Quantas entregas temos pendentes?", "dados")
]

print("\nExemplos de perguntas e respostas esperadas:")
print("-" * 60)
for query, tipo in test_queries:
    print(f"\n❓ Pergunta: '{query}'")
    if tipo in ["arquivo", "função", "modelo"]:
        print("✅ Resposta esperada: 'Não tenho acesso direto aos arquivos. Por favor, compartilhe o código...'")
    else:
        print("✅ Resposta esperada: Análise dos dados fornecidos")

# 3. Resumo das mudanças
print("\n\n=== RESUMO DAS MUDANÇAS ===")
print("❌ ANTES: Claude inventava código quando não tinha acesso")
print("✅ AGORA: Claude é honesto sobre suas limitações")
print("\n📋 Benefícios:")
print("- Usuário sabe quando precisa compartilhar código")
print("- Evita informações inventadas")
print("- Mantém confiança no sistema")
print("- Respostas mais precisas e úteis")

print("\n💡 Teste real:")
print("1. Pergunte sobre um arquivo específico")
print("2. Claude deve pedir para você compartilhar")
print("3. Não deve inventar código") 