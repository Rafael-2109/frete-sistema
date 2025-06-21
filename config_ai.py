#!/usr/bin/env python3
"""
🤖 CONFIGURAÇÃO MCP v4.0 AVANÇADO
Configurações específicas para IA, ML e sistemas inteligentes
"""

import os
from datetime import timedelta
from typing import Dict, Any

class AIConfig:
    """Configurações para o sistema de IA"""
    
    # ==========================================
    # 🔄 REDIS & CACHE CONFIGURATION
    # ==========================================
    
    # Redis principal para cache real-time
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
    
    # Redis para dados de ML (DB separado)
    REDIS_ML_DB = int(os.environ.get('REDIS_ML_DB', 1))
    
    # Cache timeouts (em segundos)
    CACHE_TIMEOUTS = {
        'real_time_metrics': 30,        # Métricas em tempo real
        'ai_insights': 300,             # Insights da IA (5 min)
        'ml_predictions': 1800,         # Previsões ML (30 min)
        'user_context': 3600,           # Contexto do usuário (1 hora)
        'dashboard_data': 60,           # Dados do dashboard (1 min)
        'system_status': 120,           # Status do sistema (2 min)
        'alerts_cache': 15,             # Cache de alertas (15 seg)
        'query_results': 600            # Resultados de consultas (10 min)
    }
    
    # ==========================================
    # 🧠 MACHINE LEARNING CONFIGURATION
    # ==========================================
    
    # Diretório para modelos ML
    ML_MODELS_DIR = os.path.join(os.getcwd(), 'ml_models')
    
    # Configurações de modelos
    ML_CONFIG = {
        'delay_predictor': {
            'retrain_interval_hours': 24,   # Retreinar a cada 24h
            'min_samples': 100,             # Mínimo de amostras para treinar
            'accuracy_threshold': 0.85,     # Acurácia mínima aceitável
            'feature_importance_threshold': 0.01
        },
        'anomaly_detector': {
            'retrain_interval_hours': 12,
            'contamination_rate': 0.1,      # Taxa de anomalias esperada
            'confidence_threshold': 0.8
        },
        'cost_optimizer': {
            'retrain_interval_hours': 48,
            'optimization_target': 'minimize_cost',
            'constraint_tolerance': 0.05
        }
    }
    
    # ==========================================
    # 🔮 NLP & LANGUAGE PROCESSING
    # ==========================================
    
    # Configurações do processador NLP
    NLP_CONFIG = {
        'spacy_model': 'pt_core_news_lg',   # Modelo em português
        'confidence_threshold': 0.7,        # Threshold para classificação
        'max_context_length': 10,           # Máximo de mensagens no contexto
        'intent_classes': [
            'query_data', 'request_analysis', 'ask_prediction',
            'set_alert', 'export_data', 'get_status', 'optimize_route'
        ],
        'entity_types': [
            'CLIENTE', 'TRANSPORTADORA', 'DATA', 'VALOR', 'CIDADE', 'UF'
        ]
    }
    
    # Configurações de LLM (se usar)
    LLM_CONFIG = {
        'provider': 'openai',  # ou 'huggingface', 'anthropic'
        'model': 'gpt-3.5-turbo',
        'temperature': 0.7,
        'max_tokens': 1000,
        'timeout': 30
    }
    
    # ==========================================
    # 📊 ANALYTICS & DASHBOARDS
    # ==========================================
    
    # Configurações do dashboard
    DASHBOARD_CONFIG = {
        'refresh_interval_ms': 5000,    # Refresh a cada 5 segundos
        'max_data_points': 100,         # Máximo de pontos nos gráficos
        'real_time_widgets': [
            'active_shipments', 'delay_predictions', 
            'cost_savings', 'efficiency_score'
        ],
        'chart_types': {
            'time_series': 'line',
            'distribution': 'histogram',
            'correlation': 'heatmap',
            'geospatial': 'mapbox'
        }
    }
    
    # Configurações de métricas
    METRICS_CONFIG = {
        'collection_interval_seconds': 30,
        'retention_days': 90,
        'aggregation_levels': ['minute', 'hour', 'day', 'week', 'month'],
        'kpi_thresholds': {
            'efficiency_score': {'warning': 0.7, 'critical': 0.5},
            'delay_rate': {'warning': 0.15, 'critical': 0.25},
            'cost_variance': {'warning': 0.1, 'critical': 0.2}
        }
    }
    
    # ==========================================
    # 🔔 ALERTS & NOTIFICATIONS
    # ==========================================
    
    # Configurações de alertas
    ALERTS_CONFIG = {
        'processing_interval_seconds': 60,  # Processar alertas a cada minuto
        'max_alerts_per_user_per_hour': 10, # Limite de alertas por usuário
        'severity_levels': ['low', 'medium', 'high', 'critical'],
        'channels': {
            'email': {
                'enabled': True,
                'smtp_server': os.environ.get('SMTP_SERVER'),
                'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
                'username': os.environ.get('SMTP_USERNAME'),
                'password': os.environ.get('SMTP_PASSWORD')
            },
            'whatsapp': {
                'enabled': False,  # Para implementar futuramente
                'api_key': os.environ.get('WHATSAPP_API_KEY'),
                'phone_number': os.environ.get('WHATSAPP_PHONE')
            },
            'slack': {
                'enabled': False,  # Para implementar futuramente
                'webhook_url': os.environ.get('SLACK_WEBHOOK_URL'),
                'channel': '#alerts'
            }
        }
    }
    
    # ==========================================
    # 🔄 AUTOMATION & WORKFLOWS
    # ==========================================
    
    # Configurações de automação
    AUTOMATION_CONFIG = {
        'enabled': True,
        'max_concurrent_workflows': 10,
        'workflow_timeout_minutes': 30,
        'retry_attempts': 3,
        'retry_delay_seconds': 60,
        'auto_approve_threshold': 0.95,  # Auto-aprovar se confiança > 95%
        'workflows': {
            'daily_report': {
                'schedule': '0 8 * * *',  # Todo dia às 8h
                'enabled': True,
                'recipients': ['manager@empresa.com']
            },
            'weekly_analysis': {
                'schedule': '0 9 * * 1',  # Segunda-feira às 9h
                'enabled': True,
                'include_predictions': True
            },
            'anomaly_response': {
                'auto_trigger': True,
                'escalation_minutes': 15,
                'max_escalation_level': 3
            }
        }
    }
    
    # ==========================================
    # 🌐 EXTERNAL INTEGRATIONS
    # ==========================================
    
    # APIs externas
    EXTERNAL_APIS = {
        'weather': {
            'provider': 'openweathermap',
            'api_key': os.environ.get('WEATHER_API_KEY'),
            'base_url': 'https://api.openweathermap.org/data/2.5',
            'timeout': 10,
            'cache_hours': 1
        },
        'traffic': {
            'provider': 'google_maps',
            'api_key': os.environ.get('GOOGLE_MAPS_API_KEY'),
            'base_url': 'https://maps.googleapis.com/maps/api',
            'timeout': 15,
            'cache_minutes': 30
        },
        'logistics': {
            'provider': 'custom',
            'enabled': False,
            'endpoints': {}
        }
    }
    
    # ==========================================
    # 🧪 TESTING & DEVELOPMENT
    # ==========================================
    
    # Configurações de teste
    TESTING_CONFIG = {
        'mock_external_apis': True,
        'generate_synthetic_data': True,
        'test_data_size': 1000,
        'performance_test_duration_seconds': 60,
        'load_test_concurrent_users': 50
    }
    
    # Configurações de desenvolvimento
    DEV_CONFIG = {
        'debug_mode': os.environ.get('AI_DEBUG', 'False').lower() == 'true',
        'log_level': os.environ.get('AI_LOG_LEVEL', 'INFO'),
        'profiling_enabled': False,
        'hot_reload': True
    }
    
    # ==========================================
    # 📈 PERFORMANCE & OPTIMIZATION
    # ==========================================
    
    # Configurações de performance
    PERFORMANCE_CONFIG = {
        'max_memory_usage_mb': 2048,    # Máximo 2GB de RAM
        'max_cpu_usage_percent': 80,    # Máximo 80% CPU
        'async_workers': 4,             # Workers assíncronos
        'thread_pool_size': 10,         # Thread pool
        'connection_pool_size': 20,     # Pool de conexões DB
        'query_timeout_seconds': 30,    # Timeout para queries
        'batch_processing_size': 100    # Tamanho dos lotes
    }
    
    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """Retorna configuração completa do Redis"""
        return {
            'host': cls.REDIS_HOST,
            'port': cls.REDIS_PORT,
            'db': cls.REDIS_DB,
            'password': cls.REDIS_PASSWORD,
            'decode_responses': True,
            'socket_timeout': 5,
            'socket_connect_timeout': 5,
            'retry_on_timeout': True,
            'health_check_interval': 30
        }
    
    @classmethod
    def get_ml_redis_config(cls) -> Dict[str, Any]:
        """Retorna configuração do Redis para ML"""
        config = cls.get_redis_config()
        config['db'] = cls.REDIS_ML_DB
        return config
    
    @classmethod
    def validate_config(cls) -> bool:
        """Valida se as configurações estão corretas"""
        try:
            # Verificar se diretórios existem
            os.makedirs(cls.ML_MODELS_DIR, exist_ok=True)
            
            # Verificar configurações críticas
            required_configs = [
                cls.REDIS_HOST,
                cls.NLP_CONFIG['spacy_model'],
                cls.CACHE_TIMEOUTS
            ]
            
            for config in required_configs:
                if not config:
                    return False
            
            return True
            
        except Exception as e:
            print(f"Erro na validação da configuração: {e}")
            return False

# Instância global da configuração
ai_config = AIConfig()

# Validar configuração na importação
if not ai_config.validate_config():
    print("⚠️ Aviso: Algumas configurações de IA podem estar inválidas")
else:
    print("✅ Configurações de IA validadas com sucesso") 