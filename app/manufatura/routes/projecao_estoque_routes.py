"""
Routes para Projeção de Estoque
"""
from flask import Blueprint, render_template, jsonify, request

from app.manufatura.services.projecao_estoque_service import ServicoProjecaoEstoque

projecao_estoque_bp = Blueprint(
    'projecao_estoque',
    __name__,
    url_prefix='/manufatura/projecao-estoque'
)


@projecao_estoque_bp.route('/')
def index():
    """Tela principal de projeção de estoque (consolidada)"""
    return render_template('manufatura/projecao_estoque/consolidado.html')


@projecao_estoque_bp.route('/api/projetar')
def api_projetar():
    """
    API: Projeção de estoque de componentes (60 dias)

    Query params:
        - cod_produto: Código do produto (opcional, se não informado projeta todos)
        - dias: Dias no futuro (padrão: 60)
    """
    cod_produto = request.args.get('cod_produto')
    dias = request.args.get('dias', 60, type=int)

    service = ServicoProjecaoEstoque()

    try:
        if cod_produto:
            # ✅ Validar se produto é comprado (componente)
            from app.producao.models import CadastroPalletizacao

            produto = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto,
                ativo=True
            ).first()

            if not produto:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Produto não encontrado ou inativo'
                }), 404

            if not produto.produto_comprado:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Produto não é componente comprado. Use a projeção de produção para produtos fabricados.'
                }), 400

            # Projetar apenas 1 produto
            projecao = service.projetar_produto(cod_produto, dias=dias)

            if not projecao:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Produto não encontrado ou sem movimentação'
                }), 404

            return jsonify({
                'sucesso': True,
                'projecao': projecao
            })
        else:
            # Projetar todos os componentes
            projecao = service.projetar_componentes_60_dias()
            return jsonify({
                'sucesso': True,
                **projecao
            })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@projecao_estoque_bp.route('/api/produtos-comprados')
def api_produtos_comprados():
    """
    API: Lista todos os produtos comprados (componentes)
    """
    from app.producao.models import CadastroPalletizacao

    produtos = CadastroPalletizacao.query.filter_by(
        produto_comprado=True,
        ativo=True
    ).order_by(CadastroPalletizacao.cod_produto).all()

    return jsonify({
        'sucesso': True,
        'total': len(produtos),
        'produtos': [
            {
                'cod_produto': p.cod_produto,
                'nome_produto': p.nome_produto,
                'tipo_materia_prima': p.tipo_materia_prima,
                'categoria_produto': p.categoria_produto
            }
            for p in produtos
        ]
    })


@projecao_estoque_bp.route('/api/projetar-consolidado')
def api_projetar_consolidado():
    """
    API: Retorna projeção consolidada de TODOS os componentes

    Estrutura otimizada para exibição em tabela:
    - Colunas fixas: Estoque, Consumo Carteira, Saldo, Qtd Req, Qtd Ped
    - Timeline D0-D60: array de 61 posições
    """
    try:
        service = ServicoProjecaoEstoque()
        resultado = service.projetar_componentes_consolidado()

        return jsonify(resultado)

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500
