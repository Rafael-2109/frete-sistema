#!/usr/bin/env python3
"""
Script para testar o mapeamento de endereço do pedido VCD2521559
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.carteira_mapper import CarteiraMapper
import json
from pprint import pprint

def testar_pedido_especifico():
    """Testa o pedido VCD2521559 especificamente"""
    
    print("=" * 80)
    print("TESTE DE MAPEAMENTO - PEDIDO VCD2521559")
    print("=" * 80)
    
    # Conectar ao Odoo
    connection = get_odoo_connection()
    if not connection:
        print("❌ Erro ao conectar com Odoo")
        return
    
    # Buscar o pedido específico
    print("\n📋 Buscando pedido VCD2521559...")
    
    # Primeiro buscar o pedido
    pedido = connection.search_read(
        'sale.order',
        [('name', '=', 'VCD2521559')],
        ['id', 'name', 'partner_id', 'partner_shipping_id', 'carrier_id', 'incoterm', 'state']
    )
    
    if not pedido:
        print("❌ Pedido VCD2521559 não encontrado")
        return
    
    pedido = pedido[0]
    print(f"✅ Pedido encontrado: ID {pedido['id']}")
    
    # Mostrar informações básicas do pedido
    print("\n📊 INFORMAÇÕES DO PEDIDO:")
    print(f"  Nome: {pedido['name']}")
    print(f"  Estado: {pedido.get('state', 'N/A')}")
    print(f"  Cliente ID: {pedido.get('partner_id', 'N/A')}")
    print(f"  Partner Shipping ID: {pedido.get('partner_shipping_id', 'N/A')}")
    print(f"  Carrier ID: {pedido.get('carrier_id', 'N/A')}")
    print(f"  Incoterm (raw): {pedido.get('incoterm', 'N/A')}")
    print(f"  Tipo do Incoterm: {type(pedido.get('incoterm'))}")
    
    # Verificar formato do incoterm
    incoterm = pedido.get('incoterm')
    if isinstance(incoterm, (list, tuple)) and len(incoterm) > 0:
        print(f"  Incoterm ID: {incoterm[0]}")
        print(f"  Incoterm Nome: {incoterm[1] if len(incoterm) > 1 else 'N/A'}")
    
    # Buscar linhas do pedido
    print("\n📦 Buscando linhas do pedido...")
    linhas = connection.search_read(
        'sale.order.line',
        [('order_id', '=', pedido['id'])],
        ['id', 'product_id', 'product_uom_qty', 'qty_saldo', 'price_unit']
    )
    
    print(f"  Encontradas {len(linhas)} linhas")
    
    if linhas:
        # Pegar primeira linha para teste
        linha = linhas[0]
        
        # Simular estrutura de dados como vem do Odoo
        dados_teste = [{
            'order_id': pedido,
            'product_id': linha.get('product_id'),
            'product_uom_qty': linha.get('product_uom_qty'),
            'qty_saldo': linha.get('qty_saldo'),
            'price_unit': linha.get('price_unit')
        }]
        
        # Testar mapeamento
        print("\n🔄 Testando mapeamento com CarteiraMapper...")
        mapper = CarteiraMapper()
        
        # Verificar se deve usar carrier
        deve_usar_carrier = mapper._deve_usar_carrier_para_endereco(incoterm)
        print(f"\n  Deve usar carrier_id? {deve_usar_carrier}")
        
        if deve_usar_carrier:
            print("\n  ✅ REDESPACHO DETECTADO - Buscando dados do CARRIER...")
            
            # Buscar dados do carrier
            if pedido.get('carrier_id'):
                carrier_id = pedido['carrier_id'][0] if isinstance(pedido['carrier_id'], (list, tuple)) else pedido['carrier_id']
                # O carrier_id no pedido já é o res.partner, não delivery.carrier
                # Buscar direto os dados do partner que é a transportadora
                carrier_partner = connection.search_read(
                    'res.partner',
                    [('id', '=', carrier_id)],
                    ['name', 'l10n_br_cnpj', 'zip', 'street', 'l10n_br_endereco_numero', 
                     'l10n_br_endereco_bairro', 'l10n_br_municipio_id', 'phone', 'city', 'state_id']
                )
                
                if carrier_partner:
                    print("\n  📍 DADOS DO CARRIER (TRANSPORTADORA) - QUE DEVEM SER USADOS:")
                    print("  " + "=" * 60)
                    pc = carrier_partner[0]
                    print(f"    Nome: {pc.get('name', 'N/A')}")
                    print(f"    CNPJ: {pc.get('l10n_br_cnpj', 'N/A')}")
                    print(f"    CEP: {pc.get('zip', 'N/A')}")
                    print(f"    Rua: {pc.get('street', 'N/A')}")
                    print(f"    Número: {pc.get('l10n_br_endereco_numero', 'N/A')}")
                    print(f"    Bairro: {pc.get('l10n_br_endereco_bairro', 'N/A')}")
                    print(f"    Cidade: {pc.get('city', 'N/A')}")
                    print(f"    Estado: {pc.get('state_id', 'N/A')}")
                    print(f"    Município ID: {pc.get('l10n_br_municipio_id', 'N/A')}")
                    print(f"    Telefone: {pc.get('phone', 'N/A')}")
                else:
                    print("  ⚠️ Carrier não encontrado")
        
        else:
            print("\n  ℹ️ Pedido normal - Usando partner_shipping_id")
            
        # Buscar dados do partner_shipping para comparação
        if pedido.get('partner_shipping_id'):
            print("\n  📍 DADOS DO PARTNER_SHIPPING (CLIENTE):")
            shipping_id = pedido['partner_shipping_id'][0] if isinstance(pedido['partner_shipping_id'], (list, tuple)) else pedido['partner_shipping_id']
            
            partner_shipping = connection.search_read(
                'res.partner',
                [('id', '=', shipping_id)],
                ['name', 'l10n_br_cnpj', 'zip', 'street', 'l10n_br_endereco_numero', 
                 'l10n_br_endereco_bairro', 'l10n_br_municipio_id', 'phone']
            )
            
            if partner_shipping:
                ps = partner_shipping[0]
                print(f"    Nome: {ps.get('name', 'N/A')}")
                print(f"    CNPJ: {ps.get('l10n_br_cnpj', 'N/A')}")
                print(f"    CEP: {ps.get('zip', 'N/A')}")
                print(f"    Rua: {ps.get('street', 'N/A')}")
                print(f"    Número: {ps.get('l10n_br_endereco_numero', 'N/A')}")
                print(f"    Bairro: {ps.get('l10n_br_endereco_bairro', 'N/A')}")
                print(f"    Município: {ps.get('l10n_br_municipio_id', 'N/A')}")
                print(f"    Telefone: {ps.get('phone', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("TESTE CONCLUÍDO")
    print("=" * 80)

if __name__ == "__main__":
    testar_pedido_especifico()