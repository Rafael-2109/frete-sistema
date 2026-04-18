"""Rotas de cadastro: lojas e modelos."""
from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from app.hora.decorators import require_lojas as login_required

from app.hora.routes import hora_bp
from app.hora.services import cadastro_service


# ----------------------------- Lojas -----------------------------

@hora_bp.route('/lojas')
@login_required
def lojas_lista():
    lojas = cadastro_service.listar_lojas(apenas_ativas=False)
    return render_template('hora/lojas_lista.html', lojas=lojas)


@hora_bp.route('/lojas/novo', methods=['GET', 'POST'])
@login_required
def lojas_novo():
    if request.method == 'POST':
        try:
            cadastro_service.criar_loja(
                cnpj=request.form['cnpj'],
                nome=request.form['nome'],
                endereco=request.form.get('endereco'),
                cidade=request.form.get('cidade'),
                uf=request.form.get('uf'),
            )
            flash('Loja cadastrada com sucesso.', 'success')
            return redirect(url_for('hora.lojas_lista'))
        except ValueError as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template('hora/lojas_novo.html')


# ----------------------------- Modelos -----------------------------

@hora_bp.route('/modelos')
@login_required
def modelos_lista():
    modelos = cadastro_service.listar_modelos(apenas_ativos=False)
    return render_template('hora/modelos_lista.html', modelos=modelos)


@hora_bp.route('/modelos/novo', methods=['GET', 'POST'])
@login_required
def modelos_novo():
    if request.method == 'POST':
        try:
            cadastro_service.criar_modelo(
                nome_modelo=request.form['nome_modelo'],
                potencia_motor=request.form.get('potencia_motor') or None,
                descricao=request.form.get('descricao') or None,
            )
            flash('Modelo cadastrado com sucesso.', 'success')
            return redirect(url_for('hora.modelos_lista'))
        except ValueError as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template('hora/modelos_novo.html')
