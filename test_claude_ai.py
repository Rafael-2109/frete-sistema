#!/usr/bin/env python3
"""
Script de teste para verificar Claude AI
"""

from app.claude_ai.claude_real_integration import ClaudeRealIntegration

# Testar processamento de consulta
claude = ClaudeRealIntegration()

# Teste 1: Consulta simples
print("\n=== TESTE 1: Consulta Simples ===")
resposta = claude.processar_consulta_real("Quantas entregas temos hoje?")
print(f"Resposta: {resposta[:200]}...")

# Teste 2: Consulta sobre memória vitalícia
print("\n=== TESTE 2: Memória Vitalícia ===")
resposta = claude.processar_consulta_real("O que você tem guardado na memória vitalícia?")
print(f"Resposta: {resposta[:200]}...")

# Teste 3: Comando automático
print("\n=== TESTE 3: Comando Automático ===")
resposta = claude.processar_consulta_real("Quero descobrir o projeto atual")
print(f"Resposta: {resposta[:200]}...")

print("\n✅ Testes concluídos!")
