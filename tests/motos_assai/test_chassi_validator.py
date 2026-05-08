from app import db
from app.motos_assai.models import AssaiModelo
from app.motos_assai.services import validar_chassi


def test_chassi_vazio():
    r = validar_chassi('', None)
    assert r['ok'] is False
    assert 'vazio' in r['mensagem']


def test_modelo_none(app):
    with app.app_context():
        r = validar_chassi('LA12345', None)
        assert r['ok'] is True


def test_modelo_sem_regex(app):
    """Modelo cadastrado mas sem regex_chassi → passa com aviso."""
    with app.app_context():
        m = AssaiModelo(codigo='TESTE_NO_REGEX', nome='T', regex_chassi=None)
        db.session.add(m); db.session.flush()
        r = validar_chassi('XYZ', m.id)
        assert r['ok'] is True
        assert 'sem regex' in r['mensagem']
        db.session.rollback()


def test_chassi_bate_regex(app):
    with app.app_context():
        m = AssaiModelo(codigo='TESTE_DOT_RX', nome='T', regex_chassi=r'LA\d+')
        db.session.add(m); db.session.flush()
        r = validar_chassi('LA12345', m.id)
        assert r['ok'] is True
        db.session.rollback()


def test_chassi_nao_bate_regex(app):
    with app.app_context():
        m = AssaiModelo(codigo='TESTE_DOT_RX2', nome='T', regex_chassi=r'LA\d+')
        db.session.add(m); db.session.flush()
        r = validar_chassi('XX99', m.id)
        assert r['ok'] is False
        assert 'não bate' in r['mensagem']
        db.session.rollback()


def test_anchors_aplicados_se_faltam(app):
    """Regex 'LA\\d+' sem anchors deve ser tratado como '^LA\\d+$'."""
    with app.app_context():
        m = AssaiModelo(codigo='TESTE_ANCHOR', nome='T', regex_chassi=r'LA\d+')
        db.session.add(m); db.session.flush()
        # 'XLA123' contém 'LA123' mas anchored não bate
        r = validar_chassi('XLA123', m.id)
        assert r['ok'] is False
        db.session.rollback()
