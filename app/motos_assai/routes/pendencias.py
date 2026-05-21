"""Rotas para gestao de pendencias de montagem (defeito de peca).

Pendencia aberta: chassi com ultimo evento PENDENTE.
Resolucao: chama montagem_service.resolver_pendencia() ja existente.
Historico: lista append-only de eventos PENDENCIA_RESOLVIDA.

2026-05-13: filtros chassi/modelo/data/operador adicionados as duas telas
(abertas e historico). Operadores e modelos populados via servicos auxiliares
para autocomplete (datalist HTML5 + select).
"""

from datetime import date, datetime

from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.models import EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA
from app.motos_assai.services.pendencia_service import (
    listar_abertas, listar_historico_resolvidas, contar_pendencias_abertas,
    operadores_que_registraram_pendencia, modelos_com_pendencias,
)
from app.motos_assai.services.montagem_service import (
    resolver_pendencia, enviar_para_pendencia, MontagemValidationError,
)


def _parse_date(s: str | None) -> date | None:
    """Aceita 'YYYY-MM-DD' (formato HTML5 input type=date)."""
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d').date()
    except (ValueError, AttributeError):
        return None


def _coletar_filtros() -> dict:
    """Le filtros da query string e devolve dict normalizado para o service."""
    return {
        'chassi': (request.args.get('chassi') or '').strip() or None,
        'modelo_id': request.args.get('modelo_id', type=int) or None,
        'data_inicio': _parse_date(request.args.get('data_inicio')),
        'data_fim': _parse_date(request.args.get('data_fim')),
        'operador_id': request.args.get('operador_id', type=int) or None,
    }


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
    filtros = _coletar_filtros()
    abertas = listar_abertas(filtros=filtros)
    operadores = operadores_que_registraram_pendencia(tipos=[EVENTO_PENDENTE])
    modelos = modelos_com_pendencias(tipos=[EVENTO_PENDENTE])
    return render_template(
        'motos_assai/pendencias/abertas.html',
        abertas=abertas,
        filtros_aplicados=filtros,
        operadores=operadores,
        modelos=modelos,
    )


@motos_assai_bp.route('/pendencias/historico')
@login_required
@require_motos_assai
def pendencias_historico():
    """Lista append-only de PENDENCIA_RESOLVIDA com observacao original."""
    filtros = _coletar_filtros()
    historico = listar_historico_resolvidas(limit=300, filtros=filtros)
    operadores = operadores_que_registraram_pendencia(
        tipos=[EVENTO_PENDENCIA_RESOLVIDA],
    )
    modelos = modelos_com_pendencias(
        tipos=[EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA],
    )
    return render_template(
        'motos_assai/pendencias/historico.html',
        historico=historico,
        filtros_aplicados=filtros,
        operadores=operadores,
        modelos=modelos,
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


@motos_assai_bp.route('/pendencias/criar', methods=['POST'])
@login_required
@require_motos_assai
def pendencias_criar():
    """Envia uma moto já processada para PENDENTE (defeito descoberto depois).

    Usado pelos botões "Enviar p/ Pendência" das telas Montagem, Disponibilizar
    e Separação. Aceita MONTADA / REVERTIDA_PARA_MONTADA / DISPONIVEL / SEPARADA.
    Para SEPARADA, libera o chassi da separação (só EM_SEPARACAO).

    Espera JSON: {chassi, descricao_pendencia, chassi_doador?}
    """
    data = request.get_json(silent=True) or {}
    try:
        result = enviar_para_pendencia(
            chassi=data.get('chassi', ''),
            descricao_pendencia=data.get('descricao_pendencia'),
            chassi_doador=data.get('chassi_doador'),
            operador_id=current_user.id,
        )
    except MontagemValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    return jsonify({'ok': True, **result})
