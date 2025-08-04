"""
MCP Logística - Sistema autônomo para consultas em linguagem natural
"""

from .nlp_engine import MCPNLPEngine
from .entity_mapper import EntityMapper
from .intent_classifier import IntentClassifier
from .query_processor import QueryProcessor
from .preference_manager import PreferenceManager
from .confirmation_system import ConfirmationSystem

__version__ = "1.0.0"
__all__ = [
    "MCPNLPEngine",
    "EntityMapper",
    "IntentClassifier",
    "QueryProcessor",
    "PreferenceManager",
    "ConfirmationSystem"
]