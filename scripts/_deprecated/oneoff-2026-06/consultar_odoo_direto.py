#!/usr/bin/env python3
"""
Consulta DIRETA ao Odoo para mostrar 5 linhas de produtos
"""

from app.odoo.utils.connection import get_odoo_connection

def consultar_odoo():
    """Consulta direta ao Odoo"""
    print("\n🔄 Conectando ao Odoo...")
    
    # Obter conexão
    connection = get_odoo_connection()
    
    # Autenticar
    uid = connection.authenticate()
    if not uid:
        print("❌ Falha na autenticação")
        return
    
    print("✅ Conectado ao Odoo")
    
    # Buscar 2 pedidos de venda
    print("\n📥 Buscando pedidos no Odoo...")
    pedidos = connection.search_read(
        'sale.order',
        [['state', 'in', ['sale', 'done']]],
        ['name', 'partner_id', 'date_order'],
        limit=2
    )
    
    print(f"📦 {len(pedidos)} pedidos encontrados")
    
    total_linhas = 0
    
    for pedido in pedidos:
        print(f"\n{'='*80}")
        print(f"📋 PEDIDO: {pedido['name']}")
        print(f"   Cliente: {pedido['partner_id'][1] if pedido.get('partner_id') else 'N/A'}")
        print(f"   Data: {pedido.get('date_order', 'N/A')}")
        print(f"{'='*80}")
        
        # Buscar linhas do pedido
        linhas = connection.search_read(
            'sale.order.line',
            [['order_id', '=', pedido['id']]],
            ['product_id', 'product_uom_qty', 'price_unit', 'price_total'],
            limit=3
        )
        
        print(f"   📦 {len(linhas)} linhas no pedido")
        
        # Para cada linha, buscar o produto completo
        for i, linha in enumerate(linhas, 1):
            if total_linhas >= 5:
                break
                
            total_linhas += 1
            
            print(f"\n   {'─'*70}")
            print(f"   📌 LINHA {total_linhas}:")
            print(f"   {'─'*70}")
            
            # Buscar dados COMPLETOS do produto
            if linha.get('product_id'):
                product_id = linha['product_id'][0]
                produto = connection.search_read(
                    'product.product',
                    [['id', '=', product_id]],
                    ['id', 'default_code', 'name', 'barcode', 'categ_id', 'list_price', 'standard_price']
                )
                
                if produto:
                    prod = produto[0]
                    print(f"   🔴 ID Odoo (interno):        {prod['id']}")
                    print(f"   ✅ DEFAULT_CODE (correto):   {prod.get('default_code', 'VAZIO')}")
                    print(f"   📝 Nome Completo:            {prod.get('name', 'N/A')}")
                    print(f"   📊 Código de Barras:         {prod.get('barcode', 'N/A')}")
                    print(f"   📁 Categoria:                {prod['categ_id'][1] if prod.get('categ_id') else 'N/A'}")
                    print(f"   💰 Preço de Lista:           {prod.get('list_price', 0)}")
                    print(f"   💵 Custo Padrão:             {prod.get('standard_price', 0)}")
                else:
                    print(f"   ❌ Produto não encontrado")
            
            print(f"\n   📊 DADOS DA LINHA DO PEDIDO:")
            print(f"   Quantidade:                  {linha.get('product_uom_qty', 0)}")
            print(f"   Preço Unitário:              {linha.get('price_unit', 0)}")
            print(f"   Valor Total:                 {linha.get('price_total', 0)}")
            
        if total_linhas >= 5:
            break
    
    print(f"\n{'='*80}")
    print(f"🎯 RESUMO: {total_linhas} linhas de produtos mostradas do Odoo")
    print(f"{'='*80}")
    
    # Buscar também alguns produtos direto da tabela product.product
    print("\n\n📦 CONSULTA DIRETA NA TABELA DE PRODUTOS:")
    print("="*80)
    
    produtos = connection.search_read(
        'product.product',
        [['sale_ok', '=', True]],  # Produtos que podem ser vendidos
        ['id', 'default_code', 'name', 'barcode'],
        limit=5
    )
    
    for i, prod in enumerate(produtos, 1):
        print(f"\nPRODUTO {i}:")
        print(f"  ID Odoo:      {prod['id']}")
        print(f"  DEFAULT_CODE: {prod.get('default_code', 'VAZIO')}")
        print(f"  Nome:         {prod.get('name', 'N/A')}")
        print(f"  Código Barras:{prod.get('barcode', 'N/A')}")

if __name__ == "__main__":
    consultar_odoo()