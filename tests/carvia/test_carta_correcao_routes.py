"""Rotas da Carta de Correção (CCe) CarVia — B4/C2 do plano.

Login via patch('flask_login.utils._get_user') (padrao do projeto).
"""
import io
from unittest.mock import patch, MagicMock

from app import db as _db


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.sistema_carvia = True
    u.perfil = 'administrador'
    u.email = 'test@bot'
    return u


def _nf(numero):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(numero_nf=numero, cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf)
    _db.session.flush()
    return nf


def test_upload_carta_correcao_na_nf(db, client):
    nf = _nf('8800')
    db.session.commit()
    data = {'arquivo': (io.BytesIO(b'%PDF-1.4 x'), 'cce.pdf'), 'descricao': 'corr'}
    with patch('flask_login.utils._get_user', return_value=_user()):
        resp = client.post(f'/carvia/api/carta-correcao/nf/{nf.id}/upload',
                           data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    assert resp.get_json()['sucesso'] is True
