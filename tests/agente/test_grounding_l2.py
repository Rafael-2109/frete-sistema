def test_l2_tem_grounding_de_estrutura():
    with open('app/agente/prompts/system_prompt.md', encoding='utf-8') as f:
        txt = f.read().lower()
    # ancoras UNICAS (grep=0 hoje): 'resolver' e 'nao encontrei' ja existem no prompt
    assert 'grounding de estrutura' in txt
    assert 'mcp__resolver' in txt
    assert 'nao prova inexistencia' in txt or 'não prova inexistência' in txt
