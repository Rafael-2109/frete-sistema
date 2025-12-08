#!/usr/bin/env python3
"""
Script: consultando_programacao_producao.py
Queries cobertas: Q15

Simula reprogramacao de producao para resolver rupturas.

Uso:
    --produto "VF pouch 150"    # Q15: Opcoes de reprogramacao
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
        description='Simular opcoes de reprogramacao para resolver ruptura (Q15)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python consultando_programacao_producao.py --produto "VF pouch 150"
  python consultando_programacao_producao.py --produto "azeitona preta mezzani"
  python consultando_programacao_producao.py --cod-produto AZ001
        """
    )
    parser.add_argument('--produto', help='Nome ou termo do produto')
    parser.add_argument('--cod-produto', help='Codigo do produto')
    parser.add_argument('--linha', help='Linha de producao especifica')
    parser.add_argument('--limit', type=int, default=5, help='Limite de opcoes (default: 5)')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        resultado = consultar_programacao_producao(args)
        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()
