#!/usr/bin/env python
"""
Testar produto 4310164
"""
import os
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.carteira.utils.workspace_utils import processar_dados_workspace_produto
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from datetime import date
import logging

# Desabilitar logs desnecessários
logging.getLogger('app').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)
logging.getLogger('apscheduler').setLevel(logging.ERROR)

app = create_app()

with app.app_context():
    # Buscar produto 4310164
    produto = db.session.query(CarteiraPrincipal).filter(
        CarteiraPrincipal.cod_produto == '4310164',
        CarteiraPrincipal.ativo == True
    ).first()
    
    if produto:
        print(f"Produto encontrado no pedido: {produto.num_pedido}")
        print(f"Código: {produto.cod_produto}")
        print(f"Nome: {produto.nome_produto}")
        print(f"Qtd Pedido: {produto.qtd_saldo_produto_pedido}")
        
        # Obter projeção completa
        projecao = ServicoEstoqueTempoReal.get_projecao_completa(produto.cod_produto, dias=30)
        
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
                print(f"\nDados do workspace:")
                print(f"  estoque_hoje: {dados_workspace.get('estoque_hoje')}")
                print(f"  menor_estoque_7d: {dados_workspace.get('menor_estoque_7d')}")
                print(f"  data_disponibilidade: {dados_workspace.get('data_disponibilidade')}")
                print(f"  qtd_disponivel: {dados_workspace.get('qtd_disponivel')}")
                
                # Calcular D+X
                hoje = date.today()
                if dados_workspace.get('data_disponibilidade'):
                    try:
                        ano, mes, dia = dados_workspace['data_disponibilidade'].split('-')
                        data_disp = date(int(ano), int(mes), int(dia))
                        dias_ate = (data_disp - hoje).days
                        print(f"  Dias até disponível: D+{dias_ate}")
                    except:
                        pass
            
            # Mostrar projeção detalhada
            print(f"\nProjeção dos próximos dias (mostrando Saldo):")
            print(f"Hoje: {date.today()}")
            for dia in projecao['projecao'][:25]:
                if dia['entrada'] > 0 or dia['saida'] > 0 or dia['dia'] in [0, 18, 19, 20]:
                    print(f"  D{dia['dia']:2d} ({dia['data']}): Entrada {dia['entrada']:6.0f}, Saída {dia['saida']:6.0f} → Saldo {dia['saldo_final']:7.0f}")
        else:
            print("❌ Sem projeção disponível")
    else:
        print("❌ Produto 4310164 não encontrado na carteira")