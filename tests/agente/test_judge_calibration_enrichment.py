"""Enriquecimento dos casos de calibracao do judge: usuario + pergunta + resposta.

Antes a tela de spot-check so mostrava a `evidence` resumida do judge (truncada em
160 no front, sem usuario) -> nao dava para avaliar se o judge acertou. Agora
_enrich_calibration_cases resolve case_id (=step_uid) -> AgentStep -> AgentSession e
injeta user_name/pergunta/resposta; o template ganha coluna Usuario + linha expansivel.
"""
from pathlib import Path

import pytest

from app import create_app, db
from app.auth.models import Usuario
from app.agente.models import AgentSession, AgentStep
from app.agente.services.insights_service import _enrich_calibration_cases

TEMPLATE = Path('app/agente/templates/agente/insights.html')


# ───────────── wiring do template (deterministico, sem DB) ─────────────

@pytest.fixture(scope='module')
def html():
    return TEMPLATE.read_text(encoding='utf-8')


def test_coluna_usuario_no_thead(html):
    assert '<th>Usuario</th>' in html


def test_linha_expansivel_wired(html):
    assert 'function toggleJudgeDetail(' in html
    assert 'judgeDetail-' in html
    assert 'onclick="toggleJudgeDetail(' in html


def test_js_le_campos_enriquecidos(html):
    for campo in ('c.user_name', 'c.pergunta', 'c.resposta'):
        assert campo in html, f'JS nao le {campo}'


def test_colspan_atualizado_para_5_colunas(html):
    # apos adicionar a coluna Usuario, os estados vazios cobrem 5 colunas
    assert 'colspan="5"' in html


# ───────────── enriquecimento backend (com DB) ─────────────

@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture
def cenario(app):
    """Usuario + AgentSession (1 turno) + AgentStep; limpa no fim (auto-contido)."""
    sid = 'test_judge_enrich_sess'
    user = Usuario.query.filter_by(email='test_judge_enrich@test.com').first()
    if not user:
        user = Usuario(email='test_judge_enrich@test.com', nome='Revisor Teste',
                       perfil='agente', status='ativo')
        user.set_senha('test_password_123')
        db.session.add(user)
        db.session.commit()

    def _wipe():
        AgentStep.query.filter_by(step_uid=f'{sid}:1').delete()
        AgentSession.query.filter_by(session_id=sid).delete()
        db.session.commit()

    _wipe()
    session = AgentSession.get_or_create(session_id=sid, user_id=user.id)
    if isinstance(session, tuple):  # get_or_create -> (obj, created)
        session = session[0]
    session.add_user_message('quanto de palmito tem em estoque?')
    session.add_assistant_message('Ha 1.234 caixas de palmito disponiveis.')
    db.session.commit()

    step = AgentStep(step_uid=f'{sid}:1', session_id=sid, user_id=user.id)
    db.session.add(step)
    db.session.commit()

    yield user, sid
    _wipe()


def test_enrich_injeta_usuario_pergunta_resposta(app, cenario):
    user, sid = cenario
    casos = [{'case_id': f'{sid}:1', 'evidence': 'label=success score=80 | ...'}]
    _enrich_calibration_cases(casos)
    c = casos[0]
    assert c.get('user_name') == 'Revisor Teste'
    assert 'palmito' in (c.get('pergunta') or '')
    assert '1.234' in (c.get('resposta') or '')


def test_enrich_degrada_sem_step(app):
    # case_id inexistente -> best-effort: nao quebra e nao enriquece
    casos = [{'case_id': 'inexistente:99', 'evidence': 'x'}]
    _enrich_calibration_cases(casos)
    assert 'user_name' not in casos[0]
