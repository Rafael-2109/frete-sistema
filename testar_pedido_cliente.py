#!/usr/bin/env python3
"""
Script para testar se o pedido_cliente está sendo passado corretamente
"""

import sys
import os
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient

def main():
    print("=" * 60)
    print("TESTE DO PEDIDO_CLIENTE")
    print("=" * 60)
    
    client = AtacadaoPlaywrightClient(headless=False)
    
    try:
        # 1. Fazer login se necessário
        print("\n1. Verificando sessão...")
        if not client.verificar_sessao_ativa():
            print("   Sessão expirada, fazendo login...")
            if not client.fazer_login_com_captcha():
                print("❌ Erro no login")
                return
        
        # 2. Criar agendamento usando pedido_cliente
        print("\n2. Testando criar_agendamento com pedido_cliente...")
        
        # Dados do agendamento (como vem do routes.py)
        dados = {
            'pedido_cliente': '932955',  # Esse é o valor correto da CarteiraPrincipal
            'cnpj': '00.063.960/0035-40',
            'data_agendamento': '27/08/2025',
            'peso_total': 10.25,
            'produtos': [
                {'codigo': '4830176', 'quantidade': 16},
                {'codigo': '4320147', 'quantidade': 16},
                {'codigo': '4320177', 'quantidade': 5},
                {'codigo': '4360177', 'quantidade': 10},
                {'codigo': '4830103', 'quantidade': 16},
                {'codigo': '4510145', 'quantidade': 9},
                {'codigo': '4810146', 'quantidade': 5},
                {'codigo': '4880103', 'quantidade': 5},
                {'codigo': '4840103', 'quantidade': 5},
                {'codigo': '4820112', 'quantidade': 4},
                {'codigo': '4070176', 'quantidade': 5},
                {'codigo': '4870112', 'quantidade': 8}
            ]
        }
        
        print(f"\n📋 Dados sendo enviados:")
        print(f"   pedido_cliente: {dados['pedido_cliente']}")
        print(f"   data_agendamento: {dados['data_agendamento']}")
        print(f"   peso_total: {dados['peso_total']} kg")
        print(f"   produtos: {len(dados['produtos'])} itens")
        
        # Chamar o método criar_agendamento (como faz o routes.py)
        resultado = client.criar_agendamento(dados)
        
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