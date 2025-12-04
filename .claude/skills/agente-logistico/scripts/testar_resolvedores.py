#!/usr/bin/env python3
"""
Script de teste para validar resolvedores.
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from resolver_entidades import resolver_grupo, resolver_uf

def decimal_default(obj):
    from decimal import Decimal
    from datetime import date, datetime
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def teste_resolver_grupo():
    print("=== TESTE 1: resolver_grupo('atacadao') ===")
    resultado = resolver_grupo('atacadao')
    print(json.dumps(resultado, indent=2, default=decimal_default))
    print()

    print("=== TESTE 2: resolver_grupo('atacadao', uf='SP', loja='183') ===")
    resultado = resolver_grupo('atacadao', uf='SP', loja='183')
    print(json.dumps(resultado, indent=2, default=decimal_default))
    print()

    print("=== TESTE 3: resolver_grupo('assai') ===")
    resultado = resolver_grupo('assai')
    print(json.dumps(resultado, indent=2, default=decimal_default))
    print()

def teste_resolver_uf():
    print("=== TESTE 4: resolver_uf('SP') ===")
    resultado = resolver_uf('SP')
    print(f"Total pedidos: {resultado.get('resumo', {}).get('total_pedidos')}")
    print(f"Total valor: R$ {resultado.get('resumo', {}).get('total_valor'):,.2f}")
    print(f"Cidades: {resultado.get('resumo', {}).get('cidades')}")
    print()

if __name__ == '__main__':
    from app import create_app
    app = create_app()

    with app.app_context():
        teste_resolver_grupo()
        teste_resolver_uf()
