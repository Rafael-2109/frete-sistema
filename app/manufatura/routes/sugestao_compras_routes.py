"""
Routes para Sugestao de Compras (MRP Simplificado)
"""
from flask import Blueprint, render_template, jsonify
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
