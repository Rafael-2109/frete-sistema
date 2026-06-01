#!/usr/bin/env python3
"""Wrapper fino — resolver_cidade (Onda D, 2026-06-01).

Delega a app.resolvedores.resolver_cidade_cli, que corrige o BUG de accent-sensitivity da versao
anterior (agora 'itanhaem' casa 'Itanhaém'). Contrato CLI (flags + JSON) preservado 1:1.
Detalhes: docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md

Uso:
    python resolver_cidade.py --cidade "itanhaem"
    python resolver_cidade.py --cidade "Sao Paulo" --fonte entregas
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def main():
    parser = argparse.ArgumentParser(description='Resolve cidade com normalizacao de acentos')
    parser.add_argument('--cidade', type=str, required=True, help='Nome da cidade (com ou sem acentos)')
    parser.add_argument('--fonte', type=str, default='entregas',
                        choices=['carteira', 'separacao', 'entregas'],
                        help='Fonte de dados (default: entregas)')
    parser.add_argument('--limite', type=int, default=50, help='Maximo de registros')
    args = parser.parse_args()

    from app import create_app
    from app.resolvedores import resolver_cidade_cli

    app = create_app()
    with app.app_context():
        resultado = resolver_cidade_cli(cidade=args.cidade, fonte=args.fonte, limite=args.limite)

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
