#!/usr/bin/env python3
"""
Excel Commands - Comandos especializados para Excel
"""

import os
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class ExcelCommands:
    """Classe para comandos de Excel"""
    
    def __init__(self, claude_client=None):
        self.client = claude_client
    
    def is_excel_command(self, consulta: str) -> bool:
        """Detecta se é comando Excel"""
        excel_keywords = [
            'excel', 'planilha', 'exportar', 'relatório', 'relatório excel',
            'xls', 'xlsx', 'exportar dados', 'gerar planilha', 'baixar excel',
            'salvar excel', 'criar relatório', 'dados em excel'
        ]
        
        consulta_lower = consulta.lower()
        return any(keyword in consulta_lower for keyword in excel_keywords)
    
    def processar_comando_excel(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa comando Excel"""
        try:
            # Lógica básica de processamento Excel
            return f"📊 Comando Excel processado: {consulta[:100]}..."
            
        except Exception as e:
            logger.error(f"Erro no comando Excel: {e}")
            return f"❌ Erro no processamento Excel: {e}"

# Instância global
_excel_commands = None

def get_excel_commands():
    """Retorna instância de ExcelCommands"""
    global _excel_commands
    if _excel_commands is None:
        _excel_commands = ExcelCommands()
    return _excel_commands
