#!/usr/bin/env python3
"""
Script: consultando_produtos_estoque.py
Queries cobertas: Q13, Q17, Q18, Q20

Consulta estoque atual, entradas, pendencias e projecoes.

Uso:
    --produto palmito --entradas          # Q13: Chegou o produto?
    --produto pessego --pendente          # Q17: Falta embarcar muito?
    --produto pessego --sobra             # Q18: Quanto vai sobrar no estoque?
    --ruptura --dias 7                    # Q20: O que vai dar falta essa semana?
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
    resolver_produto,
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
    from sqlalchemy import func

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
    from sqlalchemy import func

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


def consultar_produtos_previsao_ruptura(args):
    """
    Query 20: O que vai dar falta essa semana?
    Lista produtos com ruptura prevista nos proximos N dias.
    """
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from app.producao.models import CadastroPalletizacao
    from app.estoque.models import MovimentacaoEstoque
    from sqlalchemy import func

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
        for p in resultado['produtos_ruptura']['critico'][:3]:
            msg_linhas.append(f"  - {p['nome_produto']}: Ruptura em {p['dia_ruptura']} - Faltam {p['deficit']:.0f} un")

    if total_alerta > 0:
        msg_linhas.append(f"\nALERTA (3-5 dias): {total_alerta} produto(s)")
        for p in resultado['produtos_ruptura']['alerta'][:3]:
            msg_linhas.append(f"  - {p['nome_produto']}: Ruptura em {p['dia_ruptura']} - Faltam {p['deficit']:.0f} un")

    if total_atencao > 0:
        msg_linhas.append(f"\nATENCAO (6+ dias): {total_atencao} produto(s)")
        for p in resultado['produtos_ruptura']['atencao'][:3]:
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
        description='Consultar estoque, entradas, saidas, pendencias e projecoes (Q13, Q17, Q18, Q20)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python consultando_produtos_estoque.py --produto palmito --entradas
  python consultando_produtos_estoque.py --produto palmito --saidas
  python consultando_produtos_estoque.py --produto pessego --pendente
  python consultando_produtos_estoque.py --produto pessego --sobra
  python consultando_produtos_estoque.py --ruptura --dias 7
        """
    )

    # Argumentos
    parser.add_argument('--produto', help='Nome ou termo do produto')
    parser.add_argument('--entradas', action='store_true', help='Mostrar entradas recentes (qtd > 0)')
    parser.add_argument('--saidas', action='store_true', help='Mostrar saidas recentes (qtd < 0)')
    parser.add_argument('--pendente', action='store_true', help='Mostrar pendente de embarque')
    parser.add_argument('--sobra', action='store_true', help='Calcular sobra de estoque')
    parser.add_argument('--ruptura', action='store_true', help='Previsao de rupturas')
    parser.add_argument('--dias', type=int, default=7, help='Horizonte de projecao em dias (default: 7)')
    parser.add_argument('--limit', type=int, default=100, help='Limite de resultados (default: 100)')
    parser.add_argument('--limit-entradas', type=int, default=100, dest='limit_entradas',
                        help='Limite de movimentacoes por produto (default: 100)')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Determinar qual analise executar
        if args.produto and args.entradas:
            resultado = consultar_produtos_entradas(args)
        elif args.produto and args.saidas:
            resultado = consultar_produtos_saidas(args)
        elif args.produto and args.pendente:
            resultado = consultar_produtos_pendente_embarque(args)
        elif args.produto and args.sobra:
            resultado = consultar_produtos_sobra_estoque(args)
        elif args.ruptura:
            resultado = consultar_produtos_previsao_ruptura(args)
        else:
            resultado = {
                'sucesso': False,
                'erro': 'Informe ao menos um filtro: --produto com (--entradas, --saidas, --pendente ou --sobra), ou --ruptura'
            }

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()
