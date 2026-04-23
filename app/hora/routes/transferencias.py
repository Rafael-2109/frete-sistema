"""Rotas de transferencia entre filiais HORA."""
from __future__ import annotations

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_

from app import db
from app.hora.decorators import require_hora_perm
from app.hora.models import (
    HoraLoja, HoraTransferencia, HoraTransferenciaAuditoria,
)
from app.hora.routes import hora_bp
from app.hora.services import transferencia_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids, usuario_tem_acesso_a_loja,
    loja_origem_permitida_para_transferencia,
)


@hora_bp.route('/transferencias')
@require_hora_perm('transferencias', 'ver')
def transferencias_lista():
    permitidas = lojas_permitidas_ids()
    q = HoraTransferencia.query

    status = request.args.get('status')
    if status:
        q = q.filter(HoraTransferencia.status == status)
    loja_id = request.args.get('loja_id', type=int)
    if loja_id:
        q = q.filter(or_(
            HoraTransferencia.loja_origem_id == loja_id,
            HoraTransferencia.loja_destino_id == loja_id,
        ))
    if permitidas is not None:
        q = q.filter(or_(
            HoraTransferencia.loja_origem_id.in_(permitidas),
            HoraTransferencia.loja_destino_id.in_(permitidas),
        ))

    transferencias = q.order_by(HoraTransferencia.emitida_em.desc()).limit(500).all()
    lojas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.apelido).all()
    return render_template(
        'hora/transferencias_lista.html',
        transferencias=transferencias, lojas=lojas,
        filtros={'status': status, 'loja_id': loja_id},
    )


@hora_bp.route('/transferencias/<int:transferencia_id>')
@require_hora_perm('transferencias', 'ver')
def transferencia_detalhe(transferencia_id):
    t = HoraTransferencia.query.get_or_404(transferencia_id)
    if not (usuario_tem_acesso_a_loja(t.loja_origem_id)
            or usuario_tem_acesso_a_loja(t.loja_destino_id)):
        abort(403)
    return render_template('hora/transferencia_detalhe.html', t=t)


@hora_bp.route('/transferencias/nova', methods=['GET', 'POST'])
@require_hora_perm('transferencias', 'criar')
def transferencia_nova():
    permitidas = lojas_permitidas_ids()
    origem_fixa = loja_origem_permitida_para_transferencia()

    if request.method == 'POST':
        loja_origem_id = request.form.get('loja_origem_id', type=int)
        loja_destino_id = request.form.get('loja_destino_id', type=int)
        chassis_raw = request.form.get('chassis') or ''
        observacoes = (request.form.get('observacoes') or '').strip() or None

        chassis = [c.strip().upper() for c in chassis_raw.splitlines() if c.strip()]

        if origem_fixa is not None and loja_origem_id != origem_fixa:
            flash('Voce so pode emitir transferencias da sua loja', 'danger')
            return redirect(url_for('hora.transferencia_nova'))
        if permitidas is not None and loja_origem_id not in permitidas:
            flash('Loja origem fora do escopo', 'danger')
            return redirect(url_for('hora.transferencia_nova'))

        try:
            t = transferencia_service.criar_transferencia(
                loja_origem_id=loja_origem_id,
                loja_destino_id=loja_destino_id,
                chassis=chassis,
                usuario=current_user.nome,
                observacoes=observacoes,
            )
            db.session.commit()
            flash(f'Transferencia #{t.id} emitida com {len(t.itens)} chassi(s).', 'success')
            return redirect(url_for('hora.transferencia_detalhe', transferencia_id=t.id))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'danger')
            return redirect(url_for('hora.transferencia_nova'))

    lojas_todas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.apelido).all()
    return render_template(
        'hora/transferencia_nova.html',
        lojas=lojas_todas, origem_fixa=origem_fixa,
    )


@hora_bp.route('/transferencias/<int:transferencia_id>/confirmar')
@require_hora_perm('transferencias', 'editar')
def transferencia_confirmar_wizard(transferencia_id):
    t = HoraTransferencia.query.get_or_404(transferencia_id)
    if not usuario_tem_acesso_a_loja(t.loja_destino_id):
        abort(403)
    return render_template('hora/transferencia_confirmar_wizard.html', t=t)


@hora_bp.route('/transferencias/<int:transferencia_id>/confirmar-item', methods=['POST'])
@require_hora_perm('transferencias', 'editar')
def transferencia_confirmar_item(transferencia_id):
    t = HoraTransferencia.query.get_or_404(transferencia_id)
    if not usuario_tem_acesso_a_loja(t.loja_destino_id):
        return jsonify(error='forbidden'), 403

    numero_chassi = (request.form.get('numero_chassi') or '').strip().upper()
    qr_code_lido = request.form.get('qr_code_lido') == 'true'
    foto_s3_key = (request.form.get('foto_s3_key') or '').strip() or None
    observacao = (request.form.get('observacao') or '').strip() or None

    try:
        item = transferencia_service.confirmar_item_destino(
            transferencia_id=transferencia_id,
            numero_chassi=numero_chassi,
            usuario=current_user.nome,
            qr_code_lido=qr_code_lido,
            foto_s3_key=foto_s3_key,
            observacao=observacao,
        )
        transferencia_service.finalizar_se_tudo_confirmado(transferencia_id)
        db.session.commit()
        t_reload = HoraTransferencia.query.get(transferencia_id)
        return jsonify(
            ok=True,
            item_id=item.id,
            status=t_reload.status if t_reload else None,
        )
    except ValueError as e:
        db.session.rollback()
        return jsonify(error=str(e)), 400


@hora_bp.route('/transferencias/<int:transferencia_id>/cancelar', methods=['POST'])
@require_hora_perm('transferencias', 'editar')
def transferencia_cancelar(transferencia_id):
    t = HoraTransferencia.query.get_or_404(transferencia_id)
    if not usuario_tem_acesso_a_loja(t.loja_origem_id):
        abort(403)
    motivo = (request.form.get('motivo') or '').strip()
    try:
        transferencia_service.cancelar_transferencia(
            transferencia_id, motivo, current_user.nome,
        )
        db.session.commit()
        flash('Transferencia cancelada.', 'success')
    except ValueError as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('hora.transferencia_detalhe', transferencia_id=transferencia_id))


@hora_bp.route('/transferencias/<int:transferencia_id>/auditoria')
@require_hora_perm('transferencias', 'ver')
def transferencia_auditoria_json(transferencia_id):
    t = HoraTransferencia.query.get_or_404(transferencia_id)
    if not (usuario_tem_acesso_a_loja(t.loja_origem_id)
            or usuario_tem_acesso_a_loja(t.loja_destino_id)):
        return jsonify(error='forbidden'), 403
    itens = (
        HoraTransferenciaAuditoria.query
        .filter_by(transferencia_id=transferencia_id)
        .order_by(HoraTransferenciaAuditoria.criado_em.desc())
        .all()
    )
    return jsonify(auditoria=[
        dict(
            id=a.id, usuario=a.usuario, acao=a.acao,
            campo_alterado=a.campo_alterado,
            valor_antes=a.valor_antes, valor_depois=a.valor_depois,
            detalhe=a.detalhe,
            criado_em=a.criado_em.isoformat() if a.criado_em else None,
        )
        for a in itens
    ])
