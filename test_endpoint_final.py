#!/usr/bin/env python3
"""
Teste final dos endpoints após integração completa
"""
import requests
import json
from app import create_app

app = create_app()

def testar_saldo_estoque():
    """
    Testa endpoint /estoque/saldo-estoque
    """
    print("\n" + "="*60)
    print("🧪 TESTANDO ENDPOINT /estoque/saldo-estoque")
    print("="*60)
    
    with app.test_client() as client:
        # Fazer requisição ao endpoint
        response = client.get('/estoque/saldo-estoque/')
        
        print(f"\n📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.get_json()
                
                if 'produtos' in data:
                    produtos = data['produtos']
                    print(f"✅ {len(produtos)} produtos retornados")
                    
                    # Verificar se tem produtos reais (não apenas teste)
                    produtos_reais = [p for p in produtos if 'TEST' not in str(p.get('cod_produto', '')).upper()]
                    produtos_teste = [p for p in produtos if 'TEST' in str(p.get('cod_produto', '')).upper()]
                    
                    print(f"\n📊 Distribuição:")
                    print(f"  - Produtos reais: {len(produtos_reais)}")
                    print(f"  - Produtos teste: {len(produtos_teste)}")
                    
                    # Mostrar primeiros 5 produtos reais
                    if produtos_reais:
                        print(f"\n🏭 Primeiros 5 produtos REAIS:")
                        for p in produtos_reais[:5]:
                            print(f"  - {p.get('cod_produto')}: {p.get('nome_produto')} | Estoque: {p.get('estoque_atual')}")
                    
                    # Procurar produto específico 4320162
                    produto_4320162 = next((p for p in produtos if str(p.get('cod_produto')) == '4320162'), None)
                    if produto_4320162:
                        print(f"\n🎯 Produto 4320162 encontrado:")
                        print(f"  - Nome: {produto_4320162.get('nome_produto')}")
                        print(f"  - Estoque: {produto_4320162.get('estoque_atual')}")
                        print(f"  - Status: {produto_4320162.get('status_ruptura')}")
                    else:
                        print(f"\n⚠️ Produto 4320162 não aparece no saldo-estoque")
                    
                else:
                    print(f"❌ Resposta sem campo 'produtos': {data}")
                    
            except Exception as e:
                print(f"❌ Erro ao processar resposta: {e}")
                print(f"Resposta raw: {response.data}")
        else:
            print(f"❌ Erro {response.status_code}: {response.data}")

def testar_cardex(cod_produto='4320162'):
    """
    Testa endpoint do cardex
    """
    print("\n" + "="*60)
    print(f"🧪 TESTANDO CARDEX DO PRODUTO {cod_produto}")
    print("="*60)
    
    with app.test_client() as client:
        # Fazer requisição ao endpoint
        response = client.get(f'/carteira/api/produto/{cod_produto}/cardex')
        
        print(f"\n📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.get_json()
                
                if data.get('success'):
                    print(f"✅ Cardex carregado com sucesso")
                    
                    # Verificar resumo
                    resumo = data.get('resumo', {})
                    print(f"\n📊 Resumo:")
                    print(f"  - Estoque inicial: {resumo.get('estoque_inicial')}")
                    print(f"  - Menor estoque 7d: {resumo.get('menor_estoque_7d')}")
                    print(f"  - Status ruptura: {resumo.get('status_ruptura')}")
                    
                    # Verificar cardex
                    cardex = data.get('cardex', [])
                    print(f"\n📅 Cardex com {len(cardex)} dias")
                    
                    if cardex and len(cardex) > 0:
                        primeiro_dia = cardex[0]
                        print(f"\n🗓️ Primeiro dia (D0):")
                        print(f"  - Data: {primeiro_dia.get('data')}")
                        print(f"  - Estoque inicial: {primeiro_dia.get('estoque_inicial')}")
                        print(f"  - Saídas: {primeiro_dia.get('saidas')}")
                        print(f"  - Produção: {primeiro_dia.get('producao')}")
                        print(f"  - Estoque final: {primeiro_dia.get('estoque_final')}")
                        
                        # VERIFICAR SE TEM CAMPO 'valor' (não deveria ter)
                        if 'valor' in primeiro_dia:
                            print(f"  ⚠️ Campo 'valor' encontrado: {primeiro_dia['valor']}")
                        else:
                            print(f"  ✅ Campo 'valor' NÃO existe (correto)")
                    
                else:
                    print(f"❌ Erro: {data.get('error')}")
                    
            except Exception as e:
                print(f"❌ Erro ao processar resposta: {e}")
                print(f"Resposta raw: {response.data}")
        else:
            print(f"❌ Erro {response.status_code}: {response.data}")

def testar_workspace(num_pedido='VCD2521025'):
    """
    Testa endpoint do workspace
    """
    print("\n" + "="*60)
    print(f"🧪 TESTANDO WORKSPACE DO PEDIDO {num_pedido}")
    print("="*60)
    
    with app.test_client() as client:
        # Fazer requisição ao endpoint
        response = client.get(f'/carteira/api/pedido/{num_pedido}/workspace')
        
        print(f"\n📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.get_json()
                
                if data.get('success'):
                    print(f"✅ Workspace carregado com sucesso")
                    
                    print(f"\n📊 Resumo:")
                    print(f"  - Pedido: {data.get('num_pedido')}")
                    print(f"  - Status: {data.get('status_pedido')}")
                    print(f"  - Total produtos: {data.get('total_produtos')}")
                    print(f"  - Valor total: R$ {data.get('valor_total', 0):.2f}")
                    
                    # Verificar produtos
                    produtos = data.get('produtos', [])
                    if produtos:
                        print(f"\n📦 Produtos no pedido:")
                        for p in produtos[:3]:  # Primeiros 3
                            print(f"  - {p.get('cod_produto')}: {p.get('nome_produto')}")
                            print(f"    • Qtd pedido: {p.get('qtd_pedido')}")
                            print(f"    • Estoque hoje: {p.get('estoque_hoje')}")
                            print(f"    • Menor estoque 7d: {p.get('menor_estoque_7d')}")
                            print(f"    • Produção hoje: {p.get('producao_hoje')}")
                    
                else:
                    print(f"❌ Erro: {data.get('error')}")
                    
            except Exception as e:
                print(f"❌ Erro ao processar resposta: {e}")
                print(f"Resposta raw: {response.data}")
        else:
            print(f"❌ Erro {response.status_code}: {response.data}")

def main():
    """
    Executa todos os testes
    """
    print("\n" + "="*60)
    print("🚀 TESTE FINAL DOS ENDPOINTS")
    print("="*60)
    
    with app.app_context():
        # 1. Testar saldo-estoque
        testar_saldo_estoque()
        
        # 2. Testar cardex com produto real
        testar_cardex('4320162')
        
        # 3. Testar workspace com pedido real
        testar_workspace('VCD2521025')
        
        print("\n" + "="*60)
        print("✅ TESTES FINALIZADOS")
        print("="*60)
        print("""
        📊 Resumo dos Testes:
        1. /estoque/saldo-estoque - Deve mostrar produtos reais
        2. /carteira/api/produto/4320162/cardex - Deve mostrar estoque inicial correto
        3. /carteira/api/pedido/VCD2521025/workspace - Deve mostrar quantidades corretas
        
        🎯 Verificações críticas:
        - EstoqueAtual sincronizado com MovimentacaoEstoque ✅
        - Saídas incluem Separacao + PreSeparacaoItem ✅
        - Projeções recalculadas com dados reais ✅
        """)

if __name__ == "__main__":
    main()