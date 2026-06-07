"""Diretiva constitucional pinada — registro proativo de melhorias (inclusive casos sutis).

Promovida explicitamente por decisao do usuario (2026-06-06, sessao da fatura 161-9):
a regra de registrar atrito que impacta o agente — inclusive CASOS SUTIS — deve aparecer
SEMPRE como <operational_directive> (R0d), independente do effective_count das heuristicas
organicas (cap MANDATORY_MAX_COUNT=5; a heuristica 882 tinha effective_count=2, fora do top-5).

Espelha o setup de test_directives_status_filter.py (app_context modulo + rollback).
"""
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from app import create_app
from app.agente.sdk.memory_injection import _build_operational_directives

# Conteudo organico valido (nivel 5 + prescricao extraivel pelo builder).
_ORG_CONTENT = '<titulo>T</titulo><when>w</when><prescricao>faca x</prescricao><nivel>5</nivel>'


@pytest.fixture(scope='module')
def app_ctx():
    _app = create_app()
    _app.config.update({'TESTING': True, 'SQLALCHEMY_TRACK_MODIFICATIONS': False})
    with _app.app_context():
        yield _app


def _mock_candidates(fakes):
    """Mocka AgentMemory.query.filter(...).order_by(...).limit(...).all() -> fakes."""
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = fakes
    return patch('app.agente.models.AgentMemory.query', mock_query)


class TestConstitutionalDirective:
    def test_constitucional_presente_mesmo_sem_organicas(self, app_ctx):
        """Sem heuristicas organicas nivel-5, o builder antes retornava None.
        A diretiva constitucional de registro de melhorias deve aparecer mesmo assim."""
        with patch('app.agente.config.feature_flags.USE_OPERATIONAL_DIRECTIVES', True), \
             _mock_candidates([]):
            out = _build_operational_directives(user_id=5) or ''

        assert '<operational_directives' in out, f"bloco deveria existir. out={out!r}"
        assert '<directive id="registro-melhorias">' in out, (
            f"diretiva constitucional ausente. out={out!r}"
        )

    def test_constitucional_carrega_casos_sutis_e_principio(self, app_ctx):
        """A substancia acordada na sessao 161-9 precisa estar no texto: casos sutis,
        register_improvement como acao, e o principio de capacitacao (nao overhead)."""
        with patch('app.agente.config.feature_flags.USE_OPERATIONAL_DIRECTIVES', True), \
             _mock_candidates([]):
            out = (_build_operational_directives(user_id=5) or '').lower()

        assert 'sutis' in out, "deve mencionar casos SUTIS"
        assert 'register_improvement' in out, "deve citar a acao register_improvement"
        assert 'overhead' in out or 'proposito' in out, "deve carregar o principio de capacitacao"

    def test_constitucional_nao_reduz_as_5_organicas(self, app_ctx):
        """A constitucional eh EXTRA: nao pode comer slot das top-MANDATORY_MAX_COUNT organicas.
        Com 6 organicas, o bloco deve ter as 5 primeiras + a constitucional (6 no total)."""
        fakes = [SimpleNamespace(id=9000 + i, content=_ORG_CONTENT) for i in range(6)]
        with patch('app.agente.config.feature_flags.USE_OPERATIONAL_DIRECTIVES', True), \
             patch('app.agente.config.feature_flags.MANDATORY_MAX_COUNT', 5), \
             _mock_candidates(fakes):
            out = _build_operational_directives(user_id=5) or ''

        assert '<directive id="registro-melhorias">' in out, "constitucional deve estar presente"
        # 5 primeiras organicas presentes
        for i in range(5):
            assert f'<directive id="{9000 + i}">' in out, f"organica {9000 + i} deveria estar"
        # 6a organica cortada pelo cap
        assert '<directive id="9005">' not in out, "6a organica deveria ser cortada pelo cap=5"
