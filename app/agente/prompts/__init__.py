"""
Prompts do Agente.
"""

from pathlib import Path


def get_system_prompt_path() -> Path:
    """Retorna caminho do system prompt."""
    return Path(__file__).parent / "system_prompt.md"


def load_system_prompt() -> str:
    """Carrega conteúdo do system prompt."""
    path = get_system_prompt_path()
    if path.exists():
        return path.read_text(encoding='utf-8')
    return ""


__all__ = ['get_system_prompt_path', 'load_system_prompt']
