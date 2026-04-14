#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE ALERTAS PARA CARTEIRA DE PEDIDOS
Gerencia alertas relacionados a separações cotadas e outras situações críticas

INTEGRADO COM: app.notificacoes.services.NotificationDispatcher
- Alertas são persistidos em alerta_notificacoes
- Suporta envio por email, webhook e in_app
"""

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
        Detecta alterações que afetaram separações cotadas APÓS sincronização.

        OTIMIZACAO (2026-04-14): Usa 1 query batch com JOIN Separacao x Pedido
        filtrando por num_pedido IN (lista) + status='COTADO', ao inves de
        N queries individuais dentro do loop (gargalo historico do Step 2
        do scheduler: 500+ queries por ciclo quando ha muitos itens alterados).
        """
        alertas = []

        if not alteracoes_detectadas:
            return alertas

        try:
            from app.separacao.models import Separacao
            from app.pedidos.models import Pedido

            # Coletar num_pedidos unicos das alteracoes
            pedidos_afetados = {
                a['num_pedido'] for a in alteracoes_detectadas
                if a.get('num_pedido')
            }
            if not pedidos_afetados:
                return alertas

            # 1 query batch: buscar TODAS separacoes cotadas dos pedidos afetados
            separacoes_cotadas = db.session.query(
                Separacao.num_pedido,
                Separacao.separacao_lote_id
            ).join(
                Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
            ).filter(
                Separacao.num_pedido.in_(pedidos_afetados),
                Pedido.status == 'COTADO'
            ).all()

            # Dict {num_pedido: separacao_lote_id} para lookup O(1)
            # Se houver mais de uma separacao cotada por pedido, pega a primeira
            sep_por_pedido = {}
            for num_pedido, sep_lote_id in separacoes_cotadas:
                sep_por_pedido.setdefault(num_pedido, sep_lote_id)

            for alteracao in alteracoes_detectadas:
                separacao_lote_id = sep_por_pedido.get(alteracao.get('num_pedido'))
                if separacao_lote_id:
                    alertas.append({
                        'nivel': 'CRITICO',
                        'tipo': 'SEPARACAO_COTADA_ALTERADA',
                        'separacao_lote_id': separacao_lote_id,
                        'pedido': alteracao['num_pedido'],
                        'produto': alteracao.get('cod_produto', 'N/A'),
                        'alteracao': alteracao['tipo_alteracao'],
                        'timestamp': agora_utc_naive(),
                        'mensagem': f'URGENTE: Separacao COTADA {separacao_lote_id} foi afetada por alteracao no Odoo',
                        'acao_requerida': 'Verificar impacto no processo fisico imediatamente'
                    })

            return alertas

        except ImportError:
            logger.warning("Modulo separacao nao disponivel para deteccao de alertas")
            return []
        except Exception as e:
            logger.error(f"Erro ao detectar alteracoes em separacoes cotadas: {e}")
            return []
