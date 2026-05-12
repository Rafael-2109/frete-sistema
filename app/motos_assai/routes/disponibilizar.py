from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    disponibilizar as svc_disponibilizar,
    reverter_para_montada,
    historico_3_ultimas_disponibilizacoes,
    DisponibilizarValidationError,
)
from app.motos_assai.services.resumo_service import (
    listar_motos_disponiveis_agrupadas,
)


@motos_assai_bp.route('/disponibilizar')
@login_required
@require_motos_assai
def disponibilizar_tela():
    historico = historico_3_ultimas_disponibilizacoes()
    # Item 1b (2026-05-12): exibir inventario atual de motos DISPONIVEIS,
    # agrupado por modelo (motos prontas para separacao).
    disponiveis = listar_motos_disponiveis_agrupadas()
    return render_template(
        'motos_assai/disponibilizar/quick.html',
        historico=historico,
        disponiveis=disponiveis,
    )


@motos_assai_bp.route('/disponibilizar/registrar', methods=['POST'])
@login_required
@require_motos_assai
def disponibilizar_registrar():
    data = request.get_json(silent=True) or {}
    try:
        result = svc_disponibilizar(data.get('chassi', ''), current_user.id)
    except DisponibilizarValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    historico = historico_3_ultimas_disponibilizacoes()
    return jsonify({'ok': True, **result, 'historico': [
        {**h, 'ocorrido_em': h['ocorrido_em'].strftime('%d/%m %H:%M')}
        for h in historico
    ]})


@motos_assai_bp.route('/disponibilizar/reverter', methods=['POST'])
@login_required
@require_motos_assai
def disponibilizar_reverter():
    data = request.get_json(silent=True) or {}
    try:
        result = reverter_para_montada(
            chassi=data.get('chassi', ''),
            motivo=data.get('motivo', ''),
            operador_id=current_user.id,
        )
    except DisponibilizarValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    historico = historico_3_ultimas_disponibilizacoes()
    return jsonify({'ok': True, **result, 'historico': [
        {**h, 'ocorrido_em': h['ocorrido_em'].strftime('%d/%m %H:%M')}
        for h in historico
    ]})
