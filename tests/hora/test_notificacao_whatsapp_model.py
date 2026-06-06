"""Testa o model HoraTagPlusNotificacaoWhatsapp (defaults + dedupe)."""
import pytest
from app import db
from app.hora.models.tagplus import HoraTagPlusNotificacaoWhatsapp


def test_cria_com_defaults(app):
    with app.app_context():
        reg = HoraTagPlusNotificacaoWhatsapp(tipo="NFE", ref_id=123)
        db.session.add(reg); db.session.commit()
        assert reg.id is not None
        assert reg.status == "PENDENTE"
        assert reg.enviado_grupo is False
        assert reg.tentativas == 0
        db.session.delete(reg); db.session.commit()


def test_unique_tipo_ref(app):
    with app.app_context():
        r1 = HoraTagPlusNotificacaoWhatsapp(tipo="PEDIDO", ref_id=999)
        db.session.add(r1); db.session.commit()
        r2 = HoraTagPlusNotificacaoWhatsapp(tipo="PEDIDO", ref_id=999)
        db.session.add(r2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()
        db.session.delete(r1); db.session.commit()
