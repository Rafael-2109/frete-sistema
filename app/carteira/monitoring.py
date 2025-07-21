#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE MONITORAMENTO PARA CARTEIRA DE PEDIDOS
Logging, métricas e auditoria para operações críticas
"""

import time
import logging
from datetime import datetime, timedelta
from functools import wraps
from app.utils.logging_config import logger
from app import db


class MetricasCarteira:
    """
    Coletor de métricas para operações da carteira
    """
    
    @staticmethod
    def registrar_operacao_pre_separacao(operacao, dados, tempo_execucao=None, sucesso=True):
        """
        Registra métricas de operações de pré-separação
        """
        try:
            metrica = {
                'timestamp': datetime.utcnow(),
                'operacao': operacao,
                'sucesso': sucesso,
                'tempo_execucao_ms': tempo_execucao,
                'dados': dados
            }
            
            logger.info(f"METRICA PRE_SEPARACAO: {operacao} | Sucesso: {sucesso} | Tempo: {tempo_execucao}ms | {dados}")
            
            # TODO: Persistir métricas em base de dados ou enviar para sistema de monitoramento
            # return persistir_metrica(metrica)
            
            return metrica
            
        except Exception as e:
            logger.error(f"Erro ao registrar métrica: {e}")
            return None
    
    @staticmethod
    def registrar_sincronizacao_odoo(resultado, tempo_execucao, alteracoes_detectadas):
        """
        Registra métricas de sincronização com Odoo
        """
        try:
            metrica = {
                'timestamp': datetime.utcnow(),
                'operacao': 'SINCRONIZACAO_ODOO',
                'sucesso': resultado.get('sucesso', False),
                'tempo_execucao_ms': tempo_execucao,
                'total_alteracoes': len(alteracoes_detectadas),
                'tipos_alteracao': list(set(alt.get('tipo', 'UNKNOWN') for alt in alteracoes_detectadas)),
                'resultado': resultado
            }
            
            nivel = 'info' if resultado.get('sucesso') else 'error'
            getattr(logger, nivel)(f"METRICA SINCRONIZACAO: Sucesso: {metrica['sucesso']} | "
                                  f"Tempo: {tempo_execucao}ms | Alterações: {len(alteracoes_detectadas)}")
            
            return metrica
            
        except Exception as e:
            logger.error(f"Erro ao registrar métrica de sincronização: {e}")
            return None
    
    @staticmethod
    def registrar_calculo_estoque(cod_produto, data_expedicao, resultado, tempo_execucao):
        """
        Registra métricas de cálculo de estoque
        """
        try:
            metrica = {
                'timestamp': datetime.utcnow(),
                'operacao': 'CALCULO_ESTOQUE',
                'produto': cod_produto,
                'data_expedicao': data_expedicao.isoformat() if data_expedicao else None,
                'estoque_calculado': resultado,
                'tempo_execucao_ms': tempo_execucao,
                'sucesso': resultado is not None
            }
            
            logger.debug(f"METRICA ESTOQUE: {cod_produto} | Data: {data_expedicao} | "
                        f"Resultado: {resultado} | Tempo: {tempo_execucao}ms")
            
            return metrica
            
        except Exception as e:
            logger.error(f"Erro ao registrar métrica de estoque: {e}")
            return None


class AuditoriaCarteira:
    """
    Sistema de auditoria para operações críticas
    """
    
    @staticmethod
    def registrar_alteracao_pre_separacao(pre_separacao_id, operacao, dados_anterior, dados_novo, usuario):
        """
        Registra alterações em pré-separações para auditoria
        """
        try:
            registro_auditoria = {
                'timestamp': datetime.utcnow(),
                'tipo': 'PRE_SEPARACAO_ALTERACAO',
                'pre_separacao_id': pre_separacao_id,
                'operacao': operacao,  # CRIACAO, EDICAO, CANCELAMENTO, ENVIO_SEPARACAO
                'dados_anterior': dados_anterior,
                'dados_novo': dados_novo,
                'usuario': usuario,
                'ip_origem': None  # TODO: Capturar IP da requisição
            }
            
            logger.info(f"AUDITORIA PRE_SEPARACAO: {operacao} | ID: {pre_separacao_id} | Usuario: {usuario}")
            
            # TODO: Persistir em tabela de auditoria
            # return persistir_auditoria(registro_auditoria)
            
            return registro_auditoria
            
        except Exception as e:
            logger.error(f"Erro ao registrar auditoria: {e}")
            return None
    
    @staticmethod
    def registrar_violacao_constraint(tabela, constraint, dados_tentativa, usuario):
        """
        Registra tentativas de violação de constraints para análise
        """
        try:
            registro = {
                'timestamp': datetime.utcnow(),
                'tipo': 'VIOLACAO_CONSTRAINT',
                'tabela': tabela,
                'constraint': constraint,
                'dados_tentativa': dados_tentativa,
                'usuario': usuario
            }
            
            logger.warning(f"VIOLACAO CONSTRAINT: {constraint} | Tabela: {tabela} | Usuario: {usuario} | "
                          f"Dados: {dados_tentativa}")
            
            return registro
            
        except Exception as e:
            logger.error(f"Erro ao registrar violação de constraint: {e}")
            return None
    
    @staticmethod
    def registrar_alerta_critico(tipo_alerta, dados, nivel='CRITICO'):
        """
        Registra alertas críticos do sistema
        """
        try:
            registro = {
                'timestamp': datetime.utcnow(),
                'tipo': 'ALERTA_CRITICO',
                'nivel': nivel,
                'alerta_tipo': tipo_alerta,
                'dados': dados
            }
            
            logger.critical(f"ALERTA {nivel}: {tipo_alerta} | {dados}")
            
            return registro
            
        except Exception as e:
            logger.error(f"Erro ao registrar alerta crítico: {e}")
            return None


def monitorar_performance(operacao_nome):
    """
    Decorator para monitorar performance de operações
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            inicio = time.time()
            erro = None
            resultado = None
            
            try:
                resultado = func(*args, **kwargs)
                return resultado
                
            except Exception as e:
                erro = e
                raise
                
            finally:
                fim = time.time()
                tempo_execucao = int((fim - inicio) * 1000)  # em millisegundos
                
                # Registrar métrica
                MetricasCarteira.registrar_operacao_pre_separacao(
                    operacao=operacao_nome,
                    dados={
                        'funcao': func.__name__,
                        'args_count': len(args),
                        'kwargs_count': len(kwargs),
                        'erro': str(erro) if erro else None
                    },
                    tempo_execucao=tempo_execucao,
                    sucesso=erro is None
                )
                
        return wrapper
    return decorator


def auditar_alteracao(tipo_operacao):
    """
    Decorator para auditar alterações em modelos
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Capturar estado anterior se for uma edição
            dados_anterior = None
            pre_separacao_id = None
            
            try:
                # Tentar extrair ID da pré-separação dos argumentos
                if args and hasattr(args[0], 'id'):
                    pre_separacao_id = args[0].id
                    # Capturar dados atuais para auditoria
                    dados_anterior = {
                        'qtd_selecionada': getattr(args[0], 'qtd_selecionada_usuario', None),
                        'data_expedicao': getattr(args[0], 'data_expedicao_editada', None),
                        'data_agendamento': getattr(args[0], 'data_agendamento_editada', None),
                        'protocolo': getattr(args[0], 'protocolo_editado', None),
                        'status': getattr(args[0], 'status', None)
                    }
                
                # Executar função
                resultado = func(*args, **kwargs)
                
                # Capturar dados após alteração
                dados_novo = None
                if args and hasattr(args[0], 'id'):
                    dados_novo = {
                        'qtd_selecionada': getattr(args[0], 'qtd_selecionada_usuario', None),
                        'data_expedicao': getattr(args[0], 'data_expedicao_editada', None),
                        'data_agendamento': getattr(args[0], 'data_agendamento_editada', None),
                        'protocolo': getattr(args[0], 'protocolo_editado', None),
                        'status': getattr(args[0], 'status', None)
                    }
                
                # Registrar auditoria
                if pre_separacao_id:
                    AuditoriaCarteira.registrar_alteracao_pre_separacao(
                        pre_separacao_id=pre_separacao_id,
                        operacao=tipo_operacao,
                        dados_anterior=dados_anterior,
                        dados_novo=dados_novo,
                        usuario='sistema'  # TODO: Capturar usuário atual
                    )
                
                return resultado
                
            except Exception as e:
                # Registrar erro em auditoria
                if pre_separacao_id:
                    AuditoriaCarteira.registrar_alteracao_pre_separacao(
                        pre_separacao_id=pre_separacao_id,
                        operacao=f"{tipo_operacao}_ERRO",
                        dados_anterior=dados_anterior,
                        dados_novo={'erro': str(e)},
                        usuario='sistema'
                    )
                raise
                
        return wrapper
    return decorator


class MonitorSaude:
    """
    Monitor de saúde do sistema de carteira
    """
    
    @staticmethod
    def verificar_inconsistencias_pre_separacao():
        """
        Verifica inconsistências na base de dados de pré-separações
        """
        try:
            from app.carteira.models import PreSeparacaoItem
            
            verificacoes = {}
            
            # 1. Pré-separações sem data de expedição (violam nova constraint)
            sem_data_expedicao = PreSeparacaoItem.query.filter(
                PreSeparacaoItem.data_expedicao_editada.is_(None)
            ).count()
            
            verificacoes['sem_data_expedicao'] = sem_data_expedicao
            
            # 2. Pré-separações com quantidades zeradas ou negativas
            qtd_invalida = PreSeparacaoItem.query.filter(
                db.or_(
                    PreSeparacaoItem.qtd_selecionada_usuario <= 0,
                    PreSeparacaoItem.qtd_selecionada_usuario.is_(None)
                )
            ).count()
            
            verificacoes['quantidade_invalida'] = qtd_invalida
            
            # 3. Pré-separações órfãs (sem item correspondente na carteira)
            # TODO: Implementar verificação de referência
            
            # 4. Status de saúde geral
            total_pre_separacoes = PreSeparacaoItem.query.count()
            pre_separacoes_ativas = PreSeparacaoItem.query.filter(
                PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
            ).count()
            
            verificacoes['total_registros'] = total_pre_separacoes
            verificacoes['registros_ativos'] = pre_separacoes_ativas
            verificacoes['saude_geral'] = 'OK' if (sem_data_expedicao + qtd_invalida) == 0 else 'PROBLEMAS'
            
            logger.info(f"MONITOR SAUDE: {verificacoes}")
            return verificacoes
            
        except Exception as e:
            logger.error(f"Erro na verificação de saúde: {e}")
            return {'erro': str(e), 'saude_geral': 'ERRO'}
    
    @staticmethod
    def relatorio_uso_diario():
        """
        Gera relatório de uso diário do sistema
        """
        try:
            from app.carteira.models import PreSeparacaoItem
            
            hoje = datetime.now().date()
            ontem = hoje - timedelta(days=1)
            
            # Pré-separações criadas hoje
            criadas_hoje = PreSeparacaoItem.query.filter(
                db.func.date(PreSeparacaoItem.data_criacao) == hoje
            ).count()
            
            # Pré-separações criadas ontem
            criadas_ontem = PreSeparacaoItem.query.filter(
                db.func.date(PreSeparacaoItem.data_criacao) == ontem
            ).count()
            
            relatorio = {
                'data': hoje.isoformat(),
                'pre_separacoes_criadas_hoje': criadas_hoje,
                'pre_separacoes_criadas_ontem': criadas_ontem,
                'variacao_diaria': criadas_hoje - criadas_ontem,
                'timestamp': datetime.utcnow()
            }
            
            logger.info(f"RELATORIO DIARIO: {relatorio}")
            return relatorio
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório diário: {e}")
            return {'erro': str(e)}


# Inicialização do sistema de monitoramento
def inicializar_monitoramento():
    """
    Inicializa sistema de monitoramento
    """
    logger.info("Inicializando sistema de monitoramento da carteira")
    
    # Verificar saúde inicial
    saude = MonitorSaude.verificar_inconsistencias_pre_separacao()
    
    if saude.get('saude_geral') != 'OK':
        logger.warning(f"Sistema inicializado com problemas de saúde: {saude}")
    else:
        logger.info("Sistema de monitoramento inicializado com saúde OK")
    
    return saude