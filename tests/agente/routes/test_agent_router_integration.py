from unittest.mock import patch
from app import db
from app.agente.models import AgentSession
from app.agente.routes.chat import _resolve_agent_role


def test_shadow_decide_e_persiste_mas_nao_troca(app):
    with app.app_context():
        db.session.add(AgentSession(session_id='ari-1', user_id=1, data={}))
        db.session.commit()
        with patch('app.agente.config.feature_flags.resolve_specialist_handoff_mode',
                   return_value='shadow'):
            role_efetivo = _resolve_agent_role(
                session_id='ari-1', message='vincular pedido C1 na nota 48862 pelo odoo',
                is_admin=False)
        assert role_efetivo == 'principal'   # shadow nao troca
        r = AgentSession.query.filter_by(session_id='ari-1').first()
        assert r.get_agente_ativo() == 'gestor-recebimento'   # decisao registrada
        AgentSession.query.filter_by(session_id='ari-1').delete(); db.session.commit()


def test_on_troca_para_especialista(app):
    with app.app_context():
        db.session.add(AgentSession(session_id='ari-2', user_id=1, data={}))
        db.session.commit()
        with patch('app.agente.config.feature_flags.resolve_specialist_handoff_mode',
                   return_value='on'):
            role_efetivo = _resolve_agent_role(
                session_id='ari-2', message='vincular pedido C1 na nota 48862 pelo odoo',
                is_admin=False)
        assert role_efetivo == 'gestor-recebimento'
        AgentSession.query.filter_by(session_id='ari-2').delete(); db.session.commit()
