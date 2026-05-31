"""Onda 1 / D0 — nome de entidade nao deve reter sufixo :E/:A do parsing."""
from app.agente.services.knowledge_graph_service import parse_contextual_response


def test_parse_remove_sufixo_essencial_acidental_do_nome():
    texto = "RESPOSTA: ok\nENTIDADES: cliente:Atacadão:E|produto:Palmito:A"
    _resp, entidades, _rel = parse_contextual_response(texto)
    nomes = {e[1] for e in entidades}
    assert "Atacadão" in nomes, f"esperado nome limpo, veio {nomes}"
    assert "Palmito" in nomes
    assert not any(n.endswith(':E') or n.endswith(':A') for n in nomes), f"sufixo vazou: {nomes}"


def test_parse_preserva_dois_pontos_legitimo_no_nome():
    texto = "RESPOSTA: ok\nENTIDADES: atributo:prioridade:alta"
    _resp, entidades, _rel = parse_contextual_response(texto)
    nomes = {e[1] for e in entidades}
    assert "prioridade:alta" in nomes
