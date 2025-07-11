from datetime import datetime, timedelta, date
#!/usr/bin/env python3
"""
ContextProcessor - Processamento especializado de contexto
"""

# Imports da base comum (apenas o que realmente existe)
from .base import ProcessorBase, logging

# Imports específicos com fallbacks
try:
    from flask_login import current_user
    from flask_sqlalchemy import db
    from sqlalchemy import func, and_, or_, text
    FLASK_AVAILABLE = True
except ImportError:
    # Fallbacks para execução standalone
    current_user = None
    db = None
    func = and_ = or_ = text = None
    FLASK_AVAILABLE = False

# Models com fallbacks
try:
    from app.fretes.models import Frete
    from app.embarques.models import Embarque, EmbarqueItem
    from app.transportadoras.models import Transportadora
    from app.pedidos.models import Pedido
    from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
    from app.faturamento.models import RelatorioFaturamentoImportado
    from app.financeiro.models import PendenciaFinanceiraNF
    from app.fretes.models import DespesaExtra
    MODELS_AVAILABLE = True
except ImportError:
    # Fallbacks para quando modelos não estão disponíveis
    Frete = Embarque = EmbarqueItem = Transportadora = None
    Pedido = EntregaMonitorada = AgendamentoEntrega = None
    RelatorioFaturamentoImportado = PendenciaFinanceiraNF = DespesaExtra = None
    MODELS_AVAILABLE = False

# Imports básicos
import json
import asyncio
import time

# Imports específicos do contexto
from typing import Dict, List, Optional, Any

# Configuração local
try:
    from app.claude_ai_novo.config import ClaudeAIConfig, AdvancedConfig
    CONFIG_LOCAL_AVAILABLE = True
except ImportError:
    CONFIG_LOCAL_AVAILABLE = False

class ContextProcessor(ProcessorBase):
    """Classe para processamento especializado de contexto"""
    
    def __init__(self):
        super().__init__()
        self._ultimo_contexto_carregado = None
        
    def _build_contexto_por_intencao(self, intencoes_scores: Dict[str, float], 
                                      analise: Dict[str, Any]) -> str:
        """
        Constrói contexto específico baseado na intenção dominante
        """
        
        # Validar entrada
        if not intencoes_scores or not analise:
            return ""
        
        # Log da operação
        self._log_operation("build_contexto_por_intencao", f"intencoes: {len(intencoes_scores)}")
        
        # Verificar cache
        cache_key = self._generate_cache_key("contexto_intencao", str(intencoes_scores), str(analise))
        cached_result = self._get_cached_result(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            # Encontrar intenção dominante
            intencao_principal = max(intencoes_scores, key=lambda k: intencoes_scores[k])
            score_principal = intencoes_scores[intencao_principal]
            
            # Log da intenção detectada
            self.logger.info(f"🎯 Intenção principal: {intencao_principal} ({score_principal:.1%})")
            
            # Se confiança baixa, usar contexto genérico
            if score_principal < 0.4:
                result = self._descrever_contexto_carregado(analise)
                self._set_cached_result(cache_key, result, ttl=300)
                return result
            
            # Contextos específicos por intenção
            periodo = analise.get('periodo_dias', 30)
            cliente = analise.get('cliente_especifico')
            
            if intencao_principal == "desenvolvimento":
                result = """Contexto: Sistema Flask/PostgreSQL
Estrutura: app/[modulo]/{models,routes,forms}.py  
Padrões: SQLAlchemy, WTForms, Jinja2
Módulos: pedidos, fretes, embarques, monitoramento, separacao, carteira, etc."""
            
            elif intencao_principal == "analise_dados":
                registros = self._ultimo_contexto_carregado.get('registros_carregados', 0) if hasattr(self, '_ultimo_contexto_carregado') else 0
                result = f"Dados: {registros} registros, {periodo} dias"
                if cliente:
                    result += f", cliente: {cliente}"
            
            elif intencao_principal == "resolucao_problema":
                result = "Contexto: Diagnóstico e resolução\nSistema: Flask/PostgreSQL\nLogs disponíveis"
            
            elif intencao_principal == "comando_acao":
                result = f"Ação solicitada. Período: {periodo} dias"
                if cliente:
                    result += f", Cliente: {cliente}"
            
            else:
                result = self._descrever_contexto_carregado(analise)
            
            # Armazenar no cache
            self._set_cached_result(cache_key, result, ttl=300)
            
            return result
            
        except Exception as e:
            error_msg = self._handle_error(e, "_build_contexto_por_intencao")
            self.logger.error(f"Erro ao construir contexto: {error_msg}")
            return ""
    
    def _descrever_contexto_carregado(self, analise: Dict[str, Any]) -> str:
        """Descrição simplificada do contexto para o Claude"""
        
        if not hasattr(self, '_ultimo_contexto_carregado') or not self._ultimo_contexto_carregado:
            return ""
        
        try:
            dados = self._ultimo_contexto_carregado.get('dados_especificos', {})
            if not dados:
                return ""
            
            # Contexto básico
            periodo = analise.get('periodo_dias', 30)
            cliente = analise.get('cliente_especifico')
            
            if cliente:
                return f"Contexto: {cliente}, últimos {periodo} dias."
            else:
                return f"Contexto: últimos {periodo} dias."
                
        except Exception as e:
            self.logger.error(f"Erro ao descrever contexto: {e}")
            return ""
    
    def carregar_contexto_inteligente(self, consulta: str, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Carrega contexto inteligente baseado na consulta"""
        
        # Validar entrada
        if not self._validate_input(consulta):
            return {}
        
        # Sanitizar consulta
        consulta = self._sanitize_input(consulta)
        
        # Log da operação
        self._log_operation("carregar_contexto_inteligente", f"consulta: {consulta[:50]}...")
        
        # Verificar cache
        cache_key = self._generate_cache_key("contexto_inteligente", consulta, str(analise))
        cached_result = self._get_cached_result(cache_key)
        
        if cached_result:
            self._log_operation("Cache hit para contexto inteligente")
            return cached_result
        
        try:
            # Verificar se banco está disponível
            if not FLASK_AVAILABLE or not db:
                self.logger.warning("Banco não disponível - retornando contexto vazio")
                return {}
            
            # Detectar domínio da consulta
            dominio = self._detectar_dominio(consulta)
            
            # Carregar dados específicos do domínio
            dados = {}
            
            if dominio == "entregas":
                dados = self._carregar_dados_entregas(analise)
            elif dominio == "fretes":
                dados = self._carregar_dados_fretes(analise)
            elif dominio == "pedidos":
                dados = self._carregar_dados_pedidos(analise)
            elif dominio == "financeiro":
                dados = self._carregar_dados_financeiro(analise)
            else:
                # Domínio geral - carregar amostra de tudo
                dados = self._carregar_dados_geral(analise)
            
            # Construir contexto
            contexto = {
                'dominio': dominio,
                'dados': dados,
                'periodo': analise.get('periodo_dias', 30),
                'cliente': analise.get('cliente_especifico'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Armazenar contexto carregado
            self._ultimo_contexto_carregado = {
                'dados_especificos': dados,
                'registros_carregados': len(dados.get('registros', [])),
                'dominio': dominio
            }
            
            # Armazenar no cache
            self._set_cached_result(cache_key, contexto, ttl=600)
            
            return contexto
            
        except Exception as e:
            error_msg = self._handle_error(e, "carregar_contexto_inteligente")
            self.logger.error(f"Erro ao carregar contexto: {error_msg}")
            return {}
    
    def _detectar_dominio(self, consulta: str) -> str:
        """Detecta domínio da consulta"""
        
        consulta_lower = consulta.lower()
        
        # Padrões de domínio
        dominios = {
            'entregas': ['entrega', 'monitoramento', 'agendamento', 'canhoto'],
            'fretes': ['frete', 'cte', 'transportadora', 'custo'],
            'pedidos': ['pedido', 'cotação', 'separação', 'carteira'],
            'financeiro': ['financeiro', 'pagamento', 'pendencia', 'cobrança']
        }
        
        scores = {}
        for dominio, termos in dominios.items():
            score = sum(1 for termo in termos if termo in consulta_lower)
            scores[dominio] = score
        
        # Retornar domínio com maior score
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                # Encontrar domínio com maior score
                for dominio, score in scores.items():
                    if score == max_score:
                        return dominio
        
        return 'geral'
    
    def _carregar_dados_entregas(self, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Carrega dados específicos de entregas"""
        
        try:
            if not MODELS_AVAILABLE:
                return {}
            
            # Construir query básica
            query = db.session.query(EntregaMonitorada)
            
            # Filtrar por cliente se especificado
            cliente = analise.get('cliente_especifico')
            if cliente:
                query = query.filter(EntregaMonitorada.nome_cliente.ilike(f'%{cliente}%'))
            
            # Filtrar por período
            periodo = analise.get('periodo_dias', 30)
            data_limite = datetime.now() - timedelta(days=periodo)
            query = query.filter(EntregaMonitorada.data_embarque >= data_limite)
            
            # Limitar resultados
            registros = query.limit(100).all()
            
            return {
                'registros': [self._serialize_entrega(r) for r in registros],
                'total': query.count(),
                'dominio': 'entregas'
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados de entregas: {e}")
            return {}
    
    def _carregar_dados_fretes(self, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Carrega dados específicos de fretes"""
        
        try:
            if not MODELS_AVAILABLE:
                return {}
            
            # Construir query básica
            query = db.session.query(Frete)
            
            # Filtrar por cliente se especificado
            cliente = analise.get('cliente_especifico')
            if cliente:
                query = query.filter(Frete.nome_cliente.ilike(f'%{cliente}%'))
            
            # Filtrar por período
            periodo = analise.get('periodo_dias', 30)
            data_limite = datetime.now() - timedelta(days=periodo)
            query = query.filter(Frete.data_cotacao >= data_limite)
            
            # Limitar resultados
            registros = query.limit(100).all()
            
            return {
                'registros': [self._serialize_frete(r) for r in registros],
                'total': query.count(),
                'dominio': 'fretes'
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados de fretes: {e}")
            return {}
    
    def _carregar_dados_pedidos(self, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Carrega dados específicos de pedidos"""
        
        try:
            if not MODELS_AVAILABLE:
                return {}
            
            # Construir query básica
            query = db.session.query(Pedido)
            
            # Filtrar por cliente se especificado
            cliente = analise.get('cliente_especifico')
            if cliente:
                query = query.filter(Pedido.raz_social_red.ilike(f'%{cliente}%'))
            
            # Filtrar por período
            periodo = analise.get('periodo_dias', 30)
            data_limite = datetime.now() - timedelta(days=periodo)
            query = query.filter(Pedido.data_pedido >= data_limite)
            
            # Limitar resultados
            registros = query.limit(100).all()
            
            return {
                'registros': [self._serialize_pedido(r) for r in registros],
                'total': query.count(),
                'dominio': 'pedidos'
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados de pedidos: {e}")
            return {}
    
    def _carregar_dados_financeiro(self, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Carrega dados específicos financeiros"""
        
        try:
            if not MODELS_AVAILABLE:
                return {}
            
            # Construir query básica
            query = db.session.query(PendenciaFinanceiraNF)
            
            # Filtrar por cliente se especificado
            cliente = analise.get('cliente_especifico')
            if cliente:
                query = query.filter(PendenciaFinanceiraNF.nome_cliente.ilike(f'%{cliente}%'))
            
            # Limitar resultados
            registros = query.limit(100).all()
            
            return {
                'registros': [self._serialize_pendencia(r) for r in registros],
                'total': query.count(),
                'dominio': 'financeiro'
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados financeiros: {e}")
            return {}
    
    def _carregar_dados_geral(self, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Carrega amostra geral de dados"""
        
        try:
            if not MODELS_AVAILABLE:
                return {}
            
            # Amostra de diferentes domínios
            dados_geral = {
                'entregas': self._carregar_dados_entregas(analise),
                'fretes': self._carregar_dados_fretes(analise),
                'pedidos': self._carregar_dados_pedidos(analise)
            }
            
            return {
                'registros': dados_geral,
                'total': sum(d.get('total', 0) for d in dados_geral.values()),
                'dominio': 'geral'
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados gerais: {e}")
            return {}
    
    def _serialize_entrega(self, entrega: Any) -> Dict:
        """Serializa entrega para contexto"""
        
        return {
            'id': entrega.id,
            'numero_nf': entrega.numero_nf,
            'nome_cliente': entrega.nome_cliente,
            'data_embarque': self._format_date_br(entrega.data_embarque),
            'status': entrega.status_finalizacao or 'Em andamento',
            'entregue': entrega.entregue
        }
    
    def _serialize_frete(self, frete: Any) -> Dict:
        """Serializa frete para contexto"""
        
        return {
            'id': frete.id,
            'nome_cliente': frete.nome_cliente,
            'valor_cotado': self._format_currency(frete.valor_cotado),
            'valor_considerado': self._format_currency(frete.valor_considerado),
            'data_cotacao': self._format_date_br(frete.data_cotacao),
            'status': frete.status_aprovacao or 'Pendente'
        }
    
    def _serialize_pedido(self, pedido: Any) -> Dict:
        """Serializa pedido para contexto"""
        
        return {
            'id': pedido.id,
            'num_pedido': pedido.num_pedido,
            'raz_social_red': pedido.raz_social_red,
            'data_pedido': self._format_date_br(pedido.data_pedido),
            'valor_saldo_total': self._format_currency(pedido.valor_saldo_total),
            'status': pedido.status_calculado
        }
    
    def _serialize_pendencia(self, pendencia: Any) -> Dict:
        """Serializa pendência para contexto"""
        
        return {
            'id': pendencia.id,
            'numero_nf': pendencia.numero_nf,
            'nome_cliente': pendencia.nome_cliente,
            'descricao': pendencia.descricao,
            'data_criacao': self._format_date_br(pendencia.data_criacao),
            'resolvida': pendencia.resolvida
        }

# Instância global
_contextprocessor = None

def get_contextprocessor():
    """Retorna instância de ContextProcessor"""
    global _contextprocessor
    if _contextprocessor is None:
        _contextprocessor = ContextProcessor()
    return _contextprocessor

# Alias para compatibilidade
get_context_processor = get_contextprocessor