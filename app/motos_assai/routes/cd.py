from flask import render_template, redirect, url_for, flash, abort
from flask_login import login_required
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import CdForm
from app.motos_assai.services import get_cd_principal, atualizar_cd


@motos_assai_bp.route('/cd')
@login_required
@require_motos_assai
def cd_detalhe():
    cd = get_cd_principal()
    if not cd:
        flash('CD não cadastrado. Rode a migration de seed.', 'warning')
        return redirect(url_for('motos_assai.dashboard'))
    return render_template('motos_assai/cd/detalhe.html', cd=cd)


@motos_assai_bp.route('/cd/editar', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def cd_editar():
    cd = get_cd_principal()
    if not cd:
        abort(404)
    form = CdForm(obj=cd)
    if form.validate_on_submit():
        atualizar_cd(cd.id, {
            'nome': form.nome.data.strip(),
            'cnpj': form.cnpj.data.strip() if form.cnpj.data else None,
            'endereco': form.endereco.data.strip() if form.endereco.data else None,
            'bairro': form.bairro.data.strip() if form.bairro.data else None,
            'cep': form.cep.data.strip() if form.cep.data else None,
            'cidade': form.cidade.data.strip() if form.cidade.data else None,
            'uf': form.uf.data or None,
            'ativo': form.ativo.data,
        })
        flash('CD atualizado.', 'success')
        return redirect(url_for('motos_assai.cd_detalhe'))
    return render_template('motos_assai/cd/form.html', form=form, cd=cd)
