"""
Testes para o Capability Registry descritivo (S0c).

TDD: estes testes foram escritos ANTES da implementacao.
"""


def test_registry_skill_binding_n_para_m():
    from app.agente.config.capability_registry import build_registry
    reg = build_registry()
    assert reg.skills          # SkillEntry por skill
    assert reg.bindings        # arestas
    binds = [b for b in reg.bindings if b.skill_name == 'consultando-sql']
    assert len(binds) >= 2     # declarada por varios agentes — exposure e' aresta, nao escalar


def test_registry_principal_binding_presente():
    from app.agente.config.capability_registry import build_registry
    reg = build_registry()
    assert any(b.agent_name == 'principal' for b in reg.bindings)


def test_registry_skillentry_tem_flag_principal_coerente():
    from app.agente.config.capability_registry import build_registry
    reg = build_registry()
    # toda skill com binding ao principal deve ter available_to_principal=True
    princ = {b.skill_name for b in reg.bindings if b.agent_name == 'principal'}
    for e in reg.skills:
        if e.name in princ:
            assert e.available_to_principal is True


def test_flag_capability_registry_off_por_default(monkeypatch):
    monkeypatch.delenv("AGENT_CAPABILITY_REGISTRY", raising=False)
    import importlib
    from app.agente.config import feature_flags as ff
    importlib.reload(ff)
    assert ff.USE_CAPABILITY_REGISTRY is False
