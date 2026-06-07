"""T1 (honestidade da observacao) — resolves_to nao penaliza o health_score do routing.

CONTEXTO (auditoria 2026-06-06): o indicador `resolves_to (KG)` aparecia "Morto" na tela e
PENALIZAVA 10pts do health_score do routing, porque mede uma relacao que o caminho-feliz do
produto quase nunca dispara (gatilho AND-triplo + system_prompt manda resolver sem perguntar).
Correcao: o score so conta os 3 indicadores REAIS (correction_count/effective_count/usage_count);
resolves_to vira informativo "nao_instrumentado", sem penalizar.
"""
from pathlib import Path

import pytest
from app import create_app

_TEMPLATE = Path('app/agente/templates/agente/insights.html')


def test_tela_resolves_to_e_experimental_nao_morto():
    """A tela nao trata mais resolves_to como indicador 'Ativo/Morto' do score;
    ele vira sinal experimental ('nao instrumentado'), sem alarme falso de 'Morto'."""
    html = _TEMPLATE.read_text(encoding='utf-8')
    assert "resolves_to_ativo: 'resolves_to (KG)'" not in html
    assert 'instrumentacao_experimental' in html


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


def test_score_instrumentacao_usa_so_indicadores_reais():
    """3 indicadores reais, todos ativos -> 40 (cheio). resolves_to NAO entra mais no score."""
    from app.agente.services.insights_service import _compute_routing_instrumentacao_score
    inst = {
        'correction_count_ativo': True,
        'effective_count_ativo': True,
        'usage_count_ativo': True,
    }
    assert _compute_routing_instrumentacao_score(inst) == 40.0


def test_score_instrumentacao_parcial():
    """2 de 3 ativos -> 2/3 * 40 ~ 26.67 (nao mais teto artificial de 30 por causa do resolves_to)."""
    from app.agente.services.insights_service import _compute_routing_instrumentacao_score
    inst = {
        'correction_count_ativo': True,
        'effective_count_ativo': True,
        'usage_count_ativo': False,
    }
    assert round(_compute_routing_instrumentacao_score(inst), 2) == 26.67


def test_routing_metrics_resolves_to_e_informativo_nao_penaliza(app):
    """get_routing_metrics: instrumentacao tem so os 3 reais; resolves_to vai p/ bloco experimental."""
    from app.agente.services.insights_service import get_routing_metrics
    data = get_routing_metrics(days=30, user_id=999999)  # usuario sem sessoes -> early return
    assert set(data['instrumentacao'].keys()) == {
        'correction_count_ativo', 'effective_count_ativo', 'usage_count_ativo'
    }
    assert 'resolves_to_ativo' not in data['instrumentacao']
    assert 'instrumentacao_experimental' in data
    rt = data['instrumentacao_experimental']['resolves_to']
    assert rt['status'] in ('nao_instrumentado', 'ativo')
