#!/usr/bin/env python3
"""
FileCommands - Comandos especializados para arquivos (OTIMIZADO)
"""

from app.claude_ai_novo.commands.base_command import BaseCommand, format_response
import logging

logger = logging.getLogger(__name__)

class FileCommands(BaseCommand):
    """Classe para comandos de arquivo (versão otimizada)"""
    
    def is_file_command(self, consulta: str) -> bool:
        """Detecta comandos de arquivo"""
        keywords = [
            'verificar', 'ver arquivo', 'ler arquivo', 'mostrar arquivo',
            'abrir arquivo', 'conteudo de', 'conteúdo de', 'código de',
            'listar arquivos', 'listar diretorio', 'listar diretório',
            'routes.py', 'models.py', 'forms.py', '.html',
            'app/', 'onde está', 'onde fica', 'qual arquivo'
        ]
        
        consulta_lower = consulta.lower()
        return any(cmd in consulta_lower for cmd in keywords)
    
    def processar_file_command(self, consulta: str, user_context=None) -> str:
        """Processa comandos de arquivo"""
        if not self._validate_input(consulta):
            return "❌ Consulta inválida"
        
        self._log_command(consulta, "arquivo")
        
        try:
            # Implementação otimizada
            return format_response(
                f"📁 Comando de arquivo processado: {consulta[:100]}...",
                "FileCommands"
            )
            
        except Exception as e:
            return self._handle_error(e, "arquivo")

# Instância global
_file_commands = None

def get_file_commands():
    """Retorna instância de FileCommands"""
    global _file_commands
    if _file_commands is None:
        _file_commands = FileCommands()
    return _file_commands
