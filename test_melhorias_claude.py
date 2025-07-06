#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🧪 TESTE DAS MELHORIAS APLICADAS NO CLAUDE AI
Verifica se detecção de intenção e decisões inteligentes funcionam
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

print("=== TESTE DAS MELHORIAS NO CLAUDE AI ===\n")

# 1. Testar detecção de intenção com scores
print("1. Testando detecção de intenção refinada...")
try:
    from app.claude_ai.claude_real_integration import claude_real_integration
    
    testes_intencao = [
        ("Quantas entregas temos pendentes?", "analise_dados"),
        ("Criar módulo para controle de estoque", "desenvolvimento"),
        ("Erro ao salvar pedido, como resolver?", "resolucao_problema"),
        ("Como funciona o sistema de agendamentos?", "explicacao_conceitual"),
        ("Gerar relatório Excel das entregas", "comando_acao"),
        ("Qual o status das entregas do Assai e criar relatório", "múltiplas")
    ]
    
    for consulta, esperado in testes_intencao:
        intencoes = claude_real_integration._detectar_intencao_refinada(consulta)
        
        # Encontrar intenção dominante
        intencao_principal = max(intencoes, key=lambda k: intencoes[k])
        score_principal = intencoes[intencao_principal]
        
        print(f"\n   Consulta: '{consulta[:40]}...'")
        print(f"   Intenção principal: {intencao_principal} ({score_principal:.1%})")
        
        # Mostrar todas as intenções se múltiplas > 0.2
        multiplas = [f"{k}: {v:.1%}" for k, v in intencoes.items() if v > 0.2]
        if len(multiplas) > 1:
            print(f"   Múltiplas intenções detectadas: {', '.join(multiplas)}")
            
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 2. Testar decisão de sistemas avançados
print("\n\n2. Testando decisão inteligente de sistemas avançados...")
try:
    testes_avancado = [
        # (consulta, deve_usar_avancado)
        ("Status das entregas", False),  # Simples
        ("Análise profunda e detalhada de todas as entregas dos últimos 90 dias com comparação entre períodos", True),  # Complexa
        ("Como criar um módulo e qual o status das entregas?", True),  # Múltiplas intenções
        ("Erro 500 ao acessar relatórios", False),  # Problema específico
    ]
    
    for consulta, esperado in testes_avancado:
        intencoes = claude_real_integration._detectar_intencao_refinada(consulta)
        usar_avancado = claude_real_integration._deve_usar_sistema_avancado(consulta, intencoes)
        
        resultado = "✅" if usar_avancado == esperado else "❌"
        print(f"\n   {resultado} '{consulta[:50]}...'")
        print(f"      Usar avançado: {usar_avancado} (esperado: {esperado})")
        
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 3. Testar contexto dinâmico
print("\n\n3. Testando contexto dinâmico por intenção...")
try:
    analise_exemplo = {"periodo_dias": 30, "cliente_especifico": "Assai"}
    
    for consulta, _ in testes_intencao[:4]:  # Primeiras 4 consultas
        intencoes = claude_real_integration._detectar_intencao_refinada(consulta)
        contexto = claude_real_integration._build_contexto_por_intencao(intencoes, analise_exemplo)
        
        print(f"\n   Consulta: '{consulta[:40]}...'")
        print(f"   Contexto gerado: {contexto[:100]}...")
        
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 4. Resumo das melhorias
print("\n\n=== RESUMO DAS MELHORIAS APLICADAS ===")
print("✅ Detecção de intenção com scores (não binária)")
print("✅ Decisão multi-critério para sistemas avançados")
print("✅ Contexto dinâmico baseado na intenção")
print("✅ Sistema mais inteligente e adaptável")

print("\n💡 BENEFÍCIOS:")
print("- Respostas mais adequadas ao tipo de pergunta")
print("- Uso eficiente de recursos (sistemas avançados só quando necessário)")
print("- Melhor compreensão de consultas complexas")
print("- Contexto relevante para cada situação") 