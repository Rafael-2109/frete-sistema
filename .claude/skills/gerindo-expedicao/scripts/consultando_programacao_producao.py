#!/usr/bin/env python3
"""
Script: consultando_programacao_producao.py
Queries cobertas: Q15 + LISTAGEM COMPLETA

Consulta programacao de producao e simula reprogramacao para resolver rupturas.

Uso:
    --listar                    # ⭐ TODA A PROGRAMACAO (proximos 14 dias)
    --listar --dias 7           # Programacao proximos 7 dias
    --listar --linha "Linha A"  # Programacao de uma linha especifica
    --listar --por-dia          # Agrupa por dia
    --listar --por-linha        # Agrupa por linha
    --produto "VF pouch 150"    # Q15: Opcoes de reprogramacao para ruptura
    --produto "azeitona preta"  # Busca por termos
    --cod-produto AZ001         # Busca por codigo direto
"""
import sys
import os
import json
import argparse
from datetime import date, datetime, timedelta
from decimal import Decimal

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


def listar_programacao_completa(args):
    """
    NOVA QUERY: Lista TODA a programacao de producao.

    Retorna:
    - Programacao completa dos proximos N dias
    - Pode agrupar por dia ou por linha
    - Inclui totais e resumo

    Uso:
        --listar                    # Toda programacao (14 dias)
        --listar --dias 7           # Proximos 7 dias
        --listar --linha "Linha A"  # Apenas uma linha
        --listar --por-dia          # Agrupa por dia
        --listar --por-linha        # Agrupa por linha
    """
    from app.producao.models import CadastroPalletizacao, ProgramacaoProducao
    from collections import defaultdict

    resultado = {
        'sucesso': True,
        'tipo_analise': 'PROGRAMACAO_COMPLETA',
        'filtros': {},
        'programacao': [],
        'por_dia': {},
        'por_linha': {},
        'resumo': {}
    }

    hoje = date.today()
    dias = args.dias if hasattr(args, 'dias') and args.dias else 14
    data_fim = hoje + timedelta(days=dias)

    resultado['filtros'] = {
        'data_inicio': hoje.isoformat(),
        'data_fim': data_fim.isoformat(),
        'dias': dias
    }

    # Construir query
    query = ProgramacaoProducao.query.filter(
        ProgramacaoProducao.data_programacao >= hoje,
        ProgramacaoProducao.data_programacao <= data_fim
    )

    # Filtro por linha
    if hasattr(args, 'linha') and args.linha:
        query = query.filter(ProgramacaoProducao.linha_producao.ilike(f'%{args.linha}%'))
        resultado['filtros']['linha'] = args.linha

    programacoes = query.order_by(
        ProgramacaoProducao.data_programacao.asc(),
        ProgramacaoProducao.linha_producao.asc()
    ).all()

    if not programacoes:
        resultado['resumo'] = {
            'total_programacoes': 0,
            'mensagem': f"Nenhuma programacao encontrada para os proximos {dias} dias"
        }
        return resultado

    # Caches para nome de produto
    nomes_produtos = {}

    # Processar programacoes
    programacao_lista = []
    por_dia = defaultdict(lambda: {'itens': [], 'total_qtd': 0, 'total_linhas': set()})
    por_linha = defaultdict(lambda: {'itens': [], 'total_qtd': 0, 'total_dias': set()})

    for prog in programacoes:
        # Buscar nome do produto (com cache)
        if prog.cod_produto not in nomes_produtos:
            cadastro = CadastroPalletizacao.query.filter_by(cod_produto=prog.cod_produto).first()
            nomes_produtos[prog.cod_produto] = cadastro.nome_produto if cadastro else prog.cod_produto

        item = {
            'data': prog.data_programacao.isoformat(),
            'linha': prog.linha_producao,
            'cod_produto': prog.cod_produto,
            'nome_produto': nomes_produtos[prog.cod_produto],
            'quantidade': float(prog.qtd_programada or 0)
        }
        programacao_lista.append(item)

        # Agrupar por dia
        data_str = prog.data_programacao.isoformat()
        por_dia[data_str]['itens'].append(item)
        por_dia[data_str]['total_qtd'] += float(prog.qtd_programada or 0) #type: ignore
        por_dia[data_str]['total_linhas'].add(prog.linha_producao)

        # Agrupar por linha
        linha = prog.linha_producao or 'SEM_LINHA'
        por_linha[linha]['itens'].append(item)
        por_linha[linha]['total_qtd'] += float(prog.qtd_programada or 0) #type: ignore
        por_linha[linha]['total_dias'].add(data_str)

    resultado['programacao'] = programacao_lista

    # Converter sets para contagem
    resultado['por_dia'] = {
        data: {
            'quantidade_total': round(dados['total_qtd'], 2),
            'linhas_ativas': len(dados['total_linhas']),
            'produtos': len(dados['itens']),
            'itens': dados['itens'] if (hasattr(args, 'por_dia') and args.por_dia) else []
        }
        for data, dados in sorted(por_dia.items())
    }

    resultado['por_linha'] = {
        linha: {
            'quantidade_total': round(dados['total_qtd'], 2),
            'dias_programados': len(dados['total_dias']),
            'produtos': len(dados['itens']),
            'itens': dados['itens'] if (hasattr(args, 'por_linha') and args.por_linha) else []
        }
        for linha, dados in sorted(por_linha.items())
    }

    # Resumo
    total_qtd = sum(float(p.qtd_programada or 0) for p in programacoes)
    linhas_unicas = set(p.linha_producao for p in programacoes if p.linha_producao)
    produtos_unicos = set(p.cod_produto for p in programacoes)

    # Construir mensagem de resumo
    msg_linhas = [f"PROGRAMACAO DE PRODUCAO ({hoje.strftime('%d/%m')} a {data_fim.strftime('%d/%m')})"]
    msg_linhas.append(f"  Total: {len(programacoes)} programacoes, {total_qtd:,.0f} unidades")
    msg_linhas.append(f"  Linhas: {len(linhas_unicas)} ativas")
    msg_linhas.append(f"  Produtos: {len(produtos_unicos)} diferentes")

    # Top 5 datas com mais producao
    top_dias = sorted(por_dia.items(), key=lambda x: -x[1]['total_qtd'])[:5] #type: ignore
    if top_dias:
        msg_linhas.append("  Top producao:")
        for data, dados in top_dias:
            msg_linhas.append(f"    - {data}: {dados['total_qtd']:,.0f} un ({dados['total_linhas']} linhas)")

    resultado['resumo'] = {
        'total_programacoes': len(programacoes),
        'quantidade_total': round(total_qtd, 2),
        'linhas_ativas': list(linhas_unicas),
        'produtos_unicos': len(produtos_unicos),
        'mensagem': '\n'.join(msg_linhas)
    }

    return resultado


def consultar_programacao_producao(args):
    """
    Query 15: O que da pra alterar na programacao pra matar a ruptura do produto X?
    """
    from app.producao.models import CadastroPalletizacao, ProgramacaoProducao
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from app import db

    resultado = {
        'sucesso': True,
        'produto': None,
        'situacao_atual': None,
        'opcoes_reprogramacao': [],
        'resumo': {}
    }

    # 1. Identificar produto usando modulo centralizado
    cod_produto = args.cod_produto

    if not cod_produto and args.produto:
        # Usar resolver_produto_unico para busca flexivel
        produto_info, info_busca = resolver_produto_unico(args.produto)

        if produto_info:
            cod_produto = produto_info['cod_produto']
            resultado['busca'] = {
                'estrategia': 'PRODUTO_UNICO' if info_busca['encontrado'] else 'MULTIPLOS',
                'termo_buscado': args.produto,
                'multiplos_candidatos': info_busca.get('multiplos', False)
            }
            if info_busca.get('candidatos'):
                resultado['busca']['outros_candidatos'] = info_busca['candidatos']
        else:
            resultado['sucesso'] = False
            resultado['erro'] = f"Produto '{args.produto}' nao encontrado"
            resultado['sugestao'] = formatar_sugestao_produto(info_busca)
            return resultado

    if not cod_produto:
        resultado['sucesso'] = False
        resultado['erro'] = "Informe --produto ou --cod-produto"
        return resultado

    # Buscar info do produto no cadastro
    cadastro = CadastroPalletizacao.query.filter_by(
        cod_produto=cod_produto,
        ativo=True
    ).first()

    if not cadastro:
        resultado['sucesso'] = False
        resultado['erro'] = f"Produto {cod_produto} nao encontrado no cadastro"
        return resultado

    resultado['produto'] = {
        'cod_produto': cod_produto,
        'nome_produto': cadastro.nome_produto,
        'categoria': cadastro.categoria_produto,
        'subcategoria': cadastro.subcategoria,
        'tipo_embalagem': cadastro.tipo_embalagem,
        'tipo_materia_prima': cadastro.tipo_materia_prima,
        'linha_producao': cadastro.linha_producao
    }

    # 2. Calcular situacao atual
    projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, 14)
    estoque_atual = projecao.get('estoque_atual', 0)
    dia_ruptura = projecao.get('dia_ruptura')
    menor_estoque = projecao.get('menor_estoque_d7', 0)

    resultado['situacao_atual'] = {
        'estoque_atual': estoque_atual,
        'dia_ruptura': dia_ruptura,
        'menor_estoque_d7': menor_estoque,
        'status': 'EM_RUPTURA' if menor_estoque < 0 else ('RISCO' if dia_ruptura else 'OK')
    }

    if not dia_ruptura and menor_estoque >= 0:
        resultado['resumo'] = {
            'mensagem': f"Produto {cadastro.nome_produto} nao tem ruptura prevista nos proximos 14 dias"
        }
        return resultado

    # 3. Buscar programacao da linha
    linha_producao = cadastro.linha_producao

    # Buscar programacoes futuras da mesma linha
    hoje = date.today()
    programacoes = ProgramacaoProducao.query.filter(
        ProgramacaoProducao.linha_producao == linha_producao,
        ProgramacaoProducao.data_programacao >= hoje,
        ProgramacaoProducao.data_programacao <= hoje + timedelta(days=14)
    ).order_by(
        ProgramacaoProducao.data_programacao.asc()
    ).all()

    # Verificar se o produto ja esta programado
    prog_produto = [p for p in programacoes if p.cod_produto == cod_produto]

    # Programacoes de outros produtos (candidatos a troca)
    prog_outros = [p for p in programacoes if p.cod_produto != cod_produto]

    # 4. Gerar opcoes de reprogramacao
    opcoes = []

    # Opcao 1: Antecipar producao existente
    if prog_produto:
        for prog in prog_produto:
            if prog.data_programacao > hoje:
                opcoes.append({
                    'tipo': 'ANTECIPAR',
                    'descricao': f"Antecipar producao de {prog.data_programacao.isoformat()} para antes",
                    'data_atual': prog.data_programacao.isoformat(),
                    'qtd_programada': float(prog.qtd_programada or 0),
                    'impacto': 'Pode resolver ruptura mais cedo'
                })

    # Opcao 2: Trocar com outro produto
    for prog_outro in prog_outros:
        # Verificar se o outro produto tem folga
        projecao_outro = ServicoEstoqueSimples.calcular_projecao(prog_outro.cod_produto, 14)
        menor_outro = projecao_outro.get('menor_estoque_d7', 0)

        cadastro_outro = CadastroPalletizacao.query.filter_by(cod_produto=prog_outro.cod_produto).first()
        nome_outro = cadastro_outro.nome_produto if cadastro_outro else prog_outro.cod_produto

        if menor_outro > 0:  # Tem folga
            opcoes.append({
                'tipo': 'TROCAR',
                'descricao': f"Trocar {cadastro.nome_produto} com {nome_outro}",
                'data_slot': prog_outro.data_programacao.isoformat(),
                'produto_substituido': {
                    'cod_produto': prog_outro.cod_produto,
                    'nome_produto': nome_outro,
                    'menor_estoque': menor_outro
                },
                'impacto': f"{nome_outro} seria adiado mas tem folga de {menor_outro:.0f} unidades"
            })

    # Opcao 3: Adicionar producao extra
    if linha_producao:
        opcoes.append({
            'tipo': 'ADICIONAR_PRODUCAO',
            'descricao': f"Adicionar producao extra na linha {linha_producao}",
            'qtd_sugerida': abs(menor_estoque) if menor_estoque < 0 else 1000,
            'impacto': 'Requer verificacao de capacidade'
        })

    resultado['opcoes_reprogramacao'] = opcoes[:args.limit]

    # Resumo
    resultado['resumo'] = {
        'dia_ruptura': dia_ruptura,
        'total_opcoes': len(opcoes),
        'mensagem': f"Ruptura de {cadastro.nome_produto} prevista para {dia_ruptura}. {len(opcoes)} opcao(oes) de reprogramacao sugerida(s)."
    }

    return resultado


def main():
    from app import create_app

    parser = argparse.ArgumentParser(
        description='Consultar programacao de producao e simular reprogramacao (Q15 + Listagem)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # ⭐ LISTAGEM COMPLETA (NOVO!)
  python consultando_programacao_producao.py --listar                    # Toda programacao (14 dias)
  python consultando_programacao_producao.py --listar --dias 7           # Proximos 7 dias
  python consultando_programacao_producao.py --listar --linha "Linha A"  # Apenas uma linha
  python consultando_programacao_producao.py --listar --por-dia          # Detalhes por dia
  python consultando_programacao_producao.py --listar --por-linha        # Detalhes por linha

  # REPROGRAMACAO (Q15)
  python consultando_programacao_producao.py --produto "VF pouch 150"
  python consultando_programacao_producao.py --produto "azeitona preta mezzani"
  python consultando_programacao_producao.py --cod-produto AZ001
        """
    )
    # Nova opcao de listagem
    parser.add_argument('--listar', action='store_true', help='Listar toda a programacao de producao')
    parser.add_argument('--dias', type=int, default=14, help='Horizonte em dias (default: 14)')
    parser.add_argument('--por-dia', action='store_true', dest='por_dia', help='Mostrar detalhes agrupados por dia')
    parser.add_argument('--por-linha', action='store_true', dest='por_linha', help='Mostrar detalhes agrupados por linha')

    # Opcoes de reprogramacao
    parser.add_argument('--produto', help='Nome ou termo do produto (para reprogramacao)')
    parser.add_argument('--cod-produto', dest='cod_produto', help='Codigo do produto')
    parser.add_argument('--linha', help='Linha de producao especifica')
    parser.add_argument('--limit', type=int, default=5, help='Limite de opcoes (default: 5)')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Determinar qual funcao usar
        if args.listar:
            resultado = listar_programacao_completa(args)
        elif args.produto or args.cod_produto:
            resultado = consultar_programacao_producao(args)
        else:
            resultado = {
                'sucesso': False,
                'erro': 'Informe --listar para ver toda a programacao ou --produto para opcoes de reprogramacao'
            }

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()
