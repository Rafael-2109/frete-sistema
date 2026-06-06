# tests/integracoes/tagplus/test_processar_notificacao.py
"""Testa o processamento de uma notificação NF (com PDF) e os status de destino."""
from unittest.mock import MagicMock, patch

from app import db
from app.integracoes.tagplus.models import TagPlusNotificacaoWhatsapp
from app.integracoes.tagplus.services import notificacao_whatsapp_service as svc

NFE = {
    "numero": 3706, "serie": 1, "valor_nota": 100.0,
    "data_emissao": "2024-08-15", "destinatario": {"razao_social": "CLIENTE Y"},
    "itens": [], "pedido_os_vinculada": {"id": 77},
}
PEDIDO = {"numero": 9, "vendedor": {"nome": "João Silva"}}


def _registro(app, tipo="NFE", event="nfe_criada", tid="3706"):
    reg = TagPlusNotificacaoWhatsapp(tipo=tipo, event_type=event, tagplus_id=tid)
    db.session.add(reg); db.session.commit()
    return reg.id


def test_nf_envia_grupo_e_vendedor_com_pdf(app, monkeypatch):
    with app.app_context():
        rid = _registro(app)
        monkeypatch.setenv("TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID", "120363@g.us")
        enviados = []

        def fake_send(target, text, **kw):
            enviados.append((target, kw.get("anexo_b64") is not None))
            return {"ok": True}

        vendedor = MagicMock(); vendedor.telefone = "11999990000"; vendedor.id = 5
        vendedor.nome = "João Silva"

        with patch.object(svc, "_get_api"), \
             patch.object(svc, "_buscar_nfe_com_retry", return_value=NFE), \
             patch.object(svc, "_buscar_pedido", return_value=PEDIDO), \
             patch.object(svc, "_baixar_danfe_pdf", return_value=b"%PDF-1.4"), \
             patch.object(svc, "_resolver_vendedor", return_value=vendedor), \
             patch("app.integracoes.tagplus.services.notificacao_whatsapp_service.send_whatsapp", side_effect=fake_send):
            svc.processar_notificacao_async(app, rid)

        reg = db.session.get(TagPlusNotificacaoWhatsapp, rid)
        assert reg.status == "ENVIADO"
        assert reg.enviado_grupo is True
        assert reg.enviado_vendedor is True
        assert reg.anexou_pdf is True
        assert len(enviados) == 2
        assert all(tem_pdf for _, tem_pdf in enviados)
        db.session.delete(reg); db.session.commit()


def test_nf_sem_vendedor_so_grupo(app, monkeypatch):
    with app.app_context():
        rid = _registro(app, tid="3707")
        monkeypatch.setenv("TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID", "120363@g.us")

        with patch.object(svc, "_get_api"), \
             patch.object(svc, "_buscar_nfe_com_retry", return_value=NFE), \
             patch.object(svc, "_buscar_pedido", return_value=None), \
             patch.object(svc, "_baixar_danfe_pdf", return_value=None), \
             patch.object(svc, "_resolver_vendedor", return_value=None), \
             patch("app.integracoes.tagplus.services.notificacao_whatsapp_service.send_whatsapp", return_value={"ok": True}):
            svc.processar_notificacao_async(app, rid)

        reg = db.session.get(TagPlusNotificacaoWhatsapp, rid)
        assert reg.status == "ENVIADO"
        assert reg.enviado_grupo is True
        assert reg.enviado_vendedor is None
        db.session.delete(reg); db.session.commit()


def test_reenvio_parcial_nao_duplica_grupo(app, monkeypatch):
    """Reenvio de PARCIAL (grupo OK, vendedor falhou) só re-tenta o vendedor."""
    with app.app_context():
        # Cleanup idempotente — evita UniqueViolation em re-execuções
        stale = TagPlusNotificacaoWhatsapp.query.filter_by(
            tipo="NFE", tagplus_id="88888", event_type="nfe_criada"
        ).first()
        if stale:
            db.session.delete(stale); db.session.commit()

        reg = TagPlusNotificacaoWhatsapp(
            tipo="NFE", event_type="nfe_criada", tagplus_id="88888",
            enviado_grupo=True, enviado_vendedor=False, status="PARCIAL",
        )
        db.session.add(reg); db.session.commit()
        rid = reg.id
        monkeypatch.setenv("TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID", "120363@g.us")
        enviados = []

        def fake_send(target, text, **kw):
            enviados.append(target); return {"ok": True}

        vendedor = MagicMock(); vendedor.telefone = "11999990000"; vendedor.id = 5

        with patch.object(svc, "_get_api"), \
             patch.object(svc, "_buscar_nfe_com_retry", return_value=NFE), \
             patch.object(svc, "_buscar_pedido", return_value=PEDIDO), \
             patch.object(svc, "_baixar_danfe_pdf", return_value=None), \
             patch.object(svc, "_resolver_vendedor", return_value=vendedor), \
             patch("app.integracoes.tagplus.services.notificacao_whatsapp_service.send_whatsapp", side_effect=fake_send):
            svc.processar_notificacao_async(app, rid)

        # processar_notificacao_async usa contexto aninhado com sessão própria;
        # expire_all força re-leitura do banco (evita cache da identity map).
        db.session.expire_all()
        reg = db.session.get(TagPlusNotificacaoWhatsapp, rid)
        assert reg.status == "ENVIADO"
        assert reg.enviado_grupo is True
        assert reg.enviado_vendedor is True
        assert enviados == ["11999990000"]  # só o vendedor; grupo NÃO foi reenviado
        db.session.delete(reg); db.session.commit()


def test_kill_switch_ignora_sem_enviar(app, monkeypatch):
    """TAGPLUS_NOTIFY_ENABLED=false -> status IGNORADO, nada enviado."""
    with app.app_context():
        # Cleanup idempotente — evita UniqueViolation em re-execuções
        stale = TagPlusNotificacaoWhatsapp.query.filter_by(
            tipo="NFE", tagplus_id="99999", event_type="nfe_criada"
        ).first()
        if stale:
            db.session.delete(stale); db.session.commit()

        reg = TagPlusNotificacaoWhatsapp(tipo="NFE", event_type="nfe_criada", tagplus_id="99999")
        db.session.add(reg); db.session.commit()
        rid = reg.id
        monkeypatch.setenv("TAGPLUS_NOTIFY_ENABLED", "false")
        monkeypatch.setenv("TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID", "120363@g.us")
        chamado = []

        with patch.object(svc, "_get_api"), \
             patch("app.integracoes.tagplus.services.notificacao_whatsapp_service.send_whatsapp",
                   side_effect=lambda *a, **k: chamado.append(1)):
            svc.processar_notificacao_async(app, rid)

        # processar_notificacao_async usa contexto aninhado com sessão própria;
        # expire_all força re-leitura do banco (evita cache da identity map).
        db.session.expire_all()
        reg = db.session.get(TagPlusNotificacaoWhatsapp, rid)
        assert reg.status == "IGNORADO"
        assert chamado == []
        db.session.delete(reg); db.session.commit()
