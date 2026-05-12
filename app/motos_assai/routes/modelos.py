from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import ModeloForm, TestarRegexForm
from app.motos_assai.services import (
    listar_modelos, get_modelo, criar_modelo, atualizar_modelo,
    testar_regex, ModeloJaExisteError,
)


@motos_assai_bp.route('/modelos')
@login_required
@require_motos_assai
def modelos_lista():
    somente_ativos = request.args.get('ativos') == '1'
    modelos = listar_modelos(somente_ativos=somente_ativos)
    return render_template('motos_assai/modelos/lista.html',
                           modelos=modelos, somente_ativos=somente_ativos)


@motos_assai_bp.route('/modelos/novo', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def modelos_novo():
    form = ModeloForm()
    teste_form = TestarRegexForm()
    if form.validate_on_submit():
        try:
            m = criar_modelo({
                'codigo': form.codigo.data.strip().upper(),
                'nome': form.nome.data.strip(),
                'descricao_qpa': form.descricao_qpa.data.strip() if form.descricao_qpa.data else None,
                'codigo_qpa': form.codigo_qpa.data.strip() if form.codigo_qpa.data else None,
                'regex_chassi': form.regex_chassi.data.strip() if form.regex_chassi.data else None,
                'peso_kg': form.peso_kg.data,
                'peso_cubado_kg': form.peso_cubado_kg.data,
                'ativo': form.ativo.data,
            })
            flash(f'Modelo {m.codigo} criado.', 'success')
            return redirect(url_for('motos_assai.modelos_detalhe', modelo_id=m.id))
        except ModeloJaExisteError as e:
            flash(str(e), 'danger')
    return render_template('motos_assai/modelos/form.html',
                           form=form, teste_form=teste_form, modo='novo')


@motos_assai_bp.route('/modelos/<int:modelo_id>')
@login_required
@require_motos_assai
def modelos_detalhe(modelo_id):
    modelo = get_modelo(modelo_id)
    return render_template('motos_assai/modelos/detalhe.html', modelo=modelo)


@motos_assai_bp.route('/modelos/<int:modelo_id>/editar', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def modelos_editar(modelo_id):
    modelo = get_modelo(modelo_id)
    form = ModeloForm(obj=modelo)
    teste_form = TestarRegexForm()
    if form.validate_on_submit():
        atualizar_modelo(modelo_id, {
            'codigo': form.codigo.data.strip().upper(),
            'nome': form.nome.data.strip(),
            'descricao_qpa': form.descricao_qpa.data.strip() if form.descricao_qpa.data else None,
            'codigo_qpa': form.codigo_qpa.data.strip() if form.codigo_qpa.data else None,
            'regex_chassi': form.regex_chassi.data.strip() if form.regex_chassi.data else None,
            'peso_kg': form.peso_kg.data,
            'peso_cubado_kg': form.peso_cubado_kg.data,
            'ativo': form.ativo.data,
        })
        flash(f'Modelo {modelo.codigo} atualizado.', 'success')
        return redirect(url_for('motos_assai.modelos_detalhe', modelo_id=modelo_id))
    return render_template('motos_assai/modelos/form.html',
                           form=form, teste_form=teste_form, modelo=modelo, modo='editar')


@motos_assai_bp.route('/modelos/api/testar-regex', methods=['POST'])
@login_required
@require_motos_assai
def modelos_api_testar_regex():
    """Endpoint AJAX para testar regex contra chassi sem salvar."""
    data = request.get_json(silent=True) or {}
    regex = (data.get('regex') or '').strip()
    chassi = (data.get('chassi') or '').strip()
    if not regex or not chassi:
        return jsonify({'ok': False, 'erro': 'regex e chassi obrigatórios'}), 400
    try:
        bate = testar_regex(regex, chassi)
        return jsonify({'ok': True, 'bate': bate, 'regex': regex, 'chassi': chassi})
    except Exception as e:
        return jsonify({'ok': False, 'erro': f'regex inválido: {e}'}), 400
