"""Tests para deteccao de linguagem prescritiva -> priority=mandatory."""
import pytest
from app import create_app
from app.agente.services.pattern_analyzer import _is_mandatory_trigger


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


def test_sempre_trigger_is_mandatory(app):
    assert _is_mandatory_trigger("SEMPRE usar Excel para relatorios") is True


def test_nunca_trigger_is_mandatory(app):
    assert _is_mandatory_trigger("NUNCA use tabela local") is True


def test_rejeitar_trigger_is_mandatory(app):
    assert _is_mandatory_trigger("Rejeitar HTML sem consultar") is True


def test_formato_travado_is_mandatory(app):
    assert _is_mandatory_trigger("O formato esta travado em 4 abas") is True


def test_nao_aceito_is_mandatory(app):
    assert _is_mandatory_trigger("nao aceito variacao de layout") is True


def test_descricao_not_mandatory(app):
    assert _is_mandatory_trigger("Marcus prefere Excel") is False


def test_observacao_not_mandatory(app):
    assert _is_mandatory_trigger("Este cliente pagou ontem") is False


def test_pergunta_not_mandatory(app):
    assert _is_mandatory_trigger("Qual e o formato esperado?") is False


def test_empty_string_returns_false(app):
    assert _is_mandatory_trigger("") is False


def test_none_returns_false(app):
    assert _is_mandatory_trigger(None) is False
