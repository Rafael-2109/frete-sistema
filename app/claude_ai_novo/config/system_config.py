"""
🔧 SYSTEM CONFIG - Configuração do Sistema
==========================================

Módulo responsável por gerenciar configurações dinâmicas e adaptáveis do sistema.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class SystemConfig:
    """
    Gerenciador de configuração dinâmica do sistema.
    
    Responsabilidades:
    - Configurações centralizadas
    - Configurações dinâmicas
    - Profiles de configuração
    - Validação de configurações
    - Hot reload de configurações
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o gerenciador de configuração.
        
        Args:
            config_path: Caminho para arquivo de configuração personalizado
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("🔧 SystemConfig inicializado")
        
        # Caminhos de configuração
        self.config_path = config_path or self._get_default_config_path()
        self.config_dir = Path(self.config_path).parent
        
        # Configurações carregadas
        self.configurations = {}
        
        # Profiles disponíveis
        self.profiles = {
            'development': 'dev',
            'testing': 'test', 
            'staging': 'stage',
            'production': 'prod'
        }
        
        # Profile ativo
        self.active_profile = self._detect_active_profile()
        
        # Configurações padrão
        self.default_configurations = self._initialize_default_configurations()
        
        # Histórico de mudanças
        self.change_history = []
        
        # Watchers de configuração
        self.config_watchers = {}
        
        # Métricas de configuração
        self.metrics = {
            'config_loads': 0,
            'config_saves': 0,
            'hot_reloads': 0,
            'validation_errors': 0,
            'profile_switches': 0
        }
        
        # Carregar configurações iniciais
        self._load_initial_configurations()
    
    def get_config(self, key: str, default: Any = None, profile: Optional[str] = None) -> Any:
        """
        Obtém valor de configuração.
        
        Args:
            key: Chave da configuração (suporta notação de ponto)
            default: Valor padrão se não encontrado
            profile: Profile específico (usa ativo se None)
            
        Returns:
            Valor da configuração ou padrão
        """
        try:
            target_profile = profile or self.active_profile
            
            # Buscar em configurações do profile
            if target_profile in self.configurations:
                value = self._get_nested_value(self.configurations[target_profile], key)
                if value is not None:
                    return value
            
            # Buscar em configurações globais
            if 'global' in self.configurations:
                value = self._get_nested_value(self.configurations['global'], key)
                if value is not None:
                    return value
            
            # Buscar em configurações padrão
            value = self._get_nested_value(self.default_configurations, key)
            if value is not None:
                return value
            
            self.logger.debug(f"🔍 Configuração '{key}' não encontrada, usando padrão: {default}")
            return default
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter configuração '{key}': {e}")
            return default
    
    def set_config(self, key: str, value: Any, profile: Optional[str] = None, persist: bool = True) -> bool:
        """
        Define valor de configuração.
        
        Args:
            key: Chave da configuração
            value: Valor a ser definido
            profile: Profile específico (usa ativo se None)
            persist: Se deve persistir no arquivo
            
        Returns:
            True se definido com sucesso
        """
        try:
            target_profile = profile or self.active_profile
            
            # Validar valor
            if not self._validate_config_value(key, value):
                self.logger.warning(f"⚠️ Valor inválido para '{key}': {value}")
                return False
            
            # Garantir que profile existe
            if target_profile not in self.configurations:
                self.configurations[target_profile] = {}
            
            # Obter valor anterior para histórico
            old_value = self.get_config(key, profile=target_profile)
            
            # Definir novo valor
            self._set_nested_value(self.configurations[target_profile], key, value)
            
            # Registrar mudança no histórico
            self._record_config_change(key, old_value, value, target_profile)
            
            # Persistir se solicitado
            if persist:
                self._save_profile_config(target_profile)
            
            # Notificar watchers
            self._notify_config_watchers(key, value, old_value, target_profile)
            
            self.logger.info(f"✅ Configuração '{key}' definida: {value} (profile: {target_profile})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao definir configuração '{key}': {e}")
            return False
    
    def get_profile_config(self, profile: str) -> Dict[str, Any]:
        """
        Obtém todas as configurações de um profile.
        
        Args:
            profile: Nome do profile
            
        Returns:
            Dicionário com configurações do profile
        """
        if profile in self.configurations:
            return self.configurations[profile].copy()
        else:
            return {}
    
    def switch_profile(self, profile: str) -> bool:
        """
        Muda o profile ativo.
        
        Args:
            profile: Nome do profile
            
        Returns:
            True se mudança bem-sucedida
        """
        try:
            if profile not in self.profiles.values() and profile not in self.profiles.keys():
                self.logger.warning(f"⚠️ Profile desconhecido: {profile}")
                return False
            
            old_profile = self.active_profile
            self.active_profile = profile
            
            # Carregar configurações do novo profile se necessário
            if profile not in self.configurations:
                self._load_profile_config(profile)
            
            # Registrar mudança
            self._record_profile_switch(old_profile, profile)
            
            # Atualizar métricas
            self.metrics['profile_switches'] += 1
            
            self.logger.info(f"🔄 Profile alterado: {old_profile} → {profile}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao alterar profile: {e}")
            return False
    
    def reload_config(self, profile: Optional[str] = None) -> bool:
        """
        Recarrega configurações do arquivo.
        
        Args:
            profile: Profile específico (recarrega ativo se None)
            
        Returns:
            True se recarregado com sucesso
        """
        try:
            target_profile = profile or self.active_profile
            
            self.logger.info(f"🔄 Recarregando configurações do profile: {target_profile}")
            
            # Fazer backup das configurações atuais
            backup = self.configurations.get(target_profile, {}).copy()
            
            try:
                # Recarregar do arquivo
                self._load_profile_config(target_profile)
                
                # Atualizar métricas
                self.metrics['hot_reloads'] += 1
                
                self.logger.info(f"✅ Configurações recarregadas: {target_profile}")
                return True
                
            except Exception as e:
                # Restaurar backup em caso de erro
                self.configurations[target_profile] = backup
                self.logger.error(f"❌ Erro ao recarregar, backup restaurado: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Erro no reload de configurações: {e}")
            return False
    
    def validate_configuration(self, profile: Optional[str] = None) -> Dict[str, Any]:
        """
        Valida configurações de um profile.
        
        Args:
            profile: Profile a validar (usa ativo se None)
            
        Returns:
            Relatório de validação
        """
        try:
            target_profile = profile or self.active_profile
            config_data = self.get_profile_config(target_profile)
            
            validation_report = {
                'profile': target_profile,
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'errors': [],
                'warnings': [],
                'validated_keys': 0,
                'total_keys': 0
            }
            
            # Contar chaves totais
            validation_report['total_keys'] = len(self._flatten_dict(config_data))
            
            # Validar cada configuração
            for key, value in self._flatten_dict(config_data).items():
                try:
                    if self._validate_config_value(key, value):
                        validation_report['validated_keys'] += 1
                    else:
                        validation_report['warnings'].append(f"Valor questionável para '{key}': {value}")
                        
                except Exception as e:
                    validation_report['errors'].append(f"Erro ao validar '{key}': {e}")
            
            # Determinar status final
            if validation_report['errors']:
                validation_report['status'] = 'error'
                self.metrics['validation_errors'] += len(validation_report['errors'])
            elif validation_report['warnings']:
                validation_report['status'] = 'warning'
            
            self.logger.info(f"✅ Validação concluída: {target_profile} - {validation_report['status']}")
            
            return validation_report
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação: {e}")
            return {
                'profile': target_profile,
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def register_config_watcher(self, key_pattern: str, callback, name: Optional[str] = None) -> str:
        """
        Registra um watcher para mudanças de configuração.
        
        Args:
            key_pattern: Padrão de chave para observar
            callback: Função a chamar quando houver mudança
            name: Nome do watcher
            
        Returns:
            ID do watcher registrado
        """
        try:
            watcher_id = name or f"watcher_{len(self.config_watchers)}_{datetime.now().timestamp()}"
            
            self.config_watchers[watcher_id] = {
                'pattern': key_pattern,
                'callback': callback,
                'registered_at': datetime.now().isoformat(),
                'trigger_count': 0
            }
            
            self.logger.info(f"👁️ Watcher registrado: {watcher_id} para padrão '{key_pattern}'")
            return watcher_id
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao registrar watcher: {e}")
            return ""
    
    def export_config(self, profile: Optional[str] = None, format: str = 'json') -> str:
        """
        Exporta configurações em formato especificado.
        
        Args:
            profile: Profile a exportar (todos se None)
            format: Formato de exportação ('json' apenas - sem YAML)
            
        Returns:
            String com configurações exportadas
        """
        try:
            if profile:
                data = {profile: self.get_profile_config(profile)}
            else:
                data = self.configurations.copy()
            
            # Adicionar metadados
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'active_profile': self.active_profile,
                'configurations': data
            }
            
            # Sempre JSON (removida dependência YAML)
            return json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao exportar configurações: {e}")
            return "{}"
    
    def import_config(self, config_string: str, format: str = 'json', profile: Optional[str] = None) -> bool:
        """
        Importa configurações de string.
        
        Args:
            config_string: String com configurações
            format: Formato da string ('json' apenas)
            profile: Profile de destino (detecta automaticamente se None)
            
        Returns:
            True se importado com sucesso
        """
        try:
            # Parse da string (apenas JSON)
            data = json.loads(config_string)
            
            # Extrair configurações
            if 'configurations' in data:
                import_configs = data['configurations']
            else:
                import_configs = data
            
            # Importar cada profile
            imported_count = 0
            for profile_name, profile_config in import_configs.items():
                target_profile = profile or profile_name
                
                # Validar antes de importar
                if self._validate_profile_config(profile_config):
                    self.configurations[target_profile] = profile_config
                    self._save_profile_config(target_profile)
                    imported_count += 1
                    self.logger.info(f"✅ Profile importado: {target_profile}")
                else:
                    self.logger.warning(f"⚠️ Profile inválido não importado: {profile_name}")
            
            return imported_count > 0
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao importar configurações: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Obtém status do sistema de configuração.
        
        Returns:
            Status detalhado do sistema
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'active_profile': self.active_profile,
            'available_profiles': list(self.profiles.keys()),
            'loaded_profiles': list(self.configurations.keys()),
            'config_watchers': len(self.config_watchers),
            'metrics': self.metrics.copy(),
            'config_path': str(self.config_path),
            'change_history_count': len(self.change_history)
        }
    
    def _get_default_config_path(self) -> str:
        """Obtém caminho padrão do arquivo de configuração."""
        # Tentar diretório atual primeiro
        current_dir = Path.cwd()
        config_candidates = [
            current_dir / 'config' / 'system_config.json',
            current_dir / 'config.json',
            current_dir / 'settings.json',
            Path(__file__).parent / 'system_config.json'
        ]
        
        for candidate in config_candidates:
            if candidate.exists():
                return str(candidate)
        
        # Usar o primeiro candidato como padrão se nenhum existir
        return str(config_candidates[0])
    
    def _detect_active_profile(self) -> str:
        """Detecta profile ativo baseado no ambiente."""
        # Verificar variável de ambiente
        env_profile = os.getenv('SYSTEM_PROFILE', '').lower()
        if env_profile in self.profiles:
            return env_profile
        
        # Verificar variáveis Flask/Django
        flask_env = os.getenv('FLASK_ENV', '').lower()
        django_env = os.getenv('DJANGO_SETTINGS_MODULE', '').lower()
        
        if 'prod' in flask_env or 'prod' in django_env:
            return 'production'
        elif 'test' in flask_env or 'test' in django_env:
            return 'testing'
        elif 'stage' in flask_env or 'stage' in django_env:
            return 'staging'
        else:
            return 'development'
    
    def _initialize_default_configurations(self) -> Dict[str, Any]:
        """Inicializa configurações padrão."""
        return {
            'system': {
                'name': 'Claude AI Novo',
                'version': '2.0.0',
                'debug': False,
                'log_level': 'INFO'
            },
            'database': {
                'connection_timeout': 30,
                'pool_size': 10,
                'retry_attempts': 3
            },
            'ai': {
                'model': 'claude-sonnet-4',
                'max_tokens': 4000,
                'temperature': 0.7,
                'timeout_seconds': 120
            },
            'claude_api': {
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 8192,
                'temperature_balanced': 0.7,
                'temperature_precision': 0.1,
                'temperature_creative': 0.9,
                'top_p': 0.95,
                'timeout_seconds': 120,
                'retry_attempts': 3,
                'max_output_tokens': 8192
            },
            'cache': {
                'enabled': True,
                'ttl_minutes': 30,
                'max_size': 1000
            },
            'security': {
                'jwt_expiry_hours': 24,
                'max_login_attempts': 5,
                'password_min_length': 8
            },
            'monitoring': {
                'metrics_enabled': True,
                'log_retention_days': 30,
                'alert_threshold': 0.8
            }
        }
    
    def _load_initial_configurations(self):
        """Carrega configurações iniciais."""
        try:
            # Tentar carregar configuração do profile ativo
            self._load_profile_config(self.active_profile)
            
            # Tentar carregar configurações globais
            self._load_profile_config('global')
            
            self.logger.info(f"✅ Configurações iniciais carregadas (profile: {self.active_profile})")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao carregar configurações iniciais: {e}")
            # Usar apenas configurações padrão
            self.configurations[self.active_profile] = self.default_configurations.copy()
    
    def _load_profile_config(self, profile: str):
        """Carrega configuração de um profile específico."""
        profile_path = self._get_profile_config_path(profile)
        
        if profile_path.exists():
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                self.configurations[profile] = config_data
                self.metrics['config_loads'] += 1
                
                self.logger.debug(f"📂 Configuração carregada: {profile} ({profile_path})")
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao carregar {profile_path}: {e}")
                raise
        else:
            # Criar configuração padrão para o profile
            self.configurations[profile] = self.default_configurations.copy()
            self._save_profile_config(profile)
    
    def _save_profile_config(self, profile: str):
        """Salva configuração de um profile."""
        if profile not in self.configurations:
            return
        
        profile_path = self._get_profile_config_path(profile)
        
        try:
            # Garantir que diretório existe
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(self.configurations[profile], f, indent=2, ensure_ascii=False, default=str)
            
            self.metrics['config_saves'] += 1
            self.logger.debug(f"💾 Configuração salva: {profile} ({profile_path})")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar {profile_path}: {e}")
    
    def _get_profile_config_path(self, profile: str) -> Path:
        """Obtém caminho do arquivo de configuração do profile."""
        config_dir = Path(self.config_path).parent
        return config_dir / f"{profile}_config.json"
    
    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """Obtém valor usando notação de ponto (ex: 'section.subsection.key')."""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current
    
    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any):
        """Define valor usando notação de ponto."""
        keys = key.split('.')
        current = data
        
        # Navegar até o penúltimo nível
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Definir valor final
        current[keys[-1]] = value
    
    def _validate_config_value(self, key: str, value: Any) -> bool:
        """Valida um valor de configuração."""
        try:
            # Validações específicas por chave
            if 'timeout' in key.lower() and isinstance(value, (int, float)):
                return value > 0
            
            if 'port' in key.lower() and isinstance(value, int):
                return 1 <= value <= 65535
            
            if 'max_' in key.lower() and isinstance(value, (int, float)):
                return value >= 0
            
            if 'enabled' in key.lower():
                return isinstance(value, bool)
            
            # Validação geral - não pode ser None para chaves críticas
            critical_keys = ['system.name', 'database.host', 'ai.model']
            if key in critical_keys:
                return value is not None and str(value).strip() != ''
            
            return True
            
        except Exception:
            return False
    
    def _validate_profile_config(self, config: Dict[str, Any]) -> bool:
        """Valida configuração completa de um profile."""
        try:
            if not isinstance(config, dict):
                return False
            
            # Verificar se contém pelo menos uma seção
            if not config:
                return False
            
            # Validar estrutura básica
            for section_name, section_data in config.items():
                if not isinstance(section_data, dict):
                    continue
                
                for key, value in section_data.items():
                    full_key = f"{section_name}.{key}"
                    if not self._validate_config_value(full_key, value):
                        self.logger.warning(f"⚠️ Valor inválido: {full_key} = {value}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação do profile: {e}")
            return False
    
    def _flatten_dict(self, data: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """Aplaina dicionário aninhado."""
        flattened = {}
        
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                flattened.update(self._flatten_dict(value, full_key))
            else:
                flattened[full_key] = value
        
        return flattened
    
    def _record_config_change(self, key: str, old_value: Any, new_value: Any, profile: str):
        """Registra mudança de configuração no histórico."""
        change_record = {
            'timestamp': datetime.now().isoformat(),
            'profile': profile,
            'key': key,
            'old_value': old_value,
            'new_value': new_value,
            'change_type': 'update' if old_value is not None else 'create'
        }
        
        self.change_history.append(change_record)
        
        # Manter apenas últimas 1000 mudanças
        if len(self.change_history) > 1000:
            self.change_history = self.change_history[-1000:]
    
    def _record_profile_switch(self, old_profile: str, new_profile: str):
        """Registra mudança de profile."""
        change_record = {
            'timestamp': datetime.now().isoformat(),
            'change_type': 'profile_switch',
            'old_profile': old_profile,
            'new_profile': new_profile
        }
        
        self.change_history.append(change_record)
    
    def _notify_config_watchers(self, key: str, new_value: Any, old_value: Any, profile: str):
        """Notifica watchers sobre mudanças."""
        for watcher_id, watcher_info in self.config_watchers.items():
            try:
                pattern = watcher_info['pattern']
                
                # Verificar se chave corresponde ao padrão
                if self._key_matches_pattern(key, pattern):
                    callback = watcher_info['callback']
                    
                    # Chamar callback
                    callback(key, new_value, old_value, profile)
                    
                    # Incrementar contador
                    watcher_info['trigger_count'] += 1
                    
            except Exception as e:
                self.logger.error(f"❌ Erro ao notificar watcher {watcher_id}: {e}")
    
    def _key_matches_pattern(self, key: str, pattern: str) -> bool:
        """Verifica se chave corresponde ao padrão."""
        # Suporte básico a wildcards
        if '*' in pattern:
            import fnmatch
            return fnmatch.fnmatch(key, pattern)
        else:
            return key == pattern or key.startswith(pattern + '.')


def get_system_config() -> SystemConfig:
    """
    Obtém instância do gerenciador de configuração.
    
    Returns:
        Instância do SystemConfig
    """
    return SystemConfig() 