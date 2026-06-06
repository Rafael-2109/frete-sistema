# app/integracoes/tagplus/webhook_notificacao_routes.py
"""Webhook dedicado de NOTIFICAÇÃO WhatsApp (pedido_criado / nfe_criada).

Separado do /webhook/tagplus/nfe (faturamento) — falha aqui não afeta a
importação e vice-versa. Valida X-Hub-Secret (reusa validar_assinatura),
registra em tagplus_notificacao_whatsapp (dedupe) e dispara thread async.
"""
import logging

from flask import Blueprint, request, jsonify
from flask_login import login_required

from app import db, csrf
from app.integracoes.tagplus.models import TagPlusNotificacaoWhatsapp
from app.integracoes.tagplus.webhook_routes import validar_assinatura
from app.integracoes.tagplus.services.notificacao_whatsapp_service import disparar_thread

logger = logging.getLogger(__name__)

tagplus_notificacao = Blueprint('tagplus_notificacao', __name__)

EVENTO_TIPO = {
    'pedido_criado': 'PEDIDO',
    'nfe_criada': 'NFE',
}


@csrf.exempt
@tagplus_notificacao.route('/integracoes/tagplus/webhook/notificacao', methods=['POST'])
def webhook_notificacao():
    # Endurecimento: este endpoint exige assinatura (não aceita o modo inseguro
    # herdado de validar_assinatura, pois a URL é pública).
    if not request.headers.get('X-Hub-Secret') and not request.headers.get('X-TagPlus-Signature'):
        logger.warning("[TAGPLUS-NOTIF] Webhook sem cabeçalho de assinatura rejeitado")
        return jsonify({'erro': 'assinatura obrigatória'}), 401

    ok, motivo = validar_assinatura(request)
    if not ok:
        logger.warning(f"[TAGPLUS-NOTIF] Webhook rejeitado: {motivo}")
        return jsonify({'erro': motivo}), 401

    dados = request.get_json(silent=True) or {}
    event_type = (dados.get('event_type') or '').strip()
    data_arr = dados.get('data') or []
    tagplus_id = str(data_arr[0].get('id')) if data_arr and isinstance(data_arr[0], dict) and data_arr[0].get('id') is not None else None

    tipo = EVENTO_TIPO.get(event_type)
    if not tipo:
        logger.info(f"[TAGPLUS-NOTIF] Evento fora do escopo: '{event_type}' (ignorado)")
        return jsonify({'status': 'ignorado', 'event_type': event_type}), 200

    if not tagplus_id:
        logger.error(f"[TAGPLUS-NOTIF] Webhook sem id em data[]: {dados}")
        return jsonify({'erro': 'id ausente em data[]'}), 400

    existente = TagPlusNotificacaoWhatsapp.query.filter_by(
        tipo=tipo, tagplus_id=tagplus_id, event_type=event_type
    ).first()
    if existente:
        logger.info(f"[TAGPLUS-NOTIF] Duplicado {tipo} {tagplus_id} (status={existente.status}) — skip")
        return jsonify({'status': 'duplicado', 'id': existente.id}), 200

    reg = TagPlusNotificacaoWhatsapp(tipo=tipo, event_type=event_type, tagplus_id=tagplus_id)
    db.session.add(reg)
    db.session.commit()

    from flask import current_app
    disparar_thread(current_app._get_current_object(), reg.id)
    return jsonify({'status': 'ok', 'id': reg.id}), 200


@tagplus_notificacao.route('/integracoes/tagplus/notificacoes', methods=['GET'])
@login_required
def notificacoes_lista():
    from flask import render_template
    page = request.args.get('page', 1, type=int)
    pag = (TagPlusNotificacaoWhatsapp.query
           .order_by(TagPlusNotificacaoWhatsapp.criado_em.desc())
           .paginate(page=page, per_page=50, error_out=False))
    return render_template('integracoes/tagplus_notificacoes.html', pag=pag)


@tagplus_notificacao.route('/integracoes/tagplus/notificacoes/<int:reg_id>/reenviar', methods=['POST'])
@login_required
def notificacao_reenviar(reg_id):
    from flask import current_app, redirect, url_for, flash
    reg = TagPlusNotificacaoWhatsapp.query.get_or_404(reg_id)
    reg.status = 'PENDENTE'
    db.session.commit()
    disparar_thread(current_app._get_current_object(), reg.id)
    flash(f'Reenvio disparado para {reg.tipo} {reg.tagplus_id}.', 'info')
    return redirect(url_for('tagplus_notificacao.notificacoes_lista'))
