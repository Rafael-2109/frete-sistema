"""Aba Resumo: visao por modelo x status com modais de detalhamento."""

from flask import render_template, jsonify, abort, request
from flask_login import login_required
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services.resumo_service import (
    resumo_por_modelo,
    detalhe_estoque,
    detalhe_pendente,
    detalhe_montada,
    detalhe_disponivel,
    detalhe_separada,
    detalhe_carregada,
    detalhe_faturada,
    detalhe_em_pedido,
)
from app.motos_assai.services.rastreamento_chassi_service import rastrear_chassi


STATUS_HANDLERS = {
    'estoque': detalhe_estoque,
    'pendente': detalhe_pendente,
    'montada': detalhe_montada,
    'disponivel': detalhe_disponivel,
    'separada': detalhe_separada,
    'carregada': detalhe_carregada,
    'faturada': detalhe_faturada,
    'em_pedido': detalhe_em_pedido,
}


@motos_assai_bp.route('/resumo')
@login_required
@require_motos_assai
def resumo_lista():
    """Tabela por modelo com badges-botao para abrir modal de cada status."""
    linhas = resumo_por_modelo()
    return render_template(
        'motos_assai/resumo/lista.html',
        linhas=linhas,
    )


@motos_assai_bp.route('/resumo/<int:modelo_id>/<string:status>')
@login_required
@require_motos_assai
def resumo_detalhe(modelo_id, status):
    """JSON com chassis do modelo no status. Consumido por modal via fetch."""
    status_norm = (status or '').strip().lower()
    handler = STATUS_HANDLERS.get(status_norm)
    if not handler:
        abort(404)
    itens = handler(modelo_id)
    return jsonify({'ok': True, 'status': status_norm, 'modelo_id': modelo_id, 'itens': itens})


@motos_assai_bp.route('/resumo/rastrear-chassi')
@login_required
@require_motos_assai
def resumo_rastrear_chassi():
    """Visao 360 de um chassi: recibo, montagem, pendencia, separacao,
    carregamento, NFe, CCe e divergencia. Consumido pelo modal via fetch."""
    chassi = (request.args.get('chassi') or '').strip()
    if not chassi:
        return jsonify({
            'ok': False,
            'encontrado': False,
            'erro': 'Informe um chassi para pesquisar.',
        }), 400
    resultado = rastrear_chassi(chassi)
    return jsonify(resultado)
