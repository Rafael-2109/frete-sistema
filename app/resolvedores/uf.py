"""Resolucao de UF.

resolver_uf (rico) = port fiel de resolver_entidades.py:386.
resolver_uf_cli (achatado, +entregas) = port de resolvendo-entidades/scripts/resolver_uf.py.
"""
from app.resolvedores.constantes import UFS_VALIDAS
from app.resolvedores._fontes import fonte_cli


def resolver_uf(uf: str, fonte: str = 'carteira') -> dict:
    """Resolve pedidos de uma UF especifica (rico). Port :386."""
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from collections import defaultdict

    uf_upper = (uf or '').upper().strip()

    if uf_upper not in UFS_VALIDAS:
        return {
            'sucesso': False,
            'uf': uf,
            'erro': f"UF '{uf}' inválida",
            'ufs_validas': UFS_VALIDAS
        }

    if fonte == 'carteira':
        Model = CarteiraPrincipal
        filtro_saldo = CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    elif fonte == 'separacao':
        Model = Separacao
        filtro_saldo = (Separacao.sincronizado_nf == False) & (Separacao.qtd_saldo > 0)
    else:
        Model = CarteiraPrincipal
        filtro_saldo = CarteiraPrincipal.qtd_saldo_produto_pedido > 0

    itens = Model.query.filter(
        Model.cod_uf == uf_upper,
        filtro_saldo
    ).all()

    if not itens:
        return {
            'sucesso': False,
            'uf': uf_upper,
            'erro': f"Nenhum pedido encontrado para UF {uf_upper}"
        }

    pedidos_dict = defaultdict(lambda: {'itens': [], 'valor_total': 0, 'total_itens': 0})

    for item in itens:
        num = item.num_pedido
        pedidos_dict[num]['num_pedido'] = num
        pedidos_dict[num]['cnpj'] = item.cnpj_cpf
        pedidos_dict[num]['cliente'] = item.raz_social_red or item.raz_social
        pedidos_dict[num]['cidade'] = item.nome_cidade or item.municipio
        pedidos_dict[num]['uf'] = item.cod_uf or item.estado
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
    cidades = sorted(set(p['cidade'] for p in pedidos if p['cidade']))

    return {
        'sucesso': True,
        'uf': uf_upper,
        'fonte': fonte,
        'pedidos': pedidos,
        'resumo': {
            'total_pedidos': len(pedidos),
            'total_valor': round(total_valor, 2),
            'cidades': cidades
        }
    }


def resolver_uf_cli(uf: str, fonte: str = 'entregas', limite: int = 100) -> dict:
    """Fachada CLI (JSON achatado) — port de resolvendo-entidades/scripts/resolver_uf.py.

    Shape: {sucesso, uf, clientes, cidades, total, exibindo, fonte} ou erro com ufs_validas.
    """
    uf_upper = (uf or '').upper().strip()

    resultado = {
        'sucesso': False,
        'uf': uf_upper,
        'clientes': [],
        'cidades': [],
        'total': 0,
    }

    if uf_upper not in UFS_VALIDAS:
        resultado['erro'] = f"UF '{uf}' invalida"
        resultado['ufs_validas'] = UFS_VALIDAS
        return resultado

    Model, c_cnpj, c_nome, c_uf, c_cidade, saldo = fonte_cli(fonte)
    col_cnpj = getattr(Model, c_cnpj)
    col_nome = getattr(Model, c_nome)
    col_uf = getattr(Model, c_uf)
    col_cidade = getattr(Model, c_cidade)

    rows = Model.query.with_entities(col_cnpj, col_nome, col_cidade, col_uf).filter(
        col_uf == uf_upper, saldo
    ).distinct().order_by(col_nome).limit(limite).all()

    if not rows:
        resultado['erro'] = f"Nenhum registro encontrado para UF {uf_upper}"
        return resultado

    clientes = []
    cidades_set = set()
    for row in rows:
        clientes.append({'cnpj': row[0], 'nome': row[1], 'cidade': row[2], 'uf': row[3]})
        if row[2]:
            cidades_set.add(row[2])

    total = Model.query.with_entities(col_cnpj).filter(
        col_uf == uf_upper, saldo
    ).distinct().count()

    resultado['sucesso'] = True
    resultado['clientes'] = clientes
    resultado['cidades'] = sorted(list(cidades_set))
    resultado['total'] = total
    resultado['exibindo'] = len(clientes)
    resultado['fonte'] = fonte

    return resultado
