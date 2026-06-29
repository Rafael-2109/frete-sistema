"""Perfis de especialista quente (F1). Piloto: gestor-recebimento.

Cada SpecialistProfile descreve o cliente ESPECIALISTA de um papel: o prompt
de sistema proprio (substitui o do principal) e a allow-list de skills que o
papel pode usar. Consumido por client._build_options(specialist_profile=...)
e pelo agent_router (routes/chat.py:_resolve_agent_role).
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field

_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


@dataclass(frozen=True)
class SpecialistProfile:
    role: str
    system_prompt_path: str
    skills: list[str] = field(default_factory=list)


SPECIALIST_PROFILES: dict[str, SpecialistProfile] = {
    "gestor-recebimento": SpecialistProfile(
        role="gestor-recebimento",
        system_prompt_path=os.path.join(_PROMPTS_DIR, "especialista_recebimento.md"),
        skills=["validacao-nf-po", "conciliando-odoo-po", "rastreando-odoo",
                "resolvendo-entidades"],
    ),
}
