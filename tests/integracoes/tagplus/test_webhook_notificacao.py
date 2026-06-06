"""Testa o endpoint de webhook de notificação (dedupe, parsing, assinatura)."""
import json
from unittest.mock import patch

from app import db
from app.integracoes.tagplus.models import TagPlusNotificacaoWhatsapp
from app.integracoes.tagplus.webhook_routes import WEBHOOK_SECRET

URL = "/integracoes/tagplus/webhook/notificacao"


def _payload(event="nfe_criada", tid="3706"):
    return {"event_type": event, "data": [{"id": tid}]}


def test_assinatura_invalida_401(client):
    r = client.post(URL, json=_payload(), headers={"X-Hub-Secret": "errado"})
    assert r.status_code == 401


def test_cria_registro_e_dispara_thread(client, app):
    with patch("app.integracoes.tagplus.webhook_notificacao_routes.disparar_thread") as disp:
        r = client.post(URL, json=_payload(tid="55555"),
                        headers={"X-Hub-Secret": WEBHOOK_SECRET})
    assert r.status_code == 200
    assert disp.called
    with app.app_context():
        reg = TagPlusNotificacaoWhatsapp.query.filter_by(tipo="NFE", tagplus_id="55555").first()
        assert reg is not None
        db.session.delete(reg); db.session.commit()


def test_dedupe_nao_duplica(client, app):
    with patch("app.integracoes.tagplus.webhook_notificacao_routes.disparar_thread"):
        client.post(URL, json=_payload(tid="66666"), headers={"X-Hub-Secret": WEBHOOK_SECRET})
        client.post(URL, json=_payload(tid="66666"), headers={"X-Hub-Secret": WEBHOOK_SECRET})
    with app.app_context():
        regs = TagPlusNotificacaoWhatsapp.query.filter_by(tipo="NFE", tagplus_id="66666").all()
        assert len(regs) == 1
        for r in regs:
            db.session.delete(r)
        db.session.commit()


def test_evento_fora_do_escopo_ignorado(client):
    with patch("app.integracoes.tagplus.webhook_notificacao_routes.disparar_thread") as disp:
        r = client.post(URL, json=_payload(event="produto_criado", tid="1"),
                        headers={"X-Hub-Secret": WEBHOOK_SECRET})
    assert r.status_code == 200
    assert not disp.called


def test_sem_assinatura_401(client):
    r = client.post(URL, json=_payload(tid="77777"))  # sem X-Hub-Secret
    assert r.status_code == 401
