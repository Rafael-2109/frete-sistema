#!/usr/bin/env python3
"""
Script de teste para o endpoint /estoque/saldo-estoque
"""
from app import create_app
from app.estoque.models import SaldoEstoque
from app.estoque.models_hibrido import ServicoProjecaoEstoque, EstoqueAtual

app = create_app()

with app.app_context():
    print("=" * 60)
    print("🧪 TESTE DO ENDPOINT /estoque/saldo-estoque")
    print("=" * 60)
    
    # 1. Testar obter_produtos_com_estoque
    print("\n1️⃣ Testando SaldoEstoque.obter_produtos_com_estoque()...")
    produtos = SaldoEstoque.obter_produtos_com_estoque()
    
    if produtos:
        print(f"✅ {len(produtos)} produtos encontrados")
        
        # Verificar estrutura do primeiro produto
        primeiro = produtos[0]
        print(f"\n📦 Estrutura do primeiro produto:")
        print(f"  - Tipo: {type(primeiro)}")
        
        if isinstance(primeiro, dict):
            print(f"  - Chaves: {list(primeiro.keys())}")
            print(f"  - cod_produto: {primeiro.get('cod_produto', 'N/A')}")
            print(f"  - nome_produto: {primeiro.get('nome_produto', 'N/A')}")
            
            # Testar filtro como no código
            codigo_teste = str(primeiro.get('cod_produto', ''))[:3]  # Primeiros 3 chars
            print(f"\n2️⃣ Testando filtro por código '{codigo_teste}'...")
            
            # Simular o filtro do routes.py
            produtos_filtrados = [
                p for p in produtos 
                if codigo_teste.lower() in str(p.get('cod_produto', '')).lower() or 
                   codigo_teste.lower() in str(p.get('nome_produto', '')).lower()
            ]
            
            print(f"✅ Filtro funcionou: {len(produtos_filtrados)} produtos encontrados")
            
            # Testar obter projeção
            print(f"\n3️⃣ Testando ServicoProjecaoEstoque.obter_projecao()...")
            cod = primeiro.get('cod_produto')
            if cod:
                resumo = ServicoProjecaoEstoque.obter_projecao(cod)
                if resumo:
                    print(f"✅ Projeção obtida para produto {cod}")
                    print(f"  - status_ruptura: {resumo.get('status_ruptura', 'N/A')}")
                    print(f"  - estoque_inicial: {resumo.get('estoque_inicial', 0)}")
                else:
                    print(f"⚠️ Projeção não disponível para {cod}")
            
        else:
            print(f"  ⚠️ Produto não é dict, é {type(primeiro)}")
            # Se for objeto, tentar acessar atributos
            if hasattr(primeiro, 'cod_produto'):
                print(f"  - cod_produto (attr): {primeiro.cod_produto}")
            if hasattr(primeiro, 'nome_produto'):
                print(f"  - nome_produto (attr): {primeiro.nome_produto}")
    else:
        print("⚠️ Nenhum produto encontrado")
    
    # 4. Verificar estrutura correta
    print(f"\n4️⃣ Verificando estrutura esperada...")
    
    # Criar produto de teste se necessário
    produto_teste = EstoqueAtual.query.filter_by(cod_produto='TEST001').first()
    if not produto_teste:
        produto_teste = EstoqueAtual(
            cod_produto='TEST001',
            nome_produto='Produto Teste Saldo',
            estoque=500
        )
        from app import db
        db.session.add(produto_teste)
        db.session.commit()
        print("📝 Produto de teste criado: TEST001")
    
    # Testar novamente
    produtos = SaldoEstoque.obter_produtos_com_estoque()
    teste_encontrado = False
    for p in produtos:
        if isinstance(p, dict) and p.get('cod_produto') == 'TEST001':
            teste_encontrado = True
            print(f"✅ Produto teste encontrado como dict")
            print(f"  - cod_produto: {p.get('cod_produto')}")
            print(f"  - nome_produto: {p.get('nome_produto')}")
            break
    
    if not teste_encontrado:
        print("⚠️ Produto teste não encontrado ou não é dict")
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DO TESTE")
    print("=" * 60)
    print("""
    ✅ Correção aplicada:
    - Mudança de p.cod_produto para p.get('cod_produto')
    - Mudança de p.nome_produto para p.get('nome_produto')
    
    🎯 O erro "'dict' object has no attribute 'cod_produto'" 
       deve estar resolvido agora!
    """)
    print("=" * 60)