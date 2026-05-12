"""Rotas para gestao de pendencias de montagem (defeito de peca).

Pendencia aberta: chassi com ultimo evento PENDENTE.
Resolucao: chama montagem_service.resolver_pendencia() ja existente.
Historico: lista append-only de eventos PENDENCIA_RESOLVIDA.
"""

from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services.pendencia_service import (
    listar_abertas, listar_historico_resolvidas, contar_pendencias_abertas,
)
from app.motos_assai.services.montagem_service import (
    resolver_pendencia, MontagemValidationError,
)


@motos_assai_bp.route('/pendencias')
@login_required
@require_motos_assai
def pendencias_landing():
    """Landing com 2 cards/botoes: Abertas e Historico."""
    total_abertas = contar_pendencias_abertas()
    return render_template(
        'motos_assai/pendencias/landing.html',
        total_abertas=total_abertas,
    )


@motos_assai_bp.route('/pendencias/abertas')
@login_required
@require_motos_assai
def pendencias_abertas():
    """Lista chassis em PENDENTE com botao para resolver."""
    abertas = listar_abertas()
    return render_template(
        'motos_assai/pendencias/abertas.html',
        abertas=abertas,
    )


@motos_assai_bp.route('/pendencias/historico')
@login_required
@require_motos_assai
def pendencias_historico():
    """Lista append-only de PENDENCIA_RESOLVIDA com observacao original."""
    historico = listar_historico_resolvidas(limit=300)
    return render_template(
        'motos_assai/pendencias/historico.html',
        historico=historico,
    )


@motos_assai_bp.route('/pendencias/resolver', methods=['POST'])
@login_required
@require_motos_assai
def pendencias_resolver():
    """Resolve pendencia: PENDENTE -> PENDENCIA_RESOLVIDA -> MONTADA.

    Espera JSON: {chassi, descricao_resolucao}
    """
    data = request.get_json(silent=True) or {}
    chassi = (data.get('chassi') or '').strip().upper()
    descricao = (data.get('descricao_resolucao') or '').strip()
    if not chassi:
        return jsonify({'ok': False, 'erro': 'Chassi obrigatorio'}), 400
    try:
        result = resolver_pendencia(
            chassi=chassi,
            descricao_resolucao=descricao,
            operador_id=current_user.id,
        )
    except MontagemValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    return jsonify({'ok': True, **(result if isinstance(result, dict) else {})})
