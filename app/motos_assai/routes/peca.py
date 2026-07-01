from decimal import InvalidOperation

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms.peca_forms import PecaForm
from app.motos_assai.services import peca_service, movimento_service
from app.motos_assai.services.peca_service import PecaError
from app.motos_assai.models import AssaiModelo, AssaiPeca

# Erros de conversão numérica que devem virar mensagem de formulário, não 500.
_ERROS_CUSTO_INVALIDO = (PecaError, InvalidOperation, ValueError)


def _modelo_choices():
    return [(m.id, f'{m.codigo} — {m.nome}') for m in AssaiModelo.query.order_by(AssaiModelo.codigo).all()]


def _br_decimal(s):
    s = (s or '').strip().replace('.', '').replace(',', '.')
    return s or None


def _decimal_to_br(d):
    """Formata um Decimal para string BR (vírgula decimal), round-trip com `_br_decimal`.

    Ex: Decimal('12.5000') -> '12,50'. NÃO insere separador de milhar — `_br_decimal`
    assume que qualquer '.' é separador de milhar, então incluí-lo aqui quebraria o
    round-trip (era exatamente o bug: `str(Decimal)` usa '.' como decimal, não milhar).
    """
    if d is None:
        return ''
    texto = format(d, 'f')  # notação fixa, nunca científica
    if '.' in texto:
        inteiro, frac = texto.split('.')
        frac = frac.rstrip('0')
        if len(frac) < 2:
            frac = frac.ljust(2, '0')
    else:
        inteiro, frac = texto, '00'
    return f'{inteiro},{frac}'


def _flash_erro_custo(e):
    if isinstance(e, InvalidOperation):
        flash('Custo de referência inválido. Use um valor numérico (ex: 12,50).', 'danger')
    else:
        flash(str(e), 'danger')


@motos_assai_bp.route('/pecas')
@login_required
@require_motos_assai
def peca_lista():
    busca = (request.args.get('q') or '').strip() or None
    somente_ativos = request.args.get('ativos') == '1'
    pecas = peca_service.listar(ativo=True if somente_ativos else None, busca=busca)
    linhas = [{'p': p, 'saldo': movimento_service.saldo(p.id)} for p in pecas]
    return render_template('motos_assai/pecas/lista.html', linhas=linhas, q=busca or '',
                           somente_ativos=somente_ativos)


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
        except _ERROS_CUSTO_INVALIDO as e:
            db.session.rollback(); _flash_erro_custo(e)
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
        if peca.custo_referencia is not None:
            form.custo_referencia.data = _decimal_to_br(peca.custo_referencia)
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
        except _ERROS_CUSTO_INVALIDO as e:
            db.session.rollback(); _flash_erro_custo(e)
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
