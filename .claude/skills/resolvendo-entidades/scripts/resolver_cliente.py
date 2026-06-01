#!/usr/bin/env python3
"""Wrapper fino — resolver_cliente (Onda D, 2026-06-01).

Delega a app.resolvedores.resolver_cliente_cli. Contrato CLI (flags + JSON) preservado 1:1.
Logica consolidada em app/resolvedores/. Detalhes:
docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md

Uso:
    python resolver_cliente.py --termo "Supermercado Bom Preco"
    python resolver_cliente.py --termo "45.543.915"
    python resolver_cliente.py --termo "Padaria" --fonte entregas
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def main():
    parser = argparse.ArgumentParser(description='Resolve cliente por CNPJ ou nome')
    parser.add_argument('--termo', type=str, required=True, help='CNPJ parcial ou nome do cliente')
    parser.add_argument('--fonte', type=str, default='entregas',
                        choices=['carteira', 'separacao', 'entregas'],
                        help='Fonte de dados (default: entregas)')
    parser.add_argument('--limite', type=int, default=50, help='Maximo de registros')
    args = parser.parse_args()

    from app import create_app
    from app.resolvedores import resolver_cliente_cli

    app = create_app()
    with app.app_context():
        resultado = resolver_cliente_cli(termo=args.termo, fonte=args.fonte, limite=args.limite)

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
