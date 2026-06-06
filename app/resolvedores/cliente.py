"""Resolucao de cliente (nao-grupo).

resolver_cliente (rico, carteira/separacao) = port fiel de resolver_entidades.py:506 — serve o
  importador Python consultando_situacao_pedidos (clientes_encontrados + pedidos + resumo).
resolver_cliente_cli (achatado, +entregas) = port de resolvendo-entidades/scripts/resolver_cliente.py.
"""
import re

from app.resolvedores._fontes import fonte_cli


def resolver_cliente(termo: str, fonte: str = 'carteira') -> dict:
    """Resolve termo de cliente para pedidos da carteira/separacao (rico). Port :506."""
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from sqlalchemy import or_
    from collections import defaultdict

    termo = (termo or '').strip()

    resultado = {
        'sucesso': False,
        'termo_original': termo,
        'estrategia': None,
        'clientes_encontrados': [],
        'pedidos': [],
        'resumo': {}
    }

    if not termo:
        resultado['erro'] = 'Termo de busca vazio'
        return resultado

    termo_limpo = re.sub(r'[^\d]', '', termo)
    parece_cnpj = (
        len(termo_limpo) >= 8 or
        re.match(r'^\d{2}\.\d{3}\.\d{3}', termo) or
        '/' in termo
    )

    if fonte == 'carteira':
        Model = CarteiraPrincipal
        filtro_saldo = CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    elif fonte == 'separacao':
        Model = Separacao
        filtro_saldo = (Separacao.sincronizado_nf == False) & (Separacao.qtd_saldo > 0)
    else:  # ambos - priorizar carteira
        Model = CarteiraPrincipal
        filtro_saldo = CarteiraPrincipal.qtd_saldo_produto_pedido > 0

    itens = []

    if parece_cnpj and len(termo_limpo) >= 8:
        resultado['estrategia'] = 'CNPJ'
        itens = Model.query.filter(
            or_(
                Model.cnpj_cpf.ilike(f'%{termo}%'),
                Model.cnpj_cpf.ilike(f'%{termo_limpo[:8]}%')
            ),
            filtro_saldo
        ).all()

    if not itens:
        resultado['estrategia'] = 'NOME_PARCIAL'
        itens = Model.query.filter(
            Model.raz_social_red.ilike(f'%{termo}%'),
            filtro_saldo
        ).all()

    if not itens:
        resultado['erro'] = f"Cliente '{termo}' nao encontrado"
        resultado['sugestao'] = "Tente buscar por CNPJ (ex: 45.543.915) ou nome parcial (ex: Carrefour)"
        return resultado

    clientes_dict = defaultdict(lambda: {
        'cnpj': None, 'nome': None, 'cidade': None, 'uf': None, 'num_pedidos': 0, 'valor_total': 0.0
    })
    pedidos_dict = defaultdict(lambda: {
        'num_pedido': None, 'cliente': None, 'cnpj': None, 'cidade': None, 'uf': None,
        'total_itens': 0, 'valor_total': 0.0
    })

    for item in itens:
        cnpj = item.cnpj_cpf
        num = item.num_pedido

        if clientes_dict[cnpj]['cnpj'] is None:
            clientes_dict[cnpj]['cnpj'] = cnpj
            clientes_dict[cnpj]['nome'] = item.raz_social_red
            clientes_dict[cnpj]['cidade'] = item.nome_cidade
            clientes_dict[cnpj]['uf'] = item.cod_uf

        if pedidos_dict[num]['num_pedido'] is None:
            pedidos_dict[num]['num_pedido'] = num
            pedidos_dict[num]['cliente'] = item.raz_social_red
            pedidos_dict[num]['cnpj'] = cnpj
            pedidos_dict[num]['cidade'] = item.nome_cidade
            pedidos_dict[num]['uf'] = item.cod_uf
            clientes_dict[cnpj]['num_pedidos'] += 1

        pedidos_dict[num]['total_itens'] += 1

        if fonte == 'separacao':
            valor_item = float(item.valor_saldo or 0)
        else:
            valor_item = float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)

        pedidos_dict[num]['valor_total'] += valor_item
        clientes_dict[cnpj]['valor_total'] += valor_item

    clientes_lista = list(clientes_dict.values())
    clientes_lista.sort(key=lambda c: -c['valor_total'])

    pedidos_lista = list(pedidos_dict.values())
    pedidos_lista.sort(key=lambda p: -p['valor_total'])

    resultado['sucesso'] = True
    resultado['clientes_encontrados'] = clientes_lista
    resultado['pedidos'] = pedidos_lista
    resultado['fonte'] = fonte

    total_valor = sum(p['valor_total'] for p in pedidos_lista)
    resultado['resumo'] = {
        'total_clientes': len(clientes_lista),
        'total_pedidos': len(pedidos_lista),
        'total_valor': round(total_valor, 2)
    }

    return resultado


def resolver_cliente_cli(termo: str, fonte: str = 'entregas', limite: int = 50) -> dict:
    """Fachada CLI (JSON achatado) — port de resolvendo-entidades/scripts/resolver_cliente.py.

    Shape: {sucesso, termo_original, estrategia, clientes:[{cnpj,nome,cidade,uf}], total, fonte}.
    """
    from sqlalchemy import or_

    termo = (termo or '').strip()
    resultado = {
        'sucesso': False,
        'termo_original': termo,
        'estrategia': None,
        'clientes': [],
        'total': 0,
    }
    if not termo:
        resultado['erro'] = 'Termo de busca vazio'
        return resultado

    termo_limpo = re.sub(r'[^\d]', '', termo)
    parece_cnpj = (
        len(termo_limpo) >= 8 or
        re.match(r'^\d{2}\.\d{3}\.\d{3}', termo) or
        '/' in termo
    )

    Model, c_cnpj, c_nome, c_uf, c_cidade, saldo = fonte_cli(fonte)
    col_cnpj = getattr(Model, c_cnpj)
    col_nome = getattr(Model, c_nome)
    col_uf = getattr(Model, c_uf)
    col_cidade = getattr(Model, c_cidade)

    q = Model.query.with_entities(col_cnpj, col_nome, col_cidade, col_uf)

    if parece_cnpj and len(termo_limpo) >= 8:
        resultado['estrategia'] = 'CNPJ'
        rows = q.filter(
            or_(col_cnpj.ilike(f'%{termo}%'), col_cnpj.ilike(f'%{termo_limpo[:8]}%')),
            saldo
        ).distinct().order_by(col_nome).limit(limite).all()
    else:
        resultado['estrategia'] = 'NOME_PARCIAL'
        rows = q.filter(
            col_nome.ilike(f'%{termo}%'), saldo
        ).distinct().order_by(col_nome).limit(limite).all()

    if not rows:
        resultado['erro'] = f"Cliente '{termo}' nao encontrado"
        resultado['sugestao'] = "Tente buscar por CNPJ (ex: 45.543.915) ou nome parcial"
        return resultado

    resultado['clientes'] = [
        {'cnpj': r[0], 'nome': r[1], 'cidade': r[2], 'uf': r[3]} for r in rows
    ]
    resultado['sucesso'] = True
    resultado['total'] = len(resultado['clientes'])
    resultado['fonte'] = fonte
    return resultado
