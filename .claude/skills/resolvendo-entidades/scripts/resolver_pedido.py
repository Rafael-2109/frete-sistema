#!/usr/bin/env python3
"""Wrapper fino — resolver_pedido (Onda D, 2026-06-01).

Delega a app.resolvedores.resolver_pedido_cli. Contrato CLI (flags + JSON) preservado 1:1.
Detalhes: docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md

Uso:
    python resolver_pedido.py --termo "VCD123"
    python resolver_pedido.py --termo "123" --fonte carteira
    python resolver_pedido.py --termo "atacadao 183" --fonte separacao
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def main():
    parser = argparse.ArgumentParser(description='Resolve pedido por numero ou termo')
    parser.add_argument('--termo', type=str, required=True, help='Numero parcial ou termo de busca')
    parser.add_argument('--fonte', type=str, default='ambos',
                        choices=['carteira', 'separacao', 'ambos'],
                        help='Fonte de dados (default: ambos)')
    parser.add_argument('--limite', type=int, default=50, help='Maximo de registros')
    args = parser.parse_args()

    from app import create_app
    from app.resolvedores import resolver_pedido_cli

    app = create_app()
    with app.app_context():
        resultado = resolver_pedido_cli(termo=args.termo, fonte=args.fonte, limite=args.limite)

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
