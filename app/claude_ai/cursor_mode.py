"""
🎯 CURSOR MODE - Ativação completa das funcionalidades similares ao Cursor
Integra todas as capacidades de desenvolvimento em um modo unificado
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .claude_development_ai import get_claude_development_ai, init_claude_development_ai
from .claude_project_scanner import get_project_scanner
from .claude_code_generator import get_code_generator
from .unlimited_mode import activate_unlimited_mode

logger = logging.getLogger(__name__)

class CursorMode:
    """
    🎯 CURSOR MODE - Funcionalidades similares ao Cursor integradas
    
    Capacidades ativadas:
    - ✅ Análise completa de código
    - ✅ Geração inteligente de módulos
    - ✅ Refatoração automática
    - ✅ Detecção de bugs
    - ✅ Busca semântica no código
    - ✅ Modificação inteligente
    - ✅ Documentação automática
    - ✅ Validação de código
    """
    
    def __init__(self):
        """Inicializa Cursor Mode com todas as ferramentas"""
        self.development_ai = get_claude_development_ai() or init_claude_development_ai()
        self.activated = False
        self.mode_features = {
            'code_analysis': True,
            'intelligent_generation': True,
            'automatic_refactoring': True,
            'bug_detection': True,
            'semantic_search': True,
            'smart_modification': True,
            'auto_documentation': True,
            'code_validation': True,
            'unlimited_mode': False
        }
        
        logger.info("🎯 Cursor Mode inicializado - Pronto para ativação")
    
    def activate_cursor_mode(self, unlimited: bool = False) -> Dict[str, Any]:
        """
        🚀 ATIVA MODO CURSOR COMPLETO
        """
        try:
            logger.info("🚀 Ativando Cursor Mode...")
            
            # Ativar modo ilimitado se solicitado
            if unlimited:
                activate_unlimited_mode()
                self.mode_features['unlimited_mode'] = True
                logger.info("⚡ Modo Ilimitado ativado!")
            
            # Verificar disponibilidade de todas as ferramentas
            tools_status = self._check_tools_availability()
            
            # Ativar modo
            self.activated = True
            
            # Fazer scan inicial do projeto
            initial_scan = self.development_ai.analyze_project_complete()
            
            result = {
                'status': 'success',
                'activated_at': datetime.now().isoformat(),
                'mode': 'Cursor Mode',
                'features_available': self.mode_features,
                'tools_status': tools_status,
                'initial_project_analysis': {
                    'total_modules': initial_scan.get('project_overview', {}).get('total_modules', 0),
                    'total_files': initial_scan.get('scan_metadata', {}).get('total_files', 0),
                    'architecture': initial_scan.get('architecture_analysis', {}),
                    'issues_detected': len(initial_scan.get('potential_issues', []))
                },
                'capabilities': self._list_cursor_capabilities()
            }
            
            logger.info("✅ Cursor Mode ativado com sucesso!")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao ativar Cursor Mode: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def analyze_code(self, target: str = 'project') -> Dict[str, Any]:
        """
        🔍 ANÁLISE DE CÓDIGO (Similar ao Cursor)
        """
        if not self.activated:
            return {'error': 'Cursor Mode não ativado. Use activate_cursor_mode() primeiro.'}
        
        try:
            if target == 'project':
                return self.development_ai.analyze_project_complete()
            else:
                return self.development_ai.analyze_specific_file(target)
                
        except Exception as e:
            return {'error': str(e)}
    
    def generate_code(self, description: str, module_name: Optional[str] = None) -> Dict[str, Any]:
        """
        🚀 GERAÇÃO DE CÓDIGO (Similar ao Cursor)
        """
        if not self.activated:
            return {'error': 'Cursor Mode não ativado. Use activate_cursor_mode() primeiro.'}
        
        try:
            # Auto-detectar nome do módulo se não fornecido
            if not module_name:
                module_name = self._extract_module_name(description)
            
            return self.development_ai.generate_new_module(module_name, description)
            
        except Exception as e:
            return {'error': str(e)}
    
    def modify_code(self, file_path: str, modification_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✏️ MODIFICAÇÃO DE CÓDIGO (Similar ao Cursor)
        """
        if not self.activated:
            return {'error': 'Cursor Mode não ativado. Use activate_cursor_mode() primeiro.'}
        
        try:
            return self.development_ai.modify_existing_file(file_path, modification_type, details)
            
        except Exception as e:
            return {'error': str(e)}
    
    def fix_issues(self, auto_fix: bool = True) -> Dict[str, Any]:
        """
        🔧 CORREÇÃO DE PROBLEMAS (Similar ao Cursor)
        """
        if not self.activated:
            return {'error': 'Cursor Mode não ativado. Use activate_cursor_mode() primeiro.'}
        
        try:
            return self.development_ai.detect_and_fix_issues()
            
        except Exception as e:
            return {'error': str(e)}
    
    def search_code(self, query: str, scope: str = 'project') -> Dict[str, Any]:
        """
        🔍 BUSCA SEMÂNTICA NO CÓDIGO (Similar ao Cursor)
        """
        if not self.activated:
            return {'error': 'Cursor Mode não ativado. Use activate_cursor_mode() primeiro.'}
        
        try:
            # Usar project scanner para busca semântica
            scanner = get_project_scanner()
            if scanner:
                results = scanner.search_in_project(query)
                return {
                    'query': query,
                    'results': results,
                    'total_matches': len(results)
                }
            else:
                return {'error': 'Project scanner não disponível'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def chat_with_code(self, message: str) -> Dict[str, Any]:
        """
        💬 CHAT COM CÓDIGO (Similar ao Cursor)
        """
        if not self.activated:
            return {'error': 'Cursor Mode não ativado. Use activate_cursor_mode() primeiro.'}
        
        try:
            return self.development_ai.analyze_and_suggest(message)
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """
        📊 STATUS DO CURSOR MODE
        """
        return {
            'activated': self.activated,
            'features': self.mode_features,
            'tools_available': self._check_tools_availability(),
            'capabilities': self._list_cursor_capabilities() if self.activated else []
        }
    
    # Métodos auxiliares
    
    def _check_tools_availability(self) -> Dict[str, bool]:
        """Verifica disponibilidade das ferramentas"""
        return {
            'development_ai': self.development_ai is not None,
            'project_scanner': get_project_scanner() is not None,
            'code_generator': get_code_generator() is not None
        }
    
    def _list_cursor_capabilities(self) -> List[str]:
        """Lista capacidades similares ao Cursor"""
        return [
            "🔍 Análise completa de projetos",
            "🚀 Geração automática de código Flask",
            "✏️ Modificação inteligente de arquivos",
            "🔧 Detecção e correção automática de bugs",
            "🔍 Busca semântica no código",
            "📚 Documentação automática",
            "🏗️ Análise de arquitetura",
            "⚡ Refatoração inteligente",
            "🛡️ Validação de código",
            "💾 Backup automático",
            "🎯 Sugestões contextuais",
            "🧠 Chat inteligente com código"
        ]
    
    def _extract_module_name(self, description: str) -> str:
        """Extrai nome do módulo da descrição"""
        # Lógica simples para extrair nome
        words = description.lower().split()
        
        # Procurar por substantivos comuns
        keywords = ['módulo', 'sistema', 'gestão', 'controle', 'cadastro']
        
        for i, word in enumerate(words):
            if word in keywords and i + 1 < len(words):
                return words[i + 1].replace(' ', '_')
        
        # Fallback: usar primeira palavra significativa
        for word in words:
            if len(word) > 3 and word.isalpha():
                return word.replace(' ', '_')
        
        return 'novo_modulo'
    
    def deactivate_cursor_mode(self) -> Dict[str, Any]:
        """
        ⏹️ DESATIVA CURSOR MODE
        """
        try:
            self.activated = False
            
            return {
                'status': 'success',
                'message': 'Cursor Mode desativado',
                'deactivated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


# Instância global
_cursor_mode = None

def get_cursor_mode() -> CursorMode:
    """Obtém instância global do Cursor Mode"""
    global _cursor_mode
    if _cursor_mode is None:
        _cursor_mode = CursorMode()
    return _cursor_mode

def activate_cursor_mode(unlimited: bool = False) -> Dict[str, Any]:
    """Atalho para ativar Cursor Mode"""
    cursor = get_cursor_mode()
    return cursor.activate_cursor_mode(unlimited) 