#!/usr/bin/env python3
"""
Busca semantica de rotas e templates do sistema.

Uso:
    python .claude/skills/buscando-rotas/scripts/buscar_rotas.py "contas a pagar"
    python .claude/skills/buscando-rotas/scripts/buscar_rotas.py "fretes" --tipo rota_api
    python .claude/skills/buscando-rotas/scripts/buscar_rotas.py "dashboard" --limit 3
"""

import argparse
import json
import os
import sys

# Ajustar path para importar modulos do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def buscar_rotas(query: str, tipo: str = None, limit: int = 10) -> dict:
    """
    Busca semantica em rotas e templates.

    Args:
        query: Texto de busca em linguagem natural
        tipo: Filtro opcional - 'rota_template' ou 'rota_api'
        limit: Maximo de resultados

    Returns:
        Dict com sucesso, query, total e resultados
    """
    from app import create_app
    from app.embeddings.route_template_search import search_routes

    resultado = {
        'sucesso': False,
        'query': query,
        'resultados': [],
        'total': 0,
    }

    app = create_app()
    with app.app_context():
        results = search_routes(query=query, tipo=tipo, limit=limit)
        resultado['sucesso'] = True
        resultado['resultados'] = results
        resultado['total'] = len(results)

    return resultado


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Busca semantica de rotas e templates do sistema'
    )
    parser.add_argument('query', help='Texto de busca em linguagem natural')
    parser.add_argument(
        '--tipo',
        choices=['rota_template', 'rota_api'],
        default=None,
        help='Filtro: rota_template (telas) ou rota_api (APIs)',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Maximo de resultados (default: 10)',
    )
    args = parser.parse_args()

    resultado = buscar_rotas(args.query, args.tipo, args.limit)
    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
