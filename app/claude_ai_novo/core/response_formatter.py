"""
📝 RESPONSE FORMATTER
Formatação e padronização de respostas
"""

from typing import Dict, Any, Optional
from datetime import datetime

class ResponseFormatter:
    """Formatador de respostas do sistema"""
    
    @staticmethod
    def format_standard_response(content: str, metadata: Optional[Dict] = None) -> str:
        """Formata resposta padrão"""
        
        formatted = f"""🤖 **CLAUDE 4 SONNET**

{content}

---
🧠 Claude 4 Sonnet | {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
        
        if metadata and metadata.get('context_used'):
            formatted += " | 🧠 Contexto aplicado"
            
        if metadata and metadata.get('learning_applied'):
            formatted += " | 📚 Conhecimento aplicado"
            
        return formatted
    
    @staticmethod
    def format_error_response(error_msg: str) -> str:
        """Formata resposta de erro"""
        
        return f"""❌ **ERRO NO PROCESSAMENTO**

Ocorreu um problema ao processar sua consulta:
{error_msg}

Por favor, tente novamente ou reformule sua pergunta.

---
🤖 Claude AI | {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
    
    @staticmethod
    def format_excel_response(file_path: str, description: str) -> str:
        """Formata resposta com link para Excel"""
        
        return f"""📊 **RELATÓRIO EXCEL GERADO**

{description}

[📥 Baixar Relatório Excel]({file_path})

---
🤖 Claude 4 Sonnet | {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
