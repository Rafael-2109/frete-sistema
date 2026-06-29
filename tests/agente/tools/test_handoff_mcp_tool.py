# tests/agente/tools/test_handoff_mcp_tool.py
from app import db
from app.agente.models import AgentSession
from app.agente.tools.handoff_mcp_tool import (
    _apply_transfer, _apply_devolver, handoff_server,
    transferir_para, devolver_ao_principal, should_register_handoff)


def test_handoff_server_registra_duas_tools():
    assert handoff_server is not None
    # Asserta DE FATO as 2 tools (nome promete, agora verifica).
    nomes = {transferir_para.name, devolver_ao_principal.name}
    assert nomes == {"transferir_para", "devolver_ao_principal"}


def test_should_register_handoff_so_principal_e_on():
    # off / shadow: NAO registra (off=inerte; shadow=medicao PURA, sem tool de troca).
    assert should_register_handoff('off', None) is False
    assert should_register_handoff('shadow', None) is False
    # on, cliente PRINCIPAL (specialist_profile None): registra (prepara o swap 8b).
    assert should_register_handoff('on', None) is True
    # ESPECIALISTA (specialist_profile != None): NUNCA recebe transferir_para
    # (usa o executor atomico, nao re-delega) — nem em on.
    assert should_register_handoff('on', object()) is False
    assert should_register_handoff('shadow', object()) is False

def test_apply_transfer_persiste_ativo_e_contexto(app):
    with app.app_context():
        db.session.add(AgentSession(session_id='hx-1', user_id=1, data={}))
        db.session.commit()
        out = _apply_transfer('hx-1', 'gestor-recebimento',
                              objetivo='vincular NF 48862 ao PO C2615437',
                              entidades={'nf': '48862', 'po': 'C2615437'}, saldo=None)
        assert out['ok'] is True
        r = AgentSession.query.filter_by(session_id='hx-1').first()
        assert r.get_agente_ativo() == 'gestor-recebimento'
        assert r.data['handoff_context']['entidades']['nf'] == '48862'
        AgentSession.query.filter_by(session_id='hx-1').delete()
        db.session.commit()

def test_apply_transfer_sem_sessao_retorna_erro(app):
    with app.app_context():
        out = _apply_transfer('nao-existe', 'gestor-recebimento', objetivo='x', entidades={})
        assert out['ok'] is False

def test_apply_devolver_volta_ao_principal(app):
    with app.app_context():
        s = AgentSession(session_id='hx-2', user_id=1,
                         data={'agente_ativo': 'gestor-recebimento',
                               'handoff_context': {'objetivo': 'x'}})
        db.session.add(s)
        db.session.commit()
        out = _apply_devolver('hx-2')
        assert out['ok'] is True
        r = AgentSession.query.filter_by(session_id='hx-2').first()
        assert r.get_agente_ativo() == 'principal'
        assert 'handoff_context' not in (r.data or {})
        AgentSession.query.filter_by(session_id='hx-2').delete()
        db.session.commit()
