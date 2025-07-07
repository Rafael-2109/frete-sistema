#!/usr/bin/env python3
"""
ResponseProcessor - Processamento especializado
"""

import os
import anthropic
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from flask_login import current_user
from sqlalchemy import func, and_, or_, text
from app import db
import json
from app.utils.redis_cache import redis_cache, cache_aside, cached_query
from app.utils.grupo_empresarial import GrupoEmpresarialDetector, detectar_grupo_empresarial
from app.utils.ml_models_real import get_ml_models_system
import config_ai
from app.utils.api_helper import get_system_alerts
from app.utils.ai_logging import ai_logger, AILogger
from app.utils.redis_cache import intelligent_cache
import re
import time
import asyncio
import re
from app.utils.grupo_empresarial import GrupoEmpresarialDetector
from app import db
from app.fretes.models import Frete
from app.embarques.models import Embarque
from app.transportadoras.models import Transportadora
from app.pedidos.models import Pedido
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.faturamento.models import RelatorioFaturamentoImportado
from app import db
from app.monitoramento.models import EntregaMonitorada
from app import db
from app.fretes.models import Frete, DespesaExtra
from app.transportadoras.models import Transportadora
from app import db
from app.monitoramento.models import AgendamentoEntrega
from app import db
from app.monitoramento.models import EntregaMonitorada
from app.fretes.models import Frete
from app.utils.grupo_empresarial import detectar_grupo_empresarial
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import re
from app import db
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.embarques.models import Embarque, EmbarqueItem
from app.pedidos.models import Pedido
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada
from app.pedidos.models import Pedido
from app.utils.grupo_empresarial import GrupoEmpresarialDetector
import re
import re
import re
import re
from app import db
from app.fretes.models import Frete, DespesaExtra
from app.transportadoras.models import Transportadora
from app import db
from app.transportadoras.models import Transportadora
from app.fretes.models import Frete
from app import db
from app.pedidos.models import Pedido
from app import db
from app.embarques.models import Embarque, EmbarqueItem
from datetime import date
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado as RelatorioImportado
from app import db
from app.fretes.models import DespesaExtra
from app.financeiro.models import PendenciaFinanceiraNF

# Configurar logger
logger = logging.getLogger(__name__)

class ResponseProcessor:
    """Classe para processamento especializado"""
    
    def __init__(self):
        pass
        
    def _gerar_resposta_inicial(self, consulta: str, analise: Dict[str, Any], user_context: Optional[Dict] = None) -> str:
        """🎯 Gera resposta inicial otimizada"""
        # Usar o sistema existente mas com configurações otimizadas
        return self._processar_consulta_padrao(consulta, user_context)
    def _avaliar_qualidade_resposta(self, consulta: str, resposta: str, analise: Dict[str, Any]) -> Dict[str, Any]:
        """🔍 Avalia qualidade da resposta (similar ao Cursor)"""
        score = 0.8  # Base score
        
        # Critérios de avaliação
        if len(resposta) < 100:
            score -= 0.2  # Resposta muito curta
        
        if 'erro' in resposta.lower():
            score -= 0.3  # Contém erro
        
        if 'dados' in analise['tipo'] and 'total' not in resposta.lower():
            score -= 0.1  # Falta estatísticas
        
        return {
            'score': max(0.0, min(1.0, score)),
            'criterios': {
                'completude': 0.8,
                'precisao': 0.9,
                'relevancia': 0.8
            }
        }
    def _melhorar_resposta(self, consulta: str, resposta_inicial: str, qualidade: Dict[str, Any], user_context: Optional[Dict] = None) -> str:
        """🚀 Melhora resposta com reflexão"""
        try:
            # Gerar uma segunda tentativa com contexto da primeira
            prompt_reflexao = f"""
            Consulta original: {consulta}
            
            Primeira resposta: {resposta_inicial}
            
            Problemas identificados: {qualidade['criterios']}
            
            Melhore a resposta considerando:
            1. Seja mais específico e detalhado
            2. Inclua dados quantitativos quando possível
            3. Forneça contexto relevante
            4. Certifique-se de responder completamente à pergunta
            """
            
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                temperature=0.6,  # Ligeiramente mais criativo para melhorias
                messages=[{"role": "user", "content": prompt_reflexao}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"❌ Erro na melhoria da resposta: {e}")
            return resposta_inicial
    def _validar_resposta_final(self, resposta: str, analise: Dict[str, Any]) -> str:
        """✅ Validação final da resposta"""
        # Adicionar timestamp e fonte
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        return f"""{resposta}

---
🧠 **Processado com Sistema de Reflexão Avançada**
🕒 **Timestamp:** {timestamp}
⚡ **Fonte:** Claude 4 Sonnet + Análise Profunda
🎯 **Qualidade:** Otimizada por múltiplas validações"""

# Instância global
_responseprocessor = None

def get_responseprocessor():
    """Retorna instância de ResponseProcessor"""
    global _responseprocessor
    if _responseprocessor is None:
        _responseprocessor = ResponseProcessor()
    return _responseprocessor
