"""Rotas para gestao de pendencias de montagem (defeito de peca).

Pendencia aberta: chassi com ultimo evento PENDENTE.
Resolucao: chama montagem_service.resolver_pendencia() ja existente.
Historico: lista append-only de eventos PENDENCIA_RESOLVIDA.

2026-05-13: filtros chassi/modelo/data/operador adicionados as duas telas
(abertas e historico). Operadores e modelos populados via servicos auxiliares
para autocomplete (datalist HTML5 + select).
"""

from datetime import date, datetime

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
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


@motos_assai_bp.route('/pendencias/<int:pid>')
@login_required
@require_motos_assai
def pendencia_detalhe(pid):
    """Visao 360 read-only de uma ficha de pendencia (Spec 2 Task 8)."""
    from app.motos_assai.services import pendencia_service
    d = pendencia_service.detalhe_pendencia(pid)
    if d is None:
        flash('Pendência não encontrada.', 'danger')
        return redirect(url_for('motos_assai.pendencias_abertas'))
    return render_template('motos_assai/pendencias/detalhe.html', d=d)


@motos_assai_bp.route('/pendencias/<int:pid>/resolver', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def pendencia_resolver_tela(pid):
    """Tela de resolucao por ficha (Spec 2 Task 7): GET exibe form, POST processa acao."""
    from app.motos_assai.services import pendencia_service, peca_service, movimento_service
    from app.motos_assai.services.resolucao_service import resolver_com_tratativa, ResolucaoError
    from app.motos_assai.services.pendencia_service import PendenciaError
    from app.motos_assai.models import AssaiMoto

    detalhe = pendencia_service.detalhe_pendencia(pid)
    if detalhe is None:
        flash('Pendência não encontrada.', 'danger')
        return redirect(url_for('motos_assai.pendencias_abertas'))

    if request.method == 'POST':
        acao = request.form.get('acao')
        try:
            if acao == 'reclassificar':
                pendencia_service.reclassificar(
                    pendencia_id=pid, categoria=request.form.get('categoria'),
                    origem=request.form.get('origem'), operador_id=current_user.id)
                db.session.commit()
                flash('Pendência reclassificada.', 'success')
            elif acao == 'solicitar-compra':
                itens = [{'peca_id': request.form.get('peca_id', type=int),
                          'quantidade': request.form.get('quantidade', type=float)}]
                pendencia_service.solicitar_compra(
                    pendencia_id=pid, tipo=request.form.get('tipo'), itens=itens,
                    operador_id=current_user.id)
                db.session.commit()
                flash('Compra/garantia solicitada.', 'success')
            elif acao == 'resolver':
                if detalhe['ficha']['categoria'] == 'INDETERMINADA':
                    pendencia_service.reclassificar(
                        pendencia_id=pid, categoria=request.form.get('categoria'),
                        origem=request.form.get('origem'), operador_id=current_user.id)
                resolver_com_tratativa(
                    pendencia_id=pid, tratativa=request.form.get('tratativa'),
                    resolucao_descricao=request.form.get('resolucao_descricao', ''),
                    operador_id=current_user.id,
                    peca_id=request.form.get('peca_id', type=int),
                    quantidade=request.form.get('quantidade', type=float),
                    chassi_doador=(request.form.get('chassi_doador') or '').strip().upper() or None)
                db.session.commit()
                flash('Pendência resolvida.', 'success')
                return redirect(url_for('motos_assai.pendencias_abertas'))
        except (ResolucaoError, PendenciaError) as e:
            db.session.rollback()
            flash(str(e), 'danger')
        return redirect(url_for('motos_assai.pendencia_resolver_tela', pid=pid))

    moto = AssaiMoto.query.filter_by(chassi=detalhe['ficha']['chassi']).first()
    pecas = []
    if moto:
        for p in peca_service.listar_compativeis(moto.modelo_id):
            pecas.append({'id': p.id, 'nome': p.nome, 'saldo': movimento_service.saldo(p.id)})
    return render_template('motos_assai/pendencias/resolver.html', d=detalhe, pecas=pecas)
