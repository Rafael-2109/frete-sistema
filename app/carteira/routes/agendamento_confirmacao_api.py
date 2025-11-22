"""
API simplificada para confirmação de agendamento em Separações
Funciona para qualquer status
✅ ATUALIZADO: Sincroniza com EmbarqueItem (se existir) via SincronizadorAgendamentoService
"""

from flask import jsonify
from flask_login import login_required, current_user
from app import db
from app.separacao.models import Separacao
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/separacao/<string:lote_id>/confirmar-agendamento', methods=['POST'])
@login_required
def confirmar_agendamento_separacao(lote_id):
    """Confirmar agendamento de todas as separações de um lote (independente do status)"""
    try:
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

        if not separacoes:
            return jsonify({
                'success': False,
                'error': f'Nenhuma separação encontrada para o lote {lote_id}'
            }), 404

        # Verificar se todas têm data de agendamento
        sem_agendamento = [s for s in separacoes if not s.agendamento]
        if sem_agendamento:
            return jsonify({
                'success': False,
                'error': f'{len(sem_agendamento)} de {len(separacoes)} itens não possuem data de agendamento'
            }), 400

        # Confirmar agendamento de todas
        for sep in separacoes:
            sep.agendamento_confirmado = True

        db.session.commit()

        logger.info(f"Agendamento confirmado para lote {lote_id} ({len(separacoes)} itens) por {current_user.nome}")

        # ✅ SINCRONIZAR com EmbarqueItem (se existir)
        tabelas_sincronizadas = []
        try:
            from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

            sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome)
            resultado_sync = sincronizador.sincronizar_desde_separacao(
                separacao_lote_id=lote_id,
                criar_agendamento=False  # Não criar AgendamentoEntrega pois pode não existir EntregaMonitorada
            )

            if resultado_sync['success']:
                tabelas_sincronizadas = resultado_sync.get('tabelas_atualizadas', [])
                if tabelas_sincronizadas:
                    logger.info(f"[SINCRONIZAÇÃO] Tabelas atualizadas: {', '.join(tabelas_sincronizadas)}")
        except Exception as sync_error:
            logger.warning(f"Aviso na sincronização: {sync_error}")

        return jsonify({
            'success': True,
            'message': f'Agendamento confirmado para {len(separacoes)} itens',
            'tabelas_sincronizadas': tabelas_sincronizadas
        })

    except Exception as e:
        logger.error(f"Erro ao confirmar agendamento do lote {lote_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/separacao/<string:lote_id>/reverter-agendamento', methods=['POST'])
@login_required
def reverter_agendamento_separacao(lote_id):
    """Reverter confirmação de agendamento de todas as separações de um lote (independente do status)"""
    try:
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

        if not separacoes:
            return jsonify({
                'success': False,
                'error': f'Nenhuma separação encontrada para o lote {lote_id}'
            }), 404

        # Reverter confirmação de todas
        for sep in separacoes:
            sep.agendamento_confirmado = False

        db.session.commit()

        logger.info(f"Confirmação de agendamento revertida para lote {lote_id} ({len(separacoes)} itens) por {current_user.nome}")

        # ✅ SINCRONIZAR com EmbarqueItem (se existir)
        tabelas_sincronizadas = []
        try:
            from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

            sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome)
            resultado_sync = sincronizador.sincronizar_desde_separacao(
                separacao_lote_id=lote_id,
                criar_agendamento=False
            )

            if resultado_sync['success']:
                tabelas_sincronizadas = resultado_sync.get('tabelas_atualizadas', [])
                if tabelas_sincronizadas:
                    logger.info(f"[SINCRONIZAÇÃO] Tabelas atualizadas: {', '.join(tabelas_sincronizadas)}")
        except Exception as sync_error:
            logger.warning(f"Aviso na sincronização: {sync_error}")

        return jsonify({
            'success': True,
            'message': f'Confirmação revertida para {len(separacoes)} itens',
            'tabelas_sincronizadas': tabelas_sincronizadas
        })

    except Exception as e:
        logger.error(f"Erro ao reverter agendamento do lote {lote_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
