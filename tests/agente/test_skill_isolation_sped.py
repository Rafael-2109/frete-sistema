"""Testa que skills SPED ficam invisíveis ao agente principal Nacom."""
from app.agente.config.settings import AgentSettings
from app.agente.sdk.client import _discover_skills_from_project


def test_sped_skills_reserved_constant_complete():
    """Garantir que a constante cobre as 4 skills planejadas."""
    expected = {
        "parseando-sped-ecd",
        "auditando-sped-vs-manual",
        "auditando-sped-contabil",
        "comparando-sped-ground-truth",
    }
    assert AgentSettings.SPED_SKILLS_RESERVED == expected


def test_discover_skills_excludes_sped():
    """_discover_skills_from_project() deve retornar lista sem SPED skills."""
    all_skills = _discover_skills_from_project()
    assert isinstance(all_skills, list)
    assert len(all_skills) > 0
    for sped_skill in AgentSettings.SPED_SKILLS_RESERVED:
        assert sped_skill not in all_skills, \
            f"Skill {sped_skill} deve estar excluída do listing principal"
