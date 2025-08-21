#!/usr/bin/env python
"""
Script para testar busca de pedido no portal Atacadão
"""

import sys
from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

def testar_busca(numero_pedido="892784"):
    """Testa busca de pedido no portal"""
    print(f"\n🔍 TESTANDO BUSCA DO PEDIDO {numero_pedido}")
    print("=" * 50)
    
    try:
        # Criar cliente
        client = AtacadaoPlaywrightClient(headless=False)  # Modo visível para debug
        
        # Iniciar sessão
        print("1. Iniciando sessão...")
        client.iniciar_sessao()
        
        # Verificar login
        print("2. Verificando login...")
        if not client.verificar_login():
            print("❌ Não está logado! Execute: python configurar_sessao_atacadao.py")
            client.fechar()
            return False
        
        print("✅ Login OK")
        
        # Buscar pedido
        print(f"3. Buscando pedido {numero_pedido}...")
        encontrado = client.buscar_pedido(numero_pedido)
        
        if encontrado:
            print(f"✅ PEDIDO {numero_pedido} ENCONTRADO!")
            # Tirar screenshot
            client.page.screenshot(path=f"pedido_{numero_pedido}.png")
            print(f"📸 Screenshot salvo: pedido_{numero_pedido}.png")
        else:
            print(f"❌ PEDIDO {numero_pedido} NÃO ENCONTRADO!")
            print("\nPossíveis razões:")
            print("1. O pedido não existe no portal")
            print("2. O pedido foi cancelado ou excluído")
            print("3. O número está incorreto")
            print("\nVerifique o campo 'pedido_cliente' na CarteiraPrincipal")
        
        # Fechar
        client.fechar()
        return encontrado
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Pegar número do pedido da linha de comando se fornecido
    if len(sys.argv) > 1:
        numero = sys.argv[1]
    else:
        numero = input("Digite o número do pedido (ou ENTER para usar 892784): ").strip()
        if not numero:
            numero = "892784"
    
    resultado = testar_busca(numero)
    
    if resultado:
        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("\n⚠️ TESTE FALHOU - Verifique os logs acima")
        print("\n💡 DICA: Para testar com outro pedido, execute:")
        print(f"   python {sys.argv[0]} <numero_pedido>")