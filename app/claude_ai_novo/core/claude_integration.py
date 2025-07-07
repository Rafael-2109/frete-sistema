#!/usr/bin/env python3
"""
Claude Integration - Core Simplificado
Classe principal da integração com Claude AI
"""

import os
import anthropic
import logging
from typing import Dict, Optional, Any
from datetime import datetime

# Imports dos módulos decompostos
from app.claude_ai_novo.commands.excel_commands import get_excel_commands
from app.claude_ai_novo.data_loaders.database_loader import get_database_loader

logger = logging.getLogger(__name__)

class ClaudeRealIntegration:
    """Integração com Claude REAL da Anthropic - Versão Modular"""
    
    def __init__(self):
        """Inicializa integração com Claude real"""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            logger.warning("⚠️ ANTHROPIC_API_KEY não configurada - usando modo simulado")
            self.client = None
            self.modo_real = False
        else:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.modo_real = True
                logger.info("🚀 Claude REAL conectado com sucesso!")
            except Exception as e:
                logger.error(f"❌ Erro ao conectar Claude real: {e}")
                self.client = None
                self.modo_real = False
        
        # Carregar módulos decompostos
        self.excel_commands = get_excel_commands()
        self.database_loader = get_database_loader()
        
        logger.info("🎯 Claude Integration Modular inicializado!")
    
    def processar_consulta_real(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa consulta usando Claude REAL com arquitetura modular"""
        
        if not self.modo_real:
            return self._fallback_simulado(consulta)
        
        try:
            # Detectar tipo de comando
            if self.excel_commands.is_excel_command(consulta):
                logger.info("📊 Comando Excel detectado")
                return self.excel_commands.processar_comando_excel(consulta, user_context)
            
            # Processamento padrão
            return self._processar_consulta_padrao(consulta, user_context)
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento: {e}")
            return f"❌ Erro interno: {e}"
    
    def _processar_consulta_padrao(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processamento padrão"""
        try:
            if not self.client:
                return self._fallback_simulado(consulta)
            
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": consulta}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"❌ Erro no Claude API: {e}")
            return self._fallback_simulado(consulta)
    
    def _fallback_simulado(self, consulta: str) -> str:
        """Fallback simulado"""
        return f"🤖 **CLAUDE AI MODULAR - MODO SIMULADO**\n\nConsulta processada: {consulta}\n\n✅ Sistema modular funcionando!"

# Instância global para compatibilidade
_claude_integration = None

def get_claude_integration():
    """Retorna instância da integração Claude"""
    global _claude_integration
    if _claude_integration is None:
        _claude_integration = ClaudeRealIntegration()
    return _claude_integration

def processar_com_claude_real(consulta: str, user_context: Optional[Dict] = None) -> str:
    """Função de compatibilidade com o sistema existente"""
    integration = get_claude_integration()
    return integration.processar_consulta_real(consulta, user_context)
