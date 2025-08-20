#!/usr/bin/env python
"""Confirmar bug no TabelaFreteManager"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.fretes.models import Frete
from app.utils.tabela_frete_manager import TabelaFreteManager

app = create_app()

with app.app_context():
    frete = Frete.query.order_by(Frete.id.desc()).first()
    
    print("PROBLEMA IDENTIFICADO:")
    print(f"  frete.valor_cte (campo errado): {frete.valor_cte}")
    print(f"  frete.tabela_valor_cte (campo correto): {frete.tabela_valor_cte}")
    
    print("\nO que o Manager está fazendo:")
    print("  1. Verifica hasattr(frete, 'valor_cte'): True")
    print("  2. Pega getattr(frete, 'valor_cte'): None")
    print("  3. Converte None para 0")
    
    print("\nO que deveria fazer:")
    print("  1. O frete NÃO é uma TabelaFrete, então deveria ir para o else")
    print("  2. Deveria pegar tabela_valor_cte")
    
    # Testar fix temporário
    print("\nTESTE DE CORREÇÃO:")
    
    # Forçar o manager a não encontrar o campo sem prefixo
    dados_corretos = {}
    for campo in TabelaFreteManager.CAMPOS:
        # Para Frete, sempre usar prefixo tabela_
        campo_com_prefixo = f'tabela_{campo}' if campo != 'modalidade' else campo
        valor = getattr(frete, campo_com_prefixo, 0)
        dados_corretos[campo] = valor or 0
    
    print(f"  valor_cte corrigido: R$ {dados_corretos.get('valor_cte', 0):.2f}")
    
    print("\n" + "="*60)
    print("CONFIRMAÇÃO DO BUG:")
    
    # Usar o manager atual
    dados_bugados = TabelaFreteManager.preparar_dados_tabela(frete)
    print(f"  Manager atual retorna valor_cte: R$ {dados_bugados.get('valor_cte', 0):.2f}")
    print(f"  Deveria retornar: R$ {frete.tabela_valor_cte:.2f}")
    
    if dados_bugados.get('valor_cte', 0) != frete.tabela_valor_cte:
        print("\n❌ BUG CONFIRMADO: Manager está pegando o campo errado!")