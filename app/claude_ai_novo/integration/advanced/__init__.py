#!/usr/bin/env python3
"""
🚀 SISTEMA AVANÇADO DE IA INDUSTRIAL - MÓDULOS ESPECIALIZADOS
Arquitetura modular com responsabilidades claras e imports organizados
"""

# Imports dos módulos especializados (reorganizados)
from ...analyzers.metacognitive_analyzer import MetacognitiveAnalyzer, get_metacognitive_analyzer
from ...analyzers.structural_ai import StructuralAI, get_structural_ai
from ...processors.semantic_loop_processor import SemanticLoopProcessor, get_semantic_loop_processor
from .advanced_integration import AdvancedAIIntegration, get_advanced_ai_integration

# Exports principais
__all__ = [
    # Classes principais
    'MetacognitiveAnalyzer',
    'StructuralAI', 
    'SemanticLoopProcessor',
    'AdvancedAIIntegration',
    
    # Funções de conveniência
    'get_metacognitive_analyzer',
    'get_structural_ai',
    'get_semantic_loop_processor',
    'get_advanced_ai_integration'
]

# Versão da arquitetura modular reorganizada
__version__ = "2.1.0-reorganized"
