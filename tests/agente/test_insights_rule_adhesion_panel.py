"""O0.3 — painel 'Adesao de Regras' (loop corretivo) no dashboard de insights.

O backend ja injeta `data.rule_adhesion` (insights_service.get_insights_data ->
_get_rule_adhesion_section). Este teste garante o WIRING das camadas estaticas do
template `insights.html`: os elementos DOM existem e o JS (renderAll -> renderRuleAdhesion)
os popula a partir de `data.rule_adhesion`. DoD do card: a pagina mostra a tabela
error_signature x antes/depois.
"""
from pathlib import Path

import pytest

TEMPLATE = Path('app/agente/templates/agente/insights.html')


@pytest.fixture(scope='module')
def html():
    return TEMPLATE.read_text(encoding='utf-8')


def test_render_all_chama_render_rule_adhesion(html):
    # renderAll precisa despachar a secao a partir de data.rule_adhesion
    assert 'renderRuleAdhesion(data.rule_adhesion' in html
    assert 'function renderRuleAdhesion(' in html


def test_tabela_antes_depois_existe(html):
    # DoD: tabela error_signature x antes/depois
    assert 'id="ruleAdhesionTable"' in html
    assert '>Antes<' in html
    assert '>Depois<' in html


def test_ids_do_painel_existem_no_dom(html):
    # Todo getElementById/setText usado por renderRuleAdhesion precisa ter
    # contrapartida no HTML estatico (senao a camada DOM falta silenciosamente).
    for el_id in (
        'ruleAdhesionTable',
        'ruleAdhesionMandatoryPct',
        'ruleAdhesionTotal',
        'ruleAdhesionMandatory',
        'ruleAdhesionHarmful',
        'ruleAdhesionHelpful',
        'ruleAdhesionContidas',
        'ruleAdhesionReincidindo',
        'ruleAdhesionPromovidas',
        'ruleAdhesionTaxaContencao',
    ):
        assert f'id="{el_id}"' in html, f'falta elemento DOM id={el_id}'


def test_contencao_wired(html):
    # contencao retroativa: o JS le data.rule_adhesion.contencao e popula o DOM
    assert 'ra.contencao' in html
    assert 'contidas' in html
