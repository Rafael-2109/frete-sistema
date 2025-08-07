#!/usr/bin/env python
"""
Debug workspace
"""
import os
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.carteira.utils.workspace_utils import processar_dados_workspace_produto
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
import logging

# Desabilitar logs desnecessários
logging.getLogger('app').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)
logging.getLogger('apscheduler').setLevel(logging.ERROR)

app = create_app()

with app.app_context():
    # Buscar um pedido com produto 4520145
    produto = db.session.query(CarteiraPrincipal).filter(
        CarteiraPrincipal.cod_produto == '4520145',
        CarteiraPrincipal.ativo == True
    ).first()
    
    if produto:
        print(f"Produto encontrado no pedido: {produto.num_pedido}")
        print(f"Código: {produto.cod_produto}")
        print(f"Nome: {produto.nome_produto}")
        print(f"Qtd Pedido: {produto.qtd_saldo_produto_pedido}")
        
        # Obter projeção completa
        projecao = ServicoEstoqueTempoReal.get_projecao_completa(produto.cod_produto)
        
        if projecao:
            print(f"\nProjeção completa:")
            print(f"  Estoque Atual: {projecao['estoque_atual']}")
            print(f"  Menor Estoque D7: {projecao['menor_estoque_d7']}")
            print(f"  Data Disponível: {projecao.get('data_disponivel')}")
            print(f"  Qtd Disponível: {projecao.get('qtd_disponivel')}")
            
            # Processar com workspace_utils
            print(f"\nProcessando com workspace_utils...")
            dados_workspace = processar_dados_workspace_produto(produto, projecao)
            
            if dados_workspace:
                print(f"Dados do workspace:")
                print(f"  estoque_hoje: {dados_workspace.get('estoque_hoje')}")
                print(f"  menor_estoque_7d: {dados_workspace.get('menor_estoque_7d')}")
                print(f"  data_disponibilidade: {dados_workspace.get('data_disponibilidade')}")
                print(f"  qtd_disponivel: {dados_workspace.get('qtd_disponivel')}")
            else:
                print("❌ Erro ao processar dados do workspace")
        else:
            print("❌ Sem projeção disponível")
    else:
        print("❌ Produto 4520145 não encontrado na carteira")