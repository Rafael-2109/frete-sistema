"""
Capability Registry — grafo descritivo read-only skill↔agente (S0c).

ESCOPO DESTA VERSAO (v1 — Onda 0)
----------------------------------
Descreve QUAIS skills sao acessiveis a QUAIS agentes (principal + subagentes)
via grafo N:M de SkillBinding. Fonte de verdade:
  - Subagentes: campo `skills:` no frontmatter de .claude/agents/*.md
  - Principal:  _discover_skills_from_project() (deny-list aplicada)

FORA DE ESCOPO (decisao consciente — nao implementar ate onda futura)
----------------------------------------------------------------------
  - 5 tabelas-catalogo de props intrinSecas de skills de estoque (F4/D2).
    O contrato falsificavel (grafo N:M) nao depende dessas tabelas extras.
  - Consumidores de runtime (nenhum codigo fora deste arquivo le o registry).
  - Persistencia em banco ou cache — registry e calculado on-demand, deterministico.

FLAG: USE_CAPABILITY_REGISTRY (feature_flags.py) e OFF por default.
Nenhum runtime consome o registry ainda; a flag marca a fundacao como inerte.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("sistema_fretes")


# ---------------------------------------------------------------------------
# Dataclasses (frozen = hasheavel, imutavel apos construcao)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SkillEntry:
    """Propriedades intrinsecas de uma skill (node do grafo)."""
    name: str
    description: str          # best-effort de SKILL.md; '' se ausente
    available_to_principal: bool  # True se name ∈ _discover_skills_from_project()


@dataclass(frozen=True)
class SkillBinding:
    """Aresta N:M entre skill e agente.

    A mesma skill gera multiplos bindings — um por agente que a declara.
    O principal entra como agent_name='principal'.
    Exposure e ARESTA, nao escalar.
    """
    skill_name: str
    agent_name: str


@dataclass(frozen=True)
class CapabilityRegistry:
    """Grafo completo skill↔agente.

    Imutavel apos construcao (frozen dataclass).
    Ordene skills/bindings por nome para estabilidade deterministica.
    """
    skills: tuple[SkillEntry, ...]
    bindings: tuple[SkillBinding, ...]

    def agents_for(self, skill_name: str) -> list[str]:
        """Retorna lista de agent_names que declaram a skill, ordenada."""
        return sorted({b.agent_name for b in self.bindings if b.skill_name == skill_name})

    def skills_for(self, agent_name: str) -> list[str]:
        """Retorna lista de skill_names declaradas pelo agente, ordenada."""
        return sorted({b.skill_name for b in self.bindings if b.agent_name == agent_name})


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _project_root() -> Path:
    """Root do projeto: capability_registry.py esta em app/agente/config/ = 4 parents."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _agents_dir() -> Path:
    return _project_root() / ".claude" / "agents"


def _skills_dir() -> Path:
    return _project_root() / ".claude" / "skills"


def _parse_frontmatter_safe(content: str) -> dict:
    """Parseia frontmatter YAML de um .md usando agent_loader._parse_frontmatter.

    Retorna dict vazio em caso de erro (best-effort — nao deve quebrar o registry).
    """
    try:
        # Reutiliza o parser canonico do projeto
        from app.agente.config.agent_loader import _parse_frontmatter
        fm, _ = _parse_frontmatter(content)
        return fm or {}
    except Exception as exc:
        logger.debug(f"[CAPABILITY_REGISTRY] _parse_frontmatter_safe falhou: {exc!r}")
        return {}


def _parse_skills_safe(skills_value) -> list[str]:
    """Parseia campo skills: do frontmatter — reutiliza _parse_skills do agent_loader."""
    if not skills_value:
        return []
    try:
        from app.agente.config.agent_loader import _parse_skills
        result = _parse_skills(skills_value)
        return result or []
    except Exception as exc:
        logger.debug(f"[CAPABILITY_REGISTRY] _parse_skills_safe falhou: {exc!r}")
        return []


def _read_skill_description(skill_name: str) -> str:
    """Le description do frontmatter de .claude/skills/<name>/SKILL.md.

    Retorna '' se arquivo ausente, frontmatter invalido, ou campo description ausente.
    Best-effort: nao deve lancar excecao.
    """
    skill_md = _skills_dir() / skill_name / "SKILL.md"
    if not skill_md.is_file():
        return ""
    try:
        content = skill_md.read_text(encoding="utf-8", errors="replace")
        fm = _parse_frontmatter_safe(content)
        desc = fm.get("description", "") or ""
        # description pode ser multiline YAML (str com \n); normalizar para string plana
        return str(desc).strip()
    except Exception as exc:
        logger.debug(f"[CAPABILITY_REGISTRY] _read_skill_description({skill_name!r}): {exc!r}")
        return ""


def _collect_principal_skills() -> list[str]:
    """Retorna skills do agente principal via _discover_skills_from_project().

    Retorna lista vazia se nao for possivel importar (e.g., fora do contexto Flask).
    Best-effort — nao deve quebrar o registry.
    """
    try:
        from app.agente.sdk.client import _discover_skills_from_project
        return list(_discover_skills_from_project())
    except Exception as exc:
        logger.debug(f"[CAPABILITY_REGISTRY] _collect_principal_skills falhou: {exc!r}")
        return []


def _collect_subagent_bindings() -> list[SkillBinding]:
    """Itera .claude/agents/*.md e gera um SkillBinding por (skill, agent).

    - agent_name: campo `name:` do frontmatter ou stem do arquivo como fallback.
    - skills: campo `skills:` parseado por _parse_skills.
    - Arquivos com erro sao logados e ignorados (nao bloqueiam os demais).
    """
    bindings: list[SkillBinding] = []
    agents_path = _agents_dir()

    if not agents_path.is_dir():
        logger.debug(f"[CAPABILITY_REGISTRY] Diretorio agents nao encontrado: {agents_path}")
        return bindings

    for agent_file in sorted(agents_path.glob("*.md")):
        try:
            content = agent_file.read_text(encoding="utf-8", errors="replace")
            fm = _parse_frontmatter_safe(content)
            agent_name = str(fm.get("name") or agent_file.stem).strip()
            skills = _parse_skills_safe(fm.get("skills"))
            for skill in skills:
                bindings.append(SkillBinding(skill_name=skill, agent_name=agent_name))
        except Exception as exc:
            logger.warning(
                f"[CAPABILITY_REGISTRY] Erro ao processar {agent_file.name}: {exc!r}"
            )

    return bindings


# ---------------------------------------------------------------------------
# Funcao principal
# ---------------------------------------------------------------------------

def build_registry() -> CapabilityRegistry:
    """Constroi o CapabilityRegistry a partir dos arquivos em disco.

    Algoritmo:
    a. Bindings de subagentes: .claude/agents/*.md → (skill, agent_name)
    b. Bindings do principal: _discover_skills_from_project() → (skill, 'principal')
    c. SkillEntry por skill_name unico: description best-effort, available_to_principal

    Deterministico: skills e bindings sao ordenados por (name/skill_name, agent_name).
    Read-only puro: sem DB, sem efeito colateral.
    """
    # a. Subagent bindings
    subagent_bindings = _collect_subagent_bindings()

    # b. Principal bindings
    principal_skills = _collect_principal_skills()
    principal_bindings = [
        SkillBinding(skill_name=s, agent_name="principal")
        for s in sorted(principal_skills)
    ]

    # Todos os bindings (sem duplicatas — mesma skill+agent pode existir uma vez)
    all_bindings_set: set[SkillBinding] = set(subagent_bindings) | set(principal_bindings)
    all_bindings: tuple[SkillBinding, ...] = tuple(
        sorted(all_bindings_set, key=lambda b: (b.skill_name, b.agent_name))
    )

    # c. SkillEntry por skill_name unico
    principal_skill_set: set[str] = set(principal_skills)
    all_skill_names: set[str] = {b.skill_name for b in all_bindings}

    skill_entries: tuple[SkillEntry, ...] = tuple(
        sorted(
            (
                SkillEntry(
                    name=name,
                    description=_read_skill_description(name),
                    available_to_principal=(name in principal_skill_set),
                )
                for name in all_skill_names
            ),
            key=lambda e: e.name,
        )
    )

    return CapabilityRegistry(skills=skill_entries, bindings=all_bindings)


# ---------------------------------------------------------------------------
# CLI de auditoria (python -m app.agente.config.capability_registry)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Adiciona root do projeto ao sys.path para importar app.*
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # Precisa de Flask app context para importar modelos SQLAlchemy (nao usados aqui)
    # mas _discover_skills_from_project() nao precisa — apenas leitura de arquivos.
    # Importacoes do agent_loader.py e client.py sao pure-Python (sem DB).

    reg = build_registry()

    # --- Resumo auditavel ---
    print(f"\n{'='*60}")
    print(f"  Capability Registry — resumo de auditoria")
    print(f"{'='*60}")
    print(f"  Skills totais (nodes):  {len(reg.skills)}")
    print(f"  Bindings totais (arestas): {len(reg.bindings)}")

    # Agentes distintos
    all_agents = sorted({b.agent_name for b in reg.bindings})
    print(f"  Agentes distintos:      {len(all_agents)}")
    print(f"  Lista de agentes:       {', '.join(all_agents)}")

    # Skills disponiveis ao principal
    principal_skills = [e for e in reg.skills if e.available_to_principal]
    print(f"\n  Skills disponíveis ao principal: {len(principal_skills)}")

    # Top 10 skills por numero de agentes (incluindo principal)
    from collections import Counter
    skill_counts = Counter(b.skill_name for b in reg.bindings)
    print(f"\n  Top 10 skills por numero de agentes:")
    for skill, count in skill_counts.most_common(10):
        agents = reg.agents_for(skill)
        print(f"    {skill:<40s}  {count:>3d} agente(s): {', '.join(agents)}")

    # Skills sem description (SKILL.md ausente ou sem campo description)
    no_desc = [e for e in reg.skills if not e.description]
    print(f"\n  Skills sem description (SKILL.md ausente/sem campo): {len(no_desc)}")
    for e in no_desc:
        print(f"    - {e.name}")

    print(f"{'='*60}\n")
