#!/usr/bin/env python3
"""
🧠 SYSTEM MEMORY - Memória do Sistema
====================================

Módulo responsável por memorizar configurações e estado do sistema.
Responsabilidade: MEMORIZAR estado e configurações do sistema.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import json
import os

# Flask fallback para execução standalone
try:
    from app.utils.redis_cache import redis_cache, REDIS_DISPONIVEL
    from app.claude_ai_novo.config import ClaudeAIConfig, AdvancedConfig
except ImportError:
    # Fallback quando não há Flask
    try:
        from unittest.mock import Mock
    except ImportError:
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
            def __call__(self, *args, **kwargs):
                return self
            def __getattr__(self, name):
                return self
    redis_cache = Mock()
    REDIS_DISPONIVEL = False
    ClaudeAIConfig = AdvancedConfig = Mock()

# Configurar logger
logger = logging.getLogger(__name__)

class SystemMemory:
    """
    Memória do sistema para configurações e estado.
    
    Responsável por armazenar e recuperar configurações do sistema,
    estado de componentes e informações de desempenho.
    """
    
    def __init__(self):
        """Inicializa a memória do sistema"""
        self.logger = logging.getLogger(__name__)
        self.memory_timeout = 86400  # 24 horas
        self.local_cache = {}        # Cache local como fallback
        self.system_state = {
            'initialized': datetime.now().isoformat(),
            'version': '1.0.0',
            'components': {},
            'performance': {}
        }
        
    def store_system_config(self, config_key: str, config_value: Any) -> bool:
        """
        Armazena configuração do sistema.
        
        Args:
            config_key: Chave da configuração
            config_value: Valor da configuração
            
        Returns:
            True se armazenado com sucesso, False caso contrário
        """
        try:
            config_data = {
                'key': config_key,
                'value': config_value,
                'timestamp': datetime.now().isoformat(),
                'type': type(config_value).__name__
            }
            
            # Tentar armazenar no Redis primeiro
            if REDIS_DISPONIVEL:
                key = f"system_memory:config:{config_key}"
                if redis_cache:
                    redis_cache.set(key, config_data, ttl=self.memory_timeout)
                self.logger.info(f"✅ Configuração armazenada no Redis: {config_key}")
                return True
            else:
                # Fallback para cache local
                self.local_cache[f"config:{config_key}"] = {
                    'data': config_data,
                    'timestamp': datetime.now().timestamp()
                }
                self.logger.info(f"✅ Configuração armazenada localmente: {config_key}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao armazenar configuração: {e}")
            return False
    
    def retrieve_system_config(self, config_key: str) -> Optional[Any]:
        """
        Recupera configuração do sistema.
        
        Args:
            config_key: Chave da configuração
            
        Returns:
            Valor da configuração ou None se não encontrado
        """
        try:
            # Tentar recuperar do Redis primeiro
            if REDIS_DISPONIVEL:
                key = f"system_memory:config:{config_key}"
                config_data = None
                if redis_cache:
                    config_data = redis_cache.get(key)
                if config_data:
                    self.logger.info(f"✅ Configuração recuperada do Redis: {config_key}")
                    return config_data.get('value')
            
            # Fallback para cache local
            cache_key = f"config:{config_key}"
            if cache_key in self.local_cache:
                cached = self.local_cache[cache_key]
                # Verificar se não expirou
                if datetime.now().timestamp() - cached['timestamp'] < self.memory_timeout:
                    self.logger.info(f"✅ Configuração recuperada localmente: {config_key}")
                    return cached['data']['value']
                else:
                    # Remover configuração expirada
                    del self.local_cache[cache_key]
            
            self.logger.info(f"📭 Configuração não encontrada: {config_key}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao recuperar configuração: {e}")
            return None
    
    def store_component_state(self, component_name: str, state: Dict[str, Any]) -> bool:
        """
        Armazena estado de um componente.
        
        Args:
            component_name: Nome do componente
            state: Estado do componente
            
        Returns:
            True se armazenado com sucesso, False caso contrário
        """
        try:
            state_data = {
                'component': component_name,
                'state': state,
                'timestamp': datetime.now().isoformat(),
                'status': state.get('status', 'unknown')
            }
            
            # Atualizar estado local
            self.system_state['components'][component_name] = state_data
            
            # Tentar armazenar no Redis
            if REDIS_DISPONIVEL:
                key = f"system_memory:component:{component_name}"
                if redis_cache:
                    redis_cache.set(key, state_data, ttl=self.memory_timeout)
                self.logger.info(f"✅ Estado do componente armazenado: {component_name}")
                return True
            else:
                # Fallback para cache local
                self.local_cache[f"component:{component_name}"] = {
                    'data': state_data,
                    'timestamp': datetime.now().timestamp()
                }
                self.logger.info(f"✅ Estado do componente armazenado localmente: {component_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao armazenar estado do componente: {e}")
            return False
    
    def retrieve_component_state(self, component_name: str) -> Optional[Dict[str, Any]]:
        """
        Recupera estado de um componente.
        
        Args:
            component_name: Nome do componente
            
        Returns:
            Estado do componente ou None se não encontrado
        """
        try:
            # Tentar recuperar do Redis primeiro
            if REDIS_DISPONIVEL:
                key = f"system_memory:component:{component_name}"
                state_data = None
                if redis_cache:
                    state_data = redis_cache.get(key)
                if state_data:
                    self.logger.info(f"✅ Estado do componente recuperado do Redis: {component_name}")
                    return state_data.get('state')
            
            # Fallback para cache local
            cache_key = f"component:{component_name}"
            if cache_key in self.local_cache:
                cached = self.local_cache[cache_key]
                # Verificar se não expirou
                if datetime.now().timestamp() - cached['timestamp'] < self.memory_timeout:
                    self.logger.info(f"✅ Estado do componente recuperado localmente: {component_name}")
                    return cached['data']['state']
                else:
                    # Remover estado expirado
                    del self.local_cache[cache_key]
            
            # Verificar estado local
            if component_name in self.system_state['components']:
                return self.system_state['components'][component_name]['state']
            
            self.logger.info(f"📭 Estado do componente não encontrado: {component_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao recuperar estado do componente: {e}")
            return None
    
    def store_performance_metric(self, metric_name: str, value: Union[int, float], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Armazena métrica de desempenho.
        
        Args:
            metric_name: Nome da métrica
            value: Valor da métrica
            metadata: Metadados adicionais
            
        Returns:
            True se armazenado com sucesso, False caso contrário
        """
        try:
            metric_data = {
                'name': metric_name,
                'value': value,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # Atualizar performance local
            if metric_name not in self.system_state['performance']:
                self.system_state['performance'][metric_name] = []
            
            self.system_state['performance'][metric_name].append(metric_data)
            
            # Limitar histórico (últimas 100 métricas)
            if len(self.system_state['performance'][metric_name]) > 100:
                self.system_state['performance'][metric_name] = self.system_state['performance'][metric_name][-100:]
            
            # Tentar armazenar no Redis
            if REDIS_DISPONIVEL:
                key = f"system_memory:performance:{metric_name}"
                if redis_cache:
                    redis_cache.set(key, metric_data, ttl=self.memory_timeout)
                self.logger.info(f"✅ Métrica de desempenho armazenada: {metric_name}")
                return True
            else:
                self.logger.info(f"✅ Métrica de desempenho armazenada localmente: {metric_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao armazenar métrica de desempenho: {e}")
            return False
    
    def get_system_overview(self) -> Dict[str, Any]:
        """
        Retorna visão geral do sistema.
        
        Returns:
            Dict com informações gerais do sistema
        """
        try:
            overview = {
                'system_info': {
                    'initialized': self.system_state['initialized'],
                    'version': self.system_state['version'],
                    'uptime': self._calculate_uptime(),
                    'memory_type': 'Redis' if REDIS_DISPONIVEL else 'Local'
                },
                'components': {
                    'total': len(self.system_state['components']),
                    'active': len([c for c in self.system_state['components'].values() 
                                 if c.get('state', {}).get('status') == 'active']),
                    'components': list(self.system_state['components'].keys())
                },
                'performance': {
                    'metrics_count': len(self.system_state['performance']),
                    'metrics': list(self.system_state['performance'].keys())
                },
                'memory_stats': {
                    'local_cache_size': len(self.local_cache),
                    'redis_available': REDIS_DISPONIVEL
                }
            }
            
            return overview
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter visão geral do sistema: {e}")
            return {'error': str(e)}
    
    def get_component_status(self) -> Dict[str, str]:
        """
        Retorna status de todos os componentes.
        
        Returns:
            Dict com status dos componentes
        """
        try:
            status = {}
            
            for component_name, component_data in self.system_state['components'].items():
                status[component_name] = component_data.get('state', {}).get('status', 'unknown')
            
            return status
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter status dos componentes: {e}")
            return {}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo de desempenho.
        
        Returns:
            Dict com resumo de desempenho
        """
        try:
            summary = {}
            
            for metric_name, metrics in self.system_state['performance'].items():
                if metrics:
                    values = [m['value'] for m in metrics]
                    summary[metric_name] = {
                        'count': len(values),
                        'latest': values[-1] if values else None,
                        'average': sum(values) / len(values) if values else 0,
                        'min': min(values) if values else None,
                        'max': max(values) if values else None
                    }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter resumo de desempenho: {e}")
            return {}
    
    def cleanup_expired_data(self) -> int:
        """
        Limpa dados expirados.
        
        Returns:
            Número de itens limpos
        """
        try:
            cleaned = 0
            current_time = datetime.now().timestamp()
            
            # Limpar cache local
            expired_keys = []
            for key, cached in self.local_cache.items():
                if current_time - cached['timestamp'] >= self.memory_timeout:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.local_cache[key]
                cleaned += 1
            
            if cleaned > 0:
                self.logger.info(f"🧹 Dados expirados limpos: {cleaned}")
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao limpar dados expirados: {e}")
            return 0
    
    def _calculate_uptime(self) -> str:
        """
        Calcula tempo de atividade do sistema.
        
        Returns:
            String com tempo de atividade
        """
        try:
            init_time = datetime.fromisoformat(self.system_state['initialized'])
            uptime = datetime.now() - init_time
            
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m {seconds}s"
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao calcular uptime: {e}")
            return "unknown"


# Instância global
_system_memory = None

def get_system_memory():
    """Retorna instância do SystemMemory"""
    global _system_memory
    if _system_memory is None:
        _system_memory = SystemMemory()
    return _system_memory 