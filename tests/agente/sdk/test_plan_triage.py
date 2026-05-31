"""
Testes do classificador semântico B-TRIAGE (Onda 2).

B-TRIAGE: dada uma META do usuário, decompõe em steps de plano, ancorando em
entidades reais do KG via query_ontology_entities.

SHADOW: nenhum caller ativo. O wiring futuro (sob USE_AGENT_PLANNER)
alimentaria o PlanState com os steps retornados.

Cobertura:
- test_triage_retorna_steps_e_grounded_entities:
    LLM retorna JSON com steps + ontologia retorna 1 entidade → ambos presentes no resultado.
- test_triage_degrada_quando_llm_falha:
    LLM levanta exceção → degrada gracioso: steps=[], grounded_entities=[].
- test_triage_meta_vazia_nao_chama_nada:
    meta vazia/None → retorna estrutura vazia SEM chamar LLM ou ontologia.
- test_triage_degrada_quando_json_invalido:
    LLM retorna string não-JSON → degrada gracioso: steps=[], grounded_entities=[].
- test_triage_sem_entidades_ontologia:
    query_ontology_entities retorna [] → steps ainda retornados (grounded_entities=[]).
- test_triage_estrutura_retorno:
    Verifica que o retorno sempre tem 'steps' e 'grounded_entities' como listas.
- test_parse_triage_json_valido:
    _parse_triage_json com JSON válido retorna dict com 'steps'.
- test_parse_triage_json_invalido:
    _parse_triage_json com string não-JSON retorna None.
- test_parse_triage_json_sem_chave_steps:
    _parse_triage_json sem chave 'steps' retorna None.
- test_call_llm_triage_mockavel:
    Confirma que _call_llm_triage é mockável (não chama API real quando mockado).
"""

import json

import pytest


# ─── Fixtures ───────────────────────────────────────────────────────────────

META_CONSULTA = "Quero ver todos os pedidos do Atacadao em aberto esta semana"
META_TRANSFERENCIA = "Transferir 100 unidades de palmito do lote MIGRACAO para o lote real"

_STEPS_JSON_OK = json.dumps({
    "steps": [
        {"subject": "Consultar pedidos em aberto do cliente Atacadao", "entities": ["ATACADAO DISTRIBUIDORA"]},
        {"subject": "Filtrar por data da semana atual", "entities": []},
    ]
})

_ENTITY_ATACADAO = {
    "entity_type": "cliente",
    "entity_name": "ATACADAO DISTRIBUIDORA",
    "entity_key": "75315333",
    "user_id": 0,
}


# ─── Testes de triage_meta ───────────────────────────────────────────────────

def test_triage_retorna_steps_e_grounded_entities(monkeypatch):
    """LLM retorna JSON com steps + ontologia retorna 1 entidade → ambos presentes."""
    from app.agente.sdk import plan_triage

    monkeypatch.setattr(plan_triage, '_call_llm_triage', lambda prompt: _STEPS_JSON_OK)
    monkeypatch.setattr(
        plan_triage,
        'query_ontology_entities',
        lambda user_id, **kwargs: [_ENTITY_ATACADAO],
    )

    result = plan_triage.triage_meta(META_CONSULTA, user_id=42)

    assert 'steps' in result
    assert 'grounded_entities' in result
    assert isinstance(result['steps'], list)
    assert len(result['steps']) >= 1
    assert isinstance(result['grounded_entities'], list)
    assert len(result['grounded_entities']) >= 1


def test_triage_degrada_quando_llm_falha(monkeypatch):
    """Exceção no LLM → best-effort: steps=[], grounded_entities=[]."""
    from app.agente.sdk import plan_triage

    def _explode(prompt):
        raise RuntimeError("Timeout de API simulado")

    monkeypatch.setattr(plan_triage, '_call_llm_triage', _explode)
    monkeypatch.setattr(
        plan_triage,
        'query_ontology_entities',
        lambda user_id, **kwargs: [_ENTITY_ATACADAO],
    )

    # Não deve levantar exceção
    result = plan_triage.triage_meta(META_CONSULTA, user_id=42)

    assert result['steps'] == []
    assert result['grounded_entities'] == []


def test_triage_meta_vazia_nao_chama_nada(monkeypatch):
    """meta vazia → retorna vazio SEM chamar LLM ou ontologia."""
    from app.agente.sdk import plan_triage

    chamadas_llm = []
    chamadas_ontologia = []

    def _llm_espiao(prompt):
        chamadas_llm.append(prompt)
        return _STEPS_JSON_OK

    def _ontologia_espiao(user_id, **kwargs):
        chamadas_ontologia.append(user_id)
        return [_ENTITY_ATACADAO]

    monkeypatch.setattr(plan_triage, '_call_llm_triage', _llm_espiao)
    monkeypatch.setattr(plan_triage, 'query_ontology_entities', _ontologia_espiao)

    for meta_vazia in ('', None, '   '):
        result = plan_triage.triage_meta(meta_vazia, user_id=42)
        assert result['steps'] == []
        assert result['grounded_entities'] == []

    assert chamadas_llm == [], "LLM não deve ser chamado com meta vazia"
    assert chamadas_ontologia == [], "Ontologia não deve ser chamada com meta vazia"


def test_triage_degrada_quando_json_invalido(monkeypatch):
    """LLM retorna string não-JSON → degrada gracioso."""
    from app.agente.sdk import plan_triage

    monkeypatch.setattr(plan_triage, '_call_llm_triage', lambda prompt: "Desculpe, não entendi.")
    monkeypatch.setattr(
        plan_triage,
        'query_ontology_entities',
        lambda user_id, **kwargs: [],
    )

    result = plan_triage.triage_meta(META_CONSULTA, user_id=42)

    assert result['steps'] == []
    assert result['grounded_entities'] == []


def test_triage_sem_entidades_ontologia(monkeypatch):
    """ontologia retorna [] → steps ainda retornados (grounded_entities=[])."""
    from app.agente.sdk import plan_triage

    monkeypatch.setattr(plan_triage, '_call_llm_triage', lambda prompt: _STEPS_JSON_OK)
    monkeypatch.setattr(
        plan_triage,
        'query_ontology_entities',
        lambda user_id, **kwargs: [],
    )

    result = plan_triage.triage_meta(META_CONSULTA, user_id=42)

    assert isinstance(result['steps'], list)
    assert len(result['steps']) >= 1
    assert result['grounded_entities'] == []


def test_triage_estrutura_retorno(monkeypatch):
    """Resultado sempre tem 'steps' e 'grounded_entities' como listas."""
    from app.agente.sdk import plan_triage

    monkeypatch.setattr(plan_triage, '_call_llm_triage', lambda prompt: _STEPS_JSON_OK)
    monkeypatch.setattr(
        plan_triage,
        'query_ontology_entities',
        lambda user_id, **kwargs: [_ENTITY_ATACADAO],
    )

    result = plan_triage.triage_meta(META_TRANSFERENCIA, user_id=1)

    assert set(result.keys()) >= {'steps', 'grounded_entities'}
    assert isinstance(result['steps'], list)
    assert isinstance(result['grounded_entities'], list)
    # Cada step deve ter ao menos 'subject'
    for step in result['steps']:
        assert 'subject' in step


def test_triage_degrada_quando_ontologia_falha(monkeypatch):
    """Exceção na ontologia → best-effort: triage ainda retorna steps (sem entidades)."""
    from app.agente.sdk import plan_triage

    monkeypatch.setattr(plan_triage, '_call_llm_triage', lambda prompt: _STEPS_JSON_OK)

    def _ontologia_falha(user_id, **kwargs):
        raise RuntimeError("DB timeout simulado")

    monkeypatch.setattr(plan_triage, 'query_ontology_entities', _ontologia_falha)

    # Não deve levantar exceção
    result = plan_triage.triage_meta(META_CONSULTA, user_id=42)

    # Degrada: steps podem estar presentes ou não (best-effort), mas estrutura ok
    assert 'steps' in result
    assert 'grounded_entities' in result
    assert isinstance(result['steps'], list)
    assert isinstance(result['grounded_entities'], list)


# ─── Testes de helpers internos ──────────────────────────────────────────────

def test_parse_triage_json_valido():
    """_parse_triage_json com JSON válido retorna dict com 'steps'."""
    from app.agente.sdk.plan_triage import _parse_triage_json

    json_str = json.dumps({"steps": [{"subject": "Consultar pedidos"}]})
    result = _parse_triage_json(json_str)

    assert result is not None
    assert 'steps' in result
    assert isinstance(result['steps'], list)


def test_parse_triage_json_invalido():
    """_parse_triage_json com string não-JSON retorna None."""
    from app.agente.sdk.plan_triage import _parse_triage_json

    result = _parse_triage_json("não é JSON")
    assert result is None


def test_parse_triage_json_sem_chave_steps():
    """_parse_triage_json sem chave 'steps' retorna None."""
    from app.agente.sdk.plan_triage import _parse_triage_json

    json_str = json.dumps({"other_key": "value"})
    result = _parse_triage_json(json_str)
    assert result is None


def test_parse_triage_json_vazio():
    """_parse_triage_json com string vazia ou None retorna None."""
    from app.agente.sdk.plan_triage import _parse_triage_json

    assert _parse_triage_json('') is None
    assert _parse_triage_json(None) is None


def test_parse_triage_json_com_prefixo_sufixo():
    """_parse_triage_json tolera texto antes/depois do JSON."""
    from app.agente.sdk.plan_triage import _parse_triage_json

    raw = 'Aqui está o plano:\n{"steps": [{"subject": "Consultar"}]}\nObrigado!'
    result = _parse_triage_json(raw)

    assert result is not None
    assert 'steps' in result


def test_call_llm_triage_mockavel(monkeypatch):
    """Confirma que _call_llm_triage é mockável (sem chamar API real)."""
    from app.agente.sdk import plan_triage

    chamadas = []

    def _mock_llm(prompt: str) -> str:
        chamadas.append(prompt)
        return _STEPS_JSON_OK

    monkeypatch.setattr(plan_triage, '_call_llm_triage', _mock_llm)
    monkeypatch.setattr(
        plan_triage,
        'query_ontology_entities',
        lambda user_id, **kwargs: [],
    )

    plan_triage.triage_meta(META_CONSULTA, user_id=42)

    assert len(chamadas) == 1, "_call_llm_triage deve ser chamado exatamente 1 vez"
    # Prompt deve conter a meta original
    assert META_CONSULTA in chamadas[0] or 'atacadao' in chamadas[0].lower()
