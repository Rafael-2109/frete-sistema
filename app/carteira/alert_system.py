#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE ALERTAS PARA CARTEIRA DE PEDIDOS
Gerencia alertas relacionados a separações cotadas e outras situações críticas

INTEGRADO COM: app.notificacoes.services.NotificationDispatcher
- Alertas são persistidos em alerta_notificacoes
- Suporta envio por email, webhook e in_app
"""

from datetime import datetime
from app.utils.logging_config import logger
from app import db
from app.utils.timezone import agora_utc_naive

class AlertaSistemaCarteira:
    """
    Sistema centralizado de alertas para operações críticas da carteira
    """
    
    @staticmethod
    def verificar_separacoes_cotadas_antes_sincronizacao():
        """
        Verifica separações cotadas antes da sincronização com Odoo
        Retorna alertas se existirem separações que podem ser afetadas
        """
        try:
            from app.separacao.models import Separacao
            from app.pedidos.models import Pedido
            from app import db
            
            # CORRIGIDO: Separacao não tem campo 'status', usar Pedido.status via JOIN
            separacoes_cotadas = db.session.query(Separacao).join(
                Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
            ).filter(
                Pedido.status == 'COTADO'
            ).all()
            
            if separacoes_cotadas:
                return {
                    'alertas': True,
                    'nivel': 'ATENCAO',
                    'quantidade': len(separacoes_cotadas),
                    'separacoes_afetadas': [s.separacao_lote_id for s in separacoes_cotadas],
                    'mensagem': f'ATENCAO: {len(separacoes_cotadas)} separacoes COTADAS podem ser afetadas',
                    'recomendacao': 'Confirme se estas separacoes ja foram processadas fisicamente',
                    'timestamp': agora_utc_naive()
                }
            
            return {'alertas': False, 'timestamp': agora_utc_naive()}
            
        except ImportError:
            logger.warning("Modulo separacao nao disponivel para verificacao de alertas")
            return {'alertas': False, 'erro': 'Modulo separacao indisponivel'}
        except Exception as e:
            logger.error(f"Erro ao verificar separacoes cotadas: {e}")
            return {'alertas': False, 'erro': str(e)}
    
    @staticmethod
    def detectar_alteracoes_separacao_cotada_pos_sincronizacao(alteracoes_detectadas):
        """
        Detecta alterações que afetaram separações cotadas APÓS sincronização
        """
        alertas = []
        
        try:
            from app.separacao.models import Separacao
            
            for alteracao in alteracoes_detectadas:
                # Buscar se pedido tem separação cotada - CORRIGIDO: usar Pedido.status
                from app.pedidos.models import Pedido
                separacao_cotada = db.session.query(Separacao).join(
                    Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
                ).filter(
                    Separacao.num_pedido == alteracao['num_pedido'],
                    Pedido.status == 'COTADO'
                ).first()
                
                if separacao_cotada:
                    alertas.append({
                        'nivel': 'CRITICO',
                        'tipo': 'SEPARACAO_COTADA_ALTERADA',
                        'separacao_lote_id': separacao_cotada.separacao_lote_id,
                        'pedido': alteracao['num_pedido'],
                        'produto': alteracao.get('cod_produto', 'N/A'),
                        'alteracao': alteracao['tipo_alteracao'],
                        'timestamp': agora_utc_naive(),
                        'mensagem': f'URGENTE: Separacao COTADA {separacao_cotada.separacao_lote_id} foi afetada por alteracao no Odoo',
                        'acao_requerida': 'Verificar impacto no processo fisico imediatamente'
                    })
            
            return alertas
            
        except ImportError:
            logger.warning("Modulo separacao nao disponivel para deteccao de alertas")
            return []
        except Exception as e:
            logger.error(f"Erro ao detectar alteracoes em separacoes cotadas: {e}")
            return []
    
    @staticmethod
    def gerar_alerta_critico(tipo, dados, email_destinatario=None):
        """
        Gera alerta crítico padronizado e envia via NotificationDispatcher.

        Args:
            tipo: Tipo do alerta (ex: PRE_SEPARACAO_CONFLITO)
            dados: Dicionario com contexto do alerta
            email_destinatario: Email para notificacao (opcional)

        Returns:
            dict: Alerta gerado com resultado do envio
        """
        try:
            alerta = {
                'nivel': 'CRITICO',
                'tipo': tipo,
                'timestamp': agora_utc_naive(),
                'dados': dados
            }

            # Log crítico
            logger.critical(f"ALERTA CRITICO: {tipo} | {dados}")

            # IMPLEMENTADO: Enviar via NotificationDispatcher
            try:
                from app.notificacoes.services import enviar_alerta_critico

                titulo = dados.get('mensagem', tipo)[:100]  # Limita titulo
                mensagem = dados.get('mensagem', f'Alerta critico do tipo {tipo}')

                resultado_envio = enviar_alerta_critico(
                    titulo=titulo,
                    mensagem=mensagem,
                    tipo=tipo,
                    dados=dados,
                    email_destinatario=email_destinatario,
                    origem='alert_system.gerar_alerta_critico',
                )

                alerta['envio'] = resultado_envio
                logger.info(f"Alerta {tipo} enviado via NotificationDispatcher: {resultado_envio.get('success')}")

            except ImportError as e:
                logger.warning(f"Modulo notificacoes nao disponivel: {e}")
                alerta['envio'] = {'success': False, 'error': 'Modulo notificacoes nao disponivel'}
            except Exception as e:
                logger.error(f"Erro ao enviar via NotificationDispatcher: {e}")
                alerta['envio'] = {'success': False, 'error': str(e)}

            return alerta

        except Exception as e:
            logger.error(f"Erro ao gerar alerta critico: {e}")
            return None
    
    @staticmethod
    def gerar_alerta_pre_separacao_conflito(num_pedido, cod_produto, contexto_duplicado):
        """
        Gera alerta quando há conflito na constraint única de pré-separação
        """
        return AlertaSistemaCarteira.gerar_alerta_critico(
            'PRE_SEPARACAO_CONFLITO',
            {
                'pedido': num_pedido,
                'produto': cod_produto,
                'contexto': contexto_duplicado,
                'mensagem': f'Tentativa de criar pre-separacao com contexto duplicado: {num_pedido}-{cod_produto}',
                'acao_requerida': 'Verificar logica de criacao de pre-separacoes'
            }
        )
    
    @staticmethod
    def gerar_alerta_quantidade_insuficiente(num_pedido, cod_produto, qtd_solicitada, qtd_disponivel):
        """
        Gera alerta quando quantidade solicitada excede disponível
        """
        return AlertaSistemaCarteira.gerar_alerta_critico(
            'QUANTIDADE_INSUFICIENTE',
            {
                'pedido': num_pedido,
                'produto': cod_produto,
                'qtd_solicitada': qtd_solicitada,
                'qtd_disponivel': qtd_disponivel,
                'deficit': qtd_solicitada - qtd_disponivel,
                'mensagem': f'Quantidade insuficiente para pre-separacao: {num_pedido}-{cod_produto}',
                'acao_requerida': 'Verificar estoque ou ajustar quantidade'
            }
        )
    
    @staticmethod
    def processar_alertas_interface(alertas):
        """
        Processa alertas para exibição na interface
        Retorna formato padronizado para frontend
        """
        if not alertas:
            return {'tem_alertas': False, 'alertas': []}
        
        alertas_processados = []
        
        for alerta in alertas if isinstance(alertas, list) else [alertas]:
            alerta_interface = {
                'nivel': alerta.get('nivel', 'INFO'),
                'titulo': alerta.get('tipo', 'ALERTA'),
                'mensagem': alerta.get('mensagem', 'Alerta sem detalhes'),
                'timestamp': alerta.get('timestamp', agora_utc_naive()).strftime('%d/%m/%Y %H:%M:%S'),
                'acao': alerta.get('acao_requerida', 'Nenhuma acao especifica'),
                'dados': alerta.get('dados', {})
            }
            alertas_processados.append(alerta_interface)
        
        return {
            'tem_alertas': len(alertas_processados) > 0,
            'total_alertas': len(alertas_processados),
            'alertas': alertas_processados
        }


class MonitoramentoSincronizacao:
    """
    Monitor específico para sincronização com Odoo
    """
    
    @staticmethod
    def pre_sincronizacao_check():
        """
        Executa verificações antes da sincronização
        """
        logger.info("Executando verificacoes pre-sincronizacao...")
        
        # Verificar separações cotadas
        resultado_cotadas = AlertaSistemaCarteira.verificar_separacoes_cotadas_antes_sincronizacao()
        
        # TODO: Adicionar outras verificações
        # - Pré-separações em processamento
        # - Conflitos de dados pendentes
        # - Status da base de dados
        
        return {
            'safe_to_sync': not resultado_cotadas.get('alertas', False),
            'warnings': [resultado_cotadas] if resultado_cotadas.get('alertas') else [],
            'timestamp': agora_utc_naive()
        }
    
    @staticmethod
    def pos_sincronizacao_check(alteracoes):
        """
        Executa verificações após a sincronização
        """
        logger.info("Executando verificacoes pos-sincronizacao...")
        
        # Detectar impactos em separações cotadas
        alertas_cotadas = AlertaSistemaCarteira.detectar_alteracoes_separacao_cotada_pos_sincronizacao(alteracoes)
        
        # TODO: Adicionar outras verificações
        # - Integridade das pré-separações
        # - Recomposição automática
        # - Validação de quantidades
        
        return {
            'alertas_criticos': alertas_cotadas,
            'total_alteracoes': len(alteracoes),
            'timestamp': agora_utc_naive()
        }