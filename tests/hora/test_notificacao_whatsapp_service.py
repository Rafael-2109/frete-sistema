"""Testa o service de notificação WhatsApp da HORA (sem rede)."""
from unittest.mock import patch, MagicMock
import pytest
from app import db
from app.auth.models import Usuario
from app.hora.models.tagplus import HoraTagPlusNotificacaoWhatsapp
from app.hora.services.tagplus import notificacao_whatsapp as svc


def test_resolver_vendedor_por_vinculado(app):
    with app.app_context():
        u = Usuario(nome="Vend HORA", email="vend.hora.test@x.com", perfil="vendedor",
                    status="ativo", telefone="11999990000", whatsapp_autorizado=True,
                    vendedor_vinculado="Vend HORA")
        u.set_senha("x"); db.session.add(u); db.session.commit()
        try:
            assert svc._resolver_vendedor("vend hora") is not None
            assert svc._resolver_vendedor("Inexistente ZZZ") is None
        finally:
            db.session.delete(db.session.get(Usuario, u.id)); db.session.commit()


def test_formatar_pedido_basico(app):
    with app.app_context():
        venda = MagicMock()
        venda.id = 9; venda.nome_cliente = "MERCADO X"; venda.vendedor = "João"
        venda.valor_total = 1200.50; venda.loja = MagicMock(nome="Loja Centro")
        venda.itens = []
        txt = svc._formatar_pedido(venda)
        assert "9" in txt and "MERCADO X" in txt and "1.200,50" in txt
        assert "|" not in txt  # sem tabela markdown


def test_processar_pedido_envia_grupo(app, monkeypatch):
    with app.app_context():
        venda = MagicMock()
        venda.id = 4321; venda.nome_cliente = "CLI"; venda.vendedor = None
        venda.valor_total = 100; venda.loja = None; venda.itens = []
        reg = HoraTagPlusNotificacaoWhatsapp(tipo="PEDIDO", ref_id=4321)
        db.session.add(reg); db.session.commit()
        rid = reg.id
        monkeypatch.setenv("HORA_TAGPLUS_NOTIFY_GROUP_JID", "120363@g.us")
        enviados = []
        with patch.object(svc, "_carregar_pedido", return_value=venda), \
             patch.object(svc, "_resolver_vendedor", return_value=None), \
             patch("app.hora.services.tagplus.notificacao_whatsapp.send_whatsapp",
                   side_effect=lambda t, x, **k: enviados.append(t) or {"ok": True}):
            svc.processar_notificacao(rid)
        reg = db.session.get(HoraTagPlusNotificacaoWhatsapp, rid)
        assert reg.status == "ENVIADO"
        assert reg.enviado_grupo is True
        assert reg.enviado_vendedor is None
        assert enviados == ["120363@g.us"]
        db.session.delete(reg); db.session.commit()


def test_kill_switch(app, monkeypatch):
    with app.app_context():
        reg = HoraTagPlusNotificacaoWhatsapp(tipo="PEDIDO", ref_id=4322)
        db.session.add(reg); db.session.commit()
        rid = reg.id
        monkeypatch.setenv("HORA_TAGPLUS_NOTIFY_ENABLED", "false")
        monkeypatch.setenv("HORA_TAGPLUS_NOTIFY_GROUP_JID", "120363@g.us")
        chamado = []
        with patch("app.hora.services.tagplus.notificacao_whatsapp.send_whatsapp",
                   side_effect=lambda *a, **k: chamado.append(1)):
            svc.processar_notificacao(rid)
        reg = db.session.get(HoraTagPlusNotificacaoWhatsapp, rid)
        assert reg.status == "IGNORADO"
        assert chamado == []
        db.session.delete(reg); db.session.commit()
