"""Testa a resolução do vendedor -> Usuario (whatsapp autorizado + ativo)."""
import pytest
from app import db
from app.auth.models import Usuario
from app.integracoes.tagplus.services import notificacao_whatsapp_service as svc


@pytest.fixture
def _cria_vendedor(app):
    with app.app_context():
        u = Usuario(
            nome="João Silva", email="joao.tagplus.test@x.com",
            perfil="vendedor", status="ativo",
            telefone="11999990000", whatsapp_autorizado=True,
            vendedor_vinculado="João Silva",
        )
        u.set_senha("x")
        db.session.add(u)
        db.session.commit()
        yield u.id
        db.session.delete(db.session.get(Usuario, u.id))
        db.session.commit()


def test_resolve_por_vendedor_vinculado(app, _cria_vendedor):
    with app.app_context():
        u = svc._resolver_vendedor("joão silva")
        assert u is not None
        assert u.telefone == "11999990000"


def test_nao_resolve_sem_whatsapp_autorizado(app):
    with app.app_context():
        u = Usuario(nome="Maria Sem Zap", email="maria.tagplus.test@x.com",
                    perfil="vendedor", status="ativo", telefone="11888880000",
                    whatsapp_autorizado=False, vendedor_vinculado="Maria Sem Zap")
        u.set_senha("x")
        db.session.add(u); db.session.commit()
        try:
            assert svc._resolver_vendedor("Maria Sem Zap") is None
        finally:
            db.session.delete(db.session.get(Usuario, u.id)); db.session.commit()


def test_nao_resolve_nome_inexistente(app):
    with app.app_context():
        assert svc._resolver_vendedor("Fulano Inexistente ZZZ") is None
