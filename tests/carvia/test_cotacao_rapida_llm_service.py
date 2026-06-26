"""cotacao_rapida_llm_service.extrair_motos_regiao — anthropic mockado (sem API).

Nao usa DB: passa modelos como SimpleNamespace (resolver_modelo_em_lista so le
.nome / .regex_pattern).
"""

import json
import types

import pytest

from app.carvia.services.parsers import cotacao_rapida_llm_service as llm


def _fake_client(payload):
    class _Messages:
        def create(self, **kwargs):
            return types.SimpleNamespace(
                content=[types.SimpleNamespace(text=payload)]
            )
    return types.SimpleNamespace(messages=_Messages())


def _modelos():
    return [
        types.SimpleNamespace(id=1, nome='X11 MINI', regex_pattern=None),
        types.SimpleNamespace(id=2, nome='DOT', regex_pattern=None),
    ]


def test_extrai_pdf_e_normaliza(monkeypatch):
    import anthropic
    payload = json.dumps({
        'motos': [
            {'modelo': 'X11 MINI', 'quantidade': 3},
            {'modelo': 'FOO DESCONHECIDO', 'quantidade': 2},
        ],
        'regiao': {'cidade': 'Sorocaba', 'uf': 'sp', 'cep': '18000-000'},
    })
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test')
    monkeypatch.setattr(anthropic, 'Anthropic', lambda api_key: _fake_client(payload))

    out = llm.extrair_motos_regiao(b'%PDF-1.4', 'application/pdf', _modelos())

    assert out['regiao'] == {'cidade': 'Sorocaba', 'uf': 'SP', 'cep': '18000-000'}
    assert len(out['motos']) == 2

    reconhecida = next(m for m in out['motos'] if m['reconhecido'])
    assert reconhecida['modelo_id'] == 1
    assert reconhecida['quantidade'] == 3

    nao_rec = next(m for m in out['motos'] if not m['reconhecido'])
    assert nao_rec['modelo_id'] is None
    assert nao_rec['texto_original'] == 'FOO DESCONHECIDO'


def test_extrai_imagem(monkeypatch):
    import anthropic
    payload = json.dumps({'motos': [{'modelo': 'DOT', 'quantidade': 1}],
                          'regiao': {'cidade': '', 'uf': '', 'cep': ''}})
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test')
    monkeypatch.setattr(anthropic, 'Anthropic', lambda api_key: _fake_client(payload))

    out = llm.extrair_motos_regiao(b'\xff\xd8\xff', 'image/jpeg', _modelos())
    assert out['motos'][0]['modelo_id'] == 2
    assert out['regiao'] == {'cidade': None, 'uf': None, 'cep': None}


def test_mime_invalido_levanta():
    with pytest.raises(llm.CotacaoRapidaLlmError):
        llm.extrair_motos_regiao(b'x', 'application/zip', _modelos())


def test_sem_api_key_levanta(monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    with pytest.raises(llm.CotacaoRapidaLlmError):
        llm.extrair_motos_regiao(b'x', 'application/pdf', _modelos())


def test_extrai_json_com_postambulo(monkeypatch):
    """Haiku às vezes adiciona texto APÓS o JSON ('Extra data') — deve parsear."""
    import anthropic
    payload = ('{"motos":[{"modelo":"DOT","quantidade":1}],"regiao":{}}'
               '\n\nEspero ter ajudado!')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test')
    monkeypatch.setattr(anthropic, 'Anthropic', lambda api_key: _fake_client(payload))
    out = llm.extrair_motos_regiao(b'%PDF-1.4', 'application/pdf', _modelos())
    assert out['motos'][0]['modelo_id'] == 2


def test_normaliza_estrutura_malformada_nao_quebra(monkeypatch):
    """motos=str e regiao=str (JSON válido, estrutura errada) degrada sem 500."""
    import anthropic
    payload = '{"motos":"NENHUMA","regiao":"Sao Paulo"}'
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test')
    monkeypatch.setattr(anthropic, 'Anthropic', lambda api_key: _fake_client(payload))
    out = llm.extrair_motos_regiao(b'%PDF-1.4', 'application/pdf', _modelos())
    assert out['motos'] == []
    assert out['regiao'] == {'cidade': None, 'uf': None, 'cep': None}


def test_mime_octet_stream_resolve_por_extensao_e_magic(monkeypatch):
    """mime do cliente vazio/octet-stream cai no fallback (extensão + magic bytes)."""
    import anthropic
    payload = '{"motos":[{"modelo":"DOT","quantidade":2}],"regiao":{}}'
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test')
    monkeypatch.setattr(anthropic, 'Anthropic', lambda api_key: _fake_client(payload))
    out = llm.extrair_motos_regiao(
        b'%PDF-1.4 conteudo', 'application/octet-stream', _modelos(), filename='pedido.pdf'
    )
    assert out['motos'][0]['quantidade'] == 2
