"""
Testes TDD para verify_domain (B2-domain, Onda 2).

Cobertura:
- test_verify_domain_entidade_conhecida: entidade encontrada na ontologia → ok=True, issues=[]
- test_verify_domain_entidade_desconhecida: entidade NÃO encontrada → ok=False, issue com nome da entidade
- test_verify_domain_step_sem_entidades: step sem campo 'entities' e sem 'subject' → ok=True (nada a checar)
- test_verify_domain_step_subject_sem_entidades: step com 'subject' sem termos úteis → ok=True
- test_verify_domain_erro_consulta: exception em query_ontology_entities → best-effort ok=True, issues=[]
- test_verify_domain_multiplas_entidades_misto: uma conhecida, uma desconhecida → ok=False, só desconhecida em issues
- test_verify_domain_entidades_campo_direto: step com campo 'entities' lista → valida cada uma
- test_verify_domain_extra_checks_hook: extra_checks=[fn] → fn é invocado (hook extensível)
"""

# ─── Fixtures de steps ────────────────────────────────────────────────────────

STEP_COM_ENTIDADES = {
    "action": "consultar_pedidos",
    "subject": "pedidos do Atacadão",
    "entities": ["Atacadão", "SP"],
}

STEP_SEM_ENTITIES_COM_SUBJECT = {
    "action": "calcular_frete",
    "subject": "calcular frete para Manaus",
}

STEP_VAZIO = {
    "action": "dummy_action",
}

STEP_ENTIDADE_DESCONHECIDA = {
    "action": "consultar_cliente",
    "entities": ["CLIENTE_FANTASMA_XYZ"],
}

STEP_MULTIPLAS_ENTIDADES = {
    "action": "verificar_estoque",
    "entities": ["Atacadão", "PRODUTO_INEXISTENTE_999"],
}


# ─── Helper para mock de retorno da ontologia ─────────────────────────────────



def _ontologia_vazia(*args, **kwargs):
    """Sempre retorna lista vazia — entidade desconhecida."""
    return []


def _ontologia_erro(*args, **kwargs):
    """Simula falha na consulta."""
    raise RuntimeError("DB connection timeout simulado")


# ─── Testes ───────────────────────────────────────────────────────────────────

def test_verify_domain_entidade_conhecida(monkeypatch):
    """Entidade encontrada na ontologia → ok=True, issues=[]."""
    from app.agente.sdk import verifiers
    import app.agente.tools.ontology_query_tool as oqt

    # Retorna resultado positivo para qualquer busca
    def _retorna_resultado(user_id, **kwargs):
        return [{"entity_type": "cliente", "entity_name": "ATACADAO",
                 "entity_key": "75315333", "user_id": 0}]

    monkeypatch.setattr(oqt, "query_ontology_entities", _retorna_resultado)

    result = verifiers.verify_domain(STEP_COM_ENTIDADES, user_id=42)

    assert result["ok"] is True
    assert result["issues"] == []


def test_verify_domain_entidade_desconhecida(monkeypatch):
    """Entidade NÃO encontrada na ontologia → ok=False, issue menciona o nome."""
    from app.agente.sdk import verifiers
    import app.agente.tools.ontology_query_tool as oqt

    monkeypatch.setattr(oqt, "query_ontology_entities", _ontologia_vazia)

    result = verifiers.verify_domain(STEP_ENTIDADE_DESCONHECIDA, user_id=42)

    assert result["ok"] is False
    assert len(result["issues"]) > 0
    # Issue deve mencionar o nome da entidade desconhecida
    assert any("CLIENTE_FANTASMA_XYZ" in issue for issue in result["issues"])


def test_verify_domain_step_sem_entidades(monkeypatch):
    """Step sem campo 'entities' e sem 'subject' → ok=True, sem consulta à ontologia."""
    from app.agente.sdk import verifiers
    import app.agente.tools.ontology_query_tool as oqt

    chamadas = []

    def _registra_chamada(user_id, **kwargs):
        chamadas.append(kwargs)
        return []

    monkeypatch.setattr(oqt, "query_ontology_entities", _registra_chamada)

    result = verifiers.verify_domain(STEP_VAZIO, user_id=42)

    # Sem entidades a validar → ok=True (nada violado)
    assert result["ok"] is True
    assert result["issues"] == []


def test_verify_domain_step_subject_sem_entidades(monkeypatch):
    """Step com apenas 'subject' textual → extrai termos ou ignora, mas não falha."""
    from app.agente.sdk import verifiers
    import app.agente.tools.ontology_query_tool as oqt

    # Mesmo que a ontologia retorne vazio para termos do subject,
    # o comportamento deve ser best-effort (não impede o plano)
    # A implementação pode não extrair termos do subject, retornando ok=True
    monkeypatch.setattr(oqt, "query_ontology_entities", _ontologia_vazia)

    result = verifiers.verify_domain(STEP_SEM_ENTITIES_COM_SUBJECT, user_id=42)

    # Sem 'entities' explícito → sem validação obrigatória → ok=True
    assert result["ok"] is True
    assert isinstance(result["issues"], list)


def test_verify_domain_erro_consulta(monkeypatch):
    """Exception em query_ontology_entities → best-effort: ok=True, issues=[] (não propaga)."""
    from app.agente.sdk import verifiers
    import app.agente.tools.ontology_query_tool as oqt

    monkeypatch.setattr(oqt, "query_ontology_entities", _ontologia_erro)

    # NÃO deve levantar exceção
    result = verifiers.verify_domain(STEP_ENTIDADE_DESCONHECIDA, user_id=42)

    assert result["ok"] is True
    assert result["issues"] == []


def test_verify_domain_multiplas_entidades_misto(monkeypatch):
    """Uma entidade conhecida, uma desconhecida → ok=False, somente desconhecida em issues."""
    from app.agente.sdk import verifiers
    import app.agente.tools.ontology_query_tool as oqt

    def _retorna_seletivo(user_id, **kwargs):
        name_like = kwargs.get("name_like", "")
        if "atacadão" in name_like.lower() or "atacadao" in name_like.lower():
            return [{"entity_type": "cliente", "entity_name": "ATACADAO",
                     "entity_key": "75315333", "user_id": 0}]
        return []

    monkeypatch.setattr(oqt, "query_ontology_entities", _retorna_seletivo)

    result = verifiers.verify_domain(STEP_MULTIPLAS_ENTIDADES, user_id=42)

    assert result["ok"] is False
    # Só a entidade desconhecida deve aparecer nos issues
    assert any("PRODUTO_INEXISTENTE_999" in issue for issue in result["issues"])
    # Atacadão é conhecida — não deve aparecer como issue
    assert not any("Atacadão" in issue or "ATACADAO" in issue for issue in result["issues"])


def test_verify_domain_entidades_campo_direto(monkeypatch):
    """step['entities'] lista → cada item é validado individualmente."""
    from app.agente.sdk import verifiers
    import app.agente.tools.ontology_query_tool as oqt

    chamadas_name_like = []

    def _captura_chamadas(user_id, **kwargs):
        if "name_like" in kwargs:
            chamadas_name_like.append(kwargs["name_like"])
        return []  # vazio = desconhecida

    monkeypatch.setattr(oqt, "query_ontology_entities", _captura_chamadas)

    step = {"action": "test", "entities": ["EntA", "EntB", "EntC"]}
    result = verifiers.verify_domain(step, user_id=1)

    # Deve ter consultado cada entidade
    assert len(chamadas_name_like) == 3
    assert "EntA" in chamadas_name_like
    assert "EntB" in chamadas_name_like
    assert "EntC" in chamadas_name_like
    # Todas desconhecidas → ok=False com 3 issues
    assert result["ok"] is False
    assert len(result["issues"]) == 3


def test_verify_domain_extra_checks_hook(monkeypatch):
    """extra_checks=[fn] → fn é chamado, resultado incorporado aos issues."""
    from app.agente.sdk import verifiers
    import app.agente.tools.ontology_query_tool as oqt

    # Ontologia encontra tudo (nenhum issue ontológico)
    def _retorna_resultado(user_id, **kwargs):
        return [{"entity_type": "produto", "entity_name": "X",
                 "entity_key": "123", "user_id": 0}]

    monkeypatch.setattr(oqt, "query_ontology_entities", _retorna_resultado)

    # Hook extra que sempre adiciona uma issue
    def _check_extra(step, user_id):
        return ["check extra: entidade fora de escopo"]

    step = {"action": "test", "entities": ["X"]}
    result = verifiers.verify_domain(step, user_id=1, extra_checks=[_check_extra])

    # ok=False porque o hook extra adicionou issue
    assert result["ok"] is False
    assert any("check extra" in issue for issue in result["issues"])


def test_verify_domain_step_none():
    """Step None → ok=True sem propagar (guard de entrada)."""
    from app.agente.sdk import verifiers

    result = verifiers.verify_domain(None, user_id=42)

    assert result["ok"] is True
    assert result["issues"] == []
