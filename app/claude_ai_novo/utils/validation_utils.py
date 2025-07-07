#!/usr/bin/env python3
"""
ValidationUtils - Utilitários especializados
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

class ValidationUtils:
    """Classe para utilitários especializados"""
    
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
            from app import db
            from app.monitoramento.models import EntregaMonitorada
            from app.fretes.models import Frete
            
            data_limite = datetime.now() - timedelta(days=analise.get("periodo_dias", 30))
            
            # Base query para entregas - ✅ CORREÇÃO: Incluir NULL data_embarque
            query_base = db.session.query(EntregaMonitorada).filter(
                or_(
                    EntregaMonitorada.data_embarque >= data_limite,
                    EntregaMonitorada.data_embarque.is_(None)
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
                        EntregaMonitorada.cliente.ilike(filtro_sql)
                    )
                elif analise["cliente_especifico"] == "GRUPO_CLIENTES":
                    # Filtro genérico para grupos de clientes
                    query_base = query_base.filter(
                        or_(
                            EntregaMonitorada.cliente.ilike('%atacado%'),
                            EntregaMonitorada.cliente.ilike('%supermercado%'),
                            EntregaMonitorada.cliente.ilike('%varejo%')
                        )
                    )
                else:
                    # Cliente específico sem grupo
                    query_base = query_base.filter(EntregaMonitorada.cliente.ilike(f'%{analise["cliente_especifico"]}%'))
            
            if filtros_usuario.get("vendedor_restricao"):
                query_base = query_base.filter(EntregaMonitorada.vendedor == filtros_usuario["vendedor"])
            
            total_entregas = query_base.count()
            entregas_entregues = query_base.filter(EntregaMonitorada.status_finalizacao == 'Entregue').count()
            entregas_pendentes = query_base.filter(EntregaMonitorada.status_finalizacao.in_(['Pendente', 'Em trânsito'])).count()
            
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
            from app.claude_ai_novo.core.claude_integration import get_claude_integration
            claude_integration = get_claude_integration()
            
            if not claude_integration:
                return {"erro": "Sistema de Claude não está disponível"}
            
            # Para entregas, usar a função existente
            if dominio == "entregas":
                # Usar a instância global para acessar o método
                return claude_integration._calcular_estatisticas_especificas(analise, filtros_usuario)
            
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
