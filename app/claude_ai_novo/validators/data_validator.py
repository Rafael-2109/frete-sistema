#!/usr/bin/env python3
"""
ValidationUtils - Utilitários especializados
"""

import os
import anthropic
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
try:
    from sqlalchemy import or_
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    or_ = None
    SQLALCHEMY_AVAILABLE = False
# Flask fallback para execução standalone
try:
    from app.claude_ai_novo.utils.flask_fallback import get_model, get_db, get_current_user
    from app.utils.redis_cache import redis_cache, cache_aside, cached_query
    from app.utils.grupo_empresarial import GrupoEmpresarialDetector, detectar_grupo_empresarial
    from app.utils.ml_models_real import get_ml_models_system
    from app.claude_ai_novo.config import ClaudeAIConfig, AdvancedConfig
    from app.utils.api_helper import get_system_alerts
    from app.utils.ai_logging import ai_logger, AILogger
    from app.utils.redis_cache import intelligent_cache
    from app.financeiro.models import PendenciaFinanceiraNF
    

    
except ImportError:
    # Fallback se dependências não disponíveis
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
    db = Mock()
    current_user = Mock()
    Pedido = Embarque = EmbarqueItem = EntregaMonitorada = Mock
    RelatorioFaturamentoImportado = Transportadora = Frete = Mock
    redis_cache = cache_aside = cached_query = Mock()
    GrupoEmpresarialDetector = detectar_grupo_empresarial = Mock()
    get_ml_models_system = get_system_alerts = Mock()
    ClaudeAIConfig = AdvancedConfig = ai_logger = AILogger = Mock()

try:
    from sqlalchemy import func, and_, or_, text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    func, and_, or_, text = None
    SQLALCHEMY_AVAILABLE = False
from datetime import datetime, timedelta, date
import json
import re
import time
import asyncio
# Configurar logger
logger = logging.getLogger(__name__)

class ValidationUtils:
    """Classe para utilitários especializados"""
    
    @property
    def db(self):
        """Obtém db com fallback"""
        return get_db()
    
    @property
    def current_user(self):
        return get_current_user()
    
    @property
    def Pedido(self):
        return get_model("Pedido")
    
    @property
    def Embarque(self):
        return get_model("Embarque")
    
    @property
    def EmbarqueItem(self):
        return get_model("EmbarqueItem")
    
    @property
    def EntregaMonitorada(self):
        return get_model("EntregaMonitorada")
    
    @property
    def RelatorioFaturamentoImportado(self):
        return get_model("RelatorioFaturamentoImportado")
    
    @property
    def Transportadora(self):
        return get_model("Transportadora")
    
    @property
    def Frete(self):
        return get_model("Frete")
    
    def __init__(self):
        pass
        
    def _verificar_prazo_entrega(self, entrega) -> Optional[bool]:
        """Verifica se entrega foi realizada no prazo"""
        if not entrega.data_hora_entrega_realizada or not entrega.data_entrega_prevista:
            return None
        
        return entrega.data_hora_entrega_realizada.date() <= entrega.data_entrega_prevista
    def _calcular_dias_atraso(self, entrega) -> Optional[int]:
        """Calcula dias de atraso da entrega"""
        if not entrega.data_hora_entrega_realizada or not entrega.data_entrega_prevista:
            return None
        
        if entrega.data_hora_entrega_realizada.date() > entrega.data_entrega_prevista:
            return (entrega.data_hora_entrega_realizada.date() - entrega.data_entrega_prevista).days
        
        return 0
    def _obter_filtros_usuario(self) -> Dict[str, Any]:
        """Obtém filtros específicos do usuário atual"""
        filtros = {
            "vendedor_restricao": False,
            "vendedor": None,
            "perfil": "admin"
        }
        
        try:
            if hasattr(current_user, 'vendedor') and current_user.vendedor:
                filtros["vendedor_restricao"] = True
                filtros["vendedor"] = current_user.nome
                filtros["perfil"] = "vendedor"
        except:
            pass  # Se não conseguir identificar, usar padrão admin
            
        return filtros
    def _calcular_metricas_prazo(self, entregas: List) -> Dict[str, Any]:
        """Calcula métricas de performance de prazo"""
        if not entregas:
            return {}
        
        total_entregas = len(entregas)
        entregas_realizadas = [e for e in entregas if e.data_hora_entrega_realizada]
        entregas_no_prazo = [
            e for e in entregas_realizadas 
            if e.data_entrega_prevista and e.data_hora_entrega_realizada 
            and e.data_hora_entrega_realizada.date() <= e.data_entrega_prevista
        ]
        
        # Calcular atrasos
        atrasos = []
        for e in entregas_realizadas:
            if e.data_entrega_prevista and e.data_hora_entrega_realizada.date() > e.data_entrega_prevista:
                atraso = (e.data_hora_entrega_realizada.date() - e.data_entrega_prevista).days
                atrasos.append(atraso)
        
        return {
            "total_entregas": total_entregas,
            "entregas_realizadas": len(entregas_realizadas),
            "entregas_no_prazo": len(entregas_no_prazo),
            "entregas_atrasadas": len(atrasos),
            "percentual_no_prazo": round((len(entregas_no_prazo) / len(entregas_realizadas) * 100), 1) if entregas_realizadas else 0,
            "media_lead_time": round(sum(e.lead_time for e in entregas if e.lead_time) / len([e for e in entregas if e.lead_time]), 1) if any(e.lead_time for e in entregas) else None,
            "media_atraso": round(sum(atrasos) / len(atrasos), 1) if atrasos else 0,
            "maior_atraso": max(atrasos) if atrasos else 0
        }
    def _calcular_estatisticas_especificas(self, analise: Dict[str, Any], filtros_usuario: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula estatísticas específicas para o contexto"""
        try:
            # Usar variáveis globais já configuradas
            pass
            
            data_limite = datetime.now() - timedelta(days=analise.get("periodo_dias", 30))
            
            # Base query para entregas - ✅ CORREÇÃO: Incluir NULL data_embarque
            query_base = self.db.session.query(self.EntregaMonitorada).filter(
                or_(
                    self.EntregaMonitorada.data_embarque >= data_limite,
                    self.EntregaMonitorada.data_embarque.is_(None)
                )
            )
            
            # Aplicar filtros específicos
            if analise.get("cliente_especifico"):
                # 🏢 USAR FILTRO SQL DO GRUPO EMPRESARIAL SE DETECTADO
                if analise.get("tipo_consulta") == "grupo_empresarial" and analise.get("filtro_sql"):
                    # GRUPO EMPRESARIAL - usar filtro SQL inteligente
                    filtro_sql = analise["filtro_sql"]
                    logger.info(f"🏢 ESTATÍSTICAS - Aplicando filtro SQL do grupo: {filtro_sql}")
                    query_base = query_base.filter(
                        self.EntregaMonitorada.cliente.ilike(filtro_sql)
                    )
                elif analise["cliente_especifico"] == "GRUPO_CLIENTES":
                    # Filtro genérico para grupos de clientes
                    query_base = query_base.filter(
                        or_(
                            self.EntregaMonitorada.cliente.ilike('%atacado%'),
                            self.EntregaMonitorada.cliente.ilike('%supermercado%'),
                            self.EntregaMonitorada.cliente.ilike('%varejo%')
                        )
                    )
                else:
                    # Cliente específico sem grupo
                    query_base = query_base.filter(self.EntregaMonitorada.cliente.ilike(f'%{analise["cliente_especifico"]}%'))
            
            if filtros_usuario.get("vendedor_restricao"):
                query_base = query_base.filter(self.EntregaMonitorada.vendedor == filtros_usuario["vendedor"])
            
            total_entregas = query_base.count()
            entregas_entregues = query_base.filter(self.EntregaMonitorada.status_finalizacao == 'Entregue').count()
            entregas_pendentes = query_base.filter(self.EntregaMonitorada.status_finalizacao.in_(['Pendente', 'Em trânsito'])).count()
            
            return {
                "periodo_analisado": f"{analise.get('periodo_dias', 30)} dias",
                "total_entregas": total_entregas,
                "entregas_entregues": entregas_entregues,
                "entregas_pendentes": entregas_pendentes,  
                "percentual_entregues": round((entregas_entregues / total_entregas * 100), 1) if total_entregas > 0 else 0,
                "cliente_especifico": analise.get("cliente_especifico"),
                "filtro_geografico": analise.get("filtro_geografico"),
                "restricao_vendedor": filtros_usuario.get("vendedor_restricao", False)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular estatísticas: {e}")
            return {"erro": str(e)}
    def _calcular_estatisticas_por_dominio(self, analise: Dict[str, Any], filtros_usuario: Dict[str, Any], dominio: str) -> Optional[Dict[str, Any]]:
        """📊 Calcula estatísticas específicas baseadas no domínio"""
        try:
            # Validação avançada com Claude
            try:
                from app.claude_ai_novo.integration.external_api_integration import get_claude_integration
                claude = get_claude_integration()
            except Exception as e:
                self.logger.warning(f"⚠️ Não foi possível carregar Claude Integration: {e}")
                claude = None

            if not claude:
                return {"erro": "Sistema de Claude não está disponível"}
            
            # Para entregas, usar a função existente
            if dominio == "entregas":
                # Usar o método local da própria classe
                return self._calcular_estatisticas_especificas(analise, filtros_usuario)
            
            # Para outros domínios, estatísticas já estão incluídas nos dados carregados
            return {
                "dominio": dominio,
                "periodo_analisado": f"{analise.get('periodo_dias', 30)} dias",
                "cliente_especifico": analise.get("cliente_especifico"),
                "nota": f"Estatísticas específicas incluídas nos dados de {dominio}"
            }
        except Exception as e:
            logger.error(f"❌ Erro ao calcular estatísticas do domínio {dominio}: {e}")
            return {"erro": str(e), "dominio": dominio}


# Instância global para ValidationUtils
_validationutils = None

def get_validationutils():
    """Retorna instância de ValidationUtils"""
    global _validationutils
    if _validationutils is None:
        _validationutils = ValidationUtils()
    return _validationutils
