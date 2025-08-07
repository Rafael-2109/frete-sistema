#!/usr/bin/env python
"""
Script para testar API do workspace
"""

from app import create_app
import json

app = create_app()

with app.app_context():
    with app.test_client() as client:
        # Fazer login primeiro (se necessário)
        from app.auth.models import Usuario
        from flask_login import login_user
        
        # Buscar um usuário admin
        user = Usuario.query.filter_by(email='admin@admin.com').first()
        if not user:
            user = Usuario.query.first()
        
        if user:
            # Simular login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
        
        # Testar API do workspace para um pedido
        response = client.get('/carteira/api/pedido/PED-2025-1234/workspace')
        
        if response.status_code == 200:
            data = response.get_json()
            if data.get('success'):
                print("✅ API retornou com sucesso")
                print(f"Pedido: {data.get('num_pedido')}")
                print(f"Total de produtos: {data.get('total_produtos')}")
                
                # Verificar primeiro produto
                if data.get('produtos'):
                    produto = data['produtos'][0]
                    print(f"\nPrimeiro produto: {produto.get('cod_produto')}")
                    print(f"  Nome: {produto.get('nome_produto')}")
                    print(f"  Estoque Hoje: {produto.get('estoque_hoje')}")
                    print(f"  Menor Estoque D+7: {produto.get('menor_estoque_7d')}")
                    print(f"  Data Disponibilidade: {produto.get('data_disponibilidade')}")
                    print(f"  Qtd Disponível: {produto.get('qtd_disponivel')}")
                    
                    # Imprimir JSON completo do primeiro produto
                    print(f"\nJSON completo do produto:")
                    print(json.dumps(produto, indent=2, default=str))
            else:
                print(f"❌ API retornou erro: {data.get('error')}")
        else:
            print(f"❌ Status code: {response.status_code}")
            print(f"Response: {response.get_data(as_text=True)}")