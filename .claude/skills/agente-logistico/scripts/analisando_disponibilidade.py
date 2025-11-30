#!/usr/bin/env python3
"""
Script: analisando_disponibilidade.py
Queries cobertas: Q1, Q2, Q3, Q4, Q5, Q6, Q9, Q11, Q12

Analisa disponibilidade de estoque para pedidos ou grupos de clientes.

Uso:
    --pedido VCD123                          # Q1: Disponibilidade de pedido
    --pedido VCD123 --data amanha            # Q2: Disponibilidade em data futura
    --pedido VCD123 --sugerir-adiamento      # Q3: Sugerir pedidos para adiar
    --grupo assai --uf SP                    # Q4: Gargalos por grupo/UF
    --grupo assai --diagnosticar-origem      # Q5: Falta absoluta vs relativa
    --data amanha --sem-agendamento          # Q6: Pedidos enviaveis
    --grupo atacadao --loja 183 --completude # Q9: Completude do pedido
    --atrasados --diagnosticar-causa         # Q11: Atrasados por falta
    --ranking-impacto                        # Q12: Ranking pedidos travando
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


def parse_data(data_str: str) -> date:
    """Converte string de data para date object"""
    if data_str.lower() in ['hoje', 'today']:
        return date.today()
    elif data_str.lower() in ['amanha', 'tomorrow']:
        return date.today() + timedelta(days=1)
    else:
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(data_str, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Formato de data invalido: {data_str}")


def encontrar_data_disponibilidade(projecao: dict, qtd_necessaria: float) -> str:
    """Encontra a primeira data em que havera estoque suficiente"""
    if not projecao.get('projecao'):
        return None

    for dia in projecao['projecao']:
        saldo = dia.get('saldo_final', 0)
        if saldo >= qtd_necessaria:
            return dia.get('data')

    return None


def calcular_completude(num_pedido: str, itens_carteira: list) -> dict:
    """Query 9: Calcula completude do pedido"""
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from sqlalchemy import func
    from app import db

    valor_original = db.session.query(
        func.sum(CarteiraPrincipal.qtd_produto_pedido * CarteiraPrincipal.preco_produto_pedido)
    ).filter(
        CarteiraPrincipal.num_pedido == num_pedido
    ).scalar() or 0

    valor_pendente = sum(
        float(i.qtd_saldo_produto_pedido or 0) * float(i.preco_produto_pedido or 0)
        for i in itens_carteira
    )

    valor_faturado = db.session.query(
        func.sum(Separacao.valor_saldo)
    ).filter(
        Separacao.num_pedido == num_pedido,
        Separacao.sincronizado_nf == True
    ).scalar() or 0

    valor_original = float(valor_original)
    valor_faturado = float(valor_faturado)
    percentual_completado = (valor_faturado / valor_original * 100) if valor_original > 0 else 0

    return {
        'valor_original': round(valor_original, 2),
        'valor_faturado': round(valor_faturado, 2),
        'valor_pendente': round(valor_pendente, 2),
        'percentual_completado': round(percentual_completado, 1),
        'falta_para_matar': round(100 - percentual_completado, 1)
    }


# ===== Q1, Q2, Q9: Analise de pedido especifico =====

def analisar_pedido(args):
    """Q1, Q2, Q9: Analisa disponibilidade para um pedido especifico"""
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples

    resultado = {
        'sucesso': True,
        'tipo_analise': 'PEDIDO',
        'termo_busca': args.pedido,
        'pedido': None,
        'itens': [],
        'analise': {}
    }

    # Usar resolver_pedido centralizado (busca flexivel)
    itens_carteira, num_pedido, info_busca = resolver_pedido(args.pedido, fonte='carteira')

    if not itens_carteira:
        resultado['sucesso'] = False
        resultado['erro'] = f"Pedido '{args.pedido}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_pedido(info_busca)
        resultado['estrategia_busca'] = info_busca.get('estrategia')
        return resultado

    # Incluir metadados da busca no resultado
    resultado['busca'] = {
        'estrategia': info_busca.get('estrategia'),
        'multiplos_encontrados': info_busca.get('multiplos_encontrados', False)
    }
    if info_busca.get('pedidos_candidatos'):
        resultado['busca']['outros_candidatos'] = info_busca['pedidos_candidatos']

    primeiro_item = itens_carteira[0]
    resultado['pedido'] = {
        'num_pedido': num_pedido,
        'cliente': primeiro_item.raz_social_red,
        'cnpj': primeiro_item.cnpj_cpf,
        'cidade': primeiro_item.nome_cidade,
        'uf': primeiro_item.cod_uf
    }

    data_analise = None
    if args.data:
        try:
            data_analise = parse_data(args.data)
        except ValueError as e:
            resultado['sucesso'] = False
            resultado['erro'] = str(e)
            return resultado

    itens_disponiveis = []
    itens_com_falta = []
    data_disponibilidade_maxima = date.today()

    for item in itens_carteira:
        qtd_necessaria = float(item.qtd_saldo_produto_pedido or 0)
        preco = float(item.preco_produto_pedido or 0)
        projecao = ServicoEstoqueSimples.calcular_projecao(item.cod_produto, 28)
        estoque_atual = projecao.get('estoque_atual', 0)

        item_info = {
            'cod_produto': item.cod_produto,
            'nome_produto': item.nome_produto,
            'qtd_necessaria': qtd_necessaria,
            'valor_item': round(qtd_necessaria * preco, 2),
            'estoque_atual': estoque_atual
        }

        if data_analise:
            dias_ate_data = (data_analise - date.today()).days
            estoque_na_data = estoque_atual
            if projecao.get('projecao'):
                for dia in projecao['projecao']:
                    if dia.get('data') == data_analise.isoformat():
                        estoque_na_data = dia.get('saldo_final', estoque_atual)
                        break

            item_info['estoque_na_data'] = estoque_na_data
            item_info['data_analise'] = data_analise.isoformat()

            if estoque_na_data >= qtd_necessaria:
                item_info['status'] = 'DISPONIVEL'
                itens_disponiveis.append(item_info)
            else:
                item_info['status'] = 'FALTA'
                item_info['falta'] = round(qtd_necessaria - estoque_na_data, 2)
                data_disp = encontrar_data_disponibilidade(projecao, qtd_necessaria)
                item_info['data_disponibilidade'] = data_disp
                itens_com_falta.append(item_info)
        else:
            if estoque_atual >= qtd_necessaria:
                item_info['status'] = 'DISPONIVEL'
                item_info['data_disponibilidade'] = date.today().isoformat()
                itens_disponiveis.append(item_info)
            else:
                item_info['status'] = 'FALTA'
                item_info['falta'] = round(qtd_necessaria - estoque_atual, 2)
                data_disp = encontrar_data_disponibilidade(projecao, qtd_necessaria)
                item_info['data_disponibilidade'] = data_disp

                if data_disp:
                    data_disp_obj = datetime.strptime(data_disp, '%Y-%m-%d').date()
                    if data_disp_obj > data_disponibilidade_maxima:
                        data_disponibilidade_maxima = data_disp_obj

                itens_com_falta.append(item_info)

        resultado['itens'].append(item_info)

    # Montar analise
    if data_analise:
        resultado['analise'] = {
            'tipo': 'RUPTURA_EM_DATA',
            'data_analise': data_analise.isoformat(),
            'total_itens': len(itens_carteira),
            'itens_disponiveis': len(itens_disponiveis),
            'itens_com_falta': len(itens_com_falta),
            'percentual_disponivel': round(len(itens_disponiveis) / len(itens_carteira) * 100, 1) if itens_carteira else 0,
            'itens_faltantes': itens_com_falta
        }
        if itens_com_falta:
            resultado['analise']['mensagem'] = f"Se enviar em {data_analise.isoformat()}, faltarao {len(itens_com_falta)} produto(s)"
        else:
            resultado['analise']['mensagem'] = f"Todos os {len(itens_carteira)} itens estarao disponiveis em {data_analise.isoformat()}"
    else:
        tem_previsao = any(i.get('data_disponibilidade') for i in itens_com_falta)
        if itens_com_falta and not tem_previsao:
            data_100_str = "SEM_PREVISAO"
        elif itens_com_falta:
            data_100_str = data_disponibilidade_maxima.isoformat()
        else:
            data_100_str = date.today().isoformat()

        resultado['analise'] = {
            'tipo': 'PREVISAO_DISPONIBILIDADE',
            'total_itens': len(itens_carteira),
            'itens_disponiveis_hoje': len(itens_disponiveis),
            'itens_com_falta': len(itens_com_falta),
            'percentual_disponivel': round(len(itens_disponiveis) / len(itens_carteira) * 100, 1) if itens_carteira else 0,
            'data_100_disponivel': data_100_str,
            'itens_limitantes': itens_com_falta  # Sem limite - Claude decide o que mostrar
        }
        if itens_com_falta:
            if tem_previsao:
                resultado['analise']['mensagem'] = f"Pedido 100% disponivel em {data_disponibilidade_maxima.isoformat()}"
            else:
                resultado['analise']['mensagem'] = f"SEM PREVISAO de disponibilidade para {len(itens_com_falta)} item(ns) nos proximos 28 dias"
        else:
            resultado['analise']['mensagem'] = "Todos os itens disponiveis HOJE"

    # Completude (Q9)
    if args.completude:
        resultado['completude'] = calcular_completude(num_pedido, itens_carteira)

    # Sugerir adiamento (Q3)
    if args.sugerir_adiamento and itens_com_falta:
        resultado['sugestoes_adiamento'] = sugerir_adiamento(num_pedido, itens_com_falta, args.limit)

    return resultado


# ===== Q3: Sugerir pedidos para adiar =====

def sugerir_adiamento(num_pedido_prioridade: str, produtos_falta: list, limit: int = 10) -> list:
    """Q3: Identifica pedidos que, se adiados, liberam estoque"""
    from app.separacao.models import Separacao
    from sqlalchemy import func
    from app import db

    amanha = date.today() + timedelta(days=1)
    sugestoes = []

    for produto in produtos_falta:
        cod_produto = produto['cod_produto']

        separacoes = Separacao.query.filter(
            Separacao.cod_produto == cod_produto,
            Separacao.num_pedido != num_pedido_prioridade,
            Separacao.sincronizado_nf == False,
            Separacao.expedicao <= amanha
        ).order_by(Separacao.expedicao.desc()).all()

        for sep in separacoes:
            valor_total_pedido = db.session.query(
                func.sum(Separacao.valor_saldo)
            ).filter(
                Separacao.num_pedido == sep.num_pedido,
                Separacao.sincronizado_nf == False
            ).scalar() or 1

            valor_item = float(sep.valor_saldo or 0)
            concentracao = valor_item / float(valor_total_pedido) if valor_total_pedido else 0

            sugestao = {
                'num_pedido': sep.num_pedido,
                'cliente': sep.raz_social_red,
                'expedicao_atual': sep.expedicao.isoformat() if sep.expedicao else None,
                'produto_liberado': cod_produto,
                'nome_produto': sep.nome_produto,
                'qtd_liberada': float(sep.qtd_saldo or 0),
                'concentracao': round(concentracao * 100, 1),
                'impacto': f"Libera {float(sep.qtd_saldo or 0):.0f} un de {sep.nome_produto}"
            }

            if not any(s['num_pedido'] == sep.num_pedido and s['produto_liberado'] == cod_produto for s in sugestoes):
                sugestoes.append(sugestao)

    sugestoes.sort(key=lambda x: (-x['concentracao'], x['expedicao_atual'] or ''))
    return sugestoes[:limit]


# ===== Q4, Q5: Analise de gargalos por grupo/cliente =====

def analisar_grupo(args):
    """Q4, Q5: Analisa gargalos para um grupo/cliente"""
    from app.carteira.models import CarteiraPrincipal
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from sqlalchemy import or_
    from app import db

    resultado = {
        'sucesso': True,
        'tipo_analise': 'GRUPO',
        'filtros_aplicados': {},
        'gargalos': [],
        'resumo': {}
    }

    filtros = []

    if args.grupo:
        prefixos = get_prefixos_grupo(args.grupo)
        if prefixos:
            filtros_cnpj = [CarteiraPrincipal.cnpj_cpf.like(f'{p}%') for p in prefixos]
            filtros.append(or_(*filtros_cnpj))
            resultado['filtros_aplicados']['grupo'] = args.grupo
        else:
            resultado['sucesso'] = False
            resultado['erro'] = f"Grupo '{args.grupo}' nao encontrado"
            resultado['sugestao'] = f"Grupos validos: {listar_grupos_disponiveis()}"
            return resultado

    if args.loja:
        filtros.append(CarteiraPrincipal.raz_social_red.ilike(f'%{args.loja}%'))
        resultado['filtros_aplicados']['loja'] = args.loja

    if args.uf:
        filtros.append(CarteiraPrincipal.cod_uf == args.uf.upper())
        resultado['filtros_aplicados']['uf'] = args.uf.upper()

    if not filtros:
        resultado['sucesso'] = False
        resultado['erro'] = 'Informe ao menos um filtro: --grupo, --loja ou --uf'
        return resultado

    itens_carteira = CarteiraPrincipal.query.filter(
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
        *filtros
    ).all()

    if not itens_carteira:
        resultado['resumo'] = {
            'total_gargalos': 0,
            'mensagem': 'Nenhum item pendente encontrado para os filtros informados'
        }
        return resultado

    # Agrupar por produto
    produtos_analise = {}
    for item in itens_carteira:
        cod = item.cod_produto
        if cod not in produtos_analise:
            produtos_analise[cod] = {
                'cod_produto': cod,
                'nome_produto': item.nome_produto,
                'demanda_cliente': 0,
                'pedidos_afetados': set(),
                'valor_total': 0
            }
        produtos_analise[cod]['demanda_cliente'] += float(item.qtd_saldo_produto_pedido or 0)
        produtos_analise[cod]['pedidos_afetados'].add(item.num_pedido)
        produtos_analise[cod]['valor_total'] += float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)

    # Verificar gargalos
    gargalos = []
    for cod, dados in produtos_analise.items():
        estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod)
        demanda = dados['demanda_cliente']

        if estoque_atual < demanda:
            falta = demanda - estoque_atual
            gargalo = {
                'cod_produto': cod,
                'nome_produto': dados['nome_produto'],
                'estoque_atual': estoque_atual,
                'demanda_cliente': demanda,
                'falta': round(falta, 2),
                'pedidos_afetados': len(dados['pedidos_afetados']),
                'valor_impactado': round(dados['valor_total'], 2)
            }

            if args.diagnosticar_origem:
                gargalo['diagnostico'] = diagnosticar_origem_falta(cod, demanda, estoque_atual, args)

            gargalos.append(gargalo)

    gargalos.sort(key=lambda x: (-x['pedidos_afetados'], -x['falta']))
    resultado['gargalos'] = gargalos[:args.limit]

    resultado['resumo'] = {
        'total_gargalos': len(gargalos),
        'total_pedidos_impactados': len(set(p for item in itens_carteira for p in [item.num_pedido])),
        'valor_total_impactado': round(sum(g['valor_impactado'] for g in gargalos), 2),
        'mensagem': f"{len(gargalos)} produto(s) com falta impactando pedidos"
    }

    return resultado


def diagnosticar_origem_falta(cod_produto: str, demanda_cliente: float, estoque_atual: float, args) -> dict:
    """Q5: Distingue falta absoluta vs falta relativa"""
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from sqlalchemy import func
    from app import db

    filtros_exclusao = []

    if args.grupo:
        prefixos = get_prefixos_grupo(args.grupo)
        for p in prefixos:
            filtros_exclusao.append(~CarteiraPrincipal.cnpj_cpf.like(f'{p}%'))

    demanda_outros = db.session.query(
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
    ).filter(
        CarteiraPrincipal.cod_produto == cod_produto,
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
        *filtros_exclusao
    ).scalar() or 0

    demanda_outros = float(demanda_outros)

    if estoque_atual >= demanda_cliente:
        tipo = 'FALTA_RELATIVA'
        explicacao = f"Estoque ({estoque_atual:.0f}) >= Demanda cliente ({demanda_cliente:.0f}). Falta por comprometimento com outros"
    else:
        falta_absoluta = demanda_cliente - estoque_atual
        tipo = 'FALTA_ABSOLUTA'
        explicacao = f"Mesmo sem outros pedidos, faltariam {falta_absoluta:.0f} unidades"

    return {
        'tipo': tipo,
        'estoque_atual': estoque_atual,
        'demanda_cliente': demanda_cliente,
        'demanda_outros': demanda_outros,
        'explicacao': explicacao
    }


# ===== Q6: Listar pedidos enviaveis =====

def listar_enviaveis(args):
    """Q6: Lista pedidos que podem ser enviados (sem agendamento, 100% disponivel)"""
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from sqlalchemy import func
    from app import db

    resultado = {
        'sucesso': True,
        'tipo_analise': 'ENVIAVEIS',
        'data_analise': None,
        'filtros_aplicados': {},
        'pedidos_enviaveis': [],
        'pedidos_parciais': [],
        'resumo': {}
    }

    try:
        data_analise = parse_data(args.data)
        resultado['data_analise'] = data_analise.isoformat()
    except ValueError as e:
        resultado['sucesso'] = False
        resultado['erro'] = str(e)
        return resultado

    # Buscar pedidos pendentes
    pedidos_carteira = db.session.query(
        CarteiraPrincipal.num_pedido,
        CarteiraPrincipal.cnpj_cpf,
        CarteiraPrincipal.raz_social_red,
        CarteiraPrincipal.nome_cidade,
        CarteiraPrincipal.cod_uf,
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
        func.count(CarteiraPrincipal.id).label('qtd_itens')
    ).filter(
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    )

    if args.uf:
        pedidos_carteira = pedidos_carteira.filter(CarteiraPrincipal.cod_uf == args.uf.upper())
        resultado['filtros_aplicados']['uf'] = args.uf.upper()

    pedidos_carteira = pedidos_carteira.group_by(
        CarteiraPrincipal.num_pedido,
        CarteiraPrincipal.cnpj_cpf,
        CarteiraPrincipal.raz_social_red,
        CarteiraPrincipal.nome_cidade,
        CarteiraPrincipal.cod_uf
    ).all()

    pedidos_em_separacao = set(
        s.num_pedido for s in Separacao.query.filter(
            Separacao.sincronizado_nf == False
        ).with_entities(Separacao.num_pedido).distinct().all()
    )

    pedidos_pendentes = [p for p in pedidos_carteira if p.num_pedido not in pedidos_em_separacao]

    if args.sem_agendamento:
        resultado['filtros_aplicados']['sem_agendamento'] = True
        pedidos_pendentes = filtrar_sem_agendamento(pedidos_pendentes)

    pedidos_enviaveis = []
    pedidos_parciais = []

    for pedido in pedidos_pendentes:
        itens = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido == pedido.num_pedido,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        itens_disponiveis = 0
        for item in itens:
            estoque = ServicoEstoqueSimples.calcular_estoque_atual(item.cod_produto)
            if estoque >= float(item.qtd_saldo_produto_pedido or 0):
                itens_disponiveis += 1

        total_itens = len(itens)
        percentual_disponivel = round(itens_disponiveis / total_itens * 100, 1) if total_itens > 0 else 0

        pedido_info = {
            'num_pedido': pedido.num_pedido,
            'cliente': pedido.raz_social_red,
            'cnpj': pedido.cnpj_cpf,
            'cidade': pedido.nome_cidade,
            'uf': pedido.cod_uf,
            'valor_total': float(pedido.valor_total or 0),
            'qtd_itens': pedido.qtd_itens,
            'percentual_disponivel': percentual_disponivel
        }

        if percentual_disponivel == 100:
            pedido_info['status'] = '100%_DISPONIVEL'
            pedidos_enviaveis.append(pedido_info)
        elif percentual_disponivel >= 80:
            pedido_info['status'] = 'PARCIAL_80+'
            pedidos_parciais.append(pedido_info)

    pedidos_enviaveis.sort(key=lambda x: -x['valor_total'])
    pedidos_parciais.sort(key=lambda x: -x['valor_total'])

    resultado['pedidos_enviaveis'] = pedidos_enviaveis[:args.limit]
    resultado['pedidos_parciais'] = pedidos_parciais  # Sem limite - Claude decide o que mostrar

    total_valor_enviavel = sum(p['valor_total'] for p in pedidos_enviaveis)
    resultado['resumo'] = {
        'total_enviaveis': len(pedidos_enviaveis),
        'valor_total_enviavel': round(total_valor_enviavel, 2),
        'total_parciais': len(pedidos_parciais),
        'mensagem': f"{len(pedidos_enviaveis)} pedidos 100% disponiveis para envio em {data_analise.isoformat()}, total R$ {total_valor_enviavel:,.2f}"
    }

    return resultado


def filtrar_sem_agendamento(pedidos: list) -> list:
    """Filtra pedidos de clientes que nao precisam de agendamento"""
    from app.cadastros_agendamento.models import ContatoAgendamento

    cnpjs_com_agendamento = set()
    contatos = ContatoAgendamento.query.filter(
        ContatoAgendamento.forma != 'SEM AGENDAMENTO'
    ).all()

    for contato in contatos:
        if contato.cnpj:
            cnpjs_com_agendamento.add(contato.cnpj)

    return [p for p in pedidos if p.cnpj_cpf not in cnpjs_com_agendamento]


# ===== Q11: Atrasados por falta =====

def analisar_atrasados(args):
    """Q11: Analisa pedidos atrasados e diagnostica se eh por falta de estoque"""
    from app.separacao.models import Separacao
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from sqlalchemy import func
    from app import db

    resultado = {
        'sucesso': True,
        'tipo_analise': 'ATRASADOS',
        'data_referencia': date.today().isoformat(),
        'pedidos_atrasados': [],
        'resumo': {}
    }

    hoje = date.today()

    query = db.session.query(
        Separacao.num_pedido,
        Separacao.cnpj_cpf,
        Separacao.raz_social_red,
        Separacao.nome_cidade,
        Separacao.cod_uf,
        Separacao.expedicao,
        func.sum(Separacao.valor_saldo).label('valor_total'),
        func.count(Separacao.id).label('qtd_itens')
    ).filter(
        Separacao.expedicao < hoje,
        Separacao.sincronizado_nf == False
    )

    pedidos_atrasados = query.group_by(
        Separacao.num_pedido,
        Separacao.cnpj_cpf,
        Separacao.raz_social_red,
        Separacao.nome_cidade,
        Separacao.cod_uf,
        Separacao.expedicao
    ).order_by(Separacao.expedicao.asc()).limit(args.limit).all()

    if not pedidos_atrasados:
        resultado['resumo'] = {'total_pedidos': 0, 'mensagem': 'Nenhum pedido atrasado encontrado'}
        return resultado

    total_valor = 0
    pedidos_por_falta = []
    pedidos_outro_motivo = []

    for pedido in pedidos_atrasados:
        dias_atraso = (hoje - pedido.expedicao).days if pedido.expedicao else 0
        pedido_info = {
            'num_pedido': pedido.num_pedido,
            'cliente': pedido.raz_social_red,
            'cnpj': pedido.cnpj_cpf,
            'cidade': pedido.nome_cidade,
            'uf': pedido.cod_uf,
            'expedicao': pedido.expedicao.isoformat() if pedido.expedicao else None,
            'dias_atraso': dias_atraso,
            'valor_total': float(pedido.valor_total or 0),
            'qtd_itens': pedido.qtd_itens
        }
        total_valor += float(pedido.valor_total or 0)

        if args.diagnosticar_causa:
            causa, itens_faltantes = diagnosticar_causa_atraso(pedido.num_pedido)
            pedido_info['causa'] = causa
            pedido_info['itens_faltantes'] = itens_faltantes

            if causa == 'FALTA_ESTOQUE':
                pedidos_por_falta.append(pedido_info)
            else:
                pedidos_outro_motivo.append(pedido_info)
        else:
            resultado['pedidos_atrasados'].append(pedido_info)

    if args.diagnosticar_causa:
        resultado['por_falta_estoque'] = {'quantidade': len(pedidos_por_falta), 'pedidos': pedidos_por_falta}
        resultado['outro_motivo'] = {'quantidade': len(pedidos_outro_motivo), 'pedidos': pedidos_outro_motivo}
        resultado['resumo'] = {
            'total_pedidos': len(pedidos_atrasados),
            'total_valor': round(total_valor, 2),
            'por_falta': len(pedidos_por_falta),
            'outro_motivo': len(pedidos_outro_motivo),
            'mensagem': f"{len(pedidos_por_falta)} pedidos atrasados por falta de estoque, {len(pedidos_outro_motivo)} por outro motivo"
        }
    else:
        resultado['resumo'] = {
            'total_pedidos': len(pedidos_atrasados),
            'total_valor': round(total_valor, 2),
            'mensagem': f"{len(pedidos_atrasados)} pedidos atrasados, total R$ {total_valor:,.2f}"
        }

    return resultado


def diagnosticar_causa_atraso(num_pedido: str) -> tuple:
    """Verifica se o atraso eh por falta de estoque"""
    from app.separacao.models import Separacao
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples

    itens = Separacao.query.filter(
        Separacao.num_pedido == num_pedido,
        Separacao.sincronizado_nf == False
    ).all()

    itens_faltantes = []
    for item in itens:
        qtd_necessaria = float(item.qtd_saldo or 0)
        estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(item.cod_produto)

        if estoque_atual < qtd_necessaria:
            itens_faltantes.append({
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'qtd_necessaria': qtd_necessaria,
                'estoque_atual': estoque_atual,
                'falta': round(qtd_necessaria - estoque_atual, 2)
            })

    return ('FALTA_ESTOQUE', itens_faltantes) if itens_faltantes else ('OUTRO_MOTIVO', [])


# ===== Q12: Ranking de pedidos travando carteira =====

def ranking_impacto(args):
    """Q12: Ranking de pedidos que mais travam a carteira por consumir estoque em ruptura"""
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from sqlalchemy import func
    from app import db

    resultado = {
        'sucesso': True,
        'tipo_analise': 'RANKING_IMPACTO',
        'produtos_em_ruptura': [],
        'pedidos_travando': [],
        'resumo': {}
    }

    # Agregar demanda por produto
    demanda_carteira = db.session.query(
        CarteiraPrincipal.cod_produto,
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('demanda')
    ).filter(
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    ).group_by(CarteiraPrincipal.cod_produto).all()

    demanda_separacao = db.session.query(
        Separacao.cod_produto,
        func.sum(Separacao.qtd_saldo).label('demanda')
    ).filter(
        Separacao.sincronizado_nf == False
    ).group_by(Separacao.cod_produto).all()

    demanda_total = defaultdict(float)
    for cod, dem in demanda_carteira:
        demanda_total[cod] += float(dem or 0)
    for cod, dem in demanda_separacao:
        demanda_total[cod] += float(dem or 0)

    # Identificar rupturas
    produtos_ruptura = []
    for cod_produto, demanda in demanda_total.items():
        estoque = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)
        if estoque < demanda:
            produtos_ruptura.append({
                'cod_produto': cod_produto,
                'estoque_atual': estoque,
                'demanda_total': demanda,
                'deficit': demanda - estoque
            })

    if not produtos_ruptura:
        resultado['resumo'] = {'total_produtos_ruptura': 0, 'mensagem': 'Nenhum produto em ruptura encontrado'}
        return resultado

    resultado['produtos_em_ruptura'] = produtos_ruptura  # Sem limite - Claude decide o que mostrar

    # Calcular impacto por pedido
    impacto_pedidos = defaultdict(lambda: {
        'num_pedido': '',
        'cliente': '',
        'produtos_ruptura': [],
        'impacto_total': 0,
        'valor_total': 0
    })

    for prod_ruptura in produtos_ruptura:
        cod_produto = prod_ruptura['cod_produto']
        deficit = prod_ruptura['deficit']

        # Separacoes
        separacoes = Separacao.query.filter(
            Separacao.cod_produto == cod_produto,
            Separacao.sincronizado_nf == False
        ).all()

        for sep in separacoes:
            qtd_consumida = float(sep.qtd_saldo or 0)
            impacto = qtd_consumida / deficit if deficit > 0 else 0

            if impacto_pedidos[sep.num_pedido]['num_pedido'] == '':
                impacto_pedidos[sep.num_pedido]['num_pedido'] = sep.num_pedido
                impacto_pedidos[sep.num_pedido]['cliente'] = sep.raz_social_red

            impacto_pedidos[sep.num_pedido]['produtos_ruptura'].append({
                'cod_produto': cod_produto,
                'nome_produto': sep.nome_produto,
                'qtd_consumida': qtd_consumida,
                'impacto_percentual': round(impacto * 100, 1)
            })
            impacto_pedidos[sep.num_pedido]['impacto_total'] += impacto
            impacto_pedidos[sep.num_pedido]['valor_total'] += float(sep.valor_saldo or 0)

        # Carteira
        itens_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        for item in itens_carteira:
            qtd_consumida = float(item.qtd_saldo_produto_pedido or 0)
            impacto = qtd_consumida / deficit if deficit > 0 else 0

            if impacto_pedidos[item.num_pedido]['num_pedido'] == '':
                impacto_pedidos[item.num_pedido]['num_pedido'] = item.num_pedido
                impacto_pedidos[item.num_pedido]['cliente'] = item.raz_social_red

            if not any(p['cod_produto'] == cod_produto for p in impacto_pedidos[item.num_pedido]['produtos_ruptura']):
                impacto_pedidos[item.num_pedido]['produtos_ruptura'].append({
                    'cod_produto': cod_produto,
                    'nome_produto': item.nome_produto,
                    'qtd_consumida': qtd_consumida,
                    'impacto_percentual': round(impacto * 100, 1)
                })
                impacto_pedidos[item.num_pedido]['impacto_total'] += impacto
                valor_item = qtd_consumida * float(item.preco_produto_pedido or 0)
                impacto_pedidos[item.num_pedido]['valor_total'] += valor_item

    pedidos_lista = list(impacto_pedidos.values())
    pedidos_lista.sort(key=lambda x: -x['impacto_total'])

    for pedido in pedidos_lista:
        pedido['impacto_total'] = round(pedido['impacto_total'], 2)
        pedido['valor_total'] = round(pedido['valor_total'], 2)
        pedido['qtd_produtos_ruptura'] = len(pedido['produtos_ruptura'])

    resultado['pedidos_travando'] = pedidos_lista[:args.limit]

    resultado['resumo'] = {
        'total_produtos_ruptura': len(produtos_ruptura),
        'total_pedidos_analisados': len(pedidos_lista),
        'mensagem': f"{len(pedidos_lista)} pedidos consumindo estoque de {len(produtos_ruptura)} produtos em ruptura"
    }

    return resultado


# ===== MAIN =====

def main():
    from app import create_app

    parser = argparse.ArgumentParser(
        description='Analisa disponibilidade de estoque (Q1, Q2, Q3, Q4, Q5, Q6, Q9, Q11, Q12)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python analisando_disponibilidade.py --pedido VCD123                          # Q1
  python analisando_disponibilidade.py --pedido VCD123 --data amanha            # Q2
  python analisando_disponibilidade.py --pedido VCD123 --data amanha --sugerir-adiamento  # Q3
  python analisando_disponibilidade.py --grupo assai --uf SP                    # Q4
  python analisando_disponibilidade.py --grupo assai --diagnosticar-origem      # Q5
  python analisando_disponibilidade.py --data amanha --sem-agendamento          # Q6
  python analisando_disponibilidade.py --grupo atacadao --loja 183 --completude # Q9
  python analisando_disponibilidade.py --atrasados --diagnosticar-causa         # Q11
  python analisando_disponibilidade.py --ranking-impacto                        # Q12
        """
    )
    # Filtros
    parser.add_argument('--pedido', help='Numero do pedido ou "grupo termo" (ex: "atacadao 183")')
    parser.add_argument('--grupo', help='Grupo empresarial (atacadao, assai, tenda)')
    parser.add_argument('--loja', help='Identificador da loja (em raz_social_red)')
    parser.add_argument('--uf', help='Filtrar por UF')
    parser.add_argument('--data', help='Data para analise (hoje, amanha, ou YYYY-MM-DD)')

    # Flags de funcionalidade
    parser.add_argument('--sem-agendamento', action='store_true', help='Apenas pedidos sem exigencia de agendamento (Q6)')
    parser.add_argument('--sugerir-adiamento', action='store_true', help='Sugerir pedidos para adiar (Q3)')
    parser.add_argument('--diagnosticar-origem', action='store_true', help='Diagnosticar falta absoluta vs relativa (Q5)')
    parser.add_argument('--completude', action='store_true', help='Calcular completude do pedido (Q9)')
    parser.add_argument('--atrasados', action='store_true', help='Analisar pedidos com expedicao vencida (Q11)')
    parser.add_argument('--diagnosticar-causa', action='store_true', help='Diagnosticar causa do atraso (Q11)')
    parser.add_argument('--ranking-impacto', action='store_true', help='Ranking de pedidos travando carteira (Q12)')

    # Outros
    parser.add_argument('--limit', type=int, default=100, help='Limite de resultados (default: 100)')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Determinar qual analise executar
        if args.ranking_impacto:
            resultado = ranking_impacto(args)
        elif args.atrasados:
            resultado = analisar_atrasados(args)
        elif args.pedido:
            resultado = analisar_pedido(args)
        elif args.grupo or args.loja or args.uf:
            if args.data and args.sem_agendamento:
                resultado = listar_enviaveis(args)
            else:
                resultado = analisar_grupo(args)
        elif args.data and args.sem_agendamento:
            resultado = listar_enviaveis(args)
        else:
            resultado = {
                'sucesso': False,
                'erro': 'Informe ao menos um filtro: --pedido, --grupo, --loja, --atrasados, --ranking-impacto ou --data com --sem-agendamento'
            }

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()
