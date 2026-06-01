#!/usr/bin/env python3
"""Wrapper fino — resolver_transportadora (Onda D, 2026-06-01).

Delega a app.resolvedores.resolver_transportadora. Contrato CLI (flags + JSON) preservado 1:1.
Detalhes: docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md

Uso:
    python resolver_transportadora.py --termo "TAC"
    python resolver_transportadora.py --termo "Transmerc"
    python resolver_transportadora.py --termo "45.543.915"
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def main():
    parser = argparse.ArgumentParser(description='Resolver transportadora por nome ou CNPJ')
    parser.add_argument('--termo', required=True, help='Nome parcial ou CNPJ')
    parser.add_argument('--limite', type=int, default=10, help='Maximo de resultados')
    args = parser.parse_args()

    from app import create_app
    from app.resolvedores import resolver_transportadora

    app = create_app()
    with app.app_context():
        resultado = resolver_transportadora(args.termo, limite=args.limite)

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
