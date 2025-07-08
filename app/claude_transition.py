"""
Interface de Transição - Claude AI
Permite usar tanto o sistema antigo quanto o novo
"""

import os
from typing import Dict, Optional, Any

class ClaudeTransition:
    """Classe de transição entre sistemas antigo e novo"""
    
    def __init__(self):
        self.usar_sistema_novo = os.getenv('USE_NEW_CLAUDE_SYSTEM', 'true').lower() == 'true'
        
        if self.usar_sistema_novo:
            self._inicializar_sistema_novo()
        else:
            self._inicializar_sistema_antigo()
    
    def _inicializar_sistema_novo(self):
        """Inicializa sistema novo"""
        try:
            from app.claude_ai_novo.integration.claude import get_claude_integration
            self.claude = get_claude_integration()
            self.sistema_ativo = "novo"
            print("✅ Sistema Claude AI NOVO ativado")
        except Exception as e:
            print(f"❌ Erro ao inicializar sistema novo: {e}")
            self._inicializar_sistema_antigo()
    
    def _inicializar_sistema_antigo(self):
        """Inicializa sistema antigo"""
        try:
            from app.claude_ai.claude_real_integration import processar_com_claude_real
            self.processar_consulta_real = processar_com_claude_real
            self.sistema_ativo = "antigo"
            print("✅ Sistema Claude AI ANTIGO ativado")
        except Exception as e:
            print(f"❌ Erro ao inicializar sistema antigo: {e}")
            self.sistema_ativo = "nenhum"
    
    def processar_consulta(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa consulta usando o sistema ativo"""
        
        if self.sistema_ativo == "novo":
            return self.claude.processar_consulta_real(consulta, user_context)
        elif self.sistema_ativo == "antigo":
            return self.processar_consulta_real(consulta, user_context)
        else:
            return "❌ Nenhum sistema Claude AI disponível"
    
    def alternar_sistema(self):
        """Alterna entre sistema antigo e novo"""
        if self.sistema_ativo == "novo":
            self._inicializar_sistema_antigo()
        else:
            self._inicializar_sistema_novo()
        
        return f"🔄 Sistema alterado para: {self.sistema_ativo}"

# Instância global
_claude_transition = None

def get_claude_transition():
    """Retorna instância de transição"""
    global _claude_transition
    if _claude_transition is None:
        _claude_transition = ClaudeTransition()
    return _claude_transition

def processar_consulta_transicao(consulta: str, user_context: Optional[Dict] = None) -> str:
    """Função única para processar consultas independente do sistema"""
    transition = get_claude_transition()
    return transition.processar_consulta(consulta, user_context)
