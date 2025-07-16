"""
Script de diagnóstico para verificar os campos do Odoo
Identifica o formato correto dos dados de município, estado, incoterm, etc.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection

def diagnosticar_campos_odoo():
    """Analisa os campos do Odoo para identificar formatos corretos"""
    
    app = create_app()
    with app.app_context():
        connection = get_odoo_connection()
        
        if not connection:
            print("❌ Não foi possível conectar ao Odoo")
            return
        
        print("🔍 DIAGNÓSTICO DE CAMPOS DO ODOO\n")
        
        # 1. Verificar formato de municípios
        print("=" * 80)
        print("1️⃣ ANÁLISE DE MUNICÍPIOS (l10n_br_ciel_it_account.res.municipio)")
        print("=" * 80)
        
        municipios = connection.search_read(
            'l10n_br_ciel_it_account.res.municipio',
            [('name', 'ilike', 'Fortaleza')],
            ['id', 'name', 'state_id'],
            limit=5
        )
        
        print("\nMunicípios encontrados:")
        for mun in municipios:
            print(f"\nID: {mun['id']}")
            print(f"Nome: {mun['name']}")
            print(f"Estado (state_id): {mun.get('state_id')}")
        
        # 2. Verificar formato de estados
        print("\n" + "=" * 80)
        print("2️⃣ ANÁLISE DE ESTADOS (res.country.state)")
        print("=" * 80)
        
        # Buscar alguns estados principais para ver o campo code
        estados_principais = connection.search_read(
            'res.country.state',
            [('country_id.code', '=', 'BR')],
            ['id', 'name', 'code', 'country_id'],
            limit=10
        )
        
        print("\nEstados brasileiros:")
        for estado in estados_principais:
            print(f"ID: {estado['id']:3} | Código: {estado.get('code', 'N/A'):5} | Nome: {estado['name']}")
        
        # Se encontramos um município com state_id, vamos buscar detalhes
        if municipios and municipios[0].get('state_id'):
            state_id = municipios[0]['state_id'][0] if isinstance(municipios[0]['state_id'], list) else municipios[0]['state_id']
            
            estados = connection.search_read(
                'res.country.state',
                [('id', '=', state_id)],
                ['id', 'name', 'code', 'country_id']
            )
            
            if estados:
                estado = estados[0]
                print(f"\nEstado do município Fortaleza:")
                print(f"ID: {estado['id']}")
                print(f"Nome: {estado['name']}")
                print(f"Código (UF): {estado.get('code')}")
                print(f"País: {estado.get('country_id')}")
        
        # 3. Verificar um partner com endereço completo
        print("\n" + "=" * 80)
        print("3️⃣ ANÁLISE DE PARTNER (res.partner)")
        print("=" * 80)
        
        partners = connection.search_read(
            'res.partner',
            [('l10n_br_municipio_id', '!=', False)],
            ['id', 'name', 'l10n_br_cnpj', 'l10n_br_municipio_id', 'state_id', 
             'city', 'street', 'l10n_br_endereco_numero', 'l10n_br_endereco_bairro'],
            limit=3
        )
        
        for partner in partners:
            print(f"\n🏢 Partner: {partner['name']}")
            print(f"CNPJ: {partner.get('l10n_br_cnpj')}")
            print(f"Município (l10n_br_municipio_id): {partner.get('l10n_br_municipio_id')}")
            print(f"Estado (state_id): {partner.get('state_id')}")
            print(f"Cidade (city): {partner.get('city')}")
            print(f"Rua: {partner.get('street')}")
            print(f"Número: {partner.get('l10n_br_endereco_numero')}")
            print(f"Bairro: {partner.get('l10n_br_endereco_bairro')}")
        
        # 4. Verificar formato de incoterms
        print("\n" + "=" * 80)
        print("4️⃣ ANÁLISE DE INCOTERMS (account.incoterms)")
        print("=" * 80)
        
        incoterms = connection.search_read(
            'account.incoterms',
            [],
            ['id', 'name', 'code'],
            limit=10
        )
        
        print("\nIncoterms disponíveis:")
        for inco in incoterms:
            print(f"ID: {inco['id']:3} | Código: {inco.get('code', 'N/A'):10} | Nome: {inco['name']}")
        
        # 5. Verificar uma fatura real
        print("\n" + "=" * 80)
        print("5️⃣ ANÁLISE DE FATURA (account.move)")
        print("=" * 80)
        
        faturas = connection.search_read(
            'account.move',
            [('state', '=', 'posted'), ('move_type', '=', 'out_invoice')],
            ['id', 'name', 'invoice_origin', 'invoice_incoterm_id'],
            limit=3
        )
        
        for fatura in faturas:
            print(f"\n📄 Fatura: {fatura['name']}")
            print(f"Origem: {fatura.get('invoice_origin')}")
            print(f"Incoterm: {fatura.get('invoice_incoterm_id')}")
            
            # Verificar tamanho dos campos
            if fatura.get('name'):
                print(f"  └─ Tamanho número NF: {len(fatura['name'])} caracteres")
            if fatura.get('invoice_origin'):
                print(f"  └─ Tamanho origem: {len(fatura['invoice_origin'])} caracteres")
        
        # 6. Verificar pedido de venda
        print("\n" + "=" * 80)
        print("6️⃣ ANÁLISE DE PEDIDO DE VENDA (sale.order)")
        print("=" * 80)
        
        pedidos = connection.search_read(
            'sale.order',
            [('state', '!=', 'cancel')],
            ['id', 'name', 'incoterm'],
            limit=3
        )
        
        for pedido in pedidos:
            print(f"\n📋 Pedido: {pedido['name']}")
            print(f"Incoterm: {pedido.get('incoterm')}")

        # 7. Testar acesso direto aos campos relacionados
        print("\n" + "=" * 80)
        print("7️⃣ TESTE DE ACESSO DIRETO AOS CAMPOS RELACIONADOS")
        print("=" * 80)
        
        # Buscar um pedido com município
        pedidos_teste = connection.search_read(
            'sale.order',
            [('partner_id.l10n_br_municipio_id', '!=', False)],
            ['id', 'name', 'partner_id'],
            limit=1
        )
        
        if pedidos_teste:
            pedido_teste = pedidos_teste[0]
            partner_id = pedido_teste['partner_id'][0] if isinstance(pedido_teste['partner_id'], list) else pedido_teste['partner_id']
            
            # Tentar buscar com campos expandidos
            print("\n📋 Teste 1: Buscar partner com campos expandidos")
            partners_expandidos = connection.search_read(
                'res.partner',
                [('id', '=', partner_id)],
                ['name', 'l10n_br_municipio_id', 'l10n_br_municipio_id.name', 
                 'state_id', 'state_id.code', 'state_id.name']
            )
            
            if partners_expandidos:
                partner = partners_expandidos[0]
                print(f"Partner: {partner['name']}")
                print(f"Município ID: {partner.get('l10n_br_municipio_id')}")
                print(f"Município Nome (direto): {partner.get('l10n_br_municipio_id.name', 'N/A')}")
                print(f"Estado ID: {partner.get('state_id')}")
                print(f"Estado Code (direto): {partner.get('state_id.code', 'N/A')}")
                print(f"Estado Nome (direto): {partner.get('state_id.name', 'N/A')}")

if __name__ == "__main__":
    diagnosticar_campos_odoo() 