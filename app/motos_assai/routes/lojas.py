from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import LojaForm
from app.motos_assai.services import (
    listar_lojas, criar_loja, atualizar_loja, get_loja, LojaJaExisteError,
)


@motos_assai_bp.route('/lojas')
@login_required
@require_motos_assai
def lojas_lista():
    busca = request.args.get('q', '').strip() or None
    somente_ativas = request.args.get('ativas') == '1'
    lojas = listar_lojas(somente_ativas=somente_ativas, busca=busca)
    return render_template('motos_assai/lojas/lista.html',
                           lojas=lojas, busca=busca, somente_ativas=somente_ativas)


@motos_assai_bp.route('/lojas/nova', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def lojas_nova():
    form = LojaForm()
    if form.validate_on_submit():
        try:
            loja = criar_loja({
                'numero': form.numero.data.strip(),
                'nome': form.nome.data.strip(),
                'razao_social': form.razao_social.data.strip(),
                'cnpj': form.cnpj.data.strip(),
                'ie': form.ie.data.strip() if form.ie.data else None,
                'endereco': form.endereco.data.strip() if form.endereco.data else None,
                'bairro': form.bairro.data.strip() if form.bairro.data else None,
                'cep': form.cep.data.strip() if form.cep.data else None,
                'cidade': form.cidade.data.strip() if form.cidade.data else None,
                'uf': form.uf.data,
                'regional': form.regional.data.strip() if form.regional.data else None,
                'ativo': form.ativo.data,
            })
            flash(f'Loja {loja.numero} criada.', 'success')
            return redirect(url_for('motos_assai.lojas_detalhe', loja_id=loja.id))
        except LojaJaExisteError as e:
            flash(str(e), 'danger')
    return render_template('motos_assai/lojas/form.html', form=form, modo='nova')


@motos_assai_bp.route('/lojas/<int:loja_id>')
@login_required
@require_motos_assai
def lojas_detalhe(loja_id):
    loja = get_loja(loja_id)
    return render_template('motos_assai/lojas/detalhe.html', loja=loja)


@motos_assai_bp.route('/lojas/<int:loja_id>/editar', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def lojas_editar(loja_id):
    loja = get_loja(loja_id)
    form = LojaForm(obj=loja)
    if form.validate_on_submit():
        atualizar_loja(loja_id, {
            'nome': form.nome.data.strip(),
            'razao_social': form.razao_social.data.strip(),
            'cnpj': form.cnpj.data.strip(),
            'ie': form.ie.data.strip() if form.ie.data else None,
            'endereco': form.endereco.data.strip() if form.endereco.data else None,
            'bairro': form.bairro.data.strip() if form.bairro.data else None,
            'cep': form.cep.data.strip() if form.cep.data else None,
            'cidade': form.cidade.data.strip() if form.cidade.data else None,
            'uf': form.uf.data,
            'regional': form.regional.data.strip() if form.regional.data else None,
            'ativo': form.ativo.data,
        })
        flash(f'Loja {loja.numero} atualizada.', 'success')
        return redirect(url_for('motos_assai.lojas_detalhe', loja_id=loja_id))
    return render_template('motos_assai/lojas/form.html', form=form, loja=loja, modo='editar')
