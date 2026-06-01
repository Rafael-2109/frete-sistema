"""Resolucao de grupo empresarial.

Helpers puros (sem banco): get_prefixos_grupo, listar_grupos_disponiveis.
resolver_grupo (rico, port monolito :214) e resolver_grupo_cli (achatado, port split, +fonte entregas).
"""
from app.resolvedores.constantes import GRUPOS_EMPRESARIAIS
from app.resolvedores._fontes import fonte_cli


def get_prefixos_grupo(grupo: str) -> list:
    """Retorna prefixos CNPJ de um grupo empresarial (lista vazia se nao encontrado).

    Port de resolver_entidades.py:196.
    """
    return GRUPOS_EMPRESARIAIS.get((grupo or '').lower().strip(), [])


def listar_grupos_disponiveis() -> list:
    """Retorna lista de grupos empresariais disponiveis. Port de resolver_entidades.py:209."""
    return list(GRUPOS_EMPRESARIAIS.keys())


def resolver_grupo(grupo: str, uf: str = None, loja: str = None, fonte: str = 'carteira') -> dict:
    """Resolve grupo empresarial retornando prefixos CNPJ + pedidos (rico). Port :214."""
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from sqlalchemy import or_
    from collections import defaultdict

    grupo_lower = (grupo or '').lower().strip()
    prefixos = get_prefixos_grupo(grupo_lower)

    if not prefixos:
        return {
            'sucesso': False,
            'grupo': grupo,
            'erro': f"Grupo '{grupo}' não encontrado",
            'grupos_disponiveis': listar_grupos_disponiveis()
        }

    filtros_aplicados = {}
    if uf:
        filtros_aplicados['uf'] = uf.upper()
    if loja:
        filtros_aplicados['loja'] = loja

    if fonte == 'carteira':
        Model = CarteiraPrincipal
        filtro_saldo = CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    elif fonte == 'separacao':
        Model = Separacao
        filtro_saldo = (Separacao.sincronizado_nf == False) & (Separacao.qtd_saldo > 0)
    else:  # ambos - priorizar carteira
        Model = CarteiraPrincipal
        filtro_saldo = CarteiraPrincipal.qtd_saldo_produto_pedido > 0

    filtros_cnpj = [Model.cnpj_cpf.like(f'{prefixo}%') for prefixo in prefixos]
    query = Model.query.filter(or_(*filtros_cnpj), filtro_saldo)

    if uf:
        query = query.filter(Model.cod_uf == uf.upper())
    if loja:
        query = query.filter(Model.raz_social_red.ilike(f'%{loja}%'))

    itens = query.all()

    if not itens:
        return {
            'sucesso': False,
            'grupo': grupo,
            'prefixos_cnpj': prefixos,
            'filtros_aplicados': filtros_aplicados,
            'erro': 'Nenhum pedido encontrado com os filtros aplicados',
            'sugestao': 'Tente remover filtros de UF ou loja'
        }

    pedidos_dict = defaultdict(lambda: {'itens': [], 'valor_total': 0, 'total_itens': 0})

    for item in itens:
        num = item.num_pedido
        pedidos_dict[num]['num_pedido'] = num
        pedidos_dict[num]['cnpj'] = item.cnpj_cpf
        pedidos_dict[num]['cliente'] = item.raz_social_red or item.raz_social
        pedidos_dict[num]['cidade'] = item.nome_cidade or item.municipio
        pedidos_dict[num]['uf'] = item.cod_uf or item.estado
        pedidos_dict[num]['itens'].append(item)
        pedidos_dict[num]['total_itens'] += 1

        if fonte == 'carteira':
            valor_item = float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
        else:
            valor_item = float(item.valor_saldo or 0)

        pedidos_dict[num]['valor_total'] += valor_item

    pedidos = []
    for num, dados in pedidos_dict.items():
        pedidos.append({
            'num_pedido': num,
            'cnpj': dados['cnpj'],
            'cliente': dados['cliente'],
            'cidade': dados['cidade'],
            'uf': dados['uf'],
            'total_itens': dados['total_itens'],
            'valor_total': round(dados['valor_total'], 2)
        })

    pedidos.sort(key=lambda p: p['valor_total'], reverse=True)

    total_valor = sum(p['valor_total'] for p in pedidos)
    ufs = sorted(set(p['uf'] for p in pedidos if p['uf']))
    cidades = sorted(set(p['cidade'] for p in pedidos if p['cidade']))
    lojas = sorted(set(p['cliente'].split()[-1] for p in pedidos if p['cliente']))

    return {
        'sucesso': True,
        'grupo': grupo,
        'prefixos_cnpj': prefixos,
        'filtros_aplicados': filtros_aplicados,
        'fonte': fonte,
        'pedidos': pedidos,
        'resumo': {
            'total_pedidos': len(pedidos),
            'total_valor': round(total_valor, 2),
            'ufs': ufs,
            'cidades': cidades,
            'lojas': lojas
        }
    }


def resolver_grupo_cli(grupo: str, uf: str = None, loja: str = None,
                       fonte: str = 'entregas', limite: int = 100) -> dict:
    """Fachada CLI (JSON achatado) — port de resolvendo-entidades/scripts/resolver_grupo.py.

    ORM bind-safe (elimina a interpolacao de prefixo de resolver_grupo.py:116).
    Shape: {sucesso, grupo, prefixos_cnpj, filtros_aplicados, fonte, cnpjs, clientes, total, exibindo}.
    """
    from sqlalchemy import or_

    grupo_lower = (grupo or '').lower().strip()
    prefixos = get_prefixos_grupo(grupo_lower)

    if not prefixos:
        return {
            'sucesso': False,
            'grupo': grupo,
            'erro': f"Grupo '{grupo}' nao encontrado",
            'grupos_disponiveis': listar_grupos_disponiveis()
        }

    filtros_aplicados = {}
    if uf:
        filtros_aplicados['uf'] = uf.upper()
    if loja:
        filtros_aplicados['loja'] = loja

    Model, c_cnpj, c_nome, c_uf, c_cidade, saldo = fonte_cli(fonte)
    col_cnpj = getattr(Model, c_cnpj)
    col_nome = getattr(Model, c_nome)
    col_uf = getattr(Model, c_uf)
    col_cidade = getattr(Model, c_cidade)

    filtros_cnpj = or_(*[col_cnpj.like(f'{p}%') for p in prefixos])

    q = Model.query.with_entities(col_cnpj, col_nome, col_cidade, col_uf).filter(filtros_cnpj, saldo)
    if uf:
        q = q.filter(col_uf == uf.upper())
    if loja:
        q = q.filter(col_nome.ilike(f'%{loja}%'))
    rows = q.distinct().order_by(col_nome).limit(limite).all()

    cnpjs = []
    clientes = []
    for row in rows:
        cnpjs.append(row[0])
        clientes.append({'cnpj': row[0], 'nome': row[1], 'cidade': row[2], 'uf': row[3]})

    q_count = Model.query.with_entities(col_cnpj).filter(filtros_cnpj, saldo)
    if uf:
        q_count = q_count.filter(col_uf == uf.upper())
    if loja:
        q_count = q_count.filter(col_nome.ilike(f'%{loja}%'))
    total = q_count.distinct().count()

    return {
        'sucesso': True,
        'grupo': grupo_lower,
        'prefixos_cnpj': prefixos,
        'filtros_aplicados': filtros_aplicados,
        'fonte': fonte,
        'cnpjs': cnpjs,
        'clientes': clientes,
        'total': total,
        'exibindo': len(cnpjs)
    }
