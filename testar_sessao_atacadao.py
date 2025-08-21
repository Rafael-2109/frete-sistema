#!/usr/bin/env python3
"""
Script para testar a sessão do Atacadão
"""

import sys
import os
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient

def main():
    print("\n" + "="*60)
    print("TESTE DE SESSÃO - PORTAL ATACADÃO")
    print("="*60)
    
    # Verificar se arquivo de sessão existe
    if not os.path.exists("storage_state_atacadao.json"):
        print("\n❌ Sessão não configurada!")
        print("Execute primeiro: python configurar_sessao_atacadao.py")
        return False
    
    print("\n🔍 Verificando sessão salva...")
    
    client = AtacadaoPlaywrightClient(headless=True)
    
    try:
        client.iniciar_sessao()
        
        if client.verificar_login():
            print("✅ Sessão válida - Portal acessível!")
            
            print("\n" + "✅"*30)
            print("TUDO FUNCIONANDO!")
            print("✅"*30)
            print("\nO sistema está pronto para uso!")
            return True
            
        else:
            print("❌ Sessão expirada ou inválida")
            print("Execute novamente: python configurar_sessao_atacadao.py")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar: {e}")
        return False
    finally:
        client.fechar()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)