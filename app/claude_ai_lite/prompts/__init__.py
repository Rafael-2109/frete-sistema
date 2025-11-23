"""
Prompts centralizados do Claude AI Lite.

Inclui:
- system_base: prompt base do sistema
- intent_prompt: prompt para classificação de intenções (gerado dinamicamente)
"""

from .system_base import SYSTEM_PROMPT_BASE
from .intent_prompt import gerar_prompt_classificacao

__all__ = ['SYSTEM_PROMPT_BASE', 'gerar_prompt_classificacao']
