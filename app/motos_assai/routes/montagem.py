from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    registrar_montagem, historico_3_ultimas_montagens,
    MontagemValidationError,
)
from app.motos_assai.services.resumo_service import (
    listar_motos_montadas_agrupadas,
)


@motos_assai_bp.route('/montagem')
@login_required
@require_motos_assai
def montagem_tela():
    historico = historico_3_ultimas_montagens()
    # Item 1a (2026-05-12): exibir inventario atual de motos MONTADAS,
    # agrupado por modelo. Inclui REVERTIDA_PARA_MONTADA (efetivo).
    montadas = listar_motos_montadas_agrupadas()
    return render_template(
        'motos_assai/montagem/quick.html',
        historico=historico,
        montadas=montadas,
    )


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


#
# 2026-05-13 (#12 fix): rota POST /montagem/resolver-pendencia REMOVIDA por
# ser duplicata exata de POST /pendencias/resolver (mesmo body, mesmo service
# `resolver_pendencia`, mesma exception). Toda UI consome /pendencias/resolver
# via pendencias_resolver.js. Mantida apenas pendencias_resolver como
# endpoint canonico (single source of truth).
#
