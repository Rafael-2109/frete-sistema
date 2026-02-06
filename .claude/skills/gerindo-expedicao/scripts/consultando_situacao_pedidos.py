#!/usr/bin/env python3
"""
Script: consultando_situacao_pedidos.py
Queries cobertas: Q8, Q10, Q14, Q16, Q19

Consulta pedidos por diversos filtros e perspectivas.

Uso:
    --grupo atacadao                      # Q8: Pedidos pendentes do grupo
    --atrasados                           # Q10: Pedidos atrasados para embarque
    --verificar-bonificacao               # Q14: Pedidos faltando bonificacao
    --pedido VCD123 --status              # Q16: Status do pedido
    --consolidar-com "assai 123"          # Q19: Pedidos para consolidar
    --produto "azeitona verde"            # Pedidos com produto especifico
    --produto palmito --ate-data amanha   # Filtrar por data de expedicao
    --produto pessego --em-separacao      # Buscar em Separacao (nao faturados)
"""
import sys
import os
import json
import argparse
from datetime import date, datetime, timedelta
from decimal import Decimal
from collections import defaultdict

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# Importar modulo centralizado de resolucao de entidades
from resolver_entidades import (
    resolver_pedido,
    resolver_produto_unico,
    resolver_produtos_na_carteira_cliente,  # NOVO: filosofia 50% regra / 50% IA
    resolver_cliente,  # NOVO: GAP-01
    formatar_sugestao_produto,
    get_prefixos_grupo,
    listar_grupos_disponiveis,
    formatar_sugestao_pedido,
    GRUPOS_EMPRESARIAIS
) # type: ignore


def decimal_default(obj):
    """Serializa Decimal para JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def parse_data_natural(termo: str) -> date:
    """
    Interpreta termo de data em linguagem natural ou formato brasileiro.

    Formatos aceitos:
    - "hoje" -> date.today()
    - "amanha" ou "amanhã" -> date.today() + 1 dia
    - "dd/mm/yyyy" -> data completa
    - "dd/mm" -> assume ano atual
    - "dd" -> assume mes e ano atuais

    Args:
        termo: String representando a data

    Returns:
        date: Data interpretada

    Raises:
        ValueError: Se nao conseguir interpretar
    """
    termo = termo.strip().lower()
    hoje = date.today()

    # Termos naturais
    if termo in ('hoje', 'today'):
        return hoje
    if termo in ('amanha', 'amanhã', 'tomorrow'):
        return hoje + timedelta(days=1)
    if termo in ('ontem', 'yesterday'):
        return hoje - timedelta(days=1)

    # Formatos com barra (dd/mm/yyyy, dd/mm, dd)
    partes = termo.replace('-', '/').split('/')

    try:
        if len(partes) == 3:
            # dd/mm/yyyy
            dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
            # Se ano com 2 digitos, assume 2000+
            if ano < 100:
                ano += 2000
            return date(ano, mes, dia)
        elif len(partes) == 2:
            # dd/mm - assume ano atual
            dia, mes = int(partes[0]), int(partes[1])
            return date(hoje.year, mes, dia)
        elif len(partes) == 1 and partes[0].isdigit():
            # dd - assume mes e ano atuais
            dia = int(partes[0])
            return date(hoje.year, hoje.month, dia)
    except (ValueError, TypeError):
        pass

    raise ValueError(f"Formato de data nao reconhecido: '{termo}'. Use: hoje, amanha, dd/mm/yyyy, dd/mm ou dd")


def consultar_situacao_pedidos_grupo(args):
    """
    Query 8: Tem pedido pendente pro Atacadao?
    Busca pedidos pendentes de um grupo empresarial.
    """
    from app.carteira.models import CarteiraPrincipal
    from sqlalchemy import or_

    resultado = {
        'sucesso': True,
        'tipo_analise': 'PEDIDOS_GRUPO',
        'grupo': args.grupo,
        'pedidos': [],
        'resumo': {}
    }

    # Validar grupo
    prefixos = get_prefixos_grupo(args.grupo)
    if not prefixos:
        resultado['sucesso'] = False
        resultado['erro'] = f"Grupo '{args.grupo}' nao encontrado"
        resultado['sugestao'] = f"Grupos validos: {listar_grupos_disponiveis()}"
        return resultado

    # Construir filtros CNPJ
    filtros_cnpj = [CarteiraPrincipal.cnpj_cpf.like(f'{p}%') for p in prefixos]

    # Buscar pedidos do grupo com saldo > 0
    itens = CarteiraPrincipal.query.filter(
        or_(*filtros_cnpj),
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    ).all()

    if not itens:
        resultado['resumo'] = {
            'total_pedidos': 0,
            'mensagem': f"Nenhum pedido pendente para {args.grupo.capitalize()}"
        }
        return resultado

    # Agrupar por pedido
    pedidos_dict = defaultdict(lambda: {
        'num_pedido': None,
        'cliente': None,
        'cnpj': None,
        'cidade': None,
        'uf': None,
        'total_itens': 0,
        'valor_total': 0.0
    })

    for item in itens:
        num = item.num_pedido
        if pedidos_dict[num]['num_pedido'] is None:
            pedidos_dict[num]['num_pedido'] = num
            pedidos_dict[num]['cliente'] = item.raz_social_red
            pedidos_dict[num]['cnpj'] = item.cnpj_cpf
            pedidos_dict[num]['cidade'] = item.nome_cidade
            pedidos_dict[num]['uf'] = item.cod_uf

        pedidos_dict[num]['total_itens'] += 1 # type: ignore
        preco = float(item.preco_produto_pedido or 0)
        qtd = float(item.qtd_saldo_produto_pedido or 0)
        pedidos_dict[num]['valor_total'] += preco * qtd # type: ignore

    # Converter para lista
    pedidos_lista = list(pedidos_dict.values())
    pedidos_lista.sort(key=lambda x: -x['valor_total']) # type: ignore

    resultado['pedidos'] = pedidos_lista[:args.limit]

    # Resumo
    total_valor = sum(p['valor_total'] for p in pedidos_lista)
    resultado['resumo'] = {
        'total_pedidos': len(pedidos_lista),
        'valor_total': total_valor,
        'mensagem': f"Sim! {len(pedidos_lista)} pedido(s) pendente(s) para {args.grupo.capitalize()}. Total: R$ {total_valor:,.2f}"
    }

    return resultado


def consultar_situacao_pedidos_grupo_produto(args):
    """
    NOVO: Combina filtros --grupo + --produto para responder perguntas como:
    "quantas caixas de ketchup tem pendentes pro atacadao?"
    "pedidos do assai com palmito"

    Fluxo:
    1. Valida grupo (prefixos CNPJ)
    2. Resolve produto (cod_produto via resolver_produto_unico)
    3. Busca em CarteiraPrincipal com ambos os filtros
    4. Agrupa por pedido, mostrando quantidade do produto especifico
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from sqlalchemy import or_

    resultado = {
        'sucesso': True,
        'tipo_analise': 'PEDIDOS_GRUPO_PRODUTO',
        'grupo': args.grupo,
        'termo_produto': args.produto,
        'produto': None,
        'fonte': 'separacao' if getattr(args, 'em_separacao', False) else 'carteira',
        'pedidos': [],
        'resumo': {}
    }

    # 1. Validar grupo
    prefixos = get_prefixos_grupo(args.grupo)
    if not prefixos:
        resultado['sucesso'] = False
        resultado['erro'] = f"Grupo '{args.grupo}' nao encontrado"
        resultado['sugestao'] = f"Grupos validos: {listar_grupos_disponiveis()}"
        return resultado

    # 2. Resolver produto
    produto_info, info_busca = resolver_produto_unico(args.produto)

    # NOVO: Se multiplos candidatos, usar filosofia 50% regra / 50% IA
    # Buscar TODOS os candidatos na carteira do cliente e deixar IA decidir
    if info_busca.get('multiplos') and not info_busca.get('encontrado'):
        # Construir lista de CNPJs do grupo
        cnpjs_grupo = []
        for p in prefixos:
            itens_grupo = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.cnpj_cpf.like(f'{p}%'),
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).with_entities(CarteiraPrincipal.cnpj_cpf).distinct().all()
            cnpjs_grupo.extend([i.cnpj_cpf for i in itens_grupo])

        # Usar nova funcao que retorna todos os candidatos
        resultado_carteira = resolver_produtos_na_carteira_cliente(args.produto, cnpjs_grupo)

        if resultado_carteira['sucesso'] and resultado_carteira['itens_carteira']:
            resultado['sucesso'] = True
            resultado['tipo_analise'] = 'MULTIPLOS_PRODUTOS_GRUPO'
            resultado['grupo'] = args.grupo
            resultado['produtos'] = resultado_carteira['itens_carteira']
            resultado['total_skus'] = resultado_carteira['total_skus']
            resultado['candidatos_cadastro'] = resultado_carteira['candidatos_cadastro']
            resultado['resumo'] = {
                'total_skus': resultado_carteira['total_skus'],
                'total_quantidade': resultado_carteira['total_quantidade'],
                'total_valor': resultado_carteira['total_valor'],
                'mensagem': f"{resultado_carteira['total_skus']} SKU(s) de '{args.produto}' encontrado(s) pro {args.grupo.capitalize()}"
            }
            resultado['ia_decide'] = True
            return resultado
        elif not resultado_carteira['itens_carteira']:
            # Candidatos existem no cadastro mas nao na carteira do cliente
            resultado['sucesso'] = False
            resultado['erro'] = f"Produto '{args.produto}' existe no catalogo mas nao tem pedidos do {args.grupo.capitalize()}"
            resultado['candidatos_cadastro'] = resultado_carteira['candidatos_cadastro']
            return resultado

    # Comportamento original para produto unico ou nao encontrado
    if not produto_info:
        resultado['sucesso'] = False
        resultado['erro'] = f"Produto '{args.produto}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_produto(info_busca)
        if info_busca.get('candidatos'):
            resultado['candidatos'] = info_busca['candidatos']
        return resultado

    cod_produto = produto_info['cod_produto']
    nome_produto = produto_info['nome_produto']

    resultado['produto'] = {
        'cod_produto': cod_produto,
        'nome_produto': nome_produto
    }
    resultado['busca'] = {
        'encontrado': info_busca.get('encontrado', False),
        'multiplos': info_busca.get('multiplos', False)
    }
    if info_busca.get('candidatos'):
        resultado['busca']['outros_candidatos'] = info_busca['candidatos']

    # 3. Construir filtros combinados
    filtros_cnpj = [CarteiraPrincipal.cnpj_cpf.like(f'{p}%') for p in prefixos]

    # Buscar na fonte correta
    em_separacao = getattr(args, 'em_separacao', False)

    if em_separacao:
        # Buscar em Separacao
        filtros_cnpj_sep = [Separacao.cnpj_cpf.like(f'{p}%') for p in prefixos]
        itens = Separacao.query.filter(
            or_(*filtros_cnpj_sep),
            Separacao.cod_produto == cod_produto,
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0
        ).all()
    else:
        # Buscar em CarteiraPrincipal
        itens = CarteiraPrincipal.query.filter(
            or_(*filtros_cnpj),
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

    if not itens:
        resultado['resumo'] = {
            'total_pedidos': 0,
            'total_quantidade': 0,
            'total_valor': 0,
            'mensagem': f"Nenhum pedido do {args.grupo.capitalize()} com {nome_produto}"
        }
        return resultado

    # 4. Agrupar por pedido
    pedidos_dict = defaultdict(lambda: {
        'num_pedido': None,
        'cliente': None,
        'cnpj': None,
        'cidade': None,
        'uf': None,
        'qtd_produto': 0.0,
        'valor_produto': 0.0,
        'total_itens': 0
    })

    for item in itens:
        num = item.num_pedido
        if pedidos_dict[num]['num_pedido'] is None:
            pedidos_dict[num]['num_pedido'] = num
            pedidos_dict[num]['cliente'] = item.raz_social_red
            pedidos_dict[num]['cnpj'] = item.cnpj_cpf
            pedidos_dict[num]['cidade'] = item.nome_cidade
            pedidos_dict[num]['uf'] = item.cod_uf

        if em_separacao:
            qtd = float(item.qtd_saldo or 0)
            valor = float(item.valor_saldo or 0)
        else:
            qtd = float(item.qtd_saldo_produto_pedido or 0)
            preco = float(item.preco_produto_pedido or 0)
            valor = qtd * preco

        pedidos_dict[num]['qtd_produto'] += qtd  # type: ignore
        pedidos_dict[num]['valor_produto'] += valor  # type: ignore
        pedidos_dict[num]['total_itens'] += 1  # type: ignore

    # Converter para lista
    pedidos_lista = list(pedidos_dict.values())
    pedidos_lista.sort(key=lambda x: -x['valor_produto'])  # type: ignore

    resultado['pedidos'] = pedidos_lista[:args.limit]

    # Resumo
    total_qtd = sum(p['qtd_produto'] for p in pedidos_lista)
    total_valor = sum(p['valor_produto'] for p in pedidos_lista)
    fonte_texto = 'em separacao' if em_separacao else 'na carteira'

    resultado['resumo'] = {
        'total_pedidos': len(pedidos_lista),
        'total_quantidade': total_qtd,
        'total_valor': total_valor,
        'mensagem': (
            f"{len(pedidos_lista)} pedido(s) do {args.grupo.capitalize()} com {nome_produto} ({fonte_texto}). "
            f"Total: {total_qtd:,.0f} unid, R$ {total_valor:,.2f}"
        )
    }

    return resultado


def consultar_situacao_pedidos_cliente(args):
    """
    GAP-01: Tem pedido do cliente X?
    Busca pedidos de um cliente especifico por CNPJ ou nome parcial.

    Diferente de --grupo, aceita qualquer cliente, nao apenas grupos mapeados.

    Exemplos:
        --cliente "Carrefour"
        --cliente "45.543.915"
        --cliente "12345678000199"
    """
    resultado = {
        'sucesso': True,
        'tipo_analise': 'PEDIDOS_CLIENTE',
        'termo_cliente': args.cliente,
        'pedidos': [],
        'clientes_encontrados': [],
        'resumo': {}
    }

    # Usar resolver_cliente
    em_separacao = getattr(args, 'em_separacao', False)
    fonte = 'separacao' if em_separacao else 'carteira'

    cliente_info = resolver_cliente(args.cliente, fonte=fonte)

    if not cliente_info['sucesso']:
        resultado['sucesso'] = False
        resultado['erro'] = cliente_info.get('erro', f"Cliente '{args.cliente}' nao encontrado")
        resultado['sugestao'] = cliente_info.get('sugestao')
        return resultado

    resultado['estrategia'] = cliente_info['estrategia']
    resultado['clientes_encontrados'] = cliente_info['clientes_encontrados']
    resultado['pedidos'] = cliente_info['pedidos'][:args.limit]
    resultado['fonte'] = fonte

    # Resumo
    total_clientes = cliente_info['resumo']['total_clientes']
    total_pedidos = cliente_info['resumo']['total_pedidos']
    total_valor = cliente_info['resumo']['total_valor']

    resultado['resumo'] = {
        'total_clientes': total_clientes,
        'total_pedidos': total_pedidos,
        'total_valor': total_valor,
        'mensagem': (
            f"{total_pedidos} pedido(s) de {total_clientes} cliente(s) encontrado(s) para '{args.cliente}'. "
            f"Total: R$ {total_valor:,.2f}"
        )
    }

    return resultado


def consultar_situacao_pedidos_cliente_produto(args):
    """
    GAP-03: Combina filtros --cliente + --produto
    Exemplo: "quanto de palmito tem pro Carrefour?"

    Fluxo:
    1. Resolve cliente (CNPJ ou nome parcial)
    2. Resolve produto
    3. Busca pedidos combinando ambos os filtros
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from sqlalchemy import or_

    resultado = {
        'sucesso': True,
        'tipo_analise': 'PEDIDOS_CLIENTE_PRODUTO',
        'termo_cliente': args.cliente,
        'termo_produto': args.produto,
        'cliente': None,
        'produto': None,
        'fonte': 'separacao' if getattr(args, 'em_separacao', False) else 'carteira',
        'pedidos': [],
        'resumo': {}
    }

    em_separacao = getattr(args, 'em_separacao', False)
    fonte = 'separacao' if em_separacao else 'carteira'

    # 1. Resolver cliente
    cliente_info = resolver_cliente(args.cliente, fonte=fonte)

    if not cliente_info['sucesso']:
        resultado['sucesso'] = False
        resultado['erro'] = cliente_info.get('erro', f"Cliente '{args.cliente}' nao encontrado")
        resultado['sugestao'] = cliente_info.get('sugestao')
        return resultado

    # Pegar CNPJs encontrados
    cnpjs_encontrados = [c['cnpj'] for c in cliente_info['clientes_encontrados']]

    resultado['cliente'] = {
        'termo': args.cliente,
        'estrategia': cliente_info['estrategia'],
        'total_encontrados': len(cnpjs_encontrados),
        'clientes': cliente_info['clientes_encontrados'] # Limitar para nao poluir
    }

    # 2. Resolver produto
    produto_info, info_busca = resolver_produto_unico(args.produto)

    # NOVO: Se multiplos candidatos, usar filosofia 50% regra / 50% IA
    # Buscar TODOS os candidatos na carteira do cliente e deixar IA decidir
    if info_busca.get('multiplos') and not info_busca.get('encontrado'):
        # Usar nova funcao que retorna todos os candidatos
        resultado_carteira = resolver_produtos_na_carteira_cliente(args.produto, cnpjs_encontrados)

        if resultado_carteira['sucesso'] and resultado_carteira['itens_carteira']:
            resultado['sucesso'] = True
            resultado['tipo_analise'] = 'MULTIPLOS_PRODUTOS_CLIENTE'
            resultado['cliente'] = args.cliente
            resultado['produtos'] = resultado_carteira['itens_carteira']
            resultado['total_skus'] = resultado_carteira['total_skus']
            resultado['candidatos_cadastro'] = resultado_carteira['candidatos_cadastro']
            resultado['resumo'] = {
                'total_skus': resultado_carteira['total_skus'],
                'total_quantidade': resultado_carteira['total_quantidade'],
                'total_valor': resultado_carteira['total_valor'],
                'mensagem': f"{resultado_carteira['total_skus']} SKU(s) de '{args.produto}' encontrado(s) pro cliente '{args.cliente}'"
            }
            resultado['ia_decide'] = True
            return resultado
        elif not resultado_carteira['itens_carteira']:
            # Candidatos existem no cadastro mas nao na carteira do cliente
            resultado['sucesso'] = False
            resultado['erro'] = f"Produto '{args.produto}' existe no catalogo mas nao tem pedidos do cliente '{args.cliente}'"
            resultado['candidatos_cadastro'] = resultado_carteira['candidatos_cadastro']
            return resultado

    # Comportamento original para produto unico ou nao encontrado
    if not produto_info:
        resultado['sucesso'] = False
        resultado['erro'] = f"Produto '{args.produto}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_produto(info_busca)
        if info_busca.get('candidatos'):
            resultado['candidatos'] = info_busca['candidatos']
        return resultado

    cod_produto = produto_info['cod_produto']
    nome_produto = produto_info['nome_produto']

    resultado['produto'] = {
        'cod_produto': cod_produto,
        'nome_produto': nome_produto
    }
    resultado['busca_produto'] = {
        'encontrado': info_busca.get('encontrado', False),
        'multiplos': info_busca.get('multiplos', False)
    }
    if info_busca.get('candidatos'):
        resultado['busca_produto']['outros_candidatos'] = info_busca['candidatos']

    # 3. Buscar pedidos combinando cliente + produto
    if em_separacao:
        filtros_cnpj = [Separacao.cnpj_cpf == cnpj for cnpj in cnpjs_encontrados]
        itens = Separacao.query.filter(
            or_(*filtros_cnpj),
            Separacao.cod_produto == cod_produto,
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0
        ).all()
    else:
        filtros_cnpj = [CarteiraPrincipal.cnpj_cpf == cnpj for cnpj in cnpjs_encontrados]
        itens = CarteiraPrincipal.query.filter(
            or_(*filtros_cnpj),
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

    if not itens:
        resultado['resumo'] = {
            'total_pedidos': 0,
            'total_quantidade': 0,
            'total_valor': 0,
            'mensagem': f"Nenhum pedido de '{args.cliente}' com {nome_produto}"
        }
        return resultado

    # 4. Agrupar por pedido
    pedidos_dict = defaultdict(lambda: {
        'num_pedido': None,
        'cliente': None,
        'cnpj': None,
        'cidade': None,
        'uf': None,
        'qtd_produto': 0.0,
        'valor_produto': 0.0,
        'total_itens': 0
    })

    for item in itens:
        num = item.num_pedido
        if pedidos_dict[num]['num_pedido'] is None:
            pedidos_dict[num]['num_pedido'] = num
            pedidos_dict[num]['cliente'] = item.raz_social_red
            pedidos_dict[num]['cnpj'] = item.cnpj_cpf
            pedidos_dict[num]['cidade'] = item.nome_cidade
            pedidos_dict[num]['uf'] = item.cod_uf

        if em_separacao:
            qtd = float(item.qtd_saldo or 0)
            valor = float(item.valor_saldo or 0)
        else:
            qtd = float(item.qtd_saldo_produto_pedido or 0)
            preco = float(item.preco_produto_pedido or 0)
            valor = qtd * preco

        pedidos_dict[num]['qtd_produto'] += qtd # type: ignore
        pedidos_dict[num]['valor_produto'] += valor # type: ignore
        pedidos_dict[num]['total_itens'] += 1 # type: ignore

    # Converter para lista
    pedidos_lista = list(pedidos_dict.values())
    pedidos_lista.sort(key=lambda x: -x['valor_produto']) # type: ignore

    resultado['pedidos'] = pedidos_lista[:args.limit]

    # Resumo
    total_qtd = sum(p['qtd_produto'] for p in pedidos_lista)
    total_valor = sum(p['valor_produto'] for p in pedidos_lista)
    fonte_texto = 'em separacao' if em_separacao else 'na carteira'

    resultado['resumo'] = {
        'total_pedidos': len(pedidos_lista),
        'total_quantidade': total_qtd,
        'total_valor': total_valor,
        'mensagem': (
            f"{len(pedidos_lista)} pedido(s) de '{args.cliente}' com {nome_produto} ({fonte_texto}). "
            f"Total: {total_qtd:,.0f} unid, R$ {total_valor:,.2f}"
        )
    }

    return resultado


def consultar_situacao_pedidos_atrasados(args):
    """
    Query 10: Tem pedido atrasado pra embarcar?
    Busca pedidos com expedicao < hoje em Separacao (sincronizado_nf=False).
    """
    from app.separacao.models import Separacao

    resultado = {
        'sucesso': True,
        'tipo_analise': 'PEDIDOS_ATRASADOS',
        'pedidos': [],
        'resumo': {}
    }

    hoje = date.today()

    # Buscar separacoes atrasadas (expedicao < hoje E nao faturadas E com saldo)
    itens = Separacao.query.filter(
        Separacao.expedicao < hoje,
        Separacao.sincronizado_nf == False,
        Separacao.qtd_saldo > 0  # CORRECAO: Filtrar itens com saldo zerado
    ).all()

    if not itens:
        resultado['resumo'] = {
            'total_pedidos': 0,
            'mensagem': "Nenhum pedido atrasado para embarque"
        }
        return resultado

    # Agrupar por pedido
    pedidos_dict = defaultdict(lambda: {
        'num_pedido': None,
        'cliente': None,
        'cnpj': None,
        'cidade': None,
        'uf': None,
        'expedicao': None,
        'dias_atraso': 0,
        'total_itens': 0,
        'valor_total': 0.0
    })

    for item in itens:
        num = item.num_pedido
        if pedidos_dict[num]['num_pedido'] is None:
            pedidos_dict[num]['num_pedido'] = num
            pedidos_dict[num]['cliente'] = item.raz_social_red
            pedidos_dict[num]['cnpj'] = item.cnpj_cpf
            pedidos_dict[num]['cidade'] = item.nome_cidade
            pedidos_dict[num]['uf'] = item.cod_uf
            pedidos_dict[num]['expedicao'] = item.expedicao.isoformat() if item.expedicao else None
            if item.expedicao:
                pedidos_dict[num]['dias_atraso'] = (hoje - item.expedicao).days

        pedidos_dict[num]['total_itens'] += 1 # type: ignore
        pedidos_dict[num]['valor_total'] += float(item.valor_saldo or 0) # type: ignore

    # Converter para lista e ordenar por dias de atraso
    pedidos_lista = list(pedidos_dict.values())
    pedidos_lista.sort(key=lambda x: -x['dias_atraso']) # type: ignore

    resultado['pedidos'] = pedidos_lista[:args.limit]

    # Resumo
    total_valor = sum(p['valor_total'] for p in pedidos_lista)
    resultado['resumo'] = {
        'total_pedidos': len(pedidos_lista),
        'valor_total': total_valor,
        'maior_atraso': max(p['dias_atraso'] for p in pedidos_lista) if pedidos_lista else 0,
        'mensagem': f"Sim! {len(pedidos_lista)} pedido(s) atrasado(s). Total em atraso: R$ {total_valor:,.2f}"
    }

    return resultado


def verificar_bonificacao(args):
    """
    Query 14: Tem pedido faltando bonificacao?
    Identifica CNPJs com bonificacao onde venda e bonificacao nao estao juntos na separacao.
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao

    resultado = {
        'sucesso': True,
        'tipo_analise': 'BONIFICACAO_FALTANDO',
        'pedidos_faltando': [],
        'resumo': {}
    }

    # 1. Identificar CNPJs que TEM bonificacao na carteira
    # Bonificacao = forma_pgto_pedido LIKE 'Sem Pagamento%'
    cnpjs_bonificacao = CarteiraPrincipal.query.filter(
        CarteiraPrincipal.forma_pgto_pedido.ilike('Sem Pagamento%'),
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    ).with_entities(
        CarteiraPrincipal.cnpj_cpf.distinct()
    ).all()

    cnpjs_com_bonificacao = [c[0] for c in cnpjs_bonificacao]

    if not cnpjs_com_bonificacao:
        resultado['resumo'] = {
            'total': 0,
            'mensagem': "Nenhum cliente com bonificacao pendente na carteira"
        }
        return resultado

    pedidos_faltando = []

    for cnpj in cnpjs_com_bonificacao:
        # Buscar vendas em separacao para este CNPJ
        vendas_separacao = Separacao.query.filter(
            Separacao.cnpj_cpf == cnpj,
            Separacao.sincronizado_nf == False
        ).all()

        # Buscar bonificacoes em separacao para este CNPJ
        bonificacoes_separacao = Separacao.query.filter(
            Separacao.cnpj_cpf == cnpj,
            Separacao.sincronizado_nf == False
        ).all()

        # Buscar vendas na carteira
        vendas_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cnpj_cpf == cnpj,
            ~CarteiraPrincipal.forma_pgto_pedido.ilike('Sem Pagamento%'),
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        # Buscar bonificacoes na carteira
        bonificacoes_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cnpj_cpf == cnpj,
            CarteiraPrincipal.forma_pgto_pedido.ilike('Sem Pagamento%'),
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        # Verificar se ha desbalanceamento:
        # - Venda em separacao mas bonificacao nao
        # - Bonificacao em separacao mas venda nao

        tem_venda_separacao = len(vendas_separacao) > 0
        tem_bonificacao_separacao = any(
            s for s in vendas_separacao
            # Nota: Separacao nao tem forma_pgto, entao usamos heuristica
            # A flag real seria via join com CarteiraPrincipal
        )

        # Por simplificacao, verificamos se ha bonificacao pendente na carteira
        # enquanto ha venda em separacao
        if vendas_separacao and bonificacoes_carteira:
            # Obter info do primeiro item
            primeiro_venda = vendas_separacao[0]
            primeiro_bonificacao = bonificacoes_carteira[0]

            pedidos_faltando.append({
                'cnpj': cnpj,
                'cliente': primeiro_venda.raz_social_red,
                'pedido_venda': {
                    'num_pedido': primeiro_venda.num_pedido,
                    'status': 'Em separacao',
                    'valor': sum(float(v.valor_saldo or 0) for v in vendas_separacao)
                },
                'bonificacao': {
                    'num_pedido': primeiro_bonificacao.num_pedido,
                    'status': 'NAO esta em separacao',
                    'valor': sum(float(b.qtd_saldo_produto_pedido or 0) * float(b.preco_produto_pedido or 0) for b in bonificacoes_carteira)
                }
            })

    resultado['pedidos_faltando'] = pedidos_faltando[:args.limit]

    # Resumo
    resultado['resumo'] = {
        'total': len(pedidos_faltando),
        'mensagem': f"{'Sim! ' if pedidos_faltando else ''}{len(pedidos_faltando)} cliente(s) com bonificacao faltando na separacao" if pedidos_faltando else "Nenhum cliente com bonificacao faltando"
    }

    return resultado


def consultar_status_pedido(args):
    """
    Query 16: Pedido VCD123 ta em separacao?
    Verifica status detalhado: faturado, 100% separado, parcial, nao separado.

    LOGICA CORRETA (conforme Rafael):
    - CarteiraPrincipal.qtd_saldo_produto_pedido = saldo TOTAL do pedido (nao diminui ao separar)
    - Separacao.qtd_saldo = quantidade JA separada (sincronizado_nf=False = nao faturado)
    - Saldo pendente = cp.qtd_saldo - SUM(s.qtd_saldo WHERE mesmo produto E sincronizado_nf=False)
    - % separado = valor_separado / valor_total_pedido (NAO somar os dois!)
    """
    from app.separacao.models import Separacao
    from app.producao.models import CadastroPalletizacao

    resultado = {
        'sucesso': True,
        'tipo_analise': 'STATUS_PEDIDO',
        'pedido': None,
        'status': None,
        'detalhes': {}
    }

    # Usar resolver_pedido centralizado
    itens_carteira, num_pedido, info_busca = resolver_pedido(args.pedido, fonte='carteira')

    # Buscar em separacao tambem (sincronizado_nf=False)
    itens_separacao, _, info_sep = resolver_pedido(args.pedido, fonte='separacao')

    # Incluir metadados da busca
    resultado['busca'] = {
        'estrategia': info_busca.get('estrategia') or info_sep.get('estrategia'),
        'multiplos_encontrados': info_busca.get('multiplos_encontrados', False) or info_sep.get('multiplos_encontrados', False)
    }
    if info_busca.get('pedidos_candidatos') or info_sep.get('pedidos_candidatos'):
        resultado['busca']['outros_candidatos'] = (
            info_busca.get('pedidos_candidatos', []) +
            info_sep.get('pedidos_candidatos', [])
        )  # Sem limite - Claude decide o que mostrar

    # Se nao encontrou em nenhum lugar
    if not itens_carteira and not itens_separacao:
        resultado['sucesso'] = False
        resultado['erro'] = f"Pedido '{args.pedido}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_pedido(info_busca)
        return resultado

    # Determinar num_pedido
    if not num_pedido:
        num_pedido = itens_separacao[0].num_pedido if itens_separacao else None

    # ============================================================
    # CALCULO CORRETO: Carteira eh o TODO, Separacao eh a PARTE
    # ============================================================

    # 1. Valor TOTAL do pedido (da carteira - saldo original)
    valor_total_pedido = sum(
        float(i.qtd_saldo_produto_pedido or 0) * float(i.preco_produto_pedido or 0)
        for i in itens_carteira
    )
    itens_carteira_count = len(itens_carteira)

    # 2. Valor JA SEPARADO (nao faturado)
    valor_separado = sum(float(i.valor_saldo or 0) for i in itens_separacao)
    itens_separacao_count = len(itens_separacao)

    # 3. Verificar faturados (sincronizado_nf = True)
    itens_faturados = Separacao.query.filter(
        Separacao.num_pedido == num_pedido,
        Separacao.sincronizado_nf == True
    ).all()
    valor_faturado = sum(float(i.valor_saldo or 0) for i in itens_faturados)
    itens_faturados_count = len(itens_faturados)

    # 4. Calcular saldo PENDENTE de separacao por produto
    # Agrupar separacoes por cod_produto
    separado_por_produto = defaultdict(float)
    for s in itens_separacao:
        separado_por_produto[s.cod_produto] += float(s.qtd_saldo or 0)

    # Calcular pendente = carteira - separado (por produto)
    valor_pendente = 0.0
    qtd_pendente_total = 0.0
    itens_pendentes = []
    for cp in itens_carteira:
        qtd_carteira = float(cp.qtd_saldo_produto_pedido or 0)
        qtd_sep = separado_por_produto.get(cp.cod_produto, 0)
        qtd_pendente = max(0, qtd_carteira - qtd_sep)
        preco = float(cp.preco_produto_pedido or 0)
        valor_item_pendente = qtd_pendente * preco

        valor_pendente += valor_item_pendente
        qtd_pendente_total += qtd_pendente

        if qtd_pendente > 0:
            itens_pendentes.append({
                'cod_produto': cp.cod_produto,
                'nome_produto': cp.nome_produto,
                'qtd_carteira': qtd_carteira,
                'qtd_separada': qtd_sep,
                'qtd_pendente': qtd_pendente,
                'valor_pendente': valor_item_pendente
            })

    # 5. Calcular peso/pallet do pedido
    peso_total = 0.0
    pallet_total = 0.0
    palletizacao_cache = {}

    # Buscar palletizacao uma vez
    for cp in itens_carteira:
        if cp.cod_produto not in palletizacao_cache:
            pallet_info = CadastroPalletizacao.query.filter_by(
                cod_produto=cp.cod_produto, ativo=True
            ).first()
            if pallet_info:
                palletizacao_cache[cp.cod_produto] = {
                    'peso_bruto': float(pallet_info.peso_bruto or 0),
                    'palletizacao': float(pallet_info.palletizacao or 100)
                }
            else:
                palletizacao_cache[cp.cod_produto] = {'peso_bruto': 1.0, 'palletizacao': 100}

        qtd = float(cp.qtd_saldo_produto_pedido or 0)
        info = palletizacao_cache[cp.cod_produto]
        peso_total += qtd * info['peso_bruto']
        pallet_total += qtd / info['palletizacao'] if info['palletizacao'] > 0 else 0

    # 6. Determinar status
    # Usar valor_total_pedido como base (carteira eh a referencia)
    if valor_total_pedido == 0 and valor_faturado > 0:
        status = 'FATURADO'
        status_descricao = '100% faturado'
        pct_separado = 100.0
    elif valor_total_pedido == 0 and itens_separacao_count > 0:
        # Pedido ja foi todo separado e saiu da carteira
        status = 'SEPARADO'
        status_descricao = '100% em separacao'
        pct_separado = 100.0
    elif valor_separado > 0 and valor_pendente > 0:
        status = 'PARCIALMENTE_SEPARADO'
        # CORRECAO: % = separado / total (NAO somar separado + carteira!)
        pct_separado = (valor_separado / valor_total_pedido * 100) if valor_total_pedido > 0 else 0
        status_descricao = f'{pct_separado:.0f}% separado'
    elif valor_separado > 0 and valor_pendente == 0:
        status = 'SEPARADO'
        status_descricao = '100% em separacao'
        pct_separado = 100.0
    elif itens_carteira_count > 0:
        status = 'PENDENTE'
        status_descricao = 'Nao separado (pendente na carteira)'
        pct_separado = 0.0
    else:
        status = 'NAO_ENCONTRADO'
        status_descricao = 'Status indefinido'
        pct_separado = 0.0

    # Extrair info do cliente e data_entrega_pedido
    primeiro_item = itens_carteira[0] if itens_carteira else (itens_separacao[0] if itens_separacao else None)

    # Buscar campos importantes da carteira
    data_entrega = None
    observacao = None
    incoterm = None
    forma_pgto = None
    vendedor = None
    equipe_vendas = None
    pedido_cliente = None
    tags_pedido = None
    cep = None

    if itens_carteira:
        for cp in itens_carteira:
            if cp.data_entrega_pedido and not data_entrega:
                data_entrega = cp.data_entrega_pedido.isoformat() if hasattr(cp.data_entrega_pedido, 'isoformat') else str(cp.data_entrega_pedido)
            if cp.observ_ped_1 and not observacao:
                observacao = cp.observ_ped_1
            if hasattr(cp, 'incoterm') and cp.incoterm and not incoterm:
                incoterm = cp.incoterm
            if hasattr(cp, 'forma_pgto_pedido') and cp.forma_pgto_pedido and not forma_pgto:
                forma_pgto = cp.forma_pgto_pedido
            if hasattr(cp, 'vendedor') and cp.vendedor and not vendedor:
                vendedor = cp.vendedor
            if hasattr(cp, 'equipe_vendas') and cp.equipe_vendas and not equipe_vendas:
                equipe_vendas = cp.equipe_vendas
            if hasattr(cp, 'pedido_cliente') and cp.pedido_cliente and not pedido_cliente:
                pedido_cliente = cp.pedido_cliente
            if hasattr(cp, 'tags_pedido') and cp.tags_pedido and not tags_pedido:
                tags_pedido = cp.tags_pedido
            if hasattr(cp, 'cep_endereco_ent') and cp.cep_endereco_ent and not cep:
                cep = cp.cep_endereco_ent

    # Identificar se é bonificação
    eh_bonificacao = forma_pgto and 'sem pagamento' in forma_pgto.lower() if forma_pgto else False

    # Buscar lotes de separação existentes (detalhado)
    lotes_separacao = []
    if itens_separacao:
        lotes_dict = {}
        for s in itens_separacao:
            lote_id = s.separacao_lote_id or 'SEM_LOTE'
            if lote_id not in lotes_dict:
                lotes_dict[lote_id] = {
                    'lote_id': lote_id,
                    'expedicao': s.expedicao.isoformat() if s.expedicao else None,
                    'status': s.status,
                    'itens': 0,
                    'valor': 0.0
                }
            lotes_dict[lote_id]['itens'] += 1
            lotes_dict[lote_id]['valor'] += float(s.valor_saldo or 0)
        lotes_separacao = list(lotes_dict.values())

    resultado['pedido'] = {
        'num_pedido': num_pedido,
        'cliente': primeiro_item.raz_social_red if primeiro_item else None,
        'cnpj': primeiro_item.cnpj_cpf if primeiro_item else None,
        'cidade': primeiro_item.nome_cidade if primeiro_item else None,
        'uf': primeiro_item.cod_uf if primeiro_item else None,
        'cep': cep,
        'data_entrega_pedido': data_entrega,
        'observ_ped_1': observacao,
        'peso_total_kg': round(peso_total, 2),
        'pallets_total': round(pallet_total, 2),
        # Campos CRITICOS para regras de negocio
        'incoterm': incoterm,
        'forma_pgto': forma_pgto,
        'eh_bonificacao': eh_bonificacao,
        'eh_fob': incoterm and incoterm.upper() == 'FOB',
        # Campos para comunicacao
        'vendedor': vendedor,
        'equipe_vendas': equipe_vendas,
        'pedido_cliente': pedido_cliente,
        'tags_pedido': tags_pedido,
        # Lotes de separacao existentes
        'lotes_separacao': lotes_separacao
    }

    resultado['status'] = status
    resultado['detalhes'] = {
        'status_descricao': status_descricao,
        'percentual_separado': round(pct_separado, 1),
        'em_separacao': {
            'itens': itens_separacao_count,
            'valor': valor_separado
        },
        'pendente_separar': {
            'itens': len(itens_pendentes),
            'valor': valor_pendente,
            'detalhes': itens_pendentes[:30]  # Limitar para nao poluir
        },
        'valor_total_pedido': valor_total_pedido,
        'faturado': {
            'itens': itens_faturados_count,
            'valor': valor_faturado
        }
    }

    resultado['resumo'] = {
        'mensagem': f"Pedido {num_pedido} - {resultado['pedido']['cliente']}: {status_descricao}"
    }

    return resultado


def consultar_consolidacao(args):
    """
    Query 19: Tem mais pedido pra mandar junto com o Assai lj 123?
    Busca pedidos proximos para consolidar com base em CEP, cidade e sub_rota.
    """
    from app.carteira.models import CarteiraPrincipal

    resultado = {
        'sucesso': True,
        'tipo_analise': 'CONSOLIDACAO',
        'pedido_base': None,
        'candidatos_consolidacao': {
            'mesmo_cep': [],
            'mesma_cidade': [],
            'mesma_sub_rota': []
        },
        'resumo': {}
    }

    # Resolver pedido base
    itens_base, num_pedido_base, info_busca = resolver_pedido(args.consolidar_com, fonte='ambos')

    if not itens_base:
        resultado['sucesso'] = False
        resultado['erro'] = f"Pedido '{args.consolidar_com}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_pedido(info_busca)
        return resultado

    primeiro_item = itens_base[0]

    # Extrair dados de localizacao do pedido base
    cep_base = getattr(primeiro_item, 'cep_endereco_ent', None)
    cidade_base = primeiro_item.nome_cidade
    uf_base = primeiro_item.cod_uf
    sub_rota_base = getattr(primeiro_item, 'sub_rota', None)

    resultado['pedido_base'] = {
        'num_pedido': num_pedido_base,
        'cliente': primeiro_item.raz_social_red,
        'cidade': cidade_base,
        'uf': uf_base,
        'cep': cep_base,
        'sub_rota': sub_rota_base
    }

    # Incluir metadados da busca
    resultado['busca'] = {
        'estrategia': info_busca.get('estrategia'),
        'multiplos_encontrados': info_busca.get('multiplos_encontrados', False)
    }

    # Buscar candidatos na carteira (excluindo o pedido base)
    # Prioridade 1: Mesmo CEP
    if cep_base:
        itens_mesmo_cep = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cep_endereco_ent == cep_base,
            CarteiraPrincipal.num_pedido != num_pedido_base,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        # Agrupar por pedido com campos criticos
        pedidos_cep = {}
        for item in itens_mesmo_cep:
            if item.num_pedido not in pedidos_cep:
                valor = float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
                data_ent = item.data_entrega_pedido.isoformat() if item.data_entrega_pedido and hasattr(item.data_entrega_pedido, 'isoformat') else None
                inco = getattr(item, 'incoterm', None)
                fpgto = getattr(item, 'forma_pgto_pedido', None)
                pedidos_cep[item.num_pedido] = {
                    'num_pedido': item.num_pedido,
                    'cliente': item.raz_social_red,
                    'cidade': item.nome_cidade,
                    'valor': valor,
                    # Campos CRITICOS para decisao
                    'data_entrega_pedido': data_ent,
                    'observ_ped_1': item.observ_ped_1,
                    'incoterm': inco,
                    'eh_fob': inco and inco.upper() == 'FOB',
                    'eh_bonificacao': fpgto and 'sem pagamento' in fpgto.lower() if fpgto else False
                }
            else:
                pedidos_cep[item.num_pedido]['valor'] += float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)

        resultado['candidatos_consolidacao']['mesmo_cep'] = list(pedidos_cep.values())  # Sem limite

    # Prioridade 2: Mesma cidade
    if cidade_base and uf_base:
        itens_mesma_cidade = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.nome_cidade == cidade_base,
            CarteiraPrincipal.cod_uf == uf_base,
            CarteiraPrincipal.num_pedido != num_pedido_base,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        # Agrupar por pedido (excluindo os que ja estao em mesmo_cep)
        pedidos_cep_nums = {p['num_pedido'] for p in resultado['candidatos_consolidacao']['mesmo_cep']}
        pedidos_cidade = {}
        for item in itens_mesma_cidade:
            if item.num_pedido not in pedidos_cep_nums and item.num_pedido not in pedidos_cidade:
                valor = float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
                data_ent = item.data_entrega_pedido.isoformat() if item.data_entrega_pedido and hasattr(item.data_entrega_pedido, 'isoformat') else None
                inco = getattr(item, 'incoterm', None)
                fpgto = getattr(item, 'forma_pgto_pedido', None)
                pedidos_cidade[item.num_pedido] = {
                    'num_pedido': item.num_pedido,
                    'cliente': item.raz_social_red,
                    'cidade': item.nome_cidade,
                    'valor': valor,
                    # Campos CRITICOS para decisao
                    'data_entrega_pedido': data_ent,
                    'observ_ped_1': item.observ_ped_1,
                    'incoterm': inco,
                    'eh_fob': inco and inco.upper() == 'FOB',
                    'eh_bonificacao': fpgto and 'sem pagamento' in fpgto.lower() if fpgto else False
                }
            elif item.num_pedido in pedidos_cidade:
                pedidos_cidade[item.num_pedido]['valor'] += float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)

        resultado['candidatos_consolidacao']['mesma_cidade'] = list(pedidos_cidade.values())  # Sem limite

    # Prioridade 3: Mesma sub_rota (se disponivel)
    if sub_rota_base:
        itens_mesma_rota = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.sub_rota == sub_rota_base,
            CarteiraPrincipal.num_pedido != num_pedido_base,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        # Agrupar por pedido (excluindo os que ja estao nas outras categorias)
        pedidos_anteriores = (
            {p['num_pedido'] for p in resultado['candidatos_consolidacao']['mesmo_cep']} |
            {p['num_pedido'] for p in resultado['candidatos_consolidacao']['mesma_cidade']}
        )
        pedidos_rota = {}
        for item in itens_mesma_rota:
            if item.num_pedido not in pedidos_anteriores and item.num_pedido not in pedidos_rota:
                valor = float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
                data_ent = item.data_entrega_pedido.isoformat() if item.data_entrega_pedido and hasattr(item.data_entrega_pedido, 'isoformat') else None
                inco = getattr(item, 'incoterm', None)
                fpgto = getattr(item, 'forma_pgto_pedido', None)
                pedidos_rota[item.num_pedido] = {
                    'num_pedido': item.num_pedido,
                    'cliente': item.raz_social_red,
                    'cidade': item.nome_cidade,
                    'sub_rota': sub_rota_base,
                    'valor': valor,
                    # Campos CRITICOS para decisao
                    'data_entrega_pedido': data_ent,
                    'observ_ped_1': item.observ_ped_1,
                    'incoterm': inco,
                    'eh_fob': inco and inco.upper() == 'FOB',
                    'eh_bonificacao': fpgto and 'sem pagamento' in fpgto.lower() if fpgto else False
                }
            elif item.num_pedido in pedidos_rota:
                pedidos_rota[item.num_pedido]['valor'] += float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)

        resultado['candidatos_consolidacao']['mesma_sub_rota'] = list(pedidos_rota.values())  # Sem limite

    # Resumo
    total_cep = len(resultado['candidatos_consolidacao']['mesmo_cep'])
    total_cidade = len(resultado['candidatos_consolidacao']['mesma_cidade'])
    total_rota = len(resultado['candidatos_consolidacao']['mesma_sub_rota'])
    total = total_cep + total_cidade + total_rota

    resultado['resumo'] = {
        'total_candidatos': total,
        'por_cep': total_cep,
        'por_cidade': total_cidade,
        'por_sub_rota': total_rota,
        'mensagem': (
            f"Pedidos para consolidar com {resultado['pedido_base']['cliente']} ({cidade_base}/{uf_base}):\n"
            f"MESMO CEP: {total_cep} pedido(s)\n"
            f"MESMA CIDADE: {total_cidade} pedido(s)\n"
            f"MESMA SUB-ROTA: {total_rota} pedido(s)"
        ) if total > 0 else f"Nenhum pedido encontrado para consolidar com {resultado['pedido_base']['cliente']}"
    }

    return resultado


def consultar_situacao_pedidos_por_produto(args):
    """
    Consulta pedidos que contem um produto especifico.

    Fluxo:
    1. Resolve termo do produto para cod_produto via resolver_produto_unico
    2. Busca em Separacao (--em-separacao) ou CarteiraPrincipal (padrao)
    3. Filtra por data de expedicao se --ate-data informado
    4. Agrupa por pedido

    Args:
        args: Argumentos parseados (produto, ate_data, em_separacao, limit)

    Returns:
        dict: Resultado com pedidos encontrados
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao

    resultado = {
        'sucesso': True,
        'tipo_analise': 'PEDIDOS_POR_PRODUTO',
        'termo_busca': args.produto,
        'produto': None,
        'filtro_data': None,
        'fonte': 'separacao' if args.em_separacao else 'carteira',
        'pedidos': [],
        'resumo': {}
    }

    # 1. Resolver produto
    produto_info, info_busca = resolver_produto_unico(args.produto)

    if not produto_info:
        resultado['sucesso'] = False
        resultado['erro'] = f"Produto '{args.produto}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_produto(info_busca)
        if info_busca.get('candidatos'):
            resultado['candidatos'] = info_busca['candidatos']
        return resultado

    cod_produto = produto_info['cod_produto']
    nome_produto = produto_info['nome_produto']

    resultado['produto'] = {
        'cod_produto': cod_produto,
        'nome_produto': nome_produto
    }
    resultado['busca'] = {
        'encontrado': info_busca.get('encontrado', False),
        'multiplos': info_busca.get('multiplos', False)
    }
    if info_busca.get('candidatos'):
        resultado['busca']['outros_candidatos'] = info_busca['candidatos']

    # 2. Parsear data limite se informada
    data_limite = None
    if args.ate_data:
        try:
            data_limite = parse_data_natural(args.ate_data)
            resultado['filtro_data'] = {
                'termo': args.ate_data,
                'data': data_limite.isoformat()
            }
        except ValueError as e:
            resultado['sucesso'] = False
            resultado['erro'] = str(e)
            return resultado

    # 3. Buscar pedidos
    pedidos_dict = defaultdict(lambda: {
        'num_pedido': None,
        'cliente': None,
        'cnpj': None,
        'cidade': None,
        'uf': None,
        'expedicao': None,
        'qtd_produto': 0.0,
        'valor_produto': 0.0,
        'total_itens': 0
    })

    if args.em_separacao:
        # Buscar em Separacao (nao faturados)
        query = Separacao.query.filter(
            Separacao.cod_produto == cod_produto,
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0  # CORRECAO: Filtrar itens com saldo zerado
        )

        if data_limite:
            query = query.filter(Separacao.expedicao <= data_limite)

        itens = query.all()

        for item in itens:
            num = item.num_pedido
            if pedidos_dict[num]['num_pedido'] is None:
                pedidos_dict[num]['num_pedido'] = num
                pedidos_dict[num]['cliente'] = item.raz_social_red
                pedidos_dict[num]['cnpj'] = item.cnpj_cpf
                pedidos_dict[num]['cidade'] = item.nome_cidade
                pedidos_dict[num]['uf'] = item.cod_uf
                pedidos_dict[num]['expedicao'] = item.expedicao.isoformat() if item.expedicao else None

            pedidos_dict[num]['qtd_produto'] += float(item.qtd_saldo or 0)  # type: ignore
            pedidos_dict[num]['valor_produto'] += float(item.valor_saldo or 0) # type: ignore
            pedidos_dict[num]['total_itens'] += 1 # type: ignore
    else:
        # Buscar em CarteiraPrincipal (saldo pendente > 0)
        query = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        )

        if data_limite:
            query = query.filter(CarteiraPrincipal.data_entrega_pedido <= data_limite)

        itens = query.all()

        for item in itens:
            num = item.num_pedido
            if pedidos_dict[num]['num_pedido'] is None:
                pedidos_dict[num]['num_pedido'] = num
                pedidos_dict[num]['cliente'] = item.raz_social_red
                pedidos_dict[num]['cnpj'] = item.cnpj_cpf
                pedidos_dict[num]['cidade'] = item.nome_cidade
                pedidos_dict[num]['uf'] = item.cod_uf
                pedidos_dict[num]['expedicao'] = item.data_entrega_pedido.isoformat() if item.data_entrega_pedido else None

            qtd = float(item.qtd_saldo_produto_pedido or 0)
            preco = float(item.preco_produto_pedido or 0)
            pedidos_dict[num]['qtd_produto'] += qtd # type: ignore
            pedidos_dict[num]['valor_produto'] += qtd * preco # type: ignore
            pedidos_dict[num]['total_itens'] += 1 # type: ignore

    # 4. Converter para lista e ordenar por valor
    pedidos_lista = list(pedidos_dict.values())
    pedidos_lista.sort(key=lambda x: -x['valor_produto']) # type: ignore

    resultado['pedidos'] = pedidos_lista[:args.limit]

    # 5. Resumo
    total_qtd = sum(p['qtd_produto'] for p in pedidos_lista)
    total_valor = sum(p['valor_produto'] for p in pedidos_lista)
    fonte_texto = 'em separacao' if args.em_separacao else 'na carteira'
    data_texto = f" ate {data_limite.strftime('%d/%m/%Y')}" if data_limite else ""

    resultado['resumo'] = {
        'total_pedidos': len(pedidos_lista),
        'total_quantidade': total_qtd,
        'total_valor': total_valor,
        'mensagem': (
            f"{len(pedidos_lista)} pedido(s) {fonte_texto} com {nome_produto}{data_texto}. "
            f"Total: {total_qtd:,.0f} unid, R$ {total_valor:,.2f}"
        ) if pedidos_lista else f"Nenhum pedido encontrado {fonte_texto} com {nome_produto}{data_texto}"
    }

    return resultado


def consultar_co_passageiros_embarque(args):
    """
    Lista todos os clientes/pedidos/NFs que compartilham o mesmo embarque.
    Util para saber "quem mais vai no caminhao".

    Aceita --co-passageiros-embarque <numero_embarque>
    """
    from app import db
    from sqlalchemy import text

    numero_embarque = args.co_passageiros_embarque

    try:
        numero_embarque = int(numero_embarque)
    except (ValueError, TypeError):
        return {
            'sucesso': False,
            'erro': f"Numero de embarque invalido: '{numero_embarque}'. Informe um numero inteiro."
        }

    # Buscar embarque pelo numero
    sql_embarque = """
        SELECT
            e.id,
            e.numero,
            e.data_embarque,
            e.tipo_carga,
            e.peso_total,
            e.valor_total,
            e.pallet_total,
            e.status,
            e.modalidade,
            t.razao_social as transportadora
        FROM embarques e
        LEFT JOIN transportadoras t ON t.id = e.transportadora_id
        WHERE e.numero = :numero
    """
    result = db.session.execute(text(sql_embarque), {'numero': numero_embarque})
    row = result.fetchone()

    if not row:
        return {
            'sucesso': False,
            'erro': f"Embarque numero {numero_embarque} nao encontrado."
        }

    embarque = dict(zip(result.keys(), row))

    # Buscar todos os itens do embarque
    sql_itens = """
        SELECT
            ei.id,
            ei.cnpj_cliente,
            ei.cliente,
            ei.pedido,
            ei.nota_fiscal,
            ei.peso,
            ei.valor,
            ei.volumes,
            ei.pallets,
            ei.uf_destino,
            ei.cidade_destino,
            ei.status,
            ei.protocolo_agendamento,
            ei.data_agenda,
            ei.agendamento_confirmado
        FROM embarque_itens ei
        WHERE ei.embarque_id = :embarque_id
        AND ei.status = 'ativo'
        ORDER BY ei.uf_destino, ei.cidade_destino, ei.cliente
    """
    result_itens = db.session.execute(text(sql_itens), {'embarque_id': embarque['id']})
    itens = [dict(zip(result_itens.keys(), r)) for r in result_itens.fetchall()]

    # Agregar por cliente (um cliente pode ter multiplos pedidos no mesmo embarque)
    clientes_dict = {}
    for item in itens:
        chave = item['cnpj_cliente'] or item['cliente']
        if chave not in clientes_dict:
            clientes_dict[chave] = {
                'cliente': item['cliente'],
                'cnpj': item['cnpj_cliente'],
                'uf_destino': item['uf_destino'],
                'cidade_destino': item['cidade_destino'],
                'pedidos': [],
                'peso_total': 0,
                'valor_total': 0,
                'volumes_total': 0,
                'pallets_total': 0
            }
        clientes_dict[chave]['pedidos'].append({
            'pedido': item['pedido'],
            'nota_fiscal': item['nota_fiscal'],
            'peso': item['peso'],
            'valor': item['valor'],
            'volumes': item['volumes'],
            'pallets': item['pallets'],
            'agendamento': item['protocolo_agendamento'],
            'data_agenda': item['data_agenda'],
            'confirmado': item['agendamento_confirmado']
        })
        clientes_dict[chave]['peso_total'] += (item['peso'] or 0)
        clientes_dict[chave]['valor_total'] += (item['valor'] or 0)
        clientes_dict[chave]['volumes_total'] += (item['volumes'] or 0)
        clientes_dict[chave]['pallets_total'] += (item['pallets'] or 0)

    clientes_lista = sorted(clientes_dict.values(), key=lambda c: c['peso_total'], reverse=True)

    # Destinos unicos
    destinos = list({f"{item['cidade_destino']}/{item['uf_destino']}" for item in itens})

    return {
        'sucesso': True,
        'modo': 'co_passageiros_embarque',
        'embarque': {
            'numero': embarque['numero'],
            'data_embarque': embarque['data_embarque'],
            'tipo_carga': embarque['tipo_carga'],
            'transportadora': embarque['transportadora'],
            'modalidade': embarque['modalidade'],
            'peso_total': embarque['peso_total'],
            'valor_total': embarque['valor_total'],
            'pallet_total': embarque['pallet_total'],
            'status': embarque['status']
        },
        'resumo': {
            'total_clientes': len(clientes_lista),
            'total_itens': len(itens),
            'total_destinos': len(destinos),
            'destinos': destinos,
            'mensagem': (
                f"Embarque {numero_embarque}: {len(clientes_lista)} cliente(s), "
                f"{len(itens)} item(ns), {len(destinos)} destino(s). "
                f"Transp: {embarque['transportadora'] or 'N/D'}. "
                f"Tipo: {embarque['tipo_carga'] or 'N/D'}."
            )
        },
        'clientes': clientes_lista
    }


def main():
    from app import create_app

    parser = argparse.ArgumentParser(
        description='Consultar pedidos por diversos filtros (Q8, Q10, Q14, Q16, Q19)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python consultando_situacao_pedidos.py --grupo atacadao
  python consultando_situacao_pedidos.py --grupo atacadao --produto ketchup  # combina grupo + produto
  python consultando_situacao_pedidos.py --cliente "Carrefour"              # NOVO: busca por cliente (GAP-01)
  python consultando_situacao_pedidos.py --cliente "45.543.915"             # NOVO: busca por CNPJ
  python consultando_situacao_pedidos.py --cliente "Carrefour" --produto palmito  # NOVO: cliente + produto (GAP-03)
  python consultando_situacao_pedidos.py --atrasados
  python consultando_situacao_pedidos.py --verificar-bonificacao
  python consultando_situacao_pedidos.py --pedido VCD123 --status
  python consultando_situacao_pedidos.py --consolidar-com "assai 123"
  python consultando_situacao_pedidos.py --produto "azeitona verde pouch" --em-separacao
  python consultando_situacao_pedidos.py --produto palmito --ate-data amanha
  python consultando_situacao_pedidos.py --produto pessego --ate-data 15/12
  python consultando_situacao_pedidos.py --co-passageiros-embarque 1234
        """
    )

    # Argumentos
    parser.add_argument('--pedido', help='Numero do pedido ou termo de busca')
    parser.add_argument('--grupo', help='Grupo empresarial (atacadao, assai, tenda)')
    parser.add_argument('--cliente', help='CNPJ ou nome parcial do cliente (ex: "Carrefour", "45.543.915")')
    parser.add_argument('--atrasados', action='store_true', help='Listar pedidos atrasados')
    parser.add_argument('--verificar-bonificacao', action='store_true', help='Verificar bonificacoes faltando')
    parser.add_argument('--status', action='store_true', help='Mostrar status detalhado do pedido')
    parser.add_argument('--consolidar-com', help='Buscar pedidos para consolidar com este')
    parser.add_argument('--produto', help='Termo de busca do produto (nome, abreviacao)')
    parser.add_argument('--ate-data', dest='ate_data', help='Data limite de expedicao (hoje, amanha, dd/mm/yyyy, dd/mm, dd)')
    parser.add_argument('--em-separacao', dest='em_separacao', action='store_true', help='Buscar em Separacao ao inves de CarteiraPrincipal')
    parser.add_argument('--co-passageiros-embarque', dest='co_passageiros_embarque', help='Numero do embarque para listar co-passageiros')
    parser.add_argument('--limit', type=int, default=100, help='Limite de resultados (default: 100)')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Determinar qual analise executar
        # IMPORTANTE: Verificar combinacoes ANTES dos filtros individuais
        if args.co_passageiros_embarque:
            resultado = consultar_co_passageiros_embarque(args)
        elif args.grupo and args.produto:
            resultado = consultar_situacao_pedidos_grupo_produto(args)
        elif args.cliente and args.produto:
            # GAP-03: cliente + produto
            resultado = consultar_situacao_pedidos_cliente_produto(args)
        elif args.grupo:
            resultado = consultar_situacao_pedidos_grupo(args)
        elif args.cliente:
            # GAP-01: cliente (CNPJ ou nome)
            resultado = consultar_situacao_pedidos_cliente(args)
        elif args.atrasados:
            resultado = consultar_situacao_pedidos_atrasados(args)
        elif args.verificar_bonificacao:
            resultado = verificar_bonificacao(args)
        elif args.pedido and args.status:
            resultado = consultar_status_pedido(args)
        elif args.consolidar_com:
            resultado = consultar_consolidacao(args)
        elif args.produto:
            resultado = consultar_situacao_pedidos_por_produto(args)
        else:
            resultado = {
                'sucesso': False,
                'erro': 'Informe ao menos um filtro: --grupo, --cliente, --atrasados, --verificar-bonificacao, --pedido com --status, --consolidar-com, --produto, ou --co-passageiros-embarque'
            }

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()
