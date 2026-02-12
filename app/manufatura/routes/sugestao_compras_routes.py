"""
Routes para Sugestao de Compras (MRP Simplificado)
"""
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required

sugestao_compras_bp = Blueprint(
    'sugestao_compras',
    __name__,
    url_prefix='/manufatura/sugestao-compras'
)


@sugestao_compras_bp.route('/')
@login_required
def index():
    """Tela principal de sugestao de compras"""
    return render_template('manufatura/sugestao_compras/index.html')


@sugestao_compras_bp.route('/api/calcular')
@login_required
def api_calcular():
    """
    API: Calcula sugestoes de compra para todos os componentes
    """
    try:
        from app.manufatura.services.sugestao_compras_service import ServicoSugestaoCompras

        service = ServicoSugestaoCompras()
        resultado = service.calcular_sugestoes(dias_horizonte=60)

        return jsonify(resultado)

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@sugestao_compras_bp.route('/api/em-transito')
@login_required
def api_em_transito():
    """
    API: Detalha POs e Requisicoes em transito para um produto.
    """
    cod_produto = request.args.get('cod_produto', '').strip()
    if not cod_produto:
        return jsonify({'sucesso': False, 'erro': 'cod_produto obrigatorio'}), 400

    try:
        from app.manufatura.services.sugestao_compras_service import ServicoSugestaoCompras

        service = ServicoSugestaoCompras()
        resultado = service.buscar_em_transito(cod_produto)
        return jsonify(resultado)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@sugestao_compras_bp.route('/api/cardex')
@login_required
def api_cardex():
    """
    API: Projecao dia-a-dia do cardex (estoque projetado).
    """
    cod_produto = request.args.get('cod_produto', '').strip()
    if not cod_produto:
        return jsonify({'sucesso': False, 'erro': 'cod_produto obrigatorio'}), 400

    dia_inicio = request.args.get('inicio', 0, type=int)
    dia_fim = request.args.get('fim', 30, type=int)

    try:
        from app.manufatura.services.sugestao_compras_service import ServicoSugestaoCompras

        service = ServicoSugestaoCompras()
        resultado = service.projetar_cardex(cod_produto, dia_inicio, dia_fim)
        return jsonify(resultado)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@sugestao_compras_bp.route('/api/sugestao-inteligente')
@login_required
def api_sugestao_inteligente():
    """
    API: Projecao dia-a-dia com sugestoes automaticas de compra.
    """
    cod_produto = request.args.get('cod_produto', '').strip()
    if not cod_produto:
        return jsonify({'sucesso': False, 'erro': 'cod_produto obrigatorio'}), 400

    dia_inicio = request.args.get('inicio', 0, type=int)
    dia_fim = request.args.get('fim', 30, type=int)

    try:
        from app.manufatura.services.sugestao_compras_service import ServicoSugestaoCompras

        service = ServicoSugestaoCompras()
        resultado = service.sugestao_inteligente(cod_produto, dia_inicio, dia_fim)
        return jsonify(resultado)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
