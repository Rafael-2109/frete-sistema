#!/usr/bin/env python3
"""
Script para configurar sessão do Atacadão
Só precisa rodar uma vez para fazer login
"""

import sys
import os
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient

def main():
    print("\n" + "🚀"*30)
    print("CONFIGURAÇÃO DE SESSÃO - PORTAL ATACADÃO")
    print("🚀"*30)
    print("\nEste script vai:")
    print("1. Abrir o navegador")
    print("2. Você faz login manualmente")
    print("3. A sessão é salva para uso futuro")
    print("\n" + "="*60)
    
    resposta = input("\nDeseja continuar? (s/n): ")
    
    if resposta.lower() != 's':
        print("Cancelado.")
        return
    
    print("\n🌐 Abrindo navegador...")
    print("⚠️ NÃO FECHE O NAVEGADOR até fazer login completo!\n")
    
    client = AtacadaoPlaywrightClient(headless=False)
    
    if client.fazer_login_manual():
        print("\n" + "✅"*30)
        print("SESSÃO CONFIGURADA COM SUCESSO!")
        print("✅"*30)
        print("\nAgora você pode:")
        print("1. Testar: python testar_sessao_atacadao.py")
        print("2. Usar o sistema normalmente")
        print("\nA sessão fica salva em: storage_state_atacadao.json")
        print("Validade: geralmente 24-48 horas (depende do portal)")
    else:
        print("\n❌ Erro ao configurar sessão")

if __name__ == "__main__":
    main()