#!/usr/bin/env python3
"""Wrapper fino — resolver_uf (Onda D, 2026-06-01).

Delega a app.resolvedores.resolver_uf_cli. Contrato CLI (flags + JSON) preservado 1:1.
Detalhes: docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md

Uso:
    python resolver_uf.py --uf SP
    python resolver_uf.py --uf RJ --fonte entregas
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def main():
    parser = argparse.ArgumentParser(description='Resolve UF para lista de clientes')
    parser.add_argument('--uf', type=str, required=True, help='Sigla da UF (ex: SP, RJ)')
    parser.add_argument('--fonte', type=str, default='entregas',
                        choices=['carteira', 'separacao', 'entregas'],
                        help='Fonte de dados (default: entregas)')
    parser.add_argument('--limite', type=int, default=100, help='Maximo de registros')
    args = parser.parse_args()

    from app import create_app
    from app.resolvedores import resolver_uf_cli

    app = create_app()
    with app.app_context():
        resultado = resolver_uf_cli(uf=args.uf, fonte=args.fonte, limite=args.limite)

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
