#!/usr/bin/env python3
"""
Script para verificar como os dados DE-PARA estão armazenados no banco
"""

import os
import sys

# Adicionar o caminho do projeto
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.portal.sendas.models import ProdutoDeParaSendas

def main():
    """Verificar mapeamentos"""
    
    app = create_app()
    
    with app.app_context():
        print("\n=== VERIFICANDO MAPEAMENTOS DE-PARA ===\n")
        
        # Buscar alguns exemplos
        mapeamentos = ProdutoDeParaSendas.query.limit(10).all()
        
        print("Primeiros 10 mapeamentos no banco:")
        print("-" * 80)
        for m in mapeamentos:
            print(f"codigo_nosso: {m.codigo_nosso:10} | codigo_sendas: {m.codigo_sendas:10} | CNPJ: {m.cnpj_cliente}")
        
        print("\n" + "=" * 80)
        
        # Verificar especificamente o código 4230162
        print("\n=== BUSCANDO CÓDIGO 4230162 ===\n")
        
        # Buscar onde codigo_nosso = '4230162'
        resultado1 = ProdutoDeParaSendas.query.filter_by(codigo_nosso='4230162').all()
        print(f"Registros onde codigo_nosso='4230162': {len(resultado1)}")
        for r in resultado1:
            print(f"  - codigo_sendas: {r.codigo_sendas}, CNPJ: {r.cnpj_cliente}")
        
        # Buscar onde codigo_sendas = '4230162'
        resultado2 = ProdutoDeParaSendas.query.filter_by(codigo_sendas='4230162').all()
        print(f"\nRegistros onde codigo_sendas='4230162': {len(resultado2)}")
        for r in resultado2:
            print(f"  - codigo_nosso: {r.codigo_nosso}, CNPJ: {r.cnpj_cliente}")
        
        print("\n" + "=" * 80)
        
        # Verificar especificamente o código 92003
        print("\n=== BUSCANDO CÓDIGO 92003 ===\n")
        
        # Buscar onde codigo_nosso = '92003'
        resultado3 = ProdutoDeParaSendas.query.filter_by(codigo_nosso='92003').all()
        print(f"Registros onde codigo_nosso='92003': {len(resultado3)}")
        for r in resultado3:
            print(f"  - codigo_sendas: {r.codigo_sendas}, CNPJ: {r.cnpj_cliente}")
        
        # Buscar onde codigo_sendas = '92003'
        resultado4 = ProdutoDeParaSendas.query.filter_by(codigo_sendas='92003').all()
        print(f"\nRegistros onde codigo_sendas='92003': {len(resultado4)}")
        for r in resultado4:
            print(f"  - codigo_nosso: {r.codigo_nosso}, CNPJ: {r.cnpj_cliente}")
        
        print("\n" + "=" * 80)
        
        # Testar o método obter_codigo_sendas
        print("\n=== TESTANDO MÉTODO obter_codigo_sendas ===\n")
        
        # Teste 1: Com nosso código
        codigo_sendas = ProdutoDeParaSendas.obter_codigo_sendas('4230162')
        print(f"obter_codigo_sendas('4230162') = {codigo_sendas}")
        
        # Teste 2: Com código do Sendas (para ver se está invertido)
        codigo_sendas2 = ProdutoDeParaSendas.obter_codigo_sendas('92003')
        print(f"obter_codigo_sendas('92003') = {codigo_sendas2}")
        
        print("\n" + "=" * 80)
        
        # Testar o método obter_nosso_codigo
        print("\n=== TESTANDO MÉTODO obter_nosso_codigo ===\n")
        
        # Teste 1: Com código do Sendas
        nosso_codigo = ProdutoDeParaSendas.obter_nosso_codigo('92003')
        print(f"obter_nosso_codigo('92003') = {nosso_codigo}")
        
        # Teste 2: Com nosso código (para ver se está invertido)
        nosso_codigo2 = ProdutoDeParaSendas.obter_nosso_codigo('4230162')
        print(f"obter_nosso_codigo('4230162') = {nosso_codigo2}")
        

if __name__ == "__main__":
    main()