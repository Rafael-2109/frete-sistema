"""
🔒 SECURITY GUARD - Sistema de Segurança Absoluto para Claude AI
Controla e protege todas as ações que o Claude pode executar
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from flask import current_user
from functools import wraps

logger = logging.getLogger(__name__)

class ClaudeSecurityGuard:
    """Sistema de segurança absoluto para Claude AI"""
    
    def __init__(self, app_path: Optional[str] = None):
        """Inicializa sistema de segurança"""
        self.app_path = Path(app_path) if app_path else Path(__file__).parent.parent
        self.security_config_file = self.app_path / 'claude_ai' / 'security_config.json'
        self.action_log_file = self.app_path / 'claude_ai' / 'security_actions.log'
        self.pending_actions_file = self.app_path / 'claude_ai' / 'pending_actions.json'
        
        # Carregar configurações
        self.security_config = self._load_security_config()
        self.pending_actions = self._load_pending_actions()
        
        logger.info("🔒 Claude Security Guard ativado")
    
    def _load_security_config(self) -> Dict[str, Any]:
        """Carrega configurações de segurança"""
        default_config = {
            "modo_seguranca": "MAXIMO",  # MAXIMO, MEDIO, BASICO
            "require_approval": True,    # Sempre pedir aprovação
            "whitelist_paths": [
                "app/teste_*",           # Apenas módulos de teste
                "app/templates/teste_*", # Templates de teste
                "app/static/temp_*"      # Arquivos temporários
            ],
            "blacklist_paths": [
                "app/__init__.py",       # Arquivo principal
                "app/*/models.py",       # Nunca modificar models existentes
                "config.py",             # Configurações
                "requirements.txt",      # Dependências
                "migrations/",           # Migrações
                "app/auth/",            # Sistema de autenticação
                "app/utils/",           # Utilitários críticos
                ".env",                 # Variáveis de ambiente
                "*.pyc",                # Arquivos compilados
                "__pycache__/",         # Cache Python
            ],
            "max_file_size_kb": 100,     # Máximo 100KB por arquivo
            "max_files_per_action": 5,   # Máximo 5 arquivos por ação
            "admin_users": [],           # Lista de admins
            "auto_backup": True,         # Backup automático
            "require_reason": True,      # Exigir justificativa
            "action_timeout_hours": 24   # Ações expiram em 24h
        }
        
        try:
            if self.security_config_file.exists():
                with open(self.security_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge com config padrão
                    default_config.update(config)
            
            # Salvar config atualizada
            with open(self.security_config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            return default_config
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar config de segurança: {e}")
            return default_config
    
    def _load_pending_actions(self) -> List[Dict[str, Any]]:
        """Carrega ações pendentes de aprovação"""
        try:
            if self.pending_actions_file.exists():
                with open(self.pending_actions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"❌ Erro ao carregar ações pendentes: {e}")
            return []
    
    def _save_pending_actions(self):
        """Salva ações pendentes"""
        try:
            with open(self.pending_actions_file, 'w', encoding='utf-8') as f:
                json.dump(self.pending_actions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Erro ao salvar ações pendentes: {e}")
    
    def _log_security_action(self, action_type: str, details: Dict[str, Any], approved: bool = False):
        """Log de ações de segurança"""
        user_name = 'system'
        user_id = None
        
        if current_user and hasattr(current_user, 'nome') and current_user.nome:
            user_name = current_user.nome
        if current_user and hasattr(current_user, 'id'):
            user_id = current_user.id
            
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user_name,
            'user_id': user_id,
            'action_type': action_type,
            'approved': approved,
            'details': details
        }
        
        try:
            with open(self.action_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            logger.info(f"🔒 Ação registrada: {action_type} - Aprovada: {approved}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao registrar ação: {e}")
    
    def validate_file_operation(self, file_path: str, operation: str, content: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Valida operação em arquivo
        Returns: (permitido, motivo, action_id)
        """
        try:
            # Normalizar caminho
            normalized_path = str(Path(file_path).as_posix())
            
            # 1. VERIFICAR BLACKLIST
            for blacklist_pattern in self.security_config['blacklist_paths']:
                if self._path_matches_pattern(normalized_path, blacklist_pattern):
                    reason = f"❌ BLOQUEADO: Arquivo em blacklist - {blacklist_pattern}"
                    self._log_security_action('FILE_BLOCKED', {
                        'file_path': file_path,
                        'operation': operation,
                        'reason': reason
                    }, approved=False)
                    return False, reason, ""
            
            # 2. VERIFICAR WHITELIST (se modo MAXIMO)
            if self.security_config['modo_seguranca'] == 'MAXIMO':
                whitelist_ok = False
                for whitelist_pattern in self.security_config['whitelist_paths']:
                    if self._path_matches_pattern(normalized_path, whitelist_pattern):
                        whitelist_ok = True
                        break
                
                if not whitelist_ok:
                    reason = f"❌ BLOQUEADO: Arquivo fora da whitelist (modo MÁXIMO)"
                    self._log_security_action('FILE_BLOCKED', {
                        'file_path': file_path,
                        'operation': operation,
                        'reason': reason
                    }, approved=False)
                    return False, reason, ""
            
            # 3. VERIFICAR TAMANHO DO CONTEÚDO
            if content and len(content.encode('utf-8')) > self.security_config['max_file_size_kb'] * 1024:
                reason = f"❌ BLOQUEADO: Arquivo muito grande ({len(content.encode('utf-8'))/1024:.1f}KB > {self.security_config['max_file_size_kb']}KB)"
                self._log_security_action('FILE_BLOCKED', {
                    'file_path': file_path,
                    'operation': operation,
                    'reason': reason,
                    'size_kb': len(content.encode('utf-8'))/1024
                }, approved=False)
                return False, reason, ""
            
            # 4. GERAR ACTION_ID PARA APROVAÇÃO
            action_id = f"action_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.pending_actions)}"
            
            # 5. SE REQUER APROVAÇÃO, ADICIONAR À LISTA
            if self.security_config['require_approval']:
                user_name = 'system'
                user_id = None
                
                if current_user and hasattr(current_user, 'nome') and current_user.nome:
                    user_name = current_user.nome
                if current_user and hasattr(current_user, 'id'):
                    user_id = current_user.id
                
                pending_action = {
                    'action_id': action_id,
                    'timestamp': datetime.now().isoformat(),
                    'user': user_name,
                    'user_id': user_id,
                    'operation': operation,
                    'file_path': file_path,
                    'content_preview': (content[:200] + '...' if len(content) > 200 else content) if content else None,
                    'status': 'PENDING',
                    'expires_at': (datetime.now() + timedelta(hours=self.security_config['action_timeout_hours'])).isoformat()
                }
                
                self.pending_actions.append(pending_action)
                self._save_pending_actions()
                
                reason = f"⚠️ AGUARDANDO APROVAÇÃO: Ação {action_id} criada"
                self._log_security_action('ACTION_PENDING', pending_action, approved=False)
                
                return False, reason, action_id
            
            # 6. SE NÃO REQUER APROVAÇÃO, PERMITIR
            self._log_security_action('FILE_ALLOWED', {
                'file_path': file_path,
                'operation': operation
            }, approved=True)
            
            return True, "✅ Operação permitida", action_id
            
        except Exception as e:
            logger.error(f"❌ Erro na validação de segurança: {e}")
            return False, f"❌ Erro interno de segurança: {e}", ""
    
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Verifica se caminho corresponde ao padrão"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern) or pattern in path
    
    def approve_action(self, action_id: str, approved: bool, admin_user: str, reason: str = "") -> Tuple[bool, str]:
        """Aprova ou rejeita uma ação pendente"""
        try:
            # Buscar ação pendente
            action = None
            action_index = None
            
            for i, pending_action in enumerate(self.pending_actions):
                if pending_action['action_id'] == action_id:
                    action = pending_action
                    action_index = i
                    break
            
            if not action or action_index is None:
                return False, f"❌ Ação {action_id} não encontrada"
            
            # Verificar se não expirou
            expires_at = datetime.fromisoformat(action['expires_at'])
            if datetime.now() > expires_at:
                # Remover ação expirada
                self.pending_actions.pop(action_index)
                self._save_pending_actions()
                return False, f"❌ Ação {action_id} expirou"
            
            # Atualizar status
            action['status'] = 'APPROVED' if approved else 'REJECTED'
            action['approved_by'] = admin_user
            action['approved_at'] = datetime.now().isoformat()
            action['approval_reason'] = reason
            
            # Log da decisão
            self._log_security_action('ACTION_DECISION', {
                'action_id': action_id,
                'approved': approved,
                'admin_user': admin_user,
                'reason': reason,
                'original_action': action
            }, approved=approved)
            
            # Salvar
            self._save_pending_actions()
            
            result_msg = f"✅ Ação {action_id} {'APROVADA' if approved else 'REJEITADA'} por {admin_user}"
            
            return True, result_msg
            
        except Exception as e:
            logger.error(f"❌ Erro ao aprovar ação: {e}")
            return False, f"❌ Erro interno: {e}"
    
    def get_pending_actions(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retorna ações pendentes (filtradas por usuário se especificado)"""
        try:
            # Remover ações expiradas
            now = datetime.now()
            self.pending_actions = [
                action for action in self.pending_actions
                if datetime.fromisoformat(action['expires_at']) > now
            ]
            self._save_pending_actions()
            
            # Filtrar por usuário se especificado
            if user_id:
                return [action for action in self.pending_actions if action.get('user_id') == user_id]
            
            return self.pending_actions
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter ações pendentes: {e}")
            return []
    
    def is_action_approved(self, action_id: str) -> Tuple[bool, str]:
        """Verifica se uma ação foi aprovada"""
        for action in self.pending_actions:
            if action['action_id'] == action_id:
                if action['status'] == 'APPROVED':
                    return True, "✅ Ação aprovada"
                elif action['status'] == 'REJECTED':
                    return False, "❌ Ação rejeitada"
                else:
                    return False, "⏳ Ação ainda pendente"
        
        return False, "❌ Ação não encontrada"
    
    def emergency_lockdown(self, reason: str, admin_user: str):
        """Modo de emergência - bloqueia todas as operações"""
        try:
            self.security_config['modo_seguranca'] = 'LOCKDOWN'
            self.security_config['require_approval'] = True
            self.security_config['emergency_lockdown'] = {
                'enabled': True,
                'reason': reason,
                'admin_user': admin_user,
                'timestamp': datetime.now().isoformat()
            }
            
            # Salvar configuração
            with open(self.security_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.security_config, f, indent=2, ensure_ascii=False)
            
            # Log da emergência
            self._log_security_action('EMERGENCY_LOCKDOWN', {
                'reason': reason,
                'admin_user': admin_user
            }, approved=True)
            
            logger.critical(f"🚨 LOCKDOWN DE EMERGÊNCIA ATIVADO por {admin_user}: {reason}")
            
        except Exception as e:
            logger.error(f"❌ Erro no lockdown de emergência: {e}")

# Instância global
security_guard = None

def init_security_guard(app_path: Optional[str] = None) -> ClaudeSecurityGuard:
    """Inicializa o sistema de segurança"""
    global security_guard
    security_guard = ClaudeSecurityGuard(app_path)
    return security_guard

def get_security_guard() -> Optional[ClaudeSecurityGuard]:
    """Retorna instância do sistema de segurança"""
    return security_guard

def require_security_approval(f):
    """Decorator para operações que requerem aprovação de segurança"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        guard = get_security_guard()
        if not guard:
            return {'error': 'Sistema de segurança não inicializado'}, 500
        
        # Verificar se operação requer aprovação
        if guard.security_config.get('require_approval', True):
            # Implementar lógica de verificação
            pass
        
        return f(*args, **kwargs)
    return decorated_function 