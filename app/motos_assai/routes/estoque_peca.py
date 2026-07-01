"""Rotas de Estoque de Peça (ledger + entrada/ajuste/descarte) — Spec 2 Task 11.

Tela agregada por peça (saldo + custo médio) e ledger append-only por peça.
3 ações POST: entrada manual (sem NF), ajuste (correção/contagem) e descarte.
`movimento_service` faz add+flush SEM commit — a rota controla a transação.
"""
from decimal import InvalidOperation

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm

from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import peca_service, movimento_service
from app.motos_assai.services.movimento_service import EstoqueError
from app.motos_assai.models import AssaiPeca, AssaiEstoqueMovimento

# Erros de conversão numérica que devem virar flash gracioso, não 500.
# `movimento_service._decimal` já embrulha `Decimal(str(valor))` em EstoqueError,
# mas capturamos também InvalidOperation/ValueError como defesa em profundidade
# (mesma classe de bug do Task 10 — não confiar cegamente que o service cobre tudo).
_ERROS_ENTRADA_INVALIDA = (EstoqueError, InvalidOperation, ValueError)


def _br(s):
    s = (s or '').strip().replace('.', '').replace(',', '.')
    return s or None


@motos_assai_bp.route('/estoque-pecas')
@login_required
@require_motos_assai
def estoque_peca_lista():
    linhas = [{'p': p, 'saldo': movimento_service.saldo(p.id),
               'custo_medio': movimento_service.custo_medio(p.id)}
              for p in peca_service.listar(ativo=None)]
    return render_template('motos_assai/estoque_pecas/lista.html', linhas=linhas, form=FlaskForm())


@motos_assai_bp.route('/estoque-pecas/<int:peca_id>')
@login_required
@require_motos_assai
def estoque_peca_detalhe(peca_id):
    peca = db.session.get(AssaiPeca, peca_id)
    if not peca:
        flash('Peça não encontrada.', 'danger')
        return redirect(url_for('motos_assai.estoque_peca_lista'))
    movs = (AssaiEstoqueMovimento.query.filter_by(peca_id=peca_id)
            .order_by(AssaiEstoqueMovimento.id.desc()).limit(300).all())
    return render_template('motos_assai/estoque_pecas/detalhe.html', peca=peca, movs=movs,
                           saldo=movimento_service.saldo(peca_id),
                           custo_medio=movimento_service.custo_medio(peca_id), form=FlaskForm())


@motos_assai_bp.route('/estoque-pecas/entrada', methods=['POST'])
@login_required
@require_motos_assai
def estoque_peca_entrada():
    try:
        movimento_service.registrar_entrada(
            peca_id=request.form.get('peca_id', type=int),
            quantidade=_br(request.form.get('quantidade')),
            custo_unitario=_br(request.form.get('custo_unitario')),
            operador_id=current_user.id,
            recebimento_ref=(request.form.get('recebimento_ref') or None))
        db.session.commit()
        flash('Entrada registrada.', 'success')
    except _ERROS_ENTRADA_INVALIDA as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(request.referrer or url_for('motos_assai.estoque_peca_lista'))


@motos_assai_bp.route('/estoque-pecas/ajustar', methods=['POST'])
@login_required
@require_motos_assai
def estoque_peca_ajustar():
    try:
        movimento_service.ajustar(
            peca_id=request.form.get('peca_id', type=int),
            delta=_br(request.form.get('delta')),
            motivo=request.form.get('motivo', ''), operador_id=current_user.id)
        db.session.commit()
        flash('Ajuste registrado.', 'success')
    except _ERROS_ENTRADA_INVALIDA as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(request.referrer or url_for('motos_assai.estoque_peca_lista'))


@motos_assai_bp.route('/estoque-pecas/descartar', methods=['POST'])
@login_required
@require_motos_assai
def estoque_peca_descartar():
    try:
        movimento_service.descartar(
            peca_id=request.form.get('peca_id', type=int),
            quantidade=_br(request.form.get('quantidade')), operador_id=current_user.id)
        db.session.commit()
        flash('Descarte registrado.', 'success')
    except _ERROS_ENTRADA_INVALIDA as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(request.referrer or url_for('motos_assai.estoque_peca_lista'))
