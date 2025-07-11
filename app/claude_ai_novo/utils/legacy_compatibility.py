#!/usr/bin/env python3
"""
Claude AI - Sistema Modular Integrado
Agora com NLP Enhanced Analyzer incluído!
"""

from typing import Dict, Any, Optional, Union

# Variáveis globais para armazenar as funções importadas
_processar_com_claude_real = None
_get_claude_integration = None
_get_nlp_enhanced_analyzer = None
_ClaudeRealIntegration = None

try:
    # Tentar imports do sistema modular
    from app.claude_ai_novo.integration.claude.claude_integration import ClaudeRealIntegration, get_claude_integration, processar_com_claude_real
    from app.claude_ai_novo.analyzers.nlp_enhanced_analyzer import get_nlp_enhanced_analyzer
    
    # Armazenar nas variáveis globais
    _processar_com_claude_real = processar_com_claude_real
    _get_claude_integration = get_claude_integration
    _get_nlp_enhanced_analyzer = get_nlp_enhanced_analyzer
    _ClaudeRealIntegration = ClaudeRealIntegration
    
except ImportError as e:
    # Fallback para compatibilidade
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ Erro no import modular: {e}")
    
    # Definir funções de fallback
    def _processar_com_claude_real_fallback(consulta: str, user_context=None) -> str:
        return "Sistema modular não disponível"
    
    def _get_claude_integration_fallback():
        return None
    
    def _get_nlp_enhanced_analyzer_fallback():
        return None
    
    class _ClaudeRealIntegrationFallback:
        pass
    
    # Atribuir fallbacks
    _processar_com_claude_real = _processar_com_claude_real_fallback
    _get_claude_integration = _get_claude_integration_fallback
    _get_nlp_enhanced_analyzer = _get_nlp_enhanced_analyzer_fallback
    _ClaudeRealIntegration = _ClaudeRealIntegrationFallback

# Função principal de compatibilidade
def processar_consulta_modular(consulta: str, user_context: Optional[Dict[str, Any]] = None) -> str:
    """Função principal para processar consultas no sistema modular"""
    try:
        if _processar_com_claude_real:
            return _processar_com_claude_real(consulta, user_context)
        else:
            return "Sistema modular não disponível"
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Erro no processamento modular: {e}")
        return "Erro no sistema modular"

# Função de acesso ao NLP
def get_nlp_analyzer():
    """Retorna analisador NLP avançado"""
    try:
        if _get_nlp_enhanced_analyzer:
            return _get_nlp_enhanced_analyzer()
        else:
            return None
    except Exception:
        return None

# Funções de acesso direto
def processar_com_claude_real(consulta: str, user_context=None) -> str:
    """Acesso direto ao processador Claude Real"""
    if _processar_com_claude_real:
        return _processar_com_claude_real(consulta, user_context)
    return "Sistema não disponível"

def get_claude_integration():
    """Acesso direto à integração Claude"""
    if _get_claude_integration:
        return _get_claude_integration()
    return None

def get_nlp_enhanced_analyzer():
    """Acesso direto ao analisador NLP"""
    if _get_nlp_enhanced_analyzer:
        return _get_nlp_enhanced_analyzer()
    return None

# Classe principal (para compatibilidade)
ClaudeRealIntegration = _ClaudeRealIntegration

__all__ = [
    'ClaudeRealIntegration',
    'get_claude_integration', 
    'processar_com_claude_real',
    'processar_consulta_modular',
    'get_nlp_enhanced_analyzer',
    'get_nlp_analyzer'
]
