#!/usr/bin/env python3
"""Wrapper fino — resolver_produto (Onda D, 2026-06-01).

Delega a app.resolvedores.resolver_produto_cli (que usa app.embeddings.product_search.
buscar_produtos_hibrido — SoT de runtime). Contrato CLI (flags + JSON) preservado 1:1.
Detalhes: docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md

Uso:
    python resolver_produto.py --termo "palmito"
    python resolver_produto.py --termo "AZ VF"
    python resolver_produto.py --termo "cogumelo" --modo hibrida
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def main():
    parser = argparse.ArgumentParser(description='Resolve produto por termo ou abreviacao')
    parser.add_argument('--termo', type=str, required=True, help='Nome, abreviacao ou caracteristica do produto')
    parser.add_argument('--limite', type=int, default=50, help='Maximo de registros')
    parser.add_argument('--modo', type=str, default='hibrida',
                        choices=['texto', 'semantica', 'hibrida'],
                        help='Modo de busca: texto (ILIKE), semantica (embeddings), hibrida (ambos)')
    args = parser.parse_args()

    from app import create_app
    from app.resolvedores import resolver_produto_cli

    app = create_app()
    with app.app_context():
        resultado = resolver_produto_cli(termo=args.termo, limite=args.limite, modo=args.modo)

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
