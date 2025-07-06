#!/usr/bin/env python3
"""
Script para testar qual versão do Claude está realmente respondendo
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from anthropic import Anthropic
from colorama import init, Fore, Style
init(autoreset=True)

print(f"""
{Fore.CYAN}{'='*60}
{Fore.YELLOW}🤖 TESTE DE VERSÃO DO CLAUDE 🤖
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
""")

# Verificar API key
api_key = os.environ.get('ANTHROPIC_API_KEY')
if not api_key:
    print(f"{Fore.RED}❌ ANTHROPIC_API_KEY não configurada no ambiente{Style.RESET_ALL}")
    print("Configure com: export ANTHROPIC_API_KEY='sua-chave-aqui'")
    sys.exit(1)

print(f"{Fore.GREEN}✅ API Key encontrada{Style.RESET_ALL}")

# Testar diferentes modelos
modelos_para_testar = [
    ("claude-sonnet-4-20250514", "Claude 4 Sonnet (maio 2025)"),
    ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet (outubro 2024)"),
    ("claude-3-5-sonnet-latest", "Claude 3.5 Sonnet (latest)"),
    ("claude-3-7-sonnet-20250219", "Claude 3.7 Sonnet (fevereiro 2025)"),
    ("claude-3-7-sonnet-latest", "Claude 3.7 Sonnet (latest)"),
]

client = Anthropic(api_key=api_key)

print(f"\n{Fore.BLUE}Testando modelos disponíveis...{Style.RESET_ALL}\n")

for model_id, model_name in modelos_para_testar:
    print(f"🔍 Testando: {model_name}")
    print(f"   ID: {model_id}")
    
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=50,
            messages=[{"role": "user", "content": "Qual é sua versão exata? Responda apenas com sua versão."}]
        )
        
        resposta = response.content[0].text
        print(f"   {Fore.GREEN}✅ Modelo disponível!{Style.RESET_ALL}")
        print(f"   Resposta: {resposta[:100]}")
        print()
        
    except Exception as e:
        error_msg = str(e)
        if "model_not_found" in error_msg or "does not exist" in error_msg:
            print(f"   {Fore.RED}❌ Modelo não existe{Style.RESET_ALL}")
        elif "permission" in error_msg.lower():
            print(f"   {Fore.YELLOW}⚠️ Sem permissão para usar este modelo{Style.RESET_ALL}")
        else:
            print(f"   {Fore.RED}❌ Erro: {error_msg[:100]}{Style.RESET_ALL}")
        print()

print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
print(f"{Fore.YELLOW}Teste concluído!{Style.RESET_ALL}") 