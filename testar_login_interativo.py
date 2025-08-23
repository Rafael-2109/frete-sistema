#!/usr/bin/env python3
"""
Script para testar o login interativo com CAPTCHA
Demonstra como o sistema funciona quando a sessão expira
"""

import sys
import os
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app.portal.atacadao.login_interativo import LoginInterativoAtacadao, garantir_sessao_antes_operacao

def main():
    print("\n" + "🔐"*30)
    print("TESTE DE LOGIN INTERATIVO - PORTAL ATACADÃO")
    print("🔐"*30)
    
    print("\nEste teste demonstra:")
    print("1. Detecção de sessão expirada")
    print("2. Pré-preenchimento de credenciais (se configuradas)")
    print("3. Login com resolução manual de CAPTCHA")
    print("4. Salvamento automático da sessão")
    print("\n" + "="*60)
    
    # Verificar se tem credenciais configuradas
    tem_credenciais = bool(os.environ.get('ATACADAO_USUARIO') and os.environ.get('ATACADAO_SENHA'))
    
    if tem_credenciais:
        usuario = os.environ.get('ATACADAO_USUARIO')
        print(f"✅ Credenciais encontradas para: {usuario}")
        print("   As credenciais serão pré-preenchidas automaticamente")
    else:
        print("⚠️  Credenciais não configuradas")
        print("   Configure ATACADAO_USUARIO e ATACADAO_SENHA no .env")
        print("   Você precisará digitar manualmente no navegador")
    
    print("\n" + "="*60)
    
    escolha = input("\nEscolha uma opção:\n1. Verificar status da sessão\n2. Forçar novo login\n3. Testar garantir_sessao_antes_operacao()\n\nOpção: ")
    
    login_manager = LoginInterativoAtacadao()
    
    if escolha == "1":
        print("\n🔍 Verificando status da sessão...")
        status = login_manager.verificar_necessidade_login()
        
        print("\nResultado:")
        print(f"  Precisa login: {status['precisa_login']}")
        print(f"  Tem CAPTCHA: {status.get('tem_captcha', 'N/A')}")
        print(f"  Mensagem: {status['mensagem']}")
        
        if status['precisa_login']:
            fazer_login = input("\nDeseja fazer login agora? (s/n): ")
            if fazer_login.lower() == 's':
                resultado = login_manager.abrir_janela_login_usuario()
                print(f"\nResultado do login: {resultado}")
    
    elif escolha == "2":
        print("\n🔄 Forçando novo login...")
        resultado = login_manager.abrir_janela_login_usuario()
        
        if resultado['sucesso']:
            print("\n✅ Login realizado com sucesso!")
            print("   Sessão salva em: storage_state_atacadao.json")
        else:
            print(f"\n❌ Login falhou: {resultado['mensagem']}")
    
    elif escolha == "3":
        print("\n🛡️ Testando garantir_sessao_antes_operacao()...")
        print("Esta função é chamada automaticamente antes de operações no portal")
        
        sucesso = garantir_sessao_antes_operacao()
        
        if sucesso:
            print("\n✅ Sessão garantida com sucesso!")
            print("   Operações no portal podem prosseguir")
        else:
            print("\n❌ Não foi possível garantir sessão")
    
    else:
        print("\nOpção inválida")

if __name__ == "__main__":
    main()