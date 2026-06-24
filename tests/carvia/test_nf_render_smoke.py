"""Smoke de RENDER do detalhe de NF CarVia tocado na consolidacao (Fase 0).

Render real (test client + login mock) — pega erro de Jinja/atributo que o unit test do
resolver nao pega. Cobre detalhe_nf, que passou a resolver o embarque pelo resolver canonico
`resolve_embarque_por_nf_ids` (antes usava so a via CarviaFrete e divergia da listagem).

NB: a LISTAGEM (listar_nfs) usa `db.session.query(...).paginate()`, que NAO roda sob a
TestingSession do conftest ('Query' object has no attribute 'paginate') — limitacao do
harness, nao do codigo. Por isso a listagem e' coberta pelos unit tests dos subqueries
(test_nf_listar_filtros) e do resolver (test_resolve_embarque_por_nf), nao por render aqui.
Login via patch('flask_login.utils._get_user') (padrao do projeto).
"""
import uuid
from unittest.mock import patch, MagicMock

from app.utils.timezone import agora_utc_naive
from tests.carvia._embarque_builders import (
    mk_transportadora, mk_embarque, mk_nf, mk_embarque_item, mk_operacao_frete,
)


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.sistema_carvia = True
    u.perfil = 'administrador'
    u.email = 'test@bot'
    return u


def test_detalhe_nf_render_embarque_via_item(db, client):
    """NF em embarque via EmbarqueItem CARVIA ativo (via a do resolver) -> detalhe renderiza."""
    transp = mk_transportadora(db)
    emb = mk_embarque(db, transp, data_embarque=agora_utc_naive().date())
    nf = mk_nf(db, 'NF-DET-' + uuid.uuid4().hex[:6])
    mk_embarque_item(db, emb, nf.numero_nf)
    db.session.commit()  # savepoint commit (revertido no teardown) — visivel ao request
    with patch('flask_login.utils._get_user', return_value=_user()):
        assert client.get(f'/carvia/nfs/{nf.id}').status_code == 200


def test_detalhe_nf_render_embarque_via_frete(db, client):
    """NF em embarque so via operacao->CarviaFrete (via b) -> detalhe renderiza (caso que
    antes divergia da listagem)."""
    transp = mk_transportadora(db)
    emb = mk_embarque(db, transp, data_embarque=agora_utc_naive().date())
    nf = mk_nf(db, 'NF-DEF-' + uuid.uuid4().hex[:6])
    mk_operacao_frete(db, transp, emb, nf)  # frete->embarque, sem EmbarqueItem
    db.session.commit()
    with patch('flask_login.utils._get_user', return_value=_user()):
        assert client.get(f'/carvia/nfs/{nf.id}').status_code == 200


def test_detalhe_nf_render_sem_embarque(db, client):
    """NF fora de qualquer embarque -> detalhe renderiza (embarque_nf None)."""
    nf = mk_nf(db, 'NF-DES-' + uuid.uuid4().hex[:6])
    db.session.commit()
    with patch('flask_login.utils._get_user', return_value=_user()):
        assert client.get(f'/carvia/nfs/{nf.id}').status_code == 200
