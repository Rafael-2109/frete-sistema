from app import db
from app.agente.models import AgentSession


def test_default_principal_quando_ausente(app):
    with app.app_context():
        s = AgentSession(session_id='t-ativo-1', user_id=1, data={})
        assert s.get_agente_ativo() == 'principal'

def test_set_persiste_com_flag_modified(app):
    with app.app_context():
        s = AgentSession(session_id='t-ativo-2', user_id=1, data={})
        db.session.add(s)
        s.set_agente_ativo('gestor-recebimento')
        db.session.commit()
    with app.app_context():
        r = AgentSession.query.filter_by(session_id='t-ativo-2').first()
        assert r.get_agente_ativo() == 'gestor-recebimento'
        AgentSession.query.filter_by(session_id='t-ativo-2').delete()
        db.session.commit()

def test_set_preserva_outras_chaves_de_data(app):
    with app.app_context():
        s = AgentSession(session_id='t-ativo-3', user_id=1,
                         data={'sdk_session_id': 'abc', 'messages': [1, 2]})
        s.set_agente_ativo('gestor-recebimento')
        assert s.data['sdk_session_id'] == 'abc'
        assert s.data['messages'] == [1, 2]
        assert s.data['agente_ativo'] == 'gestor-recebimento'
