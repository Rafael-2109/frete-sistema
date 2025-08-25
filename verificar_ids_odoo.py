#!/usr/bin/env python3
"""
Script para verificar IDs antes de criar pedido teste
"""

import xmlrpc.client

# Configurações do Odoo
url = 'https://odoo.nacomgoya.com.br'
db = 'odoo-17-ee-nacomgoya-prd'
username = 'rafael@conservascampobelo.com.br'
api_key = '67705b0986ff5c052e657f1c0ffd96ceb191af69'

print("="*60)
print("VERIFICANDO IDs NO ODOO")
print("="*60)

try:
    # Conectar
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, api_key, {})
    
    if not uid:
        print("❌ Erro na autenticação")
        exit(1)
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    print("✅ Conectado ao Odoo\n")
    
    def executar(model, method, *args):
        return models.execute_kw(db, uid, api_key, model, method, *args)
    
    # ========================================================================
    # 1. VERIFICAR CLIENTE (ATACADAO)
    # ========================================================================
    print("1️⃣ BUSCANDO CLIENTE ATACADAO...")
    
    # Buscar por nome
    clientes = executar('res.partner', 'search_read', [
        ['name', 'ilike', 'ATACADAO'],
        ['customer_rank', '>', 0]
    ], {
        'fields': ['id', 'name', 'l10n_br_cnpj', 'state_id'],
        'limit': 5
    })
    
    if clientes:
        print("Clientes encontrados:")
        for c in clientes:
            print(f"  ID: {c['id']} - {c['name']}")
            print(f"     CNPJ: {c.get('l10n_br_cnpj', 'N/A')}")
            print(f"     Estado: {c['state_id'][1] if c.get('state_id') else 'N/A'}")
        
        # Verificar se ID 2124 existe
        cliente_2124 = executar('res.partner', 'search_read', [
            ['id', '=', 2124]
        ], {'fields': ['name', 'l10n_br_cnpj']})
        
        if cliente_2124:
            print(f"\n✅ Cliente ID 2124 existe: {cliente_2124[0]['name']}")
        else:
            print("\n⚠️ Cliente ID 2124 NÃO existe. Use um dos IDs acima.")
    else:
        print("❌ Nenhum cliente ATACADAO encontrado")
    
    # ========================================================================
    # 2. VERIFICAR EMPRESA (NACOM GOYA - CD)
    # ========================================================================
    print("\n2️⃣ BUSCANDO EMPRESAS...")
    
    empresas = executar('res.company', 'search_read', [
        ['name', 'ilike', 'NACOM']
    ], {
        'fields': ['id', 'name'],
        'limit': 5
    })
    
    if empresas:
        print("Empresas encontradas:")
        for e in empresas:
            print(f"  ID: {e['id']} - {e['name']}")
        
        # Verificar se ID 4 existe
        empresa_4 = executar('res.company', 'search_read', [
            ['id', '=', 4]
        ], {'fields': ['name']})
        
        if empresa_4:
            print(f"\n✅ Empresa ID 4 existe: {empresa_4[0]['name']}")
        else:
            print("\n⚠️ Empresa ID 4 NÃO existe. Use um dos IDs acima.")
    else:
        print("❌ Nenhuma empresa NACOM encontrada")
    
    # ========================================================================
    # 3. VERIFICAR PRODUTO (LIMAO TAHITI)
    # ========================================================================
    print("\n3️⃣ BUSCANDO PRODUTOS...")
    
    produtos = executar('product.product', 'search_read', [
        ['name', 'ilike', 'LIMAO']
    ], {
        'fields': ['id', 'name', 'default_code'],
        'limit': 5
    })
    
    if produtos:
        print("Produtos encontrados:")
        for p in produtos:
            print(f"  ID: {p['id']} - {p['name']}")
            print(f"     Código: {p.get('default_code', 'N/A')}")
        
        # Verificar se ID 24 existe
        produto_24 = executar('product.product', 'search_read', [
            ['id', '=', 24]
        ], {'fields': ['name', 'default_code']})
        
        if produto_24:
            print(f"\n✅ Produto ID 24 existe: {produto_24[0]['name']}")
        else:
            print("\n⚠️ Produto ID 24 NÃO existe. Use um dos IDs acima.")
    else:
        print("❌ Nenhum produto LIMAO encontrado")
    
    # ========================================================================
    # 4. VERIFICAR POSIÇÃO FISCAL
    # ========================================================================
    print("\n4️⃣ BUSCANDO POSIÇÕES FISCAIS...")
    
    posicoes = executar('account.fiscal.position', 'search_read', [
        ['name', 'ilike', 'TRANSFERÊNCIA']
    ], {
        'fields': ['id', 'name'],
        'limit': 5
    })
    
    if posicoes:
        print("Posições fiscais encontradas:")
        for p in posicoes:
            print(f"  ID: {p['id']} - {p['name']}")
        
        # Verificar se ID 49 existe
        posicao_49 = executar('account.fiscal.position', 'search_read', [
            ['id', '=', 49]
        ], {'fields': ['name']})
        
        if posicao_49:
            print(f"\n✅ Posição Fiscal ID 49 existe: {posicao_49[0]['name']}")
        else:
            print("\n⚠️ Posição Fiscal ID 49 NÃO existe. Use um dos IDs acima.")
    else:
        print("❌ Nenhuma posição fiscal de TRANSFERÊNCIA encontrada")
    
    # ========================================================================
    # 5. VERIFICAR ARMAZÉM
    # ========================================================================
    print("\n5️⃣ BUSCANDO ARMAZÉNS...")
    
    armazens = executar('stock.warehouse', 'search_read', [], {
        'fields': ['id', 'name', 'code'],
        'limit': 10
    })
    
    if armazens:
        print("Armazéns encontrados:")
        for a in armazens:
            print(f"  ID: {a['id']} - {a['name']} ({a.get('code', 'N/A')})")
    
    # ========================================================================
    # 6. VERIFICAR INCOTERM
    # ========================================================================
    print("\n6️⃣ BUSCANDO INCOTERMS...")
    
    incoterms = executar('account.incoterms', 'search_read', [
        ['code', '=', 'CIF']
    ], {
        'fields': ['id', 'name', 'code'],
        'limit': 5
    })
    
    if incoterms:
        print("Incoterm CIF encontrado:")
        for i in incoterms:
            print(f"  ID: {i['id']} - {i['code']} - {i['name']}")
    else:
        # Buscar todos os incoterms
        todos_incoterms = executar('account.incoterms', 'search_read', [], {
            'fields': ['id', 'name', 'code'],
            'limit': 10
        })
        
        if todos_incoterms:
            print("Incoterms disponíveis:")
            for i in todos_incoterms:
                print(f"  ID: {i['id']} - {i['code']} - {i['name']}")
    
    # ========================================================================
    # 7. VERIFICAR PAYMENT PROVIDER
    # ========================================================================
    print("\n7️⃣ BUSCANDO FORMAS DE PAGAMENTO...")
    
    # Tentar payment.provider
    try:
        providers = executar('payment.provider', 'search_read', [
            ['name', 'ilike', 'Transferência']
        ], {
            'fields': ['id', 'name'],
            'limit': 5
        })
        
        if providers:
            print("Payment Providers encontrados:")
            for p in providers:
                print(f"  ID: {p['id']} - {p['name']}")
    except:
        print("payment.provider não encontrado, tentando payment.acquirer...")
        
        # Tentar payment.acquirer (versões antigas)
        try:
            acquirers = executar('payment.acquirer', 'search_read', [
                ['name', 'ilike', 'Transferência']
            ], {
                'fields': ['id', 'name'],
                'limit': 5
            })
            
            if acquirers:
                print("Payment Acquirers encontrados:")
                for a in acquirers:
                    print(f"  ID: {a['id']} - {a['name']}")
        except:
            print("Modelo de payment não encontrado")
    
    print("\n" + "="*60)
    print("VERIFICAÇÃO CONCLUÍDA")
    print("="*60)
    print("\n⚠️ Ajuste os IDs no script fase1_criar_pedido_teste.py conforme necessário")
    
except Exception as e:
    print(f"❌ Erro: {e}")