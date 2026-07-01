from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms.peca_forms import PecaForm
from app.motos_assai.services import peca_service, movimento_service
from app.motos_assai.services.peca_service import PecaError
from app.motos_assai.models import AssaiModelo, AssaiPeca


def _modelo_choices():
    return [(m.id, f'{m.codigo} — {m.nome}') for m in AssaiModelo.query.order_by(AssaiModelo.codigo).all()]


def _br_decimal(s):
    s = (s or '').strip().replace('.', '').replace(',', '.')
    return s or None


@motos_assai_bp.route('/pecas')
@login_required
@require_motos_assai
def peca_lista():
    busca = (request.args.get('q') or '').strip() or None
    pecas = peca_service.listar(ativo=None, busca=busca)
    linhas = [{'p': p, 'saldo': movimento_service.saldo(p.id)} for p in pecas]
    return render_template('motos_assai/pecas/lista.html', linhas=linhas, q=busca or '')


@motos_assai_bp.route('/pecas/novo', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def peca_novo():
    form = PecaForm()
    form.modelo_ids.choices = _modelo_choices()
    if form.validate_on_submit():
        try:
            peca_service.criar_peca(
                nome=form.nome.data, codigo=form.codigo.data or None,
                custo_referencia=_br_decimal(form.custo_referencia.data),
                modelo_ids=form.modelo_ids.data, operador_id=current_user.id)
            db.session.commit(); flash('Peça criada.', 'success')
            return redirect(url_for('motos_assai.peca_lista'))
        except PecaError as e:
            db.session.rollback(); flash(str(e), 'danger')
    return render_template('motos_assai/pecas/form.html', form=form, modo='novo')


@motos_assai_bp.route('/pecas/<int:pid>/editar', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def peca_editar(pid):
    peca = db.session.get(AssaiPeca, pid)
    if not peca:
        flash('Peça não encontrada.', 'danger')
        return redirect(url_for('motos_assai.peca_lista'))
    form = PecaForm(obj=peca)
    form.modelo_ids.choices = _modelo_choices()
    if request.method == 'GET':
        form.modelo_ids.data = [pm.modelo_id for pm in peca.modelos]
    if form.validate_on_submit():
        try:
            peca_service.editar_peca(
                peca_id=pid, nome=form.nome.data, codigo=form.codigo.data or None,
                custo_referencia=_br_decimal(form.custo_referencia.data), ativo=form.ativo.data)
            atuais = {pm.modelo_id for pm in peca.modelos}
            novos = set(form.modelo_ids.data or [])
            for mid in (novos - atuais):
                peca_service.vincular_modelo(peca_id=pid, modelo_id=mid)
            for mid in (atuais - novos):
                peca_service.desvincular_modelo(peca_id=pid, modelo_id=mid)
            db.session.commit(); flash('Peça atualizada.', 'success')
            return redirect(url_for('motos_assai.peca_detalhe', pid=pid))
        except PecaError as e:
            db.session.rollback(); flash(str(e), 'danger')
    return render_template('motos_assai/pecas/form.html', form=form, modo='editar', peca=peca)


@motos_assai_bp.route('/pecas/<int:pid>')
@login_required
@require_motos_assai
def peca_detalhe(pid):
    peca = db.session.get(AssaiPeca, pid)
    if not peca:
        flash('Peça não encontrada.', 'danger')
        return redirect(url_for('motos_assai.peca_lista'))
    return render_template('motos_assai/pecas/detalhe.html', peca=peca,
                           saldo=movimento_service.saldo(pid),
                           custo_medio=movimento_service.custo_medio(pid))
