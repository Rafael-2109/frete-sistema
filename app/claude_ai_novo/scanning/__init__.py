"""
🔍 SCANNING SYSTEM  
Sistema de escaneamento e descoberta de projetos
"""

from .scanner import get_project_scanner, ClaudeProjectScanner

__all__ = [
    'get_project_scanner',
    'ClaudeProjectScanner'
] 