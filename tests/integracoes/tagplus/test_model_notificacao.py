# tests/integracoes/tagplus/test_model_notificacao.py
"""Testa o model TagPlusNotificacaoWhatsapp (dedupe + defaults)."""
import pytest
from app import db
from app.integracoes.tagplus.models import TagPlusNotificacaoWhatsapp


def test_cria_registro_com_defaults(app):
    with app.app_context():
        reg = TagPlusNotificacaoWhatsapp(tipo="NFE", event_type="nfe_criada", tagplus_id="2659")
        db.session.add(reg)
        db.session.commit()
        assert reg.id is not None
        assert reg.status == "PENDENTE"
        assert reg.enviado_grupo is False
        assert reg.tentativas == 0
        db.session.delete(reg)
        db.session.commit()


def test_unique_tipo_id_event(app):
    with app.app_context():
        r1 = TagPlusNotificacaoWhatsapp(tipo="NFE", event_type="nfe_criada", tagplus_id="999")
        db.session.add(r1)
        db.session.commit()
        r2 = TagPlusNotificacaoWhatsapp(tipo="NFE", event_type="nfe_criada", tagplus_id="999")
        db.session.add(r2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()
        db.session.delete(r1)
        db.session.commit()
