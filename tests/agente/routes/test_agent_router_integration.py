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


def test_on_decide_especialista_mas_swap_e_8b(app):
    # 'on' RETORNA o especialista (decisao), mas o swap real do stream e' 8b
    # (deferido) — hoje o stream continua no principal. O nome reflete isso.
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


def test_off_nao_toca_db_nem_router(app):
    # Invariante #1 (ships inerte em flag-off): em 'off' o _resolve_agent_role faz
    # early-return 'principal' ANTES de consultar o router ou persistir no DB.
    with app.app_context():
        db.session.add(AgentSession(session_id='ari-off', user_id=1, data={}))
        db.session.commit()
        with patch('app.agente.config.feature_flags.resolve_specialist_handoff_mode',
                   return_value='off'), \
             patch('app.agente.sdk.agent_router.select_specialist') as mock_sel:
            role = _resolve_agent_role(
                session_id='ari-off', message='vincular pedido C1 na nota 48862 pelo odoo',
                is_admin=False)
        assert role == 'principal'
        mock_sel.assert_not_called()                      # router NAO consultado em off
        r = AgentSession.query.filter_by(session_id='ari-off').first()
        assert r.get_agente_ativo() == 'principal'        # nada persistido
        AgentSession.query.filter_by(session_id='ari-off').delete(); db.session.commit()
