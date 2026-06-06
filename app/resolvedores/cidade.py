"""Resolucao de cidade.

resolver_cidade (rico) + resolver_cidades_multiplas = port fiel de resolver_entidades.py:930/1058
  (accent-insensitive REAL: normaliza em Python e compara).
resolver_cidade_cli (achatado, +entregas) = port da split COM o bug de acento CORRIGIDO
  (a split usava o termo cru no ILIKE; aqui normalizamos no match).
"""
from collections import defaultdict

from app.resolvedores.normalizacao import normalizar_texto
from app.resolvedores._fontes import fonte_cli


def resolver_cidade(termo: str, fonte: str = 'separacao', apenas_pendentes: bool = True):
    """Resolve termo de cidade para pedidos, normalizando acentos e case (port :930)."""
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao

    termo_normalizado = normalizar_texto(termo)

    resultado = {
        'sucesso': True,
        'termo_original': termo,
        'termo_normalizado': termo_normalizado,
        'cidades_encontradas': [],
        'pedidos': [],
        'total_pedidos': 0
    }

    if not termo_normalizado:
        resultado['sucesso'] = False
        resultado['erro'] = 'Termo de busca vazio'
        return resultado

    cidades_encontradas = set()
    pedidos_dict = defaultdict(lambda: {
        'num_pedido': None, 'cliente': None, 'cidade': None, 'uf': None, 'valor': 0.0, 'itens': 0
    })

    # Buscar em Separacao
    if fonte in ('separacao', 'ambos'):
        query = Separacao.query
        if apenas_pendentes:
            query = query.filter(
                Separacao.sincronizado_nf == False,
                Separacao.qtd_saldo > 0
            )
        for item in query.all():
            cidade_item = item.nome_cidade or ''
            if termo_normalizado in normalizar_texto(cidade_item):
                cidades_encontradas.add(cidade_item)
                num = item.num_pedido
                if pedidos_dict[num]['num_pedido'] is None:
                    pedidos_dict[num]['num_pedido'] = num
                    pedidos_dict[num]['cliente'] = item.raz_social_red
                    pedidos_dict[num]['cidade'] = cidade_item
                    pedidos_dict[num]['uf'] = item.cod_uf
                    pedidos_dict[num]['fonte'] = 'separacao'
                pedidos_dict[num]['valor'] += float(item.valor_saldo or 0)
                pedidos_dict[num]['itens'] += 1

    # Buscar em Carteira
    if fonte in ('carteira', 'ambos'):
        query = CarteiraPrincipal.query
        if apenas_pendentes:
            query = query.filter(CarteiraPrincipal.qtd_saldo_produto_pedido > 0)
        for item in query.all():
            cidade_item = item.nome_cidade or ''
            if termo_normalizado in normalizar_texto(cidade_item):
                cidades_encontradas.add(cidade_item)
                num = item.num_pedido
                if pedidos_dict[num]['num_pedido'] is None:
                    pedidos_dict[num]['num_pedido'] = num
                    pedidos_dict[num]['cliente'] = item.raz_social_red
                    pedidos_dict[num]['cidade'] = cidade_item
                    pedidos_dict[num]['uf'] = item.cod_uf
                    pedidos_dict[num]['fonte'] = 'carteira'

                    preco = float(item.preco_produto_pedido or 0)
                    qtd = float(item.qtd_saldo_produto_pedido or 0)
                    pedidos_dict[num]['valor'] += preco * qtd
                    pedidos_dict[num]['itens'] += 1

    resultado['cidades_encontradas'] = sorted(list(cidades_encontradas))
    resultado['pedidos'] = list(pedidos_dict.values())
    resultado['total_pedidos'] = len(pedidos_dict)

    if not resultado['pedidos']:
        resultado['sucesso'] = False
        resultado['erro'] = f"Nenhum pedido encontrado para cidade '{termo}'"
        resultado['sugestao'] = "Verifique a grafia da cidade ou tente sem acentos"

    return resultado


def resolver_cidades_multiplas(cidades: list, fonte: str = 'separacao', apenas_pendentes: bool = True):
    """Resolve multiplas cidades de uma vez (port :1058)."""
    resultado_final = {
        'sucesso': True,
        'cidades_buscadas': cidades,
        'cidades_encontradas': [],
        'pedidos': [],
        'total_pedidos': 0,
        'por_cidade': {}
    }

    pedidos_unicos = {}

    for cidade in cidades:
        resultado = resolver_cidade(cidade, fonte=fonte, apenas_pendentes=apenas_pendentes)
        if resultado['sucesso']:
            resultado_final['cidades_encontradas'].extend(resultado['cidades_encontradas'])
            resultado_final['por_cidade'][cidade] = {
                'encontradas': resultado['cidades_encontradas'],
                'total': resultado['total_pedidos']
            }
            for pedido in resultado['pedidos']:
                num = pedido['num_pedido']
                if num not in pedidos_unicos:
                    pedidos_unicos[num] = pedido

    resultado_final['pedidos'] = list(pedidos_unicos.values())
    resultado_final['total_pedidos'] = len(pedidos_unicos)
    resultado_final['cidades_encontradas'] = list(set(resultado_final['cidades_encontradas']))

    if not resultado_final['pedidos']:
        resultado_final['sucesso'] = False
        resultado_final['erro'] = f"Nenhum pedido encontrado para as cidades: {', '.join(cidades)}"

    return resultado_final


def resolver_cidade_cli(cidade: str, fonte: str = 'entregas', limite: int = 50) -> dict:
    """Fachada CLI (JSON achatado) — usada pelos 8 subagentes via resolver_cidade.py.

    Mesmo shape da split, mas accent-insensitive REAL (normalizar_texto no match) — corrige o bug
    de resolver_cidade.py:123 que usava o termo cru no ILIKE. Shape: {sucesso, cidade_original,
    termo_normalizado, cidades_encontradas:[{cidade,uf}], clientes:[{cnpj,nome,cidade,uf}], total, fonte}.
    """
    termo_normalizado = normalizar_texto(cidade)

    resultado = {
        'sucesso': False,
        'cidade_original': cidade,
        'termo_normalizado': termo_normalizado,
        'cidades_encontradas': [],
        'clientes': [],
        'total': 0,
    }
    if not termo_normalizado:
        resultado['erro'] = 'Termo de busca vazio'
        return resultado

    Model, c_cnpj, c_nome, c_uf, c_cidade, saldo = fonte_cli(fonte)
    col_cidade = getattr(Model, c_cidade)
    col_uf = getattr(Model, c_uf)
    col_cnpj = getattr(Model, c_cnpj)
    col_nome = getattr(Model, c_nome)

    # 1. Cidades distintas (filtra accent-insensitive em Python)
    cidade_rows = Model.query.with_entities(col_cidade, col_uf).filter(
        col_cidade.isnot(None), saldo
    ).distinct().all()

    cidades_casadas = []
    vistos = set()
    for nome_cidade, uf in cidade_rows:
        if termo_normalizado in normalizar_texto(nome_cidade or ''):
            key = (nome_cidade, uf)
            if key not in vistos:
                vistos.add(key)
                cidades_casadas.append((nome_cidade, uf))
    cidades_casadas.sort(key=lambda x: (x[0] or ''))
    cidades_casadas = cidades_casadas[:20]  # split limita cidades a 20

    if not cidades_casadas:
        resultado['erro'] = f"Cidade '{cidade}' nao encontrada"
        resultado['sugestao'] = "Verifique a grafia da cidade"
        return resultado

    resultado['cidades_encontradas'] = [{'cidade': c, 'uf': u} for c, u in cidades_casadas]

    # 2. Clientes dessas cidades
    nomes = [c for c, _ in cidades_casadas]
    cliente_rows = Model.query.with_entities(col_cnpj, col_nome, col_cidade, col_uf).filter(
        col_cidade.in_(nomes), saldo
    ).distinct().order_by(col_nome).limit(limite).all()

    resultado['clientes'] = [
        {'cnpj': r[0], 'nome': r[1], 'cidade': r[2], 'uf': r[3]} for r in cliente_rows
    ]
    resultado['sucesso'] = True
    resultado['total'] = len(resultado['clientes'])
    resultado['fonte'] = fonte
    return resultado
