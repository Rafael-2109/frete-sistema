#!/usr/bin/env python3
"""
Script: consultando_produtos_estoque.py
Queries cobertas: Q13, Q17, Q18, Q20 + SITUACAO COMPLETA

Consulta estoque atual, entradas, pendencias, projecoes e situacao completa de produtos.

Uso:
    --produto palmito --completo          # ⭐ SITUACAO COMPLETA (estoque, separacoes, demanda, producao, projecao)
    --produto palmito --entradas          # Q13: Chegou o produto?
    --produto pessego --pendente          # Q17: Falta embarcar muito?
    --produto pessego --sobra             # Q18: Quanto vai sobrar no estoque?
    --ruptura --dias 7                    # Q20: O que vai dar falta essa semana?

A opcao --completo retorna TUDO que o Agent SDK precisa:
    1. Estoque atual e menor estoque nos proximos 7 dias
    2. Separacoes por data de expedicao (detalhado com pedidos)
    3. Demanda total (Carteira bruta/liquida + Separacoes)
    4. Programacao de producao (proximos 14 dias)
    5. Projecao dia a dia (estoque projetado)
    6. Indicadores: sobra, cobertura em dias, % disponivel, previsao de ruptura
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
from resolver_entidades import ( # noqa: E402
    resolver_produto_unico,
    formatar_sugestao_produto
)


def decimal_default(obj):
    """Serializa Decimal para JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def consultar_movimentacoes(args, tipo='entradas'):
    """
    Query 13: Chegou o palmito? / Saiu muito palmito?
    Busca movimentacoes recentes de produtos e estoque atual.

    Args:
        tipo: 'entradas' (qtd > 0) ou 'saidas' (qtd < 0)
    """
    from app.estoque.models import MovimentacaoEstoque
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from app.producao.models import CadastroPalletizacao

    tipo_analise = 'ENTRADAS_PRODUTO' if tipo == 'entradas' else 'SAIDAS_PRODUTO'

    resultado = {
        'sucesso': True,
        'tipo_analise': tipo_analise,
        'termo_busca': args.produto,
        'produtos': [],
        'resumo': {}
    }

    # Resolver produto usando modulo centralizado
    produto_info, info_busca = resolver_produto_unico(args.produto)

    if not produto_info and not info_busca.get('multiplos'):
        resultado['sucesso'] = False
        resultado['erro'] = f"Produto '{args.produto}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_produto(info_busca)
        return resultado

    # Se multiplos candidatos, usar todos
    if info_busca.get('multiplos') and not produto_info:
        produtos_buscar = [c['cod_produto'] for c in info_busca.get('candidatos', [])]
    elif produto_info:
        produtos_buscar = [produto_info['cod_produto']]
    else:
        resultado['sucesso'] = False
        resultado['erro'] = "Nao foi possivel identificar produtos"
        return resultado

    # Incluir metadados da busca
    resultado['busca'] = {
        'encontrado': info_busca.get('encontrado', False),
        'multiplos': info_busca.get('multiplos', False)
    }
    if info_busca.get('candidatos'):
        resultado['busca']['candidatos'] = info_busca['candidatos']

    hoje = date.today()
    data_limite = hoje - timedelta(days=args.dias)

    produtos_resultado = []

    for cod_produto in produtos_buscar:
        # Buscar cadastro do produto
        cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        nome_produto = cadastro.nome_produto if cadastro else cod_produto

        # Filtro de quantidade baseado no tipo (entradas: >0, saidas: <0)
        if tipo == 'entradas':
            filtro_qtd = MovimentacaoEstoque.qtd_movimentacao > 0
        else:
            filtro_qtd = MovimentacaoEstoque.qtd_movimentacao < 0

        # Buscar movimentacoes recentes
        movimentacoes = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.cod_produto == cod_produto,
            filtro_qtd,
            MovimentacaoEstoque.data_movimentacao >= data_limite,
            MovimentacaoEstoque.ativo == True
        ).order_by(
            MovimentacaoEstoque.data_movimentacao.desc()
        ).limit(args.limit_entradas).all()

        # Calcular estoque atual
        estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

        movimentacoes_lista = []
        for mov in movimentacoes:
            movimentacoes_lista.append({
                'data': mov.data_movimentacao.isoformat() if mov.data_movimentacao else None,
                'quantidade': abs(float(mov.qtd_movimentacao or 0)),  # Valor absoluto para exibicao
                'tipo_movimentacao': mov.tipo_movimentacao,
                'local_movimentacao': mov.local_movimentacao,
                'numero_nf': mov.numero_nf
            })

        # Agrupar por data
        movimentacoes_por_data = defaultdict(float)
        for m in movimentacoes_lista:
            if m['data']:
                movimentacoes_por_data[m['data']] += m['quantidade']

        total_movimentacoes = sum(m['quantidade'] for m in movimentacoes_lista)

        produtos_resultado.append({
            'cod_produto': cod_produto,
            'nome_produto': nome_produto,
            'estoque_atual': estoque_atual,
            'movimentacoes_recentes': movimentacoes_lista,  # Sem limite - Claude decide o que mostrar
            'total_periodo': total_movimentacoes,
            'por_data': dict(movimentacoes_por_data)
        })

    resultado['produtos'] = produtos_resultado

    # Resumo
    if produtos_resultado:
        total_movimentacoes = sum(p['total_periodo'] for p in produtos_resultado)
        if total_movimentacoes > 0:
            if tipo == 'entradas':
                msg = f"Sim! Chegaram {args.produto} recentemente:\n"
                sinal = '+'
            else:
                msg = f"Saidas de {args.produto} recentes:\n"
                sinal = '-'

            for p in produtos_resultado:
                if p['total_periodo'] > 0:
                    msg += f"- {p['nome_produto']}: {sinal}{p['total_periodo']:.0f} un (Estoque: {p['estoque_atual']:.0f})\n"
        else:
            tipo_msg = 'entrada' if tipo == 'entradas' else 'saida'
            msg = f"Nenhuma {tipo_msg} de {args.produto} nos ultimos {args.dias} dias"
    else:
        msg = f"Produto {args.produto} nao encontrado"

    resultado['resumo'] = {
        'total_produtos': len(produtos_resultado),
        'mensagem': msg.strip()
    }

    return resultado


def consultar_produtos_entradas(args):
    """Wrapper para manter compatibilidade"""
    return consultar_movimentacoes(args, tipo='entradas')


def consultar_produtos_saidas(args):
    """Wrapper para consultar saidas"""
    return consultar_movimentacoes(args, tipo='saidas')


def consultar_produtos_pendente_embarque(args):
    """
    Query 17: Falta embarcar muito pessego?
    Calcula quantidade na carteira vs em separacao.
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from app.producao.models import CadastroPalletizacao

    resultado = {
        'sucesso': True,
        'tipo_analise': 'PENDENTE_EMBARQUE',
        'termo_busca': args.produto,
        'produtos': [],
        'resumo': {}
    }

    # Resolver produto
    produto_info, info_busca = resolver_produto_unico(args.produto)

    if not produto_info and not info_busca.get('multiplos'):
        resultado['sucesso'] = False
        resultado['erro'] = f"Produto '{args.produto}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_produto(info_busca)
        return resultado

    # Obter lista de produtos
    if info_busca.get('multiplos') and not produto_info:
        produtos_buscar = [c['cod_produto'] for c in info_busca.get('candidatos', [])]
    elif produto_info:
        produtos_buscar = [produto_info['cod_produto']]
    else:
        resultado['sucesso'] = False
        resultado['erro'] = "Nao foi possivel identificar produtos"
        return resultado

    resultado['busca'] = {
        'encontrado': info_busca.get('encontrado', False),
        'multiplos': info_busca.get('multiplos', False)
    }

    produtos_resultado = []

    for cod_produto in produtos_buscar:
        # Buscar cadastro
        cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        nome_produto = cadastro.nome_produto if cadastro else cod_produto

        # Buscar itens na carteira (com detalhes por pedido)
        itens_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        # Agrupar por pedido
        pedidos_carteira = {}
        for item in itens_carteira:
            num = item.num_pedido
            if num not in pedidos_carteira:
                pedidos_carteira[num] = {
                    'num_pedido': num,
                    'cliente': item.raz_social_red,
                    'quantidade': 0
                }
            pedidos_carteira[num]['quantidade'] += float(item.qtd_saldo_produto_pedido or 0)

        total_carteira = sum(p['quantidade'] for p in pedidos_carteira.values())

        # Buscar itens em separacao
        itens_separacao = Separacao.query.filter(
            Separacao.cod_produto == cod_produto,
            Separacao.sincronizado_nf == False
        ).all()

        # Agrupar por pedido
        pedidos_separacao = {}
        for item in itens_separacao:
            num = item.num_pedido
            if num not in pedidos_separacao:
                pedidos_separacao[num] = {
                    'num_pedido': num,
                    'cliente': item.raz_social_red,
                    'quantidade': 0
                }
            pedidos_separacao[num]['quantidade'] += float(item.qtd_saldo or 0)

        total_separacao = sum(p['quantidade'] for p in pedidos_separacao.values())

        # Falta separar = carteira - separacao
        falta_separar = max(0, float(total_carteira) - float(total_separacao))

        # Ordenar pedidos por quantidade (maior primeiro) - sem limite, Claude decide o que mostrar
        lista_pedidos_carteira = sorted(
            pedidos_carteira.values(),
            key=lambda x: -x['quantidade']
        )

        lista_pedidos_separacao = sorted(
            pedidos_separacao.values(),
            key=lambda x: -x['quantidade']
        )

        produtos_resultado.append({
            'cod_produto': cod_produto,
            'nome_produto': nome_produto,
            'total_carteira': float(total_carteira),
            'em_separacao': float(total_separacao),
            'falta_separar': falta_separar,
            'pedidos_carteira': lista_pedidos_carteira,
            'pedidos_separacao': lista_pedidos_separacao,
            'total_pedidos_carteira': len(pedidos_carteira),
            'total_pedidos_separacao': len(pedidos_separacao)
        })

    resultado['produtos'] = produtos_resultado

    # Resumo
    if produtos_resultado:
        msg_linhas = [f"{args.produto.capitalize()} pendente de embarque:"]
        for p in produtos_resultado:
            msg_linhas.append(
                f"- {p['nome_produto']}: "
                f"Carteira={p['total_carteira']:.0f}, "
                f"Separacao={p['em_separacao']:.0f}, "
                f"Falta separar={p['falta_separar']:.0f}"
            )
        msg = '\n'.join(msg_linhas)
    else:
        msg = f"Produto {args.produto} nao encontrado"

    resultado['resumo'] = {
        'total_produtos': len(produtos_resultado),
        'mensagem': msg
    }

    return resultado


def consultar_produtos_sobra_estoque(args):
    """
    Query 18: Quanto vai sobrar de pessego no estoque?
    Calcula: estoque - carteira_total = sobra.
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from app.producao.models import CadastroPalletizacao
    from sqlalchemy import func

    resultado = {
        'sucesso': True,
        'tipo_analise': 'SOBRA_ESTOQUE',
        'termo_busca': args.produto,
        'produtos': [],
        'resumo': {}
    }

    # Resolver produto
    produto_info, info_busca = resolver_produto_unico(args.produto)

    if not produto_info and not info_busca.get('multiplos'):
        resultado['sucesso'] = False
        resultado['erro'] = f"Produto '{args.produto}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_produto(info_busca)
        return resultado

    # Obter lista de produtos
    if info_busca.get('multiplos') and not produto_info:
        produtos_buscar = [c['cod_produto'] for c in info_busca.get('candidatos', [])]
    elif produto_info:
        produtos_buscar = [produto_info['cod_produto']]
    else:
        resultado['sucesso'] = False
        resultado['erro'] = "Nao foi possivel identificar produtos"
        return resultado

    resultado['busca'] = {
        'encontrado': info_busca.get('encontrado', False),
        'multiplos': info_busca.get('multiplos', False)
    }

    produtos_resultado = []

    for cod_produto in produtos_buscar:
        # Buscar cadastro
        cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        nome_produto = cadastro.nome_produto if cadastro else cod_produto

        # Estoque atual
        estoque = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

        # Total em separacao (sincronizado_nf = False)
        em_separacao = Separacao.query.filter(
            Separacao.cod_produto == cod_produto,
            Separacao.sincronizado_nf == False
        ).with_entities(
            func.sum(Separacao.qtd_saldo)
        ).scalar() or 0

        # Carteira total (pendente)
        carteira_total = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).with_entities(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
        ).scalar() or 0

        # Carteira sem separacao = itens que ainda nao foram para separacao
        # Simplificacao: carteira_sem_separacao = carteira_total - em_separacao
        carteira_sem_separacao = max(0, float(carteira_total) - float(em_separacao))

        # Sobra = estoque - demanda_total
        # Demanda total = em_separacao + carteira_sem_separacao
        # Simplificando: sobra = estoque - carteira_total (ja que carteira inclui tudo pendente)
        sobra = float(estoque) - float(carteira_total)

        produtos_resultado.append({
            'cod_produto': cod_produto,
            'nome_produto': nome_produto,
            'estoque_atual': float(estoque),
            'em_separacao': float(em_separacao),
            'carteira_total': float(carteira_total),
            'carteira_sem_separacao': carteira_sem_separacao,
            'sobra': sobra
        })

    resultado['produtos'] = produtos_resultado

    # Resumo
    if produtos_resultado:
        msg_linhas = []
        for p in produtos_resultado:
            status = "SOBRA" if p['sobra'] >= 0 else "FALTA"
            msg_linhas.append(
                f"{p['nome_produto']}:\n"
                f"  Estoque: {p['estoque_atual']:.0f} | "
                f"Separacao: {p['em_separacao']:.0f} | "
                f"Carteira s/ sep: {p['carteira_sem_separacao']:.0f}\n"
                f"  {status}: {abs(p['sobra']):.0f} un"
            )
        msg = '\n'.join(msg_linhas)
    else:
        msg = f"Produto {args.produto} nao encontrado"

    resultado['resumo'] = {
        'total_produtos': len(produtos_resultado),
        'mensagem': msg
    }

    return resultado


def consultar_situacao_completa_produto(args):
    """
    NOVA QUERY: Situacao completa do produto.
    Retorna TUDO que o Agent SDK precisa para analise:

    1. Estoque atual
    2. Separacoes por data de expedicao (detalhado)
    3. Demanda total (Carteira pendente)
    4. Programacao de producao (proximos 14 dias)
    5. Projecao dia a dia (estoque projetado)
    6. Indicadores calculados (sobra, ruptura, etc)

    Uso:
        --produto palmito --completo
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from app.producao.models import CadastroPalletizacao, ProgramacaoProducao
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from collections import defaultdict

    resultado = {
        'sucesso': True,
        'tipo_analise': 'SITUACAO_COMPLETA_PRODUTO',
        'termo_busca': args.produto,
        'produtos': [],
        'resumo': {}
    }

    # Resolver produto
    produto_info, info_busca = resolver_produto_unico(args.produto)

    if not produto_info and not info_busca.get('multiplos'):
        resultado['sucesso'] = False
        resultado['erro'] = f"Produto '{args.produto}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_produto(info_busca)
        return resultado

    # Se multiplos candidatos, usar todos
    if info_busca.get('multiplos') and not produto_info:
        produtos_buscar = [c['cod_produto'] for c in info_busca.get('candidatos', [])]
    elif produto_info:
        produtos_buscar = [produto_info['cod_produto']]
    else:
        resultado['sucesso'] = False
        resultado['erro'] = "Nao foi possivel identificar produtos"
        return resultado

    resultado['busca'] = {
        'encontrado': info_busca.get('encontrado', False),
        'multiplos': info_busca.get('multiplos', False)
    }
    if info_busca.get('candidatos'):
        resultado['busca']['candidatos'] = info_busca['candidatos']

    hoje = date.today()
    produtos_resultado = []

    for cod_produto in produtos_buscar:
        # ========== 1. CADASTRO DO PRODUTO ==========
        cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        nome_produto = cadastro.nome_produto if cadastro else cod_produto

        info_produto = {
            'cod_produto': cod_produto,
            'nome_produto': nome_produto,
            'tipo_embalagem': cadastro.tipo_embalagem if cadastro else None,
            'tipo_materia_prima': cadastro.tipo_materia_prima if cadastro else None,
            'categoria': cadastro.categoria_produto if cadastro else None,
            'linha_producao': cadastro.linha_producao if cadastro else None,
            'palletizacao': float(cadastro.palletizacao or 1) if cadastro else 1,
            'peso_bruto': float(cadastro.peso_bruto or 0) if cadastro else 0
        }

        # ========== 2. ESTOQUE ATUAL ==========
        estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

        # ========== 3. SEPARACOES POR DATA DE EXPEDICAO ==========
        # Buscar todas as separacoes nao faturadas
        separacoes = Separacao.query.filter(
            Separacao.cod_produto == cod_produto,
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0
        ).order_by(Separacao.expedicao.asc()).all()

        # Agrupar por data de expedicao
        separacoes_por_data = defaultdict(lambda: {'qtd': 0, 'valor': 0, 'pedidos': []})
        total_separado = 0

        for sep in separacoes:
            data_exp = sep.expedicao.isoformat() if sep.expedicao else 'SEM_DATA'
            qtd = float(sep.qtd_saldo or 0)
            valor = float(sep.valor_saldo or 0)

            separacoes_por_data[data_exp]['qtd'] += qtd # type: ignore
            separacoes_por_data[data_exp]['valor'] += valor # type: ignore
            if sep.num_pedido not in separacoes_por_data[data_exp]['pedidos']:
                separacoes_por_data[data_exp]['pedidos'].append(sep.num_pedido) # type: ignore
            total_separado += qtd

        # Converter para lista ordenada
        separacoes_lista = []
        for data_exp, dados in sorted(separacoes_por_data.items()):
            separacoes_lista.append({
                'data_expedicao': data_exp,
                'quantidade': round(dados['qtd'], 2),
                'valor': round(dados['valor'], 2),
                'pedidos': dados['pedidos'],
                'qtd_pedidos': len(dados['pedidos'])
            })

        # ========== 4. DEMANDA DA CARTEIRA (NAO SEPARADO) ==========
        # Saldo pendente na carteira que AINDA NAO foi para separacao
        itens_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        # Calcular demanda real da carteira (carteira - ja separado por pedido)
        # IMPORTANTE: CarteiraPrincipal.qtd_saldo_produto_pedido nao diminui ao separar!
        demanda_carteira_bruta = sum(float(i.qtd_saldo_produto_pedido or 0) for i in itens_carteira)

        # Demanda liquida = carteira - separado (evitar contar 2x)
        demanda_carteira_liquida = max(0, demanda_carteira_bruta - total_separado)

        # DEMANDA TOTAL = separado (vai sair) + carteira liquida (ainda nao separado)
        demanda_total = total_separado + demanda_carteira_liquida

        # Pedidos na carteira (agrupado)
        pedidos_carteira = defaultdict(lambda: {'qtd': 0, 'valor': 0})
        for item in itens_carteira:
            pedidos_carteira[item.num_pedido]['qtd'] += float(item.qtd_saldo_produto_pedido or 0)
            pedidos_carteira[item.num_pedido]['valor'] += float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
            pedidos_carteira[item.num_pedido]['cliente'] = item.raz_social_red

        carteira_lista = [
            {
                'num_pedido': num,
                'cliente': dados.get('cliente'),
                'quantidade': round(dados['qtd'], 2),
                'valor': round(dados['valor'], 2)
            }
            for num, dados in sorted(pedidos_carteira.items(), key=lambda x: -x[1]['valor'])
        ]

        # ========== 5. PROGRAMACAO DE PRODUCAO (PROXIMOS 14 DIAS) ==========
        programacoes = ProgramacaoProducao.query.filter(
            ProgramacaoProducao.cod_produto == cod_produto,
            ProgramacaoProducao.data_programacao >= hoje,
            ProgramacaoProducao.data_programacao <= hoje + timedelta(days=14)
        ).order_by(ProgramacaoProducao.data_programacao.asc()).all()

        programacao_lista = []
        total_programado = 0
        for prog in programacoes:
            qtd = float(prog.qtd_programada or 0)
            programacao_lista.append({
                'data': prog.data_programacao.isoformat(),
                'quantidade': qtd,
                'linha': prog.linha_producao,
            })
            total_programado += qtd

        # ========== 6. PROJECAO DIA A DIA (14 DIAS) ==========
        projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias=14)
        projecao_diaria = projecao.get('projecao', [])
        dia_ruptura = projecao.get('dia_ruptura')
        menor_estoque_d7 = projecao.get('menor_estoque_d7', estoque_atual)

        # ========== 7. INDICADORES CALCULADOS ==========
        sobra = estoque_atual - demanda_total
        status_estoque = 'OK'
        if sobra < 0:
            status_estoque = 'RUPTURA_IMINENTE' if dia_ruptura else 'DEFICIT'
        elif dia_ruptura:
            status_estoque = 'RISCO_RUPTURA'
        elif sobra < demanda_total * 0.1:  # Menos de 10% de folga
            status_estoque = 'ATENCAO'

        produtos_resultado.append({
            'produto': info_produto,
            'estoque': {
                'atual': round(estoque_atual, 2),
                'menor_d7': round(menor_estoque_d7, 2),
                'status': status_estoque
            },
            'separacoes': {
                'total_quantidade': round(total_separado, 2),
                'por_data_expedicao': separacoes_lista,
                'total_pedidos': len(set(p for sep in separacoes_lista for p in sep['pedidos']))
            },
            'carteira': {
                'demanda_bruta': round(demanda_carteira_bruta, 2),
                'demanda_liquida': round(demanda_carteira_liquida, 2),
                'pedidos': carteira_lista[:20],  # Top 20 por valor
                'total_pedidos': len(carteira_lista)
            },
            'demanda_total': round(demanda_total, 2),
            'programacao_producao': {
                'total_programado': round(total_programado, 2),
                'proximas_entradas': programacao_lista
            },
            'projecao': {
                'dia_ruptura': dia_ruptura,
                'dias_ate_ruptura': (date.fromisoformat(dia_ruptura) - hoje).days if dia_ruptura else None,
                'diaria': projecao_diaria[:14]  # 14 dias
            },
            'indicadores': {
                'sobra_atual': round(sobra, 2),
                'cobertura_dias': round(estoque_atual / (demanda_total / 14), 1) if demanda_total > 0 else 999,
                'percentual_disponivel': round((estoque_atual / demanda_total * 100), 1) if demanda_total > 0 else 100
            }
        })

    resultado['produtos'] = produtos_resultado

    # Resumo
    if produtos_resultado:
        p = produtos_resultado[0]
        msg_linhas = [f"SITUACAO COMPLETA - {p['produto']['nome_produto']}:"]
        msg_linhas.append(f"  Estoque atual: {p['estoque']['atual']:,.0f} un ({p['estoque']['status']})")
        msg_linhas.append(f"  Em separacao: {p['separacoes']['total_quantidade']:,.0f} un ({p['separacoes']['total_pedidos']} pedidos)")
        msg_linhas.append(f"  Carteira pendente: {p['carteira']['demanda_liquida']:,.0f} un ({p['carteira']['total_pedidos']} pedidos)")
        msg_linhas.append(f"  DEMANDA TOTAL: {p['demanda_total']:,.0f} un")
        msg_linhas.append(f"  Producao programada: {p['programacao_producao']['total_programado']:,.0f} un (14 dias)")
        msg_linhas.append(f"  SOBRA/DEFICIT: {p['indicadores']['sobra_atual']:+,.0f} un")
        if p['projecao']['dia_ruptura']:
            msg_linhas.append(f"  ⚠️ RUPTURA PREVISTA: {p['projecao']['dia_ruptura']} ({p['projecao']['dias_ate_ruptura']} dias)")
        msg = '\n'.join(msg_linhas)
    else:
        msg = f"Produto {args.produto} nao encontrado"

    resultado['resumo'] = {
        'total_produtos': len(produtos_resultado),
        'mensagem': msg
    }

    return resultado


def scan_ruptura_global(args):
    """
    SCAN GLOBAL DE RUPTURA: Analisa APENAS produtos com separacoes ativas.
    Foca em produtos com DEMANDA REAL programada (separacoes nao faturadas).

    Retorna produtos em risco ordenados por severidade:
    - CRITICO: dias_ate_ruptura <= 2 OU deficit_imediato < 0
    - ALERTA: dias_ate_ruptura <= 5
    - ATENCAO: dias_ate_ruptura > 5

    Inclui impacto financeiro e operacional (pedidos afetados, valor).
    """
    from app.separacao.models import Separacao
    from app.producao.models import CadastroPalletizacao, ProgramacaoProducao
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from sqlalchemy import func

    resultado = {
        'sucesso': True,
        'tipo_analise': 'SCAN_RUPTURA_GLOBAL',
        'horizonte_dias': args.dias,
        'total_produtos_analisados': 0,
        'total_em_risco': 0,
        'produtos_risco': [],
        'resumo': {}
    }

    hoje = date.today()
    data_limite_producao = hoje + timedelta(days=14)

    # 1. Buscar produtos DISTINTOS com separacoes ativas
    produtos_com_separacao = Separacao.query.filter(
        Separacao.sincronizado_nf == False,
        Separacao.qtd_saldo > 0
    ).with_entities(
        Separacao.cod_produto.distinct()
    ).all()

    cod_produtos = [p[0] for p in produtos_com_separacao]
    resultado['total_produtos_analisados'] = len(cod_produtos)

    produtos_risco_lista = []

    # 2. Analisar cada produto
    for cod_produto in cod_produtos:
        # Buscar cadastro
        cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        nome_produto = cadastro.nome_produto if cadastro else cod_produto

        # Calcular estoque atual
        estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

        # Somar demanda (separacoes ativas)
        separacoes = Separacao.query.filter(
            Separacao.cod_produto == cod_produto,
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0
        ).all()

        demanda_separacoes = sum(float(s.qtd_saldo or 0) for s in separacoes)

        # Contar pedidos afetados e valor total
        pedidos_afetados = set()
        valor_impactado = 0
        for sep in separacoes:
            if sep.num_pedido:
                pedidos_afetados.add(sep.num_pedido)
            valor_impactado += float(sep.valor_saldo or 0)

        # Calcular deficit imediato
        deficit_imediato = estoque_atual - demanda_separacoes

        # Calcular projecao
        projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias=args.dias)
        dia_ruptura = projecao.get('dia_ruptura')
        dias_ate_ruptura = None

        if dia_ruptura:
            dias_ate_ruptura = (date.fromisoformat(dia_ruptura) - hoje).days

        # Buscar producao programada
        programacao = ProgramacaoProducao.query.filter(
            ProgramacaoProducao.cod_produto == cod_produto,
            ProgramacaoProducao.data_programacao >= hoje,
            ProgramacaoProducao.data_programacao <= data_limite_producao
        ).with_entities(
            func.sum(ProgramacaoProducao.qtd_programada)
        ).scalar() or 0

        # Filtrar: incluir apenas produtos em risco
        em_risco = (dia_ruptura is not None and dias_ate_ruptura <= args.dias) or deficit_imediato < 0

        if em_risco:
            # Classificar severidade
            if dias_ate_ruptura is not None and dias_ate_ruptura <= 2:
                severidade = 'CRITICO'
            elif deficit_imediato < 0:
                severidade = 'CRITICO'
            elif dias_ate_ruptura is not None and dias_ate_ruptura <= 5:
                severidade = 'ALERTA'
            else:
                severidade = 'ATENCAO'

            produtos_risco_lista.append({
                'cod_produto': cod_produto,
                'nome_produto': nome_produto,
                'estoque_atual': round(estoque_atual, 2),
                'demanda_separacoes': round(demanda_separacoes, 2),
                'deficit_imediato': round(deficit_imediato, 2),
                'dia_ruptura': dia_ruptura,
                'dias_ate_ruptura': dias_ate_ruptura,
                'pedidos_afetados': len(pedidos_afetados),
                'valor_impactado': round(valor_impactado, 2),
                'severidade': severidade,
                'producao_programada': round(float(programacao), 2)
            })

    # 3. Ordenar por severidade (dias ate ruptura ASC, valor impacto DESC)
    def chave_ordenacao(p):
        # Prioridade: 1) dias ate ruptura (None = 999), 2) valor DESC
        dias = p['dias_ate_ruptura'] if p['dias_ate_ruptura'] is not None else 999
        return (dias, -p['valor_impactado'])

    produtos_risco_lista.sort(key=chave_ordenacao)

    # 4. Limitar resultados
    resultado['produtos_risco'] = produtos_risco_lista[:args.limit]
    resultado['total_em_risco'] = len(produtos_risco_lista)

    # 5. Gerar resumo
    criticos = [p for p in produtos_risco_lista if p['severidade'] == 'CRITICO']
    alertas = [p for p in produtos_risco_lista if p['severidade'] == 'ALERTA']
    atencoes = [p for p in produtos_risco_lista if p['severidade'] == 'ATENCAO']

    total_critico = len(criticos)
    total_alerta = len(alertas)
    total_atencao = len(atencoes)

    data_limite_str = (hoje + timedelta(days=args.dias)).strftime('%d/%m')

    msg_linhas = [f"SCAN GLOBAL DE RUPTURA - Produtos com separacoes ativas (ate {data_limite_str}):"]
    msg_linhas.append(f"Produtos analisados: {resultado['total_produtos_analisados']}")
    msg_linhas.append(f"Produtos em risco: {resultado['total_em_risco']}")

    if total_critico > 0:
        msg_linhas.append(f"\n🚨 CRITICO: {total_critico} produto(s)")
        for p in criticos[:5]:
            msg_linhas.append(
                f"  - {p['nome_produto']}: "
                f"Estoque={p['estoque_atual']:.0f}, Demanda={p['demanda_separacoes']:.0f}, "
                f"Deficit={p['deficit_imediato']:+.0f} | "
                f"{p['pedidos_afetados']} pedidos, R$ {p['valor_impactado']:,.2f}"
            )

    if total_alerta > 0:
        msg_linhas.append(f"\n⚠️ ALERTA: {total_alerta} produto(s)")
        for p in alertas[:5]:
            msg_linhas.append(
                f"  - {p['nome_produto']}: "
                f"Ruptura em {p['dia_ruptura']} ({p['dias_ate_ruptura']} dias) | "
                f"{p['pedidos_afetados']} pedidos, R$ {p['valor_impactado']:,.2f}"
            )

    if total_atencao > 0:
        msg_linhas.append(f"\nℹ️ ATENCAO: {total_atencao} produto(s)")
        for p in atencoes[:5]:
            msg_linhas.append(
                f"  - {p['nome_produto']}: "
                f"Ruptura em {p['dia_ruptura']} ({p['dias_ate_ruptura']} dias) | "
                f"{p['pedidos_afetados']} pedidos"
            )

    if resultado['total_em_risco'] == 0:
        msg_linhas = [
            f"Scan concluido: {resultado['total_produtos_analisados']} produtos analisados",
            f"✅ Nenhum produto em risco de ruptura nos proximos {args.dias} dias"
        ]

    resultado['resumo'] = {
        'criticos': total_critico,
        'alerta': total_alerta,
        'atencao': total_atencao,
        'mensagem': '\n'.join(msg_linhas)
    }

    return resultado


def consultar_produtos_previsao_ruptura(args):
    """
    Query 20: O que vai dar falta essa semana?
    Lista produtos com ruptura prevista nos proximos N dias.
    """
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from app.producao.models import CadastroPalletizacao
    from app.estoque.models import MovimentacaoEstoque

    resultado = {
        'sucesso': True,
        'tipo_analise': 'PREVISAO_RUPTURA',
        'horizonte_dias': args.dias,
        'produtos_ruptura': {
            'critico': [],   # Proximos 2 dias
            'alerta': [],    # 3-5 dias
            'atencao': []    # 6+ dias
        },
        'resumo': {}
    }

    hoje = date.today()

    # Buscar todos os produtos ativos com movimentacao
    produtos_com_estoque = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.ativo == True
    ).with_entities(
        MovimentacaoEstoque.cod_produto.distinct()
    ).all()

    cod_produtos = [p[0] for p in produtos_com_estoque]

    produtos_ruptura = []

    # Calcular projecao para cada produto
    for cod_produto in cod_produtos:
        projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, args.dias)

        if projecao.get('dia_ruptura'):
            dia_ruptura = date.fromisoformat(projecao['dia_ruptura'])
            dias_ate_ruptura = (dia_ruptura - hoje).days

            if dias_ate_ruptura <= args.dias:
                # Buscar nome do produto
                cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
                nome_produto = cadastro.nome_produto if cadastro else cod_produto

                produtos_ruptura.append({
                    'cod_produto': cod_produto,
                    'nome_produto': nome_produto,
                    'estoque_atual': projecao.get('estoque_atual', 0),
                    'dia_ruptura': projecao['dia_ruptura'],
                    'dias_ate_ruptura': dias_ate_ruptura,
                    'menor_estoque_d7': projecao.get('menor_estoque_d7', 0),
                    'deficit': abs(projecao.get('menor_estoque_d7', 0)) if projecao.get('menor_estoque_d7', 0) < 0 else 0
                })

    # Ordenar por dias ate ruptura
    produtos_ruptura.sort(key=lambda x: x['dias_ate_ruptura'])

    # Classificar por urgencia
    for p in produtos_ruptura:
        if p['dias_ate_ruptura'] <= 2:
            resultado['produtos_ruptura']['critico'].append(p)
        elif p['dias_ate_ruptura'] <= 5:
            resultado['produtos_ruptura']['alerta'].append(p)
        else:
            resultado['produtos_ruptura']['atencao'].append(p)

    # Limitar resultados
    resultado['produtos_ruptura']['critico'] = resultado['produtos_ruptura']['critico'][:args.limit]
    resultado['produtos_ruptura']['alerta'] = resultado['produtos_ruptura']['alerta'][:args.limit]
    resultado['produtos_ruptura']['atencao'] = resultado['produtos_ruptura']['atencao'][:args.limit]

    # Resumo
    total_critico = len(resultado['produtos_ruptura']['critico'])
    total_alerta = len(resultado['produtos_ruptura']['alerta'])
    total_atencao = len(resultado['produtos_ruptura']['atencao'])
    total = total_critico + total_alerta + total_atencao

    data_limite = (hoje + timedelta(days=args.dias)).strftime('%d/%m')

    msg_linhas = [f"Previsao de ruptura (ate {data_limite}):"]

    if total_critico > 0:
        msg_linhas.append(f"\nCRITICO (proximos 2 dias): {total_critico} produto(s)")
        for p in resultado['produtos_ruptura']['critico'][:10]:
            msg_linhas.append(f"  - {p['nome_produto']}: Ruptura em {p['dia_ruptura']} - Faltam {p['deficit']:.0f} un")

    if total_alerta > 0:
        msg_linhas.append(f"\nALERTA (3-5 dias): {total_alerta} produto(s)")
        for p in resultado['produtos_ruptura']['alerta'][:10]:
            msg_linhas.append(f"  - {p['nome_produto']}: Ruptura em {p['dia_ruptura']} - Faltam {p['deficit']:.0f} un")

    if total_atencao > 0:
        msg_linhas.append(f"\nATENCAO (6+ dias): {total_atencao} produto(s)")
        for p in resultado['produtos_ruptura']['atencao'][:10]:
            msg_linhas.append(f"  - {p['nome_produto']}: Ruptura em {p['dia_ruptura']} - Faltam {p['deficit']:.0f} un")

    if total == 0:
        msg_linhas = [f"Nenhuma ruptura prevista nos proximos {args.dias} dias"]

    resultado['resumo'] = {
        'total_rupturas': total,
        'critico': total_critico,
        'alerta': total_alerta,
        'atencao': total_atencao,
        'mensagem': '\n'.join(msg_linhas)
    }

    return resultado


def main():
    from app import create_app

    parser = argparse.ArgumentParser(
        description='Consultar estoque, entradas, saidas, pendencias, projecoes e situacao completa de produtos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python consultando_produtos_estoque.py --produto palmito --completo        # SITUACAO COMPLETA (NOVO!)
  python consultando_produtos_estoque.py --produto palmito --entradas
  python consultando_produtos_estoque.py --produto palmito --saidas
  python consultando_produtos_estoque.py --produto pessego --pendente
  python consultando_produtos_estoque.py --produto pessego --sobra
  python consultando_produtos_estoque.py --ruptura --dias 7

A opcao --completo retorna:
  - Estoque atual
  - Separacoes por data de expedicao
  - Demanda total (carteira + separacoes)
  - Programacao de producao (14 dias)
  - Projecao dia a dia
  - Indicadores (sobra, cobertura, ruptura)
        """
    )

    # Argumentos
    parser.add_argument('--produto', help='Nome ou termo do produto')
    parser.add_argument('--completo', action='store_true', help='Situacao completa do produto (estoque, separacoes, demanda, producao, projecao)')
    parser.add_argument('--entradas', action='store_true', help='Mostrar entradas recentes (qtd > 0)')
    parser.add_argument('--saidas', action='store_true', help='Mostrar saidas recentes (qtd < 0)')
    parser.add_argument('--pendente', action='store_true', help='Mostrar pendente de embarque')
    parser.add_argument('--sobra', action='store_true', help='Calcular sobra de estoque')
    parser.add_argument('--scan-ruptura-global', action='store_true', dest='scan_ruptura_global',
                        help='Scan global: analisa APENAS produtos com separacoes ativas, retorna lista priorizada por risco')
    parser.add_argument('--ruptura', action='store_true', help='Previsao de rupturas (todos produtos com movimentacao)')
    parser.add_argument('--dias', type=int, default=7, help='Horizonte de projecao em dias (default: 7)')
    parser.add_argument('--limit', type=int, default=100, help='Limite de resultados (default: 100)')
    parser.add_argument('--limit-entradas', type=int, default=100, dest='limit_entradas',
                        help='Limite de movimentacoes por produto (default: 100)')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Determinar qual analise executar
        if args.produto and args.completo:
            resultado = consultar_situacao_completa_produto(args)
        elif args.produto and args.entradas:
            resultado = consultar_produtos_entradas(args)
        elif args.produto and args.saidas:
            resultado = consultar_produtos_saidas(args)
        elif args.produto and args.pendente:
            resultado = consultar_produtos_pendente_embarque(args)
        elif args.produto and args.sobra:
            resultado = consultar_produtos_sobra_estoque(args)
        elif args.scan_ruptura_global:
            resultado = scan_ruptura_global(args)
        elif args.ruptura:
            resultado = consultar_produtos_previsao_ruptura(args)
        else:
            resultado = {
                'sucesso': False,
                'erro': 'Informe ao menos um filtro: --produto com (--completo, --entradas, --saidas, --pendente ou --sobra), --scan-ruptura-global, ou --ruptura'
            }

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()
