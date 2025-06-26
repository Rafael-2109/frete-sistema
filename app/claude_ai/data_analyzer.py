#!/usr/bin/env python3
"""
Analisador de Dados para Sugestões Inteligentes
Analisa dados reais do sistema para gerar sugestões acionáveis
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc
from flask import current_app

logger = logging.getLogger(__name__)

class VendedorDataAnalyzer:
    """
    Analisador de dados específicos do vendedor
    Baseado em: https://fastbots.ai/blog/how-chatbots-use-customer-data-to-improve-service-recommendations
    """
    
    def __init__(self, db):
        self.db = db
    
    def get_maiores_clientes_vendedor(self, vendedor_codigo: str, limite: int = 3) -> List[Dict[str, Any]]:
        """
        Busca os 3 maiores clientes do vendedor baseado no volume de entregas
        """
        try:
            from app.monitoramento.models import EntregaMonitorada
            from app.pedidos.models import Pedido
            
            # Query para buscar maiores clientes por volume de entregas
            resultado = self.db.session.query(
                Pedido.nome_cliente,
                func.count(EntregaMonitorada.id).label('total_entregas'),
                func.max(EntregaMonitorada.data_embarque).label('ultima_entrega')
            ).join(
                EntregaMonitorada, Pedido.numero_nf == EntregaMonitorada.numero_nf
            ).filter(
                and_(
                    Pedido.vendedor_codigo == vendedor_codigo,
                    EntregaMonitorada.data_embarque >= datetime.now() - timedelta(days=90)
                )
            ).group_by(
                Pedido.nome_cliente
            ).order_by(
                desc('total_entregas')
            ).limit(limite).all()
            
            clientes = []
            for cliente in resultado:
                clientes.append({
                    'nome_cliente': cliente.nome_cliente,
                    'total_entregas': cliente.total_entregas,
                    'ultima_entrega': cliente.ultima_entrega.strftime('%d/%m/%Y') if cliente.ultima_entrega else 'N/A'
                })
            
            logger.info(f"📊 Encontrados {len(clientes)} maiores clientes para vendedor {vendedor_codigo}")
            return clientes
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar maiores clientes: {e}")
            return []
    
    def get_clientes_sem_agendamento(self, vendedor_codigo: str, limite: int = 5) -> List[Dict[str, Any]]:
        """
        Busca clientes que têm entregas mas não têm agendamento
        """
        try:
            from app.monitoramento.models import EntregaMonitorada
            from app.pedidos.models import Pedido
            
            # Query para buscar entregas sem agendamento
            resultado = self.db.session.query(
                Pedido.nome_cliente,
                func.count(EntregaMonitorada.id).label('entregas_sem_agendamento')
            ).join(
                EntregaMonitorada, Pedido.numero_nf == EntregaMonitorada.numero_nf
            ).filter(
                and_(
                    Pedido.vendedor_codigo == vendedor_codigo,
                    EntregaMonitorada.status_finalizacao.in_(['Pendente', 'Em trânsito']),
                    EntregaMonitorada.data_prevista_entrega.is_(None)  # Sem data prevista = sem agendamento
                )
            ).group_by(
                Pedido.nome_cliente
            ).order_by(
                desc('entregas_sem_agendamento')
            ).limit(limite).all()
            
            clientes = []
            for cliente in resultado:
                clientes.append({
                    'nome_cliente': cliente.nome_cliente,
                    'entregas_pendentes': cliente.entregas_sem_agendamento
                })
            
            logger.info(f"📅 Encontrados {len(clientes)} clientes sem agendamento para vendedor {vendedor_codigo}")
            return clientes
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar clientes sem agendamento: {e}")
            return []
    
    def get_entregas_pendentes_urgentes(self, vendedor_codigo: str, limite: int = 5) -> List[Dict[str, Any]]:
        """
        Busca entregas pendentes que estão atrasadas ou próximas do prazo
        """
        try:
            from app.monitoramento.models import EntregaMonitorada
            from app.pedidos.models import Pedido
            
            data_limite = datetime.now() + timedelta(days=2)
            
            resultado = self.db.session.query(
                Pedido.nome_cliente,
                EntregaMonitorada.numero_nf,
                EntregaMonitorada.data_prevista_entrega,
                EntregaMonitorada.status_finalizacao
            ).join(
                EntregaMonitorada, Pedido.numero_nf == EntregaMonitorada.numero_nf
            ).filter(
                and_(
                    Pedido.vendedor_codigo == vendedor_codigo,
                    EntregaMonitorada.status_finalizacao.in_(['Pendente', 'Em trânsito']),
                    or_(
                        EntregaMonitorada.data_prevista_entrega <= data_limite.date(),
                        EntregaMonitorada.data_prevista_entrega < datetime.now().date()
                    )
                )
            ).order_by(
                EntregaMonitorada.data_prevista_entrega.asc()
            ).limit(limite).all()
            
            entregas = []
            for entrega in resultado:
                data_prevista = entrega.data_prevista_entrega
                is_atrasada = data_prevista < datetime.now().date() if data_prevista else False
                
                entregas.append({
                    'nome_cliente': entrega.nome_cliente,
                    'numero_nf': entrega.numero_nf,
                    'data_prevista': data_prevista.strftime('%d/%m/%Y') if data_prevista else 'N/A',
                    'status': entrega.status_finalizacao,
                    'is_atrasada': is_atrasada
                })
            
            logger.info(f"⚠️ Encontradas {len(entregas)} entregas urgentes para vendedor {vendedor_codigo}")
            return entregas
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar entregas urgentes: {e}")
            return []
    
    def get_resumo_vendedor(self, vendedor_codigo: str) -> Dict[str, Any]:
        """
        Gera resumo executivo para o vendedor
        """
        try:
            from app.monitoramento.models import EntregaMonitorada
            from app.pedidos.models import Pedido
            
            hoje = datetime.now().date()
            inicio_mes = hoje.replace(day=1)
            
            # Estatísticas do mês
            stats = self.db.session.query(
                func.count(EntregaMonitorada.id).label('total_entregas'),
                func.count(
                    func.nullif(EntregaMonitorada.status_finalizacao == 'Entregue', False)
                ).label('entregas_concluidas'),
                func.count(
                    func.nullif(EntregaMonitorada.data_prevista_entrega < hoje, False)
                ).label('entregas_atrasadas'),
                func.count(func.distinct(Pedido.nome_cliente)).label('clientes_ativos')
            ).join(
                EntregaMonitorada, Pedido.numero_nf == EntregaMonitorada.numero_nf
            ).filter(
                and_(
                    Pedido.vendedor_codigo == vendedor_codigo,
                    EntregaMonitorada.data_embarque >= inicio_mes
                )
            ).first()
            
            # Calcular percentuais
            total = stats.total_entregas or 1  # Evitar divisão por zero
            percentual_entregue = round((stats.entregas_concluidas or 0) / total * 100, 1)
            percentual_atraso = round((stats.entregas_atrasadas or 0) / total * 100, 1)
            
            resumo = {
                'total_entregas': stats.total_entregas or 0,
                'entregas_concluidas': stats.entregas_concluidas or 0,
                'entregas_atrasadas': stats.entregas_atrasadas or 0,
                'clientes_ativos': stats.clientes_ativos or 0,
                'percentual_entregue': percentual_entregue,
                'percentual_atraso': percentual_atraso,
                'periodo': f"{inicio_mes.strftime('%d/%m')} - {hoje.strftime('%d/%m/%Y')}"
            }
            
            logger.info(f"📈 Resumo gerado para vendedor {vendedor_codigo}: {resumo['total_entregas']} entregas")
            return resumo
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar resumo: {e}")
            return {
                'total_entregas': 0,
                'entregas_concluidas': 0,
                'entregas_atrasadas': 0,
                'clientes_ativos': 0,
                'percentual_entregue': 0,
                'percentual_atraso': 0,
                'periodo': 'N/A'
            }

class GeralDataAnalyzer:
    """
    Analisador de dados gerais do sistema
    """
    
    def __init__(self, db):
        self.db = db
    
    def get_embarques_aguardando_liberacao(self, limite: int = 5) -> List[Dict[str, Any]]:
        """
        Busca embarques aguardando liberação
        """
        try:
            from app.embarques.models import Embarque
            
            resultado = self.db.session.query(Embarque).filter(
                and_(
                    Embarque.status == 'ativo',
                    Embarque.data_embarque.is_(None)  # Ainda não saiu
                )
            ).order_by(
                Embarque.criado_em.desc()
            ).limit(limite).all()
            
            embarques = []
            for embarque in resultado:
                embarques.append({
                    'numero_embarque': embarque.numero_embarque,
                    'transportadora': embarque.transportadora.razao_social if embarque.transportadora else 'N/A',
                    'total_nfs': len(embarque.itens) if embarque.itens else 0,
                    'data_criacao': embarque.criado_em.strftime('%d/%m/%Y %H:%M') if embarque.criado_em else 'N/A',
                    'observacoes': embarque.observacoes[:50] + '...' if embarque.observacoes and len(embarque.observacoes) > 50 else embarque.observacoes
                })
            
            return embarques
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar embarques aguardando: {e}")
            return []
    
    def get_faturas_vencendo(self, dias: int = 7, limite: int = 5) -> List[Dict[str, Any]]:
        """
        Busca faturas próximas do vencimento
        """
        try:
            from app.fretes.models import Fatura
            
            data_limite = datetime.now().date() + timedelta(days=dias)
            
            resultado = self.db.session.query(Fatura).filter(
                and_(
                    Fatura.data_vencimento <= data_limite,
                    Fatura.data_vencimento >= datetime.now().date(),
                    Fatura.status_conferencia == 'CONFERIDO'  # Apenas conferidas
                )
            ).order_by(
                Fatura.data_vencimento.asc()
            ).limit(limite).all()
            
            faturas = []
            for fatura in resultado:
                dias_restantes = (fatura.data_vencimento - datetime.now().date()).days
                
                faturas.append({
                    'numero_fatura': fatura.numero_fatura,
                    'transportadora': fatura.transportadora.razao_social if fatura.transportadora else 'N/A',
                    'valor_total': float(fatura.valor_total or 0),
                    'data_vencimento': fatura.data_vencimento.strftime('%d/%m/%Y'),
                    'dias_restantes': dias_restantes,
                    'urgencia': '🔴 HOJE' if dias_restantes == 0 else f'🟡 {dias_restantes}d'
                })
            
            return faturas
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar faturas vencendo: {e}")
            return []

# Instância global dos analisadores
vendedor_analyzer = None
geral_analyzer = None

def init_data_analyzers(db):
    """Inicializa os analisadores de dados"""
    global vendedor_analyzer, geral_analyzer
    try:
        vendedor_analyzer = VendedorDataAnalyzer(db)
        geral_analyzer = GeralDataAnalyzer(db)
        logger.info("📊 Analisadores de dados inicializados")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar analisadores: {e}")
        return False

def get_vendedor_analyzer():
    """Retorna instância do analisador de vendedor"""
    return vendedor_analyzer

def get_geral_analyzer():
    """Retorna instância do analisador geral"""
    return geral_analyzer 