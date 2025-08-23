#!/usr/bin/env python3
"""
Script de teste para verificar o clique no botão Salvar
"""

import sys
import os
from datetime import datetime
from app.portal.routes_sessao import verificar_sessao

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient

def main():
    print("=" * 60)
    print("TESTE DO BOTÃO SALVAR - ATACADÃO")
    print("=" * 60)
    
    client = AtacadaoPlaywrightClient(headless=False)
    
    try:
        # 1. Fazer login se necessário
        print("\n1. Verificando sessão...")
        if not verificar_sessao('atacadao'):
            print("   Sessão expirada, fazendo login...")
            if not client.fazer_login_com_captcha():
                print("❌ Erro no login")
                return
        
        # 2. Criar agendamento para o pedido 932955
        print("\n2. Criando agendamento para pedido 932955...")
        
        # Dados do agendamento
        dados = {
            'data_agendamento': '27/08/2025',
            'peso_total': 6705,  # 6.7 toneladas
            'produtos': [
                {
                    'codigo': '30000027',
                    'quantidade': 600,
                    'peso': 6705
                }
            ]
        }
        
        # Criar agendamento
        resultado = client.criar_agendamento_completo(
            pedido_cliente='932955',
            data_agendamento='27/08/2025',
            produtos=dados['produtos']
        )
        
        print("\n" + "=" * 60)
        print("RESULTADO DO TESTE:")
        print("=" * 60)
        
        if resultado['success']:
            print(f"✅ SUCESSO!")
            print(f"   Protocolo: {resultado.get('protocolo', 'N/A')}")
            print(f"   ID Carga: {resultado.get('id_carga', 'N/A')}")
            print(f"   Mensagem: {resultado.get('message', '')}")
        else:
            print(f"❌ FALHA!")
            print(f"   Mensagem: {resultado.get('message', 'Erro desconhecido')}")
            
            # Se falhou, verificar logs detalhados
            print("\n📋 DIAGNÓSTICO DO BOTÃO SALVAR:")
            print("   Verifique os logs acima para ver:")
            print("   - Se o botão #salvar foi encontrado")
            print("   - Se estava visível e habilitado")
            print("   - Quais métodos de clique foram tentados")
            print("   - Se houve mudança de URL após o clique")
        
        print("\n" + "=" * 60)
        
        # Aguardar antes de fechar
        input("\nPressione ENTER para fechar o navegador...")
        
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.fechar()
        print("\n✅ Navegador fechado")

if __name__ == "__main__":
    main()