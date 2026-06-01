#!/usr/bin/env python3
"""Wrapper fino — resolver_grupo (Onda D, 2026-06-01).

Delega a app.resolvedores.resolver_grupo_cli (ORM bind-safe — elimina a interpolacao de prefixo
da versao anterior). Contrato CLI (flags + JSON) preservado 1:1.
Detalhes: docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md

Uso:
    python resolver_grupo.py --grupo atacadao
    python resolver_grupo.py --grupo assai --uf SP
    python resolver_grupo.py --grupo atacadao --loja 183
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def main():
    parser = argparse.ArgumentParser(description='Resolve grupo empresarial para CNPJs')
    parser.add_argument('--grupo', type=str, required=True, help='Nome do grupo (atacadao, assai, tenda)')
    parser.add_argument('--uf', type=str, help='Filtrar por UF (ex: SP)')
    parser.add_argument('--loja', type=str, help='Filtrar por identificador de loja (ex: 183)')
    parser.add_argument('--fonte', type=str, default='entregas',
                        choices=['carteira', 'separacao', 'entregas'],
                        help='Fonte de dados (default: entregas)')
    parser.add_argument('--limite', type=int, default=100, help='Maximo de registros')
    args = parser.parse_args()

    from app import create_app
    from app.resolvedores import resolver_grupo_cli

    app = create_app()
    with app.app_context():
        resultado = resolver_grupo_cli(grupo=args.grupo, uf=args.uf, loja=args.loja,
                                       fonte=args.fonte, limite=args.limite)

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
