"""Testes do _try_parse_todos — parsing de tool_result do TodoWrite."""
import json
import pytest

from app.agente_lojas.sdk.client import _try_parse_todos


class TestTodosParser:
    def test_json_puro(self):
        text = json.dumps({
            "todos": [
                {"content": "A", "status": "completed", "activeForm": "Doing A"},
                {"content": "B", "status": "in_progress"},
                {"content": "C", "status": "pending"},
            ]
        })
        result = _try_parse_todos(text)
        assert result is not None
        assert len(result) == 3
        assert result[0]['status'] == 'completed'
        assert result[1]['status'] == 'in_progress'

    def test_json_aninhado_em_texto(self):
        text = 'Output: {"todos": [{"content": "X", "status": "pending"}]} done.'
        result = _try_parse_todos(text)
        assert result is not None
        assert len(result) == 1

    def test_texto_sem_todos_retorna_none(self):
        assert _try_parse_todos("Hello world") is None
        assert _try_parse_todos("Erro: arquivo nao encontrado") is None
        assert _try_parse_todos("status=ok") is None  # tem 'status' mas nao 'todos'

    def test_empty_inputs(self):
        assert _try_parse_todos('') is None
        assert _try_parse_todos(None) is None

    def test_json_invalido_retorna_none(self):
        # Tem palavras-chave mas nao eh JSON valido
        text = "todos: [unclosed status"
        assert _try_parse_todos(text) is None

    def test_todos_lista_vazia(self):
        text = json.dumps({"todos": []})
        result = _try_parse_todos(text)
        assert result == []

    def test_todos_com_outros_campos(self):
        """Estrutura real do TodoWrite pode ter campos extras."""
        text = json.dumps({
            "todos": [
                {
                    "content": "Verificar estoque",
                    "status": "completed",
                    "activeForm": "Verificando estoque",
                }
            ],
            "extra_field": "ignored"
        })
        result = _try_parse_todos(text)
        assert result is not None
        assert len(result) == 1
        assert result[0]['content'] == 'Verificar estoque'

    @pytest.mark.parametrize("text,expected_none", [
        ('{"todos":[]}', False),  # JSON puro
        ('  {"todos":[]}  ', False),  # com whitespace
        ('No JSON here', True),
        ('{"other":[]}', True),  # falta 'todos'
    ])
    def test_edge_cases(self, text, expected_none):
        result = _try_parse_todos(text)
        if expected_none:
            assert result is None
        else:
            assert result is not None
