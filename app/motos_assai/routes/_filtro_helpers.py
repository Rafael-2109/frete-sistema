"""Helpers compartilhados para filtros de listagem (chassi + modelo).

Usado pelas telas que incluem o partial
`motos_assai/partials/_filtro_chassi_modelo.html`: Recibo, Montagem,
Disponibilizar, Separacao, Carregamento, Faturamento.

Modulo prefixado com `_` e SEM rotas — nao e registrado no blueprint
(imports em routes/__init__.py sao explicitos).
"""

from flask import request


def coletar_chassi_modelo() -> dict:
    """Le filtros chassi (str|None, ilike) e modelo_id (int|None) do request.args.

    Returns:
        {'chassi': str|None, 'modelo_id': int|None} — normalizado para passar
        direto aos services/queries e tambem ao template como filtros_aplicados.
    """
    return {
        'chassi': (request.args.get('chassi') or '').strip() or None,
        'modelo_id': request.args.get('modelo_id', type=int) or None,
    }
