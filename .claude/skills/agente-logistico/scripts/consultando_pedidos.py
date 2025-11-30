#!/usr/bin/env python3
"""
Script: consultando_pedidos.py
Queries cobertas: Q8, Q10, Q14, Q16, Q19

Consulta pedidos por diversos filtros e perspectivas.

Uso:
    --grupo atacadao                      # Q8: Pedidos pendentes do grupo
    --atrasados                           # Q10: Pedidos atrasados para embarque
    --verificar-bonificacao               # Q14: Pedidos faltando bonificacao
    --pedido VCD123 --status              # Q16: Status do pedido
    --consolidar-com "assai 123"          # Q19: Pedidos para consolidar
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
    get_prefixos_grupo,
    listar_grupos_disponiveis,
    formatar_sugestao_pedido,
    GRUPOS_EMPRESARIAIS
)


def decimal_default(obj):
    """Serializa Decimal para JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def consultar_pedidos_grupo(args):
    """
    Query 8: Tem pedido pendente pro Atacadao?
    Busca pedidos pendentes de um grupo empresarial.
    """
    from app.carteira.models import CarteiraPrincipal
    from sqlalchemy import or_, func

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

        pedidos_dict[num]['total_itens'] += 1
        preco = float(item.preco_produto_pedido or 0)
        qtd = float(item.qtd_saldo_produto_pedido or 0)
        pedidos_dict[num]['valor_total'] += preco * qtd

    # Converter para lista
    pedidos_lista = list(pedidos_dict.values())
    pedidos_lista.sort(key=lambda x: -x['valor_total'])

    resultado['pedidos'] = pedidos_lista[:args.limit]

    # Resumo
    total_valor = sum(p['valor_total'] for p in pedidos_lista)
    resultado['resumo'] = {
        'total_pedidos': len(pedidos_lista),
        'valor_total': total_valor,
        'mensagem': f"Sim! {len(pedidos_lista)} pedido(s) pendente(s) para {args.grupo.capitalize()}. Total: R$ {total_valor:,.2f}"
    }

    return resultado


def consultar_pedidos_atrasados(args):
    """
    Query 10: Tem pedido atrasado pra embarcar?
    Busca pedidos com expedicao < hoje em Separacao (sincronizado_nf=False).
    """
    from app.separacao.models import Separacao
    from sqlalchemy import func

    resultado = {
        'sucesso': True,
        'tipo_analise': 'PEDIDOS_ATRASADOS',
        'pedidos': [],
        'resumo': {}
    }

    hoje = date.today()

    # Buscar separacoes atrasadas (expedicao < hoje E nao faturadas)
    itens = Separacao.query.filter(
        Separacao.expedicao < hoje,
        Separacao.sincronizado_nf == False
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

        pedidos_dict[num]['total_itens'] += 1
        pedidos_dict[num]['valor_total'] += float(item.valor_saldo or 0)

    # Converter para lista e ordenar por dias de atraso
    pedidos_lista = list(pedidos_dict.values())
    pedidos_lista.sort(key=lambda x: -x['dias_atraso'])

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
    from sqlalchemy import func

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
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao

    resultado = {
        'sucesso': True,
        'tipo_analise': 'STATUS_PEDIDO',
        'pedido': None,
        'status': None,
        'detalhes': {}
    }

    # Usar resolver_pedido centralizado
    itens_carteira, num_pedido, info_busca = resolver_pedido(args.pedido, fonte='carteira')

    # Buscar em separacao tambem
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

    # Calcular valores
    valor_carteira = sum(
        float(i.qtd_saldo_produto_pedido or 0) * float(i.preco_produto_pedido or 0)
        for i in itens_carteira
    )
    itens_carteira_count = len(itens_carteira)

    valor_separacao = sum(float(i.valor_saldo or 0) for i in itens_separacao)
    itens_separacao_count = len(itens_separacao)

    # Verificar faturados (sincronizado_nf = True)
    itens_faturados = Separacao.query.filter(
        Separacao.num_pedido == num_pedido,
        Separacao.sincronizado_nf == True
    ).all()
    valor_faturado = sum(float(i.valor_saldo or 0) for i in itens_faturados)
    itens_faturados_count = len(itens_faturados)

    # Determinar status
    valor_total = valor_carteira + valor_separacao + valor_faturado

    if valor_faturado > 0 and valor_carteira == 0 and valor_separacao == 0:
        status = 'FATURADO'
        status_descricao = '100% faturado'
    elif itens_separacao_count > 0 and itens_carteira_count == 0:
        status = 'SEPARADO'
        status_descricao = '100% em separacao'
    elif itens_separacao_count > 0 and itens_carteira_count > 0:
        status = 'PARCIALMENTE_SEPARADO'
        pct_separado = (valor_separacao / (valor_carteira + valor_separacao)) * 100 if (valor_carteira + valor_separacao) > 0 else 0
        status_descricao = f'{pct_separado:.0f}% separado'
    elif itens_carteira_count > 0:
        status = 'PENDENTE'
        status_descricao = 'Nao separado (pendente na carteira)'
    else:
        status = 'NAO_ENCONTRADO'
        status_descricao = 'Status indefinido'

    # Extrair info do cliente
    primeiro_item = itens_carteira[0] if itens_carteira else (itens_separacao[0] if itens_separacao else None)

    resultado['pedido'] = {
        'num_pedido': num_pedido,
        'cliente': primeiro_item.raz_social_red if primeiro_item else None,
        'cnpj': primeiro_item.cnpj_cpf if primeiro_item else None,
        'cidade': primeiro_item.nome_cidade if primeiro_item else None,
        'uf': primeiro_item.cod_uf if primeiro_item else None
    }

    resultado['status'] = status
    resultado['detalhes'] = {
        'status_descricao': status_descricao,
        'em_separacao': {
            'itens': itens_separacao_count,
            'valor': valor_separacao
        },
        'pendente_carteira': {
            'itens': itens_carteira_count,
            'valor': valor_carteira
        },
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
    from app.separacao.models import Separacao

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

        # Agrupar por pedido
        pedidos_cep = {}
        for item in itens_mesmo_cep:
            if item.num_pedido not in pedidos_cep:
                valor = float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
                pedidos_cep[item.num_pedido] = {
                    'num_pedido': item.num_pedido,
                    'cliente': item.raz_social_red,
                    'cidade': item.nome_cidade,
                    'valor': valor
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
                pedidos_cidade[item.num_pedido] = {
                    'num_pedido': item.num_pedido,
                    'cliente': item.raz_social_red,
                    'cidade': item.nome_cidade,
                    'valor': valor
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
                pedidos_rota[item.num_pedido] = {
                    'num_pedido': item.num_pedido,
                    'cliente': item.raz_social_red,
                    'cidade': item.nome_cidade,
                    'sub_rota': sub_rota_base,
                    'valor': valor
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


def main():
    from app import create_app

    parser = argparse.ArgumentParser(
        description='Consultar pedidos por diversos filtros (Q8, Q10, Q14, Q16, Q19)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python consultando_pedidos.py --grupo atacadao
  python consultando_pedidos.py --atrasados
  python consultando_pedidos.py --verificar-bonificacao
  python consultando_pedidos.py --pedido VCD123 --status
  python consultando_pedidos.py --consolidar-com "assai 123"
        """
    )

    # Argumentos
    parser.add_argument('--pedido', help='Numero do pedido ou termo de busca')
    parser.add_argument('--grupo', help='Grupo empresarial (atacadao, assai, tenda)')
    parser.add_argument('--atrasados', action='store_true', help='Listar pedidos atrasados')
    parser.add_argument('--verificar-bonificacao', action='store_true', help='Verificar bonificacoes faltando')
    parser.add_argument('--status', action='store_true', help='Mostrar status detalhado do pedido')
    parser.add_argument('--consolidar-com', help='Buscar pedidos para consolidar com este')
    parser.add_argument('--limit', type=int, default=100, help='Limite de resultados (default: 100)')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Determinar qual analise executar
        if args.grupo:
            resultado = consultar_pedidos_grupo(args)
        elif args.atrasados:
            resultado = consultar_pedidos_atrasados(args)
        elif args.verificar_bonificacao:
            resultado = verificar_bonificacao(args)
        elif args.pedido and args.status:
            resultado = consultar_status_pedido(args)
        elif args.consolidar_com:
            resultado = consultar_consolidacao(args)
        else:
            resultado = {
                'sucesso': False,
                'erro': 'Informe ao menos um filtro: --grupo, --atrasados, --verificar-bonificacao, --pedido com --status, ou --consolidar-com'
            }

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()
