#!/usr/bin/env python3
"""
📊 SISTEMA DE MONITORAMENTO E ALERTAS
Configurações para monitoramento de performance e alertas
"""

import os
from datetime import timedelta
from typing import Dict, Any, List

class MonitoringConfig:
    """Configurações de monitoramento do sistema"""
    
    # ==========================================
    # 📈 MÉTRICAS DE PERFORMANCE
    # ==========================================
    
    # Thresholds de alerta para métricas principais
    PERFORMANCE_THRESHOLDS = {
        'response_time': {
            'warning': 1.0,    # 1 segundo
            'critical': 3.0    # 3 segundos
        },
        'memory_usage': {
            'warning': 0.80,   # 80%
            'critical': 0.95   # 95%
        },
        'cpu_usage': {
            'warning': 0.70,   # 70%
            'critical': 0.90   # 90%
        },
        'disk_usage': {
            'warning': 0.80,   # 80%
            'critical': 0.95   # 95%
        },
        'database_connections': {
            'warning': 15,     # 15 conexões
            'critical': 20     # 20 conexões (máximo)
        },
        'redis_connections': {
            'warning': 40,     # 40 conexões
            'critical': 50     # 50 conexões (máximo)
        }
    }
    
    # ==========================================
    # 🔍 MONITORAMENTO DE AI/CLAUDE
    # ==========================================
    
    AI_MONITORING = {
        'api_calls_per_minute': {
            'warning': 45,     # 45 calls/min
            'critical': 55     # 55 calls/min (limite: 60)
        },
        'api_response_time': {
            'warning': 5.0,    # 5 segundos
            'critical': 10.0   # 10 segundos
        },
        'api_error_rate': {
            'warning': 0.05,   # 5% erro
            'critical': 0.15   # 15% erro
        },
        'cache_hit_rate': {
            'warning': 0.70,   # 70% hit rate
            'critical': 0.50   # 50% hit rate
        },
        'context_memory_usage': {
            'warning': 50,     # 50 conversas ativas
            'critical': 80     # 80 conversas ativas
        }
    }
    
    # ==========================================
    # 🚨 ALERTAS CRÍTICOS DO NEGÓCIO
    # ==========================================
    
    BUSINESS_ALERTS = {
        'embarques_atrasados': {
            'threshold': 5,    # 5 embarques atrasados
            'check_interval': 300,  # Verificar a cada 5 min
            'severity': 'high'
        },
        'fretes_sem_aprovacao': {
            'threshold': 10,   # 10 fretes pendentes
            'check_interval': 600,  # Verificar a cada 10 min
            'severity': 'medium'
        },
        'sistema_indisponivel': {
            'threshold': 3,    # 3 falhas consecutivas
            'check_interval': 60,   # Verificar a cada 1 min
            'severity': 'critical'
        },
        'backup_falhou': {
            'check_interval': 3600,  # Verificar a cada 1 hora
            'severity': 'high'
        }
    }
    
    # ==========================================
    # 📧 CONFIGURAÇÕES DE NOTIFICAÇÃO
    # ==========================================
    
    NOTIFICATION_CONFIG = {
        'email': {
            'enabled': True,
            'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
            'username': os.environ.get('SMTP_USERNAME'),
            'password': os.environ.get('SMTP_PASSWORD'),
            'from_email': os.environ.get('ALERT_FROM_EMAIL', 'sistema@empresa.com'),
            'to_emails': [
                'admin@empresa.com',
                'ti@empresa.com'
            ]
        },
        'webhook': {
            'enabled': False,
            'urls': [
                os.environ.get('WEBHOOK_URL_SLACK'),
                os.environ.get('WEBHOOK_URL_TEAMS')
            ]
        }
    }
    
    # ==========================================
    # 🔄 HEALTH CHECKS
    # ==========================================
    
    HEALTH_CHECKS = {
        'database': {
            'query': 'SELECT 1',
            'timeout': 5,
            'interval': 30
        },
        'redis': {
            'command': 'ping',
            'timeout': 5,
            'interval': 30
        },
        'claude_api': {
            'endpoint': 'https://api.anthropic.com/v1/messages',
            'method': 'OPTIONS',
            'timeout': 10,
            'interval': 300  # 5 minutos
        },
        'file_storage': {
            'test_upload': True,
            'timeout': 10,
            'interval': 600  # 10 minutos
        }
    }
    
    # ==========================================
    # 📊 DASHBOARDS E RELATÓRIOS
    # ==========================================
    
    DASHBOARD_CONFIG = {
        'real_time_refresh': 5,      # 5 segundos
        'metrics_retention': 30,     # 30 dias
        'charts_refresh': 60,        # 1 minuto
        'export_formats': ['pdf', 'excel', 'json'],
        'auto_reports': {
            'daily': {
                'enabled': True,
                'time': '08:00',
                'recipients': ['gerencia@empresa.com']
            },
            'weekly': {
                'enabled': True,
                'day': 'monday',
                'time': '09:00',
                'recipients': ['diretoria@empresa.com']
            }
        }
    }
    
    # ==========================================
    # 🔧 CONFIGURAÇÕES AVANÇADAS
    # ==========================================
    
    ADVANCED_CONFIG = {
        'anomaly_detection': {
            'enabled': True,
            'sensitivity': 0.8,
            'learning_period_days': 7,
            'alert_threshold': 0.9
        },
        'predictive_alerts': {
            'enabled': True,
            'forecast_hours': 24,
            'confidence_threshold': 0.85
        },
        'auto_scaling': {
            'enabled': False,  # Para implementar futuramente
            'cpu_threshold': 0.80,
            'memory_threshold': 0.85,
            'scale_cooldown': 300
        }
    }
    
    @classmethod
    def get_alert_config(cls, alert_type: str) -> Dict[str, Any]:
        """Retorna configuração específica de um alerta"""
        configs = {
            **cls.PERFORMANCE_THRESHOLDS,
            **cls.AI_MONITORING,
            **cls.BUSINESS_ALERTS
        }
        return configs.get(alert_type, {})
    
    @classmethod
    def should_send_alert(cls, metric: str, value: float, level: str = 'warning') -> bool:
        """Determina se deve enviar alerta baseado no valor da métrica"""
        thresholds = cls.get_alert_config(metric)
        if not thresholds or level not in thresholds:
            return False
        
        return value >= thresholds[level]
    
    @classmethod
    def get_notification_channels(cls, severity: str) -> List[str]:
        """Retorna canais de notificação baseado na severidade"""
        channels = []
        
        if severity in ['critical', 'high']:
            if cls.NOTIFICATION_CONFIG['email']['enabled']:
                channels.append('email')
            if cls.NOTIFICATION_CONFIG['webhook']['enabled']:
                channels.append('webhook')
        elif severity == 'medium':
            if cls.NOTIFICATION_CONFIG['email']['enabled']:
                channels.append('email')
        
        return channels

# Instância global
monitoring_config = MonitoringConfig() 