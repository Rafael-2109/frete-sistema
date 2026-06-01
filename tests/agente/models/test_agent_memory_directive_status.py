"""A4 — coluna directive_status em AgentMemory (candidata|shadow|ativa|despromovida)."""
import uuid
import pytest
from app import create_app, db
from app.agente.models import AgentMemory


@pytest.fixture(scope='module')
def app_ctx():
    """Flask app context para testes de modelo (escopo de módulo)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


class TestDirectiveStatusColumn:
    def test_coluna_existe_e_default_none(self, app_ctx):
        uid = uuid.uuid4().hex[:8]
        mem = AgentMemory(user_id=0,
                          path=f'/memories/empresa/heuristicas/t1-{uid}.xml',
                          content='<nivel>5</nivel><prescricao>x</prescricao>')
        db.session.add(mem)
        db.session.flush()
        assert mem.directive_status is None  # memória comum
        db.session.rollback()

    def test_aceita_os_quatro_estados(self, app_ctx):
        for st in ('candidata', 'shadow', 'ativa', 'despromovida'):
            uid = uuid.uuid4().hex[:8]
            mem = AgentMemory(user_id=0,
                              path=f'/memories/empresa/heuristicas/{st}-{uid}.xml',
                              content='<nivel>5</nivel><prescricao>x</prescricao>',
                              directive_status=st)
            db.session.add(mem)
            db.session.flush()
            assert mem.directive_status == st
            db.session.rollback()
