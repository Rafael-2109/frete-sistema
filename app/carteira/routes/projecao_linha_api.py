"""
API de Projecao de Estoque por Linha de Producao (D0-D14)
Retorna saida, producao e saldo dia-a-dia para todos os produtos
da mesma linha_producao do produto clicado.
"""

from datetime import date, timedelta
from flask import jsonify
from flask_login import login_required
import logging

from app.estoque.models import UnificacaoCodigos
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.producao.models import CadastroPalletizacao

from . import carteira_bp

logger = logging.getLogger(__name__)

DIAS_PROJECAO = 14


@carteira_bp.route('/api/produto/<cod_produto>/projecao-linha', methods=['GET'])
@login_required
def obter_projecao_linha(cod_produto):
    """
    Retorna projecao D0-D14 (saida, producao, saldo) para todos os produtos
    da mesma linha_producao do produto informado.
    Considera UnificacaoCodigos para de-duplicar e calcular estoque corretamente.
    """
    try:
        # 1. Resolver codigos unificados do produto clicado
        codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)

        # 2. Buscar linha_producao a partir de qualquer codigo relacionado
        cadastro = CadastroPalletizacao.query.filter(
            CadastroPalletizacao.cod_produto.in_([str(c) for c in codigos_relacionados]),
            CadastroPalletizacao.ativo == True
        ).first()

        if not cadastro:
            return jsonify({
                'success': False,
                'error': f'Produto {cod_produto} nao encontrado no cadastro'
            }), 404

        linha_producao = cadastro.linha_producao
        if not linha_producao:
            return jsonify({
                'success': False,
                'error': f'Produto {cod_produto} ({cadastro.nome_produto}) nao possui linha de producao cadastrada'
            })

        # 3. Buscar TODOS os produtos da mesma linha_producao
        produtos_linha = CadastroPalletizacao.query.filter(
            CadastroPalletizacao.linha_producao == linha_producao,
            CadastroPalletizacao.ativo == True
        ).order_by(CadastroPalletizacao.nome_produto).all()

        if not produtos_linha:
            return jsonify({
                'success': False,
                'error': f'Nenhum produto encontrado na linha {linha_producao}'
            })

        # 4. De-duplicar produtos unificados (manter apenas codigo canonico)
        codigos_todos = [p.cod_produto for p in produtos_linha]
        canonicos = {}  # {codigo_canonico: CadastroPalletizacao}

        for produto in produtos_linha:
            cod_canonico = str(UnificacaoCodigos.get_codigo_unificado(produto.cod_produto))
            if cod_canonico not in canonicos:
                canonicos[cod_canonico] = produto

        codigos_unicos = list(canonicos.keys())

        # 5. Calcular projecao D0-D14 para todos os produtos em paralelo
        projecoes = ServicoEstoqueSimples.calcular_multiplos_produtos(
            codigos_unicos,
            dias=DIAS_PROJECAO,
            entrada_em_d_plus_1=False  # Modal analitico: producao entra em D0 (fato real)
        )

        # 6. Montar datas D0-D14
        hoje = date.today()
        datas = [(hoje + timedelta(days=d)).isoformat() for d in range(DIAS_PROJECAO + 1)]

        # 7. Montar resposta por produto
        produtos_resposta = []
        for cod in codigos_unicos:
            cadastro_prod = canonicos[cod]
            proj = projecoes.get(cod, {})
            projecao_dias = proj.get('projecao', [])

            saida = []
            producao = []
            saldo = []

            for i in range(DIAS_PROJECAO + 1):
                if i < len(projecao_dias):
                    dia = projecao_dias[i]
                    saida.append(round(dia.get('saida', 0)))
                    producao.append(round(dia.get('entrada', 0)))
                    saldo.append(round(dia.get('saldo_final', 0)))
                else:
                    saida.append(0)
                    producao.append(0)
                    saldo.append(0)

            produtos_resposta.append({
                'cod_produto': cadastro_prod.cod_produto,
                'nome_produto': cadastro_prod.nome_produto,
                'estoque_atual': round(proj.get('estoque_atual', 0)),
                'saida': saida,
                'producao': producao,
                'saldo': saldo
            })

        logger.info(
            f'Projecao linha {linha_producao}: {len(produtos_resposta)} produtos '
            f'({len(codigos_todos)} brutos, {len(codigos_unicos)} apos unificacao)'
        )

        return jsonify({
            'success': True,
            'linha_producao': linha_producao,
            'cod_produto_clicado': cod_produto,
            'datas': datas,
            'produtos': produtos_resposta
        })

    except Exception as e:
        logger.error(f'Erro ao calcular projecao por linha para {cod_produto}: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
