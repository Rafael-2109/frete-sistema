"""8b passo 1: sdk_session_id POR PAPEL em AgentSession.

Decisao de arquitetura #1: cada papel (principal, gestor-recebimento) tem seu
proprio sdk_session_id, em data['sdk_session_ids'][role]. Sem isso, principal e
especialista resumiriam o MESMO sdk_session_id e escreveriam na MESMA chave do
PostgresSessionStore (project_key, session_id=sdk_session_id, subpath='') ->
corrupcao do transcript.

Retrocompat (export-critico): role default 'principal'; leitura dual da string
legada data['sdk_session_id']; escrita de 'principal' espelha a string legada
(Teams/WhatsApp e a rotacao de sessao leem sem passar role).
"""
from app import db
from app.agente.models import AgentSession


def test_default_principal_ausente_retorna_none(app):
    with app.app_context():
        s = AgentSession(session_id='t-sid-1', user_id=1, data={})
        assert s.get_sdk_session_id() is None
        assert s.get_sdk_session_id(role='gestor-recebimento') is None


def test_papeis_isolados(app):
    with app.app_context():
        s = AgentSession(session_id='t-sid-2', user_id=1, data={})
        s.set_sdk_session_id('uuid-principal', role='principal')
        s.set_sdk_session_id('uuid-especialista', role='gestor-recebimento')
        assert s.get_sdk_session_id(role='principal') == 'uuid-principal'
        assert s.get_sdk_session_id(role='gestor-recebimento') == 'uuid-especialista'
        # set de um papel NAO afeta o outro
        s.set_sdk_session_id('uuid-principal-2', role='principal')
        assert s.get_sdk_session_id(role='gestor-recebimento') == 'uuid-especialista'


def test_leitura_dual_legado_mapeia_para_principal(app):
    with app.app_context():
        # Sessao em andamento gravada ANTES do 8b: so a string legada.
        s = AgentSession(session_id='t-sid-3', user_id=1,
                         data={'sdk_session_id': 'uuid-legado'})
        assert s.get_sdk_session_id() == 'uuid-legado'
        assert s.get_sdk_session_id(role='principal') == 'uuid-legado'
        # Especialista NAO herda o uuid do principal (senao a colisao volta).
        assert s.get_sdk_session_id(role='gestor-recebimento') is None


def test_escrita_principal_espelha_slot_legado(app):
    with app.app_context():
        # Retrocompat: leitores antigos (Teams/WhatsApp, rotacao) leem a string.
        s = AgentSession(session_id='t-sid-4', user_id=1, data={})
        s.set_sdk_session_id('uuid-x', role='principal')
        assert s.data['sdk_session_id'] == 'uuid-x'
        # Escrita de especialista NAO toca o slot legado.
        s.set_sdk_session_id('uuid-esp', role='gestor-recebimento')
        assert s.data['sdk_session_id'] == 'uuid-x'


def test_default_sem_role_continua_principal(app):
    with app.app_context():
        # Chamada legada (Teams/WhatsApp) sem role -> opera no slot principal.
        s = AgentSession(session_id='t-sid-5', user_id=1, data={})
        s.set_sdk_session_id('uuid-default')
        assert s.get_sdk_session_id() == 'uuid-default'
        assert s.get_sdk_session_id(role='principal') == 'uuid-default'


def test_clear_none_principal(app):
    with app.app_context():
        s = AgentSession(session_id='t-sid-6', user_id=1, data={})
        s.set_sdk_session_id('uuid-y', role='principal')
        s.set_sdk_session_id(None, role='principal')
        assert s.get_sdk_session_id(role='principal') is None
        assert s.data['sdk_session_id'] is None


def test_persiste_com_flag_modified(app):
    with app.app_context():
        s = AgentSession(session_id='t-sid-7', user_id=1, data={})
        db.session.add(s)
        s.set_sdk_session_id('uuid-persist', role='gestor-recebimento')
        db.session.commit()
    with app.app_context():
        r = AgentSession.query.filter_by(session_id='t-sid-7').first()
        assert r.get_sdk_session_id(role='gestor-recebimento') == 'uuid-persist'
        AgentSession.query.filter_by(session_id='t-sid-7').delete()
        db.session.commit()


def test_preserva_outras_chaves_de_data(app):
    with app.app_context():
        s = AgentSession(session_id='t-sid-8', user_id=1,
                         data={'messages': [1, 2], 'agente_ativo': 'gestor-recebimento'})
        s.set_sdk_session_id('uuid-z', role='gestor-recebimento')
        assert s.data['messages'] == [1, 2]
        assert s.data['agente_ativo'] == 'gestor-recebimento'
        assert s.get_sdk_session_id(role='gestor-recebimento') == 'uuid-z'
