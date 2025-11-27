"""
Prompts centralizados do Claude AI Lite.

ARQUITETURA DE PROMPTS (27/11/2025):
- PROMPT 1 (Classificação): intelligent_extractor.py
- PROMPT 2 (Planejamento): agent_planner.py
- PROMPT 3 (Resposta): system_base.py

FUNÇÕES ATIVAS:
- SYSTEM_PROMPT_BASE: Prompt base do sistema
- get_system_prompt_with_memory(): Prompt com memória integrada
- _carregar_aprendizados_usuario(): Carrega conhecimento do usuário (de intent_prompt.py)
"""

from .system_base import SYSTEM_PROMPT_BASE, get_system_prompt_with_memory
from .intent_prompt import _carregar_aprendizados_usuario

__all__ = ['SYSTEM_PROMPT_BASE', 'get_system_prompt_with_memory', '_carregar_aprendizados_usuario']
