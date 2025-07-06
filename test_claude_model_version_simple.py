#!/usr/bin/env python3
"""
Script para testar qual versão do Claude está realmente respondendo
Versão simplificada sem dependências externas
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from anthropic import Anthropic
except ImportError:
    print("ERRO: anthropic não instalado. Execute: pip install anthropic")
    sys.exit(1)

print("\n" + "="*60)
print("🤖 TESTE DE VERSÃO DO CLAUDE 🤖")
print("="*60 + "\n")

# Verificar API key
api_key = os.environ.get('ANTHROPIC_API_KEY')
if not api_key:
    print("❌ ANTHROPIC_API_KEY não configurada no ambiente")
    print("Configure com: export ANTHROPIC_API_KEY='sua-chave-aqui'")
    sys.exit(1)

print("✅ API Key encontrada")
print(f"   Primeiros caracteres: {api_key[:8]}...")

# Testar diferentes modelos
modelos_para_testar = [
    ("claude-sonnet-4-20250514", "Claude 4 Sonnet (maio 2025)"),
    ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet (outubro 2024)"),
    ("claude-3-5-sonnet-latest", "Claude 3.5 Sonnet (latest)"),
    ("claude-3-7-sonnet-20250219", "Claude 3.7 Sonnet (fevereiro 2025)"),
    ("claude-3-7-sonnet-latest", "Claude 3.7 Sonnet (latest)"),
]

client = Anthropic(api_key=api_key)

print("\nTestando modelos disponíveis...\n")

modelos_funcionando = []
modelo_configurado = "claude-sonnet-4-20250514"  # O que está no sistema

for model_id, model_name in modelos_para_testar:
    print(f"🔍 Testando: {model_name}")
    print(f"   ID: {model_id}")
    
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=100,
            messages=[{"role": "user", "content": "Qual é sua versão exata? Responda apenas com sua versão completa (ex: Claude 3.5 Sonnet)."}]
        )
        
        resposta = response.content[0].text.strip()
        print(f"   ✅ Modelo disponível!")
        print(f"   Resposta: {resposta}")
        modelos_funcionando.append((model_id, model_name, resposta))
        
        # Testar se é o modelo configurado
        if model_id == modelo_configurado:
            print(f"   ⭐ ESTE É O MODELO CONFIGURADO NO SISTEMA!")
        print()
        
    except Exception as e:
        error_msg = str(e)
        if "model_not_found" in error_msg or "does not exist" in error_msg:
            print(f"   ❌ Modelo não existe")
        elif "permission" in error_msg.lower():
            print(f"   ⚠️  Sem permissão para usar este modelo")
        elif "Invalid model" in error_msg:
            print(f"   ❌ Modelo inválido")
        else:
            print(f"   ❌ Erro: {error_msg[:100]}...")
        print()

print("="*60)
print("RESUMO DOS RESULTADOS:")
print("="*60)

if modelos_funcionando:
    print(f"\n✅ {len(modelos_funcionando)} modelo(s) funcionando:\n")
    for model_id, model_name, resposta in modelos_funcionando:
        print(f"- {model_name}")
        print(f"  ID: {model_id}")
        print(f"  Responde como: {resposta}")
        if model_id == modelo_configurado:
            print(f"  ⭐ CONFIGURADO NO SISTEMA")
        print()
else:
    print("\n❌ Nenhum modelo funcionou. Verifique:")
    print("- A API key está válida?")
    print("- A conta tem acesso aos modelos Claude?")
    print("- Há limites de uso ou restrições?")

print("="*60)
print("Teste concluído!") 