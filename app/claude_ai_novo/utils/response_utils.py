#!/usr/bin/env python3
"""
ResponseUtils - Utilitários especializados
"""

from typing import Dict, Optional, Any
from datetime import datetime

class ResponseUtils:
    """Classe para utilitários especializados"""
    
    def __init__(self):
        pass
        
    def _formatar_resultado_cursor(self, resultado: Dict[str, Any], titulo: str) -> str:
        """Formata resultado do Cursor Mode"""
        if 'error' in resultado:
            return f"❌ **Erro em {titulo}:** {resultado['error']}"
        
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        if titulo == 'Análise de Código':
            return f"""🔍 **{titulo} Completa**

📊 **Visão Geral:**
{self._formatar_analise_projeto(resultado)}

---
🎯 **Processado:** {timestamp}
⚡ **Fonte:** Cursor Mode + Claude Development AI"""
        
        elif titulo == 'Geração de Código':
            if resultado.get('status') == 'success':
                return f"""🚀 **{titulo} - Sucesso!**

📦 **Módulo:** {resultado.get('module_name', 'N/A')}
📁 **Arquivos Criados:** {resultado.get('total_files', 0)} arquivos
📋 **Lista de Arquivos:**
{chr(10).join(f"• {arquivo}" for arquivo in resultado.get('files_created', []))}

📚 **Documentação Gerada:**
{resultado.get('documentation', 'Documentação automática criada')}

---
🎯 **Processado:** {timestamp}
⚡ **Fonte:** Cursor Mode + Code Generator"""
            else:
                return f"❌ **Erro na {titulo}:** {resultado.get('error', 'Erro desconhecido')}"
        
        else:
            # Formato genérico
            return f"""✅ **{titulo} Concluído**

📋 **Resultado:** {str(resultado)[:500]}...

---
🎯 **Processado:** {timestamp}
⚡ **Fonte:** Cursor Mode"""
    def _formatar_analise_projeto(self, analise: Dict[str, Any]) -> str:
        """Formata análise do projeto"""
        overview = analise.get('project_overview', {})
        issues = analise.get('potential_issues', [])
        
        return f"""• **Módulos:** {overview.get('total_modules', 0)}
• **Modelos:** {overview.get('total_models', 0)}
• **Rotas:** {overview.get('total_routes', 0)}
• **Templates:** {overview.get('total_templates', 0)}
• **Problemas Detectados:** {len(issues)}
• **Arquitetura:** {overview.get('architecture_pattern', 'Flask MVC')}"""
    def _formatar_status_cursor(self, status: Dict[str, Any]) -> str:
        """Formata status do Cursor Mode"""
        return f"""📊 **Status do Cursor Mode**

🔧 **Estado:** {'✅ Ativo' if status['activated'] else '❌ Inativo'}

⚙️ **Funcionalidades:**
{chr(10).join(f"• {feature}: {'✅' if enabled else '❌'}" for feature, enabled in status['features'].items())}

🛠️ **Ferramentas:**
{chr(10).join(f"• {tool}: {'✅' if available else '❌'}" for tool, available in status['tools_available'].items())}

📋 **Capacidades Ativas:**
{chr(10).join(f"• {cap}" for cap in status.get('capabilities', []))}

---
🎯 **Cursor Mode - Sistema similar ao Cursor integrado!**"""

# Funções auxiliares para formatação de respostas
    def _gerar_resposta_erro(self, mensagem: str) -> Optional[Dict[str, Any]]:
        """Gera resposta de erro formatada"""
        return {
        'success': False,
        'error': mensagem,
        'response': f"❌ **Erro:** {mensagem}",
        'status': 'error'
    }
    def _gerar_resposta_sucesso(self, resposta: str) -> Optional[Dict[str, Any]]:
        """Gera resposta de sucesso formatada"""
        return {
        'success': True,
        'response': resposta,
        'status': 'success'
    }

# Adicionar nova função de detecção de consultas de desenvolvimento

# Instância global
_responseutils = None

def get_responseutils():
    """Retorna instância de ResponseUtils"""
    global _responseutils
    if _responseutils is None:
        _responseutils = ResponseUtils()
    return _responseutils
