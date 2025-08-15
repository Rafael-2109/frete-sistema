#!/usr/bin/env python3
"""
Script para verificar como o produto 4850103 está na carteira e de onde vem o nome
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import CadastroPalletizacao
from app.odoo.utils.connection import get_odoo_connection
from sqlalchemy import func

def verificar_produto_carteira(cod_produto='4850103'):
    """Verifica como o produto está em diferentes tabelas"""
    
    print(f"\n{'='*80}")
    print(f"VERIFICANDO PRODUTO {cod_produto} EM TODAS AS TABELAS")
    print(f"{'='*80}\n")
    
    # 1. Verificar na CarteiraPrincipal
    print("1️⃣ CARTEIRA PRINCIPAL:")
    print("-" * 40)
    
    itens_carteira = CarteiraPrincipal.query.filter_by(
        cod_produto=cod_produto
    ).limit(5).all()
    
    if itens_carteira:
        print(f"✅ Encontrados {len(itens_carteira)} itens na carteira:")
        for item in itens_carteira:
            print(f"\n   Pedido: {item.num_pedido}")
            print(f"   Código: {item.cod_produto}")
            print(f"   📝 Nome: {item.nome_produto}")
            print(f"   Quantidade: {item.qtd_saldo_produto_pedido}")
            print(f"   Cliente: {item.raz_social_red}")
    else:
        print("❌ Produto não encontrado na carteira")
    
    # 2. Verificar no CadastroPalletizacao
    print("\n2️⃣ CADASTRO DE PALLETIZAÇÃO:")
    print("-" * 40)
    
    cadastro = CadastroPalletizacao.query.filter_by(
        cod_produto=cod_produto
    ).first()
    
    if cadastro:
        print(f"✅ Produto encontrado no cadastro:")
        print(f"   Código: {cadastro.cod_produto}")
        print(f"   📝 Nome: {cadastro.nome_produto}")
        print(f"   Palletização: {cadastro.palletizacao}")
        print(f"   Peso Bruto: {cadastro.peso_bruto}")
    else:
        print("❌ Produto não encontrado no cadastro de palletização")
    
    # 3. Buscar direto no Odoo para comparar
    print("\n3️⃣ DADOS ATUAIS NO ODOO:")
    print("-" * 40)
    
    connection = get_odoo_connection()
    if connection:
        # Buscar o produto
        produtos = connection.search_read(
            'product.product',
            [('default_code', '=', cod_produto)],
            ['id', 'name', 'default_code', 'display_name']
        )
        
        if produtos:
            produto = produtos[0]
            print(f"✅ Produto no Odoo:")
            print(f"   ID: {produto['id']}")
            print(f"   Código: {produto.get('default_code')}")
            print(f"   📝 Nome: {produto.get('name')}")
            print(f"   Display Name: {produto.get('display_name')}")
            
            # Buscar em uma linha de pedido recente
            print("\n4️⃣ LINHA DE PEDIDO RECENTE NO ODOO:")
            print("-" * 40)
            
            linhas = connection.search_read(
                'sale.order.line',
                [('product_id', '=', produto['id'])],
                ['id', 'product_id', 'name', 'order_id'],
                limit=1,
                order='id desc'
            )
            
            if linhas:
                linha = linhas[0]
                print(f"✅ Linha de pedido mais recente:")
                print(f"   ID da linha: {linha['id']}")
                print(f"   Pedido: {linha.get('order_id')}")
                print(f"   Product ID (array): {linha.get('product_id')}")
                print(f"   📝 Descrição na linha: {linha.get('name')}")
                
                # Verificar como o product_id vem
                if isinstance(linha.get('product_id'), list):
                    print(f"\n   ⚠️ ATENÇÃO: product_id vem como array!")
                    print(f"   Array completo: {linha.get('product_id')}")
                    print(f"   Índice [0] (ID): {linha.get('product_id')[0]}")
                    print(f"   Índice [1] (Nome): {linha.get('product_id')[1]}")
                    print(f"\n   🔴 Este é o nome que está sendo usado na importação!")
    
    # 5. Comparar os nomes
    print("\n5️⃣ ANÁLISE COMPARATIVA DOS NOMES:")
    print("-" * 40)
    
    nomes = {}
    
    if itens_carteira:
        nomes['Carteira'] = itens_carteira[0].nome_produto
    
    if cadastro:
        nomes['Cadastro'] = cadastro.nome_produto
    
    if connection and produtos:
        nomes['Odoo (product.name)'] = produtos[0].get('name')
        
        if linhas and isinstance(linhas[0].get('product_id'), list):
            nomes['Odoo (product_id[1])'] = linhas[0].get('product_id')[1]
    
    if nomes:
        print("📊 Comparação dos nomes encontrados:")
        for origem, nome in nomes.items():
            print(f"   {origem:25} → {nome}")
        
        # Verificar se tem diferenças
        valores_unicos = set(nomes.values())
        if len(valores_unicos) > 1:
            print("\n   🔴 INCONSISTÊNCIA DETECTADA! Os nomes são diferentes!")
            print("   Possível causa: Importação está usando product_id[1] da linha")
            print("   em vez do campo 'name' do produto.")
    
    # 6. Verificar se o nome tem "(cópia)"
    print("\n6️⃣ VERIFICAÇÃO DE '(cópia)' NO NOME:")
    print("-" * 40)
    
    for origem, nome in nomes.items():
        if nome and '(cópia)' in nome:
            print(f"   ⚠️ {origem} contém '(cópia)': {nome}")
    
    # 7. Sugestão de correção
    print("\n7️⃣ SUGESTÃO DE CORREÇÃO:")
    print("-" * 40)
    
    print("""
   O problema está em app/odoo/services/carteira_service.py linha 421:
   
   ATUAL (incorreto):
   'nome_produto': extrair_relacao(linha.get('product_id'), 1),
   
   CORRETO seria:
   'nome_produto': produto.get('name', '') or extrair_relacao(linha.get('product_id'), 1),
   
   Isso usaria o nome do produto da tabela product.product,
   não o nome que vem no array product_id da linha do pedido.
   """)

def main():
    app = create_app()
    
    with app.app_context():
        verificar_produto_carteira('4850103')
        
        print("\n" + "="*80)
        print("VERIFICAÇÃO CONCLUÍDA")
        print("="*80)

if __name__ == "__main__":
    main()