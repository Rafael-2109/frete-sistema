#!/usr/bin/env python3
"""
Claude AI - Sistema Modular Integrado
Agora com NLP Enhanced Analyzer incluído!
"""

from .integration.claude.claude_integration import ClaudeRealIntegration, get_claude_integration, processar_com_claude_real
from .analyzers.nlp_enhanced_analyzer import get_nlp_enhanced_analyzer
from typing import Dict, Any, Optional

# Função principal de compatibilidade
def processar_consulta_modular(consulta: str, user_context: Optional[Dict[str, Any]] = None) -> str:
    """Função principal para processar consultas no sistema modular"""
    return processar_com_claude_real(consulta, user_context)

# Função de acesso ao NLP
def get_nlp_analyzer():
    """Retorna analisador NLP avançado"""
    return get_nlp_enhanced_analyzer()

__all__ = [
    'ClaudeRealIntegration',
    'get_claude_integration', 
    'processar_com_claude_real',
    'processar_consulta_modular',
    'get_nlp_enhanced_analyzer',
    'get_nlp_analyzer'
]
