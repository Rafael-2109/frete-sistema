from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    get_ou_criar_separacao, saldo_pendente_por_modelo,
    registrar_chassi, desfazer_chassi, finalizar_separacao, cancelar_separacao,
    SeparacaoConflictError, SeparacaoValidationError,
)
from app.motos_assai.models import (
    AssaiSeparacao, AssaiSeparacaoItem, AssaiPedidoVenda, AssaiLoja,
)


@motos_assai_bp.route('/separacao')
@login_required
@require_motos_assai
def separacao_lista():
    seps = (
        AssaiSeparacao.query
        .order_by(AssaiSeparacao.iniciada_em.desc())
        .limit(250).all()
    )
    return render_template('motos_assai/separacao/lista.html', separacoes=seps)


@motos_assai_bp.route('/pedidos/<int:pedido_id>/separar/<int:loja_id>')
@login_required
@require_motos_assai
def separacao_tela(pedido_id, loja_id):
    pedido = AssaiPedidoVenda.query.get_or_404(pedido_id)
    loja = AssaiLoja.query.get_or_404(loja_id)
    sep = get_ou_criar_separacao(pedido_id, loja_id, current_user.id)
    saldos = saldo_pendente_por_modelo(pedido_id, loja_id)
    items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id).all()
    return render_template(
        'motos_assai/separacao/tela.html',
        pedido=pedido, loja=loja, separacao=sep,
        saldos=saldos, items=items,
    )


@motos_assai_bp.route('/separacao/registrar-chassi', methods=['POST'])
@login_required
@require_motos_assai
def separacao_registrar_chassi():
    data = request.get_json(silent=True) or {}
    try:
        result = registrar_chassi(
            pedido_id=int(data['pedido_id']),
            loja_id=int(data['loja_id']),
            chassi=data['chassi'],
            registrada_por_id=current_user.id,
        )
    except SeparacaoConflictError as e:
        return jsonify({'ok': False, 'erro': str(e), 'retry': True}), 409
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

    saldos = saldo_pendente_por_modelo(int(data['pedido_id']), int(data['loja_id']))
    return jsonify({'ok': True, **result, 'saldos': [
        {**s, 'valor_unitario': float(s['valor_unitario'])} for s in saldos
    ]})


@motos_assai_bp.route('/separacao/desfazer/<int:item_id>', methods=['POST'])
@login_required
@require_motos_assai
def separacao_desfazer(item_id):
    try:
        result = desfazer_chassi(item_id, current_user.id)
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    return jsonify({'ok': True, **result})


@motos_assai_bp.route('/separacao/<int:separacao_id>/finalizar', methods=['POST'])
@login_required
@require_motos_assai
def separacao_finalizar(separacao_id):
    try:
        sep = finalizar_separacao(separacao_id, current_user.id)
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    return jsonify({'ok': True, 'status': sep.status})


@motos_assai_bp.route('/separacao/<int:separacao_id>/cancelar', methods=['POST'])
@login_required
@require_motos_assai
def separacao_cancelar(separacao_id):
    data = request.get_json(silent=True) or {}
    try:
        sep = cancelar_separacao(separacao_id, data.get('motivo', ''), current_user.id)
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    return jsonify({'ok': True, 'status': sep.status})
