#!/usr/bin/env python3
"""
🚨 SISTEMA DE ALERTAS INTELIGENTES
Motor de alertas baseado em dados reais do sistema
"""

from datetime import datetime, date, timedelta
from app import db
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class AlertEngine:
    """Motor de alertas inteligentes baseado em dados reais"""
    
    def __init__(self):
        self.alertas_configurados = {
            'embarques_parados': {
                'nome': 'Embarques Parados',
                'limite_horas': 24,
                'tipo': 'atencao',
                'icone': 'clock',
                'ativo': True
            },
            'entregas_atrasadas': {
                'nome': 'Entregas Atrasadas',
                'limite_dias': 0,  # Qualquer atraso
                'tipo': 'critico',
                'icone': 'exclamation-triangle',
                'ativo': True
            },
            'agendamentos_pendentes': {
                'nome': 'Agendamentos Pendentes',
                'limite_dias': 3,
                'tipo': 'atencao',
                'icone': 'calendar-times',
                'ativo': True
            },
            'pendencias_financeiras': {
                'nome': 'Pendências Financeiras',
                'limite_quantidade': 5,
                'tipo': 'critico',
                'icone': 'dollar-sign',
                'ativo': True
            },
            'fretes_sem_cte': {
                'nome': 'Fretes sem CTe',
                'limite_dias': 2,
                'tipo': 'atencao',
                'icone': 'file-times',
                'ativo': True
            },
            'clientes_sem_movimento': {
                'nome': 'Clientes sem Movimento',
                'limite_dias': 7,
                'tipo': 'info',
                'icone': 'user-clock',
                'ativo': True
            }
        }
    
    def gerar_alertas_dashboard(self, user_context=None):
        """Gera alertas para o dashboard executivo"""
        alertas = []
        
        try:
            # Importar modelos dentro da função para evitar imports circulares
            from app.monitoramento.models import EntregaMonitorada
            from app.embarques.models import Embarque
            from app.fretes.models import Frete
            
            hoje = date.today()
            
            # 🚨 EMBARQUES PARADOS
            if self.alertas_configurados['embarques_parados']['ativo']:
                embarques_parados = self._check_embarques_parados()
                if embarques_parados['quantidade'] > 0:
                    alertas.append({
                        'id': 'embarques_parados',
                        'tipo': 'atencao',
                        'icone': 'clock',
                        'titulo': 'Embarques Parados',
                        'mensagem': f"{embarques_parados['quantidade']} embarques sem movimentação há mais de 24h",
                        'quantidade': embarques_parados['quantidade'],
                        'acao_sugerida': 'Verificar com transportadoras',
                        'prioridade': 2
                    })
            
            # 🚨 ENTREGAS ATRASADAS
            if self.alertas_configurados['entregas_atrasadas']['ativo']:
                entregas_atrasadas = self._check_entregas_atrasadas()
                if entregas_atrasadas['quantidade'] > 0:
                    alertas.append({
                        'id': 'entregas_atrasadas',
                        'tipo': 'critico',
                        'icone': 'exclamation-triangle',
                        'titulo': 'Entregas Atrasadas',
                        'mensagem': f"{entregas_atrasadas['quantidade']} entregas com atraso confirmado",
                        'quantidade': entregas_atrasadas['quantidade'],
                        'detalhes': entregas_atrasadas['detalhes'],
                        'acao_sugerida': 'Contatar clientes + reagendar',
                        'prioridade': 1  # Máxima prioridade
                    })
            
            # 🚨 AGENDAMENTOS PENDENTES
            if self.alertas_configurados['agendamentos_pendentes']['ativo']:
                agendamentos_pendentes = self._check_agendamentos_pendentes()
                if agendamentos_pendentes['quantidade'] > 0:
                    alertas.append({
                        'id': 'agendamentos_pendentes',
                        'tipo': 'atencao',
                        'icone': 'calendar-times',
                        'titulo': 'Agendamentos Pendentes',
                        'mensagem': f"{agendamentos_pendentes['quantidade']} entregas precisam de agendamento",
                        'quantidade': agendamentos_pendentes['quantidade'],
                        'acao_sugerida': 'Ligar para clientes',
                        'prioridade': 2
                    })
            
            # 🚨 PENDÊNCIAS FINANCEIRAS CRÍTICAS
            if self.alertas_configurados['pendencias_financeiras']['ativo']:
                pendencias_financeiras = self._check_pendencias_financeiras()
                limite = self.alertas_configurados['pendencias_financeiras']['limite_quantidade']
                
                if pendencias_financeiras['quantidade'] > limite:
                    alertas.append({
                        'id': 'pendencias_financeiras',
                        'tipo': 'critico',
                        'icone': 'dollar-sign',
                        'titulo': 'Pendências Financeiras Críticas',
                        'mensagem': f"{pendencias_financeiras['quantidade']} entregas com pendências financeiras",
                        'quantidade': pendencias_financeiras['quantidade'],
                        'acao_sugerida': 'Acionar setor financeiro',
                        'prioridade': 1
                    })
            
            # 🚨 FRETES SEM CTe
            if self.alertas_configurados['fretes_sem_cte']['ativo']:
                fretes_sem_cte = self._check_fretes_sem_cte()
                if fretes_sem_cte['quantidade'] > 0:
                    alertas.append({
                        'id': 'fretes_sem_cte',
                        'tipo': 'atencao',
                        'icone': 'file-times',
                        'titulo': 'Fretes sem CTe',
                        'mensagem': f"{fretes_sem_cte['quantidade']} fretes aprovados sem CTe há mais de 2 dias",
                        'quantidade': fretes_sem_cte['quantidade'],
                        'acao_sugerida': 'Solicitar CTe das transportadoras',
                        'prioridade': 2
                    })
            
            # Ordenar alertas por prioridade (1 = crítico primeiro)
            alertas.sort(key=lambda x: x['prioridade'])
            
            logger.info(f"🚨 {len(alertas)} alertas gerados para o dashboard")
            return alertas
            
        except Exception as e:
            logger.error(f"Erro ao gerar alertas: {e}")
            return [{
                'id': 'error',
                'tipo': 'danger',
                'icone': 'exclamation-circle',
                'titulo': 'Erro no Sistema de Alertas',
                'mensagem': f'Erro interno: {str(e)}',
                'prioridade': 1
            }]
    
    def _check_embarques_parados(self):
        """Verifica embarques sem movimentação há mais de 24h"""
        try:
            from app.embarques.models import Embarque
            
            limite_tempo = datetime.now() - timedelta(hours=24)
            
            embarques_parados = db.session.query(Embarque).filter(
                Embarque.status == 'ativo',
                Embarque.data_embarque == None,
                Embarque.criado_em <= limite_tempo
            ).all()
            
            return {
                'quantidade': len(embarques_parados),
                'embarques': [{'numero': e.numero, 'criado_em': e.criado_em} for e in embarques_parados]
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar embarques parados: {e}")
            return {'quantidade': 0, 'erro': str(e)}
    
    def _check_entregas_atrasadas(self):
        """Verifica entregas atrasadas"""
        try:
            from app.monitoramento.models import EntregaMonitorada
            
            hoje = date.today()
            
            entregas_atrasadas = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.data_entrega_prevista < hoje,
                EntregaMonitorada.entregue == False
            ).all()
            
            detalhes = []
            for entrega in entregas_atrasadas[:5]:  # Primeiros 5 para detalhes
                dias_atraso = (hoje - entrega.data_entrega_prevista).days
                detalhes.append({
                    'numero_nf': entrega.numero_nf,
                    'cliente': entrega.cliente,
                    'dias_atraso': dias_atraso,
                    'data_prevista': entrega.data_entrega_prevista.strftime('%d/%m/%Y')
                })
            
            return {
                'quantidade': len(entregas_atrasadas),
                'detalhes': detalhes
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar entregas atrasadas: {e}")
            return {'quantidade': 0, 'erro': str(e)}
    
    def _check_agendamentos_pendentes(self):
        """Verifica entregas que precisam de agendamento"""
        try:
            from app.monitoramento.models import EntregaMonitorada
            
            data_limite = date.today() - timedelta(days=3)
            
            agendamentos_pendentes = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.data_embarque >= data_limite,
                EntregaMonitorada.data_entrega_prevista == None,
                EntregaMonitorada.entregue == False
            ).all()
            
            return {
                'quantidade': len(agendamentos_pendentes),
                'entregas': [{'numero_nf': e.numero_nf, 'cliente': e.cliente} for e in agendamentos_pendentes[:5]]
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar agendamentos pendentes: {e}")
            return {'quantidade': 0, 'erro': str(e)}
    
    def _check_pendencias_financeiras(self):
        """Verifica pendências financeiras"""
        try:
            from app.monitoramento.models import EntregaMonitorada
            
            pendencias = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.pendencia_financeira == True
            ).all()
            
            return {
                'quantidade': len(pendencias),
                'entregas': [{'numero_nf': p.numero_nf, 'cliente': p.cliente} for p in pendencias[:5]]
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar pendências financeiras: {e}")
            return {'quantidade': 0, 'erro': str(e)}
    
    def _check_fretes_sem_cte(self):
        """Verifica fretes aprovados sem CTe há mais de 2 dias"""
        try:
            from app.fretes.models import Frete
            
            data_limite = datetime.now() - timedelta(days=2)
            
            fretes_sem_cte = db.session.query(Frete).filter(
                Frete.status == 'APROVADO',
                db.or_(Frete.numero_cte == None, Frete.numero_cte == ''),
                Frete.criado_em <= data_limite
            ).all()
            
            return {
                'quantidade': len(fretes_sem_cte),
                'fretes': [{'id': f.id, 'cliente': f.nome_cliente} for f in fretes_sem_cte[:5]]
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar fretes sem CTe: {e}")
            return {'quantidade': 0, 'erro': str(e)}
    
    def gerar_alerta_personalizado(self, tipo_alerta, parametros=None):
        """Gera alerta específico baseado em parâmetros"""
        try:
            if tipo_alerta == 'cliente_especifico':
                cliente = parametros.get('cliente', '')
                return self._alerta_cliente_especifico(cliente)
            elif tipo_alerta == 'transportadora_especifica':
                transportadora = parametros.get('transportadora', '')
                return self._alerta_transportadora_especifica(transportadora)
            elif tipo_alerta == 'periodo_customizado':
                periodo = parametros.get('periodo', 7)
                return self._alerta_periodo_customizado(periodo)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Erro ao gerar alerta personalizado: {e}")
            return None
    
    def _alerta_cliente_especifico(self, cliente):
        """Gera alertas específicos para um cliente"""
        try:
            from app.monitoramento.models import EntregaMonitorada
            
            entregas_cliente = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.cliente.ilike(f'%{cliente}%'),
                EntregaMonitorada.entregue == False
            ).all()
            
            alertas_cliente = []
            hoje = date.today()
            
            for entrega in entregas_cliente:
                if entrega.data_entrega_prevista and entrega.data_entrega_prevista < hoje:
                    dias_atraso = (hoje - entrega.data_entrega_prevista).days
                    alertas_cliente.append({
                        'numero_nf': entrega.numero_nf,
                        'tipo': 'atraso',
                        'dias_atraso': dias_atraso
                    })
                elif not entrega.data_entrega_prevista:
                    alertas_cliente.append({
                        'numero_nf': entrega.numero_nf,
                        'tipo': 'sem_agendamento'
                    })
            
            return {
                'cliente': cliente,
                'total_pendencias': len(alertas_cliente),
                'alertas': alertas_cliente
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar alerta de cliente específico: {e}")
            return None

# Instância global do motor de alertas
alert_engine = AlertEngine()

def get_alert_engine():
    """Retorna instância do motor de alertas"""
    return alert_engine 