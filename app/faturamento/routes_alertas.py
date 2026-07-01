import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.faturamento.models import AlertaFaturamentoCnpj, AlertaFaturamentoConfig
from app.faturamento.services.alerta_faturamento_service import normalizar_cnpj, enviar_teste

logger = logging.getLogger(__name__)

alertas_faturamento_bp = Blueprint(
    'alertas_faturamento', __name__, url_prefix='/faturamento/alertas'
)


def _quem():
    return getattr(current_user, 'nome', None) or getattr(current_user, 'email', None)


@alertas_faturamento_bp.route('/')
@login_required
def index():
    cnpjs = AlertaFaturamentoCnpj.query.order_by(
        AlertaFaturamentoCnpj.ativo.desc(), AlertaFaturamentoCnpj.nome_cliente
    ).all()
    config = AlertaFaturamentoConfig.get_config()
    return render_template('faturamento/alertas/index.html', cnpjs=cnpjs, config=config)


@alertas_faturamento_bp.route('/novo', methods=['POST'])
@login_required
def novo():
    cnpj = normalizar_cnpj(request.form.get('cnpj'))
    emails = (request.form.get('emails') or '').strip()
    nome = (request.form.get('nome_cliente') or '').strip() or None
    if not cnpj or not emails:
        flash('Informe o CNPJ e ao menos um e-mail.', 'warning')
        return redirect(url_for('alertas_faturamento.index'))
    if AlertaFaturamentoCnpj.query.filter_by(cnpj=cnpj).first():
        flash('CNPJ já cadastrado.', 'warning')
        return redirect(url_for('alertas_faturamento.index'))
    db.session.add(AlertaFaturamentoCnpj(cnpj=cnpj, emails=emails, nome_cliente=nome, criado_por=_quem()))
    db.session.commit()
    flash('CNPJ cadastrado.', 'success')
    return redirect(url_for('alertas_faturamento.index'))


@alertas_faturamento_bp.route('/<int:id>/editar', methods=['POST'])
@login_required
def editar(id):
    reg = db.session.get(AlertaFaturamentoCnpj, id)
    if not reg:
        flash('Registro não encontrado.', 'warning')
        return redirect(url_for('alertas_faturamento.index'))
    reg.emails = (request.form.get('emails') or reg.emails).strip()
    reg.nome_cliente = (request.form.get('nome_cliente') or '').strip() or None
    reg.ativo = request.form.get('ativo') == 'on'
    db.session.commit()
    flash('Cadastro atualizado.', 'success')
    return redirect(url_for('alertas_faturamento.index'))


@alertas_faturamento_bp.route('/<int:id>/remover', methods=['POST'])
@login_required
def remover(id):
    reg = db.session.get(AlertaFaturamentoCnpj, id)
    if reg:
        db.session.delete(reg)
        db.session.commit()
        flash('CNPJ removido.', 'success')
    return redirect(url_for('alertas_faturamento.index'))


@alertas_faturamento_bp.route('/config', methods=['POST'])
@login_required
def config():
    cfg = AlertaFaturamentoConfig.get_config()
    cfg.teams_webhook_url = (request.form.get('teams_webhook_url') or '').strip() or None
    cfg.teams_ativo = request.form.get('teams_ativo') == 'on'
    cfg.email_ativo = request.form.get('email_ativo') == 'on'
    cfg.atualizado_por = _quem()
    db.session.commit()
    flash('Configuração salva.', 'success')
    return redirect(url_for('alertas_faturamento.index'))


@alertas_faturamento_bp.route('/<int:id>/testar', methods=['POST'])
@login_required
def testar(id):
    reg = db.session.get(AlertaFaturamentoCnpj, id)
    if not reg:
        flash('Registro não encontrado.', 'warning')
        return redirect(url_for('alertas_faturamento.index'))
    r = enviar_teste(reg, AlertaFaturamentoConfig.get_config())
    flash(f"Teste enviado — e-mail: {r['email'].get('success')}, teams: {r['teams'].get('success')}", 'info')
    return redirect(url_for('alertas_faturamento.index'))
