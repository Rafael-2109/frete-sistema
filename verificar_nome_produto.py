#!/usr/bin/env python3
"""
Script simplificado para verificar a origem do nome incorreto do produto
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import CadastroPalletizacao

def verificar_inconsistencia():
    print("\n" + "="*80)
    print("ANÁLISE DA INCONSISTÊNCIA DO NOME DO PRODUTO 4850103")
    print("="*80 + "\n")
    
    # 1. Nome na Carteira
    item_carteira = CarteiraPrincipal.query.filter_by(cod_produto='4850103').first()
    nome_carteira = item_carteira.nome_produto if item_carteira else "Não encontrado"
    
    # 2. Nome no Cadastro
    cadastro = CadastroPalletizacao.query.filter_by(cod_produto='4850103').first()
    nome_cadastro = cadastro.nome_produto if cadastro else "Não encontrado"
    
    print("📊 COMPARAÇÃO DOS NOMES:\n")
    print(f"1. CarteiraPrincipal (importado do Odoo):")
    print(f"   → {nome_carteira}")
    print(f"   ⚠️ Contém '(cópia)': {'SIM' if '(cópia)' in nome_carteira else 'NÃO'}")
    print(f"   ⚠️ Contém código [4850103]: {'SIM' if '[4850103]' in nome_carteira else 'NÃO'}")
    
    print(f"\n2. CadastroPalletizacao (cadastro de produtos):")
    print(f"   → {nome_cadastro}")
    print(f"   ✅ Nome correto: {'SIM' if '(cópia)' not in nome_cadastro else 'NÃO'}")
    
    print("\n" + "="*80)
    print("DIAGNÓSTICO DO PROBLEMA:")
    print("="*80 + "\n")
    
    print("""
O problema está na importação da carteira do Odoo!

📍 LOCAL DO ERRO:
   Arquivo: app/odoo/services/carteira_service.py
   Linha: 421
   
📝 CÓDIGO ATUAL (INCORRETO):
   'nome_produto': extrair_relacao(linha.get('product_id'), 1),
   
   Isso pega o nome do array product_id que vem assim:
   [29927, "[4850103] MAIONESE - POTE 6X3 KG - ST ISABEL (cópia)"]
   
❌ PROBLEMA:
   O Odoo está retornando o nome com "(cópia)" no array product_id
   quando deveria retornar o nome correto do produto.

✅ SOLUÇÃO PROPOSTA:
   Usar o campo 'name' do produto buscado separadamente:
   
   'nome_produto': produto.get('name', '') or extrair_relacao(linha.get('product_id'), 1),
   
   Isso usaria o nome correto: "MAIONESE - POTE 6X3 KG - CAMPO BELO"
   
🔧 ALTERNATIVA:
   Atualizar o CadastroPalletizacao com o nome correto quando
   o produto for criado automaticamente durante a importação.
""")

def main():
    app = create_app()
    with app.app_context():
        verificar_inconsistencia()

if __name__ == "__main__":
    main()