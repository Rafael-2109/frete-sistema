#!/usr/bin/env python3
"""
Script de teste para validar a lógica de mapeamento de endereços
quando incoterm = RED ou [RED] REDESPACHO
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.odoo.utils.carteira_mapper import CarteiraMapper
import json
from pprint import pprint

def criar_dados_teste():
    """Cria dados de teste simulando diferentes cenários"""
    
    dados_teste = [
        # Cenário 1: Incoterm normal (deve usar partner_shipping_id)
        {
            "order_id": {
                "name": "PED001",
                "incoterm": "CIF",
                "partner_shipping_id": {
                    "l10n_br_cnpj": "11.111.111/0001-11",
                    "name": "Cliente Normal LTDA",
                    "zip": "01000-000",
                    "l10n_br_municipio_id": {"name": "São Paulo"},
                    "l10n_br_endereco_bairro": "Centro",
                    "street": "Rua do Cliente",
                    "l10n_br_endereco_numero": "100",
                    "phone": "(11) 1111-1111"
                },
                "carrier_id": {
                    "l10n_br_cnpj": "99.999.999/0001-99",
                    "name": "Transportadora XYZ",
                    "zip": "09999-999",
                    "l10n_br_municipio_id": {"name": "Santo André"},
                    "l10n_br_endereco_bairro": "Industrial",
                    "street": "Av. das Transportadoras",
                    "l10n_br_endereco_numero": "999",
                    "phone": "(11) 9999-9999"
                }
            },
            "product_id": {"default_code": "PROD001"},
            "product_uom_qty": 100
        },
        
        # Cenário 2: Incoterm = RED (deve usar carrier_id)
        {
            "order_id": {
                "name": "PED002",
                "incoterm": "RED",
                "partner_shipping_id": {
                    "l10n_br_cnpj": "22.222.222/0001-22",
                    "name": "Cliente Direto LTDA",
                    "zip": "02000-000",
                    "l10n_br_municipio_id": {"name": "Rio de Janeiro"},
                    "l10n_br_endereco_bairro": "Copacabana",
                    "street": "Av. Atlântica",
                    "l10n_br_endereco_numero": "200",
                    "phone": "(21) 2222-2222"
                },
                "carrier_id": {
                    "l10n_br_cnpj": "88.888.888/0001-88",
                    "name": "Redespacho Sul Transportes",
                    "zip": "08888-888",
                    "l10n_br_municipio_id": {"name": "Curitiba"},
                    "l10n_br_endereco_bairro": "Batel",
                    "street": "Rua do Redespacho",
                    "l10n_br_endereco_numero": "888",
                    "phone": "(41) 8888-8888"
                }
            },
            "product_id": {"default_code": "PROD002"},
            "product_uom_qty": 200
        },
        
        # Cenário 3: Incoterm = [RED] REDESPACHO (deve usar carrier_id)
        {
            "order_id": {
                "name": "PED003", 
                "incoterm": "[RED] REDESPACHO",
                "partner_shipping_id": {
                    "l10n_br_cnpj": "33.333.333/0001-33",
                    "name": "Cliente Final SA",
                    "zip": "03000-000",
                    "l10n_br_municipio_id": {"name": "Belo Horizonte"},
                    "l10n_br_endereco_bairro": "Savassi",
                    "street": "Rua da Bahia",
                    "l10n_br_endereco_numero": "300",
                    "phone": "(31) 3333-3333"
                },
                "carrier_id": {
                    "l10n_br_cnpj": "77.777.777/0001-77",
                    "name": "Logística Centro-Oeste",
                    "zip": "07777-777",
                    "l10n_br_municipio_id": {"name": "Brasília"},
                    "l10n_br_endereco_bairro": "Asa Sul",
                    "street": "SQS 777",
                    "l10n_br_endereco_numero": "777",
                    "phone": "(61) 7777-7777"
                }
            },
            "product_id": {"default_code": "PROD003"},
            "product_uom_qty": 300
        },
        
        # Cenário 4: Sem incoterm (deve usar partner_shipping_id por padrão)
        {
            "order_id": {
                "name": "PED004",
                "partner_shipping_id": {
                    "l10n_br_cnpj": "44.444.444/0001-44",
                    "name": "Cliente Sem Incoterm",
                    "zip": "04000-000",
                    "l10n_br_municipio_id": {"name": "Porto Alegre"},
                    "l10n_br_endereco_bairro": "Moinhos de Vento",
                    "street": "Rua Padre Chagas",
                    "l10n_br_endereco_numero": "400",
                    "phone": "(51) 4444-4444"
                },
                "carrier_id": {
                    "l10n_br_cnpj": "66.666.666/0001-66",
                    "name": "Express Sul",
                    "zip": "06666-666",
                    "l10n_br_municipio_id": {"name": "Florianópolis"},
                    "l10n_br_endereco_bairro": "Centro",
                    "street": "Av. Beira Mar",
                    "l10n_br_endereco_numero": "666",
                    "phone": "(48) 6666-6666"
                }
            },
            "product_id": {"default_code": "PROD004"},
            "product_uom_qty": 400
        }
    ]
    
    return dados_teste

def testar_mapeamento():
    """Testa o mapeamento com diferentes cenários"""
    
    print("=" * 80)
    print("TESTE DE MAPEAMENTO DE ENDEREÇOS - INCOTERM RED/REDESPACHO")
    print("=" * 80)
    
    # Criar instância do mapper
    mapper = CarteiraMapper()
    
    # Criar dados de teste
    dados_teste = criar_dados_teste()
    
    # Processar dados
    resultado = mapper.mapear_para_carteira(dados_teste)
    
    # Analisar resultados
    for i, item in enumerate(resultado):
        dados_originais = dados_teste[i]
        incoterm = dados_originais.get("order_id", {}).get("incoterm", "N/A")
        
        print(f"\n{'-' * 40}")
        print(f"CENÁRIO {i+1}: Pedido {item.get('num_pedido')}")
        print(f"Incoterm: {incoterm}")
        print(f"{'-' * 40}")
        
        # Comparar endereços
        print("\n📍 ENDEREÇO DE ENTREGA MAPEADO:")
        campos_endereco = [
            ('CNPJ', 'cnpj_endereco_ent'),
            ('Empresa', 'empresa_endereco_ent'),
            ('CEP', 'cep_endereco_ent'),
            ('Cidade', 'nome_cidade'),
            ('Bairro', 'bairro_endereco_ent'),
            ('Rua', 'rua_endereco_ent'),
            ('Número', 'endereco_ent'),
            ('Telefone', 'telefone_endereco_ent')
        ]
        
        for label, campo in campos_endereco:
            valor = item.get(campo, 'N/A')
            print(f"  {label:10}: {valor}")
        
        # Mostrar de onde veio o endereço
        print("\n📦 DADOS ORIGINAIS:")
        
        # Partner Shipping
        partner_data = dados_originais.get("order_id", {}).get("partner_shipping_id", {})
        print(f"\n  Partner Shipping (Cliente):")
        print(f"    Nome: {partner_data.get('name', 'N/A')}")
        print(f"    CNPJ: {partner_data.get('l10n_br_cnpj', 'N/A')}")
        
        # Carrier
        carrier_data = dados_originais.get("order_id", {}).get("carrier_id", {})
        print(f"\n  Carrier (Transportadora):")
        print(f"    Nome: {carrier_data.get('name', 'N/A')}")
        print(f"    CNPJ: {carrier_data.get('l10n_br_cnpj', 'N/A')}")
        
        # Validação
        print("\n✅ VALIDAÇÃO:")
        
        # Determinar qual deveria ser usado
        deve_usar_carrier = incoterm in ["RED", "[RED] REDESPACHO"]
        
        if deve_usar_carrier:
            # Comparar com dados do carrier
            cnpj_esperado = carrier_data.get('l10n_br_cnpj')
            cnpj_obtido = item.get('cnpj_endereco_ent')
            
            if cnpj_obtido == cnpj_esperado:
                print(f"  ✅ CORRETO: Usando dados do CARRIER (transportadora)")
            else:
                print(f"  ❌ ERRO: Deveria usar CARRIER mas está usando PARTNER_SHIPPING")
                print(f"     Esperado: {cnpj_esperado}")
                print(f"     Obtido: {cnpj_obtido}")
        else:
            # Comparar com dados do partner_shipping
            cnpj_esperado = partner_data.get('l10n_br_cnpj')
            cnpj_obtido = item.get('cnpj_endereco_ent')
            
            if cnpj_obtido == cnpj_esperado:
                print(f"  ✅ CORRETO: Usando dados do PARTNER_SHIPPING (cliente)")
            else:
                print(f"  ❌ ERRO: Deveria usar PARTNER_SHIPPING mas está usando CARRIER")
                print(f"     Esperado: {cnpj_esperado}")
                print(f"     Obtido: {cnpj_obtido}")
    
    print("\n" + "=" * 80)
    print("TESTE CONCLUÍDO")
    print("=" * 80)

if __name__ == "__main__":
    testar_mapeamento()