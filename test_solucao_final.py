#!/usr/bin/env python3
"""
Teste final da solução
"""
from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.carteira.utils.workspace_utils import processar_dados_workspace_produto, converter_projecao_para_cardex
from app.estoque.models_hibrido import ServicoProjecaoEstoque

app = create_app()

with app.app_context():
    print("=" * 60)
    print("🧪 TESTE FINAL DA SOLUÇÃO")
    print("=" * 60)
    
    # Testar com produto real 4320162
    produto_codigo = '4320162'
    
    print(f"\n1️⃣ Buscando produto {produto_codigo}...")
    item_carteira = CarteiraPrincipal.query.filter_by(
        cod_produto=produto_codigo
    ).first()
    
    if not item_carteira:
        print(f"❌ Produto não encontrado, tentando pedido VCD2521025...")
        item_carteira = CarteiraPrincipal.query.filter_by(
            num_pedido='VCD2521025'
        ).first()
        if item_carteira:
            produto_codigo = item_carteira.cod_produto
    
    if item_carteira:
        print(f"✅ Produto encontrado: {item_carteira.cod_produto} - {item_carteira.nome_produto}")
        print(f"  - qtd_saldo_produto_pedido: {item_carteira.qtd_saldo_produto_pedido}")
        
        # Obter projeção
        print(f"\n2️⃣ Obtendo projeção...")
        projecao = ServicoProjecaoEstoque.obter_projecao(produto_codigo)
        
        if projecao:
            print(f"✅ Projeção obtida")
            print(f"  - estoque_inicial: {projecao.get('estoque_inicial')}")
            print(f"  - projecao_29_dias: {len(projecao.get('projecao_29_dias', []))} dias")
            
            # Testar processamento do workspace
            print(f"\n3️⃣ Testando processamento do workspace...")
            try:
                dados_workspace = processar_dados_workspace_produto(item_carteira, projecao)
                if dados_workspace:
                    print("✅ Workspace processado com sucesso!")
                    print(f"  - qtd_pedido: {dados_workspace.get('qtd_pedido')}")
                    print(f"  - estoque_hoje: {dados_workspace.get('estoque_hoje')}")
                    print(f"  - producao_hoje: {dados_workspace.get('producao_hoje')}")
                    print(f"  - menor_estoque_7d: {dados_workspace.get('menor_estoque_7d')}")
                else:
                    print("❌ processar_dados_workspace_produto retornou None")
            except AttributeError as e:
                print(f"❌ AttributeError: {e}")
            except Exception as e:
                print(f"❌ Erro: {e}")
                import traceback
                traceback.print_exc()
            
            # Testar cardex
            print(f"\n4️⃣ Testando conversão para cardex...")
            try:
                cardex = converter_projecao_para_cardex(projecao)
                if cardex:
                    print(f"✅ Cardex gerado com {len(cardex)} dias")
                    if cardex:
                        primeiro_dia = cardex[0]
                        print(f"  - Primeiro dia tem chaves: {list(primeiro_dia.keys())}")
                        if 'valor' in primeiro_dia:
                            print(f"  ❌ Campo 'valor' encontrado (não deveria existir)")
                        else:
                            print(f"  ✅ Campo 'valor' NÃO existe (correto)")
                else:
                    print("❌ Cardex vazio")
            except Exception as e:
                print(f"❌ Erro no cardex: {e}")
        else:
            print("❌ Projeção não obtida")
    else:
        print("❌ Nenhum produto encontrado")
    
    print("\n" + "=" * 60)
    print("📊 RESUMO")
    print("=" * 60)
    print("""
    Solução aplicada:
    1. processar_dados_workspace_produto agora aceita tanto:
       - Resultado de query com alias (qtd_pedido)
       - Objeto CarteiraPrincipal (qtd_saldo_produto_pedido)
    
    2. Usa getattr() para verificar campos com fallback
    
    3. Cardex não tem campo 'valor' (correto)
    
    Se este teste passar sem erros, o problema está resolvido!
    """)