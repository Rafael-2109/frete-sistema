"""
Testa a consolidação S0b: fonte única de verdade para a deny-list de skills.

Verifica:
(a) SKILLS_SPED_RESERVED existe, não é vazio, e é subconjunto de SKILLS_DELEGADAS_SUBAGENTE.
(b) As 4 skills SPED não aparecem no listing do principal (_discover_skills_from_project).
(c) Retrocompat: AgentSettings.SPED_SKILLS_RESERVED ainda == as 4 skills SPED (alias).
"""
import pytest

EXPECTED_SPED_SKILLS = frozenset({
    "parseando-sped-ecd",
    "auditando-sped-vs-manual",
    "auditando-sped-contabil",
    "comparando-sped-ground-truth",
})


def test_skills_sped_reserved_exists_and_nonempty():
    """(a-i) SKILLS_SPED_RESERVED deve existir em skills_whitelist e não ser vazio."""
    from app.agente.config.skills_whitelist import SKILLS_SPED_RESERVED
    assert isinstance(SKILLS_SPED_RESERVED, frozenset)
    assert len(SKILLS_SPED_RESERVED) > 0


def test_skills_sped_reserved_is_subset_of_delegadas():
    """(a-ii) SKILLS_SPED_RESERVED deve estar incluído em SKILLS_DELEGADAS_SUBAGENTE."""
    from app.agente.config.skills_whitelist import (
        SKILLS_SPED_RESERVED,
        SKILLS_DELEGADAS_SUBAGENTE,
    )
    assert SKILLS_SPED_RESERVED <= SKILLS_DELEGADAS_SUBAGENTE, (
        f"SKILLS_SPED_RESERVED não é subconjunto de SKILLS_DELEGADAS_SUBAGENTE. "
        f"Faltando: {SKILLS_SPED_RESERVED - SKILLS_DELEGADAS_SUBAGENTE}"
    )


def test_sped_skills_excluded_from_discover():
    """(b) As 4 skills SPED não devem aparecer em _discover_skills_from_project()."""
    # lru_cache: limpa para garantir que esta execução pega o código atualizado
    from app.agente.sdk.client import _discover_skills_from_project
    _discover_skills_from_project.cache_clear()
    skills = _discover_skills_from_project()
    assert isinstance(skills, list)
    for sped_skill in EXPECTED_SPED_SKILLS:
        assert sped_skill not in skills, (
            f"Vazamento S0b: '{sped_skill}' apareceu no listing do principal. "
            f"SKILLS_DELEGADAS_SUBAGENTE deve incluir SKILLS_SPED_RESERVED."
        )


def test_agent_settings_sped_skills_reserved_retrocompat():
    """(c) AgentSettings.SPED_SKILLS_RESERVED ainda igual às 4 skills SPED (alias retrocompat)."""
    from app.agente.config.settings import AgentSettings
    assert AgentSettings.SPED_SKILLS_RESERVED == EXPECTED_SPED_SKILLS, (
        f"Quebra de retrocompat: AgentSettings.SPED_SKILLS_RESERVED mudou. "
        f"Esperado: {EXPECTED_SPED_SKILLS}, encontrado: {AgentSettings.SPED_SKILLS_RESERVED}"
    )
