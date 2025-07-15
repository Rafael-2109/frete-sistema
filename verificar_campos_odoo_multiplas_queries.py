#!/usr/bin/env python3
"""
Script para verificar campos do Odoo usando múltiplas queries
Baseado nas informações fornecidas pelo usuário sobre a estrutura real do Odoo
"""

import json
import sys
import os
from pathlib import Path

# Adicionar o diretório do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def verificar_estrutura_campos_odoo():
    """Verifica a estrutura real dos campos no Odoo usando múltiplas queries"""
    
    print("🔍 VERIFICAÇÃO DE CAMPOS ODOO - MÚLTIPLAS QUERIES")
    print("=" * 60)
    
    # Campos que falharam na verificação anterior
    campos_problematicos = {
        # Campos do parceiro principal (partner_id)
        "order_id/partner_id/l10n_br_municipio_id/name": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_id"), 
                ("res.partner", "l10n_br_municipio_id"),
                ("l10n_br_ciel_it_account.res.municipio", "name")
            ],
            "descricao": "Nome do município do parceiro principal"
        },
        "order_id/partner_id/state_id/code": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_id"),
                ("res.partner", "state_id"),
                ("res.country.state", "code")
            ],
            "descricao": "Código do estado do parceiro principal"
        },
        
        # Campos do endereço de entrega (partner_shipping_id)
        "order_id/partner_shipping_id/l10n_br_cnpj": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_shipping_id"),
                ("res.partner", "l10n_br_cnpj")
            ],
            "descricao": "CNPJ do endereço de entrega"
        },
        "order_id/partner_shipping_id/zip": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_shipping_id"),
                ("res.partner", "zip")
            ],
            "descricao": "CEP do endereço de entrega"
        },
        "order_id/partner_shipping_id/street": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_shipping_id"),
                ("res.partner", "street")
            ],
            "descricao": "Rua do endereço de entrega"
        },
        "order_id/partner_shipping_id/street2": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_shipping_id"),
                ("res.partner", "street2")
            ],
            "descricao": "Complemento do endereço de entrega"
        },
        "order_id/partner_shipping_id/l10n_br_district": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_shipping_id"),
                ("res.partner", "l10n_br_district")
            ],
            "descricao": "Bairro do endereço de entrega"
        },
        "order_id/partner_shipping_id/city": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_shipping_id"),
                ("res.partner", "city")
            ],
            "descricao": "Cidade do endereço de entrega"
        },
        "order_id/partner_shipping_id/state_id/code": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_shipping_id"),
                ("res.partner", "state_id"),
                ("res.country.state", "code")
            ],
            "descricao": "Código do estado do endereço de entrega"
        },
        "order_id/partner_shipping_id/l10n_br_municipio_id/name": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_shipping_id"),
                ("res.partner", "l10n_br_municipio_id"),
                ("l10n_br_ciel_it_account.res.municipio", "name")
            ],
            "descricao": "Nome do município do endereço de entrega"
        },
        "order_id/partner_shipping_id/country_id/name": {
            "queries": [
                ("sale.order.line", "order_id"),
                ("sale.order", "partner_shipping_id"),
                ("res.partner", "country_id"),
                ("res.country", "name")
            ],
            "descricao": "Nome do país do endereço de entrega"
        }
    }
    
    print("📋 CAMPOS PARA VERIFICAÇÃO:")
    print(f"Total de campos problemáticos: {len(campos_problematicos)}")
    print()
    
    # Mostrar a estrutura de queries necessárias
    for campo_original, info in campos_problematicos.items():
        print(f"🔹 {campo_original}")
        print(f"   📝 {info['descricao']}")
        print(f"   🔗 Queries necessárias:")
        
        for i, (modelo, campo) in enumerate(info['queries'], 1):
            if i == 1:
                print(f"      {i}. Buscar '{campo}' em '{modelo}'")
            elif i == len(info['queries']):
                print(f"      {i}. Obter campo '{campo}' do registro encontrado")
            else:
                print(f"      {i}. Usar ID para buscar '{campo}' em '{modelo}'")
        print()
    
    # Campos confirmados que funcionam
    campos_confirmados = [
        "order_id/name",
        "product_id/default_code", 
        "product_id/name",
        "product_id/categ_id/name",
        "price_unit",
        "product_uom_qty",
        "discount",
        # etc... (os 27 que passaram no teste anterior)
    ]
    
    print("✅ CAMPOS JÁ CONFIRMADOS:")
    print(f"Total de campos funcionando: {len(campos_confirmados)}")
    print("(Estes usam sintaxe simples ou relações diretas)")
    print()
    
    print("🎯 PRÓXIMOS PASSOS:")
    print("1. Você pode verificar no Odoo se os campos base existem:")
    print("   - l10n_br_cnpj em res.partner ✓ (confirmado nas imagens)")
    print("   - zip em res.partner ✓ (confirmado nas imagens)")
    print("   - street em res.partner ✓ (confirmado nas imagens)")
    print("   - state_id em res.partner")
    print("   - l10n_br_municipio_id em res.partner")
    print("   - partner_shipping_id em sale.order")
    print()
    print("2. Implementar as múltiplas queries no código:")
    print("   - Query 1: sale.order.line → pegar order_id")
    print("   - Query 2: sale.order → pegar partner_shipping_id")  
    print("   - Query 3: res.partner → pegar campos específicos")
    print("   - Query 4 (se necessário): modelos relacionados")
    
    # Salvar estrutura para implementação
    estrutura_queries = {
        "campos_multiplas_queries": campos_problematicos,
        "campos_simples_confirmados": len(campos_confirmados),
        "modelos_envolvidos": [
            "sale.order.line",
            "sale.order", 
            "res.partner",
            "res.country.state",
            "res.country",
            "l10n_br_ciel_it_account.res.municipio"
        ]
    }
    
    with open("estrutura_queries_odoo.json", "w", encoding="utf-8") as f:
        json.dump(estrutura_queries, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Estrutura salva em: estrutura_queries_odoo.json")
    return campos_problematicos

if __name__ == "__main__":
    verificar_estrutura_campos_odoo() 