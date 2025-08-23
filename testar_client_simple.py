#!/usr/bin/env python3
"""
Teste do cliente simplificado baseado no script que funciona
"""

import sys
import os
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.portal.atacadao.playwright_client_simple import AtacadaoPlaywrightSimple

def main():
    print("=" * 60)
    print("TESTE DO CLIENTE SIMPLIFICADO")
    print("=" * 60)
    
    client = AtacadaoPlaywrightSimple(headless=False)
    
    try:
        # Iniciar sessão
        client.iniciar_sessao()
        
        # Dados do agendamento (do banco de dados)
        # VCD2520950 -> pedido_cliente = 932955
        pedido_cliente = '932955'
        data_agendamento = '27/08/2025'
        
        # Produtos da Separacao (apenas alguns para teste)
        produtos = [
            {'codigo': '4830176', 'quantidade': 16},
            {'codigo': '4320147', 'quantidade': 16},
            {'codigo': '4320177', 'quantidade': 5},
            {'codigo': '4360177', 'quantidade': 10},
            {'codigo': '4830103', 'quantidade': 16}
        ]
        
        print(f"\n📋 Executando agendamento:")
        print(f"   Pedido: {pedido_cliente}")
        print(f"   Data: {data_agendamento}")
        print(f"   Produtos: {len(produtos)} itens")
        
        # Executar agendamento completo
        resultado = client.criar_agendamento_completo(
            pedido_cliente=pedido_cliente,
            data_agendamento=data_agendamento,
            produtos=produtos
        )
        
        print("\n" + "=" * 60)
        print("RESULTADO:")
        print("=" * 60)
        
        if resultado['success']:
            print(f"✅ SUCESSO!")
            print(f"   Protocolo: {resultado.get('protocolo', 'N/A')}")
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