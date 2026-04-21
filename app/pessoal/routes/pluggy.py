"""Rotas Pluggy — conectar Bradesco via Meu Pluggy/Open Finance.

Endpoints:
    GET  /pessoal/pluggy/             — painel com items conectados
    GET  /pessoal/pluggy/conectar     — pagina com widget Pluggy Connect
    POST /pessoal/pluggy/connect-token — gera token para o widget (AJAX)
    POST /pessoal/pluggy/item-created — callback JS apos onSuccess do widget
    POST /pessoal/pluggy/sync/<pk>    — forca sync manual de um item
    POST /pessoal/pluggy/disconnect/<pk> — deleta item no Pluggy e marca inativo
    POST /pessoal/pluggy/webhook      — callback Pluggy (HMAC validated)

Webhook events manipulados:
    item/created | item/updated | item/error | item/login_succeeded
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import threading

from flask import (
    Blueprint, current_app, jsonify, render_template, request, url_for,
)
from flask_login import current_user, login_required

from app import db
from app.pessoal import pode_acessar_pessoal
from app.pessoal.models import PessoalPluggyAccount, PessoalPluggyItem
from app.pessoal.services.pluggy_client import PluggyClientError, get_pluggy_client
from app.pessoal.services.pluggy_dry_run_service import (
    dry_run_item, marcar_aprovacao, marcar_aprovacao_em_lote,
)
from app.pessoal.services.pluggy_merge_service import merge_item
from app.portal.workers import enqueue_job
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

pluggy_bp = Blueprint("pessoal_pluggy", __name__, url_prefix="/pluggy")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _verificar_acesso():
    """Retorna (ok, response) — se nao ok, retorna JSON 403."""
    if not current_user.is_authenticated:
        return False, (jsonify({"erro": "Nao autenticado"}), 401)
    if not pode_acessar_pessoal(current_user):
        return False, (jsonify({"erro": "Acesso restrito ao modulo pessoal"}), 403)
    return True, None


def _validar_assinatura_webhook(req) -> bool:
    """Valida x-pluggy-signature via HMAC SHA256 com PLUGGY_WEBHOOK_SECRET."""
    secret = current_app.config.get("PLUGGY_WEBHOOK_SECRET")
    if not secret:
        logger.warning("PLUGGY_WEBHOOK_SECRET nao configurado — aceitando webhook sem validacao.")
        return True
    signature = req.headers.get("x-signature") or req.headers.get("X-Pluggy-Signature") or ""
    if not signature:
        logger.warning("Webhook recebido sem x-signature header")
        return False
    esperada = hmac.new(
        secret.encode("utf-8"), req.get_data(), hashlib.sha256,
    ).hexdigest()
    valida = hmac.compare_digest(signature, esperada)
    if not valida:
        logger.warning(f"Assinatura webhook invalida (recebida={signature[:12]}...)")
    return valida


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
@pluggy_bp.route("/", methods=["GET"])
@login_required
def painel():
    """Lista items conectados + acoes (sync manual, desconectar, re-conectar)."""
    ok, resp = _verificar_acesso()
    if not ok:
        return resp

    items = (
        PessoalPluggyItem.query
        .filter_by(client_user_id=str(current_user.id))
        .order_by(PessoalPluggyItem.criado_em.desc())
        .all()
    )
    # Coletar accounts agrupadas
    accounts_por_item = {
        it.id: PessoalPluggyAccount.query.filter_by(pluggy_item_pk=it.id).all()
        for it in items
    }
    return render_template(
        "pessoal/pluggy_painel.html",
        items=items,
        accounts_por_item=accounts_por_item,
    )


@pluggy_bp.route("/conectar", methods=["GET"])
@login_required
def conectar():
    """Pagina com widget Pluggy Connect."""
    ok, resp = _verificar_acesso()
    if not ok:
        return resp
    return render_template(
        "pessoal/pluggy_connect.html",
        include_sandbox=current_app.config.get("PLUGGY_INCLUDE_SANDBOX", False),
    )


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------
@pluggy_bp.route("/connect-token", methods=["POST"])
@login_required
def connect_token():
    """Gera connect_token (valido 30min) para o widget."""
    ok, resp = _verificar_acesso()
    if not ok:
        return resp
    try:
        client = get_pluggy_client()
        webhook_url = current_app.config.get("PLUGGY_WEBHOOK_URL")
        result = client.create_connect_token(
            client_user_id=str(current_user.id),
            webhook_url=webhook_url,
        )
        return jsonify({"accessToken": result.access_token}), 200
    except PluggyClientError as exc:
        logger.exception("Erro ao gerar connect_token")
        return jsonify({"erro": str(exc)}), 502


@pluggy_bp.route("/item-created", methods=["POST"])
@login_required
def item_created():
    """Callback JS apos onSuccess do widget.

    Payload esperado: {"itemId": "uuid"} ou {"item": {"id": "uuid", ...}}
    """
    ok, resp = _verificar_acesso()
    if not ok:
        return resp

    body = request.get_json(silent=True) or {}
    item_id = body.get("itemId") or (body.get("item") or {}).get("id")
    if not item_id:
        return jsonify({"erro": "itemId obrigatorio"}), 400

    client_user_id = str(current_user.id)

    # Cria registro local com status UPDATING
    item = PessoalPluggyItem.query.filter_by(pluggy_item_id=item_id).first()
    if item is None:
        item = PessoalPluggyItem(
            pluggy_item_id=item_id,
            client_user_id=client_user_id,
            connector_id=0,
            status="UPDATING",
        )
        db.session.add(item)
        db.session.commit()

    # Enfileira sync completo com polling (ALERTA 7)
    try:
        enqueue_job(
            "app.pessoal.workers.pluggy_sync_worker.processar_item_criado",
            item_id, client_user_id,
            queue_name="default",
            timeout="10m",
        )
    except Exception as exc:
        logger.exception(f"Erro ao enfileirar sync inicial item={item_id}")
        return jsonify({"erro": f"Erro enfileirando sync: {exc}"}), 500

    return jsonify({"ok": True, "itemPk": item.id, "redirect": url_for("pessoal.pessoal_pluggy.painel")}), 202


@pluggy_bp.route("/sync/<int:item_pk>", methods=["POST"])
@login_required
def sync_manual(item_pk: int):
    """Dispara sync manual de um item existente."""
    ok, resp = _verificar_acesso()
    if not ok:
        return resp

    item = db.session.get(PessoalPluggyItem, item_pk)
    if item is None or item.client_user_id != str(current_user.id):
        return jsonify({"erro": "Item nao encontrado"}), 404

    try:
        # Dispara update no Pluggy
        client = get_pluggy_client()
        client.trigger_item_update(item.pluggy_item_id)
        # Enfileira sync local apos Pluggy terminar
        enqueue_job(
            "app.pessoal.workers.pluggy_sync_worker.processar_item_criado",
            item.pluggy_item_id, item.client_user_id,
            queue_name="default",
            timeout="10m",
        )
    except PluggyClientError as exc:
        logger.exception(f"Erro trigger_item_update {item.pluggy_item_id}")
        return jsonify({"erro": str(exc)}), 502

    return jsonify({"ok": True, "mensagem": "Sync enfileirado"}), 202


@pluggy_bp.route("/disconnect/<int:item_pk>", methods=["POST"])
@login_required
def disconnect(item_pk: int):
    """Deleta item no Pluggy e no sistema local."""
    ok, resp = _verificar_acesso()
    if not ok:
        return resp

    item = db.session.get(PessoalPluggyItem, item_pk)
    if item is None or item.client_user_id != str(current_user.id):
        return jsonify({"erro": "Item nao encontrado"}), 404

    try:
        client = get_pluggy_client()
        client.delete_item(item.pluggy_item_id)
    except PluggyClientError as exc:
        logger.warning(f"Erro ao deletar item no Pluggy (seguindo mesmo assim): {exc}")

    # Remove local (CASCADE deleta accounts + transacoes_stg)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True}), 200


# ----------------------------------------------------------------------
# Webhook
# ----------------------------------------------------------------------
@pluggy_bp.route("/dry-run/<int:item_pk>", methods=["GET"])
@login_required
def dry_run_view(item_pk: int):
    """Pagina de dry-run comparativo."""
    ok, resp = _verificar_acesso()
    if not ok:
        return resp

    item = db.session.get(PessoalPluggyItem, item_pk)
    if item is None or item.client_user_id != str(current_user.id):
        return jsonify({"erro": "Item nao encontrado"}), 404

    limite = request.args.get("limite", type=int)
    resultado = dry_run_item(item_pk, limite=limite)
    return render_template(
        "pessoal/pluggy_dry_run.html",
        item=item,
        resultado=resultado,
    )


@pluggy_bp.route("/aprovar-lote/<int:item_pk>", methods=["POST"])
@login_required
def aprovar_lote(item_pk: int):
    """Marca todas as stg DRY_RUN de um item como APROVADO|REPROVADO|IGNORAR."""
    ok, resp = _verificar_acesso()
    if not ok:
        return resp

    item = db.session.get(PessoalPluggyItem, item_pk)
    if item is None or item.client_user_id != str(current_user.id):
        return jsonify({"erro": "Item nao encontrado"}), 404

    status = (request.form.get("status") or
              (request.get_json(silent=True) or {}).get("status") or "").upper()
    try:
        total = marcar_aprovacao_em_lote(item_pk, status)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400

    return jsonify({"ok": True, "total_marcadas": total, "status": status}), 200


@pluggy_bp.route("/aprovar/<int:stg_id>", methods=["POST"])
@login_required
def aprovar_uma(stg_id: int):
    """Aprovar/reprovar/ignorar uma stg individual."""
    ok, resp = _verificar_acesso()
    if not ok:
        return resp

    from app.pessoal.models import PessoalPluggyTransacaoStg
    stg = db.session.get(PessoalPluggyTransacaoStg, stg_id)
    if stg is None:
        return jsonify({"erro": "STG nao encontrada"}), 404
    # Verificar dono
    if stg.account.item.client_user_id != str(current_user.id):
        return jsonify({"erro": "Acesso negado"}), 403

    status = ((request.get_json(silent=True) or {}).get("status") or "").upper()
    try:
        marcar_aprovacao(stg_id, status)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400

    return jsonify({"ok": True, "status": status}), 200


@pluggy_bp.route("/merge/<int:item_pk>", methods=["POST"])
@login_required
def executar_merge(item_pk: int):
    """Merge: converte stg APROVADAS em PessoalTransacao reais."""
    ok, resp = _verificar_acesso()
    if not ok:
        return resp

    item = db.session.get(PessoalPluggyItem, item_pk)
    if item is None or item.client_user_id != str(current_user.id):
        return jsonify({"erro": "Item nao encontrado"}), 404

    try:
        resultado = merge_item(item_pk, auto_vincular=True)
    except Exception as exc:
        logger.exception(f"Erro no merge item_pk={item_pk}")
        return jsonify({"erro": str(exc)}), 500

    return jsonify({"ok": True, **resultado}), 200


@pluggy_bp.route("/webhook", methods=["POST"])
def webhook():
    """Endpoint PUBLICO (sem login) — Pluggy posta eventos aqui."""
    if not _validar_assinatura_webhook(request):
        return jsonify({"erro": "Assinatura invalida"}), 401

    event = request.get_json(silent=True) or {}
    event_type = event.get("event")
    item_id = event.get("itemId") or (event.get("item") or {}).get("id")

    logger.info(f"[webhook] event={event_type} item={item_id} id={event.get('eventId')}")

    # Marca timestamp do webhook
    if item_id:
        item = PessoalPluggyItem.query.filter_by(pluggy_item_id=item_id).first()
        if item:
            item.ultimo_webhook_em = agora_utc_naive()
            db.session.commit()

    # Processa async para responder < 5s (requisito Pluggy)
    def _process_async():
        try:
            if event_type in ("item/created", "item/login_succeeded"):
                enqueue_job(
                    "app.pessoal.workers.pluggy_sync_worker.processar_item_atualizado",
                    item_id,
                    queue_name="default",
                    timeout="10m",
                )
            elif event_type == "item/updated":
                enqueue_job(
                    "app.pessoal.workers.pluggy_sync_worker.processar_item_atualizado",
                    item_id,
                    queue_name="default",
                    timeout="10m",
                )
            elif event_type == "item/error":
                logger.error(f"Item {item_id} em erro: {event.get('error')}")
        except Exception as exc:
            logger.exception(f"Erro processando webhook async: {exc}")

    threading.Thread(target=_process_async, daemon=True).start()
    return jsonify({"received": True}), 200
