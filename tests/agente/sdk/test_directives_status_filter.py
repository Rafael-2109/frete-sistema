"""A4 — _build_operational_directives injeta só directive_status NULL (legado) OU 'ativa'.

Espelha setup de tests/agente/models/test_agent_eval_score.py: módulo-escopo app_ctx
que entra no app_context e faz teardown garantido (rollback) APÓS o yield, de modo
que linhas inseridas não vazam para o Postgres compartilhado mesmo se o corpo do
teste levantar antes de um rollback manual.
"""
import uuid
from unittest.mock import patch

import pytest

from app import create_app, db as _db
from app.agente.models import AgentMemory
from app.agente.sdk.memory_injection import _build_operational_directives

_CONTENT = '<titulo>T</titulo><when>w</when><prescricao>faça x</prescricao><nivel>5</nivel>'


@pytest.fixture(scope='module')
def app_ctx():
    """Flask app context para o teste (escopo de módulo)."""
    _app = create_app()
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with _app.app_context():
        yield _app


@pytest.fixture
def rollback_session():
    """Garante rollback da sessão no teardown (mesmo se o teste levantar)."""
    yield
    _db.session.rollback()


def _mk(slug, status):
    m = AgentMemory(
        user_id=0,
        path=f'/memories/empresa/heuristicas/{slug}.xml',
        content=_CONTENT,
        importance_score=0.9,
        directive_status=status,
    )
    _db.session.add(m)
    return m


class TestDirectiveStatusFilter:
    def test_shadow_e_despromovida_excluidos_ativa_e_null_injetam(self, app_ctx, rollback_session):
        uid = uuid.uuid4().hex[:8]
        leg = _mk(f'leg-{uid}', None)       # legado → injeta
        atv = _mk(f'atv-{uid}', 'ativa')    # ativa → injeta
        shd = _mk(f'shd-{uid}', 'shadow')   # shadow → NÃO
        dep = _mk(f'dep-{uid}', 'despromovida')  # despromovida → NÃO
        _db.session.flush()

        leg_id, atv_id, shd_id, dep_id = leg.id, atv.id, shd.id, dep.id

        with patch('app.agente.config.feature_flags.USE_OPERATIONAL_DIRECTIVES', True):
            out = _build_operational_directives(user_id=5) or ''

        # Legado e ativa devem aparecer no output
        assert f'<directive id="{leg_id}">' in out, (
            f"legado (id={leg_id}) deveria estar no output, mas não está. out={out!r}"
        )
        assert f'<directive id="{atv_id}">' in out, (
            f"ativa (id={atv_id}) deveria estar no output, mas não está. out={out!r}"
        )

        # Shadow e despromovida devem ser excluídos
        assert f'<directive id="{shd_id}">' not in out, (
            f"shadow (id={shd_id}) NÃO deveria estar no output, mas está. out={out!r}"
        )
        assert f'<directive id="{dep_id}">' not in out, (
            f"despromovida (id={dep_id}) NÃO deveria estar no output, mas está. out={out!r}"
        )
