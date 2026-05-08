from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    registrar_montagem, historico_3_ultimas_montagens,
    MontagemValidationError,
)


@motos_assai_bp.route('/montagem')
@login_required
@require_motos_assai
def montagem_tela():
    historico = historico_3_ultimas_montagens()
    return render_template('motos_assai/montagem/quick.html', historico=historico)


@motos_assai_bp.route('/montagem/registrar', methods=['POST'])
@login_required
@require_motos_assai
def montagem_registrar():
    data = request.get_json(silent=True) or {}
    try:
        result = registrar_montagem(
            chassi=data.get('chassi', ''),
            pendencia=bool(data.get('pendencia')),
            descricao_pendencia=data.get('descricao_pendencia'),
            chassi_doador=data.get('chassi_doador'),
            operador_id=current_user.id,
        )
    except MontagemValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    historico = historico_3_ultimas_montagens()
    return jsonify({'ok': True, **result, 'historico': [
        {**h, 'ocorrido_em': h['ocorrido_em'].strftime('%d/%m %H:%M')}
        for h in historico
    ]})
